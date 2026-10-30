"""DTOs of the travellers module. They are also its public contract (see `public.py`)."""

import uuid
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.travellers.domain.validators import (
    BirthDate,
    CountryCode,
    DocumentNumber,
    Email,
    ExpiryDate,
    PersonName,
    PhoneNumber,
)


class DTO(BaseModel):
    """Base of every travellers DTO: immutable."""

    model_config = ConfigDict(frozen=True)


class Gender(StrEnum):
    """Gender as written in the traveller's identity document."""

    MALE = "m"
    FEMALE = "f"


class IdentityDocumentType(StrEnum):
    """Kind of identity document. Only passports are supported for now."""

    PASSPORT = "passport"


class IdentityDocumentDetails(DTO):
    """An identity document of a traveller, e.g. a passport."""

    type: IdentityDocumentType = Field(
        default=IdentityDocumentType.PASSPORT,
        description="Kind of document.",
    )

    number: DocumentNumber = Field(
        description="Number of the document, as printed on it.",
    )

    issuing_country_code: CountryCode = Field(
        description="ISO 3166-1 alpha-2 code of the issuing country, e.g. `AR`.",
    )

    expires_on: ExpiryDate = Field(
        description="Expiry date; it must be in the future.",
    )


class TravellerDetails(DTO):
    """Personal data of a traveller, as written in their travel document."""

    given_name: PersonName = Field(
        description="Given name.",
    )

    family_name: PersonName = Field(
        description="Family name.",
    )

    born_on: BirthDate = Field(
        description="Date of birth.",
    )

    gender: Gender = Field(
        description="Gender as written in the identity document.",
    )

    email: Email = Field(
        description="Email where the traveller gets the itinerary and the tickets.",
    )

    phone_number: PhoneNumber = Field(
        description="Phone number in international E.164 format, e.g. `+573001234567`.",
    )

    identity_documents: list[IdentityDocumentDetails] = Field(
        default_factory=list,
        description="Identity documents; at most one of each type.",
    )

    @model_validator(mode="after")
    def check_one_document_per_type(self) -> Self:
        """Rejects two documents of the same type.

        Returns:
            The validated instance.

        Raises:
            ValueError: Two documents share a type.
        """
        types = [document.type for document in self.identity_documents]
        if len(types) != len(set(types)):
            raise ValueError("at most one identity document of each type")
        return self

    def document(self, type: IdentityDocumentType) -> IdentityDocumentDetails | None:
        """Returns the document of a type, if the traveller has one.

        Args:
            type: Kind of document.

        Returns:
            The document, or `None`.
        """
        return next((d for d in self.identity_documents if d.type == type), None)


class TravellerRef(DTO):
    """Reference to a saved traveller, for other modules to keep (by id, without a foreign key)."""

    id: uuid.UUID = Field(
        description="Id of the traveller.",
    )


class Title(StrEnum):
    """Title of the traveller, as airlines print it on the ticket."""

    MR = "mr"
    MS = "ms"
    MRS = "mrs"
    MISS = "miss"
    DR = "dr"


class TravellerProfile(DTO):
    """Passenger data a user keeps for their own trips, so they don't type them every time.

    Only the account holder has one: a booking for someone else keeps that person's data in the
    booking (its traveller) and nothing else.
    """

    title: Title = Field(
        description="Title printed on the ticket.",
    )

    born_on: BirthDate = Field(
        description="Date of birth.",
    )

    gender: Gender = Field(
        description="Gender as written in the identity document.",
    )
