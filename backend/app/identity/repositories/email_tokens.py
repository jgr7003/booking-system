"""Persistence of the links sent by email."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.models.email_tokens import EmailToken


class EmailTokenRepository:
    """Reads and writes email links, inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Initializes the repository.

        Args:
            session: Session of the transaction to work in. The repository never commits.
        """
        self._session = session

    async def add(self, token_hash: str, user_id: uuid.UUID, purpose: str, expires_at: datetime) -> None:
        """Saves a new link.

        Args:
            token_hash: SHA-256 of the token.
            user_id: User the link is for.
            purpose: What it does.
            expires_at: When it stops working.
        """
        self._session.add(EmailToken(token_hash=token_hash, user_id=user_id, purpose=purpose, expires_at=expires_at))
        await self._session.flush()

    async def get_for_update(self, token_hash: str) -> EmailToken | None:
        """Reads a link and locks it, so it can't be used twice at the same time.

        Args:
            token_hash: SHA-256 of the token.

        Returns:
            The link, or `None`.
        """
        return await self._session.scalar(
            select(EmailToken).where(EmailToken.token_hash == token_hash).with_for_update()
        )

    async def expire_unused(self, user_id: uuid.UUID, purposes: list[str], now: datetime) -> None:
        """Makes the pending links of a user stop working (a new one replaces them).

        Args:
            user_id: The user.
            purposes: Which kinds of links.
            now: Current time.
        """
        await self._session.execute(
            update(EmailToken)
            .where(EmailToken.user_id == user_id, EmailToken.purpose.in_(purposes), EmailToken.used_at.is_(None))
            .values(used_at=now)
        )

    async def get(self, token_hash: str) -> EmailToken | None:
        """Reads a link without locking it.

        Args:
            token_hash: SHA-256 of the token.

        Returns:
            The link, or `None`.
        """
        return await self._session.get(EmailToken, token_hash)
