"""Pure translations between platform DTOs and Duffel's JSON format.

No I/O happens here, so every function can be tested with captured Duffel responses.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.money import Money
from app.flights.domain.dtos import (
    Amenities,
    Baggage,
    Carrier,
    Connection,
    FareBenefits,
    FareCondition,
    Offer,
    OfferAmounts,
    OfferConditions,
    PaymentTerms,
    Place,
    SearchCriteria,
    SearchPassenger,
    SearchResult,
    Segment,
    SegmentPassenger,
    Slice,
)

PROVIDER = "duffel"

Json = dict[str, Any]

_ISO_DURATION = re.compile(r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:\d+S)?)?$")


# --- Platform → Duffel ---


def to_offer_request(criteria: SearchCriteria) -> Json:
    """Builds the body of `POST /air/offer_requests` from the platform's criteria.

    A round trip becomes two slices; adults are sent by type and minors by age, as Duffel
    recommends. `criteria.airlines` isn't sent because Duffel has no such filter.

    Args:
        criteria: What the traveler is looking for.

    Returns:
        The offer request in Duffel's format, without the `data` envelope.
    """
    slices = [_slice_request(criteria.origin, criteria.destination, criteria.departure_date)]
    if criteria.return_date is not None:
        slices.append(_slice_request(criteria.destination, criteria.origin, criteria.return_date))

    passengers: list[Json] = [{"type": "adult"} for _ in range(criteria.passengers.adults)]
    passengers += [{"age": age} for age in criteria.passengers.children_ages]

    payload: Json = {"slices": slices, "passengers": passengers, "max_connections": criteria.max_connections}
    if criteria.cabin_class is not None:
        payload["cabin_class"] = criteria.cabin_class.value
    return payload


def _slice_request(origin: str, destination: str, departure_date: date) -> Json:
    """Builds one slice of an offer request."""
    return {"origin": origin, "destination": destination, "departure_date": departure_date.isoformat()}


# --- Duffel → platform ---


def to_search_result(data: Json) -> SearchResult:
    """Converts Duffel's offer request into the platform's search result.

    Args:
        data: The `data` object of Duffel's offer request response.

    Returns:
        The search result, with each offer's cost and no sale price.
    """
    return SearchResult(
        provider=PROVIDER,
        search_id=data["id"],
        passengers=[SearchPassenger(id=p["id"], type=p.get("type"), age=p.get("age")) for p in data["passengers"]],
        offers=[to_offer(offer) for offer in data.get("offers") or []],
    )


def to_offer(offer: Json) -> Offer:
    """Converts one Duffel offer into the platform's offer.

    Args:
        offer: An element of Duffel's `offers` list.

    Returns:
        The offer, with Duffel's price as `cost` and `price`/`markup` unset.
    """
    payment = offer.get("payment_requirements") or {}
    conditions = offer.get("conditions") or {}
    emissions = offer.get("total_emissions_kg")
    return Offer(
        id=offer["id"],
        provider=PROVIDER,
        owner=_carrier(offer["owner"]),
        cost=OfferAmounts(
            total=Money(amount=offer["total_amount"], currency=offer["total_currency"]),
            base=_money(offer.get("base_amount"), offer.get("base_currency")),
            taxes=_money(offer.get("tax_amount"), offer.get("tax_currency")),
        ),
        emissions_kg=round(Decimal(emissions)) if emissions else None,
        expires_at=offer["expires_at"],
        slices=[_slice(s) for s in offer["slices"]],
        conditions=OfferConditions(
            change=_fare_condition(conditions.get("change_before_departure")),
            refund=_fare_condition(conditions.get("refund_before_departure")),
        ),
        payment=PaymentTerms(
            can_hold=not payment.get("requires_instant_payment", True),
            payment_required_by=payment.get("payment_required_by"),
            price_guaranteed_until=payment.get("price_guarantee_expires_at"),
        ),
        requires_identity_documents=offer.get("passenger_identity_documents_required", False),
        supported_identity_documents=offer.get("supported_passenger_identity_document_types") or [],
    )


def _slice(data: Json) -> Slice:
    """Converts a Duffel slice, calculating its stops and connections."""
    segments = [_segment(s) for s in data["segments"]]
    conditions = data.get("conditions") or {}
    return Slice(
        origin=_place(data["origin"]),
        destination=_place(data["destination"]),
        duration_minutes=parse_duration(data.get("duration")),
        fare_brand=data.get("fare_brand_name"),
        stops=len(segments) - 1,
        benefits=FareBenefits(
            advance_seat_selection=conditions.get("advance_seat_selection"),
            priority_boarding=conditions.get("priority_boarding"),
            priority_check_in=conditions.get("priority_check_in"),
        ),
        segments=segments,
        connections=[_connection(arriving, departing) for arriving, departing in zip(segments, segments[1:])],
    )


def _segment(data: Json) -> Segment:
    """Converts a Duffel segment."""
    aircraft = data.get("aircraft") or {}
    return Segment(
        origin=_place(data["origin"], terminal=data.get("origin_terminal")),
        destination=_place(data["destination"], terminal=data.get("destination_terminal")),
        departing_at=data["departing_at"],
        arriving_at=data["arriving_at"],
        duration_minutes=parse_duration(data.get("duration")),
        marketing_carrier=_carrier(data["marketing_carrier"]),
        flight_number=data["marketing_carrier_flight_number"],
        operating_carrier=_carrier(data["operating_carrier"]),
        aircraft=aircraft.get("name"),
        passengers=[_segment_passenger(p) for p in data.get("passengers") or []],
    )


def _segment_passenger(data: Json) -> SegmentPassenger:
    """Converts a passenger's cabin, baggage and amenities on a segment."""
    baggage = {b["type"]: b["quantity"] for b in data.get("baggages") or []}
    cabin = data.get("cabin") or {}
    return SegmentPassenger(
        passenger_id=data["passenger_id"],
        cabin_class=data.get("cabin_class"),
        cabin_name=data.get("cabin_class_marketing_name"),
        # Duffel omits a baggage type when the airline doesn't report it: that stays `None`, never 0.
        baggage=Baggage(checked=baggage.get("checked"), carry_on=baggage.get("carry_on")),
        amenities=_amenities(cabin.get("amenities")),
    )


