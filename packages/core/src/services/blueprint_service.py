"""
Blueprint service - manages blueprint and agent information.

Extracted from api/routes/blueprints.py to enable:
- Unit testing without HTTP
- Reuse in CLI/background workers
- Clean separation of concerns
"""

from typing import Any

import structlog

from ..agents.registry import AgentRegistry

logger = structlog.get_logger()


class BlueprintService:
    """
    Handles blueprint management business logic.

    Responsibilities:
    - Blueprint listing and info retrieval
    - Agent listing for blueprints
    - Blueprint hot reload
    """

    def __init__(self, registry: AgentRegistry):
        self._registry = registry
        self._logger = logger.bind(service="BlueprintService")

    def list_blueprints(self) -> list[str]:
        """
        List all available blueprints.

        Returns:
            List of blueprint names
        """
        return self._registry.list_blueprints()

    def get_blueprint_info(self, blueprint: str) -> dict[str, Any] | None:
        """
        Get blueprint details including agents.

        Args:
            blueprint: Blueprint identifier

        Returns:
            Dict with blueprint info, or None if not found
        """
        configs = self._registry.get_blueprint_configs(blueprint)

        if not configs:
            return None

        agents = [
            {
                "name": config.name,
                "description": config.description,
                "model": config.model_id,
                "icon": config.icon,
                "color": config.color,
            }
            for config in configs.values()
        ]

        return {
            "name": blueprint.title(),
            "slug": blueprint,
            "description": f"Multi-agent assistant for {blueprint}",
            "agent_count": len(agents),
            "agents": agents,
        }

    def list_agents(self, blueprint: str) -> list[dict[str, Any]] | None:
        """
        List agents for a blueprint.

        Args:
            blueprint: Blueprint identifier

        Returns:
            List of agent info dicts, or None if blueprint not found
        """
        configs = self._registry.get_blueprint_configs(blueprint)

        if not configs:
            return None

        return [
            {
                "name": config.name,
                "description": config.description,
                "model": config.model_id,
                "icon": config.icon,
                "color": config.color,
            }
            for config in configs.values()
        ]

    def reload_blueprint(self, blueprint: str) -> dict[str, str]:
        """
        Reload a blueprint's agents (hot reload).

        Args:
            blueprint: Blueprint identifier

        Returns:
            Dict with status and blueprint name
        """
        self._registry.reload_blueprint(blueprint)
        self._logger.info("blueprint_reloaded", blueprint=blueprint)

        return {"status": "reloaded", "blueprint": blueprint}
