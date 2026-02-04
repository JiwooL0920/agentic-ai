"""Chat endpoints with streaming support."""

import json
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ...orchestrator.supervisor import SupervisorOrchestrator

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
) -> ChatResponse:
    """
    Send a chat message to the blueprint's agents (non-streaming).
    """
    registry = request.app.state.registry
    agents = registry.get_blueprint_agents(blueprint)

    if not agents:
        raise HTTPException(status_code=404, detail=f"Blueprint '{blueprint}' not found")

    session_id = chat_request.session_id or str(uuid.uuid4())
    user_id = "user"  # TODO: Add authentication

    logger.info(
        "chat_request",
        blueprint=blueprint,
        session_id=session_id,
        message_length=len(chat_request.message),
    )

    supervisor = SupervisorOrchestrator(agents)

    result = await supervisor.process_query(
        query=chat_request.message,
        user_id=user_id,
        session_id=session_id,
    )

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
):
    """
    Send a chat message with Server-Sent Events streaming.
    """
    registry = request.app.state.registry
    agents = registry.get_blueprint_agents(blueprint)

    if not agents:
        raise HTTPException(status_code=404, detail=f"Blueprint '{blueprint}' not found")

    session_id = chat_request.session_id or str(uuid.uuid4())
    user_id = "user"

    logger.info(
        "chat_stream_request",
        blueprint=blueprint,
        session_id=session_id,
    )

    supervisor = SupervisorOrchestrator(agents)

    async def generate():
        """Generate SSE events."""
        try:
            async for chunk in supervisor.process_query_streaming(
                query=chat_request.message,
                user_id=user_id,
                session_id=session_id,
            ):
                yield {
                    "event": chunk.get("type", "message"),
                    "data": json.dumps(chunk),
                }
        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(generate())


@router.get("/blueprints/{blueprint}/sessions/{session_id}")
async def get_session(
    request: Request,
    blueprint: str,
    session_id: str,
):
    """Get session history (placeholder - implement with storage)."""
    # TODO: Implement with DynamoDB storage
    return {
        "session_id": session_id,
        "blueprint": blueprint,
        "messages": [],
    }
