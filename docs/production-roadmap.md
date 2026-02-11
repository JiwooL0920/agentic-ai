# Production Enterprise Roadmap

Gap analysis and implementation plan to align with enterprise ML platform patterns.

---

## Current State Assessment

### ✅ Already Enterprise-Grade

| Component | Implementation | Status |
|-----------|---------------|--------|
| **API Framework** | FastAPI with async | ✅ Industry standard |
| **Orchestration** | agent-squad supervisor pattern | ✅ AWS-aligned |
| **Session Storage** | ScyllaDB/DynamoDB | ✅ Discord-scale proven |
| **Cache Layer** | Redis Sentinel | ✅ HA-ready |
| **Config Management** | Pydantic Settings | ✅ 12-factor compliant |
| **Structured Logging** | structlog | ✅ Production-ready |
| **Health Checks** | /health, /ready, /live | ✅ K8s native |
| **Metrics Endpoint** | Prometheus /metrics | ✅ Basic setup |
| **Streaming** | SSE with EventSourceResponse | ✅ Working |
| **CORS** | Configured | ✅ Ready |

### ❌ Missing for Enterprise Production

| Component | Gap | Priority | Effort |
|-----------|-----|----------|--------|
| **Tool/Function Calling** | Stubbed, not wired | 🔴 High | 3-5 days |
| **RAG Pipeline** | pgvector configured, not used | 🔴 High | 3-5 days |
| **LLM Observability** | No token tracking, latency metrics | 🔴 High | 2-3 days |
| **LLM Gateway** | Direct Ollama calls, no abstraction | 🟡 Medium | 2-3 days |
| **Cost Tracking** | None | 🟡 Medium | 1-2 days |
| **Rate Limiting** | File exists but not integrated | 🟡 Medium | 1 day |
| **Prompt Versioning** | Hardcoded prompts | 🟡 Medium | 1-2 days |
| **Error Recovery** | Basic try/catch | 🟡 Medium | 1-2 days |
| **Multi-Provider Support** | Ollama only | 🟢 Low | 2-3 days |
| **vLLM Migration** | Ollama (dev-only) | 🟢 Low | 1-2 days |

---

## Implementation Plan

### Phase 1: Core LLM Features (Week 1-2)

#### 1.1 Tool/Function Calling

**Current State**: Tools defined in YAML but never executed.

```yaml
# blueprints/devassist/agents/systemarchitect.yaml
tools:
  - name: diagram_generate
    description: Generate architecture diagrams
```

**Target State**: Native Ollama tool calling with execution.

**Implementation**:

```python
# packages/core/src/tools/base.py
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

class ToolResult(BaseModel):
    """Result from tool execution."""
    success: bool
    output: Any
    error: str | None = None

class BaseTool(ABC):
    """Base class for agent tools."""
    
    name: str
    description: str
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    def to_ollama_format(self) -> dict:
        """Convert to Ollama tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters_schema(),
            }
        }
    
    @abstractmethod
    def get_parameters_schema(self) -> dict:
        """Return JSON Schema for parameters."""
        pass


# packages/core/src/tools/registry.py
class ToolRegistry:
    """Registry for available tools."""
    
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)
    
    def get_tools_for_agent(self, tool_names: list[str]) -> list[BaseTool]:
        return [self._tools[name] for name in tool_names if name in self._tools]


# packages/core/src/tools/implementations/search.py
class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for current information"
    
    async def execute(self, query: str) -> ToolResult:
        # Implementation using httpx or search API
        pass
    
    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
```

**Files to create**:
- `packages/core/src/tools/__init__.py`
- `packages/core/src/tools/base.py`
- `packages/core/src/tools/registry.py`
- `packages/core/src/tools/executor.py`
- `packages/core/src/tools/implementations/` (various tools)

**Files to modify**:
- `packages/core/src/agents/base.py` - Add tool execution loop
- `packages/core/src/orchestrator/supervisor.py` - Pass tools to agents

---

#### 1.2 RAG Pipeline

**Current State**: pgvector in dependencies, embedding model configured, not implemented.

**Target State**: Working RAG with document ingestion and retrieval.

**Implementation**:

```python
# packages/core/src/rag/embeddings.py
from ollama import AsyncClient

class OllamaEmbeddings:
    """Generate embeddings using Ollama."""
    
    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model
        self._client = AsyncClient()
    
    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings(
            model=self.model,
            prompt=text,
        )
        return response["embedding"]
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]


# packages/core/src/rag/vector_store.py
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

class PgVectorStore:
    """Vector store using pgvector."""
    
    async def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]],
    ):
        """Add documents with embeddings."""
        pass
    
    async def similarity_search(
        self,
        query_embedding: list[float],
        k: int = 5,
        filter_metadata: dict | None = None,
    ) -> list[Document]:
        """Search for similar documents."""
        # Uses pgvector's <=> operator for cosine distance
        pass


# packages/core/src/rag/retriever.py
class RAGRetriever:
    """Retrieval-Augmented Generation retriever."""
    
    def __init__(
        self,
        embeddings: OllamaEmbeddings,
        vector_store: PgVectorStore,
    ):
        self.embeddings = embeddings
        self.vector_store = vector_store
    
    async def retrieve(
        self,
        query: str,
        k: int = 5,
        knowledge_scope: list[str] | None = None,
    ) -> list[Document]:
        """Retrieve relevant documents for query."""
        query_embedding = await self.embeddings.embed(query)
        
        filter_metadata = None
        if knowledge_scope:
            filter_metadata = {"scope": {"$in": knowledge_scope}}
        
        return await self.vector_store.similarity_search(
            query_embedding,
            k=k,
            filter_metadata=filter_metadata,
        )


# packages/core/src/rag/chain.py
class RAGChain:
    """RAG chain that combines retrieval with generation."""
    
    async def invoke(
        self,
        query: str,
        agent: OllamaAgent,
        knowledge_scope: list[str] | None = None,
    ) -> str:
        # 1. Retrieve relevant documents
        docs = await self.retriever.retrieve(query, knowledge_scope=knowledge_scope)
        
        # 2. Build context from documents
        context = self._build_context(docs)
        
        # 3. Augment query with context
        augmented_query = f"""Context:
{context}

Question: {query}

Answer based on the context provided. If the context doesn't contain relevant information, say so."""
        
        # 4. Generate response
        return await agent.generate(augmented_query)
```

**Files to create**:
- `packages/core/src/rag/__init__.py`
- `packages/core/src/rag/embeddings.py`
- `packages/core/src/rag/vector_store.py`
- `packages/core/src/rag/retriever.py`
- `packages/core/src/rag/chain.py`
- `packages/core/src/rag/document.py`
- `packages/core/src/rag/chunking.py`

**Database migration**:
```sql
-- migrations/001_add_vector_extension.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(768),  -- nomic-embed-text dimension
    metadata JSONB,
    scope VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

---

### Phase 2: Observability (Week 2-3)

#### 2.1 LLM-Specific Metrics

**Current State**: Basic Prometheus endpoint, no LLM metrics.

**Target State**: Comprehensive LLM observability.

**Implementation**:

```python
# packages/core/src/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["model", "agent", "status"]
)

LLM_TOKENS_INPUT = Counter(
    "llm_tokens_input_total",
    "Total input tokens",
    ["model", "agent"]
)

LLM_TOKENS_OUTPUT = Counter(
    "llm_tokens_output_total",
    "Total output tokens",
    ["model", "agent"]
)

