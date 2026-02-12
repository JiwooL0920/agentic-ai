"""Ollama LLM Provider implementation."""

import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import structlog
from ollama import AsyncClient

from .base import (
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMStreamChunk,
    ModelNotFoundError,
    ProviderCapabilities,
    ProviderError,
)

logger = structlog.get_logger()


class OllamaProvider(LLMProvider):

    def __init__(self, config: LLMConfig):
        super().__init__(name="ollama", config=config)
        base_url = config.base_url or "http://localhost:11434"
        self._client = AsyncClient(host=base_url)
        self._logger = logger.bind(provider="ollama", model=config.model)

    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            tool_calling=True,
            vision=False,
            json_mode=True,
            max_context_tokens=128000,
        )

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        result = []
        for msg in messages:
            role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            converted: dict[str, Any] = {
                "role": role,
                "content": msg.content,
            }
            if msg.tool_calls:
                converted["tool_calls"] = msg.tool_calls
            result.append(converted)
        return result

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        start_time = time.perf_counter()

        ollama_messages = self._convert_messages(messages)

        chat_kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
            },
        }

        if tools:
            chat_kwargs["tools"] = tools

        if "format" in kwargs:
            chat_kwargs["format"] = kwargs["format"]

        try:
            response = await self._client.chat(**chat_kwargs)
        except httpx.ConnectError as e:
            raise ProviderError(
                f"Failed to connect to Ollama: {e}",
                provider=self.name,
                retriable=True,
            ) from e
        except Exception as e:
            if "model" in str(e).lower() and "not found" in str(e).lower():
                raise ModelNotFoundError(self.name, self.config.model) from e
            raise ProviderError(
                f"Ollama chat failed: {e}",
                provider=self.name,
                retriable=True,
            ) from e

        latency_ms = (time.perf_counter() - start_time) * 1000

        content = response.get("message", {}).get("content", "")
        tool_calls = response.get("message", {}).get("tool_calls")
        input_tokens = response.get("prompt_eval_count", 0)
        output_tokens = response.get("eval_count", 0)

        return LLMResponse(
            content=content,
            model=self.config.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            finish_reason=response.get("done_reason"),
            tool_calls=tool_calls,
            latency_ms=latency_ms,
            raw_response=dict(response) if response else None,
        )

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        ollama_messages = self._convert_messages(messages)

        chat_kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
            },
        }

        if tools:
            chat_kwargs["tools"] = tools

        try:
            response = await self._client.chat(**chat_kwargs)
            async for chunk in response:
                content = chunk.get("message", {}).get("content", "")
                done = chunk.get("done", False)
                finish_reason = chunk.get("done_reason") if done else None

                yield LLMStreamChunk(
                    content=content,
                    finish_reason=finish_reason,
                    tool_calls=chunk.get("message", {}).get("tool_calls"),
                )

        except httpx.ConnectError as e:
            raise ProviderError(
                f"Failed to connect to Ollama: {e}",
                provider=self.name,
                retriable=True,
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Ollama streaming failed: {e}",
                provider=self.name,
                retriable=True,
            ) from e

    async def health_check(self) -> bool:
        try:
            models = await self._client.list()
            available_models = [m.get("name", "") for m in models.get("models", [])]
            model_available = any(
                self.config.model in m or m.startswith(self.config.model.split(":")[0])
                for m in available_models
            )
            if not model_available:
                self._logger.warning(
                    "model_not_available",
                    model=self.config.model,
                    available=available_models[:5],
                )
            return True
        except Exception as e:
            self._logger.error("health_check_failed", error=str(e))
            return False
