"""Test helpers of the identity module: device keys, DPoP proofs and ready-made sessions.

Tests of other modules may import this file (the only exception to `public.py`, declared in
`pyproject.toml`), so they authenticate exactly as a real device does.
"""

import re
import time
import uuid
from typing import Any

from joserfc import jwt
from joserfc.jwk import ECKey
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.identity.core.config import get_identity_settings
from app.identity.domain.dtos.tokens import DeviceInfo, TokenPair
from app.identity.domain.dtos.users import NewUser
from app.identity.domain.models.users import User
from app.identity.repositories.users import UserRepository
from app.identity.services.sessions import SessionStatusCache, open_device_session
from app.identity.services.users import create_user
from app.identity.tokens.dpop import token_hash
from app.identity.tokens.signing import generate_signing_key
from app.notifications.public import EmailMessage

__all__ = [
    "DeviceKey",
    "RecordingEmailSender",
    "TestSession",
    "generate_signing_key",
    "reload_identity_settings",
    "sign_in",
]


class DeviceKey:
    """The key pair of a fake device, which signs DPoP proofs like a browser would."""

    def __init__(self) -> None:
        """Creates a new P-256 key pair."""
        self._key = ECKey.generate_key("P-256", private=True)

    @property
    def jkt(self) -> str:
        """Thumbprint of the public key."""
        return self._key.thumbprint()

    def proof(
        self,
        method: str,
        url: str,
        access_token: str | None = None,
        **overrides: Any,
    ) -> str:
        """Signs a DPoP proof for a request.

        Args:
            method: HTTP method.
            url: Full URL, e.g. `http://test/api/v1/me`.
            access_token: Access token sent with the request, if any (adds `ath`).
            **overrides: Claims to replace, to build broken proofs.

        Returns:
            The proof, for the `DPoP` header.
        """
        claims: dict[str, Any] = {"htm": method, "htu": url, "iat": int(time.time()), "jti": str(uuid.uuid4())}
        if access_token is not None:
            claims["ath"] = token_hash(access_token)
        claims.update(overrides)
        header = {"typ": "dpop+jwt", "alg": "ES256", "jwk": self._key.as_dict(private=False)}
        return jwt.encode(header, claims, self._key)

    def headers(self, method: str, url: str, access_token: str | None = None) -> dict[str, str]:
        """Headers of an authenticated request (or of a sign in, without a token).

        Args:
            method: HTTP method.
            url: Full URL.
            access_token: Access token, if any.

        Returns:
            `DPoP`, and `Authorization` when there is a token.
        """
        headers = {"DPoP": self.proof(method, url, access_token)}
        if access_token is not None:
            headers["Authorization"] = f"DPoP {access_token}"
        return headers


class TestSession:
    """A user signed in on a fake device."""

    __test__ = False

    def __init__(self, user: User, device: DeviceKey, tokens: TokenPair, base_url: str) -> None:
        """Initializes the session.

        Args:
            user: The user.
            device: Their device.
            tokens: The tokens of the session.
            base_url: Base URL of the installation, e.g. `http://test`.
        """
        self.user = user
        self.device = device
        self.tokens = tokens
        self.base_url = base_url

    def headers(self, method: str, path: str) -> dict[str, str]:
        """Headers of an authenticated request of this device.

        Args:
            method: HTTP method.
            path: Path, e.g. `/api/v1/me`.

        Returns:
            `Authorization` and `DPoP`.
        """
        return self.device.headers(method, f"{self.base_url}{path}", self.tokens.access_token)

    async def sign_request(self, request: Any) -> None:
        """Request hook of an HTTP test client: signs every request as this device.

        Use it as `httpx2.AsyncClient(..., event_hooks={"request": [session.sign_request]})`.

        Args:
            request: The outgoing request.
        """
        request.headers.update(self.headers(request.method, request.url.path))


async def sign_in(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str = "ana@example.test",
    organization_id: uuid.UUID | None = None,
    host: str = "test",
    base_url: str = "http://test",
    device_name: str = "Chrome en Windows",
) -> TestSession:
    """Creates a user (or reuses it) and opens a session on a new fake device.

    Args:
        session_factory: Factory of sessions on the test database.
        email: Email of the user.
        organization_id: Organization of the user; `None` for a private traveller.
        host: Host of the installation (the issuer of the token).
        base_url: Base URL the test client uses, for the `htu` of the proofs.
        device_name: Name of the device.

    Returns:
        The signed-in session.
    """
    device = DeviceKey()
    async with session_factory() as session, session.begin():
        user = await UserRepository(session).find_by_email(organization_id, email)
        if user is None:
            user = await create_user(
                session,
                NewUser(organization_id=organization_id, email=email, display_name="Ana Prueba", email_verified=True),
            )
        tokens = await open_device_session(
            session,
            SessionStatusCache(None),
            user=user,
            issuer=host,
            device=DeviceInfo(jkt=device.jkt, device_name=device_name),
        )
    return TestSession(user, device, tokens, base_url)


class RecordingEmailSender:
    """Email sender that keeps the emails in memory, to read the links tests need."""

    def __init__(self) -> None:
        """Starts with no emails."""
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        """Keeps an email.

        Args:
            message: The email.
        """
        self.sent.append(message)

    def last_token(self, to: str) -> str:
        """Token of the link in the last email with a link sent to an address.

        Args:
            to: Recipient.

        Returns:
            The `token` query parameter of its link.
        """
        message = next(m for m in reversed(self.sent) if m.to == to and "token=" in m.text)
        return re.search(r"token=([\w-]+)", message.text).group(1)


def reload_identity_settings() -> None:
    """Reloads the identity settings after a test changed their environment variables."""
    get_identity_settings.cache_clear()
