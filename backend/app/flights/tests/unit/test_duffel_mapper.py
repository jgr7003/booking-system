import copy
from datetime import date
from decimal import Decimal

import pytest

from app.core.money import Money
from app.flights.domain.dtos.search import CabinClass, PassengerCount
from app.flights.providers.duffel import mapper
from app.flights.tests.support import make_criteria

DIRECT_BA = "off_034l6SavDjxAdhKZnJMTYm"  # LHR → JFK direct, no changes or refunds
ONE_STOP_LH = "off_034l6ScLRLhYObdEbC8k1g"  # sold by Lufthansa, flown by SWISS via ZRH
TWO_STOPS_LH = "off_034l6ScLRLhYObdEbC8k2U"  # three different operating carriers


def offer_by_id(result, offer_id):
    return next(o for o in result.offers if o.id == offer_id)


# --- Platform → Duffel ---


def test_one_way_search_becomes_a_single_slice():
    criteria = make_criteria(departure_date=date(2099, 12, 15))

    assert mapper.to_offer_request(criteria) == {
        "slices": [{"origin": "LHR", "destination": "JFK", "departure_date": "2099-12-15"}],
        "passengers": [{"type": "adult"}],
        "max_connections": 1,
    }


def test_round_trip_with_children_and_cabin():
    criteria = make_criteria(
        departure_date=date(2099, 12, 15),
        return_date=date(2099, 12, 22),
        passengers=PassengerCount(adults=2, children_ages=[10, 1]),
        cabin_class=CabinClass.BUSINESS,
        max_connections=0,
    )

    payload = mapper.to_offer_request(criteria)

    assert payload["slices"] == [
        {"origin": "LHR", "destination": "JFK", "departure_date": "2099-12-15"},
        {"origin": "JFK", "destination": "LHR", "departure_date": "2099-12-22"},
    ]
    assert payload["passengers"] == [{"type": "adult"}, {"type": "adult"}, {"age": 10}, {"age": 1}]
    assert payload["cabin_class"] == "business"
    assert payload["max_connections"] == 0


def test_airlines_are_not_sent_to_duffel():
    """Duffel has no airline filter; the adapter filters the answer instead."""
    assert "airlines" not in mapper.to_offer_request(make_criteria(airlines=["BA"]))


# --- Duffel → platform ---


def test_maps_search_and_passengers(search_result):
    assert search_result.provider == "duffel"
    assert search_result.search_id == "orq_0000BBiPI0fBoJ3vgP3eAA"
    assert [(p.id, p.type) for p in search_result.passengers] == [("pas_0000BBiPI0fXmzLVhVDviC", "adult")]
    assert len(search_result.offers) == 56


def test_offers_carry_cost_but_no_sale_price(search_result):
    offer = offer_by_id(search_result, DIRECT_BA)

    assert offer.cost.total == Money(amount=Decimal("214.34"), currency="USD")
    assert offer.price is None
    assert offer.markup is None


def test_direct_flight(search_result):
    offer = offer_by_id(search_result, DIRECT_BA)
    slice_ = offer.slices[0]

    assert offer.owner.code == "BA"
    assert slice_.stops == 0
    assert slice_.connections == []
    assert slice_.duration_minutes == 7 * 60 + 58
    assert slice_.segments[0].marketing_carrier.code == "BA"
    assert slice_.segments[0].flight_number == "0109"
    assert offer.conditions.change.allowed is False
    assert offer.conditions.refund.allowed is False


def test_connection_operated_by_another_airline(search_result):
    offer = offer_by_id(search_result, ONE_STOP_LH)
    slice_ = offer.slices[0]
    first, second = slice_.segments

    assert offer.owner.name == "Lufthansa"
    assert {s.operating_carrier.name for s in slice_.segments} == {"SWISS"}
    assert slice_.stops == 1
    assert slice_.duration_minutes == 12 * 60 + 40
    assert slice_.fare_brand == "Economy Light"
    # Arrives ZRH 11:55 and leaves 13:10, both Zurich local time.
    assert [(c.airport, c.duration_minutes) for c in slice_.connections] == [("ZRH", 75)]
    assert first.origin.terminal == "2"
    assert first.destination.terminal is None
    assert first.aircraft == "Airbus A321neo"
    assert first.flight_number == "0317"


