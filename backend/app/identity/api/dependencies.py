"""FastAPI dependencies of the identity module: who is calling, from which device.

Every authenticated request carries two headers (03-usuarios-y-acceso.md §11):

    Authorization: DPoP <access token>   bound to the device key by `cnf.jkt`
    DPoP: <proof>                        signed by that key for this very request

A token presented without its key (as `Bearer`, without a proof, or with a proof of another key)
was copied off its device: the session is closed and the request fails.
"""

from typing import Annotated

import httpx2
from fastapi import Depends, Header, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.db import get_session_factory
from app.core.http import get_http_client
from app.core.proxy import client_ip as original_client_ip
from app.identity.domain.dtos.tokens import DeviceInfo, Principal, RevocationReason
from app.identity.domain.errors.tokens import (
    AuthenticationRequiredError,
    InvalidTokenError,
    TokenBindingMismatchError,
)
from app.identity.providers.base import PasswordHasher
from app.identity.providers.oidc.client import OidcClient
from app.identity.providers.passwords.argon2 import Argon2PasswordHasher
from app.identity.services.devices import describe_device
from app.identity.services.login_guard import LoginGuard
from app.identity.services.oidc_login import OidcLogin
from app.identity.services.passwords import PasswordAccounts
from app.identity.services.rate_limit import RateLimiter
from app.identity.services.sessions import SessionStatusCache, ensure_session_open, revoke_device_sessions
from app.identity.tokens.dpop import verify_proof
from app.identity.tokens.signing import read_access_token
from app.notifications.public import EmailSender, create_email_sender
from app.organizations.public import Installation, current_installation


def get_identity_redis(request: Request) -> Redis | None:
    """FastAPI dependency that provides Redis for sessions and DPoP replays, if it's available.

    Tests override it with the test Redis or with `None` (to exercise the fallbacks).

    Args:
        request: The incoming request, used to reach the application state.

    Returns:
        The shared client, or `None` if the application has none.
    """
    return getattr(request.app.state, "redis", None)


def get_session_cache(redis: Annotated[Redis | None, Depends(get_identity_redis)]) -> SessionStatusCache:
    """FastAPI dependency that provides the cache of open sessions.

    Args:
        redis: Redis client, or `None`.

    Returns:
        The cache.
    """
    return SessionStatusCache(redis)


def client_ip(request: Request) -> str | None:
    """Address of the client, through the trusted proxies.

    Args:
        request: The incoming request.

    Returns:
        The address, or `None`.
    """
    return original_client_ip(request)


async def device_key(
    request: Request,
    installation: Annotated[Installation, Depends(current_installation)],
    redis: Annotated[Redis | None, Depends(get_identity_redis)],
    dpop: Annotated[str | None, Header(alias="DPoP", include_in_schema=False)] = None,
) -> str:
    """FastAPI dependency for requests without an access token yet (sign in, refresh).

    Args:
        request: The incoming request.
        installation: Installation of the request.
        redis: Where proof ids are remembered.
        dpop: The `DPoP` header.

    Returns:
        Thumbprint of the device key that signed the proof.

    Raises:
        InvalidDpopProofError: The proof is missing or not valid.
    """
    return await verify_proof(
        dpop, method=request.method, host=installation.host, path=request.url.path, redis=redis
    )


