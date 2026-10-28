"""Booking operations of DuffelFlightProvider against a mocked Duffel API (captured responses)."""

import json
import uuid
from decimal import Decimal

import httpx2
import pytest

from app.core.money import Money
from app.flights.core.config import get_duffel_settings
from app.flights.domain.dtos.bookings import AirlinePassenger
from app.flights.domain.dtos.orders import OrderRequest
from app.flights.domain.errors.provider import (
    OfferAlreadyBookedError,
    OfferUnavailableError,
    OrderRejectedError,
    ProviderError,
    ProviderTimeoutError,
)
from app.flights.providers.duffel.client import DuffelClient
from app.flights.providers.duffel.provider import DuffelFlightProvider
from app.flights.tests.support import (
    BOOKING_OFFER_ID,
    BOOKING_PASSENGER_ID,
    CAPTURED_BOOKING_ID,
    load_fixture,
    make_booking_passenger,
)

pytestmark = pytest.mark.anyio


def make_provider(handler) -> DuffelFlightProvider:
    """Builds the adapter on a mocked transport.

    Args:
        handler: `MockTransport` handler.

    Returns:
        The adapter.
    """
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return DuffelFlightProvider(DuffelClient(http, get_duffel_settings()))


def respond(status: int, fixture: str):
    """Handler that always answers with a captured response.

    Args:
        status: HTTP status.
        fixture: Path of the fixture.

    Returns:
        The handler.
    """
    return lambda request: httpx2.Response(status, json=load_fixture(fixture))


def order_request(**overrides) -> OrderRequest:
    """The order of the captured booking: one passenger, 226.75 USD from the balance.

    Args:
        **overrides: Fields to change.

    Returns:
        The request.
    """
    fields = {
        "offer_id": BOOKING_OFFER_ID,
        "passenger_id": BOOKING_PASSENGER_ID,
        "passenger": AirlinePassenger.from_booking(make_booking_passenger(family_name="Muñoz")),
        "payment": Money(amount=Decimal("226.75"), currency="USD"),
        "booking_id": uuid.UUID(CAPTURED_BOOKING_ID),
    }
    return OrderRequest(**(fields | overrides))


async def test_get_offer_returns_the_current_cost_and_the_passenger_ids():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(200, json=load_fixture("duffel/offer_get_response.json"))

    bookable = await make_provider(handler).get_offer(BOOKING_OFFER_ID)

    assert requests[0].method == "GET"
    assert requests[0].url.path == f"/air/offers/{BOOKING_OFFER_ID}"
    assert bookable.offer.id == BOOKING_OFFER_ID
    assert bookable.offer.cost.total == Money(amount=Decimal("226.75"), currency="USD")
    assert bookable.passenger_ids == [BOOKING_PASSENGER_ID]


async def test_get_offer_of_a_missing_offer_is_unavailable():
    with pytest.raises(OfferUnavailableError):
        await make_provider(respond(404, "duffel/error_offer_not_found.json")).get_offer("off_missing")


async def test_create_order_sends_an_instant_order_paid_from_the_balance():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(201, json=load_fixture("duffel/order_create_response.json"))

    await make_provider(handler).create_order(order_request())

    (request,) = requests
    assert (request.method, request.url.path) == ("POST", "/air/orders")
    body = json.loads(request.content)["data"]
    assert body["type"] == "instant"
    assert body["selected_offers"] == [BOOKING_OFFER_ID]
    assert body["payments"] == [{"type": "balance", "amount": "226.75", "currency": "USD"}]
    assert body["metadata"] == {"booking_id": CAPTURED_BOOKING_ID}
    (passenger,) = body["passengers"]
    assert passenger == {
        "id": BOOKING_PASSENGER_ID,
        "title": "ms",
        "given_name": "ANA",
        "family_name": "MUNOZ",
        "gender": "f",
        "born_on": "1990-05-20",
        "email": "ana.prueba@example.com",
        "phone_number": "+5491112345678",
    }


async def test_create_order_sends_the_passport_when_there_is_one():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(201, json=load_fixture("duffel/order_create_response.json"))

    passenger = make_booking_passenger(
        identity_documents=[{"number": "AB1234567", "issuing_country_code": "AR", "expires_on": "2032-01-01"}]
    )
    await make_provider(handler).create_order(order_request(passenger=AirlinePassenger.from_booking(passenger)))

    assert json.loads(requests[0].content)["data"]["passengers"][0]["identity_documents"] == [
        {"type": "passport", "unique_identifier": "AB1234567", "issuing_country_code": "AR", "expires_on": "2032-01-01"}
    ]


