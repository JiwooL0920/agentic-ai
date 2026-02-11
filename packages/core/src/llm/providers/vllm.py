"""vLLM Provider implementation using OpenAI-compatible API."""

import time
from collections.abc import AsyncIterable
from typing import Any

import httpx
import structlog

from .base import (
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMStreamChunk,
    ModelNotFoundError,
    ProviderCapabilities,
    ProviderError,
    RateLimitError,
)

logger = structlog.get_logger()


class VLLMProvider(LLMProvider):

    def __init__(self, config: LLMConfig):
        super().__init__(name="vllm", config=config)
        self._base_url = (config.base_url or "http://localhost:8000").rstrip("/")
        self._api_key = config.api_key or "EMPTY"
        self._logger = logger.bind(provider="vllm", model=config.model)
        self._timeout = httpx.Timeout(config.timeout, connect=10.0)

    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            tool_calling=True,
            vision=False,
            json_mode=True,
            max_context_tokens=self.config.extra.get("max_context_tokens", 32768),
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
            if msg.tool_call_id:
                converted["tool_call_id"] = msg.tool_call_id
            result.append(converted)
        return result

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        start_time = time.perf_counter()

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": self._convert_messages(messages),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": False,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")

        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                    headers=self._build_headers(),
                )
            except httpx.ConnectError as e:
                raise ProviderError(
                    f"Failed to connect to vLLM: {e}",
                    provider=self.name,
                    retriable=True,
                ) from e
            except httpx.TimeoutException as e:
                raise ProviderError(
                    f"vLLM request timed out: {e}",
                    provider=self.name,
                    retriable=True,
                ) from e

            if response.status_code == 429:
                retry_after = response.headers.get("retry-after")
                raise RateLimitError(
                    self.name,
                    retry_after=float(retry_after) if retry_after else None,
                )

            if response.status_code == 404:
                raise ModelNotFoundError(self.name, self.config.model)

            if response.status_code >= 400:
                raise ProviderError(
                    f"vLLM returned {response.status_code}: {response.text}",
                    provider=self.name,
                    retriable=response.status_code >= 500,
                    status_code=response.status_code,
                )

            data = response.json()

        latency_ms = (time.perf_counter() - start_time) * 1000

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})

        tool_calls = message.get("tool_calls")
        if tool_calls:
            tool_calls = [
                {
                    "id": tc.get("id"),
                    "type": tc.get("type", "function"),
                    "function": tc.get("function"),
                }
                for tc in tool_calls
            ]

        return LLMResponse(
            content=message.get("content", ""),
            model=data.get("model", self.config.model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            finish_reason=choice.get("finish_reason"),
            tool_calls=tool_calls,
            latency_ms=latency_ms,
            raw_response=data,
        )

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[LLMStreamChunk]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": self._convert_messages(messages),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                    headers=self._build_headers(),
                ) as response:
                    if response.status_code >= 400:
                        error_text = await response.aread()
                        raise ProviderError(
                            f"vLLM returned {response.status_code}: {error_text.decode()}",
                            provider=self.name,
                            retriable=response.status_code >= 500,
                            status_code=response.status_code,
                        )

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue

                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        import json

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choice = data.get("choices", [{}])[0]
                        delta = choice.get("delta", {})

                        yield LLMStreamChunk(
                            content=delta.get("content", ""),
                            finish_reason=choice.get("finish_reason"),
                            tool_calls=delta.get("tool_calls"),
                        )

            except httpx.ConnectError as e:
                raise ProviderError(
                    f"Failed to connect to vLLM: {e}",
                    provider=self.name,
                    retriable=True,
                ) from e

    async def health_check(self) -> bool:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                response = await client.get(
                    f"{self._base_url}/health",
                    headers=self._build_headers(),
                )
                return response.status_code == 200
            except Exception as e:
                self._logger.error("health_check_failed", error=str(e))
                return False

    async def get_model_info(self) -> dict[str, Any]:
        base_info = await super().get_model_info()

        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                response = await client.get(
                    f"{self._base_url}/v1/models",
                    headers=self._build_headers(),
                )
                if response.status_code == 200:
                    models_data = response.json()
                    base_info["available_models"] = [
                        m.get("id") for m in models_data.get("data", [])
                    ]
            except Exception:
                pass

        return base_info
