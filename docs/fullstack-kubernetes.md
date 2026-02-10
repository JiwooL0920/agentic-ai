# Frontend + Backend Kubernetes Development

Both frontend and backend running in Kubernetes with hot-reload.

## Setup

### 1. Add DNS entries

```bash
echo "127.0.0.1 api.local app.local" | sudo tee -a /etc/hosts
```

### 2. Start full stack development

```bash
# Backend + Frontend in Kubernetes
make dev-k8s-full
```

**Or backend only:**
```bash
# Backend only (current setup)
make dev-k8s
```

## Access

### Backend + Frontend Mode (`make dev-k8s-full`)

- 🎨 **Frontend**: `http://app.local` or `http://localhost:3000`
- 🔧 **Backend API**: `http://api.local` or `http://localhost:8001`
- 📚 **API Docs**: `http://api.local/docs`

### Backend Only Mode (`make dev-k8s`)

- 🔧 **Backend API**: `http://api.local` or `http://localhost:8001`
- 📚 **API Docs**: `http://api.local/docs`

## Hot Reload

### Frontend (Next.js)
File changes in:
- `app/**/*`
- `components/**/*`
- `*.ts`, `*.tsx`, `*.js`

→ Syncs to pod instantly + Next.js auto-reloads

### Backend (Python)
File changes in:
- `src/**/*.py`
- `**/*.yaml`

→ Syncs to pod instantly + Uvicorn auto-reloads

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Kind Cluster                        │
│                                                  │
│  ┌──────────────┐         ┌──────────────┐     │
│  │   Frontend   │         │   Backend    │     │
│  │  (Next.js)   │────────>│  (FastAPI)   │     │
│  │              │         │              │     │
│  │ app.local    │         │ api.local    │     │
│  │ :3000        │         │ :8001        │     │
│  └──────────────┘         └──────────────┘     │
│         │                        │              │
│         └────────Native──────────┘              │
│              ClusterIP DNS                      │
│                                                  │
│  Frontend calls backend via:                    │
│  http://agentic-ai-core.agentic-ai.svc:8001    │
└─────────────────────────────────────────────────┘
         │                    │
         │                    │
    Port Forward          Port Forward
         │                    │
         ▼                    ▼
   localhost:3000       localhost:8001
```

## Benefits

✅ **Native service communication** - Frontend → Backend via ClusterIP
✅ **Hot reload** - Both stack auto-reload on changes
✅ **Production parity** - Real Kubernetes networking
✅ **Fast iteration** - Changes visible in ~2 seconds
✅ **No port-forwards needed** - Native DNS resolution

## Debugging

```bash
# Check pods
kubectl get pods -n agentic-ai

# View frontend logs
kubectl logs -f -n agentic-ai -l app=agentic-ai-ui

# View backend logs
kubectl logs -f -n agentic-ai -l app=agentic-ai-core

# Shell into frontend
kubectl exec -it -n agentic-ai deployment/agentic-ai-ui -- /bin/sh

# Shell into backend
kubectl exec -it -n agentic-ai deployment/agentic-ai-core -- /bin/bash
```

## Stop Development

Press `Ctrl+C` in the terminal running Skaffold.

Skaffold will automatically clean up all resources.
