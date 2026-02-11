# Enterprise ML Platform Architecture

A comprehensive guide to production-grade ML/LLM platform architecture patterns used by industry leaders. This document covers infrastructure, orchestration, and best practices for Kubernetes-native deployments.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Model Serving Layer](#model-serving-layer)
3. [Application & Orchestration Layer](#application--orchestration-layer)
4. [Multi-Agent Patterns](#multi-agent-patterns)
5. [Data & Vector Storage](#data--vector-storage)
6. [Observability & Monitoring](#observability--monitoring)
7. [Industry Adoption](#industry-adoption)
8. [Our Architecture](#our-architecture)
9. [Migration Paths](#migration-paths)

---

## Architecture Overview

### Standard Enterprise LLM Platform

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INGRESS LAYER                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Istio / Kong / NGINX  │  Rate Limiting  │  Auth (OAuth2/OIDC)          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                  │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Chat API   │  │  Agent API   │  │  RAG API     │  │  Admin API   │    │
│  │   (FastAPI)  │  │  (FastAPI)   │  │  (FastAPI)   │  │  (FastAPI)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                 │                 │                 │             │
│         └─────────────────┼─────────────────┼─────────────────┘             │
│                           ▼                 ▼                               │
│              ┌─────────────────────────────────────────┐                    │
│              │         LLM Gateway / Router            │                    │
│              │  • Model routing & load balancing       │                    │
│              │  • Rate limiting per user/org           │                    │
│              │  • Cost tracking & quotas               │                    │
│              │  • Fallback & retry logic               │                    │
│              └─────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MODEL SERVING LAYER                                 │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │     vLLM        │  │     vLLM        │  │   Embeddings    │             │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │             │
│  │  │ LLaMA 70B │  │  │  │ Mixtral   │  │  │  │ BGE-Large │  │             │
│  │  │  (GPU×4)  │  │  │  │  (GPU×2)  │  │  │  │  (GPU×1)  │  │             │
│  │  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Alternative: Managed APIs (OpenAI, Anthropic, AWS Bedrock, Azure)      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                        │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  PostgreSQL  │  │    Redis     │  │   Vector DB  │  │  Object      │    │
│  │  + pgvector  │  │   Cluster    │  │  (pgvector/  │  │  Storage     │    │
│  │              │  │   (Cache)    │  │   Pinecone)  │  │  (S3/MinIO)  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐                                         │
│  │  ScyllaDB/   │  │  Message     │                                         │
│  │  DynamoDB    │  │  Queue       │                                         │
│  │  (Sessions)  │  │  (Kafka/SQS) │                                         │
│  └──────────────┘  └──────────────┘                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY LAYER                                   │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Prometheus  │  │   Grafana    │  │   Jaeger/    │  │  LangSmith/  │    │
│  │   Metrics    │  │  Dashboards  │  │   Tempo      │  │  Langfuse    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Principles

| Principle | Description |
|-----------|-------------|
| **Separation of Concerns** | Model serving is decoupled from application logic |
| **Horizontal Scalability** | Each layer scales independently |
| **Provider Agnostic** | LLM Gateway abstracts model providers |
| **Observable** | Every layer emits metrics, logs, and traces |
| **Cost Aware** | Token usage tracked and rate-limited |

---

## Model Serving Layer

### Comparison of Serving Solutions

| Solution | Best For | Throughput | K8s Native | GPU Optimization |
|----------|----------|------------|------------|------------------|
| **vLLM** | Production self-hosted | ⭐⭐⭐⭐⭐ | ✅ | PagedAttention, continuous batching |
| **TGI** (HuggingFace) | HF ecosystem | ⭐⭐⭐⭐ | ✅ | Flash Attention, quantization |
| **Ray Serve** | Multi-model, complex pipelines | ⭐⭐⭐⭐ | ✅ | Flexible GPU allocation |
| **Ollama** | Development, edge, Mac | ⭐⭐⭐ | ⚠️ | Apple Silicon optimized |
| **KServe** | Standardized inference | ⭐⭐⭐ | ✅⭐ | V2 inference protocol |
| **Triton** (NVIDIA) | Maximum GPU efficiency | ⭐⭐⭐⭐⭐ | ✅ | NVIDIA ecosystem |

### vLLM (Recommended for Production)

```yaml
# kubernetes/vllm-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-llama-70b
  namespace: ml-serving
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vllm-llama-70b
  template:
    metadata:
      labels:
        app: vllm-llama-70b
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
          - --model=meta-llama/Llama-3-70B-Instruct
          - --tensor-parallel-size=4
          - --max-model-len=8192
          - --gpu-memory-utilization=0.9
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 4
            memory: "160Gi"
          requests:
            nvidia.com/gpu: 4
            memory: "160Gi"
        env:
        - name: HUGGING_FACE_HUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
      nodeSelector:
        nvidia.com/gpu.product: "NVIDIA-A100-SXM4-80GB"
      tolerations:
      - key: "nvidia.com/gpu"
        operator: "Exists"
        effect: "NoSchedule"
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-llama-70b
  namespace: ml-serving
spec:
  selector:
    app: vllm-llama-70b
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### When to Use What

| Scenario | Recommended Solution |
|----------|---------------------|
| Development on Mac | Ollama |
| Production with GPUs | vLLM or TGI |
| Multi-cloud / hybrid | LiteLLM Gateway + vLLM |
| Regulated industry | Self-hosted vLLM + air-gapped |
| Startup / cost-sensitive | Managed APIs (OpenAI, Anthropic) |
| Maximum throughput | vLLM with continuous batching |

---

## Application & Orchestration Layer

### Framework Comparison

| Framework | Strengths | Weaknesses | Production Use |
|-----------|-----------|------------|----------------|
| **Direct SDK** | Full control, minimal deps | More code to write | ⭐⭐⭐⭐⭐ Most common |
| **LangChain** | Rich ecosystem, quick prototyping | Abstraction overhead, churn | ⭐⭐⭐ Prototyping |
| **LangGraph** | Stateful workflows, cycles | Newer, learning curve | ⭐⭐⭐⭐ Growing |
| **LlamaIndex** | RAG-focused, great loaders | Less flexible for agents | ⭐⭐⭐⭐ RAG apps |
| **Semantic Kernel** | Enterprise .NET/Java | Microsoft ecosystem lock-in | ⭐⭐⭐ Enterprise |
| **Haystack** | Production-ready, modular | Smaller community | ⭐⭐⭐ Regulated |

### Recommended: Thin Orchestration Layer

Most enterprises use a thin custom layer over direct SDKs:

```python
# src/llm/gateway.py
"""
LLM Gateway - Thin abstraction over multiple providers.
This is what enterprises actually build.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterable

import httpx
from ollama import AsyncClient as OllamaClient
from openai import AsyncOpenAI


@dataclass
class LLMConfig:
    provider: str  # "ollama", "openai", "anthropic", "vllm"
    model: str
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096


class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self, 
        messages: list[dict], 
        stream: bool = False
    ) -> str | AsyncIterable[str]:
        pass


class OllamaProvider(LLMProvider):
    def __init__(self, config: LLMConfig):
        self.client = OllamaClient(host=config.base_url)
        self.model = config.model
        self.config = config

    async def chat(self, messages: list[dict], stream: bool = False):
        response = await self.client.chat(
            model=self.model,
            messages=messages,
            stream=stream,
            options={
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        )
        
        if stream:
            async def generate():
                async for chunk in response:
                    yield chunk["message"]["content"]
            return generate()
        
        return response["message"]["content"]


class VLLMProvider(LLMProvider):
    """vLLM uses OpenAI-compatible API."""
    
    def __init__(self, config: LLMConfig):
        self.client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "dummy",  # vLLM doesn't require key
        )
        self.model = config.model
        self.config = config

    async def chat(self, messages: list[dict], stream: bool = False):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=stream,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        
        if stream:
            async def generate():
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            return generate()
        
        return response.choices[0].message.content


class LLMGateway:
    """
    Unified gateway supporting multiple providers.
    Handles routing, fallbacks, and cost tracking.
    """
    
    def __init__(self):
        self.providers: dict[str, LLMProvider] = {}
        self.fallback_chain: list[str] = []
    
    def register(self, name: str, config: LLMConfig):
        provider_map = {
            "ollama": OllamaProvider,
            "vllm": VLLMProvider,
            # Add more providers as needed
        }
        provider_class = provider_map[config.provider]
        self.providers[name] = provider_class(config)
    
    def set_fallback_chain(self, chain: list[str]):
        self.fallback_chain = chain
    
    async def chat(
        self, 
        messages: list[dict],
        provider: str | None = None,
        stream: bool = False,
    ):
        """Route to appropriate provider with fallback."""
        providers_to_try = [provider] if provider else self.fallback_chain
        
        for provider_name in providers_to_try:
            try:
                return await self.providers[provider_name].chat(messages, stream)
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        raise RuntimeError("All providers failed")
```

### LiteLLM (Alternative Gateway)

For multi-provider setups, LiteLLM is a popular choice:

```python
# Using LiteLLM for unified API
from litellm import acompletion

# Works with 100+ providers
response = await acompletion(
    model="ollama/qwen2.5:32b",  # or "gpt-4", "claude-3", etc.
    messages=[{"role": "user", "content": "Hello"}],
)
```

---

## Multi-Agent Patterns

### Pattern 1: Supervisor Router (Current Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    Supervisor Agent                          │
│           (Routes queries to specialists)                    │
└─────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Python     │  │  Kubernetes  │  │   AWS        │
│   Expert     │  │   Expert     │  │   Expert     │
└──────────────┘  └──────────────┘  └──────────────┘
```

**Implementation**: agent-squad (AWS Labs), custom classifier

```python
# Supervisor pattern with agent-squad
from agent_squad.orchestrator import AgentSquad
from agent_squad.classifiers import Classifier

class SupervisorClassifier(Classifier):
    async def process_request(self, input_text, chat_history):
        # LLM-based routing decision
        selected = await self._route_query(input_text)
        return ClassifierResult(selected_agent=selected)

squad = AgentSquad(classifier=SupervisorClassifier())
squad.add_agent(python_expert)
squad.add_agent(k8s_expert)
```

### Pattern 2: Hierarchical Multi-Agent

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator                              │
└─────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Planning   │  │  Execution   │  │   Review     │
│   Agent      │  │   Agent      │  │   Agent      │
└──────────────┘  └──────────────┘  └──────────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │ Tool A │ │ Tool B │ │ Tool C │
         └────────┘ └────────┘ └────────┘
```

**Implementation**: LangGraph, custom state machine

### Pattern 3: Collaborative Agents (Peer-to-Peer)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Research   │◄───►│   Writer     │◄───►│   Critic     │
│   Agent      │     │   Agent      │     │   Agent      │
└──────────────┘     └──────────────┘     └──────────────┘
       ▲                    ▲                    ▲
       └────────────────────┼────────────────────┘
                            │
                    Shared State/Memory
```

**Implementation**: AutoGen, CrewAI

### Production Framework Comparison

| Framework | Pattern | Maturity | Use Case |
|-----------|---------|----------|----------|
| **agent-squad** | Supervisor | Production | AWS-aligned, Bedrock patterns |
| **LangGraph** | Any | Production | Complex stateful workflows |
| **AutoGen** | Collaborative | Emerging | Research, autonomous agents |
| **CrewAI** | Role-based | Emerging | Simple multi-agent tasks |
| **Custom** | Any | Production | Maximum control |

---

## Data & Vector Storage

### Session/Chat Storage

| Solution | Scale | Latency | Use Case |
|----------|-------|---------|----------|
| **DynamoDB/ScyllaDB** | Unlimited | <10ms | Chat history (Discord-scale) |
| **PostgreSQL** | Large | <20ms | Structured data + vectors |
| **Redis** | Medium | <1ms | Session cache, rate limiting |
| **MongoDB** | Large | <15ms | Document-oriented |

### Vector Storage

| Solution | Scale | Managed | Self-hosted |
|----------|-------|---------|-------------|
| **pgvector** | 10M vectors | RDS, Supabase | ✅ Easy |
| **Pinecone** | Billions | ✅ Fully | ❌ |
| **Weaviate** | 100M+ | ✅ | ✅ |
| **Qdrant** | 100M+ | ✅ | ✅ |
| **Milvus** | Billions | Zilliz | ✅ |
| **Chroma** | 1M | ❌ | ✅ Dev only |

### Recommended Stack

```yaml
# For most use cases:
chat_storage: ScyllaDB (DynamoDB-compatible) or PostgreSQL
vector_storage: pgvector (embedded in PostgreSQL)
cache: Redis Cluster
object_storage: S3/MinIO (for documents, artifacts)
```

---

## Observability & Monitoring

### LLM-Specific Observability

| Tool | Type | Strengths |
|------|------|-----------|
| **Langfuse** | LLM Observability | Open-source, traces, evals |
| **LangSmith** | LLM Observability | LangChain native, powerful |
| **Helicone** | LLM Gateway + Observability | Proxy-based, caching |
| **Weights & Biases** | ML Platform | Experiment tracking |
| **Arize Phoenix** | LLM Observability | Open-source, evals |

### Metrics to Track

```python
# Essential LLM metrics
METRICS = {
    # Latency
    "llm_request_duration_seconds": Histogram,
    "llm_time_to_first_token_seconds": Histogram,
    
    # Throughput
    "llm_requests_total": Counter,
    "llm_tokens_total": Counter,  # input + output
    
    # Cost
    "llm_cost_dollars": Counter,
    
    # Quality
    "llm_errors_total": Counter,
    "llm_retries_total": Counter,
    
    # Per-model breakdown
    "llm_requests_by_model": Counter,
    "llm_tokens_by_model": Counter,
}
```

### Grafana Dashboard Example

```json
{
  "panels": [
    {
      "title": "LLM Request Latency (p50, p95, p99)",
      "expr": "histogram_quantile(0.95, llm_request_duration_seconds_bucket)"
    },
    {
      "title": "Token Throughput",
      "expr": "rate(llm_tokens_total[5m])"
    },
    {
      "title": "Cost per Hour",
      "expr": "increase(llm_cost_dollars[1h])"
    },
    {
      "title": "Error Rate",
      "expr": "rate(llm_errors_total[5m]) / rate(llm_requests_total[5m])"
    }
  ]
}
```

---

## Industry Adoption

### What Large Companies Actually Use

| Company | LLM Serving | Orchestration | Vector DB | Notes |
|---------|-------------|---------------|-----------|-------|
| **Uber** | Ray Serve | Custom | Milvus | Heavy Ray investment |
| **Airbnb** | OpenAI API | Custom | Pinecone | Managed services |
| **Stripe** | Anthropic/OpenAI | Custom | pgvector | Direct integration |
| **LinkedIn** | Azure OpenAI | Java custom | Internal | Enterprise Java |
| **Shopify** | Ray + Claude | Custom | Pinecone | Sidekick product |
| **Notion** | OpenAI | Custom | pgvector | Integrated AI |
| **Discord** | - | - | ScyllaDB | Chat storage reference |
| **Netflix** | Custom | Custom | Internal | ML platform team |

### Key Insights

1. **Almost no one uses LangChain in core production** - it's used for prototyping
2. **Direct SDK + custom orchestration dominates** - maximum control, minimum deps
3. **Managed APIs are common** - most use OpenAI/Anthropic/Azure, not self-hosted
4. **Vector DB varies** - pgvector for simplicity, Pinecone/Milvus for scale
5. **Observability is critical** - all track latency, tokens, costs

---

## Our Architecture

### Current Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Frontend                          │
│                    (shadcn/ui + Tailwind)                    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Supervisor Orchestrator (agent-squad)                   ││
│  │  ├─ OllamaSupervisorClassifier (routing)                ││
│  │  ├─ SystemArchitect Agent                               ││
│  │  ├─ KubernetesExpert Agent                              ││
│  │  ├─ PythonExpert Agent                                  ││
│  │  └─ ... more specialized agents                         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Model Serving                             │
│                    Ollama (qwen2.5:32b)                      │
│                    Mac Studio M4 Max                         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  ScyllaDB    │  │    Redis     │  │  PostgreSQL  │       │
│  │  (Sessions)  │  │   (Cache)    │  │  + pgvector  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### Alignment with Industry Standards

| Component | Our Choice | Industry Standard | Status |
|-----------|------------|-------------------|--------|
| Frontend | Next.js + shadcn | ✅ Standard | Aligned |
| API | FastAPI | ✅ Standard | Aligned |
| Orchestration | agent-squad + custom | ✅ Custom is standard | Aligned |
| LLM Serving | Ollama | ⚠️ Dev only (vLLM for prod) | Dev OK |
| Chat Storage | ScyllaDB | ✅ Discord-scale proven | Aligned |
| Vector Storage | pgvector (planned) | ✅ Standard | Planned |
| Cache | Redis | ✅ Standard | Aligned |

---

## Migration Paths

### Path 1: Scale LLM Serving (When Needed)

```
Current: Ollama (Mac Studio)
    │
    ▼ (When scaling to K8s with GPUs)
Target: vLLM + GPU Nodes
```

**Trigger**: Need for multiple GPUs, higher throughput, or production K8s deployment.

### Path 2: Add RAG (Near-term)

```
Current: pgvector (configured, not used)
    │
    ▼ (Implement directly, no LangChain)
Target: pgvector + nomic-embed-text embeddings
```

**Implementation**:
```python
# Direct pgvector implementation
async def search_knowledge(query: str, limit: int = 5):
    embedding = await ollama.embed(model="nomic-embed-text", text=query)
    
    results = await db.execute("""
        SELECT content, metadata, 
               embedding <=> $1 AS distance
        FROM documents
        ORDER BY embedding <=> $1
        LIMIT $2
    """, embedding, limit)
    
    return results
```

### Path 3: Complex Agent Workflows (Future)

```
Current: agent-squad supervisor pattern
    │
    ▼ (If needing cycles, human-in-loop, complex state)
Target: LangGraph for specific workflows
```

**Trigger**: Need for agent loops, human approval steps, or complex state machines.

### Path 4: Multi-Provider (Future)

```
Current: Ollama only
    │
    ▼ (When needing fallbacks or multiple providers)
Target: LiteLLM Gateway + multiple backends
```

---

## Summary

### Do's ✅

- Use **direct SDKs** for LLM calls (cleaner, more control)
- Build **thin custom orchestration** (what enterprises do)
- Choose **vLLM** for production GPU serving
- Use **pgvector** for vector storage (simple, integrated)
- Track **latency, tokens, costs** (essential metrics)
- Keep **observability first** (Langfuse/custom)

### Don'ts ❌

- Don't use **LangChain for production multi-agent** (use custom/LangGraph)
- Don't use **Ollama for production scale** (use vLLM/TGI)
- Don't over-engineer **before you need scale**
- Don't ignore **cost tracking** (LLM costs add up fast)
- Don't skip **prompt versioning** (critical for debugging)

### Our Current Status

| Aspect | Status | Action |
|--------|--------|--------|
| Architecture | ✅ Industry-aligned | Maintain |
| Model Serving | ⚠️ Dev-only (Ollama) | OK for now, vLLM for prod |
| Orchestration | ✅ Custom + agent-squad | Maintain |
| RAG | 🔲 Not implemented | Next priority |
| Tool Calling | 🔲 Stubbed | Implement with native Ollama |
| Observability | 🔲 Basic | Add Langfuse or custom |

---

*Document Version: 1.0*  
*Last Updated: February 2026*  
*Applies to: Agentic AI Platform*
