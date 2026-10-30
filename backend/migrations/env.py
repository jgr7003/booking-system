"""Alembic environment: runs migrations with the async engine and the app's settings."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.core.db import Base, create_engine

# Every module's models must be imported so autogenerate sees their tables. Each module keeps
# them in its own PostgreSQL schema (00-global.md §4.1); `alembic_version` stays in `public`.
import app.core.messaging.models  # noqa: F401
import app.flights.domain.models.airports  # noqa: F401
import app.flights.domain.models.bookings  # noqa: F401
import app.identity.domain.models.blocked_ips  # noqa: F401
import app.identity.domain.models.email_tokens  # noqa: F401
import app.identity.domain.models.providers  # noqa: F401
import app.identity.domain.models.sessions  # noqa: F401
import app.identity.domain.models.users  # noqa: F401
import app.organizations.domain.models  # noqa: F401
import app.payments.domain.models  # noqa: F401
import app.travellers.domain.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emits the SQL without connecting (`alembic upgrade --sql`)."""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        include_schemas=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Runs the migrations on an open connection."""
    context.configure(connection=connection, target_metadata=target_metadata, include_schemas=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Connects with the async engine and runs the migrations."""
    engine = create_engine(get_settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
