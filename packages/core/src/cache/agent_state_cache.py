"""Agent state caching operations."""

import structlog

from .base import RedisClient

logger = structlog.get_logger()


class AgentStateCache:
    """Agent state management using Redis sets."""

    PREFIX = "session_agents"
    DEFAULT_TTL = 3600

    def __init__(self, client: RedisClient):
        self._client = client

    def _key(self, session_id: str) -> str:
        return f"{self.PREFIX}:{session_id}"

    async def add_active(self, session_id: str, agent_name: str) -> None:
        """Add agent to session's active agent set."""
        key = self._key(session_id)
        await self._client.sadd(key, agent_name)
        await self._client.expire(key, self.DEFAULT_TTL)

    async def get_active(self, session_id: str) -> list[str]:
        """Get list of active agents for session."""
        agents = await self._client.smembers(self._key(session_id))
        return list(agents) if agents else []

    async def remove_active(self, session_id: str, agent_name: str) -> None:
        """Remove agent from session's active set."""
        await self._client.srem(self._key(session_id), agent_name)

    async def clear(self, session_id: str) -> None:
        """Clear all active agents for a session."""
        await self._client.delete(self._key(session_id))
