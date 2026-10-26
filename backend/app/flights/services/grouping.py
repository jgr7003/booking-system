"""Groups priced offers by flight: one card per flight, with its fares.

Pure functions, independent of the provider: the itinerary key is built from platform DTOs.
"""

import hashlib
from collections import defaultdict

from app.flights.domain.dtos import (
    Fare,
    FareSlice,
    FlightOption,
    FlightSegment,
    FlightSlice,
    Offer,
    PassengerBaggage,
    Segment,
    SegmentCabin,
    Slice,
)

# Length of the itinerary key (hex characters of a SHA-256 digest).
ITINERARY_KEY_LENGTH = 16


def itinerary_key(offer: Offer) -> str:
    """Builds the key that identifies the flight an offer sells.

    Two offers share the key when the same airline sells the same flights (marketing carrier and
    flight number) at the same local times. Fares of a flight share it, and so does the same
    flight found again in a later search, with new offer ids.

    Args:
        offer: A priced or unpriced offer.

    Returns:
        A short hexadecimal key, e.g. `3f9a1c0b7e2d4a51`.
    """
    slices = (
        ">".join(
            f"{s.marketing_carrier.code}{s.flight_number}@{s.departing_at.isoformat()}" for s in slice_.segments
        )
        for slice_ in offer.slices
    )
    raw = f"{offer.provider}|{offer.owner.code}|" + "|".join(slices)
    return hashlib.sha256(raw.encode()).hexdigest()[:ITINERARY_KEY_LENGTH]


def group_offers(offers: list[Offer]) -> list[FlightOption]:
    """Groups priced offers by flight.

    Args:
        offers: Offers with `price` and `markup` set.

    Returns:
        One `FlightOption` per flight, sorted by its cheapest fare; fares inside each flight are
        sorted by price too.

    Raises:
        ValueError: If an offer hasn't been priced.
    """
    groups: dict[str, list[Offer]] = defaultdict(list)
    for offer in offers:
        if offer.price is None or offer.markup is None:
            raise ValueError(f"Offer {offer.id} must be priced before grouping")
        groups[itinerary_key(offer)].append(offer)

    flights = [_flight_option(key, group) for key, group in groups.items()]
    return sorted(flights, key=lambda f: f.fares[0].price.total.amount)


def _flight_option(key: str, offers: list[Offer]) -> FlightOption:
    """Builds a flight from the offers that share its itinerary key."""
    offers = sorted(offers, key=lambda o: o.price.total.amount)
    reference = offers[0]
    return FlightOption(
        key=key,
        provider=reference.provider,
        owner=reference.owner,
        emissions_kg=reference.emissions_kg,
        slices=[_flight_slice(s) for s in reference.slices],
        fares=[_fare(o) for o in offers],
    )


def _flight_slice(slice_: Slice) -> FlightSlice:
    """Keeps the parts of a slice shared by every fare of the flight."""
    return FlightSlice(
        origin=slice_.origin,
        destination=slice_.destination,
        duration_minutes=slice_.duration_minutes,
        stops=slice_.stops,
        segments=[_flight_segment(s) for s in slice_.segments],
        connections=slice_.connections,
    )


def _flight_segment(segment: Segment) -> FlightSegment:
    """Keeps the parts of a segment shared by every fare; the cabin comes from the first passenger."""
    passenger = segment.passengers[0] if segment.passengers else None
    return FlightSegment(
        origin=segment.origin,
        destination=segment.destination,
        departing_at=segment.departing_at,
        arriving_at=segment.arriving_at,
        duration_minutes=segment.duration_minutes,
        marketing_carrier=segment.marketing_carrier,
        flight_number=segment.flight_number,
        operating_carrier=segment.operating_carrier,
        aircraft=segment.aircraft,
        cabin=(
            SegmentCabin(
                cabin_class=passenger.cabin_class,
                cabin_name=passenger.cabin_name,
                amenities=passenger.amenities,
            )
            if passenger
            else None
        ),
    )


def _fare(offer: Offer) -> Fare:
    """Keeps the fare-specific parts of an offer."""
    return Fare(
        offer_id=offer.id,
        cost=offer.cost,
        price=offer.price,
        markup=offer.markup,
        expires_at=offer.expires_at,
        slices=[_fare_slice(s) for s in offer.slices],
        conditions=offer.conditions,
        payment=offer.payment,
        requires_identity_documents=offer.requires_identity_documents,
        supported_identity_documents=offer.supported_identity_documents,
    )


def _fare_slice(slice_: Slice) -> FareSlice:
    """Summarizes what a fare includes on a slice."""
    return FareSlice(
        fare_brand=slice_.fare_brand,
        benefits=slice_.benefits,
        baggage=_slice_baggage(slice_),
    )


def _slice_baggage(slice_: Slice) -> list[PassengerBaggage]:
    """Bags each passenger has on the whole slice: the most restrictive allowance of its segments.

    If any segment doesn't report a bag type, the slice doesn't either (`None`).
    """
    allowances: dict[str, list] = defaultdict(list)
    for segment in slice_.segments:
        for passenger in segment.passengers:
            allowances[passenger.passenger_id].append(passenger.baggage)

    return [
        PassengerBaggage(
            passenger_id=passenger_id,
            checked=_most_restrictive([b.checked for b in bags]),
            carry_on=_most_restrictive([b.carry_on for b in bags]),
        )
        for passenger_id, bags in allowances.items()
    ]


def _most_restrictive(quantities: list[int | None]) -> int | None:
    """Lowest quantity, or `None` if any segment doesn't report it."""
    if not quantities or any(q is None for q in quantities):
        return None
    return min(quantities)
