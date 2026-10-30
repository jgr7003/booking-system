"""Creates an organization with its installation hostnames.

Until there is an administration panel, organizations are created from the command line::

    make org-create slug=acme name="Acme" host=acme.localhost
    python -m app.organizations.commands.create_organization --slug acme --name Acme \
        --host acme.localhost [--host viajes.acme.test] [--no-password-login] \
        [--trusted-network 200.1.2.0/24]
"""

import argparse
import asyncio
import logging
import sys

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.organizations.domain.dtos import NewOrganization, OrganizationRef, OrganizationSettings
from app.organizations.domain.errors import OrganizationAlreadyExistsError
from app.organizations.services.organizations import create_organization

logger = logging.getLogger(__name__)


async def run(new: NewOrganization) -> OrganizationRef:
    """Creates the organization in its own transaction.

    Args:
        new: Validated data of the organization.

    Returns:
        The new organization.
    """
    engine = create_engine(get_settings().database_url)
    try:
        async with create_session_factory(engine)() as session, session.begin():
            return await create_organization(session, new)
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
    parser = argparse.ArgumentParser(description="Creates an organization.")
    parser.add_argument("--slug", required=True, help="Short unique name, e.g. acme")
    parser.add_argument("--name", required=True, help="Name shown to users")
    parser.add_argument("--host", action="append", required=True, help="Hostname of its installation")
    parser.add_argument("--no-password-login", action="store_true", help="Only its identity providers")
    parser.add_argument(
        "--trusted-network", action="append", default=[], help="Public network of an office (CIDR); repeatable"
    )
    args = parser.parse_args(argv)
    try:
        new = NewOrganization(
            slug=args.slug,
            name=args.name,
            hostnames=args.host,
            settings=OrganizationSettings(
                password_login_enabled=not args.no_password_login, trusted_networks=args.trusted_network
            ),
        )
        organization = asyncio.run(run(new))
    except (ValidationError, OrganizationAlreadyExistsError) as exc:
        logger.error("%s", exc)
        return 1
    logger.info("Created organization %s (%s) at %s", organization.slug, organization.id, ", ".join(new.hostnames))
    return 0


if __name__ == "__main__":
    sys.exit(main())