# Latency metrics
LLM_REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration",
    ["model", "agent", "streaming"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

LLM_TIME_TO_FIRST_TOKEN = Histogram(
    "llm_time_to_first_token_seconds",
    "Time to first token for streaming requests",
    ["model", "agent"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

# Cost tracking (estimated)
LLM_COST_DOLLARS = Counter(
    "llm_cost_dollars_total",
    "Estimated LLM cost in dollars",
    ["model", "agent"]
)

# Active requests
LLM_ACTIVE_REQUESTS = Gauge(
    "llm_active_requests",
    "Currently active LLM requests",
    ["model"]
)


# packages/core/src/observability/llm_tracker.py
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

@dataclass
class LLMUsage:
    input_tokens: int
    output_tokens: int
    duration_seconds: float
    time_to_first_token: float | None = None

class LLMTracker:
    """Track LLM usage metrics."""
    
    @asynccontextmanager
    async def track_request(
        self,
        model: str,
        agent: str,
        streaming: bool = False,
    ):
        """Context manager to track LLM request metrics."""
        LLM_ACTIVE_REQUESTS.labels(model=model).inc()
        LLM_REQUESTS.labels(model=model, agent=agent, status="started").inc()
        
        start_time = time.perf_counter()
        first_token_time = None
        usage = LLMUsage(0, 0, 0)
        
        try:
            yield usage
            
            # Record success metrics
            duration = time.perf_counter() - start_time
            usage.duration_seconds = duration
            
            LLM_REQUESTS.labels(model=model, agent=agent, status="success").inc()
            LLM_REQUEST_DURATION.labels(
                model=model, agent=agent, streaming=str(streaming)
            ).observe(duration)
            
            if usage.input_tokens:
                LLM_TOKENS_INPUT.labels(model=model, agent=agent).inc(usage.input_tokens)
            if usage.output_tokens:
                LLM_TOKENS_OUTPUT.labels(model=model, agent=agent).inc(usage.output_tokens)
            
            if usage.time_to_first_token:
                LLM_TIME_TO_FIRST_TOKEN.labels(model=model, agent=agent).observe(
                    usage.time_to_first_token
                )
            
            # Estimate cost (customize per model)
            cost = self._estimate_cost(model, usage.input_tokens, usage.output_tokens)
            LLM_COST_DOLLARS.labels(model=model, agent=agent).inc(cost)
            
        except Exception:
            LLM_REQUESTS.labels(model=model, agent=agent, status="error").inc()
            raise
        finally:
            LLM_ACTIVE_REQUESTS.labels(model=model).dec()
    
    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on model pricing."""
        # Local Ollama is free, but track for capacity planning
        # These would be real costs for cloud providers
        pricing = {
            "gpt-4": {"input": 0.03 / 1000, "output": 0.06 / 1000},
            "gpt-3.5-turbo": {"input": 0.0005 / 1000, "output": 0.0015 / 1000},
            "claude-3-opus": {"input": 0.015 / 1000, "output": 0.075 / 1000},
            # Ollama models - track tokens but $0 cost
            "qwen2.5:32b": {"input": 0, "output": 0},
        }
        
        rates = pricing.get(model, {"input": 0, "output": 0})
        return (input_tokens * rates["input"]) + (output_tokens * rates["output"])
```

**Integration with agent**:

```python
# packages/core/src/agents/base.py (modified)
class OllamaAgent(Agent):
    async def process_request(self, ...):
        tracker = LLMTracker()
        
        async with tracker.track_request(
            model=self.model_id,
            agent=self.name,
            streaming=self.streaming,
        ) as usage:
            # ... existing code ...
            
            # After response, update usage
            usage.input_tokens = response.get("prompt_eval_count", 0)
            usage.output_tokens = response.get("eval_count", 0)
```

**Files to create**:
- `packages/core/src/observability/__init__.py`
- `packages/core/src/observability/metrics.py`
- `packages/core/src/observability/llm_tracker.py`
- `packages/core/src/observability/tracing.py` (OpenTelemetry)

---

#### 2.2 Langfuse Integration (Optional)

For richer LLM observability without building everything:

```python
# packages/core/src/observability/langfuse_client.py
from langfuse import Langfuse

class LangfuseTracker:
    """Optional Langfuse integration for LLM observability."""
    
    def __init__(self):
        self.client = Langfuse()
    
    def trace_generation(
        self,
        name: str,
        input: str,
        output: str,
        model: str,
        usage: dict,
        metadata: dict | None = None,
    ):
        self.client.generation(
            name=name,
            input=input,
            output=output,
            model=model,
            usage=usage,
            metadata=metadata,
        )
```

---

### Phase 3: LLM Gateway & Resilience (Week 3-4)

#### 3.1 LLM Gateway Abstraction

**Current State**: Direct Ollama calls scattered in code.

**Target State**: Unified gateway supporting multiple providers.

```python
# packages/core/src/llm/__init__.py
# packages/core/src/llm/gateway.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterable

@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str

@dataclass  
class LLMConfig:
    provider: str  # "ollama", "openai", "anthropic", "vllm"
    model: str
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 120.0

class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncIterable[str]:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass

class OllamaProvider(LLMProvider):
    # Implementation
    pass

class VLLMProvider(LLMProvider):
    """vLLM uses OpenAI-compatible API."""
    pass

class OpenAIProvider(LLMProvider):
    pass

class LLMGateway:
    """
    Unified LLM gateway with:
    - Multiple provider support
    - Automatic fallbacks
    - Rate limiting
    - Metrics collection
    """
    
    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._fallback_chain: list[str] = []
        self._tracker = LLMTracker()
    
    def register_provider(self, name: str, config: LLMConfig):
        provider_class = {
            "ollama": OllamaProvider,
            "vllm": VLLMProvider,
            "openai": OpenAIProvider,
        }[config.provider]
        self._providers[name] = provider_class(config)
    
    def set_fallback_chain(self, chain: list[str]):
        """Set fallback order for providers."""
        self._fallback_chain = chain
    
    async def chat(
        self,
        messages: list[dict],
        provider: str | None = None,
        tools: list[dict] | None = None,
        stream: bool = False,
        agent_name: str = "unknown",
    ) -> LLMResponse | AsyncIterable[str]:
        """Route request to provider with fallback."""
        
        providers_to_try = [provider] if provider else self._fallback_chain
        last_error = None
        
        for provider_name in providers_to_try:
            if provider_name not in self._providers:
                continue
                
            try:
                async with self._tracker.track_request(
                    model=provider_name,
                    agent=agent_name,
                    streaming=stream,
                ) as usage:
                    response = await self._providers[provider_name].chat(
                        messages, tools, stream
                    )
                    
                    if not stream:
                        usage.input_tokens = response.input_tokens
                        usage.output_tokens = response.output_tokens
                    
                    return response
                    
            except Exception as e:
                logger.warning(
                    "provider_failed",
                    provider=provider_name,
                    error=str(e),
                )
                last_error = e
                continue
        
        raise RuntimeError(f"All providers failed. Last error: {last_error}")
```

---

#### 3.2 Rate Limiting Integration

**Current State**: `rate_limiter.py` exists but not integrated.

```python
# packages/core/src/api/middleware/rate_limit.py
from fastapi import Request, HTTPException
from ..cache.rate_limiter import RateLimiter

async def rate_limit_middleware(request: Request, call_next):
    """Rate limit middleware for API endpoints."""
    
    # Extract user identifier
    user_id = request.headers.get("X-User-ID", "anonymous")
    
    limiter = RateLimiter()
    
    # Check rate limit
    allowed, remaining, reset_at = await limiter.check(
        key=f"api:{user_id}",
        limit=100,  # requests per minute
        window=60,
    )
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_at),
            }
        )
    
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
```

---

#### 3.3 Retry & Circuit Breaker

```python
# packages/core/src/llm/resilience.py
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class CircuitBreakerState:
    failures: int = 0
    last_failure: datetime | None = None
    state: str = "closed"  # closed, open, half-open
    
class CircuitBreaker:
    """Circuit breaker for LLM providers."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: timedelta = timedelta(seconds=30),
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._states: dict[str, CircuitBreakerState] = {}
    
    def is_available(self, provider: str) -> bool:
        state = self._states.get(provider, CircuitBreakerState())
        
        if state.state == "closed":
            return True
        
        if state.state == "open":
            if datetime.now() - state.last_failure > self.recovery_timeout:
                state.state = "half-open"
                return True
            return False
        
        return True  # half-open allows one request
    
    def record_success(self, provider: str):
        state = self._states.get(provider, CircuitBreakerState())
        state.failures = 0
        state.state = "closed"
        self._states[provider] = state
    
    def record_failure(self, provider: str):
        state = self._states.get(provider, CircuitBreakerState())
        state.failures += 1
        state.last_failure = datetime.now()
        
        if state.failures >= self.failure_threshold:
            state.state = "open"
        
        self._states[provider] = state


async def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
):
    """Retry with exponential backoff."""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                await asyncio.sleep(delay)
    
    raise last_error
```

---

### Phase 4: Prompt Management (Week 4)

#### 4.1 Prompt Versioning

**Current State**: Prompts hardcoded in `prompts.py`.

**Target State**: Versioned, auditable prompt management.

```python
# packages/core/src/prompts/manager.py
from pathlib import Path
import yaml
from pydantic import BaseModel

class PromptVersion(BaseModel):
    version: str
    content: str
    variables: list[str]
    created_at: str
    description: str | None = None

class PromptTemplate(BaseModel):
    name: str
    description: str
    current_version: str
    versions: dict[str, PromptVersion]

class PromptManager:
    """
    Manage versioned prompts.
    
    Structure:
    prompts/
    ├── routing.yaml
    ├── supervisor.yaml
    └── agents/
        ├── systemarchitect.yaml
        └── kubernetes.yaml
    """
    
    def __init__(self, prompts_dir: Path):
        self.prompts_dir = prompts_dir
        self._cache: dict[str, PromptTemplate] = {}
        self._load_all()
    
    def _load_all(self):
        for yaml_file in self.prompts_dir.rglob("*.yaml"):
            template = self._load_template(yaml_file)
            self._cache[template.name] = template
    
    def get(
        self,
        name: str,
        version: str | None = None,
        **variables,
    ) -> str:
        """Get prompt, optionally specific version, with variables filled."""
        template = self._cache.get(name)
        if not template:
            raise ValueError(f"Prompt '{name}' not found")
        
        version = version or template.current_version
        prompt_version = template.versions.get(version)
        if not prompt_version:
            raise ValueError(f"Version '{version}' not found for prompt '{name}'")
        
        # Fill in variables
        content = prompt_version.content
        for var, value in variables.items():
            content = content.replace(f"{{{var}}}", str(value))
        
        return content
    
    def list_prompts(self) -> list[str]:
        return list(self._cache.keys())
    
    def get_versions(self, name: str) -> list[str]:
        template = self._cache.get(name)
        return list(template.versions.keys()) if template else []
```

**Example prompt YAML**:

```yaml
# prompts/routing.yaml
name: routing
description: Supervisor agent routing prompt
current_version: "1.2"

versions:
  "1.0":
    created_at: "2026-01-15"
    description: Initial routing prompt
    variables: [agent_descriptions, user_query]
    content: |
      You are a supervisor agent. Route the query to the best agent.
      
      Agents: {agent_descriptions}
      Query: {user_query}
      
      Respond with agent name only.

  "1.1":
    created_at: "2026-01-20"
    description: Added explicit instructions
    variables: [agent_descriptions, user_query]
    content: |
      You are a supervisor agent in a multi-agent system.
      ...

  "1.2":
    created_at: "2026-02-01"
    description: Current production version
    variables: [agent_descriptions, user_query]
    content: |
      You are a supervisor agent in a multi-agent system. Your ONLY job is to analyze user queries and route them to the most appropriate specialist agent.
      
      Available Specialist Agents:
      {agent_descriptions}
      
      User Query: "{user_query}"
      
      Instructions:
      1. Carefully analyze what the user is asking about
      2. Determine which specialist agent is BEST suited
      3. Respond with ONLY the exact agent name
      
      Your response (agent name only):
```

---

## Summary: Implementation Priority

### 🔴 High Priority (Do First)

| Item | Effort | Impact |
|------|--------|--------|
| Tool/Function Calling | 3-5 days | Enables agent capabilities |
| RAG Pipeline | 3-5 days | Enables knowledge-augmented responses |
| LLM Metrics | 2-3 days | Production visibility |

### 🟡 Medium Priority (Next)

| Item | Effort | Impact |
|------|--------|--------|
| LLM Gateway abstraction | 2-3 days | Multi-provider, cleaner code |
| Rate Limiting integration | 1 day | Production safety |
| Prompt Versioning | 1-2 days | Audit trail, A/B testing |
| Retry/Circuit Breaker | 1-2 days | Resilience |

### 🟢 Low Priority (Future)

| Item | Effort | Impact |
|------|--------|--------|
| vLLM Migration | 1-2 days | Only needed at scale |
| Multi-Provider (OpenAI/Anthropic) | 2-3 days | Fallback options |
| Langfuse integration | 1 day | Enhanced observability |

---

## Quick Wins (Can Do Today)

1. **Enable existing rate limiter** - just wire it into middleware
2. **Add token counting** - Ollama returns this in response
3. **Extract prompts to YAML** - move from `prompts.py` to files
4. **Add request ID logging** - correlation across services

---

## Recommended Order

```
Week 1: Tool Calling + Basic Metrics
Week 2: RAG Pipeline  
Week 3: LLM Gateway + Rate Limiting
Week 4: Prompt Management + Resilience
```

This gives you production-grade capabilities incrementally, with working features at each milestone.
