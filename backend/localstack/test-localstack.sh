#!/bin/bash
# ============================================================================
# Test LocalStack for nexus-backend (Linux/macOS)
# ============================================================================
# Verifies LocalStack is running and all resources are properly configured.
# ============================================================================

set -e

ENDPOINT="${LOCALSTACK_ENDPOINT:-http://localhost:4566}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PASSED=0
FAILED=0

echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  Testing nexus-backend LocalStack${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""
echo "Endpoint: $ENDPOINT"
echo "Region:   $REGION"
echo ""

# Test function
test_check() {
    local name="$1"
    local result="$2"
    
    if [ "$result" = "0" ]; then
        echo -e "  ${GREEN}✓${NC} $name"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${RED}✗${NC} $name"
        FAILED=$((FAILED + 1))
    fi
}

# Test LocalStack health
echo -e "${YELLOW}Testing LocalStack Health...${NC}"
if curl -s "$ENDPOINT/_localstack/health" | grep -q '"dynamodb"'; then
    test_check "LocalStack health endpoint" 0
else
    test_check "LocalStack health endpoint" 1
fi

# Test DynamoDB
echo ""
echo -e "${YELLOW}Testing DynamoDB...${NC}"
if aws dynamodb describe-table \
    --endpoint-url "$ENDPOINT" \
    --region "$REGION" \
    --table-name "TransformationSystem" \
    2>/dev/null | grep -q "TransformationSystem"; then
    test_check "TransformationSystem table exists" 0
else
    test_check "TransformationSystem table exists" 1
fi

# Test GSI1 index
if aws dynamodb describe-table \
    --endpoint-url "$ENDPOINT" \
    --region "$REGION" \
    --table-name "TransformationSystem" \
    2>/dev/null | grep -q "GSI1"; then
    test_check "GSI1 index exists" 0
else
    test_check "GSI1 index exists" 1
fi

# Test S3 buckets
echo ""
echo -e "${YELLOW}Testing S3 Buckets...${NC}"
for bucket in "transformation-journey-logs" "transformation-journey-reports" "nexus-dev-wxcc-recordings" "nexus-dev-wxcc-transcripts" "nexus-dev-wxcc-simulator"; do
    if aws s3 ls "s3://$bucket" \
        --endpoint-url "$ENDPOINT" \
        --region "$REGION" \
        2>/dev/null; then
        test_check "S3 bucket: $bucket" 0
    else
        test_check "S3 bucket: $bucket" 1
    fi
done

# Test CloudWatch log groups
echo ""
echo -e "${YELLOW}Testing CloudWatch Log Groups...${NC}"
for log_group in "/aws/nexus-backend/api" "/aws/nexus-backend/jobs"; do
    if aws logs describe-log-groups \
        --endpoint-url "$ENDPOINT" \
        --region "$REGION" \
        --log-group-name-prefix "$log_group" \
        2>/dev/null | grep -q "$log_group"; then
        test_check "Log group: $log_group" 0
    else
        test_check "Log group: $log_group" 1
    fi
done

# Summary
echo ""
echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  Test Summary${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""
echo -e "  ${GREEN}Passed:${NC} $PASSED"
echo -e "  ${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Run ./localstack/localstack-init.sh to fix.${NC}"
    exit 1
fi
