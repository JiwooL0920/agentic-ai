"""Agent management schemas."""

from typing import Literal

from pydantic import BaseModel


class AgentToggleRequest(BaseModel):
    """Agent toggle request."""

    session_id: str | None = None
    enabled: bool


class AgentStatus(BaseModel):
    """Agent status response."""

    name: str
    agent_id: str
    enabled: bool
    status: str  # "healthy", "degraded", "unavailable"
    model: str
    description: str
    icon: str
    color: str


class AgentHealthResponse(BaseModel):
    """Agent health check response."""

    agents: list[AgentStatus]
    total_count: int
    healthy_count: int
    degraded_count: int
    unavailable_count: int


class AgentToggleResponse(BaseModel):
    """Response from agent toggle endpoint."""

    status: Literal["success", "error"]
    agent_id: str
    agent_name: str
    enabled: bool
    message: str | None = None


class AgentInfo(BaseModel):
    """Agent information response."""

    name: str
    description: str
    model: str
    icon: str
    color: str
