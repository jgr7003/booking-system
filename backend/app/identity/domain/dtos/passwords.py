"""DTOs of email-and-password sign in and of the links sent by email."""

from enum import StrEnum

from pydantic import Field

from app.identity.domain.dtos.base import DTO
from app.identity.domain.validators.passwords import GivenPassword, LinkToken, NewPassword
from app.identity.domain.dtos.users import Language
from app.identity.domain.validators.users import DisplayName, Email, PhoneNumber


class EmailTokenPurpose(StrEnum):
    """What a link sent by email does."""

    VERIFY_EMAIL = "verify_email"
    SET_PASSWORD = "set_password"
    RESET_PASSWORD = "reset_password"


class LookupRequest(DTO):
    """Body of `POST /auth/password/lookup`: the first step of the sign in."""

    email: Email = Field(
        description="Email the person typed.",
    )


class LookupResult(DTO):
    """What the first step of the sign in tells the screen."""

    exists: bool = Field(
        description="Whether the installation has an account with that email.",
    )

    has_password: bool = Field(
        description="Whether that account can sign in with a password; if not, it uses an identity provider.",
    )


class SignupRequest(DTO):
    """Body of `POST /auth/password/signup` (private travellers only)."""

    email: Email = Field(
        description="Email of the new account; a link to verify it is sent there.",
    )

    display_name: DisplayName = Field(
        description="Name shown in the interface.",
    )

    password: NewPassword = Field(
        description="Password: at least 10 characters.",
    )

    phone_number: PhoneNumber | None = Field(
        default=None,
        description="Phone number in E.164 format, e.g. `+573001234567`. Optional.",
    )

    language: Language | None = Field(
        default=None,
        description="Language the person chose. Omit it to let the app use the browser's or the system's.",
    )


class LoginRequest(DTO):
    """Body of `POST /auth/password/login`."""

    email: Email = Field(
        description="Email of the account.",
    )

    password: GivenPassword = Field(
        description="Password of the account.",
    )

    device_name: str | None = Field(
        default=None,
        max_length=100,
        description="Name of the device for the list of devices; the app sends its model. If omitted, it comes from the `User-Agent`.",
    )


class EmailVerificationRequest(DTO):
    """Body of `POST /auth/email/verify`."""

    token: LinkToken = Field(
        description="Token of the link sent by email.",
    )

    device_name: str | None = Field(
        default=None,
        max_length=100,
        description="Name of the device for the list of devices.",
    )


class SetPasswordRequest(DTO):
    """Body of `POST /auth/password/set`: the first password, or a new one after forgetting it."""

    token: LinkToken = Field(
        description="Token of the link sent by email.",
    )

    password: NewPassword = Field(
        description="New password: at least 10 characters.",
    )


class EmailRequest(DTO):
    """Body of the endpoints that only send an email (forgot password, resend)."""

    email: Email = Field(
        description="Email of the account.",
    )


class AccountEmail(StrEnum):
    """Kinds of account email. All but the welcome carry a single-use link."""

    WELCOME = "welcome"
    VERIFY_EMAIL = "verify_email"
    SET_PASSWORD = "set_password"
    RESET_PASSWORD = "reset_password"
    ACCOUNT_LOCKED = "account_locked"


class LinkTokenRequest(DTO):
    """Body of `POST /auth/password/link`."""

    token: LinkToken = Field(
        description="Token of the link sent by email.",
    )


class PasswordLinkInfo(DTO):
    """What the screen of a password link shows, without using the link."""

    email: str = Field(
        description="Email of the account.",
    )

    kind: str = Field(
        description="`set` (first password) or `reset` (forgotten password).",
    )

    signs_in_with: str | None = Field(
        description="What else the account signs in with, e.g. «Google» or «el SSO de Acme»; `None` if only the password.",
    )
