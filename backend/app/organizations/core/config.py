"""Settings of the organizations module, read from environment variables or `.env`."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class InstallationSettings(BaseSettings):
    """How a request is matched to its installation: the main platform or an organization."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    platform_hosts: Annotated[frozenset[str], NoDecode] = Field(
        default=frozenset({"localhost", "127.0.0.1"}),
        description=(
            "Hostnames of the main installation, the one of private travellers (`PLATFORM_HOSTS`, "
            "comma separated). Any other host must belong to an organization."
        ),
    )

    @field_validator("platform_hosts", mode="before")
    @classmethod
    def _split_hosts(cls, value: object) -> object:
        """Reads a comma-separated list of hostnames, in lower case."""
        if isinstance(value, str):
            return frozenset(h.strip().lower() for h in value.split(",") if h.strip())
        return value


@lru_cache
def get_installation_settings() -> InstallationSettings:
    """Returns the settings, loaded once per process.

    Returns:
        The cached `InstallationSettings`. Tests call `cache_clear()` to reload them.
    """
    return InstallationSettings()
