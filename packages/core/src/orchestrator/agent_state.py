"""Agent state management - tracks which agents are enabled/disabled per session."""

from typing import Any

import structlog

logger = structlog.get_logger()


class AgentStateManager:
    """
    Manages enabled/disabled state for agents per session.

    In production, this would use Redis or DynamoDB for persistence.
    For now, we use in-memory storage.
    """

    def __init__(self) -> None:
        # session_id -> blueprint -> set of disabled agent names (lowercase)
        self._disabled_agents: dict[str, dict[str, set[str]]] = {}

    def disable_agent(self, session_id: str, blueprint: str, agent_name: str) -> None:
        """Disable an agent for a specific session."""
        agent_key = agent_name.lower()

        if session_id not in self._disabled_agents:
            self._disabled_agents[session_id] = {}

        if blueprint not in self._disabled_agents[session_id]:
            self._disabled_agents[session_id][blueprint] = set()

        self._disabled_agents[session_id][blueprint].add(agent_key)

        logger.info("agent_disabled",
                   session_id=session_id,
                   blueprint=blueprint,
                   agent=agent_name)

    def enable_agent(self, session_id: str, blueprint: str, agent_name: str) -> None:
        """Enable an agent for a specific session."""
        agent_key = agent_name.lower()

        if (session_id in self._disabled_agents and
            blueprint in self._disabled_agents[session_id]):
            self._disabled_agents[session_id][blueprint].discard(agent_key)

        logger.info("agent_enabled",
                   session_id=session_id,
                   blueprint=blueprint,
                   agent=agent_name)

    def is_agent_enabled(self, session_id: str, blueprint: str, agent_name: str) -> bool:
        """Check if an agent is enabled for a session."""
        agent_key = agent_name.lower()

        if (session_id not in self._disabled_agents or
            blueprint not in self._disabled_agents[session_id]):
            return True

        return agent_key not in self._disabled_agents[session_id][blueprint]

    def get_enabled_agents(
        self,
        session_id: str,
        blueprint: str,
        all_agents: dict[str, Any]
    ) -> dict[str, Any]:
        """Get only enabled agents for a session."""
        if (session_id not in self._disabled_agents or
            blueprint not in self._disabled_agents[session_id]):
            return all_agents

        disabled = self._disabled_agents[session_id][blueprint]

        return {
            name: agent
            for name, agent in all_agents.items()
            if name.lower() not in disabled
        }

    def clear_session(self, session_id: str) -> None:
        """Clear all state for a session."""
        if session_id in self._disabled_agents:
            del self._disabled_agents[session_id]


# Global instance
_agent_state_manager = AgentStateManager()


def get_agent_state_manager() -> AgentStateManager:
    """Get the global agent state manager instance."""
    return _agent_state_manager
