"""Pydantic schemas for API request/response models."""

from .agents import (
    AgentHealthResponse,
    AgentInfo,
    AgentStatus,
    AgentToggleRequest,
    AgentToggleResponse,
)
from .blueprints import BlueprintInfo
from .chat import CancelResponse, ChatRequest, ChatResponse
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
    KnowledgeConfig,
    SessionDetailResponse,
    SessionListResponse,
    UpdateKnowledgeConfigRequest,
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
    "CancelResponse",
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
    "KnowledgeConfig",
    "SessionDetailResponse",
    "SessionListResponse",
    "UpdateKnowledgeConfigRequest",
    "UpdateSessionStateRequest",
    "UpdateSessionTitleRequest",
    # Stats
    "ResourceUsage",
    "SystemStats",
]
