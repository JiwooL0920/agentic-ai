"""
Session service - manages chat session lifecycle.

Extracted from api/routes/sessions.py to enable:
- Unit testing without HTTP
- Reuse in CLI/background workers
- Clean separation of concerns
"""

from uuid import uuid4

import structlog
from redis.exceptions import RedisError

from ..cache.redis_client import get_redis_client
from ..repositories.message_repository import MessageRepository
from ..repositories.session_repository import SessionRepository, SessionState

logger = structlog.get_logger()


class SessionService:
    """
    Handles session management business logic.

    Responsibilities:
    - Session CRUD operations
    - Session state management (pin/unpin/archive)
    - Caching coordination
    - Session listing with sorting
    """

    def __init__(
        self,
        blueprint: str,
        session_repo: SessionRepository | None = None,
        message_repo: MessageRepository | None = None,
    ):
        self._blueprint = blueprint
        self._session_repo = session_repo or SessionRepository(blueprint)
        self._message_repo = message_repo or MessageRepository(blueprint)
        self._redis = get_redis_client()
        self._logger = logger.bind(service="SessionService", blueprint=blueprint)

    @staticmethod
    def generate_session_id() -> str:
        """Generate a new session UUID."""
        return uuid4().hex

    async def create_session(self, user_id: str) -> dict:
        """
        Create a new chat session.

        Args:
            user_id: User identifier

        Returns:
            Dict with session_id
        """
        session = await self._session_repo.create_session(user_id=user_id)

        # Invalidate user's session list cache
        try:
            if self._redis:
                await self._redis.invalidate_user_sessions(user_id, self._blueprint)
        except RedisError as e:
            self._logger.warning("redis_invalidate_error", error=str(e))

        self._logger.info("session_created", session_id=session["session_id"])
        return {"session_id": session["session_id"]}

    async def get_user_sessions(
        self,
        user_id: str,
        include_archived: bool = False,
    ) -> dict:
        """
        Get all sessions for a user, sorted by activity.

        Pinned sessions appear first, followed by recent sessions.

        Args:
            user_id: User identifier
            include_archived: Whether to include archived sessions

        Returns:
            Dict with sessions list and total count
        """
        # Check Redis cache first
        try:
            if self._redis:
                cached = await self._redis.get_cached_user_sessions(user_id, self._blueprint)
                if cached and not include_archived:
                    self._logger.debug("user_sessions_cache_hit", user_id=user_id)
                    return {"sessions": cached, "total": len(cached)}
        except RedisError as e:
            self._logger.warning("redis_cache_error", error=str(e))

        # Query ScyllaDB
        raw_sessions = await self._session_repo.get_user_sessions(
            user_id=user_id,
            include_archived=include_archived,
        )

        # Map field names for frontend compatibility
        sessions = [
            {
                "session_id": s.get("session_id"),
                "title": s.get("session_title"),
                "session_state": s.get("session_state", "active"),
                "message_count": s.get("message_count", 0),
                "created_on": s.get("created_on", ""),
                "modified_on": s.get("modified_on", ""),
            }
            for s in raw_sessions
        ]

        # Cache for sidebar (5 minutes)
        if sessions and not include_archived:
            try:
                if self._redis:
                    await self._redis.cache_user_sessions(
                        user_id, self._blueprint, sessions, ttl=300
                    )
            except RedisError as e:
                self._logger.warning("redis_cache_error", error=str(e))

        return {"sessions": sessions, "total": len(sessions)}

    async def get_session_with_messages(self, session_id: str) -> dict | None:
        """
        Get session detail with all messages for resuming a conversation.

        Args:
            session_id: Session identifier

        Returns:
            Dict with session metadata and messages, or None if not found
        """
        # Get session metadata
        session = await self._session_repo.get_session(session_id)
        if not session:
            return None

        # Get messages
        messages = await self._message_repo.get_session_messages(session_id)

        return {
            "session_id": session_id,
            "blueprint": self._blueprint,
            "title": session.get("session_title"),
            "session_state": session.get("session_state", "active"),
            "messages": messages,
            "created_on": session.get("created_on", ""),
            "modified_on": session.get("modified_on", ""),
        }

    async def update_state(
        self,
        session_id: str,
        user_id: str,
        state: str,
    ) -> dict:
        """
        Update session state (pin/unpin/archive).

        Args:
            session_id: Session identifier
            user_id: User identifier
            state: New state ("active", "pinned", "unpinned", "archived")

        Returns:
            Dict with status and new_state

        Raises:
            ValueError: If state is invalid
            KeyError: If session not found
        """
        try:
            new_state = SessionState(state)
        except ValueError as err:
            raise ValueError(
                f"Invalid state: {state}. Must be one of: active, pinned, unpinned, archived"
            ) from err

        success = await self._session_repo.update_state(
            session_id=session_id,
            user_id=user_id,
            new_state=new_state,
        )

        if not success:
            raise KeyError(f"Session not found: {session_id}")

        # Invalidate user's session list cache
        try:
            if self._redis:
                await self._redis.invalidate_user_sessions(user_id, self._blueprint)
        except RedisError as e:
            self._logger.warning("redis_invalidate_error", error=str(e))

        self._logger.info(
            "session_state_updated",
            session_id=session_id,
            new_state=new_state.value,
        )

        return {"status": "updated", "new_state": new_state.value}

    async def update_title(self, session_id: str, title: str) -> dict:
        """
        Update session title.

        Typically auto-set from the first user message.

        Args:
            session_id: Session identifier
            title: New title

        Returns:
            Dict with status

        Raises:
            KeyError: If session not found
        """
        success = await self._session_repo.update_title(session_id, title)

        if not success:
            raise KeyError(f"Session not found: {session_id}")

        self._logger.info("session_title_updated", session_id=session_id)
        return {"status": "updated"}
