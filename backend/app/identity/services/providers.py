"""Registering the OIDC providers of an installation."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.models.providers import IdentityProvider
from app.identity.repositories.providers import ProviderRepository
from app.identity.services.secrets import encrypt_secret


async def register_provider(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID | None,
    slug: str,
    display_name: str,
    issuer: str,
    client_id: str,
    client_secret: str,
    backchannel_base_url: str | None = None,
    scopes: str = "openid email profile",
    trust_email: bool = False,
    extra_authorize_params: dict[str, Any] | None = None,
) -> tuple[IdentityProvider, bool]:
    """Adds a provider to an installation, or updates the one with the same slug (idempotent).

    Args:
        session: Session of the caller's transaction.
        organization_id: Organization of the installation; `None` for the main platform.
        slug: Name in URLs, e.g. `google`.
        display_name: Text of the sign-in button.
        issuer: Issuer of the provider.
        client_id: Client id registered at the provider.
        client_secret: Client secret; stored encrypted.
        backchannel_base_url: Base URL for server-to-server calls (development only).
        scopes: Scopes asked for.
        trust_email: Accept the email even without `email_verified`.
        extra_authorize_params: Extra parameters of the authorization request.

    Returns:
        The provider and whether it was created (`False` if it was updated).
    """
    repository = ProviderRepository(session)
    provider = await repository.find(organization_id, slug)
    created = provider is None
    if provider is None:
        provider = IdentityProvider(id=uuid.uuid4(), organization_id=organization_id, slug=slug)
    provider.display_name = display_name
    provider.issuer = issuer.rstrip("/")
    provider.backchannel_base_url = backchannel_base_url
    provider.client_id = client_id
    provider.client_secret_encrypted = encrypt_secret(client_secret)
    provider.scopes = scopes
    provider.trust_email = trust_email
    provider.extra_authorize_params = extra_authorize_params or {}
    provider.enabled = True
    if created:
        await repository.add(provider)
    else:
        await session.flush()
    return provider, created
