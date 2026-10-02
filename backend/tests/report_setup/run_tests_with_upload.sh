#!/bin/bash
#
# Run Tests with CloudFront Upload
# This script ensures environment is loaded and AWS credentials are valid
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Run Tests with CloudFront Upload                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo

# Step 1: Check AWS credentials
echo -e "${BLUE}Step 1: Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not valid or expired${NC}"
    echo
    echo -e "${YELLOW}Please refresh your credentials:${NC}"
    echo "  aws sso login"
    echo "  # OR"
    echo "  aws configure"
    exit 1
fi
echo -e "${GREEN}✅ AWS credentials valid${NC}"
echo

# Step 2: Load CloudFront environment
echo -e "${BLUE}Step 2: Loading CloudFront environment...${NC}"
source "$SCRIPT_DIR/load_cloudfront_env.sh"
echo

# Step 3: Verify environment
echo -e "${BLUE}Step 3: Verifying environment...${NC}"
if [ "$UPLOAD_TO_S3" != "true" ]; then
    echo -e "${RED}❌ UPLOAD_TO_S3 not set correctly${NC}"
    exit 1
fi

if [ -z "$S3_BUCKET_NAME" ]; then
    echo -e "${RED}❌ S3_BUCKET_NAME not set${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment loaded:${NC}"
echo "   UPLOAD_TO_S3: $UPLOAD_TO_S3"
echo "   S3_BUCKET_NAME: $S3_BUCKET_NAME"
echo "   CLOUDFRONT_DOMAIN: $CLOUDFRONT_DOMAIN"
echo "   S3_REGION: $S3_REGION"
echo

# Step 4: Run tests
echo -e "${BLUE}Step 4: Running tests with automatic upload...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

cd "$PROJECT_ROOT"

# Pass any arguments to run_tests.sh
./tests/run_tests.sh "${1:-unit}"

echo
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  ✅ COMPLETE                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo
echo "If upload was successful, view your reports at:"
echo "  https://d37vwg02pj6oqg.cloudfront.net/index.html"
echo

