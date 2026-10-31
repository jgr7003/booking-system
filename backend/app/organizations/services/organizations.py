"""Use cases of organizations."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.organizations.domain.dtos import Installation, NewOrganization, OrganizationRef, OrganizationSettings
from app.organizations.domain.errors import OrganizationAlreadyExistsError
from app.organizations.domain.models import Organization
from app.organizations.repositories.organizations import OrganizationRepository


def to_ref(organization: Organization) -> OrganizationRef:
    """Converts a database row into the DTO other modules see.

    Args:
        organization: The row.

    Returns:
        The organization with its settings validated.
    """
    return OrganizationRef(
        id=organization.id,
        slug=organization.slug,
        name=organization.name,
        settings=OrganizationSettings.model_validate(organization.settings),
        hostnames=sorted(d.hostname for d in organization.domains),
    )


async def find_organization_by_host(session: AsyncSession, hostname: str) -> OrganizationRef | None:
    """Finds the active organization whose installation answers at a hostname.

    Args:
        session: An open session.
        hostname: Normalized hostname.

    Returns:
        The organization, or `None`.
    """
    organization = await OrganizationRepository(session).find_active_by_host(hostname)
    return to_ref(organization) if organization else None


async def get_organization(session: AsyncSession, organization_id: uuid.UUID) -> OrganizationRef | None:
    """Reads an organization.

    Args:
        session: An open session.
        organization_id: Id of the organization.

    Returns:
        The organization, or `None`.
    """
    organization = await OrganizationRepository(session).get(organization_id)
    return to_ref(organization) if organization else None


async def get_organization_by_slug(session: AsyncSession, slug: str) -> OrganizationRef | None:
    """Reads an organization by its slug.

    Args:
        session: An open session.
        slug: Slug of the organization, e.g. `acme`.

    Returns:
        The organization, or `None`.
    """
    organization = await OrganizationRepository(session).get_by_slug(slug)
    return to_ref(organization) if organization else None


async def create_organization(session: AsyncSession, new: NewOrganization) -> OrganizationRef:
    """Creates an organization inside the caller's transaction.

    Args:
        session: Session of the caller's transaction.
        new: Validated data of the organization.

    Returns:
        The new organization.

    Raises:
        OrganizationAlreadyExistsError: The slug or a hostname is already used.
    """
    repository = OrganizationRepository(session)
    if await repository.is_taken(new.slug, new.hostnames):
        raise OrganizationAlreadyExistsError("The slug or one of the hostnames is already used.")
    return to_ref(await repository.add(new))


def installation_of(host: str, organization: OrganizationRef | None) -> Installation:
    """The installation a host answers for, with the settings in force.

    Args:
        host: Normalized hostname of the request.
        organization: Its organization; `None` for the main platform.

    Returns:
        The installation; the main platform gets the default settings.
    """
    return Installation(
        host=host,
        organization=organization,
        organization_id=organization.id if organization else None,
        settings=organization.settings if organization else OrganizationSettings(),
    )
