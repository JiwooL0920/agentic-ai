"""Session management schemas."""

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeConfig(BaseModel):
    """Knowledge base configuration for a session.

    Controls which document scopes are used for RAG retrieval.

    Scope Resolution Order:
    1. Agent's knowledge_scope (from YAML) - if include_agent_scopes=True
    2. User's personal documents - if include_user_docs=True
    3. Explicitly selected scopes - active_scopes list
    """

    active_scopes: list[str] = Field(
        default_factory=list,
        description="Explicitly selected scopes (e.g., 'kubernetes', 'python')",
    )
    include_agent_scopes: bool = Field(
        default=True,
        description="Include scopes defined in the agent's YAML config",
    )
    include_user_docs: bool = Field(
        default=True,
        description="Include user's personal uploaded documents",
    )


class SessionListResponse(BaseModel):
    """Response for session list endpoint."""

    sessions: list[dict[str, Any]]
    total: int


class SessionDetailResponse(BaseModel):
    """Response for session detail with messages."""

    session_id: str
    blueprint: str
    title: str | None = None
    session_state: str
    messages: list[dict[str, Any]]
    created_on: str
    modified_on: str
    knowledge_config: KnowledgeConfig | None = None


class UpdateSessionStateRequest(BaseModel):
    """Request to update session state."""

    state: str  # "active", "pinned", "unpinned", "archived"


class UpdateSessionTitleRequest(BaseModel):
    """Request to update session title."""

    title: str


class UpdateKnowledgeConfigRequest(BaseModel):
    """Request to update session knowledge base configuration."""

    knowledge_config: KnowledgeConfig
