"""
Factory to create agents from YAML definitions.
Mirrors company's pattern of loading agent configurations.
"""

from pathlib import Path
from typing import Dict

import structlog
import yaml

from .base import AgentConfig, OllamaAgent, OllamaAgentOptions

logger = structlog.get_logger()


def load_agent_config(yaml_path: Path) -> AgentConfig:
    """Load agent configuration from YAML file."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    return AgentConfig(
        name=data["name"],
        agent_id=data.get("id", data["name"].lower().replace(" ", "-")),
        description=data["description"],
        model_id=data.get("model", "qwen2.5:32b"),
        system_prompt=data.get("system_prompt", ""),
        temperature=data.get("temperature", 0.7),
        max_tokens=data.get("max_tokens", 4096),
        tools=data.get("tools", []),
        knowledge_scope=data.get("knowledge_scope", []),
        icon=data.get("icon", "🤖"),
        color=data.get("color", "gray-500"),
        streaming=data.get("streaming", True),
    )


def load_agent_from_yaml(yaml_path: Path) -> OllamaAgent:
    """
    Load agent from YAML file.

    Args:
        yaml_path: Path to the agent YAML file

    Returns:
        Configured OllamaAgent instance
    """
    config = load_agent_config(yaml_path)

    logger.info(
        "loading_agent",
        name=config.name,
        model=config.model_id,
        path=str(yaml_path),
    )

    return OllamaAgent(
        OllamaAgentOptions(
            name=config.name,
            description=config.description,
            model_id=config.model_id,
            system_prompt=config.system_prompt,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            streaming=config.streaming,
            tools=config.tools,
            knowledge_scope=config.knowledge_scope,
        )
    )


def load_blueprint_agents(blueprint_path: Path) -> Dict[str, OllamaAgent]:
    """
    Load all agents for a blueprint.

    Args:
        blueprint_path: Path to the blueprint directory

    Returns:
        Dictionary mapping agent names to OllamaAgent instances
    """
    agents: Dict[str, OllamaAgent] = {}
    agents_dir = blueprint_path / "agents"

    if not agents_dir.exists():
        logger.warning("no_agents_directory", blueprint_path=str(blueprint_path))
        return agents

    for yaml_file in agents_dir.glob("*.yaml"):
        try:
            agent = load_agent_from_yaml(yaml_file)
            agents[agent.name] = agent
            logger.info("loaded_agent", name=agent.name)
        except Exception as e:
            logger.error("failed_to_load_agent", file=str(yaml_file), error=str(e))

    logger.info("loaded_blueprint_agents", count=len(agents), blueprint=blueprint_path.name)

    return agents


def load_agent_configs(blueprint_path: Path) -> Dict[str, AgentConfig]:
    """
    Load all agent configurations for a blueprint (metadata only).

    Args:
        blueprint_path: Path to the blueprint directory

    Returns:
        Dictionary mapping agent names to AgentConfig
    """
    configs: Dict[str, AgentConfig] = {}
    agents_dir = blueprint_path / "agents"

    if not agents_dir.exists():
        return configs

    for yaml_file in agents_dir.glob("*.yaml"):
        try:
            config = load_agent_config(yaml_file)
            configs[config.name] = config
        except Exception as e:
            logger.error("failed_to_load_config", file=str(yaml_file), error=str(e))

    return configs
