"""Chat endpoints with streaming support."""

import json
import uuid
from typing import Optional

import structlog
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from redis.exceptions import RedisError
from sse_starlette.sse import EventSourceResponse

from ...orchestrator.supervisor import SupervisorOrchestrator
from ...repositories.session_repository import SessionRepository
from ...repositories.message_repository import MessageRepository
from ...cache.redis_client import get_redis_client
from ..dependencies import CurrentUser

logger = structlog.get_logger()

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request payload."""

    message: str
    session_id: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    """Chat response payload."""

    response: str
    agent: str
    session_id: str


@router.post("/blueprints/{blueprint}/chat")
async def chat(
    request: Request,
    blueprint: str,
    chat_request: ChatRequest,
    user: CurrentUser,
) -> ChatResponse:
    """
    Send a chat message to the blueprint's agents (non-streaming).
    """
    registry = request.app.state.registry
    agents = registry.get_blueprint_agents(blueprint)

    if not agents:
        raise HTTPException(status_code=404, detail=f"Blueprint '{blueprint}' not found")

    session_id = chat_request.session_id or str(uuid.uuid4())
    user_id = user.user_id

    logger.info(
        "chat_request",
        blueprint=blueprint,
        session_id=session_id,
        message_length=len(chat_request.message),
    )

    # Initialize repositories
    session_repo = SessionRepository(blueprint)
    message_repo = MessageRepository(blueprint)

    # Ensure session exists
    session = await session_repo.get_session(session_id)
    if not session:
        await session_repo.create_session(user_id=user_id, session_id=session_id)
        # Set title from first message
        title = chat_request.message[:50] + "..." if len(chat_request.message) > 50 else chat_request.message
        await session_repo.update_title(session_id, title)

    supervisor = SupervisorOrchestrator(agents)

    result = await supervisor.process_query(
        query=chat_request.message,
        user_id=user_id,
        session_id=session_id,
    )

    # Persist conversation turn
    try:
        await message_repo.save_conversation_turn(
            session_id=session_id,
            user_id=user_id,
            user_message=chat_request.message,
            bot_response=result["response"],
            agent=result.get("agent"),
        )
        logger.info("chat_turn_persisted", session_id=session_id)
    except (ClientError, BotoCoreError) as e:
        logger.error("chat_persistence_error", error=str(e))

    return ChatResponse(
        response=result["response"],
        agent=result["agent"],
        session_id=session_id,
    )


@router.post("/blueprints/{blueprint}/chat/stream")
async def chat_stream(
    request: Request,
    blueprint: str,
    chat_request: ChatRequest,
    user: CurrentUser,
):
    """
    Send a chat message with Server-Sent Events streaming.
    """
    registry = request.app.state.registry
    agents = registry.get_blueprint_agents(blueprint)

    if not agents:
        raise HTTPException(status_code=404, detail=f"Blueprint '{blueprint}' not found")

    session_id = chat_request.session_id or str(uuid.uuid4())
    user_id = user.user_id

    logger.info(
        "chat_stream_request",
        blueprint=blueprint,
        session_id=session_id,
    )

    session_repo = SessionRepository(blueprint)
    message_repo = MessageRepository(blueprint)

    try:
        session = await session_repo.get_session(session_id)
        if not session:
            await session_repo.create_session(user_id=user_id, session_id=session_id)
            title = chat_request.message[:50] + "..." if len(chat_request.message) > 50 else chat_request.message
            await session_repo.update_title(session_id, title)
    except (ClientError, BotoCoreError, RedisError) as e:
        logger.warning("session_persistence_disabled", error=str(e))
        # Continue without persistence

    supervisor = SupervisorOrchestrator(agents)

    async def generate():
        """Generate SSE events and persist after completion."""
        accumulated_response = ""
        active_agent = None

        try:
            async for chunk in supervisor.process_query_streaming(
                query=chat_request.message,
                user_id=user_id,
                session_id=session_id,
                blueprint=blueprint,
            ):
                # Accumulate response content
                if chunk.get("type") == "content":
                    accumulated_response += chunk.get("content", "")
                
                # Track active agent
                if chunk.get("agent"):
                    active_agent = chunk["agent"]

                yield {
                    "event": chunk.get("type", "message"),
                    "data": json.dumps(chunk),
                }

            # After streaming completes: persist conversation turn
            if accumulated_response:
                try:
                    await message_repo.save_conversation_turn(
                        session_id=session_id,
                        user_id=user_id,
                        user_message=chat_request.message,
                        bot_response=accumulated_response,
                        agent=active_agent,
                    )

                    # Track active agent in Redis
                    if active_agent:
                        try:
                            redis = get_redis_client()
                            await redis.add_active_agent(session_id, active_agent)
                        except RedisError as e:
                            logger.warning("redis_agent_tracking_error", error=str(e))

                    logger.info(
                        "stream_turn_persisted",
                        session_id=session_id,
                        response_length=len(accumulated_response),
                    )
                except (ClientError, BotoCoreError) as e:
                    logger.error("stream_persistence_error", error=str(e))

            # Send done event
            yield {
                "event": "done",
                "data": json.dumps({"session_id": session_id}),
            }

        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(generate())
