"""Database model of the single-use links sent by email."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.identity.domain.models.schema import SCHEMA


class EmailToken(Base):
    """A link sent by email: verify the email, set the first password or reset it.

    Only the SHA-256 of the token is stored; the token itself travels only in the email.
    """

    __tablename__ = "email_tokens"

    # SHA-256 of the token, hex.
    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)

    # User the link is for.
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), index=True)

    # What the link does (`EmailTokenPurpose`).
    purpose: Mapped[str] = mapped_column(Text)

    # When it was sent.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # The link stops working at this time.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # When it was used; a link works once.
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = ({"schema": SCHEMA},)
