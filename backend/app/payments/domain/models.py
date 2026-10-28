"""Database models of the payments module."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# PostgreSQL schema that holds every table of the module.
SCHEMA = "payments"


class PaymentAuthorization(Base):
    """A charge of the simulated gateway. A real gateway keeps these on its side."""

    __tablename__ = "payment_authorizations"

    # Id of the authorization.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Key given by the caller; the same key always returns the same authorization.
    idempotency_key: Mapped[str] = mapped_column(Text, unique=True)

    # Authorized amount.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    # ISO 4217 currency code.
    currency: Mapped[str] = mapped_column(String(3))

    # Last 4 digits of the card, the only card data kept.
    card_last4: Mapped[str] = mapped_column(String(4))

    # `authorized`, `captured`, `voided` or `declined`.
    status: Mapped[str] = mapped_column(Text)

    # When the authorization was created.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # When its status last changed.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = ({"schema": SCHEMA},)
