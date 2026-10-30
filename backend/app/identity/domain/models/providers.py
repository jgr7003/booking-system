"""Database models of identity providers (OIDC) and of sign-in attempts through them."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, LargeBinary, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.identity.domain.models.schema import SCHEMA


class IdentityProvider(Base):
    """An OIDC provider of an installation: Google or Keycloak for the platform, an organization's own AS.

    Every provider is a row, Google included: they differ only in their configuration.
    """

    __tablename__ = "identity_providers"

    # Id of the provider; `user_identities.provider_key` keeps it as text.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization of the installation, without a foreign key (another module); `None` for the main platform.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Name in URLs, e.g. `google` in `/auth/oidc/google/authorize`.
    slug: Mapped[str] = mapped_column(Text)

    # Name on the sign-in button, e.g. «Google» or «Acme SSO».
    display_name: Mapped[str] = mapped_column(Text)

    # Issuer: identifies the provider and is where its discovery document lives.
    issuer: Mapped[str] = mapped_column(Text)

    # Development only: base URL for server-to-server calls when the browser and the API reach the
    # provider at different hosts (Keycloak in docker).
    backchannel_base_url: Mapped[str | None] = mapped_column(Text)

    # Client id registered at the provider.
    client_id: Mapped[str] = mapped_column(Text)

    # Client secret, encrypted with `IDENTITY_SECRETS_KEY`.
    client_secret_encrypted: Mapped[bytes] = mapped_column(LargeBinary)

    # Scopes asked for, space separated.
    scopes: Mapped[str] = mapped_column(Text, server_default="openid email profile")

    # Accept the email even without `email_verified` (some organization servers don't send it).
    trust_email: Mapped[bool] = mapped_column(Boolean, server_default="false")

    # Extra parameters of the authorization request, e.g. `{"prompt": "select_account"}`.
    extra_authorize_params: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")

    # Whether the sign-in button is shown and the provider accepted.
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")

    # When it was added.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("organization_id", "slug", postgresql_nulls_not_distinct=True),
        {"schema": SCHEMA},
    )


class LoginAttempt(Base):
    """A sign in through a provider, between leaving for it and coming back.

    It holds the PKCE verifier and the `state` and `nonce`, bound to the device that started it.
    If the person has no account, it keeps the verified identity while they decide.
    """

    __tablename__ = "login_attempts"

    # Id of the attempt; the screen «no encontramos tu cuenta» refers to it.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # `state` sent to the provider and received back.
    state: Mapped[str] = mapped_column(Text, unique=True)

    # Organization of the installation; `None` for the main platform.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Provider of the attempt.
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    # `nonce` that must come back inside the id_token.
    nonce: Mapped[str] = mapped_column(Text)

    # PKCE verifier; it never leaves the server.
    code_verifier: Mapped[str] = mapped_column(Text)

    # Thumbprint of the key of the device that started the attempt; only it can finish it.
    dpop_jkt: Mapped[str] = mapped_column(Text)

    # Where the provider sends the browser back.
    redirect_uri: Mapped[str] = mapped_column(Text)

    # Path of the app to go back to after signing in.
    return_to: Mapped[str | None] = mapped_column(Text)

    # `started`, `exchanging` (the code was received) or `awaiting_signup`.
    status: Mapped[str] = mapped_column(Text)

    # The identity the provider verified (sub, email, name), while the person decides to sign up.
    verified_identity: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # When it was started.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # It stops working at this time; expired attempts are deleted by this column.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = ({"schema": SCHEMA},)
