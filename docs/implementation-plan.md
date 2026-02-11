# Production Implementation Plan

Multi-phase implementation plan to achieve enterprise-grade ML platform architecture.

**Timeline**: 4 weeks  
**Effort**: ~20-25 engineering days  
**Goal**: Production-ready multi-agent LLM platform

---

## Table of Contents

1. [Overview](#overview)
2. [Phase 1: LLM Observability](#phase-1-llm-observability-week-1)
3. [Phase 2: Tool/Function Calling](#phase-2-toolfunction-calling-week-1-2)
4. [Phase 3: RAG Pipeline](#phase-3-rag-pipeline-week-2)
5. [Phase 4: LLM Gateway](#phase-4-llm-gateway-week-3)
6. [Phase 5: Resilience & Rate Limiting](#phase-5-resilience--rate-limiting-week-3)
7. [Phase 6: Prompt Management](#phase-6-prompt-management-week-4)
8. [Phase 7: Production Hardening](#phase-7-production-hardening-week-4)
9. [File Structure](#file-structure)
10. [Migration Checklist](#migration-checklist)

---

## Overview

### Current State vs Target State

| Component | Current | Target | Gap |
|-----------|---------|--------|-----|
| LLM Calls | Direct Ollama | Gateway with metrics | No abstraction, no tracking |
| Tools | YAML stubs | Executable tools | Not implemented |
| RAG | pgvector configured | Working pipeline | Not implemented |
| Observability | Basic Prometheus | LLM-specific metrics | No token/latency/cost tracking |
| Rate Limiting | File exists | Integrated middleware | Not wired |
| Prompts | Hardcoded | Versioned YAML | No audit trail |
| Resilience | Basic try/catch | Circuit breaker + retry | Minimal |

### Architecture After Implementation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Layer                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  FastAPI + Rate Limiting Middleware + Request Tracing                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ ChatService  │  │ RAGService   │  │ ToolService  │  │PromptManager │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Orchestration Layer                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  SupervisorOrchestrator + Agent Registry + Tool Executor                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LLM Gateway                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Provider Abstraction + Fallbacks + Circuit Breaker + Metrics           ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                ││
│  │  │  Ollama  │  │   vLLM   │  │  OpenAI  │  │ Anthropic│                ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Observability Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Prometheus  │  │   Grafana    │  │  LLMTracker  │  │   Langfuse   │    │
│  │   Metrics    │  │  Dashboards  │  │   (custom)   │  │  (optional)  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: LLM Observability (Week 1)

**Effort**: 2-3 days  
**Priority**: 🔴 High  
**Dependencies**: None

### Objective

Add comprehensive LLM metrics tracking: tokens, latency, cost, errors.

### Tasks

#### 1.1 Create Prometheus Metrics

**File**: `packages/core/src/observability/metrics.py`

```python
# Metrics to implement:
# - llm_requests_total (Counter) - by model, agent, status
# - llm_tokens_input_total (Counter) - by model, agent
# - llm_tokens_output_total (Counter) - by model, agent  
# - llm_request_duration_seconds (Histogram) - by model, agent, streaming
# - llm_time_to_first_token_seconds (Histogram) - by model, agent
# - llm_cost_dollars_total (Counter) - by model, agent
# - llm_active_requests (Gauge) - by model
# - llm_errors_total (Counter) - by model, agent, error_type
```

**Acceptance Criteria**:
- [ ] All metrics defined with appropriate labels
- [ ] Histogram buckets tuned for LLM latencies (0.1s - 60s range)
- [ ] Cost calculation function for different models

#### 1.2 Create LLM Tracker

**File**: `packages/core/src/observability/llm_tracker.py`

```python
# Implement:
# - LLMUsage dataclass (input_tokens, output_tokens, duration, ttft)
# - LLMTracker class with async context manager
# - track_request() method that records all metrics
# - Automatic error counting on exceptions
```

**Acceptance Criteria**:
- [ ] Context manager pattern for easy integration
- [ ] Captures time-to-first-token for streaming
- [ ] Thread-safe metric updates

#### 1.3 Integrate with OllamaAgent

**File**: `packages/core/src/agents/base.py` (modify)

```python
# Modify process_request() to:
# - Wrap LLM calls with tracker.track_request()
# - Extract token counts from Ollama response
# - Record TTFT for streaming responses
```

**Acceptance Criteria**:
- [ ] All agent LLM calls are tracked
- [ ] Token counts extracted from `prompt_eval_count` and `eval_count`
- [ ] Streaming TTFT captured on first chunk

#### 1.4 Create Grafana Dashboard

**File**: `infrastructure/grafana/dashboards/llm-metrics.json`

```
Dashboard panels:
- Request rate by model/agent
- P50/P95/P99 latency
- Token throughput (input/output)
- Error rate
- Active requests gauge
- Cost accumulation (if using paid APIs)
```

**Acceptance Criteria**:
- [ ] Dashboard JSON exportable
- [ ] All key metrics visualized
- [ ] Time range selectors working

#### 1.5 Add Request ID Tracing

**File**: `packages/core/src/api/middleware/request_id.py`

```python
# Implement:
# - Generate UUID for each request
# - Add to structlog context
# - Return in response headers (X-Request-ID)
# - Pass through to LLM tracker
```

**Acceptance Criteria**:
- [ ] Every log line includes request_id
- [ ] Request ID in response headers
- [ ] Can trace request through all layers

### Deliverables

| Deliverable | Type | Path |
|-------------|------|------|
| Prometheus metrics | New file | `src/observability/metrics.py` |
| LLM tracker | New file | `src/observability/llm_tracker.py` |
| Request ID middleware | New file | `src/api/middleware/request_id.py` |
| Agent integration | Modified | `src/agents/base.py` |
| Grafana dashboard | New file | `infrastructure/grafana/dashboards/llm-metrics.json` |

### Verification

```bash
# After implementation, verify:
curl http://localhost:8001/metrics | grep llm_

# Should see:
# llm_requests_total{...} 
# llm_tokens_input_total{...}
# llm_request_duration_seconds_bucket{...}
```

---

## Phase 2: Tool/Function Calling (Week 1-2)

**Effort**: 3-5 days  
**Priority**: 🔴 High  
**Dependencies**: Phase 1 (for metrics)

### Objective

Enable agents to execute tools (web search, code execution, API calls).

### Tasks

#### 2.1 Create Tool Base Classes

**File**: `packages/core/src/tools/base.py`

```python
# Implement:
# - ToolParameter (Pydantic model)
# - ToolResult (success, output, error)
# - BaseTool (ABC with execute(), get_schema())
# - to_ollama_format() for native tool calling
```

**Acceptance Criteria**:
- [ ] Clean abstract interface
- [ ] JSON Schema generation for parameters
- [ ] Ollama-compatible tool format output

#### 2.2 Create Tool Registry

**File**: `packages/core/src/tools/registry.py`

```python
# Implement:
# - ToolRegistry singleton
# - register(tool) method
# - get(name) method
# - get_tools_for_agent(tool_names) method
# - Load tools from YAML config
```

**Acceptance Criteria**:
- [ ] Tools registered at startup
- [ ] Lookup by name
- [ ] Filter tools per agent based on YAML config

#### 2.3 Create Tool Executor

**File**: `packages/core/src/tools/executor.py`

```python
# Implement:
# - ToolExecutor class
# - execute_tool(name, params) method
# - Tool call loop (LLM -> tool -> LLM -> ...)
# - Max iterations limit (prevent infinite loops)
# - Error handling and recovery
```

**Acceptance Criteria**:
- [ ] Executes tools based on LLM output
- [ ] Handles tool errors gracefully
- [ ] Max 5 tool iterations per request
- [ ] Metrics for tool executions

#### 2.4 Implement Core Tools

**Directory**: `packages/core/src/tools/implementations/`

| Tool | File | Description |
|------|------|-------------|
| `web_search` | `search.py` | Search the web (via API) |
| `code_execute` | `code.py` | Execute Python code (sandboxed) |
| `file_read` | `files.py` | Read file contents |
| `http_request` | `http.py` | Make HTTP requests |

**Acceptance Criteria**:
- [ ] Each tool has tests
- [ ] Security: code execution is sandboxed
- [ ] Security: HTTP requests have allowlist

#### 2.5 Integrate with Agent

**File**: `packages/core/src/agents/base.py` (modify)

```python
# Modify OllamaAgent to:
# - Accept tools in constructor
# - Pass tools to Ollama API
# - Handle tool_calls in response
# - Execute tools and continue conversation
```

**Acceptance Criteria**:
- [ ] Tools passed to Ollama chat API
- [ ] Tool calls detected in response
- [ ] Tool results fed back to model
- [ ] Final response returned to user

#### 2.6 Update Agent YAML Schema

**File**: `blueprints/devassist/agents/*.yaml` (modify)

```yaml
# Update tool definitions with full schema:
tools:
  - name: web_search
    description: Search the web for information
    parameters:
      - name: query
        type: string
        description: Search query
        required: true
```

**Acceptance Criteria**:
- [ ] All existing tool stubs have full schema
- [ ] Factory loads tools from YAML
- [ ] Tools registered at agent creation

### Deliverables

| Deliverable | Type | Path |
|-------------|------|------|
| Tool base classes | New file | `src/tools/base.py` |
| Tool registry | New file | `src/tools/registry.py` |
| Tool executor | New file | `src/tools/executor.py` |
| Web search tool | New file | `src/tools/implementations/search.py` |
| Code exec tool | New file | `src/tools/implementations/code.py` |
| Agent integration | Modified | `src/agents/base.py` |
| Agent factory | Modified | `src/agents/factory.py` |

### Verification

```python
# Test tool execution:
response = await agent.process_request(
    "Search the web for Python 3.12 new features",
    ...
)
# Should see tool execution in logs and results in response
```

---

## Phase 3: RAG Pipeline (Week 2)

**Effort**: 3-5 days  
**Priority**: 🔴 High  
**Dependencies**: None (can parallel with Phase 2)

### Objective

Implement retrieval-augmented generation using pgvector.

### Tasks

#### 3.1 Create Embeddings Service

**File**: `packages/core/src/rag/embeddings.py`

```python
# Implement:
# - OllamaEmbeddings class
# - embed(text) -> list[float]
# - embed_batch(texts) -> list[list[float]]
# - Caching layer (optional, Redis)
```

**Acceptance Criteria**:
- [ ] Uses configured embedding model (nomic-embed-text)
- [ ] Batch processing for efficiency
- [ ] Error handling for Ollama failures

#### 3.2 Create Vector Store

**File**: `packages/core/src/rag/vector_store.py`

```python
# Implement:
# - Document dataclass (id, content, embedding, metadata)
# - PgVectorStore class
# - add_documents(docs, embeddings)
# - similarity_search(embedding, k, filters)
# - delete_documents(ids)
```

**Acceptance Criteria**:
- [ ] Uses asyncpg for async operations
- [ ] Cosine similarity search
- [ ] Metadata filtering support
- [ ] IVFFlat index for performance

#### 3.3 Create Database Migration

**File**: `packages/core/migrations/001_vector_tables.sql`

```sql
-- Tables:
-- documents (id, content, embedding, metadata, scope, timestamps)
-- Indexes:
-- IVFFlat on embedding column
```

**Acceptance Criteria**:
- [ ] Migration script runnable
- [ ] Index created for fast search
- [ ] Proper vector dimension (768 for nomic)

#### 3.4 Create Document Chunker

**File**: `packages/core/src/rag/chunking.py`

```python
# Implement:
# - TextChunker class
# - chunk_text(text, chunk_size, overlap)
# - chunk_markdown(text) - section-aware
# - chunk_code(text, language) - syntax-aware
```

**Acceptance Criteria**:
- [ ] Configurable chunk size and overlap
- [ ] Preserves semantic boundaries
- [ ] Handles markdown headers
- [ ] Handles code blocks

#### 3.5 Create RAG Retriever

**File**: `packages/core/src/rag/retriever.py`

```python
# Implement:
# - RAGRetriever class
# - retrieve(query, k, knowledge_scope)
# - Combines embedding + vector search
# - Filters by agent's knowledge_scope
```

**Acceptance Criteria**:
- [ ] Respects agent knowledge_scope from YAML
- [ ] Configurable top-k
- [ ] Returns ranked documents

#### 3.6 Create RAG Chain

**File**: `packages/core/src/rag/chain.py`

```python
# Implement:
# - RAGChain class
# - invoke(query, agent) -> augmented response
# - Context building from retrieved docs
# - Prompt template for RAG
```

**Acceptance Criteria**:
- [ ] Retrieves relevant docs
- [ ] Builds context within token limit
- [ ] Augments agent prompt
- [ ] Handles no-results case

#### 3.7 Create Document Ingestion API

**File**: `packages/core/src/api/routes/documents.py`

```python
# Endpoints:
# POST /api/documents - Upload and index document
# GET /api/documents - List documents
# DELETE /api/documents/{id} - Remove document
# POST /api/documents/search - Search documents
```

**Acceptance Criteria**:
- [ ] File upload support (PDF, MD, TXT)
- [ ] Automatic chunking and embedding
- [ ] Scope assignment for filtering

#### 3.8 Integrate with Agent

**File**: `packages/core/src/agents/base.py` (modify)

```python
# Modify OllamaAgent to:
# - Check if knowledge_scope is defined
# - If so, retrieve relevant docs before LLM call
# - Augment system prompt with context
```

**Acceptance Criteria**:
- [ ] RAG automatic for agents with knowledge_scope
- [ ] Context injected into prompt
- [ ] Works with streaming

### Deliverables

| Deliverable | Type | Path |
|-------------|------|------|
| Embeddings service | New file | `src/rag/embeddings.py` |
| Vector store | New file | `src/rag/vector_store.py` |
| Document chunker | New file | `src/rag/chunking.py` |
| RAG retriever | New file | `src/rag/retriever.py` |
| RAG chain | New file | `src/rag/chain.py` |
| Documents API | New file | `src/api/routes/documents.py` |
| DB migration | New file | `migrations/001_vector_tables.sql` |

### Verification

```bash
# 1. Ingest a document
curl -X POST http://localhost:8001/api/documents \
  -F "file=@docs/architecture.md" \
  -F "scope=architecture"

# 2. Ask a question
curl -X POST http://localhost:8001/api/blueprints/devassist/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is our system architecture?"}'

# Should see RAG retrieval in logs and context in response
```

---

## Phase 4: LLM Gateway (Week 3)

**Effort**: 2-3 days  
**Priority**: 🟡 Medium  
**Dependencies**: Phase 1 (metrics)

### Objective

Abstract LLM providers behind a unified gateway with fallback support.

### Tasks

#### 4.1 Define Provider Interface

**File**: `packages/core/src/llm/providers/base.py`

```python
# Implement:
# - LLMConfig dataclass
# - LLMResponse dataclass
# - LLMProvider ABC
#   - chat(messages, tools, stream)
#   - health_check()
#   - get_model_info()
```

**Acceptance Criteria**:
- [ ] Clean provider interface
- [ ] Supports both sync and streaming
- [ ] Health check for circuit breaker

#### 4.2 Implement Ollama Provider

**File**: `packages/core/src/llm/providers/ollama.py`

```python
# Implement:
# - OllamaProvider(LLMProvider)
# - Move existing Ollama code here
# - Add token counting from response
```

**Acceptance Criteria**:
- [ ] Backward compatible
- [ ] Token counts extracted
- [ ] Error handling

#### 4.3 Implement vLLM Provider

**File**: `packages/core/src/llm/providers/vllm.py`

```python
# Implement:
# - VLLMProvider(LLMProvider)
# - Uses OpenAI-compatible API
# - Tensor parallel support config
```

**Acceptance Criteria**:
- [ ] OpenAI SDK for vLLM endpoint
- [ ] Streaming support
- [ ] Ready for production K8s

#### 4.4 Implement OpenAI Provider (Optional)

**File**: `packages/core/src/llm/providers/openai.py`

```python
# Implement:
# - OpenAIProvider(LLMProvider)
# - GPT-4, GPT-3.5-turbo support
# - Native function calling
```

**Acceptance Criteria**:
- [ ] API key from config
- [ ] All models supported
- [ ] Cost tracking accurate

#### 4.5 Create LLM Gateway

**File**: `packages/core/src/llm/gateway.py`

```python
# Implement:
# - LLMGateway class
# - register_provider(name, config)
# - set_fallback_chain(providers)
# - chat() with automatic fallback
# - Integrated metrics tracking
```

**Acceptance Criteria**:
- [ ] Multiple providers registered
- [ ] Fallback on failure
- [ ] Metrics per provider
- [ ] Configurable timeouts

#### 4.6 Update Agent to Use Gateway

**File**: `packages/core/src/agents/base.py` (modify)

```python
# Modify OllamaAgent to:
# - Accept LLMGateway instead of direct client
# - Use gateway.chat() for all LLM calls
# - Remove direct Ollama dependency
```

**Acceptance Criteria**:
- [ ] Agents use gateway
- [ ] Provider configurable per agent
- [ ] Fallback works transparently

### Deliverables

| Deliverable | Type | Path |
|-------------|------|------|
| Provider base | New file | `src/llm/providers/base.py` |
| Ollama provider | New file | `src/llm/providers/ollama.py` |
| vLLM provider | New file | `src/llm/providers/vllm.py` |
| OpenAI provider | New file | `src/llm/providers/openai.py` |
| LLM gateway | New file | `src/llm/gateway.py` |
| Agent refactor | Modified | `src/agents/base.py` |

---

## Phase 5: Resilience & Rate Limiting (Week 3)

**Effort**: 2-3 days  
**Priority**: 🟡 Medium  
**Dependencies**: Phase 4 (gateway)

### Tasks

#### 5.1 Implement Circuit Breaker

**File**: `packages/core/src/llm/resilience.py`

```python
# Implement:
# - CircuitBreakerState dataclass
# - CircuitBreaker class
#   - is_available(provider)
#   - record_success(provider)
#   - record_failure(provider)
# - States: closed, open, half-open
```

**Acceptance Criteria**:
- [ ] Opens after N failures
- [ ] Half-open after timeout
- [ ] Closes on success
- [ ] Metrics for state changes

#### 5.2 Implement Retry with Backoff

**File**: `packages/core/src/llm/resilience.py` (add)

```python
# Implement:
# - retry_with_backoff() decorator
# - Exponential backoff
# - Configurable max retries
# - Jitter to prevent thundering herd
```

**Acceptance Criteria**:
- [ ] Configurable retries (default 3)
- [ ] Exponential backoff with jitter
- [ ] Max delay cap
- [ ] Retryable vs non-retryable errors

#### 5.3 Integrate Rate Limiter

**File**: `packages/core/src/api/middleware/rate_limit.py`

```python
# Implement:
# - RateLimitMiddleware
# - Uses existing cache/rate_limiter.py
# - Per-user and per-IP limits
# - Returns 429 with headers
```

**Acceptance Criteria**:
- [ ] Middleware integrated in app.py
- [ ] Per-user limits (100/min default)
- [ ] Per-IP limits for anonymous
- [ ] X-RateLimit-* headers

#### 5.4 Add Timeout Handling

**File**: `packages/core/src/llm/gateway.py` (modify)

```python
# Add:
# - Per-request timeout
# - Per-provider timeout config
# - Graceful timeout handling
```

**Acceptance Criteria**:
- [ ] Configurable timeouts
- [ ] Clean cancellation
- [ ] Timeout metrics

### Deliverables

| Deliverable | Type | Path |
|-------------|------|------|
| Resilience utilities | New file | `src/llm/resilience.py` |
| Rate limit middleware | New file | `src/api/middleware/rate_limit.py` |
| Gateway updates | Modified | `src/llm/gateway.py` |
| App middleware | Modified | `src/api/app.py` |

---

## Phase 6: Prompt Management (Week 4)

**Effort**: 1-2 days  
**Priority**: 🟡 Medium  
**Dependencies**: None

### Tasks

#### 6.1 Create Prompt Schema

**File**: `packages/core/src/prompts/models.py`

```python
# Implement:
# - PromptVersion (version, content, variables, created_at)
# - PromptTemplate (name, description, versions, current)
# - Variable substitution logic
```

#### 6.2 Create Prompt Manager

**File**: `packages/core/src/prompts/manager.py`

```python
# Implement:
# - PromptManager class
# - Load from YAML directory
# - get(name, version, **variables)
# - list_prompts()
# - Hot reload support
```

#### 6.3 Migrate Existing Prompts

**Directory**: `packages/core/prompts/`

```
prompts/
├── routing.yaml          # Supervisor routing
├── supervisor.yaml       # Direct response
└── agents/
    ├── systemarchitect.yaml
    ├── kubernetes.yaml
    └── python.yaml
```

#### 6.4 Integrate with Orchestrator

**File**: `packages/core/src/orchestrator/` (modify)

```python
# Update to use PromptManager instead of hardcoded strings
```

### Deliverables

| Deliverable | Type | Path |
|-------------|------|------|
| Prompt models | New file | `src/prompts/models.py` |
| Prompt manager | New file | `src/prompts/manager.py` |
| Prompt YAML files | New directory | `prompts/` |
| Orchestrator updates | Modified | `src/orchestrator/` |

---

## Phase 7: Production Hardening (Week 4)

**Effort**: 2-3 days  
**Priority**: 🟡 Medium  
**Dependencies**: All previous phases

### Tasks

#### 7.1 Security Audit

- [ ] Audit tool execution (sandboxing)
- [ ] Audit HTTP request tool (allowlist)
- [ ] Audit file access (path traversal)
- [ ] Audit prompt injection risks
- [ ] Add input validation

#### 7.2 Error Handling Review

- [ ] Consistent error response format
- [ ] Error codes documentation
- [ ] Sensitive info not leaked in errors
- [ ] Graceful degradation

#### 7.3 Configuration Validation

- [ ] Startup config validation
- [ ] Required env vars check
- [ ] Health check dependencies
- [ ] Fail-fast on misconfiguration

#### 7.4 Documentation

- [ ] API documentation (OpenAPI)
- [ ] Deployment guide
- [ ] Runbook for operations
- [ ] Architecture decision records

#### 7.5 Load Testing

- [ ] k6 or locust scripts
- [ ] Baseline performance metrics
- [ ] Identify bottlenecks
- [ ] Document capacity limits

### Deliverables

| Deliverable | Type | Path |
|-------------|------|------|
| Security fixes | Various | Various |
| Error handling | Modified | Various |
| Load test scripts | New | `tests/load/` |
| Runbook | New | `docs/runbook.md` |

---

## File Structure

After all phases, new files created:

```
packages/core/src/
├── observability/                 # Phase 1
│   ├── __init__.py
│   ├── metrics.py                # Prometheus metrics
│   └── llm_tracker.py            # Usage tracking
│
├── tools/                         # Phase 2
│   ├── __init__.py
│   ├── base.py                   # BaseTool ABC
│   ├── registry.py               # Tool registry
│   ├── executor.py               # Execution loop
│   └── implementations/
│       ├── __init__.py
│       ├── search.py             # Web search
│       ├── code.py               # Code execution
│       ├── files.py              # File operations
│       └── http.py               # HTTP requests
│
├── rag/                           # Phase 3
│   ├── __init__.py
│   ├── embeddings.py             # Ollama embeddings
│   ├── vector_store.py           # pgvector store
│   ├── chunking.py               # Document chunking
│   ├── retriever.py              # RAG retriever
│   └── chain.py                  # RAG chain
│
├── llm/                           # Phase 4
│   ├── __init__.py
│   ├── gateway.py                # LLM gateway
│   ├── resilience.py             # Circuit breaker, retry
│   └── providers/
│       ├── __init__.py
│       ├── base.py               # Provider ABC
│       ├── ollama.py             # Ollama provider
│       ├── vllm.py               # vLLM provider
│       └── openai.py             # OpenAI provider
│
├── prompts/                       # Phase 6
│   ├── __init__.py
│   ├── models.py                 # Pydantic models
│   └── manager.py                # Prompt manager
│
├── api/
│   ├── middleware/                # Phase 5
│   │   ├── __init__.py
│   │   ├── request_id.py         # Request tracing
│   │   └── rate_limit.py         # Rate limiting
│   └── routes/
│       └── documents.py          # Phase 3: RAG API
│
└── migrations/                    # Phase 3
    └── 001_vector_tables.sql

packages/core/prompts/             # Phase 6: YAML prompts
├── routing.yaml
├── supervisor.yaml
└── agents/
    └── *.yaml

infrastructure/grafana/            # Phase 1
└── dashboards/
    └── llm-metrics.json

tests/load/                        # Phase 7
├── k6/
│   └── chat_load_test.js
└── README.md
```

---

## Migration Checklist

### Pre-Implementation

- [ ] Review and approve this plan
- [ ] Set up feature branch strategy
- [ ] Ensure test coverage baseline
- [ ] Set up CI for new modules

### Phase 1 Complete

- [ ] Metrics visible in Prometheus
- [ ] Grafana dashboard deployed
- [ ] Request IDs in all logs
- [ ] No performance regression

### Phase 2 Complete

- [ ] At least 2 tools working
- [ ] Tool execution logged
- [ ] Security review passed
- [ ] Agent YAML updated

### Phase 3 Complete

- [ ] Documents can be ingested
- [ ] RAG retrieval working
- [ ] Agent knowledge_scope respected
- [ ] Migration script tested

### Phase 4 Complete

- [ ] Gateway abstraction working
- [ ] Ollama provider migrated
- [ ] Fallback tested
- [ ] No breaking changes

### Phase 5 Complete

- [ ] Rate limiting active
- [ ] Circuit breaker tested
- [ ] Retry logic verified
- [ ] 429 responses correct

### Phase 6 Complete

- [ ] All prompts in YAML
- [ ] Version history preserved
- [ ] Hot reload working
- [ ] No hardcoded prompts

### Phase 7 Complete

- [ ] Security audit passed
- [ ] Load test baseline established
- [ ] Documentation complete
- [ ] Runbook reviewed

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Latency P95 | < 2s (non-streaming) | Prometheus |
| TTFT P95 | < 500ms | Prometheus |
| Error Rate | < 1% | Prometheus |
| Tool Success Rate | > 95% | Prometheus |
| RAG Relevance | > 80% (manual eval) | Periodic review |
| Uptime | > 99.5% | Alerting |

---

*Document Version: 1.0*  
*Created: February 2026*  
*Status: Planning*
