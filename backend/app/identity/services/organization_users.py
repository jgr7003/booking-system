"""Organizations giving people access to their installation."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.dtos.passwords import AccountEmail
from app.identity.domain.dtos.users import Language, NewUser
from app.identity.domain.models.users import User
from app.identity.services.account_links import PendingEmail, issue_link, welcome_email
from app.identity.services.users import create_user
from app.organizations.public import OrganizationRef


async def give_access(
    session: AsyncSession,
    organization: OrganizationRef,
    *,
    email: str,
    display_name: str,
    phone_number: str | None = None,
    language: Language | None = None,
) -> tuple[User, list[PendingEmail]]:
    """Creates a user of an organization, inside the caller's transaction.

    The organization vouches for the email, so it's created as verified and without a password:
    the person signs in with the organization's identity provider. If the organization accepts
    passwords, they also get an email to create one. Send the emails after the commit.

    Args:
        session: Session of the caller's transaction.
        organization: The organization.
        email: Email of the person.
        display_name: Name shown in the interface.
        phone_number: Phone number in E.164 format, optional.
        language: Language of the person; `None` lets the app decide.

    Returns:
        The new user and the emails to send: the welcome and, if passwords are allowed, the one to
        create a password.

    Raises:
        UserAlreadyExistsError: The organization already has a user with that email.
    """
    new = NewUser(
        organization_id=organization.id,
        email=email,
        display_name=display_name,
        email_verified=True,
        phone_number=phone_number,
        language=language,
    )
    user = await create_user(session, new)
    host = organization.hostnames[0]
    allows_password = organization.settings.password_login_enabled
    emails = [
        welcome_email(
            user,
            host=host,
            organization_name=organization.name,
            provider_name=None,
            password_email_follows=allows_password,
        )
    ]
    if allows_password:
        emails.append(
            await issue_link(
                session, user, AccountEmail.SET_PASSWORD, host=host, organization_name=organization.name
            )
        )
    return user, emails
