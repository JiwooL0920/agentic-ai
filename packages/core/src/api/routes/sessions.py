"""Session management API routes."""

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from redis.exceptions import RedisError
import structlog

from ...repositories.session_repository import SessionRepository, SessionState
from ...repositories.message_repository import MessageRepository
from ...cache.redis_client import get_redis_client

router = APIRouter()
logger = structlog.get_logger()


# ========================================================================
# Request/Response Models
# ========================================================================

class SessionListResponse(BaseModel):
    """Response for session list endpoint."""
    sessions: List[dict]
    total: int


class SessionDetailResponse(BaseModel):
    """Response for session detail with messages."""
    session_id: str
    blueprint: str
    title: Optional[str] = None
    session_state: str
    messages: List[dict]
    created_on: str
    modified_on: str


class UpdateSessionStateRequest(BaseModel):
    """Request to update session state."""
    state: str  # "active", "pinned", "unpinned", "archived"


class UpdateSessionTitleRequest(BaseModel):
    """Request to update session title."""
    title: str


# ========================================================================
# Endpoints
# ========================================================================

@router.get("/sessions/new")
async def get_new_session_id():
    """
    Generate a new session UUID.
    
    Frontend can call this before starting a conversation.
    """
    return {"session_id": uuid4().hex}


@router.post("/blueprints/{blueprint}/sessions")
async def create_session(
    blueprint: str,
    user_id: str = "user",  # TODO: Extract from auth
):
    """Create a new chat session."""
    session_repo = SessionRepository(blueprint)
    redis = get_redis_client()
    
    session = await session_repo.create_session(user_id=user_id)
    
    # Invalidate user's session list cache
    try:
        await redis.invalidate_user_sessions(user_id, blueprint)
    except RedisError as e:
        logger.warning("redis_invalidate_error", error=str(e))
    
    return {"session_id": session["session_id"]}


@router.get("/blueprints/{blueprint}/sessions", response_model=SessionListResponse)
async def get_user_sessions(
    blueprint: str,
    user_id: str = "user",  # TODO: Extract from auth
    include_archived: bool = False,
):
    """
    Get all sessions for a user, sorted by activity.
    
    Pinned sessions appear first, followed by recent sessions.
    """
    redis = get_redis_client()
    
    # Check Redis cache first
    try:
        cached = await redis.get_cached_user_sessions(user_id, blueprint)
        if cached and not include_archived:
            logger.debug("user_sessions_cache_hit", user_id=user_id)
            return SessionListResponse(sessions=cached, total=len(cached))
    except RedisError as e:
        logger.warning("redis_cache_error", error=str(e))
    
    # Query ScyllaDB
    session_repo = SessionRepository(blueprint)
    sessions = await session_repo.get_user_sessions(
        user_id=user_id,
        include_archived=include_archived,
    )
    
    # Cache for sidebar (5 minutes)
    if sessions and not include_archived:
        try:
            await redis.cache_user_sessions(user_id, blueprint, sessions, ttl=300)
        except RedisError as e:
            logger.warning("redis_cache_error", error=str(e))
    
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.get("/blueprints/{blueprint}/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    blueprint: str,
    session_id: str,
):
    """
    Get session history for resuming a conversation.
    
    Returns session metadata and all messages.
    """
    session_repo = SessionRepository(blueprint)
    message_repo = MessageRepository(blueprint)
    
    # Get session metadata
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get messages
    messages = await message_repo.get_session_messages(session_id)
    
    return SessionDetailResponse(
        session_id=session_id,
        blueprint=blueprint,
        title=session.get("session_title"),
        session_state=session.get("session_state", "active"),
        messages=messages,
        created_on=session.get("created_on", ""),
        modified_on=session.get("modified_on", ""),
    )


@router.patch("/blueprints/{blueprint}/sessions/{session_id}/state")
async def update_session_state(
    blueprint: str,
    session_id: str,
    body: UpdateSessionStateRequest,
    user_id: str = "user",  # TODO: Extract from auth
):
    """
    Update session state (pin/unpin/archive).
    
    Pinned sessions appear at the top of the session list.
    """
    session_repo = SessionRepository(blueprint)
    redis = get_redis_client()
    
    try:
        new_state = SessionState(body.state)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state: {body.state}. Must be one of: active, pinned, unpinned, archived"
        )
    
    success = await session_repo.update_state(
        session_id=session_id,
        user_id=user_id,
        new_state=new_state,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Invalidate user's session list cache
    try:
        await redis.invalidate_user_sessions(user_id, blueprint)
    except RedisError as e:
        logger.warning("redis_invalidate_error", error=str(e))
    
    return {"status": "updated", "new_state": new_state.value}


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
    session_repo = SessionRepository(blueprint)
    
    success = await session_repo.update_title(session_id, body.title)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "updated"}
