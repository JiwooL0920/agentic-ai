"""Session management schemas."""


from pydantic import BaseModel


class SessionListResponse(BaseModel):
    """Response for session list endpoint."""

    sessions: list[dict]
    total: int


class SessionDetailResponse(BaseModel):
    """Response for session detail with messages."""

    session_id: str
    blueprint: str
    title: str | None = None
    session_state: str
    messages: list[dict]
    created_on: str
    modified_on: str


class UpdateSessionStateRequest(BaseModel):
    """Request to update session state."""

    state: str  # "active", "pinned", "unpinned", "archived"


class UpdateSessionTitleRequest(BaseModel):
    """Request to update session title."""

    title: str
