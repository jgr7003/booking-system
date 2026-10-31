from datetime import date, timedelta
from decimal import Decimal

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.core.db import get_session_factory
from app.core.http import get_http_client
from app.core.pricing.fixed_fee_random_percent import FIXED_FEE, MAX_PERCENT, MIN_PERCENT
from app.flights.api.dependencies import get_flight_provider
from app.flights.domain.errors.provider import ProviderError, ProviderTimeoutError
from app.flights.domain.errors.search import InvalidSearchError
from app.flights.tests.support import FakeFlightProvider, load_fixture
from app.main import app

client = TestClient(app)
URL = "/api/v1/flights/search"


@pytest.fixture(autouse=True)
def main_platform():
    """Requests arrive at the main platform, where the session is optional: its database is never read."""
    app.dependency_overrides[get_session_factory] = lambda: None


def body(**overrides):
    departure = (date.today() + timedelta(days=30)).isoformat()
    return {"origin": "LHR", "destination": "JFK", "departure_date": departure} | overrides


def use_provider(provider):
    app.dependency_overrides[get_flight_provider] = lambda: provider
    return provider


def fares_of(data):
    return [fare for flight in data["flights"] for fare in flight["fares"]]


def test_returns_flights_with_sale_price_only(search_result):
    use_provider(FakeFlightProvider(search_result))

    response = client.post(URL, json=body())

    assert response.status_code == 200
    assert '"cost"' not in response.text
    assert '"markup"' not in response.text
    data = response.json()
    assert data["search_id"] == "orq_0000BBiPI0fBoJ3vgP3eAA"
    assert data["passengers"] == [{"id": "pas_0000BBiPI0fXmzLVhVDviC", "type": "adult", "age": None}]
    assert len(data["flights"]) == 16
    assert len(fares_of(data)) == 56


def test_sale_price_includes_the_markup(search_result):
    use_provider(FakeFlightProvider(search_result))
    costs = {o.id: o.cost.total.amount for o in search_result.offers}

    fares = fares_of(client.post(URL, json=body()).json())

    for fare in fares:
        cost = costs[fare["offer_id"]]
        sale = Decimal(fare["price"]["total"]["amount"])
        assert FIXED_FEE + cost * MIN_PERCENT / 100 - Decimal("0.01") <= sale - cost
        assert sale - cost <= FIXED_FEE + cost * MAX_PERCENT / 100 + Decimal("0.01")


def test_amounts_are_strings_and_flights_sorted_by_lowest_price(search_result):
    use_provider(FakeFlightProvider(search_result))

    flights = client.post(URL, json=body()).json()["flights"]

    lowest = [f["lowest_price"]["amount"] for f in flights]
    assert all(isinstance(t, str) for t in lowest)
    assert [Decimal(t) for t in lowest] == sorted(Decimal(t) for t in lowest)
    assert all(f["lowest_price"] == f["fares"][0]["price"]["total"] for f in flights)


def test_flight_contract(search_result):
    use_provider(FakeFlightProvider(search_result))

    data = client.post(URL, json=body()).json()

    flight = next(f for f in data["flights"] if any(x["offer_id"] == "off_034l6ScLRLhYObdEbC8k1g" for x in f["fares"]))
    assert len(flight["key"]) == 16
    assert flight["owner"]["conditions_of_carriage_url"].startswith("https://")
    assert flight["slices"][0]["segments"][0]["cabin"]["amenities"]["seat_pitch"] == "29"
    impact = next(x for x in flight["fares"] if x["slices"][0]["fare_brand"] == "Economy Impact")
    assert impact["slices"][0]["baggage"] == [{"checked": 1, "carry_on": None, "passenger_id": "pas_0000BBiPI0fXmzLVhVDviC"}]
    assert data["expires_at"] == "2026-10-23T21:26:50Z"


def test_criteria_reach_the_provider_normalized(search_result):
    provider = use_provider(FakeFlightProvider(search_result))

    client.post(URL, json=body(origin="lhr", airlines=["ba"], passengers={"adults": 2, "children_ages": [5]}))

    (criteria,) = provider.calls
    assert criteria.origin == "LHR"
    assert criteria.airlines == ["BA"]
    assert criteria.passengers.children_ages == [5]


@pytest.mark.parametrize(
    "overrides",
    [
        {"destination": "LHR"},
        {"departure_date": (date.today() - timedelta(days=1)).isoformat()},
        {"return_date": date.today().isoformat()},
        {"passengers": {"adults": 5, "children_ages": [3, 4, 5, 6, 7]}},
        {"passengers": {"adults": 1, "children_ages": [0, 1]}},
        {"passengers": {"adults": 0}},
        {"origin": "LONDON"},
        {"airlines": ["B"]},
        {"cabin_class": "luxury"},
        {"max_connections": 3},
    ],
)
def test_invalid_criteria_are_rejected_before_calling_the_provider(overrides, search_result):
    provider = use_provider(FakeFlightProvider(search_result))

    response = client.post(URL, json=body(**overrides))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert provider.calls == []


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (InvalidSearchError("Field 'origin' is invalid."), 422, "invalid_search"),
        (ProviderError("The flight provider failed."), 502, "provider_error"),
        (ProviderTimeoutError("The flight provider didn't answer in time."), 504, "provider_timeout"),
    ],
)
def test_provider_errors_map_to_http(error, status, code):
    use_provider(FakeFlightProvider(error=error))

    response = client.post(URL, json=body())

    assert response.status_code == status
    assert response.json() == {"error": {"code": code, "message": error.message}}


def test_end_to_end_through_the_duffel_adapter():
    """Real wiring (API → service → Duffel adapter) with only the HTTP transport mocked."""
    duffel = httpx2.AsyncClient(
        transport=httpx2.MockTransport(
            lambda request: httpx2.Response(201, json=load_fixture("duffel/offer_request_response.json"))
        )
    )
    app.dependency_overrides[get_http_client] = lambda: duffel

    response = client.post(URL, json=body(airlines=["BA"]))

    assert response.status_code == 200
    (flight,) = response.json()["flights"]
    assert flight["owner"]["code"] == "BA"
    assert Decimal(flight["lowest_price"]["amount"]) > Decimal("214.34")


def test_safety_net_blocks_unmocked_provider_calls():
    with pytest.raises(AssertionError, match="Unexpected outbound HTTP request"):
        client.post(URL, json=body())
