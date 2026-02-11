# Agent Development Guide

This guide provides coding standards and patterns for agentic AI systems working on this codebase.

## Project Overview

**Agentic AI Platform** - A scalable multi-agent AI platform using the Module-Blueprint pattern, powered by Ollama and agent-squad (awslabs). This is a **monorepo** with Python backend (FastAPI) and Next.js frontend (shadcn/ui).

**Tech Stack:**
- **Backend:** Python 3.11+, FastAPI, agent-squad, Ollama, asyncio
- **Frontend:** Next.js 14 App Router, TypeScript, shadcn/ui, Tailwind CSS
- **Infrastructure:** LocalStack, Terraform, DynamoDB, S3, pgvector
- **Package Manager:** pnpm (Node.js), pip with venv (Python)

## Build & Development Commands

### Root Level (Monorepo)

```bash
# Setup (one-time)
make setup                  # Install all dependencies + create Python venv

# Development
make dev                    # Start both backend (8000) and frontend (3000)
make dev-backend            # Backend only (uses venv)
make dev-frontend           # Frontend only

# Ollama Management
make ollama-status          # Check Ollama status and models
make ollama-start           # Start Ollama server
make ollama-pull            # Pull required models (qwen2.5:32b, nomic-embed-text)
make ollama-test            # Test connection

# Quality & Testing
make test                   # Run all tests (uses venv)
make lint                   # Run all linters
make format                 # Format all code
make check                  # Run all checks (lint + type + test)

# Cleanup
make clean                  # Clean build artifacts
make clean-all              # Deep clean (includes node_modules)
```

### Backend (packages/core)

**IMPORTANT:** All Python commands run inside the virtual environment at `./venv`

```bash
# Development
cd packages/core
make dev                    # Start FastAPI server on port 8000

# Testing
make test                   # Run all tests with pytest
make test-cov               # Run tests with coverage report
pytest tests/test_agents/test_factory.py -v    # Run single test file
pytest tests/test_agents/test_factory.py::test_load_agent_config -v  # Run single test

# Code Quality
make lint                   # Run ruff linter
make lint-fix               # Auto-fix linting issues
make format                 # Format code with ruff
make type-check             # Run mypy type checking
make check                  # Run all checks (lint + type + test)

# Manual venv activation (if needed)
source ../../venv/bin/activate   # From packages/core/
```

### Frontend (packages/ui)

```bash
cd packages/ui

# Development
make dev                    # Start Next.js dev server (port 3000)
# OR
pnpm dev

# Code Quality
make lint                   # Run ESLint
pnpm lint                   # Alternative

make format                 # Format with Prettier
pnpm format                 # Alternative

# Build
pnpm build                  # Production build
pnpm start                  # Start production server
```

## Python Coding Standards

### Style & Formatting

- **Line length:** 100 characters
- **Linter:** ruff with E, F, I, N, W, UP, B, C4, SIM rules
- **Type checker:** mypy in strict mode
- **Python version:** 3.11+ (use modern features)
- **Imports:** Sorted with isort (built into ruff)
  - Standard library first
  - Third-party packages second
  - Local imports last
  - From imports after regular imports

### Import Style

```python
# Standard library
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterable, Dict, List, Optional

# Third-party
import structlog
import yaml
from agent_squad.agents import Agent, AgentOptions
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# Local
from .base import AgentConfig, OllamaAgent
from ..config import get_settings
```

### Type Annotations

**REQUIRED everywhere:** Use full type hints for all functions, methods, and class attributes.

```python
# Good
async def process_request(
    self,
    input_text: str,
    user_id: str,
    session_id: str,
    chat_history: List[ConversationMessage],
    additional_params: Optional[Dict[str, str]] = None,
) -> ConversationMessage | AsyncIterable[Any]:
    """Process user request."""
    pass

# Bad - missing types
async def process_request(self, input_text, user_id, session_id, chat_history, additional_params=None):
    pass
```

### Async Patterns

**Use `async/await` throughout** - This is an async-first codebase.

```python
# Async client initialization
from ollama import AsyncClient

class OllamaAgent(Agent):
    def __init__(self, options: OllamaAgentOptions):
        super().__init__(options)
        self._client = AsyncClient()
    
    async def process_request(self, ...) -> ConversationMessage | AsyncIterable[Any]:
        # Non-blocking async calls
        response = await self._client.chat(...)
        async for chunk in response:
            yield chunk
```

### Logging

Use `structlog` for structured logging with context:

