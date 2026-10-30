"""Database models of users, their passwords and their linked identities."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.identity.domain.dtos.users import Language
from app.identity.domain.models.schema import SCHEMA


class User(Base):
    """An account that signs in to one installation: an organization's or the main platform."""

    __tablename__ = "users"

    # Id of the user; other modules keep it without a foreign key.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization of the user, without a foreign key (another module); `None` for private travellers.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Email, in lower case.
    email: Mapped[str] = mapped_column(Text)

    # When the email was proven to belong to the user; `None` while unverified.
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Name shown in the interface.
    display_name: Mapped[str] = mapped_column(Text)

    # Phone number in E.164 format, optional.
    phone_number: Mapped[str | None] = mapped_column(Text)

    # Language the user chose (`Language`); `None` lets the app use the browser's or the system's.
    language: Mapped[Language | None] = mapped_column(
        Enum(Language, name="language", schema=SCHEMA, values_callable=lambda e: [m.value for m in e])
    )

    # `active` or `disabled`.
    status: Mapped[str] = mapped_column(Text)

    # When the user was created.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Last successful sign in.
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Wrong passwords in a row since the last successful sign in or unlock.
    failed_login_attempts: Mapped[int] = mapped_column(Integer, server_default="0")

    # Signing in with a password is blocked until this time; `None` when it isn't.
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Password, if the user set one.
    password: Mapped["PasswordCredential | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        # One account per email and installation. Without NULLS NOT DISTINCT two private travellers
        # (organization NULL) could share an email, because NULL is never equal to NULL. Its index
        # (organization_id, email) also serves the sign-in lookup and any search by organization.
        UniqueConstraint("organization_id", "email", postgresql_nulls_not_distinct=True),
        {"schema": SCHEMA},
    )


class PasswordCredential(Base):
    """The password of a user, as an Argon2id hash."""

    __tablename__ = "password_credentials"

    # Owner of the password.
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), primary_key=True)

    # Argon2id hash, with its parameters.
    password_hash: Mapped[str] = mapped_column(Text)

    # When the password was last set.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Owner of the password.
    user: Mapped[User] = relationship(back_populates="password")

    __table_args__ = ({"schema": SCHEMA},)


class UserIdentity(Base):
    """An identity at an identity provider (its `sub`), linked to a user."""

    __tablename__ = "user_identities"

    # Id of the link.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User the identity belongs to.
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), index=True)

    # Identity provider: the id of its row in `identity_providers`, as text.
    provider_key: Mapped[str] = mapped_column(Text)

    # Stable id of the person at the provider (`sub`).
    subject: Mapped[str] = mapped_column(Text)

    # When the identity was linked.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("provider_key", "subject"),
        {"schema": SCHEMA},
    )
