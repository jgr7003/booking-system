"""Orders with the provider: the offer ready to book, the request and the confirmed order."""

import uuid
from datetime import datetime

from pydantic import Field

from app.core.money import Money
from app.flights.domain.dtos.base import DTO
from app.flights.domain.dtos.bookings import AirlinePassenger
from app.flights.domain.dtos.itinerary import Carrier, Slice
from app.flights.domain.dtos.offers import OfferConditions, Offer


class BookableOffer(DTO):
    """An offer refreshed from the provider just before booking it."""

    offer: Offer = Field(
        description="The offer with its current cost.",
    )

    passenger_ids: list[str] = Field(
        description="Provider ids of the passengers of the offer, needed to book it.",
    )


class OrderRequest(DTO):
    """What the provider needs to book an offer."""

    offer_id: str = Field(
        description="Provider id of the offer.",
    )

    passenger_id: str = Field(
        description="Provider id of the passenger, from the refreshed offer.",
    )

    passenger: AirlinePassenger = Field(
        description="The passenger.",
    )

    payment: Money = Field(
        description="What the provider charges (`cost.total`), paid from the platform's balance.",
    )

    booking_id: uuid.UUID = Field(
        description="Id of the platform's booking, saved in the order to reconcile it later.",
    )


class Ticket(DTO):
    """An electronic ticket of the order."""

    passenger_id: str = Field(
        description="Provider id of the passenger.",
    )

    number: str = Field(
        description="Ticket number.",
    )


class Order(DTO):
    """A booking confirmed by the provider."""

    id: str = Field(
        description="Provider id of the order, e.g. `ord_...`.",
    )

    offer_id: str = Field(
        description="Offer that was booked.",
    )

    booking_reference: str = Field(
        description="Booking reference (PNR) given by the airline, e.g. `RZPNX8`.",
    )

    booking_id: uuid.UUID | None = Field(
        default=None,
        description="Id of the platform's booking saved in the order, if any.",
    )

    owner: Carrier = Field(
        description="Airline that sold the order.",
    )

    total: Money = Field(
        description="What the provider charged.",
    )

    slices: list[Slice] = Field(
        description="Itinerary, with the operating carrier of each segment.",
    )

    conditions: OfferConditions = Field(
        description="Change and refund rules.",
    )

    tickets: list[Ticket] = Field(
        description="Electronic tickets; empty until they are issued.",
    )

    paid_at: datetime | None = Field(
        default=None,
        description="When the order was paid (UTC).",
    )

    awaiting_payment: bool = Field(
        description="Whether the order still has to be paid.",
    )

    available_actions: list[str] = Field(
        description="What can be done with the order, e.g. `cancel`, `change`, `update`.",
    )
