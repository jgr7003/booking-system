"""Sign in through an OIDC provider, and the «no encontramos tu cuenta» decision.

1. `start`: creates the attempt (PKCE verifier, `state`, `nonce`), bound to the device key, and
   returns the provider's URL.
2. `finish`: with the `code` and `state` of the redirect, exchanges the code, checks the id_token
   and finds the account: by the linked identity, then by verified email. Without an account, the
   verified identity waits in the attempt.
3. `create_account` / `discard`: the person creates the account (private travellers only) or tries
   another one.

Attempts are bound to the key of the device that started them: only that device can finish them,
which stops login CSRF the way a cookie would (03-usuarios-y-acceso.md §7 and §9).
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.identity.core.config import get_identity_settings
from app.identity.domain.dtos.oidc import (
    AccountNotFound,
    LoginAttemptStatus,
    ProviderConfig,
    SignedIn,
    SignupDecision,
    VerifiedIdentity,
)
from app.identity.domain.dtos.passwords import AccountEmail
from app.identity.domain.dtos.tokens import DeviceInfo
from app.identity.domain.dtos.users import NewUser, UserStatus
from app.identity.domain.errors.oidc import (
    IdentityProviderError,
    InvalidIdentityError,
    InvalidLoginAttemptError,
    SignupNotAllowedError,
    UnknownProviderError,
)
from app.identity.domain.models.providers import IdentityProvider, LoginAttempt
from app.identity.domain.models.users import User
from app.identity.notifications.account_emails import installation_url
from app.identity.providers.oidc.client import OidcClient, new_pkce_pair
from app.identity.repositories.providers import ProviderRepository
from app.identity.repositories.users import UserRepository
from app.identity.services.account_links import issue_link, send_pending_email, welcome_email
from app.identity.services.login_guard import login_failed
from app.identity.services.secrets import decrypt_secret
from app.identity.services.sessions import SessionStatusCache, open_device_session
from app.notifications.public import EmailSender
from app.organizations.public import Installation

logger = logging.getLogger(__name__)

# Path of the web app where providers send the browser back.
CALLBACK_PATH = "/auth/callback"


def to_provider_config(provider: IdentityProvider) -> ProviderConfig:
    """A provider ready to use, with its secret decrypted.

    Args:
        provider: The stored provider.

    Returns:
        Its configuration.
    """
    return ProviderConfig(
        id=provider.id,
        slug=provider.slug,
        display_name=provider.display_name,
        issuer=provider.issuer,
        backchannel_base_url=provider.backchannel_base_url,
        client_id=provider.client_id,
        client_secret=decrypt_secret(provider.client_secret_encrypted),
        scopes=provider.scopes,
        trust_email=provider.trust_email,
        extra_authorize_params=provider.extra_authorize_params,
    )


class OidcLogin:
    """Use cases of sign in through the OIDC providers of an installation."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        client: OidcClient,
        sender: EmailSender,
        cache: SessionStatusCache,
        app_url: str,
    ) -> None:
        """Initializes the use cases.

        Args:
            session_factory: Factory of database sessions.
            client: OIDC client.
            sender: Email sender of the environment.
            cache: Cache of open sessions.
            app_url: Public URL of the main installation, for the redirect URI and links.
        """
        self._session_factory = session_factory
        self._client = client
        self._sender = sender
        self._cache = cache
        self._app_url = app_url

    def _redirect_uri(self, installation: Installation) -> str:
        """Where the provider sends the browser back: a page of this installation's web app.

        It's built here, never taken from the request, so the code can't be sent anywhere else.
        """
        return installation_url(self._app_url, installation.host) + CALLBACK_PATH

    async def _provider(self, session: AsyncSession, installation: Installation, slug: str) -> IdentityProvider:
        """An enabled provider of the installation."""
        provider = await ProviderRepository(session).find_enabled(installation.organization_id, slug)
        if provider is None:
            raise UnknownProviderError("There is no such identity provider here.")
        return provider

    async def start(
        self, installation: Installation, slug: str, *, return_to: str | None, jkt: str, another_account: bool = False
    ) -> str:
        """Starts a sign in through a provider.

        Args:
            installation: Installation of the request.
            slug: Provider name in the URL.
            return_to: Path of the app to go back to afterwards.
            jkt: Thumbprint of the key of the device that starts it.
            another_account: Ask the provider to sign in again instead of reusing its session.

        Returns:
            URL of the provider for the browser to open.

        Raises:
            UnknownProviderError: The installation has no such enabled provider.
            IdentityProviderError: The provider didn't answer.
        """
        verifier, challenge = new_pkce_pair()
        state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            provider = await self._provider(session, installation, slug)
            config = to_provider_config(provider)
            repository = ProviderRepository(session)
            await repository.delete_expired_attempts(now)
            await repository.add_attempt(
                LoginAttempt(
                    id=uuid.uuid4(),
                    state=state,
                    organization_id=installation.organization_id,
                    provider_id=provider.id,
                    nonce=nonce,
                    code_verifier=verifier,
                    dpop_jkt=jkt,
                    redirect_uri=self._redirect_uri(installation),
                    return_to=return_to,
                    status=LoginAttemptStatus.STARTED.value,
                    expires_at=now + timedelta(seconds=get_identity_settings().login_attempt_ttl_s),
                )
            )
        return await self._client.authorization_url(
            config,
            redirect_uri=self._redirect_uri(installation),
            state=state,
            nonce=nonce,
            code_challenge=challenge,
            prompt="login" if another_account else None,
        )

    async def finish(
        self, installation: Installation, slug: str, *, code: str, state: str, device: DeviceInfo
    ) -> SignedIn | AccountNotFound:
        """Finishes a sign in with what the provider sent back.

        The attempt is used up before calling the provider, so a replayed callback fails even if
        the first one is still running. Every failure answers the same `LoginFailedError`; the reason
        is only logged. The address isn't limited here: the organization's provider vouches for its
        people with its own protections (password, MFA, policies), and nothing can be guessed
        through this step (random `state`, single-use `code`, PKCE).

        Args:
            installation: Installation of the request.
            slug: Provider name in the URL.
            code: Authorization code.
            state: `state` from the redirect.
            device: Device finishing the sign in; it must be the one that started it.

        Returns:
            The new session, or the identity waiting for the «create account» decision.

        Raises:
            LoginFailedError: Unknown, expired or used `state`, another device, a provider that
                refused the code or didn't answer, an id_token that didn't pass the checks, an
                unverified email or a disabled account.
        """
        try:
            return await self._finish(installation, slug, code=code, state=state, device=device)
        except (InvalidLoginAttemptError, IdentityProviderError, InvalidIdentityError) as exc:
            raise login_failed(exc.code, ip=device.ip, provider=slug, detail=exc.message) from exc

    async def _finish(
        self, installation: Installation, slug: str, *, code: str, state: str, device: DeviceInfo
    ) -> SignedIn | AccountNotFound:
        """`finish` without hiding the reason of a failure."""
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            repository = ProviderRepository(session)
            attempt = await repository.attempt_by_state_for_update(state)
            provider = await repository.find_enabled(installation.organization_id, slug)
            if (
                attempt is None
                or provider is None
                or attempt.provider_id != provider.id
                or attempt.organization_id != installation.organization_id
                or attempt.status != LoginAttemptStatus.STARTED.value
                or attempt.expires_at <= now
                or attempt.dpop_jkt != device.jkt
            ):
                raise InvalidLoginAttemptError("The sign in expired or isn't valid. Start it again.")
            attempt.status = LoginAttemptStatus.EXCHANGING.value
            config = to_provider_config(provider)
            nonce, verifier, redirect_uri = attempt.nonce, attempt.code_verifier, attempt.redirect_uri
            attempt_id, return_to = attempt.id, attempt.return_to

        id_token = await self._client.exchange_code(
            config, code=code, code_verifier=verifier, redirect_uri=redirect_uri
        )
        identity = await self._client.verify_id_token(config, id_token, nonce=nonce)

        async with self._session_factory() as session, session.begin():
            repository = ProviderRepository(session)
            attempt = await repository.attempt_for_update(attempt_id)
            user = await self._find_user(session, installation, config, identity)
            if user is not None:
                await repository.delete_attempt(attempt)
                tokens = await open_device_session(
                    session, self._cache, user=user, issuer=installation.host, device=device
                )
                return SignedIn(tokens=tokens, return_to=return_to)
            attempt.status = LoginAttemptStatus.AWAITING_SIGNUP.value
            attempt.verified_identity = identity.model_dump()
            attempt.expires_at = now + timedelta(seconds=get_identity_settings().login_attempt_ttl_s)
        return AccountNotFound(
            attempt_id=attempt_id,
            email=identity.email,
            display_name=identity.display_name,
            can_create=installation.organization is None,
        )

    async def _find_user(
        self, session: AsyncSession, installation: Installation, provider: ProviderConfig, identity: VerifiedIdentity
    ) -> User | None:
        """The account of a verified identity in the installation, linking the identity if needed.

        First by the linked identity (`sub` is stable, the email may change); then by an account
        with the same email that is already verified. An unverified account is never linked: whoever
        created it didn't prove the email was theirs.
        """
        users = UserRepository(session)
        user = await users.find_by_identity(str(provider.id), identity.subject)
        if user is None:
            user = await users.find_by_email(installation.organization_id, identity.email)
            if user is None or user.email_verified_at is None:
                return None
            await users.link_identity(user.id, str(provider.id), identity.subject)
        if user.organization_id != installation.organization_id or user.status != UserStatus.ACTIVE.value:
            raise InvalidIdentityError("This account can't sign in here.")
        return user

    async def _pending(
        self, session: AsyncSession, installation: Installation, attempt_id: uuid.UUID, jkt: str
    ) -> LoginAttempt:
        """An attempt waiting for the «create account» decision of this device."""
        attempt = await ProviderRepository(session).attempt_for_update(attempt_id)
        if (
            attempt is None
            or attempt.status != LoginAttemptStatus.AWAITING_SIGNUP.value
            or attempt.organization_id != installation.organization_id
            or attempt.expires_at <= datetime.now(UTC)
            or attempt.dpop_jkt != jkt
        ):
            raise InvalidLoginAttemptError("The sign in expired or isn't valid. Start it again.")
        return attempt

    async def pending_identity(self, installation: Installation, attempt_id: uuid.UUID, jkt: str) -> AccountNotFound:
        """The identity waiting for the decision, to show it again (for example after a reload).

        Args:
            installation: Installation of the request.
            attempt_id: The attempt.
            jkt: Thumbprint of the device key; it must be the device that signed in.

        Returns:
            The identity and whether an account can be created.

        Raises:
            InvalidLoginAttemptError: Unknown, expired or of another device.
        """
        async with self._session_factory() as session, session.begin():
            attempt = await self._pending(session, installation, attempt_id, jkt)
            identity = VerifiedIdentity.model_validate(attempt.verified_identity)
        return AccountNotFound(
            attempt_id=attempt_id,
            email=identity.email,
            display_name=identity.display_name,
            can_create=installation.organization is None,
        )

    async def create_account(
        self, installation: Installation, attempt_id: uuid.UUID, device: DeviceInfo, decision: SignupDecision
    ) -> SignedIn:
        """«Crear cuenta»: creates a private traveller with what the provider verified, and signs in.

        The account starts with minimal data and no password. The person gets the welcome email and,
        right after, the one to create a password (optional).
        An unverified account with the same email (somebody who never proved it was theirs) is
        replaced.

        Args:
            installation: Installation of the request; only the main one.
            attempt_id: The attempt waiting for the decision.
            device: Device that signed in through the provider.
            decision: Optional data the person added: phone and language.

        Returns:
            The new session.

        Raises:
            SignupNotAllowedError: An organization's installation.
            InvalidLoginAttemptError: Unknown, expired or of another device.
        """
        if installation.organization is not None:
            raise SignupNotAllowedError("Ask your organization for access.")
        async with self._session_factory() as session, session.begin():
            attempt = await self._pending(session, installation, attempt_id, device.jkt)
            identity = VerifiedIdentity.model_validate(attempt.verified_identity)
            provider = await ProviderRepository(session).get(attempt.provider_id)
            users = UserRepository(session)
            unverified = await users.find_by_email(None, identity.email)
            if unverified is not None:
                if unverified.email_verified_at is not None:
                    raise InvalidLoginAttemptError("The sign in expired or isn't valid. Start it again.")
                await users.delete(unverified)
            user = await users.add(
                NewUser(
                    organization_id=None,
                    email=identity.email,
                    display_name=identity.display_name or identity.email,
                    email_verified=True,
                    phone_number=decision.phone_number,
                    language=decision.language,
                )
            )
            await users.link_identity(user.id, str(provider.id), identity.subject)
            emails = [
                welcome_email(
                    user,
                    host=installation.host,
                    organization_name=None,
                    provider_name=provider.display_name,
                    password_email_follows=True,
                ),
                await issue_link(
                    session,
                    user,
                    AccountEmail.SET_PASSWORD,
                    host=installation.host,
                    organization_name=None,
                    provider_name=provider.display_name,
                ),
            ]
            return_to = attempt.return_to
            await ProviderRepository(session).delete_attempt(attempt)
            tokens = await open_device_session(
                session, self._cache, user=user, issuer=installation.host, device=device
            )
        for email in emails:
            await send_pending_email(self._sender, email, app_url=self._app_url)
        return SignedIn(tokens=tokens, return_to=return_to)

    async def discard(self, installation: Installation, attempt_id: uuid.UUID, jkt: str) -> None:
        """«Usar otra cuenta»: forgets the identity waiting for the decision.

        Args:
            installation: Installation of the request.
            attempt_id: The attempt.
            jkt: Thumbprint of the device key.

        Raises:
            InvalidLoginAttemptError: Unknown, expired or of another device.
        """
        async with self._session_factory() as session, session.begin():
            attempt = await self._pending(session, installation, attempt_id, jkt)
            await ProviderRepository(session).delete_attempt(attempt)

    async def providers(self, installation: Installation) -> list[tuple[str, str]]:
        """Providers shown on the sign-in screen of the installation.

        Args:
            installation: Installation of the request.

        Returns:
            `(slug, display_name)` of each enabled provider.
        """
        async with self._session_factory() as session:
            providers = await ProviderRepository(session).list_enabled(installation.organization_id)
        return [(p.slug, p.display_name) for p in providers]
