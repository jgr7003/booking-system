"""Use cases of travellers."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.travellers.domain.dtos import (
    Gender,
    IdentityDocumentDetails,
    IdentityDocumentType,
    TravellerDetails,
    TravellerRef,
)
from app.travellers.repositories.travellers import TravellerRepository


async def create_traveller(session: AsyncSession, details: TravellerDetails) -> TravellerRef:
    """Saves a traveller inside the caller's transaction.

    The caller owns the transaction: if it rolls back (for example, because the booking that
    needed the traveller failed), the traveller isn't saved either.

    Args:
        session: Session of the caller's transaction.
        details: Validated personal data.

    Returns:
        A reference to the new traveller.
    """
    traveller_id = await TravellerRepository(session).add(details)
    return TravellerRef(id=traveller_id)


async def get_traveller(session: AsyncSession, traveller_id: uuid.UUID) -> TravellerDetails | None:
    """Reads a traveller's personal data.

    Args:
        session: An open session.
        traveller_id: Id of the traveller (`TravellerRef.id`).

    Returns:
        The personal data with the documents, or `None` if there is no such traveller.
    """
    traveller = await TravellerRepository(session).get(traveller_id)
    if traveller is None:
        return None
    # Stored data was validated when saved; validating it again would reject history, such as a
    # passport that expired since.
    return TravellerDetails.model_construct(
        given_name=traveller.given_name,
        family_name=traveller.family_name,
        born_on=traveller.born_on,
        gender=Gender(traveller.gender),
        email=traveller.email,
        phone_number=traveller.phone_number,
        identity_documents=[
            IdentityDocumentDetails.model_construct(
                type=IdentityDocumentType(d.type),
                number=d.number,
                issuing_country_code=d.issuing_country_code,
                expires_on=d.expires_on,
            )
            for d in traveller.identity_documents
        ],
    )