async def test_create_order_maps_the_confirmed_order():
    order = await make_provider(respond(201, "duffel/order_create_response.json")).create_order(order_request())

    assert order.id == "ord_0000BBq6AsxIyF0XrJSB82"
    assert order.booking_reference == "M6BM7T"
    assert order.booking_id == uuid.UUID(CAPTURED_BOOKING_ID)
    assert order.total == Money(amount=Decimal("226.75"), currency="USD")
    assert order.owner.name == "Duffel Airways"
    assert [(t.passenger_id, t.number) for t in order.tickets] == [(BOOKING_PASSENGER_ID, "1")]
    assert order.paid_at is not None and not order.awaiting_payment
    assert order.available_actions == ["cancel", "change", "update"]
    segment = order.slices[0].segments[0]
    assert (segment.origin.code, segment.destination.code) == ("LHR", "JFK")
    assert segment.operating_carrier.name


@pytest.mark.parametrize(
    ("status", "fixture", "error"),
    [
        (422, "duffel/error_offer_request_already_booked.json", OfferAlreadyBookedError),
        (422, "duffel/error_payment_amount_mismatch.json", OrderRejectedError),
        (404, "duffel/error_offer_not_found.json", OfferUnavailableError),
    ],
)
async def test_create_order_translates_rejections(status, fixture, error):
    with pytest.raises(error):
        await make_provider(respond(status, fixture)).create_order(order_request())


async def test_an_offer_already_booked_is_also_an_unavailable_offer():
    assert issubclass(OfferAlreadyBookedError, OfferUnavailableError)


async def test_create_order_timeout_and_server_errors_leave_the_outcome_unknown():
    def timeout(request):
        raise httpx2.ReadTimeout("slow", request=request)

    with pytest.raises(ProviderTimeoutError):
        await make_provider(timeout).create_order(order_request())
    with pytest.raises(ProviderError):
        await make_provider(lambda request: httpx2.Response(503, json={})).create_order(order_request())


async def test_find_order_returns_the_order_of_this_booking():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(200, json=load_fixture("duffel/orders_list_one.json"))

    order = await make_provider(handler).find_order(BOOKING_OFFER_ID, uuid.UUID(CAPTURED_BOOKING_ID))

    assert requests[0].url.path == "/air/orders"
    assert requests[0].url.params["offer_id"] == BOOKING_OFFER_ID
    assert order.booking_reference == "M6BM7T"


async def test_find_order_ignores_orders_of_other_bookings_and_empty_lists():
    one = make_provider(respond(200, "duffel/orders_list_one.json"))
    empty = make_provider(respond(200, "duffel/orders_list_empty.json"))

    assert await one.find_order(BOOKING_OFFER_ID, uuid.uuid4()) is None
    assert await empty.find_order(BOOKING_OFFER_ID, uuid.UUID(CAPTURED_BOOKING_ID)) is None


async def test_an_expired_offer_is_unavailable_when_refreshing_it():
    # Duffel test answers an expired offer like a missing one (404 not_found).
    with pytest.raises(OfferUnavailableError):
        await make_provider(respond(404, "duffel/error_offer_expired_get.json")).get_offer(BOOKING_OFFER_ID)


async def test_an_expired_offer_is_unavailable_when_booking_it_and_not_a_rejected_order():
    # 422 with code `not_found` on `selected_offers`: the offer is gone, the data was fine.
    with pytest.raises(OfferUnavailableError) as error:
        await make_provider(respond(422, "duffel/error_order_offer_expired.json")).create_order(order_request())
    assert not isinstance(error.value, OfferAlreadyBookedError)


async def test_creating_an_order_waits_longer_than_other_requests_because_airlines_can_take_two_minutes():
    timeouts = {}

    def handler(request):
        timeouts[request.method + request.url.path.split("/")[2]] = request.extensions["timeout"]["read"]
        if request.method == "POST":
            return httpx2.Response(201, json=load_fixture("duffel/order_create_response.json"))
        return httpx2.Response(200, json=load_fixture("duffel/offer_get_response.json"))

    provider = make_provider(handler)
    await provider.get_offer(BOOKING_OFFER_ID)
    await provider.create_order(order_request())

    assert timeouts == {"GEToffers": 60, "POSTorders": 130}
