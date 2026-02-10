# Kubernetes-Native Development Setup

This setup allows you to develop **inside your Kind cluster** with hot-reload, using native ClusterIP service connectivity.

## ✅ Benefits

- **No port-forwards needed** - Use native `*.svc.cluster.local` DNS
- **Hot-reload** - File changes sync instantly (< 1 second)
- **Production-like** - Test with real cluster networking
- **Fast feedback** - See changes in ~2 seconds
- **Native service access** - Direct ClusterIP connectivity

## 📋 Prerequisites

### 1. Install Skaffold

```bash
brew install skaffold
```

### 2. Add `/etc/hosts` entry

```bash
echo "127.0.0.1 api.local" | sudo tee -a /etc/hosts
```

### 3. Ensure Kind cluster is running

```bash
kubectl cluster-info
```

## 🚀 Quick Start

```bash
make dev-k8s
```

This will:
1. Build the Docker image
2. Deploy to Kind cluster namespace `agentic-ai`
3. Enable file sync for `packages/core/src/**/*.py`
4. Port-forward API to `localhost:8001`
5. Stream logs to your terminal

## 🔌 Service Connectivity

### Inside Cluster (Production-like)

Your app uses **native Kubernetes DNS**:

```bash
# ScyllaDB Alternator
http://scylla-client.scylla.svc.cluster.local:8000

# Redis Sentinel
redis-sentinel.redis-sentinel.svc.cluster.local:6379

# PostgreSQL
postgres-rw.database.svc.cluster.local:5432
```

### From Your Machine

```bash
# API
http://api.local
http://localhost:8001

# API Docs
http://api.local/docs
```

## 🔄 Development Workflow

1. **Edit code** in your IDE
2. **Save file**
3. Skaffold syncs to pod (< 1s)
4. Uvicorn auto-reloads (< 2s)
5. **Test** at `http://api.local/docs`

No manual rebuild/redeploy!

## 📂 What Gets Synced

```yaml
packages/core/src/**/*.py  → /app/src/
packages/core/**/*.yaml    → /app/
```

Changes to these files trigger instant sync + reload.

## 🛠️ Commands

```bash
# Start development
make dev-k8s

# Stop (Ctrl+C in terminal)

# Or manually:
skaffold dev      # Start with hot-reload
skaffold run      # Deploy once (no sync)
skaffold delete   # Clean up deployment
```

## 🐛 Debugging

### Check pod status
```bash
kubectl get pods -n agentic-ai
```

### View logs
```bash
kubectl logs -f -n agentic-ai -l app=agentic-ai-core
```

### Shell into pod
```bash
kubectl exec -it -n agentic-ai deployment/agentic-ai-core -- /bin/bash
```

### Test service connectivity
```bash
# From inside the pod
kubectl exec -it -n agentic-ai deployment/agentic-ai-core -- \
  curl http://scylla-client.scylla.svc.cluster.local:8000/
```

## 🆚 Local vs Kubernetes Development

| Aspect | Local (`make dev-backend`) | Kubernetes (`make dev-k8s`) |
|--------|----------------------------|------------------------------|
| **Service Access** | Port-forwards required | Native ClusterIP |
| **DNS** | localhost | Real Kubernetes DNS |
| **Networking** | Host network | Pod network |
| **Environment** | Local machine | Real cluster |
| **Hot Reload** | ✅ Yes | ✅ Yes (file sync) |
| **Speed** | ⚡ Fastest | ⚡ Very fast (~2s) |
| **Production Parity** | ❌ Low | ✅ High |

## 📝 Configuration Files

- `skaffold.yaml` - Skaffold configuration
- `k8s/dev/deployment.yaml` - Kubernetes manifests
- `packages/core/Dockerfile.dev` - Development Dockerfile

## 💡 Tips

1. **Edit `.env`** changes require pod restart:
   ```bash
   kubectl rollout restart -n agentic-ai deployment/agentic-ai-core
   ```

2. **Dependency changes** require image rebuild (Ctrl+C and restart)

3. **View all services**:
   ```bash
   kubectl get svc --all-namespaces
   ```

4. **Test connectivity** from your pod:
   ```bash
   kubectl exec -it -n agentic-ai deployment/agentic-ai-core -- \
     python -c "import socket; print(socket.gethostbyname('scylla-client.scylla.svc.cluster.local'))"
   ```

## 🎯 Recommended Workflow

Use **Kubernetes dev mode** (`make dev-k8s`) when:
- ✅ Testing service integrations
- ✅ Working on database/cache features
- ✅ Debugging networking issues
- ✅ Want production-like environment

Use **Local dev mode** (`make dev-backend`) when:
- ✅ Pure logic changes
- ✅ Fastest possible iteration
- ✅ Don't need cluster services
