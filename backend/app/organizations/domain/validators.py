"""Validated types of the organizations module."""

import re
from typing import Annotated

from pydantic import AfterValidator

# Lower-case letters, digits and inner hyphens, e.g. `acme` or `acme-travel`.
_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,48}[a-z0-9])?$")

# A DNS hostname: labels of letters, digits and inner hyphens, separated by dots.
_HOSTNAME = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$")


def normalize_host(host: str) -> str:
    """Normalizes the value of a `Host` header: lower case, without port or trailing dot.

    Args:
        host: The header value, e.g. `Acme.LocalHost:5173`.

    Returns:
        The bare hostname, e.g. `acme.localhost`.
    """
    host = host.strip().lower()
    if host.startswith("["):
        # IPv6 literal, e.g. `[::1]:8000`.
        return host[: host.find("]") + 1]
    return host.rsplit(":", 1)[0].rstrip(".")


def _slug(value: str) -> str:
    """Checks a slug."""
    if not _SLUG.match(value):
        raise ValueError("Use lower-case letters, digits and hyphens (max 50).")
    return value


def _hostname(value: str) -> str:
    """Normalizes and checks a hostname."""
    value = normalize_host(value)
    if not _HOSTNAME.match(value):
        raise ValueError("Not a valid hostname.")
    return value


# Short unique name of an organization, e.g. `acme`.
Slug = Annotated[str, AfterValidator(_slug)]

# Hostname of an installation, normalized, e.g. `acme.localhost`.
Hostname = Annotated[str, AfterValidator(_hostname)]
