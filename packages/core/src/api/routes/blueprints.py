"""Blueprint management endpoints."""


from fastapi import APIRouter, HTTPException, Request

from ...schemas import AgentInfo, BlueprintInfo
from ...services.blueprint_service import BlueprintService
from ..dependencies import get_registry

router = APIRouter()


@router.get("/blueprints")
async def list_blueprints(request: Request) -> list[str]:
    service = BlueprintService(get_registry(request))
    return service.list_blueprints()


@router.get("/blueprints/{blueprint}")
async def get_blueprint(request: Request, blueprint: str) -> BlueprintInfo:
    service = BlueprintService(get_registry(request))
    result = service.get_blueprint_info(blueprint)

    if not result:
        raise HTTPException(status_code=404, detail=f"Blueprint '{blueprint}' not found")

    return BlueprintInfo(**result)


@router.get("/blueprints/{blueprint}/agents")
async def list_agents(request: Request, blueprint: str) -> list[AgentInfo]:
    service = BlueprintService(get_registry(request))
    result = service.list_agents(blueprint)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Blueprint '{blueprint}' not found")

    return [AgentInfo(**agent) for agent in result]


@router.post("/blueprints/{blueprint}/reload")
async def reload_blueprint(request: Request, blueprint: str) -> dict[str, str]:
    service = BlueprintService(get_registry(request))
    return service.reload_blueprint(blueprint)
