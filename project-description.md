# DevAssist: Full-Stack Development Multi-Agent Blueprint

**Blueprint:** DevAssist - Full-Stack Development Assistant  
**Platform:** Agentic AI (Scalable Multi-Agent Platform)  
**Pattern:** AWS Bedrock Multi-Agent Supervisor (Simulated Locally)  
**Frontend:** Next.js 14 (App Router) + shadcn/ui + Tailwind CSS  
**Backend:** FastAPI + multi-agent-orchestrator + Ollama  
**Infrastructure:** Kind cluster `dev-services-amer` (LocalStack, PostgreSQL, Redis)  
**Author:** Personal POC  
**Date:** January 30, 2026

> **Note:** This document describes the DevAssist blueprint. For platform architecture, see `local-plan.md`.

---

## Overview

DevAssist is a multi-agent AI system that simulates AWS Bedrock's multi-agent supervisor pattern locally. It provides specialized AI assistants for different aspects of full-stack development, with a supervisor agent that intelligently routes queries to the most appropriate specialist.

### Why Multi-Agent?

```
Single Agent Problem:
┌─────────────────────────────────────────────────────────────────┐
│  One agent trying to be expert in EVERYTHING                     │
│  → Confused context                                              │
│  → Generic responses                                             │
│  → No specialization                                             │
└─────────────────────────────────────────────────────────────────┘

Multi-Agent Solution:
┌─────────────────────────────────────────────────────────────────┐
│  Supervisor routes to SPECIALISTS                                │
│  → Deep expertise per domain                                     │
│  → Focused context per agent                                     │
│  → Can consult multiple specialists for complex queries          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### Supervisor (Router)

The Supervisor analyzes incoming queries and routes them to the most appropriate specialist agent(s).

```yaml
Name: DevAssistSupervisor
Role: Query Router & Response Synthesizer
Collaboration Mode: SUPERVISOR_ROUTER (routes to single best agent)
                    # Can switch to SUPERVISOR for multi-agent synthesis

Routing Logic:
  - Analyzes user query intent
  - Matches against agent descriptions
  - Routes to best-fit specialist
  - Returns specialist response directly (ROUTER mode)
  - Or synthesizes multiple responses (SUPERVISOR mode)
```

---

### Agent 1: Kubernetes Expert

**Identity & Expertise**

```yaml
Name: KubernetesExpert
ID: k8s-expert-001
Description: >
  Kubernetes specialist for cluster management, troubleshooting, 
  manifest creation, Helm charts, and production best practices.
  Route queries about pods, deployments, services, ingress, 
  debugging, and K8s architecture.

Model: qwen2.5:32b (local via Ollama)
Temperature: 0.7
```

**System Prompt**

```
You are KubernetesExpert, a senior Kubernetes engineer with 10+ years of experience managing production clusters at scale.

## Your Expertise
- Cluster architecture and design (single-cluster, multi-cluster, federation)
- Workload management (Deployments, StatefulSets, DaemonSets, Jobs, CronJobs)
- Networking (Services, Ingress, NetworkPolicies, Service Mesh)
- Storage (PV, PVC, StorageClasses, CSI drivers)
- Security (RBAC, PodSecurityPolicies, Secrets management, OPA/Gatekeeper)
- Observability (Prometheus, Grafana, Loki, Jaeger)
- Troubleshooting (CrashLoopBackOff, OOMKilled, ImagePullBackOff, networking issues)
- Helm, Kustomize, and GitOps (ArgoCD, FluxCD)
- Cloud providers (EKS, GKE, AKS) and bare-metal

## Response Style
1. **Diagnose First**: Ask clarifying questions if the issue is ambiguous
2. **Provide Commands**: Include kubectl commands to investigate/fix
3. **Explain Why**: Don't just give solutions, explain the root cause
4. **Best Practices**: Mention production considerations and gotchas
5. **Code Blocks**: Format YAML manifests and commands properly

## Response Format
- Use markdown formatting
- Include ```yaml blocks for manifests
- Include ```bash blocks for commands
- Structure complex answers with headers

## Boundaries
- If asked about non-K8s topics (pure coding, databases, etc.), say:
  "That's outside my Kubernetes expertise. The [Agent Name] might help with that."
- Stay focused on Kubernetes and container orchestration
```

**Example Interactions**

```
User: "My pod keeps crashing with OOMKilled"

KubernetesExpert: 
OOMKilled means your container exceeded its memory limit. Let's diagnose:

**1. Check current limits:**
```bash
kubectl describe pod <pod-name> -n <namespace> | grep -A5 "Limits:"
```

**2. Check actual memory usage before crash:**
```bash
kubectl top pod <pod-name> -n <namespace>
```

**3. Common causes:**
- Memory limit set too low for the application
- Memory leak in the application
- JVM heap not matching container limits (Java apps)

**4. Quick fix - increase limits:**
```yaml
resources:
  requests:
    memory: "512Mi"
  limits:
    memory: "1Gi"  # Increase this
```

**5. Long-term fix:**
- Profile your application's actual memory needs
- Set requests = typical usage, limits = peak + buffer
- For Java: set `-Xmx` to ~75% of container limit

Would you like me to help analyze your specific deployment?
```

---

### Agent 2: Terraform Expert

**Identity & Expertise**

```yaml
Name: TerraformExpert
ID: tf-expert-001
Description: >
  Infrastructure as Code specialist for Terraform/OpenTofu. 
  Expert in HCL, module design, state management, and multi-cloud 
  deployments (AWS, GCP, Azure). Route queries about IaC, 
  provisioning, Terraform errors, and infrastructure architecture.

Model: qwen2.5:32b (local via Ollama)
Temperature: 0.7
```

**System Prompt**

```
You are TerraformExpert, a senior infrastructure engineer specializing in Infrastructure as Code with 8+ years of Terraform experience.

