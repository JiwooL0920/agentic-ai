"""Agent management endpoints."""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

from ...orchestrator.agent_state import get_agent_state_manager

logger = structlog.get_logger()

router = APIRouter()


class AgentToggleRequest(BaseModel):
    """Agent toggle request."""
    
    session_id: Optional[str] = None
    enabled: bool


class AgentStatus(BaseModel):
    """Agent status response."""

    name: str
    agent_id: str
    enabled: bool
    status: str  # "healthy", "degraded", "unavailable"
    model: str
    description: str
    icon: str
    color: str


class AgentHealthResponse(BaseModel):
    """Agent health check response."""

    agents: List[AgentStatus]
    total_count: int
    healthy_count: int
    degraded_count: int
    unavailable_count: int


@router.get("/blueprints/{blueprint}/agents/status")
async def get_agents_status(
    request: Request, 
    blueprint: str,
    session_id: Optional[str] = None
) -> AgentHealthResponse:
    """
    Get status of all agents for a blueprint.
    
    Health status:
    - healthy (green): Agent loaded successfully and ready
    - degraded (yellow): Agent loaded but with warnings
    - unavailable (red): Agent failed to load or not available
    
    Note: Status reflects actual health checks, not enabled/disabled state.
    Use the 'enabled' field to check if an agent is active for routing.
    """
    registry = request.app.state.registry
    configs = registry.get_blueprint_configs(blueprint)
    state_manager = get_agent_state_manager()
    
    # Use "default" session if no session_id provided (must match toggle endpoint)
    effective_session_id = session_id or "default"
    
    if not configs:
        return AgentHealthResponse(
            agents=[],
            total_count=0,
            healthy_count=0,
            degraded_count=0,
            unavailable_count=0,
        )
    
    agents_status = []
    healthy = 0
    degraded = 0
    unavailable = 0
    
    for name, config in configs.items():
        try:
            # Try to get the agent to check if it's loaded
            agent = registry.get_agent(blueprint, name)
            
            # Check if agent is enabled for this session (always check, even if no session_id)
            is_enabled = state_manager.is_agent_enabled(effective_session_id, blueprint, name)
            
            if agent:
                # Status reflects actual health, not enabled/disabled state
                status = "healthy"
                healthy += 1
            else:
                status = "unavailable"
                unavailable += 1
                is_enabled = False
            
            agents_status.append(
                AgentStatus(
                    name=config.name,
                    agent_id=config.agent_id,
                    enabled=is_enabled,
                    status=status,
                    model=config.model_id,
                    description=config.description,
                    icon=config.icon,
                    color=config.color,
                )
            )
        except Exception as e:
            logger.error("agent_status_check_failed", agent=name, error=str(e))
            unavailable += 1
            agents_status.append(
                AgentStatus(
                    name=config.name,
                    agent_id=config.agent_id,
                    enabled=False,
                    status="unavailable",
                    model=config.model_id,
                    description=config.description,
                    icon=config.icon,
                    color=config.color,
                )
            )
    
    return AgentHealthResponse(
        agents=agents_status,
        total_count=len(agents_status),
        healthy_count=healthy,
        degraded_count=degraded,
        unavailable_count=unavailable,
    )


@router.post("/blueprints/{blueprint}/agents/{agent_id}/toggle")
async def toggle_agent(
    request: Request, 
    blueprint: str, 
    agent_id: str,
    toggle_request: AgentToggleRequest
) -> Dict[str, Any]:
    """
    Toggle agent enabled/disabled state for a session.
    """
    state_manager = get_agent_state_manager()
    session_id = toggle_request.session_id or "default"
    
    # Find agent name by ID
    registry = request.app.state.registry
    configs = registry.get_blueprint_configs(blueprint)
    
    agent_name = None
    for name, config in configs.items():
        if config.agent_id == agent_id:
            agent_name = name
            break
    
    if not agent_name:
        return {"status": "error", "message": "Agent not found"}
    
    # Toggle the agent
    if toggle_request.enabled:
        state_manager.enable_agent(session_id, blueprint, agent_name)
    else:
        state_manager.disable_agent(session_id, blueprint, agent_name)
    
    logger.info("agent_toggled", 
               blueprint=blueprint, 
               agent=agent_name, 
               enabled=toggle_request.enabled,
               session_id=session_id)
    
    return {
        "status": "success",
        "agent_id": agent_id,
        "agent_name": agent_name,
        "enabled": toggle_request.enabled,
    }
