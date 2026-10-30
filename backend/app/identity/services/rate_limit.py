"""Counters of attempts in Redis, to slow down password guessing and email flooding."""

import logging
from datetime import timedelta

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.identity.domain.errors.passwords import TooManyAttemptsError

logger = logging.getLogger(__name__)

# Prefix of the Redis keys of the counters.
RATE_LIMIT_PREFIX = "identity:v1:rate:"


class RateLimiter:
    """Fixed-window counters. Without Redis nothing is limited and a warning is logged.

    Losing a counter only forgets some attempts; it never blocks a legitimate user, so Redis can
    keep them.
    """

    def __init__(self, redis: Redis | None) -> None:
        """Initializes the limiter.

        Args:
            redis: Redis client; `None` disables the limits.
        """
        self._redis = redis

    async def hit(self, action: str, subject: str, *, limit: int, window: timedelta) -> None:
        """Counts an attempt and fails if the limit was passed.

        Args:
            action: What is counted, e.g. `login-email`.
            subject: Whose attempts, e.g. the email or the address.
            limit: Attempts allowed in the window.
            window: Length of the window.

        Raises:
            TooManyAttemptsError: The subject passed the limit.
        """
        if self._redis is None:
            return
        key = f"{RATE_LIMIT_PREFIX}{action}:{subject}"
        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, int(window.total_seconds()))
        except RedisError as exc:
            logger.warning("Rate limit of %s skipped, Redis failed: %s", action, exc)
            return
        if count > limit:
            raise TooManyAttemptsError("Too many attempts. Wait a few minutes and try again.")
