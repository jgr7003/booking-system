"""Database models of the travellers module."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# PostgreSQL schema that holds every table of the module.
SCHEMA = "travellers"


class Traveller(Base):
    """A person who travels. Without user accounts, each booking creates its own traveller."""

    __tablename__ = "travellers"

    # Id of the traveller; other modules keep it without a foreign key.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Given name.
    given_name: Mapped[str] = mapped_column(Text)

    # Family name.
    family_name: Mapped[str] = mapped_column(Text)

    # Date of birth.
    born_on: Mapped[date] = mapped_column(Date)

    # `m` or `f`, as in the identity document.
    gender: Mapped[str] = mapped_column(Text)

    # Email, in lower case.
    email: Mapped[str] = mapped_column(Text)

    # Phone number in E.164 format.
    phone_number: Mapped[str] = mapped_column(Text)

    # When the traveller was saved.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Identity documents of the traveller.
    identity_documents: Mapped[list["IdentityDocument"]] = relationship(
        back_populates="traveller", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = ({"schema": SCHEMA},)


class IdentityDocument(Base):
    """An identity document of a traveller, e.g. a passport."""

    __tablename__ = "identity_documents"

    # Id of the document.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner of the document.
    traveller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.travellers.id", ondelete="CASCADE"), index=True
    )

    # Kind of document, e.g. `passport`.
    type: Mapped[str] = mapped_column(Text)

    # Number of the document.
    number: Mapped[str] = mapped_column(Text)

    # ISO 3166-1 alpha-2 code of the issuing country.
    issuing_country_code: Mapped[str] = mapped_column(Text)

    # Expiry date.
    expires_on: Mapped[date] = mapped_column(Date)

    # Owner of the document.
    traveller: Mapped[Traveller] = relationship(back_populates="identity_documents")

    __table_args__ = ({"schema": SCHEMA},)
