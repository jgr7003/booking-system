"""Public schemas of the flight search."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.money import Money
from app.flights.domain.dtos.itinerary import Carrier
from app.flights.domain.dtos.offers import OfferAmounts, OfferConditions, PaymentTerms, SearchPassenger
from app.flights.domain.dtos.results import FareSlice, FlightSlice


class FareResponse(BaseModel):
    """A bookable fare of a flight, at its sale price."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    offer_id: str = Field(
        description="Provider id of the offer; needed to book it.",
    )

    price: OfferAmounts = Field(
        description="What the customer pays, taxes included.",
    )

    expires_at: datetime = Field(
        description="After this moment (UTC) the fare can't be booked; search again.",
    )

    slices: list[FareSlice] = Field(
        description="Fare name, extras and bags on each slice, in the same order as the flight's slices.",
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


class FlightResponse(BaseModel):
    """A flight with all its fares."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(
        description="Itinerary key. Identifies the flight across fares and searches; use it to avoid duplicates in a trip.",
    )

    provider: str = Field(
        description="Provider that sells the flight.",
    )

    owner: Carrier = Field(
        description="Airline selling the fares.",
    )

    emissions_kg: int | None = Field(
        description="Estimated CO2 emissions.",
    )

    lowest_price: Money = Field(
        description="Total of the cheapest fare.",
    )

    slices: list[FlightSlice] = Field(
        description="Outbound and, for round trips, inbound.",
    )

    fares: list[FareResponse] = Field(
        description="Fares sorted by sale price, cheapest first.",
    )


class SearchResponse(BaseModel):
    """Answer of `POST /api/v1/flights/search`."""

    model_config = ConfigDict(frozen=True)

    provider: str = Field(
        description="Provider that answered the search.",
    )

    search_id: str = Field(
        description="Provider id of the search.",
    )

    passengers: list[SearchPassenger] = Field(
        description="Passengers with the ids needed to book.",
    )

    expires_at: datetime | None = Field(
        description="When the first fare of the search expires (UTC); `null` if there are no flights.",
    )

    flights: list[FlightResponse] = Field(
        description="Flights sorted by their cheapest fare.",
    )
