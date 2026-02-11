"""
Supervisor pattern - equivalent to company's SUPERVISOR_ROUTER mode.

Company Pattern:
- aws_bedrockagent_agent.agent_collaboration = "SUPERVISOR"
- aws_bedrockagent_agent_collaborator resources

Local Adaptation:
- agent-squad (awslabs) with OllamaAgents
- Routing based on agent YAML definitions
"""

from collections.abc import AsyncIterable
from typing import Any

import httpx
import structlog
from agent_squad.orchestrator import AgentSquad

from ..agents.base import OllamaAgent
from .agent_state import get_agent_state_manager
from .classifier import OllamaSupervisorClassifier
from .routing import (
    build_collaborator_context,
    build_supervisor_direct_response_prompt,
    get_explicit_agent_request,
    should_supervisor_answer_directly,
)

logger = structlog.get_logger()


class SupervisorOrchestrator:
    """
    True Bedrock supervisor pattern implementation.

    Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │              Supervisor Agent (qwen2.5:7b)                   │
    │  - Analyzes queries and determines routing strategy          │
    │  - Can ask clarifying questions                              │
    │  - Can coordinate multiple agents                            │
    │  - Synthesizes multi-agent responses                         │
    └─────────────────────────────────────────────────────────────┘
                              ↓
    ┌──────────────┬──────────────┬──────────────┬──────────────┐
    │SystemArchitect│KubernetesExpert│PythonExpert│FrontendExpert│
    │  (collaborator)│  (collaborator)│  (collaborator)│  (collaborator)│
    └──────────────┴──────────────┴──────────────┴──────────────┘

    The supervisor is always the entry point and decides:
    1. Route to single specialist
    2. Ask clarifying question
    3. Coordinate multiple specialists
    """

    def __init__(self, agents: dict[str, OllamaAgent]):
        """
        Initialize supervisor orchestrator with collaborator agents.

        Args:
            agents: Dictionary mapping agent names to OllamaAgent instances
        """
        self.agents = agents

        # Extract supervisor agent
        agents_lower = {name.lower(): agent for name, agent in agents.items()}
        self.supervisor_agent = agents_lower.get("supervisor")

        if not self.supervisor_agent:
            logger.warning("supervisor_agent_not_found",
                         available=list(agents_lower.keys()))
            # Fallback: create a simple routing classifier
            classifier = OllamaSupervisorClassifier(agents_lower, model_id="qwen2.5:7b")
            self.orchestrator = AgentSquad(classifier=classifier)
            for agent in agents.values():
                self.orchestrator.add_agent(agent)
        else:
            # Remove supervisor from collaborators list
            self.collaborators = {k: v for k, v in agents_lower.items() if k != "supervisor"}
            logger.info("supervisor_initialized",
                       agent_count=len(self.collaborators),
                       has_supervisor=True)

    async def process_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        chat_history: list[Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process query through supervisor agent (non-streaming).
        """
        logger.info(
            "processing_query",
            user_id=user_id,
            session_id=session_id,
            query_length=len(query),
        )

        try:
            if not self.supervisor_agent:
                # Fallback behavior
                return {
                    "response": "Supervisor agent not available",
                    "agent": "system",
                    "session_id": session_id,
                }

            collaborator_context = "Available specialists:\n"
            for _name, agent in self.collaborators.items():
                collaborator_context += f"- {agent.name}: {agent.description}\n"

            enhanced_query = f"""{collaborator_context}

User Query: {query}

Analyze this query and decide your response strategy."""

            response = await self.supervisor_agent.process_request(
                input_text=enhanced_query,
                user_id=user_id,
                session_id=session_id,
                chat_history=[],
                additional_params={},
            )

            content = ""
            if hasattr(response, "__aiter__"):
                async for chunk in response:
                    content += str(chunk)
            elif hasattr(response, "content") and response.content:
                content = response.content[0].get("text", "")

            return {
                "response": content,
                "agent": self.supervisor_agent.name,
                "session_id": session_id,
            }

        except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException, KeyError, ValueError, AttributeError) as e:
            logger.error("query_processing_error", error=str(e))
            raise

    async def _get_agent_response(
        self,
        agent: OllamaAgent,
        query: str,
        user_id: str,
        session_id: str,
    ) -> AsyncIterable[dict[str, Any]]:
        response = await agent.process_request(
            input_text=query,
            user_id=user_id,
            session_id=session_id,
            chat_history=[],
            additional_params={},
        )

        if hasattr(response, "__aiter__"):
            async for chunk in response:
                yield {"type": "content", "content": chunk}
        else:
            content = ""
            if hasattr(response, "content") and response.content:
                content = response.content[0].get("text", "")
            yield {"type": "content", "content": content}

        yield {"type": "done"}

    async def process_query_streaming(
        self,
        query: str,
        user_id: str,
        session_id: str,
        chat_history: list[Any] | None = None,
        blueprint: str | None = None,
    ) -> AsyncIterable[dict[str, Any]]:
        """
        Process query through supervisor agent.

        The supervisor first determines if it should:
        1. Answer directly (greetings, general questions, clarifications)
        2. Route to a specialist (technical questions requiring expertise)

        Only routes to ENABLED agents for this session.
        """
        logger.info(
            "processing_query_streaming",
            user_id=user_id,
            session_id=session_id,
        )

        try:
            # Get only enabled agents for this session
            state_manager = get_agent_state_manager()
            agents_lower = {name.lower(): agent for name, agent in self.agents.items()}

            if blueprint:
                agents_lower = state_manager.get_enabled_agents(
                    session_id, blueprint, agents_lower
                )

            if not agents_lower:
                yield {"type": "error", "error": "No agents available. Please enable at least one agent."}
                return

            logger.info("enabled_agents", count=len(agents_lower), agents=list(agents_lower.keys()))

            # Filter collaborators to only enabled agents (exclude supervisor)
            enabled_collaborators = {
                k: v for k, v in agents_lower.items()
                if k != "supervisor"
            }

            if not self.supervisor_agent:
                classifier = OllamaSupervisorClassifier(enabled_collaborators, model_id="qwen2.5:7b")
                classifier_result = await classifier.process_request(
                    input_text=query,
                    chat_history=chat_history or [],
                )

                if not classifier_result.selected_agent:
                    yield {"type": "error", "error": "No agent selected"}
                    return

                selected_agent = classifier_result.selected_agent
                agent_name = selected_agent.name

                logger.info("agent_selected_fallback", agent=agent_name, confidence=classifier_result.confidence)

                yield {
                    "type": "metadata",
                    "agent": agent_name,
                    "session_id": session_id,
                }

                async for chunk_data in self._get_agent_response(
                    selected_agent, query, user_id, session_id
                ):
                    yield chunk_data
                return

            if should_supervisor_answer_directly(query):
                logger.info("supervisor_answering_directly", query=query[:50])

                yield {
                    "type": "metadata",
                    "agent": self.supervisor_agent.name,
                    "session_id": session_id,
                }

                collaborator_context = build_collaborator_context(enabled_collaborators)
                enhanced_query = build_supervisor_direct_response_prompt(
                    query, collaborator_context
                )

                async for chunk_data in self._get_agent_response(
                    self.supervisor_agent, enhanced_query, user_id, session_id
                ):
                    yield chunk_data
                return

            explicit_agent_key = get_explicit_agent_request(query)
            explicit_agent = agents_lower.get(explicit_agent_key) if explicit_agent_key else None

            if explicit_agent:
                logger.info("explicit_agent_request", agent=explicit_agent.name)

                yield {
                    "type": "metadata",
                    "agent": explicit_agent.name,
                    "session_id": session_id,
                }

                async for chunk_data in self._get_agent_response(
                    explicit_agent, query, user_id, session_id
                ):
                    yield chunk_data
                return

            logger.info("using_classifier_for_routing", enabled_count=len(enabled_collaborators))

            if not enabled_collaborators:
                yield {"type": "error", "error": "No collaborator agents available. Please enable at least one specialist agent."}
                return

            classifier = OllamaSupervisorClassifier(enabled_collaborators, model_id="qwen2.5:7b")
            classifier_result = await classifier.process_request(
                input_text=query,
                chat_history=chat_history or [],
            )

            selected_agent = classifier_result.selected_agent

            if not selected_agent:
                logger.warning("classifier_no_agent")
                selected_agent = enabled_collaborators.get("systemarchitect")

            if not selected_agent:
                yield {"type": "error", "error": "No suitable agent found"}
                return

            agent_name = selected_agent.name
            logger.info("classifier_selected",
                       agent=agent_name,
                       confidence=classifier_result.confidence)

            yield {
                "type": "metadata",
                "agent": agent_name,
                "session_id": session_id,
            }

            async for chunk_data in self._get_agent_response(
                selected_agent, query, user_id, session_id
            ):
                yield chunk_data

        except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException, KeyError, ValueError, AttributeError) as e:
            logger.error("streaming_error", error=str(e), exc_info=True)
            yield {"type": "error", "error": str(e)}

    def list_agents(self) -> list[str]:
        """List available agent names."""
        return list(self.agents.keys())

    def get_agent(self, name: str) -> OllamaAgent | None:
        """Get a specific agent by name."""
        return self.agents.get(name)
