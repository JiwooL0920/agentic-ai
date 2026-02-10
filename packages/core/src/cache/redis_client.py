"""
Redis Sentinel client for session caching and agent state management.

Uses Redis Sentinel for high availability with automatic failover.
"""

import json
import time

import redis.asyncio as aioredis
import structlog
from redis.asyncio.sentinel import Sentinel
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from ..config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class RedisSentinelClient:
    """
    Async Redis Sentinel client for session caching and state management.

    Provides:
    - Session caching with TTL
    - Agent state management (active agents per session)
    - Rate limiting with sliding window
    - Context summary caching
    """

    def __init__(self):
        self._sentinel: Sentinel | None = None
        self._master: aioredis.Redis | None = None
        self._master_name = "mymaster"

    async def connect(self):
        """Connect to Redis Sentinel or fallback to direct connection."""
        try:
            # Try Sentinel first
            sentinel_hosts = [(settings.redis_host, settings.redis_port)]

            self._sentinel = Sentinel(
                sentinel_hosts,
                socket_timeout=5.0,
                password=settings.redis_password,
            )

            self._master = self._sentinel.master_for(
                self._master_name,
                socket_timeout=5.0,
                decode_responses=True,
            )

            # Test connection
            await self._master.ping()
            logger.info("redis_sentinel_connected", master=self._master_name)
        except (RedisConnectionError, RedisError) as e:
            # Fallback to direct Redis connection (non-Sentinel mode)
            logger.warning("redis_sentinel_failed", error=str(e))
            logger.info("falling_back_to_direct_redis")

            self._master = aioredis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                decode_responses=True,
                socket_timeout=5.0,
            )

            await self._master.ping()
            logger.info("redis_direct_connected")

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._master:
            await self._master.aclose()
            logger.info("redis_sentinel_disconnected")

    @property
    def client(self) -> aioredis.Redis:
        """Get master client."""
        if not self._master:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._master

    # =====================================================================
    # Session Caching
    # =====================================================================

    async def cache_session(self, session_id: str, data: dict, ttl: int = 3600):
        """Cache session metadata."""
        key = f"session:{session_id}"
        await self.client.setex(key, ttl, json.dumps(data))
        logger.debug("session_cached", session_id=session_id, ttl=ttl)

    async def get_cached_session(self, session_id: str) -> dict | None:
        """Get cached session."""
        key = f"session:{session_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    async def invalidate_session(self, session_id: str):
        """Delete cached session."""
        key = f"session:{session_id}"
        await self.client.delete(key)
        logger.debug("session_invalidated", session_id=session_id)

    async def cache_user_sessions(
        self,
        user_id: str,
        blueprint: str,
        sessions: list[dict],
        ttl: int = 300,  # 5 minutes
    ):
        """Cache user's session list (for sidebar)."""
        key = f"user_sessions:{user_id}:{blueprint}"
        await self.client.setex(key, ttl, json.dumps(sessions))

    async def get_cached_user_sessions(
        self,
        user_id: str,
        blueprint: str,
    ) -> list[dict] | None:
        """Get cached user session list."""
        key = f"user_sessions:{user_id}:{blueprint}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    async def invalidate_user_sessions(self, user_id: str, blueprint: str):
        """Invalidate user's session list cache."""
        key = f"user_sessions:{user_id}:{blueprint}"
        await self.client.delete(key)

    # =====================================================================
    # Agent State Management
    # =====================================================================

    async def add_active_agent(self, session_id: str, agent_name: str):
        """Add agent to session's active agent set."""
        key = f"session_agents:{session_id}"
        await self.client.sadd(key, agent_name)
        # Set expiry on the key
        await self.client.expire(key, 3600)

    async def get_active_agents(self, session_id: str) -> list[str]:
        """Get list of active agents for session."""
        key = f"session_agents:{session_id}"
        agents = await self.client.smembers(key)
        return list(agents) if agents else []

    async def remove_active_agent(self, session_id: str, agent_name: str):
        """Remove agent from session's active set."""
        key = f"session_agents:{session_id}"
        await self.client.srem(key, agent_name)

    # =====================================================================
    # Rate Limiting (Sliding Window)
    # =====================================================================

    async def check_rate_limit(
        self,
        user_id: str,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> bool:
        """
        Check if user is within rate limit using sliding window.

        Returns True if allowed, False if rate limited.
        """
        key = f"rate_limit:{user_id}"
        now = time.time()
        window_start = now - window_seconds

        pipe = self.client.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Count requests in window
        pipe.zcard(key)

        # Set expiry
        pipe.expire(key, window_seconds)

        results = await pipe.execute()
        request_count = results[2]  # zcard result

        return request_count <= max_requests

    # =====================================================================
    # Context Summary Caching
    # =====================================================================

    async def cache_context_summary(
        self,
        session_id: str,
        summary: str,
        ttl: int = 3600,
    ):
        """Cache conversation summary for context window."""
        key = f"context_summary:{session_id}"
        await self.client.setex(key, ttl, summary)

    async def get_context_summary(self, session_id: str) -> str | None:
        """Get cached context summary."""
        key = f"context_summary:{session_id}"
        return await self.client.get(key)

    # =====================================================================
    # Batch Operations (Pipeline)
    # =====================================================================

    async def batch_cache_sessions(
        self,
        sessions: list[tuple[str, dict, int]],  # (session_id, data, ttl)
    ):
        """Cache multiple sessions in a single pipeline."""
        pipe = self.client.pipeline()

        for session_id, data, ttl in sessions:
            key = f"session:{session_id}"
            pipe.setex(key, ttl, json.dumps(data))

        await pipe.execute()
        logger.debug("sessions_batch_cached", count=len(sessions))


# Global client singleton
_redis_client: RedisSentinelClient | None = None


async def init_redis():
    """Initialize Redis Sentinel connection (called at app startup)."""
    global _redis_client
    _redis_client = RedisSentinelClient()
    await _redis_client.connect()


async def close_redis():
    """Close Redis connection (called at app shutdown)."""
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None


def get_redis_client() -> RedisSentinelClient:
    """Get global Redis client (must call init_redis first)."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_client
