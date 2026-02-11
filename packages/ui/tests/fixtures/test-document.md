# Kubernetes Deployment Guide

This is a comprehensive guide for deploying applications to Kubernetes.

## Prerequisites

Before deploying to Kubernetes, ensure you have:
- kubectl installed and configured
- Access to a Kubernetes cluster
- Docker images built and pushed to a registry

## Deployment Steps

### 1. Create a Deployment YAML

Create a file named `deployment.yaml` with your application configuration:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: my-registry/my-app:latest
        ports:
        - containerPort: 8080
```

### 2. Apply the Deployment

Apply your deployment configuration to the cluster:

```bash
kubectl apply -f deployment.yaml
```

### 3. Verify the Deployment

Check that your pods are running:

```bash
kubectl get pods
kubectl describe deployment my-app
```

## Troubleshooting

If your pods are not starting, check the logs:

```bash
kubectl logs <pod-name>
kubectl describe pod <pod-name>
```

## Best Practices

- Use resource limits and requests
- Implement health checks (liveness and readiness probes)
- Use namespaces for isolation
- Enable RBAC for security
- Use ConfigMaps and Secrets for configuration
