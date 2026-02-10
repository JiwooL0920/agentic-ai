"""Registry dependency for accessing agent registry from routes."""

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request

if TYPE_CHECKING:
    from ...agents.registry import AgentRegistry as AgentRegistryType


def get_registry(request: Request) -> "AgentRegistryType":
    return request.app.state.registry


AgentRegistry = Annotated["AgentRegistryType", Depends(get_registry)]


def get_blueprint_agents(request: Request, blueprint: str) -> dict:
    registry = get_registry(request)
    agents = registry.get_blueprint_agents(blueprint)
    if not agents:
        raise HTTPException(status_code=404, detail=f"Blueprint '{blueprint}' not found")
    return agents
