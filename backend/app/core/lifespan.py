"""Startup and shutdown of the resources shared by every request."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from fastapi import FastAPI

from app.core.cache import create_redis
from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Creates the shared HTTP client, database engine and Redis client, and closes them on shutdown.

    They are stored in `app.state` and reached through the dependencies of `app.core.http`,
    `app.core.db` and `app.core.cache`.

    Args:
        app: The FastAPI application.

    Yields:
        Control back to FastAPI while the application is running.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url)
    redis = create_redis(settings.redis_url, settings.cache_timeout_s)
    async with httpx2.AsyncClient() as http_client:
        app.state.http_client = http_client
        app.state.session_factory = create_session_factory(engine)
        app.state.redis = redis
        try:
            yield
        finally:
            await redis.aclose()
            await engine.dispose()