```python
import structlog

logger = structlog.get_logger()

class MyClass:
    def __init__(self):
        # Bind logger with context
        self._logger = logger.bind(component="MyClass")
    
    async def my_method(self, user_id: str):
        self._logger.info(
            "processing_request",
            user_id=user_id,
            input_length=len(input_text),
        )
        
        try:
            result = await do_something()
        except Exception as e:
            self._logger.error("operation_failed", error=str(e))
            raise
```

### Docstrings

Use Google-style docstrings:

```python
def load_agent_config(yaml_path: Path) -> AgentConfig:
    """Load agent configuration from YAML file.
    
    Args:
        yaml_path: Path to the agent YAML file
        
    Returns:
        Configured AgentConfig instance
        
    Raises:
        FileNotFoundError: If YAML file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    pass
```

### Error Handling

```python
from fastapi import HTTPException, status

# Use appropriate HTTP status codes
if not agent_exists:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Agent '{agent_name}' not found"
    )

# Log errors before raising
try:
    result = await risky_operation()
except ValueError as e:
    logger.error("validation_error", error=str(e))
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
```

### Testing with pytest

```python
import pytest
from pathlib import Path

# Use fixtures
@pytest.fixture
def sample_agent_config():
    return AgentConfig(
        name="TestAgent",
        agent_id="test-agent",
        description="Test agent",
    )

# Async tests
@pytest.mark.asyncio
async def test_process_request(sample_agent_config):
    agent = OllamaAgent(OllamaAgentOptions(**sample_agent_config.__dict__))
    result = await agent.process_request(...)
    assert result is not None

# Parametrize for multiple cases
@pytest.mark.parametrize("input,expected", [
    ("hello", "greeting"),
    ("bye", "farewell"),
])
def test_classify(input, expected):
    assert classify(input) == expected
```

## TypeScript/React Coding Standards

### Style & Formatting

- **Linter:** ESLint with next config
- **Formatter:** Prettier
- **TypeScript:** Strict mode enabled
- **Path alias:** `@/` maps to project root

### Component Structure

Use **functional components with hooks** (App Router pattern):

```typescript
'use client';  // For client components

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatPage() {
  const params = useParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  useEffect(() => {
    // Side effects here
  }, [dependency]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Handler logic
  };
  
  return (
    <div className="flex flex-col h-screen">
      {/* JSX */}
    </div>
  );
}
```

### Type Definitions

Define interfaces for all props and data structures:

```typescript
interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    // Component logic
  }
);
Button.displayName = 'Button';
```

### API Calls

```typescript
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Streaming responses
const response = await fetch(`${apiUrl}/api/blueprints/${blueprint}/chat/stream`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message, session_id, stream: true }),
});

const reader = response.body?.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  // Process SSE chunks
}
```

### Styling (Tailwind + shadcn/ui)

- Use **Tailwind utility classes** for styling
- Use **shadcn/ui components** from `@/components/ui`
- Use `cn()` utility from `@/lib/utils` for conditional classes

```typescript
import { cn } from '@/lib/utils';

<div className={cn(
  "max-w-[80%] rounded-lg px-4 py-2",
  message.role === 'user' 
    ? 'bg-primary text-primary-foreground'
    : 'bg-muted'
)}>
  {message.content}
</div>
```

## Architectural Patterns

### 1. Module-Blueprint Pattern

**Modules** (terraform/modules/): Reusable infrastructure (DynamoDB, S3, pgvector, observability)
**Blueprints** (blueprints/): Complete applications with agents, terraform, and knowledge bases

```
blueprints/devassist/
├── agents/              # YAML agent definitions
│   ├── kubernetes.yaml
│   └── python.yaml
├── terraform/           # Blueprint-specific infra
├── knowledge/           # RAG documents
└── config.yaml          # Blueprint metadata
```

### 2. Agent Factory Pattern

Load agents dynamically from YAML:

```python
from pathlib import Path
from .factory import load_agent_from_yaml, load_blueprint_agents

# Single agent
agent = load_agent_from_yaml(Path("agents/python.yaml"))

# All agents in blueprint
agents = load_blueprint_agents(Path("blueprints/devassist"))
```

### 3. Supervisor Orchestration

Route user queries to appropriate specialized agents:

```python
class SupervisorOrchestrator:
    """Routes requests to specialized agents."""
    
    async def process(
        self,
        user_message: str,
        agents: Dict[str, OllamaAgent],
    ) -> AsyncIterable[str]:
        # 1. Classify intent
        # 2. Route to best agent
        # 3. Stream response
        pass
```

### 4. Clean Architecture (Backend)

The backend follows a layered architecture with clear separation of concerns:

