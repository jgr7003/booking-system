"""Redis cache shared by every module.

Redis is never the source of truth: if it fails, callers fall back to the database.
"""

import json
import logging
from typing import Any

from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


def create_redis(url: str, timeout_s: float) -> Redis:
    """Creates the Redis client.

    Args:
        url: Redis URL, e.g. `redis://redis:6379/0`.
        timeout_s: Max wait to connect and for each command.

    Returns:
        A client with a connection pool; close it on shutdown.
    """
    return Redis.from_url(url, socket_timeout=timeout_s, socket_connect_timeout=timeout_s, decode_responses=True)


def get_redis(request: Request) -> Redis:
    """FastAPI dependency that provides the shared Redis client.

    Args:
        request: The incoming request, used to reach the application state.

    Returns:
        The client created in the lifespan.
    """
    return request.app.state.redis


class JsonCache:
    """Cache-aside helper that stores JSON values and never raises on Redis failures."""

    def __init__(self, redis: Redis) -> None:
        """Initializes the cache.

        Args:
            redis: Redis client.
        """
        self._redis = redis

    async def get(self, key: str) -> Any | None:
        """Reads a value.

        Args:
            key: Cache key.

        Returns:
            The decoded value, or `None` if it's missing or Redis failed.
        """
        try:
            raw = await self._redis.get(key)
        except RedisError as exc:
            logger.warning("Cache read failed for %s: %s", key, exc)
            return None
        return json.loads(raw) if raw is not None else None

    async def set(self, key: str, value: Any, ttl_s: int) -> None:
        """Stores a value; failures are logged and ignored.

        Args:
            key: Cache key.
            value: JSON-serializable value.
            ttl_s: Time to live, in seconds.
        """
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl_s)
        except RedisError as exc:
            logger.warning("Cache write failed for %s: %s", key, exc)

    async def delete_prefix(self, prefix: str) -> int:
        """Deletes every key that starts with `prefix`.

        Args:
            prefix: Key prefix, e.g. `airports:v1:`.

        Returns:
            How many keys were deleted (0 if Redis failed).
        """
        deleted = 0
        try:
            async for key in self._redis.scan_iter(match=f"{prefix}*", count=500):
                deleted += await self._redis.delete(key)
        except RedisError as exc:
            logger.warning("Cache invalidation failed for %s*: %s", prefix, exc)
        return deleted
