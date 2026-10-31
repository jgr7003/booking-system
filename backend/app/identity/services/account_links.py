"""Single-use links sent by email: creating them, emailing them and redeeming them."""

import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.constants.passwords import RESET_PASSWORD_TTL, SET_PASSWORD_TTL, VERIFY_EMAIL_TTL
from app.identity.domain.dtos.passwords import AccountEmail, EmailTokenPurpose
from app.identity.domain.errors.passwords import InvalidLinkError
from app.identity.domain.models.users import User
from app.identity.notifications.account_emails import installation_url, render_link_email, render_welcome_email
from app.identity.repositories.email_tokens import EmailTokenRepository
from app.identity.repositories.users import UserRepository
from app.identity.services.sessions import hash_secret
from app.notifications.public import EmailDeliveryError, EmailSender

logger = logging.getLogger(__name__)

# Lifetime of each kind of link.
LINK_TTL = {
    EmailTokenPurpose.VERIFY_EMAIL: VERIFY_EMAIL_TTL,
    EmailTokenPurpose.SET_PASSWORD: SET_PASSWORD_TTL,
    EmailTokenPurpose.RESET_PASSWORD: RESET_PASSWORD_TTL,
}

# Link each kind of email carries: the account-locked email offers to change the password.
LINK_PURPOSE = {
    AccountEmail.VERIFY_EMAIL: EmailTokenPurpose.VERIFY_EMAIL,
    AccountEmail.SET_PASSWORD: EmailTokenPurpose.SET_PASSWORD,
    AccountEmail.RESET_PASSWORD: EmailTokenPurpose.RESET_PASSWORD,
    AccountEmail.ACCOUNT_LOCKED: EmailTokenPurpose.RESET_PASSWORD,
}


@dataclass(frozen=True)
class PendingEmail:
    """An account email to send once the transaction that saved its link commits."""

    # Which email.
    kind: AccountEmail

    # Recipient.
    to: str

    # Display name of the user.
    name: str

    # The token of the link; it exists in clear only here and in the email. `None` for the welcome.
    token: str | None

    # Host of the user's installation, for the link.
    host: str

    # Organization of the user, if any.
    organization_name: str | None

    # Identity provider the account was created with, if any.
    provider_name: str | None = None

    # How long the password sign in stays blocked, for the account-locked email.
    lock_minutes: int | None = None

    # Welcome only: whether the email to create a password follows it.
    password_email_follows: bool = False


async def issue_link(
    session: AsyncSession,
    user: User,
    kind: AccountEmail,
    *,
    host: str,
    organization_name: str | None,
    provider_name: str | None = None,
    lock_minutes: int | None = None,
) -> PendingEmail:
    """Creates a link inside the caller's transaction; earlier unused links of its kind stop working.

    Args:
        session: Session of the caller's transaction.
        user: The user.
        kind: Which email; it decides the link it carries.
        host: Host of the user's installation.
        organization_name: Organization of the user, if any.
        provider_name: Identity provider the account was created with, if any.
        lock_minutes: How long the password sign in stays blocked (account-locked email).

    Returns:
        The email to send after the commit.
    """
    now = datetime.now(UTC)
    purpose = LINK_PURPOSE[kind]
    repository = EmailTokenRepository(session)
    # Setting and resetting the password share the screen: a new link of either kind replaces both.
    kinds = [purpose.value]
    if purpose is not EmailTokenPurpose.VERIFY_EMAIL:
        kinds = [EmailTokenPurpose.SET_PASSWORD.value, EmailTokenPurpose.RESET_PASSWORD.value]
    await repository.expire_unused(user.id, kinds, now)
    token = secrets.token_urlsafe(32)
    await repository.add(hash_secret(token), user.id, purpose.value, now + LINK_TTL[purpose])
    return PendingEmail(
        kind=kind,
        to=user.email,
        name=user.display_name,
        token=token,
        host=host,
        organization_name=organization_name,
        provider_name=provider_name,
        lock_minutes=lock_minutes,
    )


async def send_pending_email(sender: EmailSender, pending: PendingEmail, *, app_url: str) -> bool:
    """Sends an account email. A failure is logged, not raised: the user can ask for another one.

    Args:
        sender: Email sender of the environment.
        pending: The email.
        app_url: Public URL of the main installation, for the scheme and port of the link.

    Returns:
        Whether the server took the email.
    """
    base_url = installation_url(app_url, pending.host)
    if pending.kind is AccountEmail.WELCOME:
        message = render_welcome_email(
            to=pending.to,
            name=pending.name,
            base_url=base_url,
            organization_name=pending.organization_name,
            provider_name=pending.provider_name,
            password_email_follows=pending.password_email_follows,
        )
    else:
        message = render_link_email(
            kind=pending.kind,
            to=pending.to,
            name=pending.name,
            token=pending.token or "",
            ttl=LINK_TTL[LINK_PURPOSE[pending.kind]],
            base_url=base_url,
            organization_name=pending.organization_name,
            provider_name=pending.provider_name,
            lock_minutes=pending.lock_minutes,
        )
    try:
        await sender.send(message)
    except EmailDeliveryError as exc:
        logger.error("Account email (%s) couldn't be sent: %s", pending.kind.value, exc)
        return False
    return True


async def redeem_link(
    session: AsyncSession, token: str, purposes: set[EmailTokenPurpose]
) -> tuple[User, EmailTokenPurpose]:
    """Uses a link, inside the caller's transaction.

    Args:
        session: Session of the caller's transaction.
        token: The token from the link.
        purposes: Kinds of link accepted here.

    Returns:
        The user of the link and its purpose.

    Raises:
        InvalidLinkError: Unknown, of another kind, expired or already used, or its user is gone.
    """
    now = datetime.now(UTC)
    link = await EmailTokenRepository(session).get_for_update(hash_secret(token))
    if link is None or EmailTokenPurpose(link.purpose) not in purposes or link.used_at is not None:
        raise InvalidLinkError("The link is not valid anymore. Ask for a new one.")
    if link.expires_at <= now:
        raise InvalidLinkError("The link expired. Ask for a new one.")
    user = await UserRepository(session).get(link.user_id)
    if user is None:
        raise InvalidLinkError("The link is not valid anymore. Ask for a new one.")
    link.used_at = now
    return user, EmailTokenPurpose(link.purpose)



def welcome_email(
    user: User,
    *,
    host: str,
    organization_name: str | None,
    provider_name: str | None,
    password_email_follows: bool,
) -> PendingEmail:
    """The welcome email of a new account, to send after the commit.

    Args:
        user: The new user.
        host: Host of the user's installation.
        organization_name: Organization of the user, if any.
        provider_name: Identity provider the account was created with; `None` if the email was verified.
        password_email_follows: Whether the email to create a password is sent right after.

    Returns:
        The email.
    """
    return PendingEmail(
        kind=AccountEmail.WELCOME,
        to=user.email,
        name=user.display_name,
        token=None,
        host=host,
        organization_name=organization_name,
        provider_name=provider_name,
        password_email_follows=password_email_follows,
    )
