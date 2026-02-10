"""Common shared Pydantic models for API responses."""

from typing import Literal

from pydantic import BaseModel


class StreamChunkMetadata(BaseModel):
    """Metadata chunk sent at stream start."""

    type: Literal["metadata"]
    agent: str
    session_id: str


class StreamChunkContent(BaseModel):
    """Content chunk during streaming."""

    type: Literal["content"]
    content: str


class StreamChunkDone(BaseModel):
    """Final chunk indicating stream completion."""

    type: Literal["done"]


class StreamChunkError(BaseModel):
    """Error chunk when streaming fails."""

    type: Literal["error"]
    error: str


class QueryResult(BaseModel):
    """Result from non-streaming query."""

    response: str
    agent: str
    session_id: str


class ToolParameter(BaseModel):
    """Parameter definition for a tool."""

    name: str
    type: str
    description: str
    required: bool = True


class ToolDefinition(BaseModel):
    """Definition of an agent tool."""

    name: str
    description: str
    parameters: list[ToolParameter] = []
