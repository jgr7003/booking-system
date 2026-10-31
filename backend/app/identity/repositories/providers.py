"""Persistence of identity providers and sign-in attempts."""

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import equals_or_null
from app.identity.domain.models.providers import IdentityProvider, LoginAttempt


class ProviderRepository:
    """Reads and writes identity providers and sign-in attempts, inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Initializes the repository.

        Args:
            session: Session of the transaction to work in. The repository never commits.
        """
        self._session = session

    async def list_enabled(self, organization_id: uuid.UUID | None) -> list[IdentityProvider]:
        """Enabled providers of an installation, by name.

        Args:
            organization_id: Organization of the installation; `None` for the main platform.

        Returns:
            The providers.
        """
        result = await self._session.scalars(
            select(IdentityProvider)
            .where(
                equals_or_null(IdentityProvider.organization_id, organization_id),
                IdentityProvider.enabled.is_(True),
            )
            .order_by(IdentityProvider.display_name)
        )
        return list(result)

    async def find_enabled(self, organization_id: uuid.UUID | None, slug: str) -> IdentityProvider | None:
        """An enabled provider of an installation by its slug.

        Args:
            organization_id: Organization of the installation; `None` for the main platform.
            slug: Name of the provider in URLs.

        Returns:
            The provider, or `None`.
        """
        return await self._session.scalar(
            select(IdentityProvider).where(
                equals_or_null(IdentityProvider.organization_id, organization_id),
                IdentityProvider.slug == slug,
                IdentityProvider.enabled.is_(True),
            )
        )

    async def find(self, organization_id: uuid.UUID | None, slug: str) -> IdentityProvider | None:
        """A provider of an installation by its slug, enabled or not.

        Args:
            organization_id: Organization of the installation; `None` for the main platform.
            slug: Name of the provider in URLs.

        Returns:
            The provider, or `None`.
        """
        return await self._session.scalar(
            select(IdentityProvider).where(
                equals_or_null(IdentityProvider.organization_id, organization_id),
                IdentityProvider.slug == slug,
            )
        )

    async def get(self, provider_id: uuid.UUID) -> IdentityProvider | None:
        """A provider by id.

        Args:
            provider_id: Id of the provider.

        Returns:
            The provider, or `None`.
        """
        return await self._session.get(IdentityProvider, provider_id)

    async def add(self, provider: IdentityProvider) -> None:
        """Saves a new provider.

        Args:
            provider: The provider.
        """
        self._session.add(provider)
        await self._session.flush()

    async def add_attempt(self, attempt: LoginAttempt) -> None:
        """Saves a new sign-in attempt.

        Args:
            attempt: The attempt.
        """
        self._session.add(attempt)
        await self._session.flush()

    async def attempt_by_state_for_update(self, state: str) -> LoginAttempt | None:
        """Reads an attempt by its `state` and locks it.

        Args:
            state: `state` the provider sent back.

        Returns:
            The attempt, or `None`.
        """
        return await self._session.scalar(select(LoginAttempt).where(LoginAttempt.state == state).with_for_update())

    async def attempt_for_update(self, attempt_id: uuid.UUID) -> LoginAttempt | None:
        """Reads an attempt by id and locks it.

        Args:
            attempt_id: Id of the attempt.

        Returns:
            The attempt, or `None`.
        """
        return await self._session.scalar(
            select(LoginAttempt).where(LoginAttempt.id == attempt_id).with_for_update()
        )

    async def delete_attempt(self, attempt: LoginAttempt) -> None:
        """Deletes an attempt that ended.

        Args:
            attempt: The attempt.
        """
        await self._session.delete(attempt)
        await self._session.flush()

    async def delete_expired_attempts(self, now: datetime) -> int:
        """Deletes attempts that expired.

        Args:
            now: Current time.

        Returns:
            How many were deleted.
        """
        result = await self._session.execute(delete(LoginAttempt).where(LoginAttempt.expires_at <= now))
        return result.rowcount