## Your Expertise
- HCL syntax and best practices
- Module design and composition
- State management (local, S3, Terraform Cloud, pg backend)
- Workspaces and environment management
- Provider configuration (AWS, GCP, Azure, Kubernetes)
- Resource dependencies and lifecycle
- Import existing infrastructure
- Debugging plan/apply errors
- CI/CD integration (GitHub Actions, GitLab CI, Atlantis)
- Terraform Cloud and Enterprise
- OpenTofu migration

## Response Style
1. **Complete Code**: Provide working HCL, not snippets
2. **Explain Structure**: Show file organization for modules
3. **State Safety**: Warn about state-affecting operations
4. **Dependencies**: Explain implicit vs explicit dependencies
5. **Variables**: Use variables for reusability, show example tfvars

## Response Format
- Use ```hcl code blocks for Terraform code
- Show file names (e.g., # main.tf, # variables.tf)
- Include example terraform.tfvars when relevant
- Structure modules with inputs/outputs

## Common Patterns You Provide
- Module structure (main.tf, variables.tf, outputs.tf)
- Remote state configuration
- Provider aliases for multi-region
- Data sources for existing resources
- Dynamic blocks and for_each
- Conditional resource creation

## Boundaries
- Focus on infrastructure and IaC
- For application code or K8s specifics, refer to other agents
```

**Example Interactions**

