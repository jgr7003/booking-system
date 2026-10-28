"""Application-wide settings, read from environment variables or `.env`."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings shared by every module."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(
        default="booking-system",
        description="Name shown in the OpenAPI docs.",
    )

    pricing_secret: SecretStr = Field(
        default=SecretStr("local-dev-secret"),
        description="Seed for the deterministic markup (`PRICING_SECRET`). The default is only for local development.",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://booking:booking@localhost:5432/booking",
        description="SQLAlchemy URL of the PostgreSQL database (`DATABASE_URL`).",
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL of the Redis cache (`REDIS_URL`).",
    )

    rabbitmq_url: str = Field(
        default="amqp://booking:booking@localhost:5672/",
        description="AMQP URL of RabbitMQ, the transport of events between the API and the workers (`RABBITMQ_URL`).",
    )

    app_url: str = Field(
        default="http://localhost:5173",
        description="Public URL of the web app, for links in emails (`APP_URL`).",
    )

    outbox_poll_interval_s: float = Field(
        default=0.5,
        description="How long the outbox relay waits before looking again when there was nothing to publish.",
    )

    cache_timeout_s: float = Field(
        default=0.5,
        description="Max wait for a Redis command; past it the cache is skipped and the database is used.",
    )


@lru_cache
def get_settings() -> Settings:
    """Returns the settings, loaded once per process.

    Returns:
        The cached `Settings` instance. Tests call `get_settings.cache_clear()` to reload it.
    """
    return Settings()
