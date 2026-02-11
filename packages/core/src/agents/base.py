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

from collections.abc import AsyncIterable
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog
from agent_squad.agents import Agent, AgentOptions
from agent_squad.types import ConversationMessage, ParticipantRole
from ollama import AsyncClient

from ..config import get_settings
from ..observability import LLMTracker

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
    tools: list[dict[str, Any]] = field(default_factory=list)
    knowledge_scope: list[str] = field(default_factory=list)
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
    system_prompt: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    knowledge_scope: list[str] = field(default_factory=list)


class OllamaAgent(Agent):

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
        settings = get_settings()
        self._client = AsyncClient(host=settings.ollama_host)

    def _build_messages(
        self,
        input_text: str,
        chat_history: list[ConversationMessage],
    ) -> list[dict[str, str]]:
        messages = []

        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        for msg in chat_history:
            content = msg.content[0].get("text", "") if msg.content else ""
            messages.append({"role": msg.role, "content": content})

        messages.append({"role": "user", "content": input_text})

        return messages

    async def _handle_streaming_response(
        self, messages: list[dict[str, str]], tracker: LLMTracker
    ) -> AsyncIterable[str]:
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

            total_output_tokens = 0
            async for chunk in response:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    if total_output_tokens == 0:
                        tracker.record_first_token()
                    total_output_tokens += 1
                    yield content

                if chunk.get("done", False):
                    input_tokens = chunk.get("prompt_eval_count", 0)
                    output_tokens = chunk.get("eval_count", total_output_tokens)
                    tracker.record_tokens(input_tokens, output_tokens)

        except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException) as e:
            self._logger.error("streaming_error", error=str(e))
            raise

    async def _handle_sync_response(
        self, messages: list[dict[str, str]], tracker: LLMTracker
    ) -> ConversationMessage:
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
            input_tokens = response.get("prompt_eval_count", 0)
            output_tokens = response.get("eval_count", 0)
            tracker.record_tokens(input_tokens, output_tokens)

            return ConversationMessage(
                role=ParticipantRole.ASSISTANT,
                content=[{"text": content}],
            )

        except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException) as e:
            self._logger.error("response_error", error=str(e))
            raise

    async def process_request(
        self,
        input_text: str,
        user_id: str,
        session_id: str,
        chat_history: list[ConversationMessage],
        additional_params: dict[str, str] | None = None,
    ) -> ConversationMessage | AsyncIterable[Any]:
        request_id = (additional_params or {}).get("request_id", "")
        self._logger.info(
            "processing_request",
            user_id=user_id,
            session_id=session_id,
            input_length=len(input_text),
            streaming=self.streaming,
            request_id=request_id,
        )

        messages = self._build_messages(input_text, chat_history)

        if self.streaming:
            return self._tracked_streaming_response(messages, request_id)
        else:
            return await self._tracked_sync_response(messages, request_id)

    async def _tracked_streaming_response(
        self, messages: list[dict[str, str]], request_id: str
    ) -> AsyncIterable[str]:
        tracker = LLMTracker(
            model=self.model_id,
            agent=self.name,
            streaming=True,
            request_id=request_id,
        )
        async with tracker:
            async for chunk in self._handle_streaming_response(messages, tracker):
                yield chunk

    async def _tracked_sync_response(
        self, messages: list[dict[str, str]], request_id: str
    ) -> ConversationMessage:
        tracker = LLMTracker(
            model=self.model_id,
            agent=self.name,
            streaming=False,
            request_id=request_id,
        )
        async with tracker:
            return await self._handle_sync_response(messages, tracker)
