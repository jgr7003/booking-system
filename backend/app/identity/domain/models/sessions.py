"""Database models of device sessions and their refresh tokens."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.identity.domain.models.schema import SCHEMA


class DeviceSession(Base):
    """A signed-in device: one per browser or app install, identified by its key."""

    __tablename__ = "sessions"

    # Id of the session: the `sid` of its access tokens.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Signed-in user.
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"))

    # Organization of the user, copied here so every check stays in this table; `None` for private travellers.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # JWK thumbprint of the device's public key; every token of the session is bound to it.
    dpop_jkt: Mapped[str] = mapped_column(Text)

    # Name shown in the list of devices.
    device_name: Mapped[str] = mapped_column(Text)

    # `User-Agent` at sign in.
    user_agent: Mapped[str | None] = mapped_column(Text)

    # Last address seen.
    last_ip: Mapped[str | None] = mapped_column(INET)

    # When the device signed in.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Last time the session was used.
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # The session ends if it isn't refreshed before this.
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # The session ends at this time, whatever its use.
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # When it was closed; `None` while open.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Why it was closed (`RevocationReason`).
    revoked_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        # The list of connected devices reads only the open sessions of a user.
        Index("ix_sessions_open_by_user", "user_id", postgresql_where=text("revoked_at IS NULL")),
        {"schema": SCHEMA},
    )


class RefreshToken(Base):
    """A single-use refresh token of a device session. Only its SHA-256 is stored."""

    __tablename__ = "refresh_tokens"

    # SHA-256 of the token, hex.
    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)

    # Session the token renews.
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.sessions.id", ondelete="CASCADE"), index=True
    )

    # When it was issued.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # When it was exchanged for the next one; seeing it again after this means it was copied.
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = ({"schema": SCHEMA},)
