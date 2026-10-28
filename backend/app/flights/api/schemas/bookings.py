"""Public schemas of the bookings: no cost, markup, contact data or payment token."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.money import Money
from app.flights.domain.dtos.bookings import BookingStatus, FailureCode, PassengerTitle
from app.flights.domain.dtos.itinerary import Carrier, Slice
from app.flights.domain.dtos.offers import OfferConditions
from app.flights.domain.dtos.orders import Ticket


class BookingPassengerResponse(BaseModel):
    """The passenger of a booking, as printed on the ticket.

    Contact data and documents aren't returned: anyone with the booking id can read it.
    """

    model_config = ConfigDict(frozen=True)

    title: PassengerTitle = Field(
        description="Title printed on the ticket.",
    )

    given_name: str = Field(
        description="Given name, as sent to the airline (e.g. `JOSE`).",
    )

    family_name: str = Field(
        description="Family name, as sent to the airline (e.g. `MUNOZ`).",
    )


class OrderResponse(BaseModel):
    """The order confirmed by the airline. Its cost to the platform isn't included."""

    model_config = ConfigDict(frozen=True)

    owner: Carrier = Field(
        description="Airline that sold the order.",
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
        description="When the order was paid (UTC).",
    )

    awaiting_payment: bool = Field(
        description="Whether the order still has to be paid.",
    )

    available_actions: list[str] = Field(
        description="What can be done with the order (`cancel`, `change`, `update`). Show only these.",
    )


class BookingResponse(BaseModel):
    """A booking and its current state."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(
        description="Id of the booking.",
    )

    status: BookingStatus = Field(
        description="`pending` → `processing` → `confirmed`, or `awaiting_price_approval`, `failed`, `cancelled`. "
        "`issuance_error` means the airline may have issued the booking but it couldn't be confirmed or charged: "
        "it is being reviewed, and it must not be booked again.",
    )

    version: int = Field(
        description="Grows with every change of state; it's the `id` of the SSE events.",
    )

    offer_id: str = Field(
        description="Provider id of the booked fare.",
    )

    price: Money = Field(
        description="Sale price the booking charges: the one confirmed or, after a change, the one approved.",
    )

    offered_price: Money | None = Field(
        description="New price found when reconfirming the fare; set while `awaiting_price_approval`.",
    )

    failure_code: FailureCode | None = Field(
        description="Why it failed, when `failed` or `issuance_error`.",
    )

    booking_reference: str | None = Field(
        description="Booking reference (PNR) of the airline, when `confirmed`.",
    )

    passenger: BookingPassengerResponse = Field(
        description="The passenger.",
    )

    order: OrderResponse | None = Field(
        description="The confirmed order, when `confirmed`.",
    )

    created_at: datetime = Field(
        description="When the booking was created (UTC).",
    )

    updated_at: datetime = Field(
        description="When it last changed (UTC).",
    )
