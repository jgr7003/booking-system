"""Pieces of an itinerary: airlines, places, segments, slices and what each passenger gets."""

from datetime import datetime

from pydantic import Field

from app.flights.domain.dtos.base import DTO


class Carrier(DTO):
    """An airline."""

    code: str = Field(
        description="2-character IATA code, e.g. `LX`.",
    )

    name: str = Field(
        description="Commercial name, e.g. `SWISS`.",
    )

    logo_url: str | None = Field(
        default=None,
        description="URL of the airline's logo (SVG).",
    )

    conditions_of_carriage_url: str | None = Field(
        default=None,
        description="URL of the airline's conditions of carriage, when the provider reports it.",
    )


class Place(DTO):
    """An airport or city."""

    code: str = Field(
        description="3-letter IATA code.",
    )

    name: str = Field(
        description="Full name, e.g. `Heathrow Airport`.",
    )

    city: str | None = Field(
        default=None,
        description="City the airport serves.",
    )

    country_code: str | None = Field(
        default=None,
        description="ISO 3166-1 alpha-2 country code.",
    )

    time_zone: str | None = Field(
        default=None,
        description="IANA time zone, e.g. `Europe/London`. Flight times at this place are local to it.",
    )

    latitude: float | None = Field(
        default=None,
        description="Latitude in degrees, for maps.",
    )

    longitude: float | None = Field(
        default=None,
        description="Longitude in degrees, for maps.",
    )

    terminal: str | None = Field(
        default=None,
        description="Terminal; only set when the place is a segment's origin or destination.",
    )


class Baggage(DTO):
    """Bags included in the fare, per passenger.

    `0` means not included; `null` means the airline doesn't report it (never inferred).
    """

    checked: int | None = Field(
        default=None,
        description="Checked bags included; `0` = not included, `null` = not reported.",
    )

    carry_on: int | None = Field(
        default=None,
        description="Cabin bags included; `0` = not included, `null` = not reported.",
    )


class Amenities(DTO):
    """On-board amenities of a cabin. `null` means unknown."""

    wifi: str | None = Field(
        default=None,
        description="`free`, `paid`, `available` (cost unknown) or `unavailable`.",
    )

    power: bool | None = Field(
        default=None,
        description="Whether there are power outlets.",
    )

    seat_pitch: str | None = Field(
        default=None,
        description="Seat pitch in inches.",
    )

    legroom: str | None = Field(
        default=None,
        description="`less`, `standard` or `more` than usual.",
    )


class SegmentPassenger(DTO):
    """What a passenger gets on a segment."""

    passenger_id: str = Field(
        description="Id of the passenger in `SearchResult.passengers`.",
    )

    cabin_class: str | None = Field(
        default=None,
        description="Cabin class, e.g. `economy`.",
    )

    cabin_name: str | None = Field(
        default=None,
        description="The airline's marketing name for the cabin.",
    )

    baggage: Baggage = Field(
        description="Bags included.",
    )

    amenities: Amenities | None = Field(default=None, description="Cabin amenities, when the airline reports them.")


class Segment(DTO):
    """A single flight, from takeoff to landing."""

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

    passengers: list[SegmentPassenger] = Field(description="Cabin, baggage and amenities of each passenger.")


class Connection(DTO):
    """Layover between two consecutive segments."""

    airport: str = Field(
        description="IATA code of the connecting airport.",
    )

    duration_minutes: int | None = Field(
        description="Time between landing and the next takeoff; `null` if a time zone is unknown.",
    )


class FareBenefits(DTO):
    """Extras included in the fare. `null` means unknown."""

    advance_seat_selection: bool | None = Field(
        default=None, 
        description="Seats can be chosen in advance.",
    )

    priority_boarding: bool | None = Field(
        default=None, 
        description="Priority boarding.",
    )

    priority_check_in: bool | None = Field(
        default=None, 
        description="Priority check-in.",
    )


class Slice(DTO):
    """One direction of the trip: outbound or inbound."""

    origin: Place = Field(
        description="Where the slice starts.",
    )

    destination: Place = Field(
        description="Where the slice ends.",
    )

    duration_minutes: int | None = Field(
        description="Total time, from first takeoff to last landing.",
    )

    fare_brand: str | None = Field(
        default=None,
        description="The airline's fare name, e.g. `Economy Light`.",
    )

    stops: int = Field(
        description="Number of connections: 0 for direct flights.",
    )

    benefits: FareBenefits = Field(
        description="Extras included in the fare.",
    )

    segments: list[Segment] = Field(
        description="Flights in order.",
    )

    connections: list[Connection] = Field(
        description="Layovers in order; one fewer than `segments`.",
    )
