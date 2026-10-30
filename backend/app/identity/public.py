"""Public interface of the identity module: the only thing other modules may import.

Example, from an endpoint that needs a signed-in user::

    from app.identity.public import Principal, current_principal

    async def endpoint(principal: Annotated[Principal, Depends(current_principal)]): ...
"""

from app.identity.api.dependencies import current_principal, installation_principal, optional_principal
from app.identity.domain.dtos.tokens import Principal

__all__ = [
    "Principal",
    "current_principal",
    "installation_principal",
    "optional_principal",
]
