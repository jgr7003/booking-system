"""Platform DTOs for flights.

Provider formats never leave the adapters; everything else uses these DTOs. Field descriptions
are published in the OpenAPI schema (Swagger).
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.money import Money
from app.flights.domain.constants import ADULT_AGE, MAX_CONNECTIONS, MIN_CONNECTIONS
from app.flights.domain.validators import (
    AirlineCode,
    AirportCode,
    validate_passenger_limits,
    validate_route_and_dates,
)


class DTO(BaseModel):
    """Base of every flights DTO: immutable."""

    model_config = ConfigDict(frozen=True)


# --- Search criteria (input) ---


class CabinClass(StrEnum):
    """Cabin the passengers want to travel in."""

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class PassengerCount(DTO):
    """Who travels."""

    adults: int = Field(
        default=1, 
        ge=1, 
        description="Passengers aged 18 or over."
    )

    children_ages: list[Annotated[int, Field(ge=0, lt=ADULT_AGE)]] = Field(
        default_factory=list,
        description="Age of each passenger under 18. Ages 0-1 are infants.",
    )

    @model_validator(mode="after")
    def check_limits(self) -> Self:
        """Validates the passenger limits airlines impose.

        Returns:
            The validated instance.

        Raises:
            ValueError: See `validators.validate_passenger_limits`.
        """
        validate_passenger_limits(self.adults, self.children_ages)
        return self


class SearchCriteria(DTO):
    """What the traveler is looking for. This is the body of `POST /api/v1/flights/search`."""

    origin: AirportCode = Field(
        description="IATA code of the departure airport or city, e.g. `LHR` or `LON`. Required.",
    )

    destination: AirportCode = Field(
        description="IATA code of the arrival airport or city. Required.",
    )

    departure_date: date = Field(
        description="Outbound date. Can't be in the past. Required.",
    )

    return_date: date | None = Field(
        default=None,
        description="Inbound date for round trips; `null` for one way. Required if `return_date` is provided.",
    )

    passengers: PassengerCount = Field(
        default_factory=PassengerCount,
        description="Who travels. Defaults to one adult. Required.",
    )

    cabin_class: CabinClass | None = Field(
        default=None,
        description="Preferred cabin; `null` for any. Required if `cabin_class` is provided.",
    )

    max_connections: int = Field(
        default=1,
        ge=MIN_CONNECTIONS,
        le=MAX_CONNECTIONS,
        description="Maximum connections per slice; 0 means direct flights only.",
    )

    airlines: list[AirlineCode] | None = Field(
        default=None,
        description="Only offers sold by these airlines (2-letter IATA codes); `null` for all.",
    )

    @model_validator(mode="after")
    def check_route_and_dates(self) -> Self:
        """Validates the route and the dates.

        Returns:
            The validated instance.

        Raises:
            ValueError: See `validators.validate_route_and_dates`.
        """
        validate_route_and_dates(self.origin, self.destination, self.departure_date, self.return_date)
        return self


# --- Search result (output) ---


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


class FareCondition(DTO):
    """Whether an action is allowed before departure and what it costs."""

    allowed: bool | None = Field(
        default=None,
        description="Whether it's allowed; `null` if the airline doesn't say.",
    )

    penalty: Money | None = Field(
        default=None,
        description="Fee charged by the airline. May be in a different currency than the price.",
    )


class OfferConditions(DTO):
    """Change and refund rules of an offer."""

    change: FareCondition = Field(
        description="Changing the flights before departure.",
    )

    refund: FareCondition = Field(
        description="Cancelling with a refund before departure.",
    )


class PaymentTerms(DTO):
    """When the offer has to be paid."""

    can_hold: bool = Field(
        description="Whether it can be booked now and paid later.",
    )

    payment_required_by: datetime | None = Field(
        default=None,
        description="Deadline to pay a held booking (UTC).",
    )

    price_guaranteed_until: datetime | None = Field(
        default=None,
        description="Until when the price of a held booking is guaranteed (UTC).",
    )


class OfferAmounts(DTO):
    """Breakdown of an amount."""

    total: Money = Field(
        description="Total to pay, taxes included.",
    )

    base: Money | None = Field(
        default=None,
        description="Fare without taxes.",
    )

    taxes: Money | None = Field(
        default=None,
        description="Taxes and fees.",
    )


class SearchPassenger(DTO):
    """A passenger as registered by the provider during the search."""

    id: str = Field(
        description="Provider id; required later to book.",
    )

    type: str | None = Field(
        default=None,
        description="Passenger type, e.g. `adult`. Not set when the passenger was searched by age.",
    )

    age: int | None = Field(default=None, description="Age, for passengers under 18.")


class Offer(DTO):
    """A bookable itinerary at a price.

    Internal DTO: it carries what the provider charges (`cost`) and, once priced, what the
    customer pays (`price`). Never return it from the API as is; use `api.schemas.OfferResponse`.
    """

    id: str = Field(
        description="Provider id of the offer, e.g. `off_...`.",
    )

    provider: str = Field(
        description="Provider that sells the offer, e.g. `duffel`.",
    )

    owner: Carrier = Field(
        description="Airline selling the fare.",
    )

    cost: OfferAmounts = Field(
        description="What the provider charges us.",
    )

    price: OfferAmounts | None = Field(
        default=None,
        description="What the customer pays; set by the pricing step.",
    )

    markup: Money | None = Field(
        default=None,
        description="`price.total - cost.total`; set by the pricing step.",
    )

    emissions_kg: int | None = Field(
        default=None,
        description="Estimated CO2 emissions.",
    )

    expires_at: datetime = Field(
        description="After this moment (UTC) the offer can't be booked.",
    )

    slices: list[Slice] = Field(
        description="Outbound and, for round trips, inbound.",
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


class SearchResult(DTO):
    """Outcome of a flight search."""

    provider: str = Field(
        description="Provider that answered the search.",
    )

    search_id: str = Field(
        description="Provider id of the search, e.g. `orq_...`.",
    )

    passengers: list[SearchPassenger] = Field(
        description="Passengers with the ids needed to book.",
    )

    offers: list[Offer] = Field(
        description="Offers found.",
    )


# --- Places (airport and city autocomplete) ---


class PlaceType(StrEnum):
    """Kind of place a traveler can fly from or to."""

    CITY = "city"
    AIRPORT = "airport"


class PlaceSuggestion(DTO):
    """A city or airport that matches what the traveler typed."""

    type: PlaceType = Field(
        description="`city` (all its airports) or `airport`.",
    )

    code: str = Field(
        description="IATA code to search with, e.g. `NYC` or `JFK`.",
    )

    name: str = Field(
        description="Name of the city or airport.",
    )

    city: str | None = Field(
        default=None,
        description="City the airport serves; `null` for cities and for airports without one.",
    )

    country_code: str = Field(
        description="ISO 3166-1 alpha-2 country code.",
    )

    time_zone: str | None = Field(
        default=None,
        description="IANA time zone of the airport; `null` for cities.",
    )

    airports: list[str] = Field(
        default_factory=list,
        description="IATA codes of the city's airports; empty for airports.",
    )


# --- Grouped search result: one flight, several fares ---


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