def test_price_breakdown_and_conditions_in_other_currency(search_result):
    offer = offer_by_id(search_result, ONE_STOP_LH)

    assert offer.cost.base == Money(amount=Decimal("24.07"), currency="USD")
    assert offer.cost.taxes == Money(amount=Decimal("378.67"), currency="USD")
    # The airline reports the change penalty in GBP while the price is in USD.
    assert offer.conditions.change.allowed is True
    assert offer.conditions.change.penalty == Money(amount=Decimal("300"), currency="GBP")
    assert offer.conditions.refund.allowed is False
    assert offer.conditions.refund.penalty is None
    assert offer.payment.can_hold is True


def test_baggage_and_amenities_per_segment(search_result):
    first, second = offer_by_id(search_result, ONE_STOP_LH).slices[0].segments

    passenger = first.passengers[0]
    assert passenger.passenger_id == "pas_0000BBiPI0fXmzLVhVDviC"
    assert (passenger.baggage.checked, passenger.baggage.carry_on) == (0, 1)
    assert passenger.amenities.wifi == "unavailable"
    assert passenger.amenities.seat_pitch == "29"
    assert passenger.amenities.legroom == "less"
    assert second.passengers[0].amenities.wifi == "paid"


def test_unreported_baggage_is_none_not_zero(search_result):
    """Duffel omits a baggage type the airline doesn't report: Economy Impact has no carry_on item."""
    impact = [o for o in search_result.offers if o.slices[0].fare_brand == "Economy Impact"]

    assert len(impact) == 10
    for offer in impact:
        baggage = offer.slices[0].segments[0].passengers[0].baggage
        assert (baggage.checked, baggage.carry_on) == (1, None)


def test_owner_keeps_conditions_of_carriage(search_result):
    owner = offer_by_id(search_result, ONE_STOP_LH).owner

    assert owner.conditions_of_carriage_url.startswith("https://www.lufthansa.com/")


def test_two_stops_with_three_operating_carriers(search_result):
    slice_ = offer_by_id(search_result, TWO_STOPS_LH).slices[0]

    assert slice_.stops == 2
    assert [s.operating_carrier.code for s in slice_.segments] == ["VL", "LH", "LX"]
    assert [c.airport for c in slice_.connections] == ["MUC", "ZRH"]


def test_places_keep_coordinates(search_result):
    origin = offer_by_id(search_result, DIRECT_BA).slices[0].origin

    assert (origin.code, origin.city, origin.country_code) == ("LHR", "London", "GB")
    assert origin.time_zone == "Europe/London"
    assert (origin.latitude, origin.longitude) == (51.470311, -0.458118)


def test_every_connection_has_a_positive_layover(search_result):
    for offer in search_result.offers:
        for slice_ in offer.slices:
            assert len(slice_.connections) == slice_.stops
            assert all(c.duration_minutes > 0 for c in slice_.connections)


def test_missing_optional_data_becomes_none(duffel_search_response):
    raw = copy.deepcopy(next(o for o in duffel_search_response["data"]["offers"] if o["id"] == ONE_STOP_LH))
    raw["conditions"] = {"change_before_departure": None, "refund_before_departure": None}
    raw["total_emissions_kg"] = None
    segment = raw["slices"][0]["segments"][0]
    segment["aircraft"] = None
    segment["passengers"][0]["cabin"] = None
    segment["destination"]["time_zone"] = None

    offer = mapper.to_offer(raw)

    assert offer.conditions.change.allowed is None
    assert offer.emissions_kg is None
    assert offer.slices[0].segments[0].aircraft is None
    assert offer.slices[0].segments[0].passengers[0].amenities is None
    assert offer.slices[0].connections[0].duration_minutes is None


@pytest.mark.parametrize(
    ("value", "minutes"),
    [("PT7H58M", 478), ("PT12H40M", 760), ("PT45M", 45), ("P1DT2H", 1560), ("PT2H", 120), (None, None), ("7h", None)],
)
def test_parse_duration(value, minutes):
    assert mapper.parse_duration(value) == minutes
