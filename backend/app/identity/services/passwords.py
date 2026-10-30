"""Sign in with email and password: lookup, sign up, verification, sign in and password links.

An installation whose organization turned passwords off has none of this (`PasswordLoginDisabledError`,
a 404 like any unknown route). Sign ups exist only in the main installation: organizations create
their users themselves (03-usuarios-y-acceso.md §9).

Every failed sign in answers the same `LoginFailedError`, whatever the reason; the reason is
logged. Wrong passwords block the account and too many failures block the address
(`services.login_guard`, §8.1).
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.identity.domain.constants.passwords import ATTEMPT_WINDOW, ATTEMPTS_PER_IP, EMAILS_PER_ADDRESS
from app.identity.domain.dtos.passwords import (
    AccountEmail,
    EmailTokenPurpose,
    LoginRequest,
    LookupResult,
    PasswordLinkInfo,
    SetPasswordRequest,
    SignupRequest,
)
from app.identity.domain.dtos.tokens import DeviceInfo, RevocationReason, TokenPair
from app.identity.domain.dtos.users import NewUser, UserStatus
from app.identity.domain.errors.passwords import InvalidLinkError, LoginFailedError, PasswordLoginDisabledError
from app.identity.domain.errors.users import UserAlreadyExistsError
from app.identity.providers.base import PasswordHasher
from app.identity.repositories.email_tokens import EmailTokenRepository
from app.identity.repositories.providers import ProviderRepository
from app.identity.repositories.users import UserRepository
from app.identity.services.account_links import (
    PendingEmail,
    issue_link,
    redeem_link,
    send_pending_email,
    welcome_email,
)
from app.identity.services.login_guard import LoginGuard, clear_lock, count_wrong_password, is_locked, login_failed
from app.identity.services.rate_limit import RateLimiter
from app.identity.services.sessions import SessionStatusCache, hash_secret, open_device_session, revoke_user_sessions
from app.notifications.public import EmailSender
from app.organizations.public import Installation

logger = logging.getLogger(__name__)


class PasswordAccounts:
    """Use cases of email-and-password accounts in one installation."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        hasher: PasswordHasher,
        sender: EmailSender,
        cache: SessionStatusCache,
        limiter: RateLimiter,
        guard: LoginGuard,
        app_url: str,
    ) -> None:
        """Initializes the use cases.

        Args:
            session_factory: Factory of database sessions.
            hasher: Password hasher.
            sender: Email sender of the environment.
            cache: Cache of open sessions.
            limiter: Attempt counters of sign ups and password emails.
            guard: Limits failed password sign ins per device and per address.
            app_url: Public URL of the main installation, for the links.
        """
        self._session_factory = session_factory
        self._hasher = hasher
        self._sender = sender
        self._cache = cache
        self._limiter = limiter
        self._guard = guard
        self._app_url = app_url

    @staticmethod
    def require_passwords(installation: Installation) -> None:
        """Fails if the installation doesn't accept passwords.

        Args:
            installation: Installation of the request.

        Raises:
            PasswordLoginDisabledError: Its organization turned passwords off.
        """
        if not installation.settings.password_login_enabled:
            raise PasswordLoginDisabledError("Not found.")

    async def lookup(self, installation: Installation, email: str, ip: str | None) -> LookupResult:
        """First step of the sign in: does the account exist, and can it use a password?

        Telling whether an email has an account is a cost the design accepts for the «no
        encontramos tu cuenta» flow. Unknown emails count against the address, so listing emails
        from one address ends up blocking it.

        Args:
            installation: Installation of the request.
            email: Email the person typed.
            ip: Address of the client.

        Returns:
            Whether the account exists and has a password.

        Raises:
            LoginFailedError: The address is blocked.
        """
        self.require_passwords(installation)
        await self._guard.ensure_allowed(installation, ip, email=email)
        async with self._session_factory() as session:
            user = await UserRepository(session).find_by_email(installation.organization_id, email)
            result = LookupResult(
                exists=user is not None and user.status == UserStatus.ACTIVE.value,
                has_password=user is not None and user.password is not None,
            )
        if not result.exists:
            await self._guard.record_failure(installation, ip, email=email)
        return result

    async def sign_up(self, installation: Installation, request: SignupRequest, ip: str | None) -> None:
        """Creates a private traveller's account and emails the link to verify it.

        An existing account that never verified its email is taken over by whoever verifies it
        now: whoever created it couldn't prove the email was theirs.

        Args:
            installation: Installation of the request; only the main one accepts sign ups.
            request: Email, name, password and the optional phone and language.
            ip: Address of the client.

        Raises:
            PasswordLoginDisabledError: An organization's installation.
            UserAlreadyExistsError: There is a verified account with that email.
        """
        if installation.organization is not None:
            raise PasswordLoginDisabledError("Not found.")
        await self._limiter.hit("email", request.email, limit=EMAILS_PER_ADDRESS, window=ATTEMPT_WINDOW)
        await self._limiter.hit("email-ip", ip or "-", limit=ATTEMPTS_PER_IP, window=ATTEMPT_WINDOW)
        async with self._session_factory() as session, session.begin():
            users = UserRepository(session)
            user = await users.find_by_email(None, request.email)
            if user is not None and user.email_verified_at is not None:
                raise UserAlreadyExistsError("There is already an account with that email.")
            if user is None:
                user = await users.add(
                    NewUser(
                        organization_id=None,
                        email=request.email,
                        display_name=request.display_name,
                        phone_number=request.phone_number,
                        language=request.language,
                    )
                )
            else:
                user.display_name = request.display_name
                user.phone_number = request.phone_number
                user.language = request.language
            await users.set_password_hash(user, self._hasher.hash(request.password))
            pending = await issue_link(
                session, user, AccountEmail.VERIFY_EMAIL, host=installation.host, organization_name=None
            )
        await send_pending_email(self._sender, pending, app_url=self._app_url)

    async def verify_email(self, installation: Installation, token: str, device: DeviceInfo) -> TokenPair:
        """Verifies the email of a new account, signs the device in and sends the welcome email.

        Args:
            installation: Installation of the request.
            token: Token of the link.
            device: Device that opened the link.

        Returns:
            Tokens of the new session.

        Raises:
            InvalidLinkError: The link is unknown, expired, used or from another installation.
        """
        welcome: PendingEmail | None = None
        async with self._session_factory() as session, session.begin():
            user, _ = await redeem_link(session, token, {EmailTokenPurpose.VERIFY_EMAIL})
            _same_installation(installation, user.organization_id)
            if user.email_verified_at is None:
                user.email_verified_at = datetime.now(UTC)
                welcome = welcome_email(
                    user,
                    host=installation.host,
                    organization_name=None,
                    provider_name=None,
                    password_email_follows=False,
                )
            tokens = await open_device_session(
                session, self._cache, user=user, issuer=installation.host, device=device
            )
        if welcome is not None:
            await send_pending_email(self._sender, welcome, app_url=self._app_url)
        return tokens

    async def sign_in(self, installation: Installation, request: LoginRequest, device: DeviceInfo) -> TokenPair:
        """Signs a device in with email and password.

        Wrong passwords count against the account: at `max_failed_logins` (setting of the
        installation) the password sign in is blocked for `login_lock_minutes` and the user gets
        an email to change it, which unblocks it. Every failure also counts against the device and
        the address (`LoginGuard`).

        Args:
            installation: Installation of the request.
            request: Email and password.
            device: Device signing in.

        Returns:
            Tokens of the new session.

        Raises:
            PasswordLoginDisabledError: The installation doesn't accept passwords.
            LoginFailedError: For any reason the sign in didn't succeed; the reason is only logged.
        """
        self.require_passwords(installation)
        ip, email = device.ip, request.email
        await self._guard.ensure_allowed(installation, ip, jkt=device.jkt, email=email)
        failure: LoginFailedError | None = None
        lock_email: PendingEmail | None = None
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            users = UserRepository(session)
            user = await users.find_by_email(installation.organization_id, email)
            if user is None:
                # Hash anyway, so a missing account takes as long as a wrong password.
                self._hasher.hash(request.password)
                failure = login_failed("unknown_email", ip=ip, email=email)
            elif user.status != UserStatus.ACTIVE.value:
                failure = login_failed("account_disabled", ip=ip, email=email, user=user.id)
            elif user.password is None:
                failure = login_failed("password_not_set", ip=ip, email=email, user=user.id)
            elif is_locked(user, now):
                failure = login_failed("account_locked", ip=ip, email=email, user=user.id)
            else:
                if user.locked_until is not None:
                    clear_lock(user)  # the lock expired
                matches, upgraded = self._hasher.verify(request.password, user.password.password_hash)
                if not matches:
                    if count_wrong_password(user, installation.settings, now):
                        lock_email = await issue_link(
                            session,
                            user,
                            AccountEmail.ACCOUNT_LOCKED,
                            host=installation.host,
                            organization_name=installation.organization.name if installation.organization else None,
                            lock_minutes=installation.settings.login_lock_minutes,
                        )
                    failure = login_failed(
                        "wrong_password", ip=ip, email=email, user=user.id, attempts=user.failed_login_attempts
                    )
                else:
                    clear_lock(user)
                    if upgraded is not None:
                        await users.set_password_hash(user, upgraded)
                    if user.email_verified_at is None:
                        failure = login_failed("email_not_verified", ip=ip, email=email, user=user.id)
                    else:
                        return await open_device_session(
                            session, self._cache, user=user, issuer=installation.host, device=device
                        )
        # The counters and the lock are saved; now the request fails.
        if lock_email is not None:
            await send_pending_email(self._sender, lock_email, app_url=self._app_url)
        await self._guard.record_failure(installation, ip, jkt=device.jkt, email=email)
        raise failure

    async def forgot_password(self, installation: Installation, email: str, ip: str | None) -> None:
        """Emails a link to choose a new password; says nothing about whether the account exists.

        An account without a password (created by SSO or by its organization) gets the link to set
        its first one instead.

        Args:
            installation: Installation of the request.
            email: Email of the account.
            ip: Address of the client.
        """
        self.require_passwords(installation)
        await self._limiter.hit("email", email, limit=EMAILS_PER_ADDRESS, window=ATTEMPT_WINDOW)
        await self._limiter.hit("email-ip", ip or "-", limit=ATTEMPTS_PER_IP, window=ATTEMPT_WINDOW)
        pending: PendingEmail | None = None
        async with self._session_factory() as session, session.begin():
            user = await UserRepository(session).find_by_email(installation.organization_id, email)
            if user is not None and user.status == UserStatus.ACTIVE.value:
                kind = AccountEmail.RESET_PASSWORD if user.password else AccountEmail.SET_PASSWORD
                pending = await issue_link(
                    session,
                    user,
                    kind,
                    host=installation.host,
                    organization_name=installation.organization.name if installation.organization else None,
                )
        if pending is not None:
            await send_pending_email(self._sender, pending, app_url=self._app_url)

    async def link_info(self, installation: Installation, token: str) -> PasswordLinkInfo:
        """What a password link is for, without using it: the screen shows the account and the kind.

        Args:
            installation: Installation of the request.
            token: Token of the link.

        Returns:
            The email of the account, whether the link sets the first password or resets it, and what
            else the account signs in with.

        Raises:
            PasswordLoginDisabledError: The installation doesn't accept passwords.
            InvalidLinkError: The link is unknown, expired, used or from another installation.
        """
        self.require_passwords(installation)
        purposes = {EmailTokenPurpose.SET_PASSWORD.value, EmailTokenPurpose.RESET_PASSWORD.value}
        async with self._session_factory() as session:
            link = await EmailTokenRepository(session).get(hash_secret(token))
            if link is None or link.purpose not in purposes or link.used_at is not None:
                raise InvalidLinkError("The link is not valid anymore. Ask for a new one.")
            if link.expires_at <= datetime.now(UTC):
                raise InvalidLinkError("The link expired. Ask for a new one.")
            users = UserRepository(session)
            user = await users.get(link.user_id)
            if user is None:
                raise InvalidLinkError("The link is not valid anymore. Ask for a new one.")
            _same_installation(installation, user.organization_id)
            signs_in_with = None
            for key in await users.provider_keys(user.id):
                provider = await ProviderRepository(session).get(uuid.UUID(key))
                if provider is not None:
                    signs_in_with = provider.display_name
                    break
            if signs_in_with is None and installation.organization is not None:
                signs_in_with = f"el SSO de {installation.organization.name}"
            kind = "set" if link.purpose == EmailTokenPurpose.SET_PASSWORD.value else "reset"
            return PasswordLinkInfo(email=user.email, kind=kind, signs_in_with=signs_in_with)

    async def set_password(self, installation: Installation, request: SetPasswordRequest) -> None:
        """Sets the first password, or a new one after forgetting it, from an email link.

        Opening the link proves the email, so it also counts as verified, and it unblocks an account
        locked by wrong passwords. Resetting a forgotten password closes every session of the user.

        Args:
            installation: Installation of the request.
            request: Token of the link and the new password.

        Raises:
            PasswordLoginDisabledError: The installation doesn't accept passwords.
            InvalidLinkError: The link is unknown, expired, used or from another installation.
        """
        self.require_passwords(installation)
        async with self._session_factory() as session, session.begin():
            user, purpose = await redeem_link(
                session, request.token, {EmailTokenPurpose.SET_PASSWORD, EmailTokenPurpose.RESET_PASSWORD}
            )
            _same_installation(installation, user.organization_id)
            await UserRepository(session).set_password_hash(user, self._hasher.hash(request.password))
            clear_lock(user)
            if user.email_verified_at is None:
                user.email_verified_at = datetime.now(UTC)
            if purpose is EmailTokenPurpose.RESET_PASSWORD:
                await revoke_user_sessions(session, self._cache, user.id, RevocationReason.PASSWORD_CHANGED)


def _same_installation(installation: Installation, organization_id: uuid.UUID | None) -> None:
    """Fails if a link of one installation is opened in another."""
    if installation.organization_id != organization_id:
        raise InvalidLinkError("The link is not valid here.")
