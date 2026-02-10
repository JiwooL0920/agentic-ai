"""System statistics schemas."""

from pydantic import BaseModel, Field


class ResourceUsage(BaseModel):
    """Individual resource usage metric."""
    
    name: str = Field(..., description="Resource name (cpu, memory, gpu, storage)")
    percent: float = Field(..., ge=0, le=100, description="Usage percentage 0-100")
    used: str | None = Field(None, description="Human-readable used amount")
    total: str | None = Field(None, description="Human-readable total amount")


class SystemStats(BaseModel):
    """Complete system statistics response."""
    
    cpu: ResourceUsage
    memory: ResourceUsage
    gpu: ResourceUsage
    storage: ResourceUsage
    timestamp: float = Field(..., description="Unix timestamp of the measurement")
