"""
LLM Gateway - Multi-provider LLM routing with fallback support.

Provides a unified interface for multiple LLM providers with automatic
fallback, metrics tracking, and health checking.
"""

import asyncio
from collections.abc import AsyncIterable
from dataclasses import dataclass
from typing import Any

import structlog

from ..observability.llm_tracker import LLMTracker
from .providers.base import (
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMStreamChunk,
    ProviderError,
)
from .providers.ollama import OllamaProvider

logger = structlog.get_logger()


@dataclass
class ProviderStatus:
    """Tracks provider health status."""

    name: str
    healthy: bool = True
    consecutive_failures: int = 0
    last_error: str | None = None
    last_check_time: float = 0.0


@dataclass
class GatewayConfig:
    """Configuration for LLM Gateway."""

    default_provider: str = "ollama"
    fallback_enabled: bool = True
    max_failures_before_unhealthy: int = 3
    health_check_interval_seconds: float = 60.0
    request_timeout_seconds: float = 120.0


class LLMGateway:
    """
    Multi-provider LLM gateway with fallback support.

    Features:
    - Register multiple providers
    - Automatic fallback on provider failure
    - Integrated metrics tracking
    - Provider health monitoring
    """

    def __init__(self, config: GatewayConfig | None = None):
        self._config = config or GatewayConfig()
        self._providers: dict[str, LLMProvider] = {}
        self._fallback_chain: list[str] = []
        self._provider_status: dict[str, ProviderStatus] = {}
        self._logger = logger.bind(component="LLMGateway")

    def register_provider(
        self,
        name: str,
        provider: LLMProvider,
    ) -> None:
        """
        Register an LLM provider.

        Args:
            name: Unique name for this provider
            provider: LLMProvider instance
        """
        self._providers[name] = provider
        self._provider_status[name] = ProviderStatus(name=name)
        self._logger.info("provider_registered", provider=name, model=provider.config.model)

    def register_provider_from_config(
        self,
        name: str,
        provider_type: str,
        config: LLMConfig,
    ) -> None:
        """
        Register a provider from configuration.

        Args:
            name: Unique name for this provider
            provider_type: Type of provider (ollama, vllm, openai)
            config: LLMConfig for the provider
        """
        provider: LLMProvider

        if provider_type == "ollama":
            provider = OllamaProvider(config)
        elif provider_type == "vllm":
            from .providers.vllm import VLLMProvider

            provider = VLLMProvider(config)
        elif provider_type == "openai":
            # OpenAI provider is optional
            try:
                from .providers.openai import OpenAIProvider

                provider = OpenAIProvider(config)
            except ImportError:
                self._logger.warning(
                    "openai_provider_unavailable",
                    reason="openai package not installed",
                )
                raise ProviderError(
                    "OpenAI provider requires 'openai' package",
                    provider="openai",
                    retriable=False,
                ) from None
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

        self.register_provider(name, provider)

    def set_fallback_chain(self, providers: list[str]) -> None:
        """
        Set the fallback chain for providers.

        Args:
            providers: Ordered list of provider names to try
        """
        for name in providers:
            if name not in self._providers:
                raise ValueError(f"Provider '{name}' not registered")
        self._fallback_chain = providers
        self._logger.info("fallback_chain_set", chain=providers)

    def get_provider(self, name: str | None = None) -> LLMProvider:
        """
        Get a provider by name.

        Args:
            name: Provider name (uses default if None)

        Returns:
            LLMProvider instance
        """
        provider_name = name or self._config.default_provider
        if provider_name not in self._providers:
            available = list(self._providers.keys())
            raise ValueError(f"Provider '{provider_name}' not found. Available: {available}")
        return self._providers[provider_name]

    def _get_healthy_providers(self) -> list[str]:
        """Get list of healthy provider names in fallback order."""
        if not self._fallback_chain:
            # Return all providers if no fallback chain set
            return [
                name
                for name, status in self._provider_status.items()
                if status.healthy
            ]

        return [
            name
            for name in self._fallback_chain
            if self._provider_status.get(name, ProviderStatus(name)).healthy
        ]

    def _record_success(self, provider_name: str) -> None:
        """Record a successful request for a provider."""
        status = self._provider_status.get(provider_name)
        if status:
            status.consecutive_failures = 0
            status.healthy = True

    def _record_failure(self, provider_name: str, error: str) -> None:
        """Record a failed request for a provider."""
        status = self._provider_status.get(provider_name)
        if status:
            status.consecutive_failures += 1
            status.last_error = error
            if status.consecutive_failures >= self._config.max_failures_before_unhealthy:
                status.healthy = False
                self._logger.warning(
                    "provider_marked_unhealthy",
                    provider=provider_name,
                    failures=status.consecutive_failures,
                    error=error,
                )

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        provider: str | None = None,
        agent_name: str = "unknown",
        request_id: str = "",
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send a chat request with automatic fallback.

        Args:
            messages: List of messages
            tools: Optional list of tools
            provider: Specific provider to use (skips fallback)
            agent_name: Agent name for metrics
            request_id: Request ID for tracing
            **kwargs: Additional arguments for the provider

        Returns:
            LLMResponse from the successful provider
        """
        providers_to_try: list[str]

        if provider:
            # Specific provider requested - no fallback
            providers_to_try = [provider]
        elif self._config.fallback_enabled:
            providers_to_try = self._get_healthy_providers()
            if not providers_to_try:
                # All providers unhealthy - try all anyway
                providers_to_try = list(self._providers.keys())
                self._logger.warning("all_providers_unhealthy", trying_all=True)
        else:
            providers_to_try = [self._config.default_provider]

        last_error: Exception | None = None

        for provider_name in providers_to_try:
            llm_provider = self._providers.get(provider_name)
            if not llm_provider:
                continue

            async with LLMTracker(
                model=llm_provider.config.model,
                agent=agent_name,
                streaming=False,
                request_id=request_id,
            ) as tracker:
                try:
                    response = await asyncio.wait_for(
                        llm_provider.chat(messages, tools, **kwargs),
                        timeout=self._config.request_timeout_seconds,
                    )
                    tracker.record_tokens(response.input_tokens, response.output_tokens)
                    self._record_success(provider_name)

                    self._logger.debug(
                        "chat_completed",
                        provider=provider_name,
                        model=response.model,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        latency_ms=response.latency_ms,
                    )
                    return response

                except TimeoutError:
                    error_msg = f"Request timed out after {self._config.request_timeout_seconds}s"
                    self._record_failure(provider_name, error_msg)
                    last_error = ProviderError(error_msg, provider_name, retriable=True)
                    self._logger.warning(
                        "provider_timeout",
                        provider=provider_name,
                        timeout=self._config.request_timeout_seconds,
                    )

                except ProviderError as e:
                    self._record_failure(provider_name, str(e))
                    last_error = e
                    self._logger.warning(
                        "provider_error",
                        provider=provider_name,
                        error=str(e),
                        retriable=e.retriable,
                    )
                    if not e.retriable:
                        raise

                except Exception as e:
                    self._record_failure(provider_name, str(e))
                    last_error = e
                    self._logger.error(
                        "provider_unexpected_error",
                        provider=provider_name,
                        error=str(e),
                    )

        # All providers failed
        if last_error:
            raise last_error
        raise ProviderError(
            "No providers available",
            provider="gateway",
            retriable=False,
        )

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        provider: str | None = None,
        agent_name: str = "unknown",
        request_id: str = "",
        **kwargs: Any,
    ) -> AsyncIterable[LLMStreamChunk]:
        """
        Send a streaming chat request with automatic fallback.

        Note: Fallback only happens on initial connection failure.
        Once streaming starts, failures will raise exceptions.

        Args:
            messages: List of messages
            tools: Optional list of tools
            provider: Specific provider to use
            agent_name: Agent name for metrics
            request_id: Request ID for tracing
            **kwargs: Additional arguments

        Yields:
            LLMStreamChunk from the provider
        """
        providers_to_try: list[str]

        if provider:
            providers_to_try = [provider]
        elif self._config.fallback_enabled:
            providers_to_try = self._get_healthy_providers()
            if not providers_to_try:
                providers_to_try = list(self._providers.keys())
        else:
            providers_to_try = [self._config.default_provider]

        last_error: Exception | None = None

        for provider_name in providers_to_try:
            llm_provider = self._providers.get(provider_name)
            if not llm_provider:
                continue

            try:
                # Try to initiate streaming
                stream = llm_provider.chat_stream(messages, tools, **kwargs)

                # Use tracker for metrics
                async with LLMTracker(
                    model=llm_provider.config.model,
                    agent=agent_name,
                    streaming=True,
                    request_id=request_id,
                ) as tracker:
                    first_chunk = True
                    total_output_tokens = 0

                    async for chunk in stream:
                        if first_chunk:
                            tracker.record_first_token()
                            first_chunk = False

                        # Estimate output tokens (1 token ≈ 4 chars)
                        total_output_tokens += max(1, len(chunk.content) // 4)
                        yield chunk

                    # Record final token counts (input tokens not available in streaming)
                    tracker.record_tokens(0, total_output_tokens)
                    self._record_success(provider_name)
                    return

            except ProviderError as e:
                self._record_failure(provider_name, str(e))
                last_error = e
                self._logger.warning(
                    "stream_provider_error",
                    provider=provider_name,
                    error=str(e),
                )
                if not e.retriable:
                    raise

            except Exception as e:
                self._record_failure(provider_name, str(e))
                last_error = e
                self._logger.error(
                    "stream_unexpected_error",
                    provider=provider_name,
                    error=str(e),
                )

        if last_error:
            raise last_error
        raise ProviderError(
            "No providers available for streaming",
            provider="gateway",
            retriable=False,
        )

    async def health_check(self, provider: str | None = None) -> dict[str, bool]:
        """
        Check health of providers.

        Args:
            provider: Specific provider to check (all if None)

        Returns:
            Dict mapping provider names to health status
        """
        results: dict[str, bool] = {}

        providers_to_check = (
            [provider] if provider else list(self._providers.keys())
        )

        for name in providers_to_check:
            llm_provider = self._providers.get(name)
            if not llm_provider:
                results[name] = False
                continue

            try:
                healthy = await llm_provider.health_check()
                results[name] = healthy

                status = self._provider_status.get(name)
                if status:
                    status.healthy = healthy
                    if healthy:
                        status.consecutive_failures = 0

            except Exception as e:
                results[name] = False
                self._logger.error("health_check_failed", provider=name, error=str(e))

        return results

    def get_provider_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all providers."""
        return {
            name: {
                "healthy": status.healthy,
                "consecutive_failures": status.consecutive_failures,
                "last_error": status.last_error,
            }
            for name, status in self._provider_status.items()
        }

    @property
    def providers(self) -> dict[str, LLMProvider]:
        """Get registered providers."""
        return self._providers.copy()


# Global gateway instance
_gateway: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    """
    Get the global LLM gateway instance.

    Returns:
        LLMGateway instance (creates if not exists)
    """
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway


def configure_gateway(config: GatewayConfig) -> LLMGateway:
    """
    Configure and return the global LLM gateway.

    Args:
        config: Gateway configuration

    Returns:
        Configured LLMGateway instance
    """
    global _gateway
    _gateway = LLMGateway(config)
    return _gateway