def device_info(
    request: Request,
    jkt: Annotated[str, Depends(device_key)],
    user_agent: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> DeviceInfo:
    """FastAPI dependency that describes the device signing in.

    Sign-in endpoints may replace the name with one the client sends (the app sends its model).

    Args:
        request: The incoming request.
        jkt: Thumbprint of the device key.
        user_agent: The `User-Agent` header.

    Returns:
        The device, named after its user agent.
    """
    return DeviceInfo(
        jkt=jkt, device_name=describe_device(user_agent), user_agent=user_agent, ip=client_ip(request)
    )


async def current_principal(
    request: Request,
    installation: Annotated[Installation, Depends(current_installation)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    redis: Annotated[Redis | None, Depends(get_identity_redis)],
    cache: Annotated[SessionStatusCache, Depends(get_session_cache)],
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
    dpop: Annotated[str | None, Header(alias="DPoP", include_in_schema=False)] = None,
) -> Principal:
    """FastAPI dependency that requires a signed-in user on the device that holds the token.

    Args:
        request: The incoming request.
        installation: Installation of the request; the token must be from it.
        session_factory: Factory of database sessions.
        redis: Where proof ids are remembered.
        cache: Cache of open sessions.
        authorization: The `Authorization` header.
        dpop: The `DPoP` header.

    Returns:
        The user of the request.

    Raises:
        AuthenticationRequiredError: No `Authorization` header.
        InvalidTokenError: Malformed, badly signed or from another installation.
        TokenExpiredError: The access token expired; the client refreshes it.
        InvalidDpopProofError: The proof is stale, replayed or for another request.
        TokenBindingMismatchError: The token was used without its device key; the session is closed.
        SessionRevokedError: The session is closed or expired.
    """
    if not authorization:
        raise AuthenticationRequiredError("Sign in to continue.")
    scheme, _, token = authorization.partition(" ")
    token = token.strip()
    if not token:
        raise InvalidTokenError("The access token is not valid.")

    if scheme.lower() != "dpop" or not dpop:
        # A signed token without its proof can only have been copied: close its session.
        claims = read_access_token(token, verify_expiry=False)
        await revoke_device_sessions(session_factory, cache, [claims.sid], RevocationReason.KEY_MISMATCH)
        raise TokenBindingMismatchError("The session was closed for security.")

    claims = read_access_token(token)
    if claims.iss != installation.host or claims.org != installation.organization_id:
        raise InvalidTokenError("The access token is not valid here.")

    jkt = await verify_proof(
        dpop,
        method=request.method,
        host=installation.host,
        path=request.url.path,
        redis=redis,
        access_token=token,
    )
    if jkt != claims.cnf.jkt:
        await revoke_device_sessions(session_factory, cache, [claims.sid], RevocationReason.KEY_MISMATCH)
        raise TokenBindingMismatchError("The session was closed for security.")

    await ensure_session_open(session_factory, cache, claims.sid)
    return Principal(
        user_id=claims.sub,
        organization_id=claims.org,
        session_id=claims.sid,
        email=claims.email,
        display_name=claims.name,
        expires_at=claims.exp,
    )


async def optional_principal(
    request: Request,
    installation: Annotated[Installation, Depends(current_installation)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    redis: Annotated[Redis | None, Depends(get_identity_redis)],
    cache: Annotated[SessionStatusCache, Depends(get_session_cache)],
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
    dpop: Annotated[str | None, Header(alias="DPoP", include_in_schema=False)] = None,
) -> Principal | None:
    """FastAPI dependency for endpoints that work with or without a session.

    Args:
        request: The incoming request.
        installation: Installation of the request.
        session_factory: Factory of database sessions.
        redis: Where proof ids are remembered.
        cache: Cache of open sessions.
        authorization: The `Authorization` header.
        dpop: The `DPoP` header.

    Returns:
        The user, or `None` if the request has no `Authorization` header. A header that is present
        but not valid fails as in `current_principal`.
    """
    if not authorization:
        return None
    return await current_principal(request, installation, session_factory, redis, cache, authorization, dpop)


async def installation_principal(
    request: Request,
    installation: Annotated[Installation, Depends(current_installation)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    redis: Annotated[Redis | None, Depends(get_identity_redis)],
    cache: Annotated[SessionStatusCache, Depends(get_session_cache)],
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
    dpop: Annotated[str | None, Header(alias="DPoP", include_in_schema=False)] = None,
) -> Principal | None:
    """FastAPI dependency for endpoints that are public on the main platform only.

    An organization's installation is closed: everything in it, searching included, needs a
    signed-in user of the organization. On the main platform the session is optional.

    Args:
        request: The incoming request.
        installation: Installation of the request.
        session_factory: Factory of database sessions.
        redis: Where proof ids are remembered.
        cache: Cache of open sessions.
        authorization: The `Authorization` header.
        dpop: The `DPoP` header.

    Returns:
        The user, or `None` on the main platform without an `Authorization` header.

    Raises:
        AuthenticationRequiredError: An organization's installation without an `Authorization` header.
    """
    if installation.organization_id is not None:
        return await current_principal(request, installation, session_factory, redis, cache, authorization, dpop)
    return await optional_principal(request, installation, session_factory, redis, cache, authorization, dpop)


def get_email_sender() -> EmailSender:
    """FastAPI dependency that provides the email sender of the environment (`EMAIL_BACKEND`).

    Tests override it with a sender that keeps the emails in memory.

    Returns:
        The sender.
    """
    return create_email_sender()


def get_password_hasher() -> PasswordHasher:
    """FastAPI dependency that provides the password hasher (Argon2id).

    Returns:
        The hasher.
    """
    return Argon2PasswordHasher()


def get_rate_limiter(redis: Annotated[Redis | None, Depends(get_identity_redis)]) -> RateLimiter:
    """FastAPI dependency that provides the attempt counters.

    Args:
        redis: Redis client, or `None` (no limits).

    Returns:
        The limiter.
    """
    return RateLimiter(redis)


def get_login_guard(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    redis: Annotated[Redis | None, Depends(get_identity_redis)],
) -> LoginGuard:
    """FastAPI dependency that provides the limits of failed password sign ins (device and address).

    Args:
        session_factory: Factory of database sessions (blocked addresses).
        redis: Redis client (counters), or `None`.

    Returns:
        The guard.
    """
    return LoginGuard(session_factory, redis)


def get_password_accounts(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    sender: Annotated[EmailSender, Depends(get_email_sender)],
    cache: Annotated[SessionStatusCache, Depends(get_session_cache)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    guard: Annotated[LoginGuard, Depends(get_login_guard)],
) -> PasswordAccounts:
    """FastAPI dependency that wires the email-and-password use cases.

    Args:
        session_factory: Factory of database sessions.
        hasher: Password hasher.
        sender: Email sender.
        cache: Cache of open sessions.
        limiter: Attempt counters.
        guard: Limits of failed password sign ins.

    Returns:
        The use cases.
    """
    return PasswordAccounts(
        session_factory,
        hasher=hasher,
        sender=sender,
        cache=cache,
        limiter=limiter,
        guard=guard,
        app_url=get_settings().app_url,
    )


def get_oidc_login(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    http: Annotated[httpx2.AsyncClient, Depends(get_http_client)],
    redis: Annotated[Redis | None, Depends(get_identity_redis)],
    sender: Annotated[EmailSender, Depends(get_email_sender)],
    cache: Annotated[SessionStatusCache, Depends(get_session_cache)],
) -> OidcLogin:
    """FastAPI dependency that wires sign in through OIDC providers.

    Args:
        session_factory: Factory of database sessions.
        http: Shared HTTP client; tests replace it with a fake provider.
        redis: Cache of discovery documents and keys.
        sender: Email sender.
        cache: Cache of open sessions.

    Returns:
        The use cases.
    """
    return OidcLogin(
        session_factory,
        client=OidcClient(http, redis),
        sender=sender,
        cache=cache,
        app_url=get_settings().app_url,
    )
