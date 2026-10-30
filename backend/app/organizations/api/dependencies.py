"""FastAPI dependencies that tell each request which installation it arrived at."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.proxy import original_host
from app.organizations.core.config import get_installation_settings
from app.organizations.domain.dtos import Installation, OrganizationRef
from app.organizations.domain.errors import UnknownInstallationError
from app.organizations.domain.validators import normalize_host
from app.organizations.services.organizations import find_organization_by_host, installation_of


class OrganizationLookup:
    """Finds the organization of a hostname, opening a database session only when it's needed.

    Requests to the main platform never touch the database, so this opens the session lazily
    instead of depending on one.
    """

    def __init__(self, session_factory: Callable[[], async_sessionmaker[AsyncSession]]) -> None:
        """Initializes the lookup.

        Args:
            session_factory: Returns the session factory; called only for organization hosts.
        """
        self._session_factory = session_factory

    async def find(self, hostname: str) -> OrganizationRef | None:
        """Finds the active organization of a hostname.

        Args:
            hostname: Normalized hostname.

        Returns:
            The organization, or `None`.
        """
        async with self._session_factory()() as session:
            return await find_organization_by_host(session, hostname)


def get_organization_lookup(request: Request) -> OrganizationLookup:
    """FastAPI dependency that provides the organization lookup.

    Tests override it with a lookup bound to the test database.

    Args:
        request: The incoming request, used to reach the session factory in the app state.

    Returns:
        A lookup that reads `app.state.session_factory` only when it's used.
    """
    return OrganizationLookup(lambda: request.app.state.session_factory)


def request_host(request: Request) -> str:
    """Hostname the client asked for.

    `X-Forwarded-Host` is honored only when the direct client is a trusted proxy (the Vite dev
    server in development); from anyone else it could be forged to reach another installation.

    Args:
        request: The incoming request.

    Returns:
        The normalized hostname, without port.
    """
    return normalize_host(original_host(request))


async def current_installation(
    request: Request,
    lookup: Annotated[OrganizationLookup, Depends(get_organization_lookup)],
) -> Installation:
    """FastAPI dependency that resolves the installation of the request.

    It's applied to every `/api` router, so an unknown host gets a 404 on every endpoint.
    FastAPI caches it per request: endpoints that need the installation declare it again at no
    extra cost.

    Args:
        request: The incoming request.
        lookup: Finds the organization of a hostname.

    Returns:
        The installation: the main platform (no organization) or an organization's.

    Raises:
        UnknownInstallationError: The host isn't the platform's nor an active organization's.
    """
    host = request_host(request)
    if host in get_installation_settings().platform_hosts:
        return installation_of(host, None)
    organization = await lookup.find(host)
    if organization is None:
        raise UnknownInstallationError("Not found.")
    return installation_of(host, organization)
