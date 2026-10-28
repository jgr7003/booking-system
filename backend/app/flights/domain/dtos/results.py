"""Priced search result grouped by flight: one flight, several fares."""

from datetime import datetime

from pydantic import Field

from app.core.money import Money
from app.flights.domain.dtos.base import DTO
from app.flights.domain.dtos.itinerary import Carrier, Place, Baggage, Amenities, Connection, FareBenefits
from app.flights.domain.dtos.offers import OfferConditions, PaymentTerms, OfferAmounts, SearchPassenger


class SegmentCabin(DTO):
    """Cabin of a segment, shared by every fare of the same flight."""

    cabin_class: str | None = Field(
        default=None,
        description="Cabin class, e.g. `economy`.",
    )

    cabin_name: str | None = Field(
        default=None,
        description="The airline's marketing name for the cabin.",
    )

    amenities: Amenities | None = Field(
        default=None,
        description="Cabin amenities, when the airline reports them.",
    )


class FlightSegment(DTO):
    """A single flight of a grouped itinerary, without fare-specific data."""

    origin: Place = Field(
        description="Departure airport, with terminal.",
    )

    destination: Place = Field(
        description="Arrival airport, with terminal.",
    )

    departing_at: datetime = Field(
        description="Departure, local time at `origin`, without time zone.",
    )

    arriving_at: datetime = Field(
        description="Arrival, local time at `destination`, without time zone.",
    )

    duration_minutes: int | None = Field(
        description="Flight time.",
    )

    marketing_carrier: Carrier = Field(
        description="Airline that sells the flight under its code.",
    )

    flight_number: str = Field(
        description="Flight number of the marketing carrier, e.g. `0317`.",
    )

    operating_carrier: Carrier = Field(
        description="Airline that actually flies the aircraft. US regulations require showing it.",
    )

    aircraft: str | None = Field(
        default=None,
        description="Aircraft model, e.g. `Airbus A321neo`.",
    )

    cabin: SegmentCabin | None = Field(
        default=None,
        description="Cabin and amenities.",
    )


class FlightSlice(DTO):
    """One direction of a grouped itinerary, without fare-specific data."""

    origin: Place = Field(
        description="Where the slice starts.",
    )

    destination: Place = Field(
        description="Where the slice ends.",
    )

    duration_minutes: int | None = Field(
        description="Total time, from first takeoff to last landing.",
    )

    stops: int = Field(
        description="Number of connections: 0 for direct flights.",
    )

    segments: list[FlightSegment] = Field(
        description="Flights in order.",
    )

    connections: list[Connection] = Field(
        description="Layovers in order; one fewer than `segments`.",
    )


class PassengerBaggage(Baggage):
    """Bags a passenger has on a whole slice: the most restrictive allowance of its segments."""

    passenger_id: str = Field(
        description="Id of the passenger in the search's `passengers`.",
    )


class FareSlice(DTO):
    """What a fare includes on one slice."""

    fare_brand: str | None = Field(
        default=None,
        description="The airline's fare name, e.g. `Economy Light`.",
    )

    benefits: FareBenefits = Field(
        description="Extras included in the fare.",
    )

    baggage: list[PassengerBaggage] = Field(
        description="Bags included, per passenger.",
    )


class Fare(DTO):
    """One bookable fare of a flight. Internal: it carries cost and markup."""

    offer_id: str = Field(
        description="Provider id of the offer; needed to book it.",
    )

    cost: OfferAmounts = Field(
        description="What the provider charges us.",
    )

    price: OfferAmounts = Field(
        description="What the customer pays.",
    )

    markup: Money = Field(
        description="`price.total - cost.total`.",
    )

    expires_at: datetime = Field(
        description="After this moment (UTC) the fare can't be booked.",
    )

    slices: list[FareSlice] = Field(
        description="What the fare includes on each slice, in the same order as the flight's slices.",
    )

    conditions: OfferConditions = Field(
        description="Change and refund rules.",
    )

    payment: PaymentTerms = Field(
        description="Payment deadlines.",
    )

    requires_identity_documents: bool = Field(
        description="Whether passengers must provide a passport to book.",
    )

    supported_identity_documents: list[str] = Field(
        description="Identity documents the airline accepts.",
    )


class FlightOption(DTO):
    """A flight (same seller, same flights at the same times) with all its fares."""

    key: str = Field(
        description="Itinerary key: identifies the flight across fares and across searches.",
    )

    provider: str = Field(
        description="Provider that sells the flight.",
    )

    owner: Carrier = Field(
        description="Airline selling the fares.",
    )

    emissions_kg: int | None = Field(
        default=None,
        description="Estimated CO2 emissions.",
    )

    slices: list[FlightSlice] = Field(
        description="Outbound and, for round trips, inbound.",
    )

    fares: list[Fare] = Field(
        description="Fares sorted by sale price, cheapest first.",
    )


class FlightSearchResult(DTO):
    """Priced search result, with offers grouped by flight."""

    provider: str = Field(
        description="Provider that answered the search.",
    )

    search_id: str = Field(
        description="Provider id of the search, e.g. `orq_...`.",
    )

    passengers: list[SearchPassenger] = Field(
        description="Passengers with the ids needed to book.",
    )

    flights: list[FlightOption] = Field(
        description="Flights sorted by their cheapest fare.",
    )
