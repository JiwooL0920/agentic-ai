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
from ..rag import get_rag_chain
from ..tools.base import ToolCall
from ..tools.executor import ToolExecutor
from ..tools.registry import get_tool_registry

logger = structlog.get_logger()

MAX_TOOL_ITERATIONS = 5
RAG_ENABLED = True


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
        self.tool_names = self._extract_tool_names(options.tools)
        self.knowledge_scope = options.knowledge_scope
        self._logger = logger.bind(agent=options.name, model=options.model_id)
        settings = get_settings()
        self._client = AsyncClient(host=settings.ollama_host)
        self._tool_executor = ToolExecutor()
        self._last_rag_context: Any | None = None  # Store last RAG context for retrieval

    def _extract_tool_names(self, tools: list[dict[str, Any]]) -> list[str]:
        return [t.get("name", "") for t in tools if t.get("name")]

    def _get_ollama_tools(self) -> list[dict[str, Any]]:
        if not self.tool_names:
            return []
        registry = get_tool_registry()
        return registry.get_ollama_tools(self.tool_names)

    def _build_messages(
        self,
        input_text: str,
        chat_history: list[ConversationMessage],
        augmented_system_prompt: str | None = None,
    ) -> list[dict[str, Any]]:
        """Build messages list for Ollama chat.

        Args:
            input_text: User input text.
            chat_history: Previous conversation messages.
            augmented_system_prompt: Optional RAG-augmented system prompt.

        Returns:
            List of message dicts for Ollama.
        """
        messages: list[dict[str, Any]] = []

        system_prompt = augmented_system_prompt or self.system_prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        for msg in chat_history:
            content = msg.content[0].get("text", "") if msg.content else ""
            messages.append({"role": msg.role, "content": content})

        messages.append({"role": "user", "content": input_text})

        return messages

    async def _handle_streaming_response(
        self, messages: list[dict[str, Any]], tracker: LLMTracker
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
        self, messages: list[dict[str, Any]], tracker: LLMTracker
    ) -> ConversationMessage:
        try:
            ollama_tools = self._get_ollama_tools()
            chat_kwargs: dict[str, Any] = {
                "model": self.model_id,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            }

            if ollama_tools:
                chat_kwargs["tools"] = ollama_tools

            response = await self._client.chat(**chat_kwargs)

            iteration = 0
            while self._has_tool_calls(response) and iteration < MAX_TOOL_ITERATIONS:
                iteration += 1
                self._logger.info("processing_tool_calls", iteration=iteration)

                tool_calls = self._parse_tool_calls(response)
                assistant_message = response.get("message", {})
                messages.append(assistant_message)

                for tool_call in tool_calls:
                    result = await self._tool_executor.execute_tool(tool_call)
                    tool_message = {
                        "role": "tool",
                        "content": result.to_message(),
                    }
                    messages.append(tool_message)

                response = await self._client.chat(**chat_kwargs | {"messages": messages})

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

    def _has_tool_calls(self, response: dict[str, Any]) -> bool:
        message = response.get("message", {})
        tool_calls = message.get("tool_calls", [])
        return len(tool_calls) > 0

    def _parse_tool_calls(self, response: dict[str, Any]) -> list[ToolCall]:
        message = response.get("message", {})
        raw_tool_calls = message.get("tool_calls", [])

        tool_calls = []
        for i, tc in enumerate(raw_tool_calls):
            function = tc.get("function", {})
            tool_calls.append(
                ToolCall(
                    tool_name=function.get("name", ""),
                    arguments=function.get("arguments", {}),
                    call_id=str(i),
                )
            )
        return tool_calls

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

        augmented_prompt = await self._get_rag_augmented_prompt(input_text)
        messages = self._build_messages(input_text, chat_history, augmented_prompt)

        if self.streaming:
            return self._tracked_streaming_response(messages, request_id)
        else:
            return await self._tracked_sync_response(messages, request_id)

    async def _get_rag_augmented_prompt(self, input_text: str) -> str | None:
        if not RAG_ENABLED or not self.knowledge_scope:
            self._last_rag_context = None
            return None

        try:
            rag_chain = await get_rag_chain()
            augmented_prompt, context = await rag_chain.invoke(
                query=input_text,
                system_prompt=self.system_prompt or "",
                knowledge_scope=self.knowledge_scope,
            )

            if context.has_context:
                # Store context for later retrieval
                self._last_rag_context = context
                self._logger.info(
                    "rag_context_applied",
                    documents_used=len(context.documents),
                    token_estimate=context.token_estimate,
                )
                return augmented_prompt

            self._last_rag_context = None
            return None
        except Exception as e:
            self._logger.warning("rag_retrieval_failed", error=str(e))
            self._last_rag_context = None
            return None
    
    def get_last_rag_context(self) -> Any | None:
        """Get the RAG context from the last request."""
        return self._last_rag_context

    async def _tracked_streaming_response(
        self, messages: list[dict[str, Any]], request_id: str
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
        self, messages: list[dict[str, Any]], request_id: str
    ) -> ConversationMessage:
        tracker = LLMTracker(
            model=self.model_id,
            agent=self.name,
            streaming=False,
            request_id=request_id,
        )
        async with tracker:
            return await self._handle_sync_response(messages, tracker)
