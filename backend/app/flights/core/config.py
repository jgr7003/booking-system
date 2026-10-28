"""Settings of the flights module, read from `DUFFEL_*` environment variables or `.env`."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DuffelSettings(BaseSettings):
    """Connection settings for the Duffel API."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="DUFFEL_", extra="ignore")

    api_url: str = Field(default="https://api.duffel.com", description="Base URL of the API.")

    api_token: SecretStr = Field(default=SecretStr(""), description="Access token; `duffel_test_...` in test mode.")

    api_version: str = Field(default="v2", description="Value of the `Duffel-Version` header.")

    supplier_timeout_ms: int = Field(
        default=45_000,
        description=(
            "How long Duffel waits for each airline (Duffel accepts 2-60 s). Airlines that don't answer "
            "in time are silently left out: with 10 s, Avianca and LATAM round trips (~20 s in test "
            "mode) were missing. Keep it below `http_timeout_s` so Duffel answers before we give up."
        ),
    )

    http_timeout_s: float = Field(
        default=60,
        description="Timeout of our HTTP requests to Duffel; above `supplier_timeout_ms`.",
    )

    order_timeout_s: float = Field(
        default=130,
        description=(
            "Timeout of the request that creates an order. Airlines can take up to 120 s to answer and "
            "Duffel advises at least 130 s: cutting earlier leaves the outcome unknown while the order "
            "may still be created."
        ),
    )


@lru_cache
def get_duffel_settings() -> DuffelSettings:
    """Returns the Duffel settings, loaded once per process.

    Returns:
        The cached `DuffelSettings`. Tests call `get_duffel_settings.cache_clear()` to reload it.
    """
    return DuffelSettings()
