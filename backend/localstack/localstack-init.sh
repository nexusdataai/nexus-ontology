#!/bin/bash
# ============================================================================
# LocalStack Initialization Script for nexus-backend
# ============================================================================
# This script initializes LocalStack with required AWS resources:
# - DynamoDB tables (TransformationSystem with GSI1)
# - S3 buckets (logs, reports, wxcc buckets)
# - CloudWatch log groups
#
# The script is idempotent - safe to run multiple times.
# ============================================================================

set -e

# Configuration
ENDPOINT="${LOCALSTACK_ENDPOINT:-http://localhost:4566}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  Initializing nexus-backend LocalStack${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""
echo "Endpoint: $ENDPOINT"
echo "Region:   $REGION"
echo ""

# Function to wait for LocalStack to be ready
wait_for_localstack() {
    echo -e "${YELLOW}Waiting for LocalStack to be ready...${NC}"
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$ENDPOINT/_localstack/health" | grep -q '"dynamodb"'; then
            echo -e "${GREEN}✓ LocalStack is ready${NC}"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts - waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ LocalStack failed to start within timeout${NC}"
    return 1
}

# Function to create DynamoDB table
create_dynamodb_table() {
    local table_name="$1"
    echo -e "${YELLOW}Creating DynamoDB table: $table_name...${NC}"
    
    # Check if table exists
    if aws dynamodb describe-table \
        --endpoint-url "$ENDPOINT" \
        --region "$REGION" \
        --table-name "$table_name" \
        2>/dev/null; then
        echo -e "  ${GREEN}Table already exists${NC}"
        return 0
    fi
    
    # Create table with GSI1
    aws dynamodb create-table \
        --endpoint-url "$ENDPOINT" \
        --region "$REGION" \
        --table-name "$table_name" \
        --attribute-definitions \
            AttributeName=PK,AttributeType=S \
            AttributeName=SK,AttributeType=S \
            AttributeName=GSI1PK,AttributeType=S \
            AttributeName=GSI1SK,AttributeType=S \
        --key-schema \
            AttributeName=PK,KeyType=HASH \
            AttributeName=SK,KeyType=RANGE \
        --global-secondary-indexes \
            '[{
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            }]' \
        --billing-mode PAY_PER_REQUEST \
        > /dev/null
    
    echo -e "  ${GREEN}✓ Table created${NC}"
}

# Function to create S3 bucket
create_s3_bucket() {
    local bucket_name="$1"
    echo -e "${YELLOW}Creating S3 bucket: $bucket_name...${NC}"
    
    if aws s3 ls "s3://$bucket_name" \
        --endpoint-url "$ENDPOINT" \
        --region "$REGION" \
        2>/dev/null; then
        echo -e "  ${GREEN}Bucket already exists${NC}"
        return 0
    fi
    
    aws s3 mb "s3://$bucket_name" \
        --endpoint-url "$ENDPOINT" \
        --region "$REGION" \
        > /dev/null 2>&1 || true
    
    echo -e "  ${GREEN}✓ Bucket created${NC}"
}

# Function to create CloudWatch log group
create_log_group() {
    local log_group="$1"
    echo -e "${YELLOW}Creating CloudWatch log group: $log_group...${NC}"
    
    aws logs create-log-group \
        --endpoint-url "$ENDPOINT" \
        --region "$REGION" \
        --log-group-name "$log_group" \
        2>/dev/null || echo -e "  ${GREEN}Log group already exists${NC}"
    
    echo -e "  ${GREEN}✓ Log group ready${NC}"
}

# Main initialization
main() {
    # Wait for LocalStack
    wait_for_localstack || exit 1
    
    echo ""
    echo -e "${CYAN}--- Creating DynamoDB Tables ---${NC}"
    create_dynamodb_table "TransformationSystem"
    create_dynamodb_table "call-processing-local-foundry-workspace"
    
    echo ""
    echo -e "${CYAN}--- Creating S3 Buckets ---${NC}"
    create_s3_bucket "transformation-journey-logs"
    create_s3_bucket "transformation-journey-reports"
    create_s3_bucket "nexus-dev-wxcc-recordings"
    create_s3_bucket "nexus-dev-wxcc-transcripts"
    create_s3_bucket "nexus-dev-wxcc-simulator"
    
    echo ""
    echo -e "${CYAN}--- Creating CloudWatch Log Groups ---${NC}"
    create_log_group "/aws/nexus-backend/api"
    create_log_group "/aws/nexus-backend/jobs"
    
    echo ""
    echo -e "${CYAN}==========================================${NC}"
    echo -e "${GREEN}  LocalStack initialization complete!${NC}"
    echo -e "${CYAN}==========================================${NC}"
    echo ""
    echo "Services available:"
    echo "  LocalStack Gateway: $ENDPOINT"
    echo "  DynamoDB Admin:     http://localhost:8001"
    echo ""
}

# Run main function
main "$@"
