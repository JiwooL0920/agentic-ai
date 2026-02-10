#!/bin/bash
# Cleanup Kind cluster disk space
# Run this before rebuilding if you encounter disk space errors

set -e

CLUSTER_NAME="${1:-dev-services-amer}"

echo "🧹 Cleaning up Kind cluster: $CLUSTER_NAME"
echo ""

# Function to clean a node
cleanup_node() {
    local node=$1
    echo "📦 Cleaning node: $node"
    
    # Remove unused images
    echo "  - Removing unused images..."
    docker exec "$node" crictl rmi --prune 2>/dev/null || true
    
    # Check disk space after cleanup
    local usage=$(docker exec "$node" df -h / | grep overlay | awk '{print $5}')
    echo "  ✅ Disk usage after cleanup: $usage"
    echo ""
}

# Get all nodes in the cluster
NODES=$(kind get nodes --name "$CLUSTER_NAME" 2>/dev/null || echo "")

if [ -z "$NODES" ]; then
    echo "❌ Cluster '$CLUSTER_NAME' not found"
    exit 1
fi

# Clean each node
for node in $NODES; do
    cleanup_node "$node"
done

# Also clean up Docker build cache
echo "🔨 Cleaning Docker build cache..."
docker builder prune -af --filter "until=24h" || true

# Show summary
echo ""
echo "📊 Docker System Summary:"
docker system df

echo ""
echo "✅ Cleanup complete!"
