# Agentic AI Platform

A scalable multi-agent AI platform following the **Module-Blueprint pattern**, powered by [Ollama](https://ollama.ai) and [agent-squad](https://github.com/awslabs/agent-squad) (awslabs).

## Quick Start

### Prerequisites

**Required:**
- Python 3.11+ (`brew install python@3.11`)
- Node.js 20+ (`brew install node`)
- Terraform 1.5+ (`brew install terraform`)

**Auto-installed by setup:**
- pnpm (installed via npm if missing)
- Python virtual environment (created at `./venv`)

**Required for full functionality:**
- [Ollama](https://ollama.ai) (`brew install ollama` or download from website)
- Kind cluster `dev-services-amer` with LocalStack (for infrastructure)

**Hardware:**
- Mac Studio M4 Max (or similar with 32GB+ RAM for running qwen2.5:32b)

**Note:** The setup will automatically create a Python virtual environment at `./venv` to comply with PEP 668.

### One-Time Setup

```bash
# 1. Clone and navigate to the repository
cd /path/to/agentic-ai

# 2. Install all dependencies (creates venv, installs packages)
make setup

# 3. Start Ollama and pull models (~19GB download)
make ollama-start
make ollama-pull

# 4. Deploy infrastructure to LocalStack
make blueprint-deploy NAME=devassist
```

### Daily Development

```bash
# Start both backend and frontend (single command)
# The backend automatically uses the virtual environment
make dev

# Or start individually:
make dev-backend   # FastAPI on port 8001 (uses venv)
make dev-frontend  # Next.js on port 3000

# Optional: Real-time GPU metrics (Mac only, requires sudo)
make dev-gpu-metrics  # Metrics server on port 8002
```

### Access the Platform

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8001/docs
- **GPU Metrics:** http://localhost:8002/gpu (if running `make dev-gpu-metrics`)
- **Grafana:** http://grafana.local (if configured)

### Verify Setup

```bash
# Check Ollama status
make ollama-status

# Test Ollama models
make ollama-test

# Run tests
make test
```

### Manual Virtual Environment Activation

If you need to run Python commands manually (outside of Make targets):

```bash
# Activate the virtual environment
source venv/bin/activate

# Now you can run Python commands
python --version
pip list

# Deactivate when done
deactivate
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENTIC AI PLATFORM                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  SHARED CORE (packages/)                                     │
│  ├── core/          Python backend (FastAPI + agent-squad)  │
│  └── ui/            Next.js frontend (shadcn/ui)            │
│                                                              │
│  TERRAFORM MODULES (terraform/modules/)                      │
│  ├── dynamodb       Session/history storage                 │
│  ├── s3             Document/knowledge storage              │
│  ├── pgvector       Vector database schema                  │
│  └── observability  Prometheus + Grafana                    │
│                                                              │
│  BLUEPRINTS (blueprints/)                                    │
│  └── devassist/     Full-stack development assistant        │
│      ├── agents/    Agent YAML definitions                  │
│      ├── terraform/ Blueprint infrastructure                │
│      └── knowledge/ RAG documents                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
agentic-ai/
├── packages/
│   ├── core/                 # Python backend
│   │   ├── src/
│   │   │   ├── agents/       # OllamaAgent, factory, registry
│   │   │   ├── orchestrator/ # Supervisor pattern
│   │   │   └── api/          # FastAPI routes
│   │   └── pyproject.toml
│   │
│   └── ui/                   # Next.js frontend
│       ├── app/              # App Router pages
│       └── components/       # shadcn/ui components
│
├── terraform/
│   ├── modules/              # Reusable Terraform modules
│   └── shared/               # Provider configuration
│
├── blueprints/
│   └── devassist/            # Development assistant blueprint
│       ├── agents/           # Agent YAML definitions
│       ├── terraform/        # Blueprint infrastructure
│       └── config.yaml       # Blueprint configuration
│
└── evaluation/               # Agent evaluation framework
```

## DevAssist Agents

| Agent | Expertise | Icon |
|-------|-----------|------|
| KubernetesExpert | Cluster management, troubleshooting, Helm | ☸️ |
| TerraformExpert | IaC, AWS, modules, state management | 🏗️ |
| PythonExpert | FastAPI, async, testing, code quality | 🐍 |
| FrontendExpert | React, Next.js, TypeScript, Tailwind | ⚛️ |
| SystemArchitect | Architecture patterns, design decisions | 🏛️ |

## Creating a New Blueprint

```bash
# 1. Create blueprint structure
make blueprint-init NAME=music-studio

# 2. Edit config.yaml and add agents
vim blueprints/music-studio/config.yaml
vim blueprints/music-studio/agents/guitar.yaml

# 3. Copy and customize terraform files from devassist
cp blueprints/devassist/terraform/main.tf blueprints/music-studio/terraform/
# Edit to match your blueprint name

# 4. Deploy infrastructure
make blueprint-deploy NAME=music-studio
```

## Common Commands

### Ollama Management

```bash
make ollama-status   # Check status and list models
make ollama-start    # Start Ollama server
make ollama-stop     # Stop Ollama server
make ollama-pull     # Pull required models
make ollama-test     # Test connection and models
make ollama-models   # List installed models
```

### Development

```bash
make dev             # Start all servers
make dev-backend     # Backend only
make dev-frontend    # Frontend only
```

### Code Quality

```bash
make lint            # Run linters
make format          # Format code
make test            # Run tests
make check           # All checks (lint + type + test)
```

### Blueprint Management

```bash
make blueprint-list                 # List all blueprints
make blueprint-init NAME=<name>     # Create new blueprint
make blueprint-deploy NAME=<name>   # Deploy infrastructure
make blueprint-destroy NAME=<name>  # Destroy infrastructure
```

### Cleanup

```bash
make clean           # Clean build artifacts
make clean-all       # Deep clean (includes node_modules)
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| LLM Runtime | Ollama (qwen2.5:32b) |
| Multi-Agent Framework | agent-squad (awslabs) |
| Backend | FastAPI + Python 3.11 |
| Frontend | Next.js 14 + shadcn/ui |
| Vector DB | PostgreSQL + pgvector |
| AWS Emulation | LocalStack |
| IaC | Terraform |
| Cluster | Kind (dev-services-amer) |

## Troubleshooting

### Ollama Issues

```bash
# Check if Ollama is running
make ollama-status

# View Ollama logs
make ollama-logs

# Restart Ollama
make ollama-stop
make ollama-start
```

### Backend Issues

```bash
# Check backend logs
cd packages/core
make dev

# Run with debug logging
make dev-debug
```

### Frontend Issues

```bash
# Clear Next.js cache
cd packages/ui
make clean-cache
make dev
```

### LocalStack Issues

```bash
# Check LocalStack is accessible
curl http://localstack.local/_localstack/health

# Redeploy blueprint infrastructure
make blueprint-destroy NAME=devassist
make blueprint-deploy NAME=devassist
```

## Project Documentation

- **`local-plan.md`** - Complete implementation plan and architecture
- **`project-description.md`** - DevAssist blueprint specification
- **`terraform/modules/README.md`** - Terraform module documentation

## License

MIT
