"""Persistence of users and their linked identities in PostgreSQL."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import equals_or_null
from app.identity.domain.dtos.users import NewUser, UserStatus
from app.identity.domain.models.users import PasswordCredential, User, UserIdentity


class UserRepository:
    """Reads and writes users, inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Initializes the repository.

        Args:
            session: Session of the transaction to work in. The repository never commits.
        """
        self._session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        """Reads a user by id.

        Args:
            user_id: Id of the user.

        Returns:
            The user, or `None`.
        """
        return await self._session.get(User, user_id)

    async def find_by_email(self, organization_id: uuid.UUID | None, email: str) -> User | None:
        """Finds the user of an installation with an email.

        Args:
            organization_id: Organization of the installation; `None` for the main platform.
            email: Email, already in lower case.

        Returns:
            The user, or `None`.
        """
        return await self._session.scalar(
            select(User).where(equals_or_null(User.organization_id, organization_id), User.email == email)
        )

    async def find_by_identity(self, provider_key: str, subject: str) -> User | None:
        """Finds the user linked to an identity of a provider.

        Args:
            provider_key: Identity provider.
            subject: Id of the person at the provider (`sub`).

        Returns:
            The user, or `None`.
        """
        return await self._session.scalar(
            select(User)
            .join(UserIdentity, UserIdentity.user_id == User.id)
            .where(UserIdentity.provider_key == provider_key, UserIdentity.subject == subject)
        )

    async def add(self, new: NewUser) -> User:
        """Saves a new active user.

        Args:
            new: Validated data of the user.

        Returns:
            The saved user.
        """
        user = User(
            id=uuid.uuid4(),
            organization_id=new.organization_id,
            email=new.email,
            display_name=new.display_name,
            status=UserStatus.ACTIVE.value,
            email_verified_at=datetime.now(UTC) if new.email_verified else None,
            phone_number=new.phone_number,
            language=new.language,
            # Set here instead of relying on the database defaults, so nothing is loaded lazily later.
            failed_login_attempts=0,
            locked_until=None,
            # A new user has no password yet; saying so avoids a lazy load on first access.
            password=None,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def delete(self, user: User) -> None:
        """Deletes a user with its password and identities.

        Args:
            user: The user.
        """
        await self._session.delete(user)
        await self._session.flush()

    async def link_identity(self, user_id: uuid.UUID, provider_key: str, subject: str) -> None:
        """Links an identity of a provider to a user.

        Args:
            user_id: Id of the user.
            provider_key: Identity provider.
            subject: Id of the person at the provider (`sub`).
        """
        self._session.add(UserIdentity(user_id=user_id, provider_key=provider_key, subject=subject))
        await self._session.flush()

    async def set_password_hash(self, user: User, password_hash: str) -> None:
        """Sets or replaces the password of a user.

        Args:
            user: The user.
            password_hash: Argon2id hash of the new password.
        """
        if user.password is None:
            user.password = PasswordCredential(user_id=user.id, password_hash=password_hash)
        else:
            user.password.password_hash = password_hash
            user.password.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def provider_keys(self, user_id: uuid.UUID) -> list[str]:
        """Identity providers linked to a user, oldest first.

        Args:
            user_id: The user.

        Returns:
            The provider keys.
        """
        result = await self._session.scalars(
            select(UserIdentity.provider_key).where(UserIdentity.user_id == user_id).order_by(UserIdentity.created_at)
        )
        return list(result)
