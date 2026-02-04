"""
Agent Registry - manages loaded agents across blueprints.
"""

from pathlib import Path
from typing import Dict, List, Optional

import structlog

from .base import AgentConfig, OllamaAgent
from .factory import load_agent_configs, load_blueprint_agents

logger = structlog.get_logger()


class AgentRegistry:
    """
    Central registry for all agents across blueprints.
    Supports lazy loading and blueprint isolation.
    """

    def __init__(self, blueprints_path: Path):
        """
        Initialize the registry.

        Args:
            blueprints_path: Path to the blueprints directory
        """
        self.blueprints_path = blueprints_path
        self._agents: Dict[str, Dict[str, OllamaAgent]] = {}
        self._configs: Dict[str, Dict[str, AgentConfig]] = {}

    def list_blueprints(self) -> List[str]:
        """List available blueprints."""
        if not self.blueprints_path.exists():
            return []

        return [
            d.name
            for d in self.blueprints_path.iterdir()
            if d.is_dir() and (d / "config.yaml").exists()
        ]

    def get_blueprint_configs(self, blueprint: str) -> Dict[str, AgentConfig]:
        """
        Get agent configurations for a blueprint (lazy loaded).

        Args:
            blueprint: Blueprint name

        Returns:
            Dictionary of agent configs
        """
        if blueprint not in self._configs:
            blueprint_path = self.blueprints_path / blueprint
            if not blueprint_path.exists():
                logger.warning("blueprint_not_found", blueprint=blueprint)
                return {}
            self._configs[blueprint] = load_agent_configs(blueprint_path)

        return self._configs[blueprint]

    def get_blueprint_agents(self, blueprint: str) -> Dict[str, OllamaAgent]:
        """
        Get agents for a blueprint (lazy loaded).

        Args:
            blueprint: Blueprint name

        Returns:
            Dictionary of OllamaAgent instances
        """
        if blueprint not in self._agents:
            blueprint_path = self.blueprints_path / blueprint
            if not blueprint_path.exists():
                logger.warning("blueprint_not_found", blueprint=blueprint)
                return {}
            self._agents[blueprint] = load_blueprint_agents(blueprint_path)

        return self._agents[blueprint]

    def get_agent(self, blueprint: str, agent_name: str) -> Optional[OllamaAgent]:
        """
        Get a specific agent.

        Args:
            blueprint: Blueprint name
            agent_name: Agent name

        Returns:
            OllamaAgent or None if not found
        """
        agents = self.get_blueprint_agents(blueprint)
        return agents.get(agent_name)

    def reload_blueprint(self, blueprint: str) -> None:
        """
        Reload agents for a blueprint.

        Args:
            blueprint: Blueprint name
        """
        if blueprint in self._agents:
            del self._agents[blueprint]
        if blueprint in self._configs:
            del self._configs[blueprint]

        logger.info("reloaded_blueprint", blueprint=blueprint)

    def list_agents(self, blueprint: str) -> List[str]:
        """
        List agent names for a blueprint.

        Args:
            blueprint: Blueprint name

        Returns:
            List of agent names
        """
        configs = self.get_blueprint_configs(blueprint)
        return list(configs.keys())
