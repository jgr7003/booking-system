"""PostgreSQL access shared by every module: declarative base, engine and sessions."""

from collections.abc import AsyncIterator
from typing import Any

from fastapi import Request
from sqlalchemy import ColumnElement, MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Predictable constraint and index names, so Alembic migrations are stable.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base of every database model. Models live in `<module>/domain/models.py`."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_engine(url: str) -> AsyncEngine:
    """Creates the async engine.

    Args:
        url: SQLAlchemy URL, e.g. `postgresql+asyncpg://user:pass@host/db`.

    Returns:
        An engine with a connection pool; dispose it on shutdown.
    """
    return create_async_engine(url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Creates the factory of sessions bound to `engine`.

    Args:
        engine: The async engine.

    Returns:
        A session factory. Objects stay usable after commit (`expire_on_commit=False`).
    """
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that provides a session for the duration of a request.

    Args:
        request: The incoming request, used to reach the session factory in the app state.

    Yields:
        A session, closed when the request ends.
    """
    async with request.app.state.session_factory() as session:
        yield session


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """FastAPI dependency that provides the session factory, for long requests (e.g. SSE).

    A streaming response shouldn't hold a connection for its whole life: it opens a short
    session for each read instead.

    Args:
        request: The incoming request, used to reach the session factory in the app state.

    Returns:
        The session factory.
    """
    return request.app.state.session_factory


def equals_or_null(column: ColumnElement[Any], value: Any) -> ColumnElement[bool]:
    """`column = value`, or `column IS NULL` when the value is `None`.

    Use it instead of `IS NOT DISTINCT FROM` on indexed columns: with a bound parameter PostgreSQL
    can't use an index for `IS NOT DISTINCT FROM`, so it scans and filters row by row. Both forms
    here are indexable (e.g. `organization_id`, which is `NULL` for private travellers).

    Args:
        column: The column, e.g. `User.organization_id`.
        value: The value to compare with.

    Returns:
        The condition.
    """
    return column.is_(None) if value is None else column == value
