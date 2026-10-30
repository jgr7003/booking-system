"""Database model of the addresses blocked from signing in with a password."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.identity.domain.models.schema import SCHEMA


class BlockedIp(Base):
    """An address that failed too many password sign ins in one installation (03-usuarios-y-acceso.md §8.1).

    The block is per installation: an attack on the main platform doesn't block that address in an
    organization's installation, and the other way around.
    """

    __tablename__ = "blocked_ips"

    # Id of the block.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization of the installation, without a foreign key (another module); `None` for the main platform.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # The address.
    ip: Mapped[str] = mapped_column(INET)

    # Password sign ins from it are refused in that installation until this time.
    blocked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # What triggered the block, for whoever reviews it (`too_many_failures`, `too_many_emails`).
    reason: Mapped[str] = mapped_column(Text)

    # When it was blocked the last time.
    blocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # One block per address and installation; its index answers «is this address blocked here?».
        UniqueConstraint("organization_id", "ip", postgresql_nulls_not_distinct=True),
        {"schema": SCHEMA},
    )
