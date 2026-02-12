"""Ollama-based supervisor classifier for agent routing."""


import httpx
import structlog
from agent_squad.classifiers import Classifier, ClassifierResult
from agent_squad.types import ConversationMessage
from ollama import AsyncClient

from ..agents.base import OllamaAgent
from ..config import get_settings
from .routing import build_routing_prompt

logger = structlog.get_logger()


class OllamaSupervisorClassifier(Classifier):  # type: ignore[misc]
    """
    LLM-based supervisor classifier using Ollama.
    Mirrors AWS Bedrock's supervisor routing pattern but runs locally.

    The supervisor ONLY routes queries to collaborator agents - it never responds directly.
    All agents are equals; there is no "default" agent.
    """

    def __init__(self, agents: dict[str, OllamaAgent], model_id: str = "qwen2.5:7b"):
        super().__init__()
        self.agents = agents
        self.agent_list = list(agents.keys())
        self.model_id = model_id
        settings = get_settings()
        self._client = AsyncClient(host=settings.ollama_host)
        self.set_agents(agents)

    def _build_agent_descriptions(self) -> str:
        descriptions = []
        for _agent_key, agent in self.agents.items():
            descriptions.append(f"- {agent.name}: {agent.description}")
        return "\n".join(descriptions)

    async def process_request(
        self,
        input_text: str,
        chat_history: list[ConversationMessage],
    ) -> ClassifierResult:
        """Process request and select an agent using LLM-based routing."""
        agent_desc_text = self._build_agent_descriptions()

        logger.info("supervisor_routing",
                   input=input_text[:100],
                   available_agents=list(self.agents.keys()))

        try:
            prompt = build_routing_prompt(input_text, agent_desc_text)

            response = await self._client.chat(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                options={
                    "temperature": 0.1,
                    "num_predict": 50,
                },
            )

            selected_agent_name = response.get("message", {}).get("content", "").strip()

            for _agent_key, agent in self.agents.items():
                if agent.name.lower() in selected_agent_name.lower():
                    logger.info("supervisor_selected",
                               agent=agent.name,
                               confidence=0.9,
                               llm_response=selected_agent_name)
                    return ClassifierResult(
                        selected_agent=agent,
                        confidence=0.9
                    )

            logger.warning("supervisor_no_match_found",
                         llm_response=selected_agent_name,
                         falling_back="systemarchitect")

            systemarchitect = self.agents.get("systemarchitect")
            if systemarchitect:
                return ClassifierResult(
                    selected_agent=systemarchitect,
                    confidence=0.6
                )

            fallback_agent = self.agents[self.agent_list[0]]
            logger.warning("supervisor_using_first_agent", agent=fallback_agent.name)
            return ClassifierResult(
                selected_agent=fallback_agent,
                confidence=0.4
            )

        except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException, KeyError, ValueError) as e:
            logger.error("supervisor_routing_error", error=str(e), exc_info=True)
            systemarchitect = self.agents.get("systemarchitect")
            if systemarchitect:
                return ClassifierResult(
                    selected_agent=systemarchitect,
                    confidence=0.3
                )
            return ClassifierResult(
                selected_agent=self.agents[self.agent_list[0]],
                confidence=0.2
            )
