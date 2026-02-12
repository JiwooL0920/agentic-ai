"""
Chat service - orchestrates chat interactions.

Extracted from api/routes/chat.py to enable:
- Unit testing without HTTP
- Reuse in CLI/background workers
- Clean separation of concerns
"""

import asyncio
from collections.abc import AsyncIterable
from typing import Any
from uuid import uuid4

import structlog
from botocore.exceptions import BotoCoreError, ClientError
from redis.exceptions import RedisError

from ..cache.redis_client import get_redis_client
from ..orchestrator.supervisor import SupervisorOrchestrator
from ..repositories.message_repository import MessageRepository
from ..repositories.session_repository import SessionRepository

logger = structlog.get_logger()


class ChatService:
    """
    Handles chat business logic.

    Responsibilities:
    - Session creation/validation
    - Message persistence
    - Agent orchestration delegation
    - Response accumulation for streaming
    """

    def __init__(
        self,
        blueprint: str,
        session_repo: SessionRepository,
        message_repo: MessageRepository,
        orchestrator: SupervisorOrchestrator,
    ):
        self._blueprint = blueprint
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._orchestrator = orchestrator
        self._logger = logger.bind(service="ChatService", blueprint=blueprint)

    async def ensure_session(
        self,
        session_id: str | None,
        user_id: str,
        first_message: str,
    ) -> str:
        """
        Ensure session exists, creating if necessary.

        Args:
            session_id: Optional existing session ID
            user_id: User identifier
            first_message: First message (used for title if creating new session)

        Returns:
            Session ID (existing or newly created)
        """
        session_id = session_id or str(uuid4())

        session = await self._session_repo.get_session(session_id)
        if not session:
            await self._session_repo.create_session(user_id=user_id, session_id=session_id)
            # Set title from first message
            title = (
                first_message[:50] + "..." if len(first_message) > 50 else first_message
            )
            await self._session_repo.update_title(session_id, title)
            self._logger.info("session_created", session_id=session_id)

        return session_id

    async def process_chat(
        self,
        message: str,
        session_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Process chat message (non-streaming).

        Args:
            message: User's message
            session_id: Session identifier
            user_id: User identifier

        Returns:
            Dict with response, agent, and session_id
        """
        self._logger.info(
            "processing_chat",
            session_id=session_id,
            message_length=len(message),
        )

        result = await self._orchestrator.process_query(
            query=message,
            user_id=user_id,
            session_id=session_id,
        )

        # Persist conversation turn
        try:
            await self._message_repo.save_conversation_turn(
                session_id=session_id,
                user_id=user_id,
                user_message=message,
                bot_response=result["response"],
                agent=result.get("agent"),
            )
            self._logger.info("chat_persisted", session_id=session_id)
        except (ClientError, BotoCoreError) as e:
            self._logger.error("persistence_error", error=str(e))

        return result

    async def process_chat_streaming(
        self,
        message: str,
        session_id: str,
        user_id: str,
    ) -> AsyncIterable[dict[str, Any]]:
        """
        Process chat message with streaming.

        Args:
            message: User's message
            session_id: Session identifier
            user_id: User identifier

        Yields:
            Stream chunks with type, content, agent, etc.

        Raises:
            asyncio.CancelledError: If the task is cancelled
        """
        self._logger.info(
            "processing_chat_streaming",
            session_id=session_id,
        )

        session = await self._session_repo.get_session(session_id)
        knowledge_config = session.get("knowledge_config") if session else None

        accumulated_response = ""
        active_agent = None

        try:
            async for chunk in self._orchestrator.process_query_streaming(
                query=message,
                user_id=user_id,
                session_id=session_id,
                blueprint=self._blueprint,
                knowledge_config=knowledge_config,
            ):
                # Track for persistence
                if chunk.get("type") == "content":
                    accumulated_response += chunk.get("content", "")
                if chunk.get("agent"):
                    active_agent = chunk["agent"]

                yield chunk

            # Persist after streaming completes
            if accumulated_response:
                await self._persist_streaming_response(
                    session_id=session_id,
                    user_id=user_id,
                    message=message,
                    accumulated_response=accumulated_response,
                    active_agent=active_agent,
                )

        except asyncio.CancelledError:
            self._logger.info(
                "streaming_cancelled",
                session_id=session_id,
                accumulated_length=len(accumulated_response),
            )
            # Persist partial response if available
            if accumulated_response:
                await self._persist_streaming_response(
                    session_id=session_id,
                    user_id=user_id,
                    message=message,
                    accumulated_response=accumulated_response + "\n\n[Response cancelled by user]",
                    active_agent=active_agent,
                )
            yield {"type": "cancelled", "message": "Response cancelled by user"}
            raise  # Re-raise to signal cancellation

        except Exception as e:
            self._logger.error("streaming_error", error=str(e))
            yield {"type": "error", "error": str(e)}

    async def _persist_streaming_response(
        self,
        session_id: str,
        user_id: str,
        message: str,
        accumulated_response: str,
        active_agent: str | None,
    ) -> None:
        """Persist the completed streaming response."""
        try:
            await self._message_repo.save_conversation_turn(
                session_id=session_id,
                user_id=user_id,
                user_message=message,
                bot_response=accumulated_response,
                agent=active_agent,
            )

            # Track active agent in Redis (optional)
            if active_agent:
                try:
                    redis = get_redis_client()
                    if redis:
                        await redis.add_active_agent(session_id, active_agent)
                except RedisError as e:
                    self._logger.warning("redis_tracking_error", error=str(e))

            self._logger.info(
                "stream_persisted",
                session_id=session_id,
                response_length=len(accumulated_response),
            )
        except (ClientError, BotoCoreError) as e:
            self._logger.error("persistence_error", error=str(e))
