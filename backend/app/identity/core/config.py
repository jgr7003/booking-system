"""Settings of the identity module, read from environment variables or `.env`."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class IdentitySettings(BaseSettings):
    """Keys, lifetimes and limits of sign in and sessions (03-usuarios-y-acceso.md §10 and §11)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    auth_signing_keys: SecretStr | None = Field(
        default=None,
        description=(
            "Private keys that sign the access tokens (`AUTH_SIGNING_KEYS`): a JSON array of EC P-256 "
            "JWKs, each with its `kid`. The first one signs; the others only verify, while tokens they "
            "signed are still alive. Generate one with `make auth-keygen`."
        ),
    )

    identity_secrets_key: SecretStr | None = Field(
        default=None,
        description=(
            "Key that encrypts the client secrets of identity providers in the database "
            "(`IDENTITY_SECRETS_KEY`, a Fernet key). Generate one with `make auth-keygen`."
        ),
    )

    oidc_cache_ttl_s: int = Field(
        default=3600,
        description="How long Redis keeps the discovery document and the keys of each identity provider.",
    )

    login_attempt_ttl_s: int = Field(
        default=600,
        description="Lifetime of a sign in through a provider, and of the decision to create the account.",
    )

    auth_audience: str = Field(
        default="booking-api",
        description="`aud` of the access tokens (`AUTH_AUDIENCE`).",
    )

    access_token_ttl_s: int = Field(
        default=600,
        description="Lifetime of an access token, in seconds.",
    )

    session_idle_ttl_s: int = Field(
        default=30 * 24 * 3600,
        description="A device session ends after this many seconds without a refresh.",
    )

    session_max_ttl_s: int = Field(
        default=90 * 24 * 3600,
        description="A device session ends this many seconds after sign in, whatever its use.",
    )

    dpop_max_age_s: int = Field(
        default=60,
        description="How old (or how far in the future, for clock skew) the `iat` of a DPoP proof may be.",
    )

    session_cache_ttl_s: int = Field(
        default=60,
        description="How long Redis remembers that a session is active; revoking it deletes the entry at once.",
    )

    device_failed_logins_limit: int = Field(
        default=10,
        description="Failed password sign ins from one device (its DPoP key) in `ip_window_s` that stop it until the window ends.",
    )

    ip_failed_logins_limit: int = Field(
        default=20,
        description="Failed password sign ins from one address of an installation in `ip_window_s` that block it there.",
    )

    ip_distinct_emails_limit: int = Field(
        default=10,
        description="Different emails tried from one address in `ip_window_s` that block it (someone guessing accounts).",
    )

    ip_window_s: int = Field(
        default=15 * 60,
        description="Window of the per-device and per-address counters, in seconds.",
    )

    ip_block_minutes: int = Field(
        default=60,
        description="How long a blocked address can't sign in.",
    )


@lru_cache
def get_identity_settings() -> IdentitySettings:
    """Returns the settings, loaded once per process.

    Returns:
        The cached `IdentitySettings`. Tests call `cache_clear()` to reload them.
    """
    return IdentitySettings()
