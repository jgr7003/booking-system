"""Protection of the password sign in against guessing: per account, per device and per address.

- **Per account** (PostgreSQL): `max_failed_logins` wrong passwords in a row, configurable per
  organization, block signing in with a password for `login_lock_minutes`. The user gets an email;
  changing the password unblocks the account at once.
- **Per device and per address of an installation** (`LoginGuard`): counters in Redis; a blocked
  address is saved in PostgreSQL (`identity.blocked_ips`), the source of truth. Losing the counters
  only forgets some attempts.

Signing in through an identity provider doesn't go through here: the organization's provider vouches
for its people with its own protections.

Every refusal looks the same from outside (`LoginFailedError`); the real reason is logged
(03-usuarios-y-acceso.md §8.1).
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import equals_or_null
from app.identity.core.config import get_identity_settings
from app.identity.domain.errors.passwords import LoginFailedError
from app.identity.domain.models.blocked_ips import BlockedIp
from app.identity.domain.models.users import User
from app.organizations.public import Installation, OrganizationSettings

logger = logging.getLogger(__name__)

# Prefix of the Redis keys of the per-device and per-address counters.
LOGIN_COUNTER_PREFIX = "identity:v2:login:"


def mask_email(email: str) -> str:
    """An email for the logs: enough to recognize it, not to read it, e.g. `a***@example.test`.

    Args:
        email: The email.

    Returns:
        The masked email.
    """
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


def login_failed(reason: str, *, ip: str | None, email: str | None = None, **context: object) -> LoginFailedError:
    """Logs why a sign in failed and returns the error that hides it.

    Args:
        reason: Real reason, for the logs (`wrong_password`, `unknown_email`, `account_locked`...).
        ip: Address of the client.
        email: Email tried, masked in the log.
        **context: More fields for the log (user id, installation...).

    Returns:
        The error to raise: always the same code and message.
    """
    details = " ".join(f"{key}={value}" for key, value in context.items())
    logger.warning(
        "Sign in refused: reason=%s ip=%s email=%s %s", reason, ip, mask_email(email) if email else "-", details
    )
    return LoginFailedError("We couldn't sign you in.")


def is_locked(user: User, now: datetime) -> bool:
    """Whether signing in with a password is blocked for a user.

    Args:
        user: The user.
        now: Current time.

    Returns:
        `True` while the lock lasts.
    """
    return user.locked_until is not None and user.locked_until > now


def clear_lock(user: User) -> None:
    """Forgets the failed attempts and any lock (successful sign in, expired lock or new password).

    Args:
        user: The user.
    """
    user.failed_login_attempts = 0
    user.locked_until = None


def count_wrong_password(user: User, settings: OrganizationSettings, now: datetime) -> bool:
    """Counts a wrong password and blocks the user when they reach the limit.

    Args:
        user: The user.
        settings: Settings of the user's installation (`max_failed_logins`, `login_lock_minutes`).
        now: Current time.

    Returns:
        `True` if this attempt blocked the user (send them the email).
    """
    user.failed_login_attempts += 1
    if user.failed_login_attempts < settings.max_failed_logins:
        return False
    user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
    logger.warning(
        "Password sign in blocked: user=%s attempts=%s until=%s",
        user.id,
        user.failed_login_attempts,
        user.locked_until.isoformat(),
    )
    return True


class LoginGuard:
    """Limits failed password sign ins per device and per address of an installation.

    Three layers, from the finest to the coarsest (03-usuarios-y-acceso.md §8.1):

    1. **Device** (its DPoP key): past `device_failed_logins_limit` failures in the window, that
       device is refused until the window ends. People sharing an office address are different
       devices, so one person failing doesn't stop the others.
    2. **Address within the installation**: failures and different emails tried are counted per
       `(installation, address)`; past the limits, the address is blocked there, in PostgreSQL. An
       attack on one installation doesn't block that address in another.
    3. **Trusted networks** of the organization (`settings.trusted_networks`): their addresses are
       never counted nor blocked; the device and account limits still apply.

    Only the password sign in goes through here: a sign in through the organization's identity
    provider is that provider's to protect.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], redis: Redis | None) -> None:
        """Initializes the guard.

        Args:
            session_factory: Factory of database sessions.
            redis: Redis client for the counters; `None` counts nothing (blocks already saved still apply).
        """
        self._session_factory = session_factory
        self._redis = redis

    async def ensure_allowed(
        self, installation: Installation, ip: str | None, *, jkt: str | None = None, email: str | None = None
    ) -> None:
        """Fails if the device reached its limit or the address is blocked in the installation.

        Args:
            installation: Installation of the request.
            ip: Address of the client.
            jkt: Thumbprint of the device key, if the request carries a DPoP proof.
            email: Email tried, for the log.

        Raises:
            LoginFailedError: The device or the address can't sign in now.
        """
        settings = get_identity_settings()
        device_failures = await self._count(_device_key(installation, jkt)) if jkt is not None else 0
        if device_failures >= settings.device_failed_logins_limit:
            raise login_failed("device_limited", ip=ip, email=email, device=jkt[:12])
        if ip is None or _trusted(installation, ip):
            return
        async with self._session_factory() as session:
            blocked_until = await session.scalar(
                select(BlockedIp.blocked_until).where(
                    equals_or_null(BlockedIp.organization_id, installation.organization_id), BlockedIp.ip == ip
                )
            )
        if blocked_until is not None and blocked_until > datetime.now(UTC):
            raise login_failed("address_blocked", ip=ip, email=email, until=blocked_until.isoformat())

    async def record_failure(
        self, installation: Installation, ip: str | None, *, jkt: str | None = None, email: str | None = None
    ) -> None:
        """Counts a failed password sign in (or a lookup of an unknown email) and blocks past the limits.

        Args:
            installation: Installation of the request.
            ip: Address of the client.
            jkt: Thumbprint of the device key, if any.
            email: Email tried, if any.
        """
        if self._redis is None:
            return
        settings = get_identity_settings()
        count_address = ip is not None and not _trusted(installation, ip)
        failures_key = _address_key(installation, ip, "failures")
        emails_key = _address_key(installation, ip, "emails")
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                if jkt is not None:
                    pipe.incr(_device_key(installation, jkt))
                    pipe.expire(_device_key(installation, jkt), settings.ip_window_s, nx=True)
                if count_address:
                    pipe.incr(failures_key)
                    pipe.expire(failures_key, settings.ip_window_s, nx=True)
                    if email:
                        pipe.sadd(emails_key, email)
                        pipe.expire(emails_key, settings.ip_window_s, nx=True)
                    pipe.get(failures_key)
                    pipe.scard(emails_key)
                results = await pipe.execute()
        except RedisError as exc:
            logger.warning("Sign-in counters skipped, Redis failed: %s", exc)
            return
        if not count_address:
            return
        failures, distinct_emails = int(results[-2]), int(results[-1])
        if failures >= settings.ip_failed_logins_limit:
            await self._block(installation, ip, "too_many_failures")
        elif distinct_emails >= settings.ip_distinct_emails_limit:
            await self._block(installation, ip, "too_many_emails")

    async def _count(self, key: str) -> int:
        """Current value of a counter; 0 if it doesn't exist or Redis failed."""
        if self._redis is None:
            return 0
        try:
            return int(await self._redis.get(key) or 0)
        except RedisError as exc:
            logger.warning("Sign-in counter read skipped, Redis failed: %s", exc)
            return 0

    async def _block(self, installation: Installation, ip: str, reason: str) -> None:
        """Saves the block of an address in an installation and resets its counters."""
        settings = get_identity_settings()
        now = datetime.now(UTC)
        until = now + timedelta(minutes=settings.ip_block_minutes)
        async with self._session_factory() as session, session.begin():
            statement = insert(BlockedIp).values(
                id=uuid.uuid4(),
                organization_id=installation.organization_id,
                ip=ip,
                blocked_until=until,
                reason=reason,
                blocked_at=now,
            )
            await session.execute(
                statement.on_conflict_do_update(
                    constraint="uq_blocked_ips_organization_id_ip",
                    set_={"blocked_until": until, "reason": reason, "blocked_at": now},
                )
            )
        try:
            await self._redis.delete(
                _address_key(installation, ip, "failures"), _address_key(installation, ip, "emails")
            )
        except RedisError:
            pass
        logger.warning(
            "Address blocked from signing in with a password: ip=%s installation=%s reason=%s until=%s",
            ip,
            installation.host,
            reason,
            until.isoformat(),
        )


def _scope(installation: Installation) -> str:
    """Part of the counter keys that tells installations apart."""
    return str(installation.organization_id) if installation.organization_id else "platform"


def _device_key(installation: Installation, jkt: str) -> str:
    """Redis key of the failures of a device in an installation."""
    return f"{LOGIN_COUNTER_PREFIX}{_scope(installation)}:device:{jkt}"


def _address_key(installation: Installation, ip: str | None, kind: str) -> str:
    """Redis key of a counter of an address in an installation (`failures` or `emails`)."""
    return f"{LOGIN_COUNTER_PREFIX}{_scope(installation)}:{kind}:{ip}"


def _trusted(installation: Installation, ip: str) -> bool:
    """Whether the address is in one of the organization's trusted networks."""
    networks = installation.settings.trusted_networks
    if not networks:
        return False
    try:
        address = ip_address(ip)
    except ValueError:
        return False
    return any(address in network for network in networks)