```
packages/core/src/
├── api/                      # Presentation Layer
│   ├── app.py               # FastAPI application factory
│   ├── dependencies/        # Dependency injection
│   │   ├── auth.py         # User authentication (CurrentUser)
│   │   └── registry.py     # Agent registry injection
│   └── routes/             # HTTP route handlers
│       ├── agents.py
│       ├── blueprints.py
│       ├── chat.py
│       └── sessions.py
│
├── schemas/                  # Data Transfer Objects (DTOs)
│   ├── common.py           # StreamChunk, QueryResult, ToolInfo
│   ├── chat.py             # ChatRequest, ChatResponse
│   ├── sessions.py         # Session-related models
│   ├── agents.py           # AgentInfo, AgentConfig
│   └── blueprints.py       # BlueprintInfo
│
├── services/                 # Business Logic Layer
│   ├── chat_service.py     # Chat orchestration logic
│   ├── session_service.py  # Session management logic
│   └── blueprint_service.py # Blueprint operations
│
├── orchestrator/             # Agent Orchestration
│   ├── routing/            # Routing components
│   │   ├── patterns.py    # RoutingPattern enum
│   │   └── prompts.py     # Prompt templates
│   ├── classifier.py       # OllamaSupervisorClassifier
│   └── supervisor.py       # SupervisorOrchestrator
│
├── agents/                   # Agent Implementations
│   ├── base.py             # OllamaAgent, AgentConfig
│   ├── factory.py          # Agent creation from YAML
│   └── registry.py         # AgentRegistry singleton
│
├── repositories/             # Data Access Layer
│   ├── dynamodb_client.py  # DynamoDB/ScyllaDB operations
│   ├── session_repository.py
│   ├── message_repository.py
│   └── schema_evolution.py # Schema versioning
│
└── cache/                    # Caching Layer
    └── redis_client.py     # Redis Sentinel client
```

**Layer Responsibilities:**

| Layer | Responsibility |
|-------|---------------|
| **Routes** | HTTP handling, request validation, response formatting |
| **Services** | Business logic, orchestration, transaction boundaries |
| **Repositories** | Data persistence, caching, external storage |
| **Schemas** | Shared DTOs between layers, Pydantic models |
| **Dependencies** | FastAPI DI for cross-cutting concerns |

**Import Rules:**

```python
# Routes import from: schemas, services, dependencies
from ...schemas import ChatRequest, ChatResponse
from ...services.chat_service import ChatService
from ..dependencies import get_registry

# Services import from: repositories, agents, schemas
from ..repositories.session_repository import SessionRepository
from ..agents.registry import AgentRegistry

# Repositories import from: config, cache (never from services/routes)
from ..config import get_settings
from ..cache.redis_client import get_redis_client
```

## Environment Variables

### Backend (.env in packages/core)

```bash
# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:32b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# LocalStack
AWS_ENDPOINT_URL=http://localstack.local
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1

# Database
POSTGRES_URL=postgresql://user:pass@localhost:5432/agentic
REDIS_URL=redis://localhost:6379/0
```

### Frontend (.env.local in packages/ui)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Git Conventions

- **Commit messages:** Use conventional commits (feat:, fix:, docs:, refactor:, test:)
- **Branch naming:** feature/name, fix/name, refactor/name
- **PR titles:** Match commit message format

## Common Gotchas

1. **Python virtual environment:** Always use `make` commands from root, which activate venv automatically. If running manual commands, activate first: `source venv/bin/activate`

2. **Ollama models:** Must pull models before first use: `make ollama-pull` (~19GB download)

3. **LocalStack:** Requires Kind cluster `dev-services-amer` running with LocalStack deployed

4. **Port conflicts:** Backend uses 8000, frontend uses 3000. Check if ports are available.

5. **Async everywhere:** Backend is fully async. Don't use blocking I/O.

6. **Type safety:** Both Python (mypy) and TypeScript run in strict mode. Fix all type errors.

## Sisyphus Agent Configuration

**Note:** This codebase uses GitHub Copilot subscription. If you need to change Sisyphus agent configuration to use Claude Opus 4.5 instead of 4.6, modify your OpenCode/Sisyphus configuration file (typically in your home directory or config folder, not in this repository).

The agent configuration is managed by the orchestration system you're using (e.g., OhMyOpenCode), not by this application's codebase.

## Quick Reference

| Task | Command |
|------|---------|
| First setup | `make setup && make ollama-pull` |
| Start dev | `make dev` |
| Run tests | `make test` |
| Format code | `make format` |
| Check quality | `make check` |
| Deploy blueprint | `make blueprint-deploy NAME=devassist` |
| View API docs | http://localhost:8000/docs |
| View frontend | http://localhost:3000 |

---

**Generated for agentic AI systems.** Follow these patterns to maintain consistency and quality across the codebase.