```
User: "How do I create an S3 bucket with Terraform?"

TerraformExpert:
Here's a production-ready S3 bucket module:

**File Structure:**
```
modules/s3-bucket/
├── main.tf
├── variables.tf
└── outputs.tf
```

**main.tf:**
```hcl
resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  
  tags = merge(var.tags, {
    Name        = var.bucket_name
    Environment = var.environment
  })
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  
  versioning_configuration {
    status = var.versioning_enabled ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

**variables.tf:**
```hcl
variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "versioning_enabled" {
  description = "Enable versioning"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}
```

**outputs.tf:**
```hcl
output "bucket_id" {
  description = "The name of the bucket"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "The ARN of the bucket"
  value       = aws_s3_bucket.this.arn
}
```

**Usage:**
```hcl
module "my_bucket" {
  source = "./modules/s3-bucket"
  
  bucket_name        = "my-app-data-${var.environment}"
  environment        = var.environment
  versioning_enabled = true
  
  tags = {
    Project = "my-app"
  }
}
```

This includes security best practices: encryption, versioning, and public access blocking.
```

---

### Agent 3: Python Backend Expert

**Identity & Expertise**

```yaml
Name: PythonBackendExpert
ID: py-backend-001
Description: >
  Python backend specialist for API development, FastAPI, Django,
  database design, async programming, and microservices. Route 
  queries about Python code, REST APIs, SQL, ORMs, and backend 
  architecture patterns.

Model: qwen2.5:32b (local via Ollama)
Temperature: 0.7
```

**System Prompt**

```
You are PythonBackendExpert, a senior backend engineer specializing in Python with 10+ years of experience building production APIs and services.

## Your Expertise
- FastAPI and async Python (your primary framework)
- Django and Django REST Framework
- SQLAlchemy and Alembic migrations
- PostgreSQL, Redis, MongoDB
- API design (REST, GraphQL)
- Authentication (JWT, OAuth2, API keys)
- Testing (pytest, fixtures, mocking)
- Async programming (asyncio, aiohttp)
- Message queues (Celery, RQ, SQS)
- Microservices patterns
- Python packaging and project structure

## Code Standards
- Type hints on all functions
- Pydantic models for validation
- Dependency injection patterns
- SOLID principles
- Comprehensive error handling
- Logging with structlog

## Response Style
1. **Working Code**: Provide complete, runnable examples
2. **Type Hints**: Always include type annotations
3. **Best Practices**: Follow PEP8, use modern Python (3.11+)
4. **Testing**: Include test examples when relevant
5. **Security**: Mention security considerations

## Response Format
- Use ```python code blocks
- Show file organization for larger examples
- Include requirements.txt or pyproject.toml deps
- Add docstrings to functions

## Boundaries
- Focus on backend Python development
- For frontend or infrastructure, refer to other agents
```

**Example Interactions**

```
User: "Create a FastAPI endpoint for user registration"

PythonBackendExpert:
Here's a production-ready user registration endpoint:

**models/user.py:**
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

**schemas/user.py:**
```python
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    
    model_config = {"from_attributes": True}
```

**services/auth.py:**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

**routes/users.py:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Register a new user.
    
    - Validates email uniqueness
    - Hashes password with bcrypt
    - Returns created user (without password)
    """
    # Check if email exists
    existing = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user
```

**Requirements:**
```
fastapi>=0.109.0
sqlalchemy[asyncio]>=2.0.0
pydantic[email]>=2.0.0
passlib[bcrypt]>=1.7.4
```

Key security features:
- Password hashed with bcrypt
- Email validation via Pydantic
- Async database operations
- Proper error handling
```

---

### Agent 4: Frontend Expert

**Identity & Expertise**

```yaml
Name: FrontendExpert
ID: frontend-001
Description: >
  Frontend specialist for React, TypeScript, Next.js, and modern 
  web development. Expert in component design, state management,
  CSS/Tailwind, and UI/UX patterns. Route queries about React,
  JavaScript/TypeScript, styling, and frontend architecture.

Model: qwen2.5:32b (local via Ollama)
Temperature: 0.7
```

**System Prompt**

```
You are FrontendExpert, a senior frontend engineer specializing in React and TypeScript with 8+ years of experience building production web applications.

## Your Expertise
- React 18+ (hooks, suspense, server components)
- TypeScript (strict mode advocate)
- Next.js 14+ (App Router, Server Actions)
- State management (Zustand, Jotai, React Query)
- Styling (Tailwind CSS, CSS Modules, styled-components)
- Component design (Radix UI, shadcn/ui, Headless UI)
- Testing (Jest, React Testing Library, Playwright)
- Performance optimization (lazy loading, memoization)
- Accessibility (WCAG, ARIA)
- Build tools (Vite, webpack, turbopack)

## Code Standards
- TypeScript strict mode
- Functional components only
- Custom hooks for logic extraction
- Proper prop typing with interfaces
- Error boundaries for resilience
- Accessible by default

## Response Style
1. **Complete Components**: Provide full, working code
2. **TypeScript**: Always use proper types, no `any`
3. **Modern React**: Use hooks, avoid class components
4. **Accessibility**: Include ARIA attributes where needed
5. **Performance**: Mention optimization opportunities

## Response Format
- Use ```tsx for React TypeScript code
- Use ```css or Tailwind classes for styling
- Show component file structure
- Include prop interfaces

## Boundaries
- Focus on frontend development
- For backend APIs or infrastructure, refer to other agents
```

---

### Agent 5: System Architect

**Identity & Expertise**

```yaml
Name: SystemArchitect
ID: architect-001
Description: >
  System architecture specialist for high-level design, technology
  decisions, scalability patterns, and trade-off analysis. Route 
  queries about architecture decisions, system design, tech stack
  selection, and cross-cutting concerns.

Model: qwen2.5:32b (local via Ollama)
Temperature: 0.7
```

**System Prompt**

```
You are SystemArchitect, a principal engineer with 15+ years of experience designing systems at scale for companies from startups to FAANG.

## Your Expertise
- Distributed systems design
- Microservices vs monolith decisions
- Database selection (SQL vs NoSQL, when to use what)
- Caching strategies (Redis, CDN, application-level)
- Message queues and event-driven architecture
- API design (REST, GraphQL, gRPC)
- Authentication and authorization patterns
- Scalability (horizontal, vertical, auto-scaling)
- Reliability (fault tolerance, disaster recovery)
- Security architecture
- Cost optimization
- Technical debt management

## Response Style
1. **Trade-offs First**: Always present pros/cons
2. **Ask Constraints**: Clarify scale, budget, team size
3. **Diagrams**: Describe architecture with ASCII diagrams
4. **Incremental**: Suggest MVP → Scale path
5. **Real Examples**: Reference how big companies solved similar problems

## Response Format
- Use ASCII diagrams for architecture
- Present options as comparison tables
- Include "Questions to Consider" sections
- Suggest phased implementation

## Approach
- Start with requirements clarification
- Present multiple options with trade-offs
- Recommend based on constraints
- Consider team capabilities and timeline

## Boundaries
- Focus on architecture and design
- For implementation details, refer to specialist agents
- You provide the "what" and "why", they provide the "how"
```

---

## Core Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DevAssist Architecture                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                            API Layer (FastAPI)                            │   │
│  │                                                                           │   │
│  │  POST /api/v1/chat                    - Send message to agents           │   │
│  │  GET  /api/v1/chat/{session_id}       - Get conversation history         │   │
│  │  POST /api/v1/documents               - Upload to knowledge base         │   │
│  │  GET  /api/v1/documents               - List documents                   │   │
│  │  DELETE /api/v1/documents/{id}        - Remove document                  │   │
│  │  GET  /api/v1/health                  - Health check                     │   │
│  │                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                          │
│                                       ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         Orchestrator Layer                                │   │
│  │                                                                           │   │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │   │
│  │  │   Classifier    │───▶│     Router      │───▶│   Synthesizer   │      │   │
│  │  │                 │    │                 │    │   (if needed)   │      │   │
│  │  │ Analyzes query  │    │ Selects agent   │    │ Combines multi- │      │   │
│  │  │ intent          │    │ based on match  │    │ agent responses │      │   │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘      │   │
│  │                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                          │
│                    ┌──────────────────┼──────────────────┐                      │
│                    │                  │                  │                      │
│                    ▼                  ▼                  ▼                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           Agent Layer                                    │   │
│  │                                                                          │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │   │
│  │  │ Kubernetes   │ │  Terraform   │ │   Python     │ │  Frontend    │   │   │
│  │  │   Expert     │ │   Expert     │ │   Backend    │ │   Expert     │   │   │
│  │  │              │ │              │ │   Expert     │ │              │   │   │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘   │   │
│  │         │                │                │                │           │   │
│  │  ┌──────────────┐                                                      │   │
│  │  │   System     │        All agents share:                             │   │
│  │  │  Architect   │        • Same LLM (Ollama)                           │   │
│  │  │              │        • Knowledge Base access                       │   │
│  │  └──────┬───────┘        • Session context                             │   │
│  │         │                                                              │   │
│  └─────────┼──────────────────────────────────────────────────────────────┘   │
│            │                                                                    │
│            ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         Knowledge Layer                                   │   │
│  │                                                                           │   │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │   │
│  │  │    Retriever    │───▶│  Vector Store   │    │ Document Store  │      │   │
│  │  │                 │    │  (PostgreSQL +  │    │      (S3)       │      │   │
│  │  │ Semantic search │    │   pgvector)     │    │                 │      │   │
│  │  │ for relevant    │    │                 │    │ Raw files:      │      │   │
│  │  │ context         │    │ Embeddings for  │    │ • PDFs          │      │   │
│  │  │                 │    │ similarity      │    │ • Markdown      │      │   │
│  │  │                 │    │ search          │    │ • Code          │      │   │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘      │   │
│  │                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                           LLM Layer (Ollama)                              │   │
│  │                                                                           │   │
│  │  ┌─────────────────────────┐    ┌─────────────────────────┐             │   │
│  │  │     qwen2.5:32b         │    │   nomic-embed-text      │             │   │
│  │  │                         │    │                         │             │   │
│  │  │   Chat & Reasoning      │    │   Text Embeddings       │             │   │
│  │  │   - Agent responses     │    │   - Document indexing   │             │   │
│  │  │   - Classification      │    │   - Semantic search     │             │   │
│  │  │                         │    │                         │             │   │
│  │  └─────────────────────────┘    └─────────────────────────┘             │   │
│  │                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        Storage Layer (Your Cluster)                       │   │
│  │                                                                           │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐         │   │
│  │  │ PostgreSQL │  │ LocalStack │  │ LocalStack │  │   Redis    │         │   │
│  │  │ + pgvector │  │     S3     │  │  DynamoDB  │  │            │         │   │
│  │  │            │  │            │  │            │  │            │         │   │
│  │  │ Vector     │  │ Documents  │  │ Sessions   │  │ Cache      │         │   │
│  │  │ embeddings │  │ Raw files  │  │ History    │  │ Rate limit │         │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘         │   │
│  │                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Request Flow                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  1. USER QUERY                                                                   │
│     │                                                                            │
│     │  "My pod keeps crashing with OOMKilled, how do I fix it?"                 │
│     │                                                                            │
│     ▼                                                                            │
│  2. API LAYER (FastAPI)                                                          │
│     │                                                                            │
│     ├─▶ Validate request                                                         │
│     ├─▶ Load/create session from DynamoDB                                        │
│     ├─▶ Rate limit check (Redis)                                                 │
│     │                                                                            │
│     ▼                                                                            │
│  3. ORCHESTRATOR                                                                 │
│     │                                                                            │
│     ├─▶ Classifier analyzes: "pod", "crashing", "OOMKilled"                     │
│     │   → Domain: Kubernetes                                                     │
│     │   → Confidence: 0.95                                                       │
│     │                                                                            │
│     ├─▶ Router selects: KubernetesExpert                                        │
│     │                                                                            │
│     ▼                                                                            │
│  4. KNOWLEDGE RETRIEVAL (Optional RAG)                                           │
│     │                                                                            │
│     ├─▶ Embed query: "OOMKilled fix kubernetes pod"                             │
│     ├─▶ Search pgvector for similar content                                      │
│     ├─▶ Retrieve top-k relevant chunks                                           │
│     │   (e.g., your runbooks, past debugging notes)                              │
│     │                                                                            │
│     ▼                                                                            │
│  5. AGENT PROCESSING                                                             │
│     │                                                                            │
│     ├─▶ Build prompt:                                                            │
│     │   - System prompt (K8s expert persona)                                     │
│     │   - Retrieved context (if any)                                             │
│     │   - Conversation history                                                   │
│     │   - User query                                                             │
│     │                                                                            │
│     ├─▶ Call Ollama (qwen2.5:32b)                                               │
│     │                                                                            │
│     ▼                                                                            │
│  6. RESPONSE                                                                     │
│     │                                                                            │
│     ├─▶ Save to session history (DynamoDB)                                       │
│     ├─▶ Return to user with metadata:                                            │
│     │   - Response text                                                          │
│     │   - Agent used: KubernetesExpert                                           │
│     │   - Confidence score                                                       │
│     │   - Sources (if RAG used)                                                  │
│     │                                                                            │
│     ▼                                                                            │
│  7. USER RECEIVES                                                                │
│                                                                                  │
│     {                                                                            │
│       "response": "OOMKilled means your container exceeded...",                 │
│       "agent": "KubernetesExpert",                                              │
│       "confidence": 0.95,                                                        │
│       "session_id": "sess_abc123"                                               │
│     }                                                                            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Session Management

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Session Architecture                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Session Storage (DynamoDB via LocalStack)                                       │
│                                                                                  │
│  Table: devassist-sessions                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ session_id (PK) │ user_id │ created_at │ updated_at │ expires_at │ ttl │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │ sess_abc123     │ user_1  │ 2026-01-30 │ 2026-01-30 │ 2026-01-31 │ ... │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  Table: devassist-history                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ session_id (PK) │ timestamp (SK) │ role │ content │ agent │ metadata  │     │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │ sess_abc123     │ 1706640000     │ user │ "Fix OOM"│  -    │    {}     │     │
│  │ sess_abc123     │ 1706640005     │ asst │ "OOM..." │ K8s   │ {conf:95} │     │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  Cache Layer (Redis)                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Key: session:{session_id}                                               │    │
│  │  Value: Recent messages (last 10)                                        │    │
│  │  TTL: 1 hour                                                             │    │
│  │                                                                          │    │
│  │  Purpose: Fast access without DynamoDB query                             │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Knowledge Base Architecture

### RAG Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RAG (Retrieval-Augmented Generation)                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  INGESTION FLOW (Upload Document)                                                │
│                                                                                  │
│  1. Upload                 2. Process              3. Chunk                      │
│  ┌──────────┐             ┌──────────┐            ┌──────────┐                  │
│  │  User    │────────────▶│  Parser  │───────────▶│ Chunker  │                  │
│  │ uploads  │             │          │            │          │                  │
│  │ PDF/MD   │             │ Extract  │            │ Split    │                  │
│  └──────────┘             │ text     │            │ into     │                  │
│                           └──────────┘            │ ~500     │                  │
│                                                   │ tokens   │                  │
│                                                   └────┬─────┘                  │
│                                                        │                         │
│  4. Embed                  5. Store                    ▼                         │
│  ┌──────────┐             ┌──────────┐           ┌──────────┐                   │
│  │  Ollama  │◀────────────│ pgvector │◀──────────│  Chunks  │                   │
│  │ nomic-  │             │          │           │          │                   │
│  │ embed-  │─────────────▶│  Store   │           │ + meta   │                   │
│  │ text    │  vectors    │ vectors  │           │          │                   │
│  └──────────┘             └──────────┘           └──────────┘                   │
│                                                                                  │
│  6. Also store raw file in S3 for reference                                      │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  RETRIEVAL FLOW (Query)                                                          │
│                                                                                  │
│  1. Query                  2. Embed               3. Search                      │
│  ┌──────────┐             ┌──────────┐           ┌──────────┐                   │
│  │  User    │────────────▶│  Ollama  │──────────▶│ pgvector │                   │
│  │ "How to │             │  nomic-  │           │          │                   │
│  │  fix X?" │             │  embed   │           │ cosine   │                   │
│  └──────────┘             └──────────┘           │ similarity│                   │
│                                                   └────┬─────┘                   │
│                                                        │                         │
│  4. Context                5. Generate                 ▼                         │
│  ┌──────────┐             ┌──────────┐           ┌──────────┐                   │
│  │  Agent   │◀────────────│  Prompt  │◀──────────│  Top-k   │                   │
│  │ receives │             │  Builder │           │  chunks  │                   │
│  │ relevant │             │          │           │          │                   │
│  │ context  │             │ System + │           │ Ranked   │                   │
│  └──────────┘             │ Context +│           │ results  │                   │
│                           │ Query    │           └──────────┘                   │
│                           └──────────┘                                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Vector Store Schema (PostgreSQL + pgvector)

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table (metadata)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,  -- 'pdf', 'markdown', 'code', 'url'
    s3_key VARCHAR(500),                -- Reference to S3 object
    agent_scope VARCHAR(50)[],          -- Which agents can access: ['k8s', 'terraform', 'all']
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Chunks table (for semantic search)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),              -- nomic-embed-text dimension
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Index for similarity search
    CONSTRAINT unique_doc_chunk UNIQUE (document_id, chunk_index)
);

-- Create HNSW index for fast similarity search
CREATE INDEX ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Search function
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(768),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    agent_filter VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT,
    title VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.document_id,
        dc.content,
        1 - (dc.embedding <=> query_embedding) AS similarity,
        d.title
    FROM document_chunks dc
    JOIN documents d ON dc.document_id = d.id
    WHERE 
        1 - (dc.embedding <=> query_embedding) > match_threshold
        AND (agent_filter IS NULL OR agent_filter = ANY(d.agent_scope) OR 'all' = ANY(d.agent_scope))
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

---

## API Specification

### Endpoints

```yaml
openapi: 3.0.0
info:
  title: DevAssist API
  version: 1.0.0
  description: Multi-Agent Development Assistant

paths:
  /api/v1/chat:
    post:
      summary: Send a message to the agent system
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - message
              properties:
                message:
                  type: string
                  example: "How do I fix OOMKilled in my pod?"
                session_id:
                  type: string
                  description: Optional. Creates new session if not provided
                agent_hint:
                  type: string
                  description: Optional. Hint for which agent to use
                  enum: [kubernetes, terraform, python, frontend, architect]
      responses:
        200:
          description: Agent response
          content:
            application/json:
              schema:
                type: object
                properties:
                  response:
                    type: string
                  agent:
                    type: string
                  confidence:
                    type: number
                  session_id:
                    type: string
                  sources:
                    type: array
                    items:
                      type: object
                      properties:
                        title:
                          type: string
                        similarity:
                          type: number

  /api/v1/chat/{session_id}:
    get:
      summary: Get conversation history
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
            default: 50
      responses:
        200:
          description: Conversation history
          content:
            application/json:
              schema:
                type: object
                properties:
                  session_id:
                    type: string
                  messages:
                    type: array
                    items:
                      type: object
                      properties:
                        role:
                          type: string
                          enum: [user, assistant]
                        content:
                          type: string
                        agent:
                          type: string
                        timestamp:
                          type: string

  /api/v1/documents:
    post:
      summary: Upload document to knowledge base
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              required:
                - file
              properties:
                file:
                  type: string
                  format: binary
                title:
                  type: string
                agent_scope:
                  type: array
                  items:
                    type: string
                  default: ["all"]
      responses:
        201:
          description: Document uploaded and indexed

    get:
      summary: List documents in knowledge base
      responses:
        200:
          description: List of documents

  /api/v1/health:
    get:
      summary: Health check
      responses:
        200:
          description: System health status
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                  ollama:
                    type: string
                  database:
                    type: string
                  redis:
                    type: string
```

---

## Frontend Architecture (Next.js)

### Full-Stack Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DevAssist Full-Stack                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                     FRONTEND (Next.js 14)                               │     │
│  │                     http://localhost:3000                               │     │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │     │
│  │  │                                                                  │   │     │
│  │  │   ┌──────────┐  ┌─────────────────────────────────────────────┐│   │     │
│  │  │   │ Sidebar  │  │              Chat Area                      ││   │     │
│  │  │   │          │  │  ┌───────────────────────────────────────┐  ││   │     │
│  │  │   │ Sessions │  │  │         Message List                  │  ││   │     │
│  │  │   │ • Chat 1 │  │  │  ┌─────────────────────────────────┐  │  ││   │     │
│  │  │   │ • Chat 2 │  │  │  │ User: How do I fix OOMKilled?   │  │  ││   │     │
│  │  │   │ • Chat 3 │  │  │  └─────────────────────────────────┘  │  ││   │     │
│  │  │   │          │  │  │  ┌─────────────────────────────────┐  │  ││   │     │
│  │  │   │ [+ New]  │  │  │  │ 🤖 KubernetesExpert             │  │  ││   │     │
│  │  │   │          │  │  │  │ OOMKilled means your container  │  │  ││   │     │
│  │  │   │          │  │  │  │ exceeded its memory limit...    │  │  ││   │     │
│  │  │   │ Agents:  │  │  │  │ ```bash                         │  │  ││   │     │
│  │  │   │ ○ K8s    │  │  │  │ kubectl describe pod...         │  │  ││   │     │
│  │  │   │ ○ TF     │  │  │  │ ```                             │  │  ││   │     │
│  │  │   │ ○ Python │  │  │  └─────────────────────────────────┘  │  ││   │     │
│  │  │   │ ○ React  │  │  └───────────────────────────────────────┘  ││   │     │
│  │  │   │ ○ Arch   │  │  ┌───────────────────────────────────────┐  ││   │     │
│  │  │   └──────────┘  │  │ [Type your message...]        [Send] │  ││   │     │
│  │  │                 │  └───────────────────────────────────────┘  ││   │     │
│  │  │                 └─────────────────────────────────────────────┘│   │     │
│  │  └─────────────────────────────────────────────────────────────────┘   │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                      │                                           │
│                                      │ HTTP/SSE (Streaming)                      │
│                                      ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                      BACKEND (FastAPI)                                  │     │
│  │                      http://localhost:8000                              │     │
│  │                                                                         │     │
│  │   POST /api/v1/chat          → Agent orchestration + streaming         │     │
│  │   GET  /api/v1/sessions      → List user sessions                      │     │
│  │   GET  /api/v1/sessions/{id} → Get conversation history                │     │
│  │   POST /api/v1/documents     → Upload to knowledge base                │     │
│  │                                                                         │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Next.js Project Structure

```
frontend/
├── package.json
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── .env.local                          # API URL config
│
├── app/
│   ├── layout.tsx                      # Root layout with providers
│   ├── page.tsx                        # Home → redirect to /chat
│   ├── globals.css                     # Tailwind imports
│   │
│   ├── chat/
│   │   ├── page.tsx                    # Main chat page
│   │   ├── [sessionId]/
│   │   │   └── page.tsx                # Chat with specific session
│   │   └── layout.tsx                  # Chat layout with sidebar
│   │
│   └── api/                            # Optional: BFF endpoints
│       └── health/
│           └── route.ts
│
├── components/
│   ├── ui/                             # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── scroll-area.tsx
│   │   ├── avatar.tsx
│   │   ├── badge.tsx
│   │   ├── card.tsx
│   │   ├── dropdown-menu.tsx
│   │   └── skeleton.tsx
│   │
│   ├── chat/
│   │   ├── chat-container.tsx          # Main chat wrapper
│   │   ├── message-list.tsx            # Scrollable message area
│   │   ├── message-item.tsx            # Individual message bubble
│   │   ├── chat-input.tsx              # Input box + send button
│   │   ├── agent-badge.tsx             # Shows which agent responded
│   │   ├── code-block.tsx              # Syntax highlighted code
│   │   ├── streaming-text.tsx          # Animated streaming text
│   │   └── typing-indicator.tsx        # "Agent is thinking..."
│   │
│   ├── sidebar/
│   │   ├── sidebar.tsx                 # Main sidebar component
│   │   ├── session-list.tsx            # List of chat sessions
│   │   ├── session-item.tsx            # Individual session row
│   │   ├── agent-status.tsx            # Shows available agents
│   │   └── new-chat-button.tsx
│   │
│   └── layout/
│       ├── header.tsx                  # Top header bar
│       └── theme-toggle.tsx            # Dark/light mode
│
├── lib/
│   ├── api.ts                          # FastAPI client
│   ├── utils.ts                        # Helper functions (cn, etc.)
│   └── hooks/
│       ├── use-chat.ts                 # Chat state management
│       ├── use-sessions.ts             # Session list hook
│       └── use-streaming.ts            # SSE streaming hook
│
├── types/
│   └── index.ts                        # TypeScript interfaces
│
└── stores/
    └── chat-store.ts                   # Zustand store for chat state
```

### Key Components

#### Chat Container

```tsx
// components/chat/chat-container.tsx
"use client";

import { useState } from "react";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { useChat } from "@/lib/hooks/use-chat";

interface ChatContainerProps {
  sessionId?: string;
}

export function ChatContainer({ sessionId }: ChatContainerProps) {
  const { messages, isLoading, sendMessage, currentAgent } = useChat(sessionId);

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-hidden">
        <MessageList 
          messages={messages} 
          isLoading={isLoading} 
        />
      </div>

      {/* Current Agent Indicator */}
      {currentAgent && (
        <div className="px-4 py-2 text-sm text-muted-foreground">
          Routed to: <span className="font-medium">{currentAgent}</span>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t p-4">
        <ChatInput 
          onSend={sendMessage} 
          disabled={isLoading} 
        />
      </div>
    </div>
  );
}
```

#### Message Item with Agent Badge

```tsx
// components/chat/message-item.tsx
"use client";

import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { CodeBlock } from "./code-block";
import { Message } from "@/types";

const agentColors: Record<string, string> = {
  KubernetesExpert: "bg-blue-500",
  TerraformExpert: "bg-purple-500",
  PythonBackendExpert: "bg-green-500",
  FrontendExpert: "bg-orange-500",
  SystemArchitect: "bg-red-500",
};

const agentIcons: Record<string, string> = {
  KubernetesExpert: "☸️",
  TerraformExpert: "🏗️",
  PythonBackendExpert: "🐍",
  FrontendExpert: "⚛️",
  SystemArchitect: "🏛️",
};

interface MessageItemProps {
  message: Message;
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === "user";
  const agentName = message.agent;

  return (
    <div
      className={cn(
        "flex gap-3 p-4",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <Avatar className="h-8 w-8">
          <AvatarFallback className={agentColors[agentName || ""] || "bg-gray-500"}>
            {agentIcons[agentName || ""] || "🤖"}
          </AvatarFallback>
        </Avatar>
      )}

      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-2",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        )}
      >
        {/* Agent Badge */}
        {!isUser && agentName && (
          <Badge variant="outline" className="mb-2 text-xs">
            {agentName}
          </Badge>
        )}

        {/* Message Content with Markdown */}
        <div className="prose prose-sm dark:prose-invert">
          <MessageContent content={message.content} />
        </div>

        {/* Confidence Score */}
        {message.confidence && (
          <div className="mt-2 text-xs text-muted-foreground">
            Confidence: {Math.round(message.confidence * 100)}%
          </div>
        )}
      </div>

      {isUser && (
        <Avatar className="h-8 w-8">
          <AvatarFallback>U</AvatarFallback>
        </Avatar>
      )}
    </div>
  );
}
```

#### Streaming Hook

```tsx
// lib/hooks/use-chat.ts
"use client";

import { useState, useCallback, useEffect } from "react";
import { Message, ChatResponse } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useChat(sessionId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState(sessionId);

  // Load existing session
  useEffect(() => {
    if (sessionId) {
      loadSession(sessionId);
    }
  }, [sessionId]);

  const loadSession = async (id: string) => {
    const res = await fetch(`${API_URL}/api/v1/chat/${id}`);
    if (res.ok) {
      const data = await res.json();
      setMessages(data.messages);
    }
  };

  const sendMessage = useCallback(async (content: string) => {
    // Add user message immediately
    const userMessage: Message = {
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Stream response from FastAPI
      const res = await fetch(`${API_URL}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: content,
          session_id: currentSessionId,
        }),
      });

      if (!res.ok) throw new Error("Failed to send message");

      const data: ChatResponse = await res.json();
      
      // Update session ID if new
      if (!currentSessionId) {
        setCurrentSessionId(data.session_id);
      }

      // Add assistant message
      const assistantMessage: Message = {
        role: "assistant",
        content: data.response,
        agent: data.agent,
        confidence: data.confidence,
        timestamp: new Date().toISOString(),
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
      setCurrentAgent(data.agent);
    } catch (error) {
      console.error("Chat error:", error);
    } finally {
      setIsLoading(false);
    }
  }, [currentSessionId]);

  return {
    messages,
    isLoading,
    sendMessage,
    currentAgent,
    sessionId: currentSessionId,
  };
}
```

### API Client

```typescript
// lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatRequest {
  message: string;
  session_id?: string;
  agent_hint?: string;
}

export interface ChatResponse {
  response: string;
  agent: string;
  confidence: number;
  session_id: string;
  sources?: Array<{ title: string; similarity: number }>;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

export const api = {
  // Chat
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const res = await fetch(`${API_URL}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) throw new Error("Failed to send message");
    return res.json();
  },

  // Sessions
  async getSessions(): Promise<Session[]> {
    const res = await fetch(`${API_URL}/api/v1/sessions`);
    if (!res.ok) throw new Error("Failed to fetch sessions");
    return res.json();
  },

  async getSession(sessionId: string): Promise<{ messages: Message[] }> {
    const res = await fetch(`${API_URL}/api/v1/chat/${sessionId}`);
    if (!res.ok) throw new Error("Failed to fetch session");
    return res.json();
  },

  async deleteSession(sessionId: string): Promise<void> {
    await fetch(`${API_URL}/api/v1/sessions/${sessionId}`, {
      method: "DELETE",
    });
  },

  // Health
  async checkHealth(): Promise<{ status: string }> {
    const res = await fetch(`${API_URL}/api/v1/health`);
    return res.json();
  },
};
```

### Types

```typescript
// types/index.ts
export interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string;
  confidence?: number;
  timestamp: string;
  sources?: Source[];
}

export interface Source {
  title: string;
  similarity: number;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Agent {
  name: string;
  description: string;
  icon: string;
  color: string;
}

export type AgentName =
  | "KubernetesExpert"
  | "TerraformExpert"
  | "PythonBackendExpert"
  | "FrontendExpert"
  | "SystemArchitect";
```

### UI Screenshots (Design)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌────┐                                              [Theme] [Settings]     │
│  │ DA │  DevAssist                                                          │
│  └────┘                                                                     │
├─────────────┬───────────────────────────────────────────────────────────────┤
│             │                                                               │
│  SESSIONS   │                    Welcome to DevAssist                       │
│  ─────────  │                                                               │
│             │     Your AI-powered development assistant with specialized   │
│  ┌────────┐ │     agents for Kubernetes, Terraform, Python, React, and     │
│  │ Chat 1 │ │     System Architecture.                                      │
│  └────────┘ │                                                               │
│  ┌────────┐ │     ┌─────────────────────────────────────────────────────┐  │
│  │ Chat 2 │ │     │                                                     │  │
│  └────────┘ │     │   💡 Try asking:                                    │  │
│             │     │                                                     │  │
│  [+ New Chat]│     │   "How do I fix OOMKilled in my Kubernetes pod?"   │  │
│             │     │                                                     │  │
│  ─────────  │     │   "Create a Terraform module for an S3 bucket"     │  │
│  AGENTS     │     │                                                     │  │
│             │     │   "Design a FastAPI endpoint for user auth"        │  │
│  ☸️ K8s     │     │                                                     │  │
│  🏗️ Terraform│     │   "What's the best architecture for a chat app?"   │  │
│  🐍 Python  │     │                                                     │  │
│  ⚛️ Frontend│     └─────────────────────────────────────────────────────┘  │
│  🏛️ Architect│                                                              │
│             │                                                               │
├─────────────┴───────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Ask anything about development...                           [Send] │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 14 (App Router) | React framework with SSR |
| **UI Components** | shadcn/ui | Beautiful, accessible components |
| **Styling** | Tailwind CSS | Utility-first CSS |
| **State** | Zustand | Lightweight state management |
| **API** | FastAPI | REST API, async support, auto OpenAPI docs |
| **Orchestration** | multi-agent-orchestrator | Agent routing and management |
| **LLM** | Ollama + qwen2.5:32b | Local inference |
| **Embeddings** | Ollama + nomic-embed-text | Vector embeddings for RAG |
| **Vector DB** | PostgreSQL + pgvector | Semantic search |
| **Document Store** | LocalStack S3 | Raw file storage |
| **Session Store** | LocalStack DynamoDB | Conversation persistence |
| **Cache** | Redis | Session cache, rate limiting |
| **Validation** | Pydantic + Zod | Backend + Frontend validation |
| **Testing** | pytest + Playwright | Backend + E2E tests |
| **Monitoring** | Prometheus + Grafana | Metrics and dashboards |

---

## Implementation Phases

### Phase 1: Backend Foundation
- [ ] Project setup (pyproject.toml, structure)
- [ ] Basic FastAPI app with health endpoint
- [ ] Ollama integration (chat + embeddings)
- [ ] Single agent working (KubernetesExpert)
- [ ] CLI for testing

### Phase 2: Multi-Agent Backend
- [ ] Add all 5 agents
- [ ] Orchestrator with classifier
- [ ] Agent routing working
- [ ] Session management (in-memory first)
- [ ] API endpoints for chat

### Phase 3: Frontend Setup
- [ ] Next.js 14 project setup
- [ ] shadcn/ui installation and config
- [ ] Basic layout (sidebar + chat area)
- [ ] Chat input component
- [ ] Message list component
- [ ] Connect to FastAPI backend

### Phase 4: Frontend Features
- [ ] Session management (new chat, history)
- [ ] Agent badges and indicators
- [ ] Code block syntax highlighting
- [ ] Markdown rendering
- [ ] Dark/light theme toggle
- [ ] Loading states and animations

### Phase 5: Persistence Layer
- [ ] LocalStack DynamoDB for sessions
- [ ] LocalStack S3 for documents
- [ ] Redis caching
- [ ] Terraform for resources

### Phase 6: Knowledge Base (RAG)
- [ ] pgvector setup in PostgreSQL
- [ ] Document ingestion pipeline
- [ ] Embedding generation
- [ ] Semantic search integration
- [ ] Document upload UI in frontend

### Phase 7: Production Polish
- [ ] API authentication
- [ ] Rate limiting
- [ ] Error handling
- [ ] Logging and monitoring
- [ ] Grafana dashboard
- [ ] E2E tests with Playwright
- [ ] Logging and monitoring
- [ ] Grafana dashboard

---

## Complete Project Structure

```
devassist/
├── README.md
├── Makefile                            # Dev commands (start, test, etc.)
├── docker-compose.yml                  # Local dev services
│
├── backend/                            # FastAPI Backend
│   ├── pyproject.toml
│   ├── .env.example
│   │
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app entry
│   │   ├── config.py                   # Settings (Pydantic)
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                 # Dependency injection
│   │   │   └── routes/
│   │   │       ├── chat.py             # POST /chat
│   │   │       ├── sessions.py         # Session management
│   │   │       ├── documents.py        # Knowledge base
│   │   │       └── health.py           # Health checks
│   │   │
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # OllamaAgent base
│   │   │   ├── kubernetes.py           # K8s expert
│   │   │   ├── terraform.py            # TF expert
│   │   │   ├── python_backend.py       # Python expert
│   │   │   ├── frontend.py             # React expert
│   │   │   ├── architect.py            # System architect
│   │   │   └── orchestrator.py         # Supervisor setup
│   │   │
│   │   ├── knowledge/
│   │   │   ├── __init__.py
│   │   │   ├── embeddings.py           # Ollama embeddings
│   │   │   ├── vectorstore.py          # pgvector
│   │   │   └── retriever.py            # RAG retrieval
│   │   │
│   │   └── storage/
│   │       ├── __init__.py
│   │       ├── sessions.py             # DynamoDB
│   │       ├── documents.py            # S3
│   │       └── cache.py                # Redis
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_agents.py
│       └── test_api.py
│
├── frontend/                           # Next.js Frontend
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── .env.local.example
│   │
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   └── chat/
│   │       ├── page.tsx
│   │       ├── layout.tsx
│   │       └── [sessionId]/
│   │           └── page.tsx
│   │
│   ├── components/
│   │   ├── ui/                         # shadcn/ui
│   │   ├── chat/
│   │   │   ├── chat-container.tsx
│   │   │   ├── message-list.tsx
│   │   │   ├── message-item.tsx
│   │   │   ├── chat-input.tsx
│   │   │   └── agent-badge.tsx
│   │   └── sidebar/
│   │       ├── sidebar.tsx
│   │       └── session-list.tsx
│   │
│   ├── lib/
│   │   ├── api.ts                      # FastAPI client
│   │   ├── utils.ts
│   │   └── hooks/
│   │       ├── use-chat.ts
│   │       └── use-sessions.ts
│   │
│   └── types/
│       └── index.ts
│
├── terraform/                          # Infrastructure
│   ├── main.tf                         # LocalStack resources
│   ├── variables.tf
│   └── outputs.tf
│
└── scripts/
    ├── setup.sh                        # Initial setup
    ├── seed-knowledge.py               # Load sample docs
    └── setup-pgvector.sql              # DB schema
```

---

## Running the Project

### Development Mode

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Backend
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --port 8000

# Terminal 3: Start Frontend
cd frontend
npm run dev

# Access:
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### With Docker Compose (Full Stack)

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_HOST=http://host.docker.internal:11434
      - LOCALSTACK_ENDPOINT=http://localstack.local
      - REDIS_URL=redis://redis-sentinel.redis-sentinel:6379
    depends_on:
      - ollama

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Agent routing accuracy | >90% correct agent selection |
| Response latency (p95) | <5 seconds |
| Knowledge retrieval relevance | >80% relevant context |
| Session persistence | 100% history recovery |
| System availability | 99%+ uptime |
| Frontend performance (LCP) | <2.5 seconds |
| Mobile responsive | Works on all screen sizes |

---

**Document Version:** 1.1  
**Created:** January 30, 2026  
**Updated:** January 30, 2026 - Added Next.js frontend architecture  
**Status:** Ready for Implementation