def _amenities(data: Json | None) -> Amenities | None:
    """Converts cabin amenities, or returns `None` if Duffel doesn't report them."""
    if not data:
        return None
    wifi = data.get("wifi") or {}
    seat = data.get("seat") or {}
    power = data.get("power") or {}
    return Amenities(
        wifi=_wifi(wifi),
        power=power.get("available"),
        seat_pitch=_known(seat.get("pitch")),
        legroom=_known(seat.get("legroom")),
    )


def _wifi(wifi: Json) -> str | None:
    """Summarizes Duffel's wifi object as `free`, `paid`, `available`, `unavailable` or `None`."""
    if "available" not in wifi:
        return None
    if not wifi["available"]:
        return "unavailable"
    return wifi.get("cost") if wifi.get("cost") in ("free", "paid") else "available"


def _known(value: str | None) -> str | None:
    """Returns `None` for the values Duffel uses to mean unknown (`"n/a"`, empty)."""
    return None if value in (None, "", "n/a") else value


def _connection(arriving: Segment, departing: Segment) -> Connection:
    """Calculates the layover between two consecutive segments.

    Local times become comparable once each gets its airport's time zone.

    Args:
        arriving: Segment that lands at the connecting airport.
        departing: Next segment, which takes off from it.

    Returns:
        The connection; its duration is `None` if a time zone is unknown.
    """
    arrival = _localize(arriving.arriving_at, arriving.destination.time_zone)
    departure = _localize(departing.departing_at, departing.origin.time_zone)
    minutes = int((departure - arrival).total_seconds() // 60) if arrival and departure else None
    return Connection(airport=arriving.destination.code, duration_minutes=minutes)


def _localize(local: datetime, time_zone: str | None) -> datetime | None:
    """Attaches an IANA time zone to a naive local time, or returns `None` if it's unknown."""
    if not time_zone:
        return None
    try:
        return local.replace(tzinfo=ZoneInfo(time_zone))
    except ZoneInfoNotFoundError:
        return None


def _place(data: Json, terminal: str | None = None) -> Place:
    """Converts a Duffel airport or city, keeping its coordinates."""
    return Place(
        code=data["iata_code"],
        name=data["name"],
        city=data.get("city_name"),
        country_code=data.get("iata_country_code"),
        time_zone=data.get("time_zone"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        terminal=terminal,
    )


def _carrier(data: Json) -> Carrier:
    """Converts a Duffel airline."""
    return Carrier(
        code=data["iata_code"],
        name=data["name"],
        logo_url=data.get("logo_symbol_url"),
        conditions_of_carriage_url=data.get("conditions_of_carriage_url"),
    )


def _fare_condition(data: Json | None) -> FareCondition:
    """Converts a change or refund condition; unknown when Duffel sends `null`."""
    if not data:
        return FareCondition()
    return FareCondition(
        allowed=data.get("allowed"),
        penalty=_money(data.get("penalty_amount"), data.get("penalty_currency")),
    )


def _money(amount: str | None, currency: str | None) -> Money | None:
    """Builds `Money`, or returns `None` if the amount or the currency is missing."""
    if amount is None or currency is None:
        return None
    return Money(amount=amount, currency=currency)


def parse_duration(value: str | None) -> int | None:
    """Converts an ISO 8601 duration into minutes.

    Args:
        value: Duration as Duffel sends it, e.g. `"PT12H40M"` or `"P1DT2H"`.

    Returns:
        The duration in minutes (seconds are dropped), or `None` if `value` is missing or isn't
        an ISO 8601 duration.
    """
    match = _ISO_DURATION.match(value or "")
    if not value or not match:
        return None
    parts = {k: int(v) for k, v in match.groupdict(default="0").items()}
    return parts["days"] * 24 * 60 + parts["hours"] * 60 + parts["minutes"]
