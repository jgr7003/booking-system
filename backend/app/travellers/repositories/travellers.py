"""Persistence of travellers in PostgreSQL."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.travellers.domain.dtos import TravellerDetails
from app.travellers.domain.models import IdentityDocument, Traveller


class TravellerRepository:
    """Reads and writes the `travellers` schema, inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Initializes the repository.

        Args:
            session: Session of the transaction to work in. The repository never commits.
        """
        self._session = session

    async def add(self, details: TravellerDetails) -> uuid.UUID:
        """Saves a new traveller with their documents.

        Args:
            details: Validated personal data.

        Returns:
            The id of the new traveller.
        """
        traveller = Traveller(
            id=uuid.uuid4(),
            given_name=details.given_name,
            family_name=details.family_name,
            born_on=details.born_on,
            gender=details.gender.value,
            email=details.email,
            phone_number=details.phone_number,
            identity_documents=[
                IdentityDocument(
                    type=document.type.value,
                    number=document.number,
                    issuing_country_code=document.issuing_country_code,
                    expires_on=document.expires_on,
                )
                for document in details.identity_documents
            ],
        )
        self._session.add(traveller)
        await self._session.flush()
        return traveller.id

    async def get(self, traveller_id: uuid.UUID) -> Traveller | None:
        """Finds a traveller by id.

        Args:
            traveller_id: Id of the traveller.

        Returns:
            The traveller with their documents, or `None`.
        """
        return await self._session.get(Traveller, traveller_id)
