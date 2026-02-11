"""Prometheus metrics for LLM observability."""

from prometheus_client import Counter, Gauge, Histogram

LATENCY_BUCKETS = (0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0, 60.0)
TTFT_BUCKETS = (0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 2.0, 5.0)

LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total number of LLM requests",
    ["model", "agent", "status"],
)

LLM_TOKENS_INPUT = Counter(
    "llm_tokens_input_total",
    "Total input tokens processed",
    ["model", "agent"],
)

LLM_TOKENS_OUTPUT = Counter(
    "llm_tokens_output_total",
    "Total output tokens generated",
    ["model", "agent"],
)

LLM_REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["model", "agent", "streaming"],
    buckets=LATENCY_BUCKETS,
)

LLM_TIME_TO_FIRST_TOKEN = Histogram(
    "llm_time_to_first_token_seconds",
    "Time to first token for streaming responses",
    ["model", "agent"],
    buckets=TTFT_BUCKETS,
)

LLM_COST_DOLLARS = Counter(
    "llm_cost_dollars_total",
    "Estimated cost in USD",
    ["model", "agent"],
)

LLM_ACTIVE_REQUESTS = Gauge(
    "llm_active_requests",
    "Number of active LLM requests",
    ["model"],
)

LLM_ERRORS = Counter(
    "llm_errors_total",
    "Total number of LLM errors",
    ["model", "agent", "error_type"],
)

MODEL_COSTS_PER_1K_TOKENS = {
    "qwen2.5:32b": {"input": 0.0, "output": 0.0},
    "nomic-embed-text": {"input": 0.0, "output": 0.0},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
}


def get_model_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = MODEL_COSTS_PER_1K_TOKENS.get(model, {"input": 0.0, "output": 0.0})
    return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000
