#!/bin/bash
# Initialize DynamoDB tables in ScyllaDB from a Kubernetes pod
# This script creates a temporary pod with the Python script and runs it

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Initializing DynamoDB tables in ScyllaDB Alternator..."

# Create a temporary pod with Python and aioboto3
kubectl run -n localstack init-tables-temp \
  --image=python:3.11-slim \
  --rm -i --restart=Never -- \
  bash -c "
    pip install -q aioboto3 structlog && \
    cat > /tmp/init.py << 'SCRIPT_EOF'
$(cat "$SCRIPT_DIR/init_dynamodb_tables.py")
SCRIPT_EOF
    python3 /tmp/init.py
  "

echo "✅ Initialization complete!"
