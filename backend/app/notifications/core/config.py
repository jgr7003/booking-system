"""Settings of the email senders, read from environment variables or `.env`."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailBackend(StrEnum):
    """Which sender delivers the emails."""

    SMTP = "smtp"
    CONSOLE = "console"


class EmailSettings(BaseSettings):
    """How emails are sent. Changing the environment changes the sender, not the code."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    email_backend: EmailBackend = Field(
        default=EmailBackend.CONSOLE,
        description="`smtp` (Mailpit in development, a real server elsewhere) or `console` (only logs) (`EMAIL_BACKEND`).",
    )

    email_from: str = Field(
        default="Vuelos <reservas@vuelos.test>",
        description="Sender of every email (`EMAIL_FROM`).",
    )

    smtp_host: str = Field(
        default="localhost",
        description="SMTP server (`SMTP_HOST`).",
    )

    smtp_port: int = Field(
        default=1025,
        description="SMTP port (`SMTP_PORT`): 1025 for Mailpit, usually 587 with STARTTLS or 465 with TLS.",
    )

    smtp_username: str | None = Field(
        default=None,
        description="SMTP user, if the server asks for authentication (`SMTP_USERNAME`).",
    )

    smtp_password: SecretStr | None = Field(
        default=None,
        description="SMTP password (`SMTP_PASSWORD`).",
    )

    smtp_starttls: bool = Field(
        default=False,
        description="Upgrade the connection with STARTTLS (`SMTP_STARTTLS`). Off for Mailpit.",
    )

    smtp_ssl: bool = Field(
        default=False,
        description="Connect with implicit TLS, usually on port 465 (`SMTP_SSL`).",
    )

    smtp_timeout_s: float = Field(
        default=15,
        description="Max wait for the SMTP server.",
    )


@lru_cache
def get_email_settings() -> EmailSettings:
    """Returns the email settings, loaded once per process.

    Returns:
        The cached `EmailSettings`. Tests call `get_email_settings.cache_clear()` to reload them.
    """
    return EmailSettings()
