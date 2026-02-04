"""Blueprint management endpoints."""

from typing import Dict, List

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter()


class AgentInfo(BaseModel):
    """Agent information response."""

    name: str
    description: str
    model: str
    icon: str
    color: str


class BlueprintInfo(BaseModel):
    """Blueprint information response."""

    name: str
    slug: str
    description: str
    agent_count: int
    agents: List[AgentInfo]


@router.get("/blueprints")
async def list_blueprints(request: Request) -> List[str]:
    """List available blueprints."""
    registry = request.app.state.registry
    return registry.list_blueprints()


@router.get("/blueprints/{blueprint}")
async def get_blueprint(request: Request, blueprint: str) -> BlueprintInfo:
    """Get blueprint details including agents."""
    registry = request.app.state.registry
    configs = registry.get_blueprint_configs(blueprint)

    if not configs:
        raise HTTPException(status_code=404, detail=f"Blueprint '{blueprint}' not found")

    agents = [
        AgentInfo(
            name=config.name,
            description=config.description,
            model=config.model_id,
            icon=config.icon,
            color=config.color,
        )
        for config in configs.values()
    ]

    return BlueprintInfo(
        name=blueprint.title(),
        slug=blueprint,
        description=f"Multi-agent assistant for {blueprint}",
        agent_count=len(agents),
        agents=agents,
    )


@router.get("/blueprints/{blueprint}/agents")
async def list_agents(request: Request, blueprint: str) -> List[AgentInfo]:
    """List agents for a blueprint."""
    registry = request.app.state.registry
    configs = registry.get_blueprint_configs(blueprint)

    if not configs:
        raise HTTPException(status_code=404, detail=f"Blueprint '{blueprint}' not found")

    return [
        AgentInfo(
            name=config.name,
            description=config.description,
            model=config.model_id,
            icon=config.icon,
            color=config.color,
        )
        for config in configs.values()
    ]


@router.post("/blueprints/{blueprint}/reload")
async def reload_blueprint(request: Request, blueprint: str) -> Dict[str, str]:
    """Reload a blueprint's agents (hot reload)."""
    registry = request.app.state.registry
    registry.reload_blueprint(blueprint)

    logger.info("blueprint_reloaded", blueprint=blueprint)

    return {"status": "reloaded", "blueprint": blueprint}
