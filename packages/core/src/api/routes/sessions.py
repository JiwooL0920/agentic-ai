"""Session management API routes."""

import structlog
from fastapi import APIRouter, HTTPException

from ...schemas import (
    SessionDetailResponse,
    SessionListResponse,
    UpdateSessionStateRequest,
    UpdateSessionTitleRequest,
)
from ...services.session_service import SessionService
from ..dependencies import CurrentUser

router = APIRouter()
logger = structlog.get_logger()


@router.get("/sessions/new")
async def get_new_session_id():
    """
    Generate a new session UUID.

    Frontend can call this before starting a conversation.
    """
    return {"session_id": SessionService.generate_session_id()}


@router.post("/blueprints/{blueprint}/sessions")
async def create_session(
    blueprint: str,
    user: CurrentUser,
):
    """Create a new chat session."""
    service = SessionService(blueprint)
    return await service.create_session(user_id=user.user_id)


@router.get("/blueprints/{blueprint}/sessions", response_model=SessionListResponse)
async def get_user_sessions(
    blueprint: str,
    user: CurrentUser,
    include_archived: bool = False,
):
    """
    Get all sessions for a user, sorted by activity.

    Pinned sessions appear first, followed by recent sessions.
    """
    service = SessionService(blueprint)
    result = await service.get_user_sessions(
        user_id=user.user_id,
        include_archived=include_archived,
    )
    return SessionListResponse(**result)


@router.get(
    "/blueprints/{blueprint}/sessions/{session_id}", response_model=SessionDetailResponse
)
async def get_session(
    blueprint: str,
    session_id: str,
):
    """
    Get session history for resuming a conversation.

    Returns session metadata and all messages.
    """
    service = SessionService(blueprint)
    result = await service.get_session_with_messages(session_id)

    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetailResponse(**result)


@router.patch("/blueprints/{blueprint}/sessions/{session_id}/state")
async def update_session_state(
    blueprint: str,
    session_id: str,
    body: UpdateSessionStateRequest,
    user: CurrentUser,
):
    """
    Update session state (pin/unpin/archive).

    Pinned sessions appear at the top of the session list.
    """
    service = SessionService(blueprint)

    try:
        return await service.update_state(
            session_id=session_id,
            user_id=user.user_id,
            state=body.state,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Session not found") from e


@router.patch("/blueprints/{blueprint}/sessions/{session_id}/title")
async def update_session_title(
    blueprint: str,
    session_id: str,
    body: UpdateSessionTitleRequest,
):
    """
    Update session title.

    Typically auto-set from the first user message.
    """
    service = SessionService(blueprint)

    try:
        return await service.update_title(session_id, body.title)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Session not found") from e
