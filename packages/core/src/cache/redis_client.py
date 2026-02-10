"""
Redis Sentinel client facade for backward compatibility.

This module maintains the original RedisSentinelClient API while internally
using the new modular components (RedisClient, SessionCache, AgentStateCache,
RateLimiter).
"""

import structlog

from .agent_state_cache import AgentStateCache
from .base import RedisClient
from .rate_limiter import RateLimiter
from .session_cache import SessionCache

logger = structlog.get_logger()


class RedisSentinelClient:
    """
    Facade over modular Redis cache components.

    Maintains backward compatibility with the original API while delegating
    to specialized cache modules internally.
    """

    def __init__(self) -> None:
        self._base_client = RedisClient()
        self._sessions: SessionCache | None = None
        self._agents: AgentStateCache | None = None
        self._rate_limiter: RateLimiter | None = None

    async def connect(self) -> None:
        """Connect to Redis and initialize cache modules."""
        await self._base_client.connect()
        self._sessions = SessionCache(self._base_client)
        self._agents = AgentStateCache(self._base_client)
        self._rate_limiter = RateLimiter(self._base_client)

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        await self._base_client.disconnect()

    @property
    def client(self):
        """Get underlying Redis client for direct operations."""
        return self._base_client.client

    @property
    def sessions(self) -> SessionCache:
        """Get session cache module."""
        if not self._sessions:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._sessions

    @property
    def agents(self) -> AgentStateCache:
        """Get agent state cache module."""
        if not self._agents:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._agents

    @property
    def rate_limiter(self) -> RateLimiter:
        """Get rate limiter module."""
        if not self._rate_limiter:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._rate_limiter

    async def cache_session(self, session_id: str, data: dict, ttl: int = 3600) -> None:
        """Cache session metadata."""
        await self.sessions.cache(session_id, data, ttl)

    async def get_cached_session(self, session_id: str) -> dict | None:
        """Get cached session."""
        return await self.sessions.get(session_id)

    async def invalidate_session(self, session_id: str) -> None:
        """Delete cached session."""
        await self.sessions.invalidate(session_id)

    async def cache_user_sessions(
        self,
        user_id: str,
        blueprint: str,
        sessions: list[dict],
        ttl: int = 300,
    ) -> None:
        """Cache user's session list (for sidebar)."""
        await self.sessions.cache_user_sessions(user_id, blueprint, sessions, ttl)

    async def get_cached_user_sessions(
        self,
        user_id: str,
        blueprint: str,
    ) -> list[dict] | None:
        """Get cached user session list."""
        return await self.sessions.get_user_sessions(user_id, blueprint)

    async def invalidate_user_sessions(self, user_id: str, blueprint: str) -> None:
        """Invalidate user's session list cache."""
        await self.sessions.invalidate_user_sessions(user_id, blueprint)

    async def add_active_agent(self, session_id: str, agent_name: str) -> None:
        """Add agent to session's active agent set."""
        await self.agents.add_active(session_id, agent_name)

    async def get_active_agents(self, session_id: str) -> list[str]:
        """Get list of active agents for session."""
        return await self.agents.get_active(session_id)

    async def remove_active_agent(self, session_id: str, agent_name: str) -> None:
        """Remove agent from session's active set."""
        await self.agents.remove_active(session_id, agent_name)

    async def check_rate_limit(
        self,
        user_id: str,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> bool:
        """Check if user is within rate limit using sliding window."""
        return await self.rate_limiter.check(user_id, max_requests, window_seconds)

    async def cache_context_summary(
        self,
        session_id: str,
        summary: str,
        ttl: int = 3600,
    ) -> None:
        """Cache conversation summary for context window."""
        await self.sessions.cache_context_summary(session_id, summary, ttl)

    async def get_context_summary(self, session_id: str) -> str | None:
        """Get cached context summary."""
        return await self.sessions.get_context_summary(session_id)

    async def batch_cache_sessions(
        self,
        sessions: list[tuple[str, dict, int]],
    ) -> None:
        """Cache multiple sessions in a single pipeline."""
        await self.sessions.batch_cache(sessions)


_redis_client: RedisSentinelClient | None = None


async def init_redis() -> None:
    global _redis_client
    client = RedisSentinelClient()
    await client.connect()
    _redis_client = client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None


def get_redis_client() -> RedisSentinelClient:
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_client
