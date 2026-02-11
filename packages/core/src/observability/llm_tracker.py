"""LLM usage tracking with async context manager."""

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from .metrics import (
    LLM_ACTIVE_REQUESTS,
    LLM_COST_DOLLARS,
    LLM_ERRORS,
    LLM_REQUEST_DURATION,
    LLM_REQUESTS,
    LLM_TIME_TO_FIRST_TOKEN,
    LLM_TOKENS_INPUT,
    LLM_TOKENS_OUTPUT,
    get_model_cost,
)

logger = structlog.get_logger()


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    duration_seconds: float = 0.0
    time_to_first_token: float | None = None
    model: str = ""
    agent: str = ""
    streaming: bool = False
    request_id: str = ""
    error: str | None = None


@dataclass
class LLMTracker:
    model: str
    agent: str
    streaming: bool = False
    request_id: str = ""

    _start_time: float = field(default=0.0, init=False)
    _first_token_time: float | None = field(default=None, init=False)
    _usage: LLMUsage = field(default_factory=LLMUsage, init=False)

    async def __aenter__(self) -> "LLMTracker":
        self._start_time = time.perf_counter()
        self._usage = LLMUsage(
            model=self.model,
            agent=self.agent,
            streaming=self.streaming,
            request_id=self.request_id,
        )
        LLM_ACTIVE_REQUESTS.labels(model=self.model).inc()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration = time.perf_counter() - self._start_time
        self._usage.duration_seconds = duration
        LLM_ACTIVE_REQUESTS.labels(model=self.model).dec()

        streaming_label = "true" if self.streaming else "false"
        LLM_REQUEST_DURATION.labels(
            model=self.model, agent=self.agent, streaming=streaming_label
        ).observe(duration)

        if exc_type is not None:
            error_type = exc_type.__name__ if exc_type else "unknown"
            self._usage.error = str(exc_val) if exc_val else error_type
            LLM_REQUESTS.labels(model=self.model, agent=self.agent, status="error").inc()
            LLM_ERRORS.labels(
                model=self.model, agent=self.agent, error_type=error_type
            ).inc()
            logger.error(
                "llm_request_failed",
                model=self.model,
                agent=self.agent,
                error=self._usage.error,
                duration=duration,
                request_id=self.request_id,
            )
        else:
            LLM_REQUESTS.labels(model=self.model, agent=self.agent, status="success").inc()
            logger.info(
                "llm_request_completed",
                model=self.model,
                agent=self.agent,
                input_tokens=self._usage.input_tokens,
                output_tokens=self._usage.output_tokens,
                duration=duration,
                ttft=self._usage.time_to_first_token,
                request_id=self.request_id,
            )

    def record_first_token(self) -> None:
        if self._first_token_time is None:
            self._first_token_time = time.perf_counter()
            ttft = self._first_token_time - self._start_time
            self._usage.time_to_first_token = ttft
            LLM_TIME_TO_FIRST_TOKEN.labels(model=self.model, agent=self.agent).observe(ttft)

    def record_tokens(self, input_tokens: int, output_tokens: int) -> None:
        self._usage.input_tokens = input_tokens
        self._usage.output_tokens = output_tokens

        LLM_TOKENS_INPUT.labels(model=self.model, agent=self.agent).inc(input_tokens)
        LLM_TOKENS_OUTPUT.labels(model=self.model, agent=self.agent).inc(output_tokens)

        cost = get_model_cost(self.model, input_tokens, output_tokens)
        if cost > 0:
            LLM_COST_DOLLARS.labels(model=self.model, agent=self.agent).inc(cost)

    @property
    def usage(self) -> LLMUsage:
        return self._usage
