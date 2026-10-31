"""Gives a person access to an organization's installation.

Until organizations have their administration panel, their users are created from the command
line. The user needs no password: they sign in with the organization's identity provider, or
set a password from the email they get when the organization allows passwords::

    make org-user-add org=acme email=viajero@acme.test name="Viajero Acme"
    python -m app.identity.commands.add_organization_user --org acme --email viajero@acme.test \
        --name "Viajero Acme" [--phone +573001234567] [--language es]
"""

import argparse
import asyncio
import logging
import sys

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.core.errors import AppError
from app.identity.domain.dtos.users import Language, UserRef
from app.identity.domain.errors.users import UnknownOrganizationError
from app.identity.services.account_links import send_pending_email
from app.identity.services.organization_users import give_access
from app.identity.services.users import to_user_ref
from app.notifications.public import create_email_sender
from app.organizations.public import get_organization_by_slug

logger = logging.getLogger(__name__)


async def run(
    org_slug: str, email: str, name: str, phone: str | None = None, language: Language | None = None
) -> UserRef:
    """Creates the user in its own transaction.

    The organization vouches for the email, so it's created as verified. The person gets the welcome
    email and, if the organization accepts passwords, the one to create a password; until then, and
    if it doesn't, they sign in with the organization's identity provider.

    Args:
        org_slug: Slug of the organization.
        email: Email of the person.
        name: Display name.
        phone: Phone number in E.164 format, optional.
        language: Language of the person, optional.

    Returns:
        The new user.

    Raises:
        UnknownOrganizationError: There is no organization with that slug.
    """
    engine = create_engine(get_settings().database_url)
    try:
        async with create_session_factory(engine)() as session, session.begin():
            organization = await get_organization_by_slug(session, org_slug)
            if organization is None:
                raise UnknownOrganizationError(f"There is no organization {org_slug!r}.")
            user, emails = await give_access(
                session, organization, email=email, display_name=name, phone_number=phone, language=language
            )
            created = to_user_ref(user)
        sender = create_email_sender()
        for email in emails:
            await send_pending_email(sender, email, app_url=get_settings().app_url)
        return created
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Arguments, without the program name; `sys.argv` if omitted.

    Returns:
        The exit code.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Gives a person access to an organization.")
    parser.add_argument("--org", required=True, help="Slug of the organization, e.g. acme")
    parser.add_argument("--email", required=True, help="Email of the person")
    parser.add_argument("--name", required=True, help="Display name")
    parser.add_argument("--phone", help="Phone number in E.164 format, e.g. +573001234567")
    parser.add_argument(
        "--language", choices=[lang.value for lang in Language], help="Language; omit it to let the app decide"
    )
    args = parser.parse_args(argv)
    try:
        language = Language(args.language) if args.language else None
        user = asyncio.run(run(args.org, args.email, args.name, args.phone, language))
    except (ValidationError, AppError) as exc:
        logger.error("%s", exc)
        return 1
    logger.info("Created user %s (%s) in %s", user.email, user.id, args.org)
    return 0


if __name__ == "__main__":
    sys.exit(main())
