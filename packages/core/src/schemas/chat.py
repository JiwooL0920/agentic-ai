"""Chat request/response schemas."""


from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Chat request payload."""

    message: str
    session_id: str | None = None
    stream: bool = True


class ChatResponse(BaseModel):
    """Chat response payload."""

    response: str
    agent: str
    session_id: str
