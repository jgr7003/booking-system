"""DTOs of the platform's tokens, the authenticated principal and device sessions."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.identity.domain.dtos.base import DTO


class Confirmation(DTO):
    """Key the token is bound to (RFC 9449 §6)."""

    jkt: str = Field(
        description="JWK SHA-256 thumbprint (RFC 7638) of the device's public key.",
    )


class AccessTokenClaims(DTO):
    """Claims of an access token. Readable by anyone who holds the token: nothing secret here.

    Later on they will also carry the user's permissions, only to decide what the interface shows;
    the backend always checks permissions on its own.
    """

    iss: str = Field(
        description="Host of the installation that issued the token, e.g. `acme.localhost`.",
    )

    aud: str = Field(
        description="Who the token is for: the platform's API.",
    )

    sub: uuid.UUID = Field(
        description="Id of the user.",
    )

    org: uuid.UUID | None = Field(
        description="Organization of the user; `null` for a private traveller.",
    )

    sid: uuid.UUID = Field(
        description="Device session the token belongs to.",
    )

    iat: int = Field(
        description="When it was issued, in seconds since the epoch.",
    )

    exp: int = Field(
        description="When it expires, in seconds since the epoch.",
    )

    jti: uuid.UUID = Field(
        description="Unique id of the token.",
    )

    name: str = Field(
        description="Display name of the user.",
    )

    email: str = Field(
        description="Email of the user.",
    )

    lang: str | None = Field(
        default=None,
        description="Language the user chose (`es`, `en`); `null` means the app uses the browser's or the system's.",
    )

    cnf: Confirmation = Field(
        description="Device key the token is bound to.",
    )


class TokenPair(DTO):
    """What a successful sign in or refresh gives the device."""

    access_token: str = Field(
        description="Signed JWT, sent as `Authorization: DPoP <access_token>`.",
    )

    expires_in: int = Field(
        description="Seconds until the access token expires.",
    )

    refresh_token: str = Field(
        description="Single-use value to get the next pair.",
    )

    session_id: uuid.UUID = Field(
        description="Device session.",
    )


class Principal(DTO):
    """The authenticated user of a request, as other modules see it."""

    user_id: uuid.UUID = Field(
        description="Id of the user.",
    )

    organization_id: uuid.UUID | None = Field(
        description="Organization of the user; `None` for a private traveller.",
    )

    session_id: uuid.UUID = Field(
        description="Device session of the request.",
    )

    email: str = Field(
        description="Email of the user.",
    )

    display_name: str = Field(
        description="Display name of the user.",
    )

    expires_at: int = Field(
        description="When the access token of the request expires, in seconds since the epoch; long requests (SSE) end then.",
    )


class RevocationReason(StrEnum):
    """Why a device session was closed."""

    LOGOUT = "logout"
    USER_REVOKED = "user_revoked"
    REFRESH_REUSE = "refresh_reuse"
    KEY_MISMATCH = "key_mismatch"
    PASSWORD_CHANGED = "password_changed"


class DeviceInfo(DTO):
    """What is known about the device that signs in."""

    jkt: str = Field(
        description="Thumbprint of the device's public key: the identity of the device.",
    )

    device_name: str = Field(
        description="Name to show in the list of devices, e.g. «Chrome en Windows».",
    )

    user_agent: str | None = Field(
        default=None,
        description="`User-Agent` header at sign in.",
    )

    ip: str | None = Field(
        default=None,
        description="Address of the client.",
    )


class DeviceSessionView(DTO):
    """A device session in the list of connected devices."""

    id: uuid.UUID = Field(
        description="Id of the session.",
    )

    device_name: str = Field(
        description="Name of the device.",
    )

    created_at: datetime = Field(
        description="When the device signed in.",
    )

    last_seen_at: datetime = Field(
        description="Last time the session was used (precision: about a minute).",
    )

    last_ip: str | None = Field(
        description="Last address seen.",
    )
