"""Public HTTP schemas. They expose the sale price only: cost and markup have no field here."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from app.core.money import Money
from app.flights.domain.dtos import (
    Carrier,
    FareSlice,
    FlightOption,
    FlightSearchResult,
    FlightSlice,
    OfferAmounts,
    OfferConditions,
    PaymentTerms,
    SearchPassenger,
)


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

    @classmethod
    def from_domain(cls, flight: FlightOption) -> Self:
        """Builds the public flight; fares are validated from dicts so cost and markup are dropped.

        Args:
            flight: Flight with priced fares.

        Returns:
            The flight to send to clients.
        """
        return cls(
            key=flight.key,
            provider=flight.provider,
            owner=flight.owner,
            emissions_kg=flight.emissions_kg,
            lowest_price=flight.fares[0].price.total,
            slices=flight.slices,
            fares=[FareResponse.model_validate(fare.model_dump()) for fare in flight.fares],
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

    @classmethod
    def from_domain(cls, result: FlightSearchResult) -> Self:
        """Builds the public response from a priced, grouped search result.

        Args:
            result: Result of `FlightSearchService.search`.

        Returns:
            The response to send to clients.
        """
        fares = [fare for flight in result.flights for fare in flight.fares]
        return cls(
            provider=result.provider,
            search_id=result.search_id,
            passengers=result.passengers,
            expires_at=min((f.expires_at for f in fares), default=None),
            flights=[FlightResponse.from_domain(f) for f in result.flights],
        )
