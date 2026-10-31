"""Device sessions: opening one per device, refresh token rotation, revocation and the device list.

A session is a device (its key thumbprint) signed in as a user. Each refresh token is single-use:
seeing a used one again means it was copied, and the whole session is closed
(03-usuarios-y-acceso.md §10.2 and §11).
"""

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.identity.core.config import get_identity_settings
from app.identity.domain.dtos.tokens import DeviceInfo, DeviceSessionView, RevocationReason, TokenPair
from app.identity.domain.dtos.users import UserStatus
from app.identity.domain.errors.tokens import InvalidTokenError, SessionExpiredError, SessionRevokedError
from app.identity.domain.models.sessions import DeviceSession
from app.identity.domain.models.users import User
from app.identity.repositories.sessions import SessionRepository
from app.identity.repositories.users import UserRepository
from app.identity.tokens.signing import issue_access_token, new_access_claims

logger = logging.getLogger(__name__)

# Prefix of the Redis keys that remember open sessions.
SESSION_CACHE_PREFIX = "identity:v1:session:"


def hash_secret(value: str) -> str:
    """SHA-256 of a secret token, hex. Only this is stored.

    Args:
        value: The token.

    Returns:
        Its hash.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SessionStatusCache:
    """Remembers in Redis which sessions are open, so most requests skip the database.

    Revoking a session deletes its entry at once. Redis is never the source of truth: without it,
    every check goes to PostgreSQL.
    """

    def __init__(self, redis: Redis | None) -> None:
        """Initializes the cache.

        Args:
            redis: Redis client; `None` disables the cache.
        """
        self._redis = redis

    async def is_open(self, session_id: uuid.UUID) -> bool:
        """Whether the cache knows the session is open.

        Args:
            session_id: The session.

        Returns:
            `True` only if the cache has it; `False` means "ask the database".
        """
        if self._redis is None:
            return False
        try:
            return await self._redis.get(f"{SESSION_CACHE_PREFIX}{session_id}") is not None
        except RedisError as exc:
            logger.warning("Session cache read failed: %s", exc)
            return False

    async def remember_open(self, session_id: uuid.UUID, ttl_s: int) -> None:
        """Remembers that a session is open.

        Args:
            session_id: The session.
            ttl_s: For how long.
        """
        if self._redis is None:
            return
        try:
            await self._redis.set(f"{SESSION_CACHE_PREFIX}{session_id}", "1", ex=ttl_s)
        except RedisError as exc:
            logger.warning("Session cache write failed: %s", exc)

    async def forget(self, session_ids: list[uuid.UUID]) -> None:
        """Forgets sessions, so the next check goes to the database.

        Args:
            session_ids: The sessions.
        """
        if self._redis is None or not session_ids:
            return
        try:
            await self._redis.delete(*(f"{SESSION_CACHE_PREFIX}{sid}" for sid in session_ids))
        except RedisError as exc:
            # The entry expires on its own within `session_cache_ttl_s`.
            logger.warning("Session cache invalidation failed: %s", exc)


def _ensure_open(device_session: DeviceSession | None, now: datetime) -> None:
    """Fails if a session is closed (`session_revoked`) or expired (`session_expired`)."""
    if device_session is None or device_session.revoked_at is not None:
        raise SessionRevokedError("The session was closed.")
    if not _is_open(device_session, now):
        raise SessionExpiredError("The session expired.")


def _is_open(device_session: DeviceSession, now: datetime) -> bool:
    """Whether a session is neither revoked nor expired."""
    return (
        device_session.revoked_at is None
        and device_session.idle_expires_at > now
        and device_session.absolute_expires_at > now
    )


def _token_pair(user: User, device_session: DeviceSession, issuer: str, refresh_token: str) -> TokenPair:
    """Signs a new access token and pairs it with a refresh token."""
    settings = get_identity_settings()
    claims = new_access_claims(
        issuer=issuer,
        user_id=user.id,
        organization_id=user.organization_id,
        session_id=device_session.id,
        name=user.display_name,
        email=user.email,
        language=user.language.value if user.language else None,
        jkt=device_session.dpop_jkt,
    )
    return TokenPair(
        access_token=issue_access_token(claims),
        expires_in=settings.access_token_ttl_s,
        refresh_token=refresh_token,
        session_id=device_session.id,
    )


async def open_device_session(
    session: AsyncSession,
    cache: SessionStatusCache,
    *,
    user: User,
    issuer: str,
    device: DeviceInfo,
) -> TokenPair:
    """Signs a device in, inside the caller's transaction.

    A device has one session per user: signing in again from the same key closes the previous one.

    Args:
        session: Session of the caller's transaction.
        cache: Cache of open sessions.
        user: The user who signed in.
        issuer: Host of the installation.
        device: The device and its key.

    Returns:
        The first token pair of the session.
    """
    settings = get_identity_settings()
    now = datetime.now(UTC)
    repository = SessionRepository(session)
    previous = [s.id for s in await repository.list_open(user.id, now) if s.dpop_jkt == device.jkt]
    await repository.revoke(previous, RevocationReason.LOGOUT.value, now)
    await cache.forget(previous)

    device_session = DeviceSession(
        id=uuid.uuid4(),
        user_id=user.id,
        organization_id=user.organization_id,
        dpop_jkt=device.jkt,
        device_name=device.device_name,
        user_agent=device.user_agent,
        last_ip=device.ip,
        created_at=now,
        last_seen_at=now,
        idle_expires_at=now + timedelta(seconds=settings.session_idle_ttl_s),
        absolute_expires_at=now + timedelta(seconds=settings.session_max_ttl_s),
    )
    await repository.add(device_session)
    refresh_token = secrets.token_urlsafe(32)
    await repository.add_refresh_token(device_session.id, hash_secret(refresh_token))
    user.last_login_at = now
    return _token_pair(user, device_session, issuer, refresh_token)


async def refresh_device_session(
    session_factory: async_sessionmaker[AsyncSession],
    cache: SessionStatusCache,
    *,
    refresh_token: str,
    jkt: str,
    issuer: str,
    organization_id: uuid.UUID | None,
    ip: str | None,
) -> TokenPair:
    """Exchanges a refresh token for a new pair (rotation).

    It manages its own transactions: when it detects a copied token it must save the revocation
    and still fail the request.

    Args:
        session_factory: Factory of database sessions.
        cache: Cache of open sessions.
        refresh_token: The token the device presents.
        jkt: Thumbprint of the key that signed the request's DPoP proof.
        issuer: Host of the installation of the request.
        organization_id: Organization of that installation.
        ip: Address of the client.

    Returns:
        The new pair; the presented refresh token can't be used again.

    Raises:
        InvalidTokenError: The token doesn't exist or is from another installation.
        SessionRevokedError: The session is closed or expired, or was just closed because the token
            was reused or came from another device.
    """
    settings = get_identity_settings()
    now = datetime.now(UTC)
    revoked: tuple[uuid.UUID, RevocationReason] | None = None
    async with session_factory() as session, session.begin():
        repository = SessionRepository(session)
        stored = await repository.get_refresh_token_for_update(hash_secret(refresh_token))
        if stored is None:
            raise InvalidTokenError("The refresh token is not valid.")
        device_session = await repository.get(stored.session_id, for_update=True)
        if device_session.organization_id != organization_id:
            raise InvalidTokenError("The refresh token is not valid.")
        _ensure_open(device_session, now)
        user = await UserRepository(session).get(device_session.user_id)
        if stored.used_at is not None:
            revoked = (device_session.id, RevocationReason.REFRESH_REUSE)
        elif device_session.dpop_jkt != jkt:
            revoked = (device_session.id, RevocationReason.KEY_MISMATCH)
        elif user is None or user.status != UserStatus.ACTIVE.value:
            revoked = (device_session.id, RevocationReason.USER_REVOKED)
        if revoked is not None:
            await repository.revoke([revoked[0]], revoked[1].value, now)
        else:
            stored.used_at = now
            new_refresh_token = secrets.token_urlsafe(32)
            await repository.add_refresh_token(device_session.id, hash_secret(new_refresh_token))
            device_session.last_seen_at = now
            device_session.last_ip = ip
            device_session.idle_expires_at = min(
                now + timedelta(seconds=settings.session_idle_ttl_s), device_session.absolute_expires_at
            )
            pair = _token_pair(user, device_session, issuer, new_refresh_token)
    if revoked is not None:
        await cache.forget([revoked[0]])
        logger.warning("Session %s revoked on refresh: %s", revoked[0], revoked[1].value)
        raise SessionRevokedError("The session was closed for security.")
    return pair


async def revoke_device_sessions(
    session_factory: async_sessionmaker[AsyncSession],
    cache: SessionStatusCache,
    session_ids: list[uuid.UUID],
    reason: RevocationReason,
) -> None:
    """Closes sessions in their own transaction, so the closing survives a failing request.

    Args:
        session_factory: Factory of database sessions.
        cache: Cache of open sessions.
        session_ids: The sessions.
        reason: Why.
    """
    async with session_factory() as session, session.begin():
        await SessionRepository(session).revoke(session_ids, reason.value, datetime.now(UTC))
    await cache.forget(session_ids)
    if reason in (RevocationReason.KEY_MISMATCH, RevocationReason.REFRESH_REUSE):
        logger.warning("Sessions %s revoked: %s", session_ids, reason.value)


async def revoke_user_sessions(
    session: AsyncSession,
    cache: SessionStatusCache,
    user_id: uuid.UUID,
    reason: RevocationReason,
    *,
    keep: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    """Closes every open session of a user, inside the caller's transaction.

    Args:
        session: Session of the caller's transaction.
        cache: Cache of open sessions.
        user_id: The user.
        reason: Why.
        keep: A session to leave open (the current device, for «close the others»).

    Returns:
        The closed sessions.
    """
    now = datetime.now(UTC)
    repository = SessionRepository(session)
    ids = [s.id for s in await repository.list_open(user_id, now) if s.id != keep]
    await repository.revoke(ids, reason.value, now)
    await cache.forget(ids)
    return ids


async def ensure_session_open(
    session_factory: async_sessionmaker[AsyncSession],
    cache: SessionStatusCache,
    session_id: uuid.UUID,
) -> None:
    """Checks that a session is still open; revocation takes effect at once, not when tokens expire.

    Args:
        session_factory: Factory of database sessions.
        cache: Cache of open sessions.
        session_id: The session of the access token.

    Raises:
        SessionRevokedError: The session is closed.
        SessionExpiredError: The session expired.
    """
    if await cache.is_open(session_id):
        return
    settings = get_identity_settings()
    now = datetime.now(UTC)
    async with session_factory() as session, session.begin():
        device_session = await SessionRepository(session).get(session_id)
        _ensure_open(device_session, now)
        # Cache misses happen about once a minute per session: a good moment to record use.
        device_session.last_seen_at = now
    await cache.remember_open(session_id, settings.session_cache_ttl_s)


async def list_device_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[DeviceSessionView]:
    """The connected devices of a user.

    Args:
        session: An open session.
        user_id: The user.

    Returns:
        The open sessions, most recently used first.
    """
    sessions = await SessionRepository(session).list_open(user_id, datetime.now(UTC))
    return [
        DeviceSessionView(
            id=s.id,
            device_name=s.device_name,
            created_at=s.created_at,
            last_seen_at=s.last_seen_at,
            last_ip=str(s.last_ip) if s.last_ip is not None else None,
        )
        for s in sessions
    ]
