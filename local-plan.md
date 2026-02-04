# Agentic AI Platform - Local Implementation Plan

**Project:** Agentic AI - Scalable Multi-Agent Platform (Local POC)  
**Pattern:** AWS Bedrock Multi-Agent Supervisor (Adapted for Local)  
**Reference:** Company `genai-platform-agents-template` architecture  
**Frontend:** Next.js 14 (App Router) + shadcn/ui + Tailwind CSS  
**Backend:** FastAPI + agent-squad (awslabs) + Ollama  
**Infrastructure:** Kind cluster `dev-services-amer` (LocalStack, PostgreSQL, Redis)  
**Hardware:** Mac Studio M4 Max, 128GB RAM  
**Date:** January 30, 2026

---

## Executive Summary

A scalable multi-agent platform following the **Module-Blueprint pattern** from the company's `genai-platform-agents-template`. Each **blueprint** is a self-contained agent system with its own agents, knowledge base, and infrastructure.

### Key Adaptations from Company Pattern

| Company (AWS Bedrock) | This Project (Local) |
|----------------------|---------------------|
| Bedrock Agents | Ollama + agent-squad (awslabs) |
| Lambda Action Groups | FastAPI endpoints |
| OpenSearch Serverless | PostgreSQL + pgvector |
| Bedrock Knowledge Bases | Custom RAG with pgvector |
| S3/DynamoDB (AWS) | S3/DynamoDB (LocalStack) |
| Terraform → AWS | Terraform → LocalStack + K8s |

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Module Reference](#module-reference)
4. [Blueprint Reference](#blueprint-reference)
5. [Phase 1: Core Setup](#phase-1-core-setup)
6. [Phase 2: Terraform Modules](#phase-2-terraform-modules)
7. [Phase 3: Backend (FastAPI)](#phase-3-backend-fastapi)
8. [Phase 4: Frontend (Next.js)](#phase-4-frontend-nextjs)
9. [Phase 5: First Blueprint (DevAssist)](#phase-5-first-blueprint-devassist)
10. [Phase 6: RAG & Knowledge Base](#phase-6-rag--knowledge-base)
11. [Phase 7: Evaluation Framework](#phase-7-evaluation-framework)
12. [Phase 8: Guardrails & Safety](#phase-8-guardrails--safety)
13. [Creating New Blueprints](#creating-new-blueprints)
14. [Implementation Checklist](#implementation-checklist)

---

## Architecture Overview

### Module-Blueprint Pattern

Following the company's architecture, this repo uses the **Module-Blueprint** pattern:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         MODULE-BLUEPRINT ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  MODULES (Building Blocks) - terraform/modules/                                  │
│  ══════════════════════════════════════════════                                  │
│  • Single-purpose, reusable components                                           │
│  • No environment-specific configuration                                         │
│  • Can be published to artifact repository later                                 │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  module "sessions" {                                                     │    │
│  │    source = "../../../terraform/modules/dynamodb"                        │    │
│  │    table_name = "${var.blueprint_name}-sessions"                         │    │
│  │    # Only takes generic inputs                                           │    │
│  │  }                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  BLUEPRINTS (Compositions) - blueprints/<name>/                                  │
│  ══════════════════════════════════════════════                                  │
│  • Combine modules for specific use cases                                        │
│  • Include environment configuration                                             │
│  • Define agent YAML definitions                                                 │
│  • Ready to deploy                                                               │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  # blueprints/devassist/terraform/main.tf                                │    │
│  │  module "sessions" { source = "../../../terraform/modules/dynamodb" }    │    │
│  │  module "documents" { source = "../../../terraform/modules/s3" }         │    │
│  │  module "monitoring" {                                                   │    │
│  │    source = "../../../terraform/modules/observability"                   │    │
│  │    # Module composition with data flow                                   │    │
│  │  }                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          AGENTIC AI PLATFORM                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  SHARED CORE (packages/)                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │    │
│  │  │  Agent   │ │Orchestr- │ │   API    │ │ Storage  │ │   RAG    │     │    │
│  │  │  Base    │ │  ator    │ │ Routes   │ │ Adapters │ │ Engine   │     │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │    │
│  │  ┌──────────┐ ┌──────────┐                                            │    │
│  │  │   UI     │ │   CLI    │  All shared, reusable across blueprints   │    │
│  │  │  Shell   │ │  Tools   │                                            │    │
│  │  └──────────┘ └──────────┘                                            │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                       │                                          │
│  TERRAFORM MODULES (terraform/modules/)                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │    │
│  │  │dynamodb│ │   s3   │ │pgvector│ │ redis  │ │observ- │ │ lambda │    │    │
│  │  │        │ │        │ │        │ │        │ │ability │ │        │    │    │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │    │
│  │  Reusable modules called by blueprint terraform/                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                       │                                          │
│  BLUEPRINTS (blueprints/)                                                        │
│  ┌────────────────────────┐    ┌────────────────────────┐                       │
│  │  devassist/            │    │  music-studio/         │                       │
│  │  ┌──────────────────┐  │    │  ┌──────────────────┐  │                       │
│  │  │ agents/          │  │    │  │ agents/          │  │                       │
│  │  │ ├─ kubernetes    │  │    │  │ ├─ guitar        │  │                       │
│  │  │ ├─ terraform     │  │    │  │ ├─ piano         │  │                       │
│  │  │ ├─ python        │  │    │  │ ├─ drums         │  │                       │
│  │  │ └─ architect     │  │    │  │ └─ producer      │  │                       │
│  │  ├──────────────────┤  │    │  ├──────────────────┤  │                       │
│  │  │ terraform/       │  │    │  │ terraform/       │  │                       │
│  │  │ (calls modules)  │  │    │  │ (calls modules)  │  │                       │
│  │  ├──────────────────┤  │    │  ├──────────────────┤  │                       │
│  │  │ knowledge/       │  │    │  │ knowledge/       │  │                       │
│  │  │ (blueprint docs) │  │    │  │ (music theory)   │  │                       │
│  │  └──────────────────┘  │    │  └──────────────────┘  │                       │
│  └────────────────────────┘    └────────────────────────┘                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Infrastructure (Kind Cluster)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Kind Cluster: dev-services-amer (3 nodes, k8s v1.31.0)                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ✅ LocalStack 4.13.1    → http://localstack.local (S3, DynamoDB, Lambda)       │
│  ✅ PostgreSQL (CNPG)    → pgvector for RAG                                     │
│  ✅ Redis Sentinel       → Session cache                                         │
│  ✅ Temporal             → Workflow orchestration (future)                       │
│  ✅ Prometheus/Grafana   → Monitoring                                            │
│  ✅ Traefik              → Ingress routing                                       │
│  ⏸️  Crossplane          → Future IaC migration                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

Following the company's `genai-platform-agents-template` structure:

```
agentic-ai/
│
├── 📁 .github/                         # CI/CD (future)
│   └── workflows/
│
├── 📁 terraform/                       # REUSABLE TERRAFORM MODULES
│   │
│   ├── modules/                        # Single-purpose modules
│   │   ├── dynamodb/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   │
│   │   ├── s3/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   │
│   │   ├── pgvector/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── schema.sql
│   │   │
│   │   ├── observability/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── dashboards/
│   │   │       └── agent-metrics.json
│   │   │
│   │   └── README.md                   # Auto-generated docs
│   │
│   └── shared/                         # Shared provider config
│       ├── provider.tf                 # LocalStack provider
│       └── versions.tf
│
├── 📁 packages/                        # SHARED PYTHON/JS CODE
│   │
│   ├── core/                           # Python core library
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── agents/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py             # OllamaAgent base class
│   │   │   │   ├── registry.py         # Agent registry
│   │   │   │   └── factory.py          # Load agents from YAML
│   │   │   │
│   │   │   ├── orchestrator/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── classifier.py       # Query classification
│   │   │   │   ├── router.py           # Agent routing
│   │   │   │   └── supervisor.py       # Supervisor pattern
│   │   │   │
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── app.py              # FastAPI app factory
│   │   │   │   └── routes/
│   │   │   │       ├── chat.py
│   │   │   │       ├── sessions.py
│   │   │   │       └── health.py
│   │   │   │
│   │   │   ├── storage/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dynamodb.py         # Session storage
│   │   │   │   ├── s3.py               # Document storage
│   │   │   │   └── redis.py            # Caching
│   │   │   │
│   │   │   ├── knowledge/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── embeddings.py       # Ollama embeddings
│   │   │   │   ├── vectorstore.py      # pgvector interface
│   │   │   │   └── retriever.py        # RAG retrieval
│   │   │   │
│   │   │   └── cli/
│   │   │       ├── __init__.py
│   │   │       ├── main.py             # CLI entry point
│   │   │       └── create.py           # agentic create <blueprint>
│   │   │
│   │   └── tests/
│   │
│   ├── ui/                             # Next.js shared UI
│   │   ├── package.json
│   │   ├── next.config.js
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                # Blueprint selector
│   │   │   └── [blueprint]/
│   │   │       └── page.tsx            # Blueprint chat
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                     # shadcn/ui
│   │   │   └── chat/
│   │   │       ├── chat-container.tsx
│   │   │       ├── message-list.tsx
│   │   │       └── chat-input.tsx
│   │   │
│   │   └── lib/
│   │       ├── api.ts
│   │       └── hooks/
│   │           └── use-chat.ts
│   │
│   └── shared/
│       └── types/
│
├── 📁 blueprints/                      # BLUEPRINT IMPLEMENTATIONS
│   │
│   ├── devassist/                      # Full-stack dev assistant
│   │   ├── config.yaml                 # Blueprint configuration
│   │   │
│   │   ├── agents/                     # Agent definitions (YAML)
│   │   │   ├── kubernetes.yaml
│   │   │   ├── terraform.yaml
│   │   │   ├── python.yaml
│   │   │   ├── frontend.yaml
│   │   │   └── architect.yaml
│   │   │
│   │   ├── terraform/                  # Blueprint infrastructure
│   │   │   ├── main.tf                 # Calls shared modules
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   ├── Makefile
│   │   │   └── config/
│   │   │       ├── example/
│   │   │       │   └── tfvars.conf.example
│   │   │       └── dev/
│   │   │           └── tfvars.conf     # (gitignored)
│   │   │
│   │   ├── knowledge/                  # Blueprint-specific docs
│   │   │   └── .gitkeep
│   │   │
│   │   └── custom/                     # Custom Python (optional)
│   │       └── tools.py
│   │
│   └── music-studio/                   # Music assistant (future)
│       └── ...
│
├── 📁 evaluation/                      # AGENT EVALUATION (like company)
│   ├── tool_selection/
│   │   ├── evaluate.py
│   │   ├── scorers.py
│   │   ├── models.py
│   │   ├── params.yaml
│   │   └── data/
│   │       └── golden_set.json
│   │
│   └── retrieval/
│       └── ...
│
├── 📄 .pre-commit-config.yaml          # Pre-commit hooks
├── 📄 .gitignore
├── 📄 Makefile                         # Platform-wide commands
├── 📄 local-plan.md                    # This file
├── 📄 project-description.md           # DevAssist blueprint spec
└── 📄 README.md
```

---

## Module Reference

### Module Overview (terraform/modules/)

| Module | Purpose | Key Resources | Dependencies |
|--------|---------|---------------|--------------|
| `dynamodb` | Session/conversation storage | `aws_dynamodb_table` | None |
| `s3` | Document/knowledge storage | `aws_s3_bucket` | None |
| `pgvector` | Vector database setup | `null_resource` (SQL exec) | PostgreSQL |
| `observability` | Prometheus + Grafana | `ServiceMonitor`, `ConfigMap` | K8s |
| `redis` | Session caching | Redis config | Redis cluster |

### Module Standard Structure

Every module follows this structure (matching company pattern):

```
terraform/modules/<module-name>/
├── main.tf              # Main resource definitions
├── variables.tf         # Input variables with validation
├── outputs.tf           # Output values
├── versions.tf          # Provider version constraints (optional)
└── README.md            # Auto-generated documentation
```

### Configuration Layering Pattern

Following the company's 3-layer configuration approach:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CONFIGURATION LAYERING                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Layer 1: Module Defaults (terraform/modules/*/variables.tf)                     │
│  ───────────────────────────────────────────────────────────                     │
│  • Sensible defaults for all variables                                           │
│  • Generic, reusable across environments                                         │
│                                                                                  │
│  variable "billing_mode" {                                                       │
│    default = "PAY_PER_REQUEST"                                                   │
│  }                                                                               │
│                                                                                  │
│  Layer 2: Blueprint Defaults (blueprints/*/terraform/variables.tf)               │
│  ─────────────────────────────────────────────────────────────────               │
│  • Blueprint-specific defaults                                                   │
│  • Override module defaults                                                      │
│                                                                                  │
│  variable "blueprint_name" {                                                     │
│    default = "devassist"                                                         │
│  }                                                                               │
│                                                                                  │
│  Layer 3: Environment Config (blueprints/*/terraform/config/dev/tfvars.conf)     │
│  ────────────────────────────────────────────────────────────────────────────    │
│  • Environment-specific values                                                   │
│  • GITIGNORED - never committed                                                  │
│                                                                                  │
│  environment = "dev"                                                             │
│  localstack_endpoint = "http://localstack.local"                                 │
│                                                                                  │
│  Layer 4: Example Templates (config/example/*.example)                           │
│  ─────────────────────────────────────────────────────                           │
│  • Committed to git                                                              │
│  • Shows required variables                                                      │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Blueprint Reference

### Blueprint Standard Structure

Each blueprint follows this structure (matching company pattern):

```
blueprints/<blueprint-name>/
├── config.yaml              # Blueprint metadata
├── agents/                  # Agent YAML definitions
│   ├── <agent-1>.yaml
│   └── <agent-2>.yaml
├── terraform/               # Infrastructure
│   ├── main.tf              # Module composition
│   ├── variables.tf         # Blueprint inputs
│   ├── outputs.tf           # Blueprint outputs
│   ├── Makefile             # Deploy commands
│   └── config/
│       ├── example/
│       │   └── tfvars.conf.example
│       └── dev/             # (gitignored)
│           └── tfvars.conf
├── knowledge/               # RAG documents
│   └── .gitkeep
└── custom/                  # Custom code (optional)
    └── tools.py
```

### Available Blueprints

| Blueprint | Description | Agents | Status |
|-----------|-------------|--------|--------|
| `devassist` | Full-stack development assistant | K8s, Terraform, Python, Frontend, Architect | 🚧 In Progress |
| `music-studio` | Music learning assistant | Guitar, Piano, Drums, Producer | 📋 Planned |

---

## Phase 1: Core Setup

### 1.1 Prerequisites

```bash
# Already have (your cluster)
✅ Kind cluster dev-services-amer
✅ LocalStack at http://localstack.local
✅ PostgreSQL (CNPG)
✅ Redis Sentinel

# Install these
brew install ollama python@3.11 node pnpm terraform
```

### 1.2 Ollama Setup

```bash
# Start Ollama
ollama serve

# Pull models
ollama pull qwen2.5:32b        # Chat model (~19GB)
ollama pull nomic-embed-text   # Embedding model (~274MB)

# Verify
ollama list
```

### 1.3 Project Initialization

```bash
cd ~/Project/agentic-ai

# Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Initialize monorepo
pnpm init
```

---

## Phase 2: Terraform Modules

### 2.1 Shared Provider Config

**`terraform/shared/provider.tf`:**

```hcl
# LocalStack provider configuration
terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  access_key                  = "test"
  secret_key                  = "test"
  region                      = "us-east-1"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    dynamodb       = "http://localstack.local"
    s3             = "http://localstack.local"
    lambda         = "http://localstack.local"
    iam            = "http://localstack.local"
    sqs            = "http://localstack.local"
    sns            = "http://localstack.local"
    secretsmanager = "http://localstack.local"
  }
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "kind-dev-services-amer"
}
```

### 2.2 DynamoDB Module

**`terraform/modules/dynamodb/main.tf`:**

```hcl
resource "aws_dynamodb_table" "this" {
  name         = var.table_name
  billing_mode = var.billing_mode
  hash_key     = var.hash_key
  range_key    = var.range_key

  attribute {
    name = var.hash_key
    type = var.hash_key_type
  }

  dynamic "attribute" {
    for_each = var.range_key != null ? [1] : []
    content {
      name = var.range_key
      type = var.range_key_type
    }
  }

  dynamic "ttl" {
    for_each = var.ttl_attribute != null ? [1] : []
    content {
      attribute_name = var.ttl_attribute
      enabled        = true
    }
  }

  tags = var.tags
}
```

**`terraform/modules/dynamodb/variables.tf`:**

```hcl
variable "table_name" {
  description = "Name of the DynamoDB table"
  type        = string
}

variable "hash_key" {
  description = "Hash key for the table"
  type        = string
}

variable "hash_key_type" {
  description = "Type of hash key (S, N, B)"
  type        = string
  default     = "S"
}

variable "range_key" {
  description = "Range key for the table (optional)"
  type        = string
  default     = null
}

variable "range_key_type" {
  description = "Type of range key"
  type        = string
  default     = "N"
}

variable "billing_mode" {
  description = "Billing mode (PAY_PER_REQUEST or PROVISIONED)"
  type        = string
  default     = "PAY_PER_REQUEST"
}

variable "ttl_attribute" {
  description = "TTL attribute name (optional)"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags for the table"
  type        = map(string)
  default     = {}
}
```

**`terraform/modules/dynamodb/outputs.tf`:**

```hcl
output "table_name" {
  description = "Name of the created table"
  value       = aws_dynamodb_table.this.name
}

output "table_arn" {
  description = "ARN of the created table"
  value       = aws_dynamodb_table.this.arn
}
```

### 2.3 S3 Module

**`terraform/modules/s3/main.tf`:**

```hcl
resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  tags   = var.tags
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
```

**`terraform/modules/s3/variables.tf`:**

```hcl
variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "versioning_enabled" {
  description = "Enable versioning"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags for the bucket"
  type        = map(string)
  default     = {}
}
```

**`terraform/modules/s3/outputs.tf`:**

```hcl
output "bucket_id" {
  description = "Bucket ID"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "Bucket ARN"
  value       = aws_s3_bucket.this.arn
}
```

### 2.4 Observability Module

**`terraform/modules/observability/main.tf`:**

```hcl
# ServiceMonitor for Prometheus
resource "kubernetes_manifest" "service_monitor" {
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "${var.blueprint_name}-monitor"
      namespace = var.namespace
      labels = {
        blueprint = var.blueprint_name
      }
    }
    spec = {
      selector = {
        matchLabels = {
          app = var.blueprint_name
        }
      }
      endpoints = [{
        port     = "http"
        path     = "/metrics"
        interval = "30s"
      }]
    }
  }
}

# Grafana Dashboard ConfigMap
resource "kubernetes_config_map" "dashboard" {
  metadata {
    name      = "${var.blueprint_name}-dashboard"
    namespace = var.namespace
    labels = {
      grafana_dashboard = "1"
    }
  }

  data = {
    "${var.blueprint_name}.json" = templatefile(
      "${path.module}/dashboards/agent-metrics.json",
      { blueprint_name = var.blueprint_name }
    )
  }
}
```

---

## Phase 3: Backend (FastAPI)

### 3.1 Core Package Structure

**`packages/core/pyproject.toml`:**

```toml
[project]
name = "agentic-core"
version = "0.1.0"
description = "Core library for Agentic AI Platform"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "agent-squad>=0.1.0",  # awslabs multi-agent framework (has OllamaAgent)
    "ollama>=0.4.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "boto3>=1.35.0",
    "redis>=5.0.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "psycopg[binary]>=3.1.0",
    "pgvector>=0.2.0",
    "python-multipart>=0.0.6",
    "pyyaml>=6.0.0",
    "structlog>=24.0.0",
    "prometheus-client>=0.19.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]

[project.scripts]
agentic = "agentic_core.cli.main:app"
```

### 3.2 Base Agent Class (Ollama-based)

**`packages/core/src/agents/base.py`:**

```python
"""
Base OllamaAgent class - replaces AWS Bedrock Agent for local execution.

NOTE: agent-squad (awslabs) has a built-in OllamaAgent in cookbook/examples.
This custom implementation extends it with our YAML-loading pattern.
See: https://github.com/awslabs/agent-squad/blob/main/docs/src/content/docs/cookbook/examples/ollama-agent.mdx

Company Pattern Adaptation:
- Bedrock Agent → OllamaAgent with agent-squad
- Action Groups → FastAPI endpoints with tool functions
- Knowledge Base → pgvector RAG
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, AsyncIterable
import ollama

from agent_squad.agents import Agent, AgentOptions
from agent_squad.types import ConversationMessage, ParticipantRole


@dataclass
class AgentConfig:
    """Agent configuration loaded from YAML (like company's prompts/)"""
    name: str
    agent_id: str
    description: str
    model_id: str = "qwen2.5:32b"
    system_prompt: str = ""
    temperature: float = 0.7
    tools: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_scope: List[str] = field(default_factory=list)
    icon: str = "🤖"
    color: str = "gray-500"


@dataclass 
class OllamaAgentOptions(AgentOptions):
    """Options for Ollama-based agents"""
    model_id: str = "qwen2.5:32b"
    streaming: bool = False
    temperature: float = 0.7
    system_prompt: Optional[str] = None


class OllamaAgent(Agent):
    """
    Agent powered by local Ollama models.
    Equivalent to company's Bedrock Agent but runs locally.
    """
    
    def __init__(self, options: OllamaAgentOptions):
        super().__init__(options)
        self.model_id = options.model_id
        self.streaming = options.streaming
        self.temperature = options.temperature
        self.system_prompt = options.system_prompt
    
    async def process_request(
        self,
        input_text: str,
        user_id: str,
        session_id: str,
        chat_history: List[ConversationMessage],
        additional_params: Optional[Dict[str, str]] = None
    ) -> ConversationMessage | AsyncIterable[Any]:
        """Process request using Ollama"""
        
        messages = []
        
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        for msg in chat_history:
            messages.append({
                "role": msg.role,
                "content": msg.content[0]["text"] if msg.content else ""
            })
        
        messages.append({
            "role": ParticipantRole.USER.value,
            "content": input_text
        })
        
        response = ollama.chat(
            model=self.model_id,
            messages=messages,
            options={"temperature": self.temperature}
        )
        
        return ConversationMessage(
            role=ParticipantRole.ASSISTANT.value,
            content=[{"text": response["message"]["content"]}]
        )
```

### 3.3 Agent Factory (Load from YAML)

**`packages/core/src/agents/factory.py`:**

```python
"""
Factory to create agents from YAML definitions.
Mirrors company's pattern of loading agent configurations.
"""
import yaml
from pathlib import Path
from typing import Dict

from .base import OllamaAgent, OllamaAgentOptions, AgentConfig


def load_agent_from_yaml(yaml_path: Path) -> OllamaAgent:
    """Load agent from YAML file (like company's prompts/)"""
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    
    return OllamaAgent(OllamaAgentOptions(
        name=config["name"],
        description=config["description"],
        model_id=config.get("model", "qwen2.5:32b"),
        system_prompt=config.get("system_prompt", ""),
        temperature=config.get("temperature", 0.7),
        streaming=config.get("streaming", False),
    ))


def load_blueprint_agents(blueprint_path: Path) -> Dict[str, OllamaAgent]:
    """Load all agents for a blueprint"""
    agents = {}
    agents_dir = blueprint_path / "agents"
    
    if not agents_dir.exists():
        return agents
    
    for yaml_file in agents_dir.glob("*.yaml"):
        agent = load_agent_from_yaml(yaml_file)
        agents[agent.name] = agent
    
    return agents
```

### 3.4 Supervisor Pattern (Multi-Agent Orchestration)

**`packages/core/src/orchestrator/supervisor.py`:**

```python
"""
Supervisor pattern - equivalent to company's SUPERVISOR_ROUTER mode.

Company Pattern:
- aws_bedrockagent_agent.agent_collaboration = "SUPERVISOR"
- aws_bedrockagent_agent_collaborator resources

Local Adaptation:
- agent-squad (awslabs) with OllamaAgents
- Routing based on agent YAML definitions
"""
from typing import Dict, List, Optional
from agent_squad.orchestrator import AgentSquad
from agent_squad.classifiers import ClassifierResult

from ..agents.base import OllamaAgent


class SupervisorOrchestrator:
    """
    Supervisor that routes queries to collaborator agents.
    Mirrors company's multi-agent collaboration pattern.
    """
    
    def __init__(self, agents: Dict[str, OllamaAgent]):
        self.orchestrator = AgentSquad()
        self.agents = agents
        
        for agent in agents.values():
            self.orchestrator.add_agent(agent)
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        chat_history: Optional[List] = None
    ) -> dict:
        """
        Process query through supervisor → collaborator flow.
        
        Flow (like company's supervisor-instructions.txt):
        1. Analyze intent
        2. Route to appropriate collaborator
        3. Return response (optionally synthesize)
        """
        response = await self.orchestrator.route_request(
            user_input=query,
            user_id=user_id,
            session_id=session_id,
            additional_params={}
        )
        
        return {
            "response": response.output.content[0]["text"],
            "agent": response.metadata.agent_name,
            "session_id": session_id
        }
```

---

## Phase 4: Frontend (Next.js)

### 4.1 Package Setup

```bash
cd packages/ui
pnpm create next-app . --typescript --tailwind --eslint --app --src-dir=false

# Install shadcn/ui
pnpm dlx shadcn-ui@latest init

# Add components
pnpm dlx shadcn-ui@latest add button input card avatar badge scroll-area
```

### 4.2 Blueprint Selector

**`packages/ui/app/page.tsx`:**

```tsx
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import Link from "next/link";

const blueprints = [
  {
    slug: "devassist",
    name: "DevAssist",
    description: "Full-stack development assistant",
    agents: 5,
    icon: "💻",
  },
  {
    slug: "music-studio",
    name: "Music Studio",
    description: "AI music learning assistant",
    agents: 4,
    icon: "🎵",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-2">Agentic AI</h1>
        <p className="text-muted-foreground mb-8">
          Select a blueprint to start chatting with specialized AI agents
        </p>
        
        <div className="grid md:grid-cols-2 gap-4">
          {blueprints.map((bp) => (
            <Link key={bp.slug} href={`/${bp.slug}`}>
              <Card className="hover:border-primary transition-colors cursor-pointer">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <span className="text-4xl">{bp.icon}</span>
                    <div>
                      <CardTitle>{bp.name}</CardTitle>
                      <CardDescription>{bp.description}</CardDescription>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    {bp.agents} agents available
                  </p>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## Phase 5: First Blueprint (DevAssist)

### 5.1 Blueprint Configuration

**`blueprints/devassist/config.yaml`:**

```yaml
name: DevAssist
slug: devassist
description: Full-stack development assistant with specialized agents

theme:
  primary_color: blue
  
agents:
  - kubernetes
  - terraform
  - python
  - frontend
  - architect

default_agent: architect

knowledge_base:
  enabled: true
  vector_store: pgvector

api:
  port: 8001
```

### 5.2 Agent Definitions

**`blueprints/devassist/agents/kubernetes.yaml`:**

```yaml
name: KubernetesExpert
id: k8s-001
description: |
  Kubernetes specialist for cluster management, troubleshooting,
  manifest creation, Helm charts, and production best practices.

model: qwen2.5:32b
temperature: 0.7

system_prompt: |
  You are KubernetesExpert, a senior Kubernetes engineer with 10+ years 
  of experience managing production clusters at scale.
  
  ## Your Expertise
  - Cluster architecture and design
  - Workloads: Deployments, StatefulSets, DaemonSets, Jobs
  - Networking: Services, Ingress, NetworkPolicies
  - Storage: PV, PVC, StorageClasses
  - Security: RBAC, PodSecurityPolicies, Secrets
  - Troubleshooting: CrashLoopBackOff, OOMKilled, networking
  - Helm, Kustomize, GitOps (ArgoCD, FluxCD)
  
  ## Response Style
  1. Diagnose first - ask clarifying questions if needed
  2. Provide kubectl commands to investigate/fix
  3. Explain WHY something is happening
  4. Mention production best practices
  5. Format YAML and commands in code blocks

knowledge_scope:
  - k8s-docs
  - runbooks

icon: ☸️
color: blue-500
```

### 5.3 Blueprint Terraform

**`blueprints/devassist/terraform/main.tf`:**

```hcl
terraform {
  required_version = ">= 1.5.0"
}

variable "blueprint_name" {
  default = "devassist"
}

variable "environment" {
  default = "local"
}

locals {
  tags = {
    Blueprint   = var.blueprint_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Session Storage (LocalStack DynamoDB)
module "sessions" {
  source = "../../../terraform/modules/dynamodb"

  table_name    = "${var.blueprint_name}-sessions"
  hash_key      = "session_id"
  ttl_attribute = "expires_at"
  tags          = local.tags
}

# Conversation History
module "history" {
  source = "../../../terraform/modules/dynamodb"

  table_name     = "${var.blueprint_name}-history"
  hash_key       = "session_id"
  range_key      = "timestamp"
  range_key_type = "N"
  tags           = local.tags
}

# Document Storage (LocalStack S3)
module "documents" {
  source = "../../../terraform/modules/s3"

  bucket_name = "${var.blueprint_name}-documents"
  tags        = local.tags
}

# Knowledge Base Storage
module "knowledge" {
  source = "../../../terraform/modules/s3"

  bucket_name = "${var.blueprint_name}-knowledge"
  tags        = local.tags
}

# Observability
module "monitoring" {
  source = "../../../terraform/modules/observability"

  blueprint_name = var.blueprint_name
  namespace      = "monitoring"
  metrics_port   = 8001
}

# Outputs
output "dynamodb_tables" {
  value = {
    sessions = module.sessions.table_name
    history  = module.history.table_name
  }
}

output "s3_buckets" {
  value = {
    documents = module.documents.bucket_id
    knowledge = module.knowledge.bucket_id
  }
}
```

**`blueprints/devassist/terraform/Makefile`:**

```makefile
.PHONY: init plan apply destroy

ENV ?= dev

init:
	terraform init

plan:
	terraform plan -var-file=config/$(ENV)/tfvars.conf

apply:
	terraform apply -var-file=config/$(ENV)/tfvars.conf -auto-approve

destroy:
	terraform destroy -var-file=config/$(ENV)/tfvars.conf -auto-approve
```

---

## Phase 6: RAG & Knowledge Base

### 6.1 pgvector Setup

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blueprint VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    source_type VARCHAR(50),
    s3_key VARCHAR(500),
    agent_scope VARCHAR(50)[],
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Chunks table with embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),  -- nomic-embed-text dimension
    created_at TIMESTAMP DEFAULT NOW()
);

-- HNSW index for similarity search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Blueprint filter index
CREATE INDEX IF NOT EXISTS idx_documents_blueprint 
ON documents(blueprint);
```

---

## Phase 7: Evaluation Framework

Following the company's evaluation pattern with Weave + DVC:

### 7.1 Structure

```
evaluation/
├── tool_selection/
│   ├── evaluate.py          # Main evaluation runner
│   ├── scorers.py           # Custom scoring functions
│   ├── models.py            # Agent wrapper
│   ├── params.yaml          # Evaluation parameters
│   └── data/
│       └── golden_set.json  # Test cases
│
└── retrieval/
    └── ...
```

### 7.2 Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| **Precision** | Correct / Selected | How many selected agents were correct |
| **Recall** | Correct / Expected | How many expected agents were selected |
| **F1 Score** | 2×(P×R)/(P+R) | Harmonic mean |
| **Exact Match** | 1.0 if perfect | Perfect agent selection |

---

## Phase 8: Guardrails & Safety

Simulating **AWS Bedrock Guardrails** for local LLM safety and content filtering. This phase implements content moderation, PII detection, and safety controls equivalent to AWS Bedrock's guardrail functionality.

### 8.1 Guardrail Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GUARDRAIL PIPELINE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INPUT VALIDATION                                                            │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐     │
│  │    PII     │───▶│  Toxicity  │───▶│   Topic    │───▶│  Prompt    │     │
│  │ Detection  │    │   Check    │    │  Filter    │    │ Injection  │     │
│  │            │    │            │    │            │    │  Defense   │     │
│  └────────────┘    └────────────┘    └────────────┘    └────────────┘     │
│       ▲                  ▲                  ▲                  ▲            │
│       │                  │                  │                  │            │
│   presidio          detoxify         embeddings            rebuff          │
│                                                                              │
│                              USER INPUT                                      │
│                                   │                                          │
│                                   ▼                                          │
│                          ┌──────────────────┐                               │
│                          │   VALIDATION     │                               │
│                          │   PASS/BLOCK     │                               │
│                          └─────────┬────────┘                               │
│                                    │                                         │
│                                    ▼                                         │
│                          ┌──────────────────┐                               │
│                          │  AGENT PROCESS   │                               │
│                          └─────────┬────────┘                               │
│                                    │                                         │
│                                    ▼                                         │
│  OUTPUT VALIDATION                                                           │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐                        │
│  │    PII     │───▶│  Toxicity  │───▶│  Content   │                        │
│  │ Redaction  │    │   Check    │    │  Policy    │                        │
│  │            │    │            │    │            │                        │
│  └────────────┘    └────────────┘    └────────────┘                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Implementation Structure

```
packages/core/src/
├── guardrails/
│   ├── __init__.py
│   ├── base.py                    # GuardrailMiddleware base class
│   ├── config.py                  # GuardrailConfig (policies)
│   │
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── pii.py                 # PII detection with presidio
│   │   ├── toxicity.py            # Toxicity scoring with detoxify
│   │   ├── topics.py              # Topic/domain filtering
│   │   └── injection.py           # Prompt injection defense
│   │
│   ├── policies/
│   │   ├── __init__.py
│   │   ├── models.py              # Pydantic models
│   │   └── defaults.yaml          # Default guardrail policies
│   │
│   └── monitoring/
│       ├── __init__.py
│       ├── metrics.py             # Prometheus metrics
│       └── logger.py              # Violation logging
```

### 8.3 Core Components

#### GuardrailMiddleware

```python
# packages/core/src/guardrails/base.py
"""
Guardrail middleware for content filtering and safety.
Simulates AWS Bedrock Guardrails for local LLM execution.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
import structlog

from .validators.pii import PIIValidator
from .validators.toxicity import ToxicityValidator
from .validators.topics import TopicValidator
from .validators.injection import InjectionValidator

logger = structlog.get_logger()


class GuardrailAction(Enum):
    """Action to take when guardrail is triggered."""
    ALLOW = "allow"
    BLOCK = "block"
    REDACT = "redact"
    WARN = "warn"


@dataclass
class GuardrailResult:
    """Result of guardrail validation."""
    action: GuardrailAction
    violations: List[Dict[str, Any]]
    redacted_text: Optional[str] = None
    confidence: float = 1.0
    
    @property
    def is_allowed(self) -> bool:
        return self.action == GuardrailAction.ALLOW


class GuardrailMiddleware:
    """
    Middleware for content safety and filtering.
    
    Equivalent to AWS Bedrock Guardrails:
    - PII detection and redaction
    - Toxicity and harmful content filtering
    - Topic/domain restrictions
    - Prompt injection defense
    """
    
    def __init__(
        self,
        pii_enabled: bool = True,
        toxicity_enabled: bool = True,
        topic_filtering_enabled: bool = True,
        injection_defense_enabled: bool = True,
        toxicity_threshold: float = 0.7,
        allowed_topics: Optional[List[str]] = None,
    ):
        self.pii_validator = PIIValidator() if pii_enabled else None
        self.toxicity_validator = (
            ToxicityValidator(threshold=toxicity_threshold)
            if toxicity_enabled
            else None
        )
        self.topic_validator = (
            TopicValidator(allowed_topics=allowed_topics)
            if topic_filtering_enabled
            else None
        )
        self.injection_validator = (
            InjectionValidator() if injection_defense_enabled else None
        )
        
        logger.info(
            "guardrail_initialized",
            pii=pii_enabled,
            toxicity=toxicity_enabled,
            topics=topic_filtering_enabled,
            injection=injection_defense_enabled,
        )
    
    async def validate_input(self, text: str) -> GuardrailResult:
        """
        Validate user input before sending to agent.
        
        Checks:
        - PII detection (redact if found)
        - Toxicity/harmful content (block if high)
        - Topic filtering (block if off-topic)
        - Prompt injection attempts (block if detected)
        """
        violations = []
        redacted_text = text
        
        # 1. PII Detection & Redaction
        if self.pii_validator:
            pii_result = await self.pii_validator.validate(text)
            if pii_result.has_pii:
                violations.append({
                    "type": "pii",
                    "entities": pii_result.entities,
                    "action": "redacted",
                })
                redacted_text = pii_result.redacted_text
        
        # 2. Toxicity Check
        if self.toxicity_validator:
            toxicity_result = await self.toxicity_validator.validate(redacted_text)
            if toxicity_result.is_toxic:
                violations.append({
                    "type": "toxicity",
                    "score": toxicity_result.score,
                    "categories": toxicity_result.categories,
                })
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    violations=violations,
                    confidence=toxicity_result.score,
                )
        
        # 3. Topic Filtering
        if self.topic_validator:
            topic_result = await self.topic_validator.validate(redacted_text)
            if not topic_result.is_allowed:
                violations.append({
                    "type": "topic",
                    "detected_topic": topic_result.detected_topic,
                    "allowed_topics": topic_result.allowed_topics,
                })
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    violations=violations,
                    confidence=topic_result.confidence,
                )
        
        # 4. Prompt Injection Defense
        if self.injection_validator:
            injection_result = await self.injection_validator.validate(redacted_text)
            if injection_result.is_injection:
                violations.append({
                    "type": "injection",
                    "technique": injection_result.technique,
                    "confidence": injection_result.confidence,
                })
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    violations=violations,
                    confidence=injection_result.confidence,
                )
        
        # All checks passed
        action = GuardrailAction.REDACT if violations else GuardrailAction.ALLOW
        return GuardrailResult(
            action=action,
            violations=violations,
            redacted_text=redacted_text if violations else None,
        )
    
    async def validate_output(self, text: str) -> GuardrailResult:
        """
        Validate agent output before returning to user.
        
        Checks:
        - PII leakage (redact if found)
        - Toxicity in response (block if high)
        - Content policy violations
        """
        violations = []
        redacted_text = text
        
        # 1. PII Detection in output
        if self.pii_validator:
            pii_result = await self.pii_validator.validate(text)
            if pii_result.has_pii:
                violations.append({
                    "type": "pii_output",
                    "entities": pii_result.entities,
                })
                redacted_text = pii_result.redacted_text
        
        # 2. Toxicity in output
        if self.toxicity_validator:
            toxicity_result = await self.toxicity_validator.validate(redacted_text)
            if toxicity_result.is_toxic:
                violations.append({
                    "type": "toxicity_output",
                    "score": toxicity_result.score,
                })
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    violations=violations,
                    confidence=toxicity_result.score,
                )
        
        action = GuardrailAction.REDACT if violations else GuardrailAction.ALLOW
        return GuardrailResult(
            action=action,
            violations=violations,
            redacted_text=redacted_text if violations else None,
        )
```

#### PII Validator (presidio-analyzer)

```python
# packages/core/src/guardrails/validators/pii.py
"""
PII detection and redaction using Microsoft Presidio.
Industry-standard tool for PII detection (50+ entity types).
"""

from dataclasses import dataclass
from typing import List, Dict
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


@dataclass
class PIIResult:
    """PII detection result."""
    has_pii: bool
    entities: List[Dict[str, any]]
    redacted_text: str
    original_text: str


class PIIValidator:
    """
    PII detection using Microsoft Presidio.
    
    Detects: EMAIL, PHONE, SSN, CREDIT_CARD, PERSON, LOCATION,
             IP_ADDRESS, CRYPTO, IBAN, etc.
    """
    
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
    
    async def validate(self, text: str) -> PIIResult:
        """Detect and redact PII from text."""
        # Analyze for PII
        results = self.analyzer.analyze(
            text=text,
            language="en",
            entities=None,  # All entities
        )
        
        if not results:
            return PIIResult(
                has_pii=False,
                entities=[],
                redacted_text=text,
                original_text=text,
            )
        
        # Anonymize detected PII
        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators={
                "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
                "PERSON": OperatorConfig("replace", {"new_value": "[NAME]"}),
            },
        )
        
        entities = [
            {
                "type": result.entity_type,
                "start": result.start,
                "end": result.end,
                "score": result.score,
            }
            for result in results
        ]
        
        return PIIResult(
            has_pii=True,
            entities=entities,
            redacted_text=anonymized.text,
            original_text=text,
        )
```

#### Toxicity Validator (detoxify)

```python
# packages/core/src/guardrails/validators/toxicity.py
"""
Toxicity detection using detoxify (BERT-based).
Production-grade toxicity classifier trained on Jigsaw dataset.
"""

from dataclasses import dataclass
from typing import Dict
from detoxify import Detoxify


@dataclass
class ToxicityResult:
    """Toxicity detection result."""
    is_toxic: bool
    score: float
    categories: Dict[str, float]


class ToxicityValidator:
    """
    Toxicity detection using detoxify.
    
    Categories: toxicity, severe_toxicity, obscene, threat,
                insult, identity_attack, sexual_explicit
    """
    
    def __init__(self, threshold: float = 0.7):
        self.model = Detoxify("original")
        self.threshold = threshold
    
    async def validate(self, text: str) -> ToxicityResult:
        """Check text for toxic content."""
        results = self.model.predict(text)
        
        # Overall toxicity score
        toxicity_score = results["toxicity"]
        is_toxic = toxicity_score > self.threshold
        
        return ToxicityResult(
            is_toxic=is_toxic,
            score=toxicity_score,
            categories=results,
        )
```

### 8.4 Integration with OllamaAgent

```python
# packages/core/src/agents/base.py (updated)

class OllamaAgent(Agent):
    """Agent with guardrail support."""
    
    def __init__(self, options: OllamaAgentOptions, guardrails: Optional[GuardrailMiddleware] = None):
        super().__init__(options)
        # ... existing init ...
        self.guardrails = guardrails
    
    async def process_request(
        self,
        input_text: str,
        user_id: str,
        session_id: str,
        chat_history: List[ConversationMessage],
        additional_params: Optional[Dict[str, str]] = None,
    ) -> ConversationMessage | AsyncIterable[Any]:
        """Process request with guardrail validation."""
        
        # 1. Validate input
        if self.guardrails:
            input_validation = await self.guardrails.validate_input(input_text)
            
            if not input_validation.is_allowed:
                self._logger.warn(
                    "input_blocked",
                    violations=input_validation.violations,
                )
                return ConversationMessage(
                    role=ParticipantRole.ASSISTANT.value,
                    content=[{
                        "text": "I cannot process this request due to safety policies.",
                    }],
                )
            
            # Use redacted text if PII was found
            if input_validation.redacted_text:
                input_text = input_validation.redacted_text
        
        # 2. Process normally
        messages = self._build_messages(input_text, chat_history)
        
        if self.streaming:
            response_stream = self._handle_streaming_response(messages)
            # TODO: Stream through output validator
            return response_stream
        else:
            response = await self._handle_sync_response(messages)
            
            # 3. Validate output
            if self.guardrails:
                content = response.content[0].get("text", "")
                output_validation = await self.guardrails.validate_output(content)
                
                if not output_validation.is_allowed:
                    self._logger.warn(
                        "output_blocked",
                        violations=output_validation.violations,
                    )
                    return ConversationMessage(
                        role=ParticipantRole.ASSISTANT.value,
                        content=[{
                            "text": "Response blocked due to safety policies.",
                        }],
                    )
                
                # Use redacted output if needed
                if output_validation.redacted_text:
                    response.content[0]["text"] = output_validation.redacted_text
            
            return response
```

### 8.5 Configuration

```yaml
# blueprints/devassist/config.yaml (add guardrails section)
name: DevAssist
slug: devassist
description: Full-Stack Development Multi-Agent Assistant

# Guardrail policies
guardrails:
  enabled: true
  
  pii:
    enabled: true
    redact: true
    entities:
      - EMAIL_ADDRESS
      - PHONE_NUMBER
      - PERSON
      - SSN
      - CREDIT_CARD
  
  toxicity:
    enabled: true
    threshold: 0.7
    block_on_detection: true
  
  topics:
    enabled: false  # Disable for dev assistant (allow all topics)
    allowed:
      - software_development
      - infrastructure
      - programming
  
  injection_defense:
    enabled: true
    block_on_detection: true

agents:
  - kubernetes
  - terraform
  - python
  - frontend
  - architect
```

### 8.6 Dependencies

```toml
# packages/core/pyproject.toml (add guardrail dependencies)

[project]
dependencies = [
    # ... existing ...
    
    # Guardrails
    "presidio-analyzer>=2.2.0",      # PII detection (Microsoft)
    "presidio-anonymizer>=2.2.0",    # PII redaction
    "detoxify>=0.5.0",               # Toxicity detection
    "rebuff>=0.2.0",                 # Prompt injection defense
]
```

### 8.7 Monitoring

```python
# packages/core/src/guardrails/monitoring/metrics.py
"""Prometheus metrics for guardrail monitoring."""

from prometheus_client import Counter, Histogram

# Violation counters
guardrail_violations = Counter(
    "guardrail_violations_total",
    "Total guardrail violations",
    ["violation_type", "action", "agent"],
)

# Processing time
guardrail_validation_duration = Histogram(
    "guardrail_validation_duration_seconds",
    "Time spent validating with guardrails",
    ["validation_type"],  # input, output
)

# PII detections
pii_detections = Counter(
    "guardrail_pii_detections_total",
    "Total PII entities detected",
    ["entity_type", "agent"],
)
```

### 8.8 Testing

```python
# packages/core/tests/test_guardrails.py
"""Test suite for guardrail functionality."""

import pytest
from src.guardrails.base import GuardrailMiddleware, GuardrailAction


@pytest.fixture
def guardrails():
    return GuardrailMiddleware(
        pii_enabled=True,
        toxicity_enabled=True,
        toxicity_threshold=0.7,
    )


@pytest.mark.asyncio
async def test_pii_detection(guardrails):
    """Test PII detection and redaction."""
    text = "My email is john.doe@example.com and phone is 555-1234"
    result = await guardrails.validate_input(text)
    
    assert result.action in [GuardrailAction.ALLOW, GuardrailAction.REDACT]
    assert result.redacted_text != text
    assert "[EMAIL]" in result.redacted_text
    assert "[PHONE]" in result.redacted_text


@pytest.mark.asyncio
async def test_toxicity_blocking(guardrails):
    """Test toxicity detection blocks harmful content."""
    text = "You are a terrible person and I hate you"
    result = await guardrails.validate_input(text)
    
    if result.action == GuardrailAction.BLOCK:
        assert len(result.violations) > 0
        assert result.violations[0]["type"] == "toxicity"


@pytest.mark.asyncio
async def test_safe_content_allowed(guardrails):
    """Test safe content passes through."""
    text = "How do I fix OOMKilled in my Kubernetes pod?"
    result = await guardrails.validate_input(text)
    
    assert result.action == GuardrailAction.ALLOW
    assert len(result.violations) == 0
```

### 8.9 Comparison with AWS Bedrock Guardrails

| Feature | AWS Bedrock Guardrails | This Implementation |
|---------|------------------------|---------------------|
| **PII Detection** | ✅ Built-in (50+ entities) | ✅ Presidio (50+ entities) |
| **Toxicity Filtering** | ✅ AWS-managed models | ✅ Detoxify (BERT-based) |
| **Content Filtering** | ✅ Hate, violence, sexual | ✅ Detoxify categories |
| **Topic Filtering** | ✅ Custom topics | ✅ Embedding-based matching |
| **Prompt Injection** | ❌ Not included | ✅ Rebuff/llm-guard |
| **Custom Regex** | ✅ Supported | ✅ Easy to add |
| **Redaction** | ✅ Automatic | ✅ Presidio anonymizer |
| **Monitoring** | ✅ CloudWatch | ✅ Prometheus metrics |
| **Configuration** | ✅ YAML-based | ✅ YAML-based |
| **Cost** | 💰 Pay per use | ✅ Free (local) |

### 8.10 Industry Best Practices

This implementation follows industry-standard practices for local LLM safety:

1. **Microsoft Presidio**: Production-grade PII detection used by enterprises worldwide
2. **Detoxify**: BERT-based toxicity classifier, trained on Jigsaw Toxic Comment dataset (used by HuggingFace Spaces)
3. **Rebuff**: Open-source prompt injection defense framework
4. **Layered Defense**: Multiple validation layers (input + output)
5. **Configurable Policies**: YAML-based configuration per blueprint
6. **Observable**: Prometheus metrics for monitoring violations
7. **Testable**: Comprehensive test coverage

### 8.11 References

- [Microsoft Presidio](https://github.com/microsoft/presidio) - Enterprise PII detection
- [Detoxify](https://github.com/unitaryai/detoxify) - Toxicity classification
- [Rebuff](https://github.com/protectai/rebuff) - Prompt injection defense
- [AWS Bedrock Guardrails Docs](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html) - Original reference
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) - LLM security best practices

---

## Creating New Blueprints

### Manual Steps

1. **Create directory:**
   ```bash
   mkdir -p blueprints/music-studio/{agents,terraform/config/example,knowledge}
   ```

2. **Create config.yaml:**
   ```yaml
   name: Music Studio
   slug: music-studio
   description: AI music learning assistant
   theme:
     primary_color: purple
   agents:
     - guitar
     - piano
   ```

3. **Create agent YAMLs:**
   ```yaml
   # agents/guitar.yaml
   name: GuitarCoach
   description: Guitar instructor for technique and theory
   system_prompt: |
     You are GuitarCoach...
   ```

4. **Create terraform (copy from devassist):**
   ```bash
   cp -r blueprints/devassist/terraform/* blueprints/music-studio/terraform/
   # Update blueprint_name variable
   ```

5. **Deploy:**
   ```bash
   cd blueprints/music-studio/terraform
   make init && make apply
   ```

---

## Implementation Checklist

### Phase 0: Infrastructure (Done)
- [x] Kind cluster running
- [x] LocalStack at http://localstack.local
- [x] PostgreSQL available
- [x] Redis available

### Phase 1: Core Setup
- [ ] Install Ollama
- [ ] Pull models (qwen2.5:32b, nomic-embed-text)
- [ ] Initialize monorepo

### Phase 2: Terraform Modules
- [ ] Create `terraform/modules/dynamodb`
- [ ] Create `terraform/modules/s3`
- [ ] Create `terraform/modules/pgvector`
- [ ] Create `terraform/modules/observability`
- [ ] Create shared provider config

### Phase 3: Backend
- [ ] Create `packages/core/` structure
- [ ] Implement OllamaAgent base class
- [ ] Implement agent factory
- [ ] Implement FastAPI app factory
- [ ] Create API routes

### Phase 4: Frontend
- [ ] Create Next.js app in `packages/ui/`
- [ ] Install shadcn/ui
- [ ] Create blueprint selector
- [ ] Create chat components

### Phase 5: DevAssist Blueprint
- [ ] Create `blueprints/devassist/config.yaml`
- [ ] Create agent YAMLs
- [ ] Create blueprint terraform
- [ ] Deploy infrastructure

### Phase 6: RAG
- [ ] Setup pgvector schema
- [ ] Implement embedding generation
- [ ] Implement semantic search

### Phase 7: Evaluation
- [ ] Create evaluation framework structure
- [ ] Create golden test set
- [ ] Implement scorers

### Phase 8: Guardrails
- [ ] Install guardrail dependencies (presidio, detoxify, rebuff)
- [ ] Implement GuardrailMiddleware base class
- [ ] Implement PII validator with presidio
- [ ] Implement toxicity validator with detoxify
- [ ] Implement prompt injection defense
- [ ] Integrate with OllamaAgent
- [ ] Add guardrail configuration to blueprint config.yaml
- [ ] Add Prometheus metrics for violations
- [ ] Create test suite for guardrails

---

## Quick Start Commands

```bash
# 1. Start Ollama
ollama serve

# 2. Pull models (first time)
ollama pull qwen2.5:32b
ollama pull nomic-embed-text

# 3. Deploy blueprint infrastructure
cd blueprints/devassist/terraform
make init
make apply

# 4. Start backend
cd packages/core
source venv/bin/activate
uvicorn src.api.app:create_app --factory --reload --port 8001

# 5. Start frontend
cd packages/ui
pnpm dev

# Open:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8001/docs
# - Grafana: http://grafana.local
```

---

**Document Version:** 3.2  
**Created:** January 30, 2026  
**Updated:** February 3, 2026 - Added Phase 8: Guardrails & Safety (AWS Bedrock Guardrails simulation)  
**Status:** Ready for Implementation

---

## Context7 Library References

For up-to-date documentation, use these Context7 library IDs:

| Library | Context7 ID | Benchmark Score |
|---------|-------------|-----------------|
| Agent Squad (awslabs) | `/awslabs/agent-squad` | 71.0 |
| Ollama | `/ollama/ollama` | 70.1 |
| FastAPI | `/websites/fastapi_tiangolo` | 96.8 |
| Next.js | `/vercel/next.js` | 87.0 |
| pgvector | `/pgvector/pgvector` | 91.4 |
| shadcn/ui | `/websites/ui_shadcn` | 81.8 |
| Presidio (Microsoft) | `/microsoft/presidio` | N/A |
