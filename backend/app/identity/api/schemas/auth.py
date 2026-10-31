"""Public schemas of sign in, tokens and the current user."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.identity.domain.dtos.users import Language
from app.travellers.public import Gender, Title


class TokenResponse(BaseModel):
    """Tokens of a device session. Send the access token as `Authorization: DPoP <access_token>`."""

    model_config = ConfigDict(frozen=True)

    token_type: Literal["DPoP"] = Field(
        default="DPoP",
        description="Scheme of the `Authorization` header. Every request also needs a `DPoP` proof signed by the device key.",
    )

    access_token: str = Field(
        description="Signed JWT (ES256). Its claims (name, email, organization) are readable, only to decide what to show.",
    )

    expires_in: int = Field(
        description="Seconds until the access token expires.",
    )

    refresh_token: str = Field(
        description="Single-use: `POST /auth/token/refresh` returns a new one. Using it twice closes the session.",
    )

    session_id: uuid.UUID = Field(
        description="Device session, as listed in `GET /me/sessions`.",
    )

    return_to: str | None = Field(
        default=None,
        description="Path of the app to go back to after signing in, if the sign in started with one.",
    )


class RefreshRequest(BaseModel):
    """Body of `POST /auth/token/refresh`."""

    refresh_token: str = Field(
        min_length=1,
        max_length=200,
        description="The last refresh token the device received.",
    )


class OrganizationSummary(BaseModel):
    """The organization of the current user."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(
        description="Id of the organization.",
    )

    name: str = Field(
        description="Name shown to users.",
    )


class TravellerProfileSummary(BaseModel):
    """Passenger data the user keeps for their own trips."""

    model_config = ConfigDict(frozen=True)

    title: Title = Field(
        description="Title printed on the ticket.",
    )

    born_on: date = Field(
        description="Date of birth.",
    )

    gender: Gender = Field(
        description="Gender as written in the identity document: `m` or `f`.",
    )


class MeResponse(BaseModel):
    """The signed-in user."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(
        description="Id of the user.",
    )

    email: str = Field(
        description="Email of the user.",
    )

    display_name: str = Field(
        description="Name shown in the interface.",
    )

    organization: OrganizationSummary | None = Field(
        description="Organization of the user; `null` for a private traveller.",
    )

    has_password: bool = Field(
        description="Whether the user set a password; if not, they sign in with an identity provider.",
    )

    phone_number: str | None = Field(
        description="Phone number in E.164 format, if the user gave one.",
    )

    language: Language | None = Field(
        description="Language the user chose; `null` means the app uses the browser's or the system's.",
    )

    traveller_profile: TravellerProfileSummary | None = Field(
        description="Passenger data of their last booking for themselves, to fill the next one; `null` until they book for themselves.",
    )

    session_id: uuid.UUID = Field(
        description="Device session of this request.",
    )


class DeviceSessionResponse(BaseModel):
    """A connected device."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(
        description="Id of the session.",
    )

    device_name: str = Field(
        description="Name of the device, e.g. «Chrome en Windows».",
    )

    created_at: datetime = Field(
        description="When the device signed in.",
    )

    last_seen_at: datetime = Field(
        description="Last time it was used (precision: about a minute).",
    )

    last_ip: str | None = Field(
        description="Last address seen.",
    )

    current: bool = Field(
        description="Whether it's the device making this request.",
    )


class DeviceSessionListResponse(BaseModel):
    """Connected devices of the signed-in user."""

    model_config = ConfigDict(frozen=True)

    sessions: list[DeviceSessionResponse] = Field(
        description="Open sessions, most recently used first.",
    )


class LookupResponse(BaseModel):
    """Answer of the first step of the sign in."""

    model_config = ConfigDict(frozen=True)

    exists: bool = Field(
        description="Whether the installation has an account with that email.",
    )

    has_password: bool = Field(
        description="Whether the account can sign in with a password.",
    )


class ProviderOption(BaseModel):
    """An identity provider on the sign-in screen."""

    model_config = ConfigDict(frozen=True)

    slug: str = Field(
        description="Name in the URLs of `/auth/oidc/{provider}/...`.",
    )

    display_name: str = Field(
        description="Text of the button, e.g. «Google» or «Acme SSO».",
    )


class AuthMethodsResponse(BaseModel):
    """How people sign in to this installation."""

    model_config = ConfigDict(frozen=True)

    organization_name: str | None = Field(
        description="Name of the organization of the installation; `null` for the main one.",
    )

    password_enabled: bool = Field(
        description="Whether email and password are accepted.",
    )

    signup_enabled: bool = Field(
        description="Whether people can create their own account (only private travellers).",
    )

    providers: list[ProviderOption] = Field(
        description="Identity providers, one button each.",
    )


class AuthorizeResponse(BaseModel):
    """Where to send the browser to sign in at the provider."""

    model_config = ConfigDict(frozen=True)

    authorization_url: str = Field(
        description="URL of the provider. It sends the browser back to `/auth/callback` of this app with `code` and `state`.",
    )


class SignedInResponse(BaseModel):
    """The provider's identity has an account here: the device is signed in."""

    model_config = ConfigDict(frozen=True)

    status: Literal["signed_in"] = Field(
        default="signed_in",
        description="Discriminator.",
    )

    tokens: TokenResponse = Field(
        description="Tokens of the new session, with `return_to`.",
    )


class AccountNotFoundResponse(BaseModel):
    """The provider's identity has no account here: «No encontramos tu cuenta»."""

    model_config = ConfigDict(frozen=True)

    status: Literal["account_not_found"] = Field(
        default="account_not_found",
        description="Discriminator.",
    )

    attempt_id: uuid.UUID = Field(
        description="Use it in `POST` (create the account) or `DELETE` (try another account) `/auth/signup/pending/{attempt_id}`.",
    )

    email: str = Field(
        description="Email the provider verified.",
    )

    display_name: str = Field(
        description="Name the provider gave.",
    )

    can_create: bool = Field(
        description="`true` for private travellers; in an organization, it must give access first.",
    )


class PasswordLinkResponse(BaseModel):
    """What a password link is for."""

    model_config = ConfigDict(frozen=True)

    email: str = Field(
        description="Email of the account.",
    )

    kind: Literal["set", "reset"] = Field(
        description="`set`: first password; `reset`: the person forgot it.",
    )

    signs_in_with: str | None = Field(
        description="What else the account signs in with, e.g. «Google» or «el SSO de Acme»; `null` if only the password.",
    )
