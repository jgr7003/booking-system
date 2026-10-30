"""DTOs of the organizations module. They are also its public contract (see `public.py`)."""

import uuid
from enum import StrEnum
from ipaddress import IPv4Network, IPv6Network

from pydantic import BaseModel, ConfigDict, Field

from app.organizations.domain.validators import Hostname, Slug


class DTO(BaseModel):
    """Base of every organizations DTO: immutable."""

    model_config = ConfigDict(frozen=True)


class OrganizationStatus(StrEnum):
    """Whether an organization's installation is open."""

    ACTIVE = "active"
    SUSPENDED = "suspended"


class OrganizationSettings(DTO):
    """Configuration of an organization, stored as JSON in `organizations.settings`.

    Every key is declared here with its type and default, so a new setting needs no migration and
    an undeclared key is rejected instead of silently ignored. Private travellers have no
    organization and get the defaults.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    password_login_enabled: bool = Field(
        default=True,
        description=(
            "Whether users may sign in with email and password. If `false`, only the organization's "
            "identity providers are accepted."
        ),
    )

    max_failed_logins: int = Field(
        default=3,
        ge=1,
        le=20,
        description=(
            "Wrong passwords in a row that block signing in with a password. The user gets an email "
            "to change it, which unblocks the account, or waits `login_lock_minutes`."
        ),
    )

    login_lock_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="How long signing in with a password stays blocked after `max_failed_logins`.",
    )

    trusted_networks: list[IPv4Network | IPv6Network] = Field(
        default_factory=list,
        max_length=50,
        description=(
            "Public networks of the organization's offices (CIDRs). Many people share their address, so "
            "it is never blocked for failed sign ins; each device and each account are still limited."
        ),
    )


class OrganizationRef(DTO):
    """An organization as other modules see it."""

    id: uuid.UUID = Field(
        description="Id of the organization.",
    )

    slug: Slug = Field(
        description="Short unique name, e.g. `acme`.",
    )

    name: str = Field(
        description="Name shown to users.",
    )

    settings: OrganizationSettings = Field(
        description="Configuration of the organization.",
    )

    hostnames: list[str] = Field(
        description="Hostnames of its installation; the first one is used in links sent by email.",
    )


class Installation(DTO):
    """The installation a request arrived at: the main platform or an organization's."""

    host: str = Field(
        description="Hostname of the request, normalized.",
    )

    organization: OrganizationRef | None = Field(
        description="Organization of the installation; `None` for the main platform (private travellers).",
    )

    organization_id: uuid.UUID | None = Field(
        description="Id of the organization; `None` for the main platform.",
    )

    settings: OrganizationSettings = Field(
        description="Settings in force: the organization's, or the platform defaults.",
    )


class NewOrganization(DTO):
    """Data to create an organization."""

    slug: Slug = Field(
        description="Short unique name, e.g. `acme`.",
    )

    name: str = Field(
        min_length=1,
        description="Name shown to users.",
    )

    hostnames: list[Hostname] = Field(
        min_length=1,
        description="Hostnames of its installation, e.g. `acme.localhost`.",
    )

    settings: OrganizationSettings = Field(
        default_factory=OrganizationSettings,
        description="Initial configuration.",
    )
