"""Offers as the provider sells them: amounts, conditions, payment terms and the search result."""

from datetime import datetime

from pydantic import Field

from app.core.money import Money
from app.flights.domain.dtos.base import DTO
from app.flights.domain.dtos.itinerary import Carrier, Slice


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
