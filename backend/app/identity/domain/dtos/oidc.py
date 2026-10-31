"""DTOs of sign in through an OIDC provider (Authorization Code + PKCE)."""

import uuid
from enum import StrEnum

from pydantic import Field, SecretStr

from app.identity.domain.dtos.base import DTO
from app.identity.domain.dtos.tokens import TokenPair
from app.identity.domain.dtos.users import Language
from app.identity.domain.validators.oidc import ReturnTo
from app.identity.domain.validators.users import PhoneNumber


class LoginAttemptStatus(StrEnum):
    """Where a sign-in attempt is."""

    STARTED = "started"
    EXCHANGING = "exchanging"
    AWAITING_SIGNUP = "awaiting_signup"


class ProviderConfig(DTO):
    """An OIDC provider ready to use, with its secret decrypted."""

    id: uuid.UUID = Field(
        description="Id of the provider.",
    )

    slug: str = Field(
        description="Name in URLs.",
    )

    display_name: str = Field(
        description="Name on the sign-in button.",
    )

    issuer: str = Field(
        description="Issuer of the provider.",
    )

    backchannel_base_url: str | None = Field(
        description="Base URL for server-to-server calls (development only).",
    )

    client_id: str = Field(
        description="Client id registered at the provider.",
    )

    client_secret: SecretStr = Field(
        description="Client secret.",
    )

    scopes: str = Field(
        description="Scopes asked for, space separated.",
    )

    trust_email: bool = Field(
        description="Accept the email even without `email_verified`.",
    )

    extra_authorize_params: dict[str, str] = Field(
        description="Extra parameters of the authorization request.",
    )


class VerifiedIdentity(DTO):
    """Who the provider says the person is, after checking the id_token."""

    subject: str = Field(
        description="Stable id of the person at the provider (`sub`).",
    )

    email: str = Field(
        description="Email, in lower case.",
    )

    display_name: str = Field(
        description="Name to show.",
    )


class AuthorizeRequest(DTO):
    """Body of `POST /auth/oidc/{provider}/authorize`."""

    return_to: ReturnTo | None = Field(
        default=None,
        description="Path of the app to go back to after signing in, e.g. `/trip`. Only paths of this app.",
    )

    another_account: bool = Field(
        default=False,
        description="«Usar otra cuenta»: asks the provider to sign in again (`prompt=login`) instead of reusing its session.",
    )


class CallbackRequest(DTO):
    """Body of `POST /auth/oidc/{provider}/callback`: what the provider put in the redirect."""

    code: str = Field(
        min_length=1,
        max_length=2048,
        description="Authorization code.",
    )

    state: str = Field(
        min_length=1,
        max_length=200,
        description="`state` the provider sent back.",
    )

    device_name: str | None = Field(
        default=None,
        max_length=100,
        description="Name of the device for the list of devices; if omitted, it comes from the `User-Agent`.",
    )


class SignupDecision(DTO):
    """Body of `POST /auth/signup/pending/{attempt_id}`."""

    device_name: str | None = Field(
        default=None,
        max_length=100,
        description="Name of the device for the list of devices.",
    )

    phone_number: PhoneNumber | None = Field(
        default=None,
        description="Phone number in E.164 format, e.g. `+573001234567`. Optional.",
    )

    language: Language | None = Field(
        default=None,
        description="Language the person chose. Omit it to let the app use the browser's or the system's.",
    )


class SignedIn(DTO):
    """The provider's identity matched an account: the device is signed in."""

    tokens: TokenPair = Field(
        description="Tokens of the new session.",
    )

    return_to: str | None = Field(
        description="Path of the app to go back to.",
    )


class AccountNotFound(DTO):
    """The provider's identity has no account in this installation."""

    attempt_id: uuid.UUID = Field(
        description="Attempt that keeps the identity while the person decides.",
    )

    email: str = Field(
        description="Email the provider verified.",
    )

    display_name: str = Field(
        description="Name the provider gave.",
    )

    can_create: bool = Field(
        description="Whether an account can be created here (only for private travellers).",
    )

