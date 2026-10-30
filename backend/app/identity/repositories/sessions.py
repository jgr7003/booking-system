"""Persistence of device sessions and refresh tokens in PostgreSQL."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.models.sessions import DeviceSession, RefreshToken


class SessionRepository:
    """Reads and writes device sessions, inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Initializes the repository.

        Args:
            session: Session of the transaction to work in. The repository never commits.
        """
        self._session = session

    async def add(self, device_session: DeviceSession) -> None:
        """Saves a new device session.

        Args:
            device_session: The session.
        """
        self._session.add(device_session)
        await self._session.flush()

    async def get(self, session_id: uuid.UUID, *, for_update: bool = False) -> DeviceSession | None:
        """Reads a device session.

        Args:
            session_id: Id of the session.
            for_update: Lock the row until the transaction ends.

        Returns:
            The session, or `None`.
        """
        query = select(DeviceSession).where(DeviceSession.id == session_id)
        if for_update:
            query = query.with_for_update()
        return await self._session.scalar(query)

    async def list_open(self, user_id: uuid.UUID, now: datetime) -> list[DeviceSession]:
        """Open sessions of a user, most recently used first.

        Args:
            user_id: The user.
            now: Current time; expired sessions are left out.

        Returns:
            The sessions.
        """
        result = await self._session.scalars(
            select(DeviceSession)
            .where(
                DeviceSession.user_id == user_id,
                DeviceSession.revoked_at.is_(None),
                DeviceSession.idle_expires_at > now,
                DeviceSession.absolute_expires_at > now,
            )
            .order_by(DeviceSession.last_seen_at.desc())
        )
        return list(result)

    async def revoke(self, session_ids: list[uuid.UUID], reason: str, now: datetime) -> None:
        """Closes sessions that are still open.

        Args:
            session_ids: The sessions.
            reason: Why (`RevocationReason`).
            now: Current time.
        """
        if not session_ids:
            return
        await self._session.execute(
            update(DeviceSession)
            .where(DeviceSession.id.in_(session_ids), DeviceSession.revoked_at.is_(None))
            .values(revoked_at=now, revoked_reason=reason)
        )

    async def add_refresh_token(self, session_id: uuid.UUID, token_hash: str) -> None:
        """Saves a new refresh token of a session.

        Args:
            session_id: The session.
            token_hash: SHA-256 of the token.
        """
        self._session.add(RefreshToken(token_hash=token_hash, session_id=session_id))
        await self._session.flush()

    async def get_refresh_token_for_update(self, token_hash: str) -> RefreshToken | None:
        """Reads a refresh token and locks it, so two concurrent refreshes can't both use it.

        Args:
            token_hash: SHA-256 of the token.

        Returns:
            The token, or `None` if it doesn't exist.
        """
        return await self._session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        )
