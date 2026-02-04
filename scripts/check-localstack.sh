#!/usr/bin/env bash
# Check LocalStack resources
# Usage: ./scripts/check-localstack.sh [dynamodb|s3|all]

set -e

LOCALSTACK_ENDPOINT="http://localstack.local"
AWS_REGION="us-east-1"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_dynamodb() {
    echo -e "${BLUE}=== DynamoDB Tables ===${NC}"
    echo ""
    
    # List all tables
    echo -e "${GREEN}Available tables:${NC}"
    aws dynamodb list-tables \
        --endpoint-url "$LOCALSTACK_ENDPOINT" \
        --region "$AWS_REGION" \
        --output table
    
    echo ""
    
    # Check devassist tables
    for table in "devassist-sessions" "devassist-history"; do
        echo -e "${GREEN}Table: $table${NC}"
        aws dynamodb describe-table \
            --table-name "$table" \
            --endpoint-url "$LOCALSTACK_ENDPOINT" \
            --region "$AWS_REGION" \
            --query 'Table.[TableName,TableStatus,ItemCount,KeySchema,GlobalSecondaryIndexes]' \
            --output table 2>/dev/null || echo "Table not found"
        echo ""
    done
}

check_s3() {
    echo -e "${BLUE}=== S3 Buckets ===${NC}"
    echo ""
    
    # List all buckets
    echo -e "${GREEN}Available buckets:${NC}"
    aws s3 ls \
        --endpoint-url "$LOCALSTACK_ENDPOINT" \
        --region "$AWS_REGION"
    
    echo ""
    
    # Check devassist buckets
    for bucket in "devassist-documents" "devassist-knowledge"; do
        echo -e "${GREEN}Bucket: $bucket${NC}"
        aws s3api head-bucket \
            --bucket "$bucket" \
            --endpoint-url "$LOCALSTACK_ENDPOINT" \
            --region "$AWS_REGION" 2>/dev/null \
            && echo "✓ Bucket exists" \
            || echo "✗ Bucket not found"
        
        # Show versioning status
        aws s3api get-bucket-versioning \
            --bucket "$bucket" \
            --endpoint-url "$LOCALSTACK_ENDPOINT" \
            --region "$AWS_REGION" 2>/dev/null
        
        echo ""
    done
}

check_kubernetes() {
    echo -e "${BLUE}=== Kubernetes Resources ===${NC}"
    echo ""
    
    # Check ServiceMonitor
    echo -e "${GREEN}ServiceMonitor:${NC}"
    kubectl get servicemonitor devassist-monitor -n monitoring -o wide 2>/dev/null \
        || echo "ServiceMonitor not found"
    
    echo ""
    
    # Check ConfigMap (Grafana Dashboard)
    echo -e "${GREEN}Grafana Dashboard ConfigMap:${NC}"
    kubectl get configmap devassist-dashboard -n monitoring -o wide 2>/dev/null \
        || echo "ConfigMap not found"
    
    echo ""
}

# Main
case "${1:-all}" in
    dynamodb)
        check_dynamodb
        ;;
    s3)
        check_s3
        ;;
    k8s|kubernetes)
        check_kubernetes
        ;;
    all)
        check_dynamodb
        echo ""
        check_s3
        echo ""
        check_kubernetes
        ;;
    *)
        echo "Usage: $0 [dynamodb|s3|kubernetes|all]"
        exit 1
        ;;
esac

echo -e "${YELLOW}Tip: You can also access LocalStack directly at $LOCALSTACK_ENDPOINT${NC}"
