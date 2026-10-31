"""Adds (or updates) an OIDC identity provider of an installation.

The client secret is stored encrypted with `IDENTITY_SECRETS_KEY`. Examples::

    make idp-add slug=google name=Google issuer=https://accounts.google.com client_id=... client_secret=...
    make idp-add org=acme slug=acme-sso name="Acme SSO" issuer=https://sso.acme.test client_id=... client_secret=...
    python -m app.identity.commands.add_identity_provider --slug google --name Google \
        --issuer https://accounts.google.com --client-id ... --client-secret ... [--org acme] \
        [--backchannel-base-url http://keycloak:8080] [--trust-email] [--prompt select_account]
"""

import argparse
import asyncio
import logging
import sys

from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.core.errors import AppError
from app.identity.domain.errors.users import UnknownOrganizationError
from app.identity.services.providers import register_provider
from app.organizations.public import get_organization_by_slug

logger = logging.getLogger(__name__)


async def run(args: argparse.Namespace) -> bool:
    """Registers the provider in its own transaction.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Whether it was created (`False` if it was updated).

    Raises:
        UnknownOrganizationError: `--org` names an organization that doesn't exist.
    """
    engine = create_engine(get_settings().database_url)
    try:
        async with create_session_factory(engine)() as session, session.begin():
            organization_id = None
            if args.org:
                organization = await get_organization_by_slug(session, args.org)
                if organization is None:
                    raise UnknownOrganizationError(f"There is no organization {args.org!r}.")
                organization_id = organization.id
            _, created = await register_provider(
                session,
                organization_id=organization_id,
                slug=args.slug,
                display_name=args.name,
                issuer=args.issuer,
                client_id=args.client_id,
                client_secret=args.client_secret,
                backchannel_base_url=args.backchannel_base_url or None,
                trust_email=args.trust_email,
                extra_authorize_params={"prompt": args.prompt} if args.prompt else None,
            )
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
    parser = argparse.ArgumentParser(description="Adds or updates an OIDC identity provider.")
    parser.add_argument("--org", help="Slug of the organization; omit it for the main platform")
    parser.add_argument("--slug", required=True, help="Name in URLs, e.g. google")
    parser.add_argument("--name", required=True, help="Text of the sign-in button")
    parser.add_argument("--issuer", required=True, help="Issuer URL of the provider")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    parser.add_argument("--backchannel-base-url", help="Development only: base URL the API uses to reach it")
    parser.add_argument("--trust-email", action="store_true", help="Accept emails without email_verified")
    parser.add_argument("--prompt", help="`prompt` of every authorization request, e.g. select_account")
    args = parser.parse_args(argv)
    try:
        created = asyncio.run(run(args))
    except AppError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("%s identity provider %s", "Created" if created else "Updated", args.slug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
