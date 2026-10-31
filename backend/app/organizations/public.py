"""Public interface of the organizations module: the only thing other modules may import.

Example, from an endpoint that needs to know where the request arrived::

    from app.organizations.public import Installation, current_installation

    async def endpoint(installation: Annotated[Installation, Depends(current_installation)]): ...
"""

from app.organizations.api.dependencies import OrganizationLookup, current_installation, get_organization_lookup
from app.organizations.domain.dtos import Installation, NewOrganization, OrganizationRef, OrganizationSettings
from app.organizations.domain.errors import OrganizationAlreadyExistsError
from app.organizations.services.organizations import create_organization, get_organization, get_organization_by_slug

__all__ = [
    "Installation",
    "NewOrganization",
    "OrganizationAlreadyExistsError",
    "OrganizationLookup",
    "OrganizationRef",
    "OrganizationSettings",
    "create_organization",
    "current_installation",
    "get_organization",
    "get_organization_by_slug",
    "get_organization_lookup",
]
