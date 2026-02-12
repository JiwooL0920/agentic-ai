"""
Tests for agent management and factory.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestAgentFactory:
    """Tests for agent factory functions."""

    def test_load_agent_config_from_yaml(self, blueprints_path: Path) -> None:
        """Test loading agent configuration from YAML file."""
        from src.agents.factory import load_agent_config

        yaml_path = blueprints_path / "test-blueprint" / "agents" / "test-agent.yaml"
        config = load_agent_config(yaml_path)

        assert config.name == "TestAgent"
        # agent_id is derived from name if 'id' key not present in YAML
        assert config.agent_id == "testagent"
        assert config.model_id == "qwen2.5:32b"
        assert config.temperature == 0.7

    def test_load_agent_config_file_not_found(self, tmp_path: Path) -> None:
        """Test that loading non-existent file raises error."""
        from src.agents.factory import load_agent_config

        with pytest.raises(FileNotFoundError):
            load_agent_config(tmp_path / "nonexistent.yaml")

    def test_load_blueprint_agents(
        self, blueprints_path: Path, mock_ollama_client: MagicMock
    ) -> None:
        """Test loading all agents from a blueprint directory."""
        from src.agents.factory import load_blueprint_agents

        agents = load_blueprint_agents(blueprints_path / "test-blueprint")

        assert len(agents) >= 1
        assert "TestAgent" in agents


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_agent_config_defaults(self, sample_agent_config: dict) -> None:
        """Test AgentConfig has sensible defaults."""
        from src.agents.base import AgentConfig

        config = AgentConfig(**sample_agent_config)

        assert config.name == "TestAgent"
        assert config.temperature == 0.7
        assert config.icon == "🤖"

    def test_agent_config_validation(self) -> None:
        """Test AgentConfig requires all fields (dataclass with required args)."""
        from src.agents.base import AgentConfig

        with pytest.raises(TypeError):
            AgentConfig(name="Test")  # Missing required fields: agent_id, description


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    def test_registry_loads_blueprints(self, blueprints_path: Path) -> None:
        """Test registry loads blueprints on initialization."""
        from src.agents.registry import AgentRegistry

        registry = AgentRegistry(blueprints_path)
        blueprints = registry.list_blueprints()

        assert "test-blueprint" in blueprints

    def test_registry_get_blueprint_configs(self, blueprints_path: Path) -> None:
        """Test getting agent configs for a blueprint."""
        from src.agents.registry import AgentRegistry

        registry = AgentRegistry(blueprints_path)
        configs = registry.get_blueprint_configs("test-blueprint")

        assert configs is not None
        assert len(configs) >= 1
        assert "TestAgent" in configs

    def test_registry_get_nonexistent_blueprint(self, blueprints_path: Path) -> None:
        """Test getting configs for non-existent blueprint returns empty."""
        from src.agents.registry import AgentRegistry

        registry = AgentRegistry(blueprints_path)
        configs = registry.get_blueprint_configs("nonexistent")

        assert configs == {} or configs is None
