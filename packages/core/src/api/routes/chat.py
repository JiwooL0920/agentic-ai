"""Chat endpoints with streaming support."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from ...orchestrator.supervisor import SupervisorOrchestrator
from ...repositories.message_repository import MessageRepository
from ...repositories.session_repository import SessionRepository
from ...schemas import CancelResponse, ChatRequest, ChatResponse
from ...services.chat_service import ChatService
from ...services.task_manager import get_task_manager
from ..dependencies import CurrentUser, get_registry

logger = structlog.get_logger()

router = APIRouter()


def _create_chat_service(blueprint: str, agents: dict[str, Any]) -> ChatService:
    return ChatService(
        blueprint=blueprint,
        session_repo=SessionRepository(blueprint),
        message_repo=MessageRepository(blueprint),
        orchestrator=SupervisorOrchestrator(agents),
    )


@router.post("/blueprints/{blueprint}/chat")
async def chat(
    request: Request,
    blueprint: str,
    chat_request: ChatRequest,
    user: CurrentUser,
) -> ChatResponse:
    registry = get_registry(request)
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

    service = _create_chat_service(blueprint, agents)

    session_id = await service.ensure_session(
        session_id=session_id,
        user_id=user_id,
        first_message=chat_request.message,
    )

    result = await service.process_chat(
        message=chat_request.message,
        session_id=session_id,
        user_id=user_id,
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
    user: CurrentUser,
) -> EventSourceResponse:
    registry = get_registry(request)
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

    service = _create_chat_service(blueprint, agents)

    session_id = await service.ensure_session(
        session_id=session_id,
        user_id=user_id,
        first_message=chat_request.message,
    )

    task_manager = get_task_manager()

    async def generate() -> AsyncGenerator[dict[str, str], None]:
        try:
            # Register this task for cancellation
            current_task = asyncio.current_task()
            if current_task:
                task_manager.register_task(session_id, current_task)

            async for chunk in service.process_chat_streaming(
                message=chat_request.message,
                session_id=session_id,
                user_id=user_id,
            ):
                yield {
                    "event": chunk.get("type", "message"),
                    "data": json.dumps(chunk),
                }

            yield {
                "event": "done",
                "data": json.dumps({"session_id": session_id}),
            }

        except asyncio.CancelledError:
            logger.info("stream_cancelled_by_user", session_id=session_id)
            yield {
                "event": "cancelled",
                "data": json.dumps({"message": "Response cancelled by user"}),
            }
            raise  # Re-raise to properly close the connection

        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(generate())


@router.post("/blueprints/{blueprint}/sessions/{session_id}/cancel", response_model=CancelResponse)
async def cancel_chat(
    blueprint: str,
    session_id: str,
    user: CurrentUser,
) -> CancelResponse:
    """
    Cancel an active streaming chat request.

    This endpoint cancels any running agent execution for the given session.
    The streaming response will receive a 'cancelled' event before closing.

    Args:
        blueprint: Blueprint name
        session_id: Session identifier
        user: Current authenticated user

    Returns:
        Status of the cancellation operation
    """
    logger.info(
        "cancel_request",
        blueprint=blueprint,
        session_id=session_id,
        user_id=user.user_id,
    )

    task_manager = get_task_manager()
    cancelled = task_manager.cancel_task(session_id)

    if cancelled:
        return CancelResponse(status="cancelled", session_id=session_id)
    else:
        return CancelResponse(
            status="not_found",
            session_id=session_id,
            message="No active task found for this session",
        )
