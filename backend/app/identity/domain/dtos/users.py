"""DTOs of users."""

import uuid
from enum import StrEnum

from pydantic import Field

from app.identity.domain.dtos.base import DTO
from app.identity.domain.validators.users import DisplayName, Email, PhoneNumber


class Language(StrEnum):
    """Language of the interface and the emails (only Spanish for now; English for future translations)."""

    SPANISH = "es"
    ENGLISH = "en"


class UserStatus(StrEnum):
    """Whether a user may sign in."""

    ACTIVE = "active"
    DISABLED = "disabled"


class NewUser(DTO):
    """Data to create a user."""

    organization_id: uuid.UUID | None = Field(
        description="Organization of the user; `None` for a private traveller.",
    )

    email: Email = Field(
        description="Email, normalized to lower case.",
    )

    display_name: DisplayName = Field(
        description="Name shown in the interface.",
    )

    email_verified: bool = Field(
        default=False,
        description="Whether the email is already proven (by an identity provider or by the organization).",
    )

    phone_number: PhoneNumber | None = Field(
        default=None,
        description="Phone number in E.164 format, optional.",
    )

    language: Language | None = Field(
        default=None,
        description="Language the user chose; `None` lets the app use the browser's or the system's.",
    )


class UserRef(DTO):
    """A user as the rest of the module sees it."""

    id: uuid.UUID = Field(
        description="Id of the user.",
    )

    organization_id: uuid.UUID | None = Field(
        description="Organization of the user; `None` for a private traveller.",
    )

    email: str = Field(
        description="Email, in lower case.",
    )

    display_name: str = Field(
        description="Name shown in the interface.",
    )

    email_verified: bool = Field(
        description="Whether the email is proven.",
    )

    has_password: bool = Field(
        description="Whether the user set a password.",
    )

    phone_number: str | None = Field(
        description="Phone number in E.164 format, if the user gave one.",
    )

    language: Language | None = Field(
        description="Language the user chose; `None` if they didn't.",
    )
