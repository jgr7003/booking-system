"""Registers the development Keycloak as identity provider, and the organization Acme (idempotent).

Development only. It leaves:

- the main installation with the provider `keycloak` (realm `particulares`), in place of Google;
- the organization Acme at `acme.localhost`, with its provider `acme-sso` (realm `acme`) and the
  user `viajero@acme.test`, who gets the email to create a password. `intruso@acme.test` exists
  only in Keycloak, to try «tu empresa todavía no te dio acceso».

The realms live in `backend/docker/keycloak/realms/`; their client secrets are development values,
committed on purpose and useless anywhere else (03-usuarios-y-acceso.md §15.1)::

    make seed-dev-idps
"""

import asyncio
import logging
import sys

from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.identity.domain.errors.users import UserAlreadyExistsError
from app.identity.services.account_links import send_pending_email
from app.identity.services.organization_users import give_access
from app.identity.services.providers import register_provider
from app.notifications.public import create_email_sender
from app.organizations.public import NewOrganization, create_organization, get_organization_by_slug

logger = logging.getLogger(__name__)

# Where the browser reaches Keycloak.
KEYCLOAK_PUBLIC_URL = "http://localhost:8080"

# Where the API reaches Keycloak, inside the docker network.
KEYCLOAK_INTERNAL_URL = "http://keycloak:8080"


async def seed() -> None:
    """Registers the providers, the organization and its user, and sends the user's email."""
    emails = []
    engine = create_engine(get_settings().database_url)
    try:
        async with create_session_factory(engine)() as session, session.begin():
            await register_provider(
                session,
                organization_id=None,
                slug="keycloak",
                display_name="Keycloak (prueba)",
                issuer=f"{KEYCLOAK_PUBLIC_URL}/realms/particulares",
                backchannel_base_url=KEYCLOAK_INTERNAL_URL,
                client_id="booking-platform",
                client_secret="dev-particulares-secret",
            )
            acme = await get_organization_by_slug(session, "acme")
            if acme is None:
                acme = await create_organization(
                    session, NewOrganization(slug="acme", name="Acme", hostnames=["acme.localhost"])
                )
            await register_provider(
                session,
                organization_id=acme.id,
                slug="acme-sso",
                display_name="Acme SSO",
                issuer=f"{KEYCLOAK_PUBLIC_URL}/realms/acme",
                backchannel_base_url=KEYCLOAK_INTERNAL_URL,
                client_id="booking-acme",
                client_secret="dev-acme-secret",
            )
            try:
                async with session.begin_nested():
                    _, emails = await give_access(
                        session, acme, email="viajero@acme.test", display_name="Viajero Acme"
                    )
            except UserAlreadyExistsError:
                logger.info("viajero@acme.test already has access to Acme")
        sender = create_email_sender()
        for email in emails:
            await send_pending_email(sender, email, app_url=get_settings().app_url)
    finally:
        await engine.dispose()


def main() -> int:
    """Command-line entry point.

    Returns:
        The exit code.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(seed())
    logger.info("Development identity providers are registered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
