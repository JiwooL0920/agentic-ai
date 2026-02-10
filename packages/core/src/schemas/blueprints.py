"""Blueprint management schemas."""


from pydantic import BaseModel

from .agents import AgentInfo


class BlueprintInfo(BaseModel):
    """Blueprint information response."""

    name: str
    slug: str
    description: str
    agent_count: int
    agents: list[AgentInfo]
