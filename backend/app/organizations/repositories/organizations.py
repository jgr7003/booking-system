"""Persistence of organizations in PostgreSQL."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.organizations.domain.dtos import NewOrganization, OrganizationStatus
from app.organizations.domain.models import Domain, Organization


class OrganizationRepository:
    """Reads and writes the `organizations` schema, inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Initializes the repository.

        Args:
            session: Session of the transaction to work in. The repository never commits.
        """
        self._session = session

    async def find_active_by_host(self, hostname: str) -> Organization | None:
        """Finds the active organization that owns a hostname.

        Args:
            hostname: Normalized hostname.

        Returns:
            The organization, or `None` if no active organization owns it.
        """
        return await self._session.scalar(
            select(Organization)
            .join(Domain)
            .where(Domain.hostname == hostname, Organization.status == OrganizationStatus.ACTIVE.value)
        )

    async def get(self, organization_id: uuid.UUID) -> Organization | None:
        """Reads an organization by id.

        Args:
            organization_id: Id of the organization.

        Returns:
            The organization, or `None`.
        """
        return await self._session.get(Organization, organization_id)

    async def get_by_slug(self, slug: str) -> Organization | None:
        """Reads an organization by slug.

        Args:
            slug: Slug of the organization.

        Returns:
            The organization, or `None`.
        """
        return await self._session.scalar(select(Organization).where(Organization.slug == slug))

    async def is_taken(self, slug: str, hostnames: list[str]) -> bool:
        """Tells whether the slug or any of the hostnames is already used.

        Args:
            slug: Slug to check.
            hostnames: Hostnames to check.

        Returns:
            `True` if any of them is taken.
        """
        by_slug = await self._session.scalar(select(Organization.id).where(Organization.slug == slug))
        by_host = await self._session.scalar(select(Domain.hostname).where(Domain.hostname.in_(hostnames)))
        return by_slug is not None or by_host is not None

    async def add(self, new: NewOrganization) -> Organization:
        """Saves a new active organization with its hostnames.

        Args:
            new: Validated data of the organization.

        Returns:
            The saved organization.
        """
        organization = Organization(
            id=uuid.uuid4(),
            slug=new.slug,
            name=new.name,
            status=OrganizationStatus.ACTIVE.value,
            settings=new.settings.model_dump(mode="json"),
            domains=[Domain(hostname=h) for h in new.hostnames],
        )
        self._session.add(organization)
        await self._session.flush()
        return organization
