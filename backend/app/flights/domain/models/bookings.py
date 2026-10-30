"""Database model of the bookings."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.flights.domain.models.schema import SCHEMA


class Booking(Base):
    """A booking of one offer for one traveler, processed in the background.

    Cost and markup are never stored: they are recalculated with the pricing policy and never
    leave the backend.
    """

    __tablename__ = "bookings"

    # Public id of the booking.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # `Idempotency-Key` of the request that created it; the same key returns the same booking.
    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True)

    # SHA-256 of the canonical body of that request, to detect a key reused with another body.
    request_hash: Mapped[str] = mapped_column(String(64))

    # See `dtos.BookingStatus`.
    status: Mapped[str] = mapped_column(Text)

    # Grows with every change of status; it is the `id` of the SSE events.
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Provider of the offer, e.g. `duffel`.
    provider: Mapped[str] = mapped_column(Text)

    # Provider id of the offer.
    offer_id: Mapped[str] = mapped_column(Text)

    # User who made the booking (identity module, by id without a foreign key). Never null: there are
    # no bookings without an owner.
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    # Organization of that user (by id without a foreign key); `None` for a private traveller. Every
    # read made for a user filters by it (`BookingOwner`).
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Traveller in the travellers module (by id, without a foreign key between modules).
    traveller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    # Fixed copy of the passenger as sent to the airline (`dtos.AirlinePassenger`).
    passenger: Mapped[dict[str, Any]] = mapped_column(JSONB)

    # Sale price the traveler saw when confirming.
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    # Currency of `expected_amount`.
    expected_currency: Mapped[str] = mapped_column(String(3))

    # New sale price found when refreshing the offer, while waiting for the traveler's decision.
    offered_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    # Currency of `offered_amount`.
    offered_currency: Mapped[str | None] = mapped_column(String(3))

    # Sale price the traveler approved after a change.
    approved_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    # Currency of `approved_amount`.
    approved_currency: Mapped[str | None] = mapped_column(String(3))

    # Token of the card (from the gateway's tokenization; never the card number).
    payment_token: Mapped[str] = mapped_column(Text)

    # Authorization at the payment gateway, once the charge was authorized.
    payment_authorization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Provider id of the order, once booked.
    provider_order_id: Mapped[str | None] = mapped_column(Text)

    # Booking reference (PNR), once booked.
    booking_reference: Mapped[str | None] = mapped_column(Text)

    # The confirmed order (`dtos.Order`), for the confirmation screen.
    order: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Why it failed (`dtos.FailureCode`).
    failure_code: Mapped[str | None] = mapped_column(Text)

    # Until when the worker processing it owns it.
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # When it was created.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # When it last changed.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_bookings_owner", "organization_id", "user_id"),
        {"schema": SCHEMA},
    )

    # Fetch the timestamps the database generates in the same INSERT/UPDATE (RETURNING), so they
    # never have to be loaded lazily, which async sessions can't do.
    __mapper_args__ = {"eager_defaults": True}
