"""Database models of the organizations module."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# PostgreSQL schema that holds every table of the module.
SCHEMA = "organizations"


class Organization(Base):
    """A company with its own installation of the platform."""

    __tablename__ = "organizations"

    # Id of the organization; other modules keep it without a foreign key.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Short unique name, used by commands and logs, e.g. `acme`.
    slug: Mapped[str] = mapped_column(Text, unique=True)

    # Name shown to users.
    name: Mapped[str] = mapped_column(Text)

    # `active` or `suspended`.
    status: Mapped[str] = mapped_column(Text)

    # Configuration of the organization, validated by `OrganizationSettings`.
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")

    # When the organization was created.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Hostnames of its installation.
    domains: Mapped[list["Domain"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = ({"schema": SCHEMA},)


class Domain(Base):
    """A hostname of an organization's installation, e.g. `acme.localhost`."""

    __tablename__ = "domains"

    # The hostname, in lower case and without port.
    hostname: Mapped[str] = mapped_column(Text, primary_key=True)

    # Organization that owns the hostname.
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.organizations.id", ondelete="CASCADE"), index=True
    )

    # Organization that owns the hostname.
    organization: Mapped[Organization] = relationship(back_populates="domains")

    __table_args__ = ({"schema": SCHEMA},)
