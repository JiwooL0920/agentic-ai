"""Registry dependency for accessing agent registry from routes."""

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, HTTPException, Request

if TYPE_CHECKING:
    from ...agents.registry import AgentRegistry as AgentRegistryType


def get_registry(request: Request) -> "AgentRegistryType":
    return request.app.state.registry  # type: ignore[no-any-return]


AgentRegistry = Annotated["AgentRegistryType", Depends(get_registry)]


def get_blueprint_agents(request: Request, blueprint: str) -> dict[str, Any]:
    registry = get_registry(request)
    agents = registry.get_blueprint_agents(blueprint)
    if not agents:
        raise HTTPException(status_code=404, detail=f"Blueprint '{blueprint}' not found")
    return agents
