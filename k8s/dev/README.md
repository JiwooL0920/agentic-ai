# Skaffold Development Workflow

Hot-reload development inside Kubernetes cluster with native service connectivity.

## Prerequisites

Install Skaffold:
```bash
# macOS
brew install skaffold

# Or download from: https://skaffold.dev/docs/install/
```

## Add to /etc/hosts

```bash
echo "127.0.0.1 api.local" | sudo tee -a /etc/hosts
```

## Usage

### Start Development Mode

```bash
skaffold dev
```

This will:
1. Build the Docker image
2. Deploy to your Kind cluster
3. Sync Python file changes automatically (no rebuild!)
4. Port-forward API to `localhost:8001`
5. Stream logs to your terminal

### File Sync

Any changes to `packages/core/src/**/*.py` will sync instantly to the running pod.
Uvicorn's `--reload` flag will auto-restart on file changes.

### Access Services

**Inside the cluster**, your app uses native ClusterIP services:
- ScyllaDB: `http://scylla-client.scylla.svc.cluster.local:8000`
- Redis: `redis-sentinel.redis-sentinel.svc.cluster.local:6379`
- PostgreSQL: `postgres-rw.database.svc.cluster.local:5432`

**From your machine**:
- API: `http://api.local` or `http://localhost:8001`
- API Docs: `http://api.local/docs`

### Debug Mode

```bash
# Run once without continuous sync
skaffold run

# Clean up deployment
skaffold delete
```

## Benefits Over Local Development

✅ **Native service connectivity** - No port-forwards needed
✅ **Real cluster environment** - Test with actual DNS, networking
✅ **Hot reload** - Python files sync instantly
✅ **Fast feedback** - See changes in seconds
✅ **Production-like** - Same config as production deployment

## Workflow

1. Edit code in your IDE
2. Save file
3. Skaffold syncs to pod (< 1 second)
4. Uvicorn detects change and reloads (< 2 seconds)
5. Test at `http://api.local/docs`

No manual rebuild/redeploy needed!

## Ollama Configuration

Ollama runs on your Mac (for direct GPU/Neural Engine access) and is accessed from the cluster via `host.docker.internal`:

```yaml
# In deployment.yaml
OLLAMA_HOST: "http://host.docker.internal:11434"
```

Ensure Ollama is running before starting the cluster:
```bash
# Start Ollama
ollama serve

# Verify models are available
ollama list
# Should show: qwen2.5:7b, qwen2.5:32b
```
