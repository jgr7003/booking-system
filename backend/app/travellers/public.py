"""Public interface of the travellers module: the only thing other modules may import.

Example, from a vertical that books for a traveller::

    from app.travellers.public import TravellerDetails, create_traveller

    ref = await create_traveller(session, details)  # inside the vertical's transaction
"""

from app.travellers.domain.dtos import (
    Gender,
    IdentityDocumentDetails,
    IdentityDocumentType,
    TravellerDetails,
    TravellerRef,
)
from app.travellers.services.travellers import create_traveller, get_traveller

__all__ = [
    "Gender",
    "IdentityDocumentDetails",
    "IdentityDocumentType",
    "TravellerDetails",
    "TravellerRef",
    "create_traveller",
    "get_traveller",
]
