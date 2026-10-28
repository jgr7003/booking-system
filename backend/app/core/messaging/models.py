"""Database models of the outbox and the inbox."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# PostgreSQL schema of the messaging tables.
SCHEMA = "messaging"


class OutboxMessage(Base):
    """An event saved with the state change that caused it, waiting to be published."""

    __tablename__ = "outbox"

    # Message id; travels as the AMQP `message_id` and is the key of the consumers' inbox.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Exchange to publish to, e.g. `bookings.events`.
    exchange: Mapped[str] = mapped_column(Text)

    # Routing key, which is also the event type, e.g. `booking.confirmed`.
    routing_key: Mapped[str] = mapped_column(Text)

    # Id of the entity the event is about, e.g. the booking id.
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    # Body of the message. Never personal data: only ids, states and versions.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)

    # When the event was saved.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # When RabbitMQ confirmed it; `None` while pending.
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # Only pending rows are looked up, so the index stays small.
        Index(
            "ix_outbox_pending",
            "created_at",
            postgresql_where=text("published_at IS NULL"),
        ),
        {"schema": SCHEMA},
    )


class InboxMessage(Base):
    """A message a consumer already processed; a redelivery of it is acknowledged and skipped."""

    __tablename__ = "inbox"

    # Id of the message (`outbox.id` of the producer).
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    # Consumer that processed it, e.g. `flights.booking-worker`; each consumer has its own record.
    consumer: Mapped[str] = mapped_column(Text, primary_key=True)

    # When it was processed.
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = ({"schema": SCHEMA},)
