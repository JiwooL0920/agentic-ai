"""Session caching operations."""

import json

import structlog

from .base import RedisClient

logger = structlog.get_logger()


class SessionCache:
    """Session-specific caching operations using Redis."""

    PREFIX_SESSION = "session"
    PREFIX_USER_SESSIONS = "user_sessions"
    PREFIX_CONTEXT = "context_summary"

    def __init__(self, client: RedisClient):
        self._client = client

    def _session_key(self, session_id: str) -> str:
        return f"{self.PREFIX_SESSION}:{session_id}"

    def _user_sessions_key(self, user_id: str, blueprint: str) -> str:
        return f"{self.PREFIX_USER_SESSIONS}:{user_id}:{blueprint}"

    def _context_key(self, session_id: str) -> str:
        return f"{self.PREFIX_CONTEXT}:{session_id}"

    async def cache(
        self,
        session_id: str,
        data: dict,
        ttl: int = 3600,
    ) -> None:
        """Cache session metadata."""
        await self._client.set(
            self._session_key(session_id),
            json.dumps(data),
            ttl=ttl,
        )
        logger.debug("session_cached", session_id=session_id, ttl=ttl)

    async def get(self, session_id: str) -> dict | None:
        """Get cached session."""
        data = await self._client.get(self._session_key(session_id))
        return json.loads(data) if data else None

    async def invalidate(self, session_id: str) -> None:
        """Delete cached session."""
        await self._client.delete(self._session_key(session_id))
        logger.debug("session_invalidated", session_id=session_id)

    async def cache_user_sessions(
        self,
        user_id: str,
        blueprint: str,
        sessions: list[dict],
        ttl: int = 300,
    ) -> None:
        """Cache user's session list (for sidebar)."""
        await self._client.set(
            self._user_sessions_key(user_id, blueprint),
            json.dumps(sessions),
            ttl=ttl,
        )

    async def get_user_sessions(
        self,
        user_id: str,
        blueprint: str,
    ) -> list[dict] | None:
        """Get cached user session list."""
        data = await self._client.get(self._user_sessions_key(user_id, blueprint))
        return json.loads(data) if data else None

    async def invalidate_user_sessions(self, user_id: str, blueprint: str) -> None:
        """Invalidate user's session list cache."""
        await self._client.delete(self._user_sessions_key(user_id, blueprint))

    async def cache_context_summary(
        self,
        session_id: str,
        summary: str,
        ttl: int = 3600,
    ) -> None:
        """Cache conversation summary for context window."""
        await self._client.set(
            self._context_key(session_id),
            summary,
            ttl=ttl,
        )

    async def get_context_summary(self, session_id: str) -> str | None:
        """Get cached context summary."""
        return await self._client.get(self._context_key(session_id))

    async def batch_cache(
        self,
        sessions: list[tuple[str, dict, int]],
    ) -> None:
        """Cache multiple sessions in a single pipeline."""
        if not sessions:
            return

        pipe = self._client.pipeline()
        for session_id, data, ttl in sessions:
            pipe.setex(self._session_key(session_id), ttl, json.dumps(data))

        await pipe.execute()
        logger.debug("sessions_batch_cached", count=len(sessions))
