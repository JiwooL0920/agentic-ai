"""
Base OllamaAgent class - replaces AWS Bedrock Agent for local execution.

NOTE: agent-squad (awslabs) has a built-in OllamaAgent in cookbook/examples.
This implementation extends it with our YAML-loading pattern and additional features.
See: https://github.com/awslabs/agent-squad/blob/main/docs/src/content/docs/cookbook/examples/ollama-agent.mdx

Company Pattern Adaptation:
- Bedrock Agent → OllamaAgent with agent-squad
- Action Groups → FastAPI endpoints with tool functions
- Knowledge Base → pgvector RAG
"""

from dataclasses import dataclass, field
from typing import Any, AsyncIterable, Dict, List, Optional

import structlog
from agent_squad.agents import Agent, AgentOptions
from agent_squad.types import ConversationMessage, ParticipantRole
from ollama import AsyncClient

logger = structlog.get_logger()


@dataclass
class AgentConfig:
    """Agent configuration loaded from YAML (like company's prompts/)."""

    name: str
    agent_id: str
    description: str
    model_id: str = "qwen2.5:32b"
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_scope: List[str] = field(default_factory=list)
    icon: str = "🤖"
    color: str = "gray-500"
    streaming: bool = True


@dataclass
class OllamaAgentOptions(AgentOptions):
    """Options for Ollama-based agents."""

    model_id: str = "qwen2.5:32b"
    streaming: bool = True
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: Optional[str] = None
    tools: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_scope: List[str] = field(default_factory=list)


class OllamaAgent(Agent):
    """
    Agent powered by local Ollama models.
    Equivalent to company's Bedrock Agent but runs locally.
    """

    def __init__(self, options: OllamaAgentOptions):
        super().__init__(options)
        self.model_id = options.model_id
        self.streaming = options.streaming
        self.temperature = options.temperature
        self.max_tokens = options.max_tokens
        self.system_prompt = options.system_prompt
        self.tools = options.tools
        self.knowledge_scope = options.knowledge_scope
        self._logger = logger.bind(agent=options.name, model=options.model_id)
        # Initialize async Ollama client
        self._client = AsyncClient()

    def _build_messages(
        self,
        input_text: str,
        chat_history: List[ConversationMessage],
    ) -> List[Dict[str, str]]:
        """Build message list for Ollama API."""
        messages = []

        # Add system prompt
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        # Add chat history
        for msg in chat_history:
            content = msg.content[0].get("text", "") if msg.content else ""
            messages.append({"role": msg.role, "content": content})

        # Add current user message
        messages.append({"role": "user", "content": input_text})

        return messages

    async def _handle_streaming_response(
        self, messages: List[Dict[str, str]]
    ) -> AsyncIterable[str]:
        """Handle streaming response from Ollama (non-blocking async)."""
        try:
            response = await self._client.chat(
                model=self.model_id,
                messages=messages,
                stream=True,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )

            async for chunk in response:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content

        except Exception as e:
            self._logger.error("streaming_error", error=str(e))
            raise

    async def _handle_sync_response(
        self, messages: List[Dict[str, str]]
    ) -> ConversationMessage:
        """Handle synchronous response from Ollama (non-blocking async)."""
        try:
            response = await self._client.chat(
                model=self.model_id,
                messages=messages,
                stream=False,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )

            content = response.get("message", {}).get("content", "")

            return ConversationMessage(
                role=ParticipantRole.ASSISTANT.value,
                content=[{"text": content}],
            )

        except Exception as e:
            self._logger.error("response_error", error=str(e))
            raise

    async def process_request(
        self,
        input_text: str,
        user_id: str,
        session_id: str,
        chat_history: List[ConversationMessage],
        additional_params: Optional[Dict[str, str]] = None,
    ) -> ConversationMessage | AsyncIterable[Any]:
        """
        Process request using Ollama.

        Args:
            input_text: User's input message
            user_id: Unique user identifier
            session_id: Session identifier
            chat_history: Previous conversation messages
            additional_params: Optional additional parameters

        Returns:
            ConversationMessage for sync, AsyncIterable[str] for streaming
        """
        self._logger.info(
            "processing_request",
            user_id=user_id,
            session_id=session_id,
            input_length=len(input_text),
            streaming=self.streaming,
        )

        messages = self._build_messages(input_text, chat_history)

        if self.streaming:
            return self._handle_streaming_response(messages)
        else:
            return await self._handle_sync_response(messages)
