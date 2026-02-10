"""Pydantic schemas for API request/response models."""

from .agents import (
    AgentHealthResponse,
    AgentInfo,
    AgentStatus,
    AgentToggleRequest,
    AgentToggleResponse,
)
from .blueprints import BlueprintInfo
from .chat import ChatRequest, ChatResponse
from .common import (
    QueryResult,
    StreamChunkContent,
    StreamChunkDone,
    StreamChunkError,
    StreamChunkMetadata,
    ToolDefinition,
    ToolParameter,
)
from .sessions import (
    SessionDetailResponse,
    SessionListResponse,
    UpdateSessionStateRequest,
    UpdateSessionTitleRequest,
)
from .stats import ResourceUsage, SystemStats

__all__ = [
    # Agents
    "AgentHealthResponse",
    "AgentInfo",
    "AgentStatus",
    "AgentToggleRequest",
    "AgentToggleResponse",
    # Blueprints
    "BlueprintInfo",
    # Chat
    "ChatRequest",
    "ChatResponse",
    # Common
    "QueryResult",
    "StreamChunkContent",
    "StreamChunkDone",
    "StreamChunkError",
    "StreamChunkMetadata",
    "ToolDefinition",
    "ToolParameter",
    # Sessions
    "SessionDetailResponse",
    "SessionListResponse",
    "UpdateSessionStateRequest",
    "UpdateSessionTitleRequest",
    # Stats
    "ResourceUsage",
    "SystemStats",
]
