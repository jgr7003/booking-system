from decimal import Decimal

import pytest

from app.core.pricing.fixed_fee_random_percent import FixedFeeRandomPercentPolicy
from app.flights.services.flight_search import FlightSearchService
from app.flights.services.grouping import group_offers, itinerary_key
from app.flights.tests.support import FakeFlightProvider, make_criteria

pytestmark = pytest.mark.anyio

ONE_STOP_LH = "off_034l6ScLRLhYObdEbC8k1g"  # Economy Light of LX 317 + LX 14


@pytest.fixture
async def flights(search_result):
    service = FlightSearchService(FakeFlightProvider(search_result), FixedFeeRandomPercentPolicy("test-secret"))
    return (await service.search(make_criteria())).flights


def flight_with(flights, offer_id):
    return next(f for f in flights if any(fare.offer_id == offer_id for fare in f.fares))


async def test_56_offers_become_16_flights(flights):
    assert len(flights) == 16
    assert sum(len(f.fares) for f in flights) == 56


async def test_matches_duffel_comparison_key(search_result, duffel_search_response):
    """Our provider-agnostic key groups exactly like Duffel's own comparison_key."""
    raw = {o["id"]: o for o in duffel_search_response["data"]["offers"]}
    ours: dict[str, set[str]] = {}
    for offer in search_result.offers:
        duffel_key = "|".join(s["comparison_key"] for s in raw[offer.id]["slices"])
        ours.setdefault(itinerary_key(offer), set()).add(duffel_key)

    assert all(len(duffel_keys) == 1 for duffel_keys in ours.values())
    assert len(ours) == len({k for keys in ours.values() for k in keys})


async def test_flight_has_its_five_fares_sorted_by_price(flights):
    flight = flight_with(flights, ONE_STOP_LH)

    names = [fare.slices[0].fare_brand for fare in flight.fares]
    totals = [fare.price.total.amount for fare in flight.fares]
    assert len(flight.fares) == 5
    assert set(names) == {"Economy Light", "Economy Comfort", "Economy Comfort Plus", "Economy Impact", "Economy Flex"}
    assert totals == sorted(totals)


async def test_flights_are_sorted_by_cheapest_fare(flights):
    cheapest = [f.fares[0].price.total.amount for f in flights]

    assert cheapest == sorted(cheapest)


async def test_shared_flight_data(flights):
    flight = flight_with(flights, ONE_STOP_LH)
    first, second = flight.slices[0].segments

    assert flight.owner.code == "LH"
    assert flight.emissions_kg == 379
    assert (first.flight_number, second.flight_number) == ("0317", "0014")
    assert first.operating_carrier.name == "SWISS"
    assert first.cabin.amenities.seat_pitch == "29"
    assert [(c.airport, c.duration_minutes) for c in flight.slices[0].connections] == [("ZRH", 75)]


async def test_fare_specific_baggage(flights):
    flight = flight_with(flights, ONE_STOP_LH)
    by_name = {fare.slices[0].fare_brand: fare.slices[0].baggage[0] for fare in flight.fares}

    assert (by_name["Economy Light"].checked, by_name["Economy Light"].carry_on) == (0, 1)
    assert (by_name["Economy Flex"].checked, by_name["Economy Flex"].carry_on) == (1, 1)
    # Lufthansa doesn't report the cabin bag of Economy Impact: unknown, not "not included".
    assert (by_name["Economy Impact"].checked, by_name["Economy Impact"].carry_on) == (1, None)


async def test_one_seller_per_flight(flights):
    """BA, IB and AA fly the same direct service, but each seller is its own flight."""
    direct_owners = [f.owner.code for f in flights if f.slices[0].stops == 0]

    assert sorted(direct_owners) == ["AA", "BA", "IB", "ZZ"]


def test_key_is_stable_across_searches(search_result):
    """The same flight found again (new offer id) gets the same key."""
    offer = next(o for o in search_result.offers if o.id == ONE_STOP_LH)
    renewed = offer.model_copy(update={"id": "off_renewed"})

    assert itinerary_key(renewed) == itinerary_key(offer)


def test_unpriced_offers_cannot_be_grouped(search_result):
    with pytest.raises(ValueError, match="must be priced"):
        group_offers(search_result.offers)


async def test_slice_baggage_is_the_most_restrictive_of_its_segments(search_result):
    offer = next(o for o in search_result.offers if o.id == ONE_STOP_LH)
    first, second = offer.slices[0].segments
    restricted = second.passengers[0].model_copy(
        update={"baggage": second.passengers[0].baggage.model_copy(update={"carry_on": None})}
    )
    offer = offer.model_copy(
        update={
            "slices": [offer.slices[0].model_copy(update={"segments": [first, second.model_copy(update={"passengers": [restricted]})]})],
            "price": offer.cost,
            "markup": offer.cost.total.model_copy(update={"amount": Decimal("0")}),
        }
    )

    (flight,) = group_offers([offer])

    assert flight.fares[0].slices[0].baggage[0].carry_on is None
