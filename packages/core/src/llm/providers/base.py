"""
LLM Provider base classes and interfaces.

Defines the abstract interface for all LLM providers (Ollama, vLLM, OpenAI, etc.)
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class LLMMessage:
    role: MessageRole | str
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    timeout: float = 60.0
    api_key: str | None = None
    base_url: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMStreamChunk:
    content: str
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    latency_ms: float = 0.0
    raw_response: dict[str, Any] | None = None

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


@dataclass
class ProviderCapabilities:
    streaming: bool = True
    tool_calling: bool = True
    vision: bool = False
    json_mode: bool = False
    max_context_tokens: int = 128000


class LLMProvider(ABC):

    def __init__(self, name: str, config: LLMConfig):
        self.name = name
        self.config = config
        self._capabilities: ProviderCapabilities | None = None

    @property
    def capabilities(self) -> ProviderCapabilities:
        if self._capabilities is None:
            self._capabilities = self._get_capabilities()
        return self._capabilities

    @abstractmethod
    def _get_capabilities(self) -> ProviderCapabilities:
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    async def get_model_info(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.config.model,
            "capabilities": {
                "streaming": self.capabilities.streaming,
                "tool_calling": self.capabilities.tool_calling,
                "vision": self.capabilities.vision,
                "json_mode": self.capabilities.json_mode,
                "max_context_tokens": self.capabilities.max_context_tokens,
            },
        }


class ProviderError(Exception):

    def __init__(
        self,
        message: str,
        provider: str,
        retriable: bool = False,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.retriable = retriable
        self.status_code = status_code


class RateLimitError(ProviderError):

    def __init__(self, provider: str, retry_after: float | None = None):
        super().__init__(
            f"Rate limit exceeded for {provider}",
            provider=provider,
            retriable=True,
            status_code=429,
        )
        self.retry_after = retry_after


class AuthenticationError(ProviderError):

    def __init__(self, provider: str):
        super().__init__(
            f"Authentication failed for {provider}",
            provider=provider,
            retriable=False,
            status_code=401,
        )


class ModelNotFoundError(ProviderError):

    def __init__(self, provider: str, model: str):
        super().__init__(
            f"Model '{model}' not found for {provider}",
            provider=provider,
            retriable=False,
            status_code=404,
        )
        self.model = model
