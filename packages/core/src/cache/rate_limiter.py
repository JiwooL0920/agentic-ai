"""Rate limiting using Redis sorted sets with sliding window algorithm."""

import time

import structlog

from .base import RedisClient

logger = structlog.get_logger()


class RateLimiter:
    """
    Rate limiter using Redis sorted sets with sliding window algorithm.

    Each request is stored as a member in a sorted set with its timestamp as the score.
    Old entries are pruned on each check, and the remaining count determines if
    the request is allowed.
    """

    PREFIX = "rate_limit"

    def __init__(self, client: RedisClient):
        self._client = client

    def _key(self, identifier: str) -> str:
        """Generate rate limit key for an identifier (user_id, ip, etc.)."""
        return f"{self.PREFIX}:{identifier}"

    async def check(
        self,
        identifier: str,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> bool:
        """
        Check if identifier is within rate limit using sliding window.

        Args:
            identifier: Unique identifier (user_id, IP address, API key, etc.)
            max_requests: Maximum allowed requests in the window
            window_seconds: Size of the sliding window in seconds

        Returns:
            True if request is allowed, False if rate limited
        """
        key = self._key(identifier)
        now = time.time()
        window_start = now - window_seconds

        pipe = self._client.pipeline()

        # Remove entries older than the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Add current request with timestamp as score
        pipe.zadd(key, {str(now): now})

        # Count requests in the current window
        pipe.zcard(key)

        # Set key expiry to auto-cleanup
        pipe.expire(key, window_seconds)

        results = await pipe.execute()
        request_count = results[2]  # zcard result

        allowed = request_count <= max_requests

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                count=request_count,
                limit=max_requests,
                window=window_seconds,
            )

        return allowed

    async def get_remaining(
        self,
        identifier: str,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> int:
        """
        Get remaining requests allowed in the current window.

        Args:
            identifier: Unique identifier
            max_requests: Maximum allowed requests
            window_seconds: Window size in seconds

        Returns:
            Number of remaining requests (0 if rate limited)
        """
        key = self._key(identifier)
        now = time.time()
        window_start = now - window_seconds

        # Clean old entries first
        await self._client.zremrangebyscore(key, 0, window_start)

        # Get current count
        current_count = await self._client.zcard(key)

        return max(0, max_requests - current_count)

    async def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier."""
        await self._client.delete(self._key(identifier))
        logger.debug("rate_limit_reset", identifier=identifier)

    async def get_retry_after(
        self,
        identifier: str,
        window_seconds: int = 60,
    ) -> float | None:
        """
        Get seconds until the oldest request expires from the window.

        Useful for setting Retry-After header when rate limited.

        Returns:
            Seconds until a slot opens up, or None if not rate limited
        """
        key = self._key(identifier)
        now = time.time()
        window_start = now - window_seconds

        # Get the oldest entry in the current window
        oldest = await self._client.client.zrangebyscore(
            key, window_start, now, start=0, num=1, withscores=True
        )

        if oldest:
            oldest_timestamp = oldest[0][1]
            retry_after = (oldest_timestamp + window_seconds) - now
            return max(0, retry_after)

        return None
