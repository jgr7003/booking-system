"""Startup and shutdown of the resources shared by every request."""

from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import httpx2
from fastapi import FastAPI

from app.core.cache import create_redis
from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.core.messaging.broadcaster import EventBinding, EventBroadcaster


def create_lifespan(
    event_bindings: Sequence[EventBinding] = (),
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Builds the lifespan of the application.

    Args:
        event_bindings: Events of every module that the API forwards to its SSE connections.

    Returns:
        The lifespan to give to `FastAPI`.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Creates the shared HTTP client, database engine, Redis client and event broadcaster.

        They are stored in `app.state` and reached through the dependencies of `app.core.http`,
        `app.core.db` and `app.core.cache`. RabbitMQ is reached in the background: the API starts
        even if it is down.

        Args:
            app: The FastAPI application.

        Yields:
            Control back to FastAPI while the application is running.
        """
        settings = get_settings()
        engine = create_engine(settings.database_url)
        redis = create_redis(settings.redis_url, settings.cache_timeout_s)
        broadcaster = EventBroadcaster(settings.rabbitmq_url, event_bindings)
        async with httpx2.AsyncClient() as http_client:
            app.state.http_client = http_client
            app.state.session_factory = create_session_factory(engine)
            app.state.redis = redis
            app.state.broadcaster = broadcaster
            await broadcaster.start()
            try:
                yield
            finally:
                await broadcaster.stop()
                await redis.aclose()
                await engine.dispose()

    return lifespan
