"""DuffelFlightProvider against a mocked Duffel API (httpx2.MockTransport + captured responses)."""

import json

import httpx2
import pytest

from app.flights.core.config import get_duffel_settings
from app.flights.domain.errors import InvalidSearchError, ProviderError, ProviderTimeoutError
from app.flights.providers.duffel.client import DuffelClient
from app.flights.providers.duffel.provider import DuffelFlightProvider
from app.flights.tests.support import load_fixture, make_criteria

pytestmark = pytest.mark.anyio


def make_provider(handler) -> DuffelFlightProvider:
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return DuffelFlightProvider(DuffelClient(http, get_duffel_settings()))


def respond(status: int, fixture: str):
    return lambda request: httpx2.Response(status, json=load_fixture(fixture))


async def test_sends_the_expected_request():
    requests: list[httpx2.Request] = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(201, json=load_fixture("duffel/offer_request_response.json"))

    await make_provider(handler).search(make_criteria())

    (request,) = requests
    assert request.method == "POST"
    assert request.url.host == "duffel.invalid"
    assert request.url.path == "/air/offer_requests"
    assert request.url.params["supplier_timeout"] == "45000"
    assert request.headers["Authorization"] == "Bearer duffel_test_fake_token"
    assert request.headers["Duffel-Version"] == "v2"
    body = json.loads(request.content)
    assert body["data"]["slices"][0]["origin"] == "LHR"
    assert body["data"]["passengers"] == [{"type": "adult"}]


async def test_maps_the_response():
    result = await make_provider(respond(201, "duffel/offer_request_response.json")).search(make_criteria())

    assert result.provider == "duffel"
    assert len(result.offers) == 56


async def test_filters_offers_by_selling_airline():
    provider = make_provider(respond(201, "duffel/offer_request_response.json"))

    result = await provider.search(make_criteria(airlines=["ba", "IB"]))

    assert sorted(o.owner.code for o in result.offers) == ["BA", "IB"]


async def test_airline_filter_matches_owner_only():
    """Lufthansa offers flown by SWISS don't match a search for LX."""
    provider = make_provider(respond(201, "duffel/offer_request_response.json"))

    result = await provider.search(make_criteria(airlines=["LX"]))

    assert result.offers == []


async def test_rejected_criteria_become_invalid_search():
    provider = make_provider(respond(422, "duffel/error_invalid_iata_code.json"))

    with pytest.raises(InvalidSearchError, match="Expected a valid IATA code"):
        await provider.search(make_criteria(origin="XQZ"))


async def test_authentication_failure_hides_provider_details():
    provider = make_provider(respond(401, "duffel/error_access_token_not_found.json"))

    with pytest.raises(ProviderError) as error:
        await provider.search(make_criteria())

    assert type(error.value) is ProviderError
    assert "token" not in error.value.message.lower()


async def test_server_error_becomes_provider_error():
    provider = make_provider(lambda request: httpx2.Response(503, text="Service Unavailable"))

    with pytest.raises(ProviderError):
        await provider.search(make_criteria())


async def test_timeout_becomes_provider_timeout():
    def handler(request):
        raise httpx2.ReadTimeout("timed out", request=request)

    with pytest.raises(ProviderTimeoutError):
        await make_provider(handler).search(make_criteria())


async def test_network_failure_becomes_provider_error():
    def handler(request):
        raise httpx2.ConnectError("connection refused", request=request)

    with pytest.raises(ProviderError) as error:
        await make_provider(handler).search(make_criteria())

    assert type(error.value) is ProviderError
