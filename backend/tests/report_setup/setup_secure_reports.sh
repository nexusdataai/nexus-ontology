#!/bin/bash
#
# Quick Setup for Secure Test Reports with CloudFront + Private S3
# This script automates the entire setup process
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║   Secure Test Reports Setup (CloudFront + Private S3)       ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo

# Get configuration
read -p "Enter S3 bucket name (e.g., my-test-reports): " BUCKET_NAME
if [ -z "$BUCKET_NAME" ]; then
    echo -e "${RED}❌ Bucket name is required${NC}"
    exit 1
fi

read -p "Enter AWS region [us-east-1]: " REGION
REGION=${REGION:-us-east-1}

# Detect Python
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."

if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif [ -f "$PROJECT_ROOT/venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python"
else
    PYTHON="python3"
fi

echo
echo -e "${BLUE}Configuration:${NC}"
echo "  Bucket: $BUCKET_NAME"
echo "  Region: $REGION"
echo "  Python: $PYTHON"
echo

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"

if ! $PYTHON -c "import boto3" &> /dev/null; then
    echo -e "${YELLOW}⚠ boto3 not installed, installing...${NC}"
    $PYTHON -m pip install -q boto3
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "  Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies ready${NC}"
echo

# Run setup
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Setting up CloudFront + Private S3...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

CONFIG_FILE="cloudfront_config.json"

$PYTHON "$SCRIPT_DIR/setup_cloudfront_reports.py" \
    --bucket "$BUCKET_NAME" \
    --region "$REGION" \
    --output "$CONFIG_FILE"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Setup failed${NC}"
    exit 1
fi

echo
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Load configuration
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

CLOUDFRONT_DOMAIN=$(jq -r '.distribution_domain' "$CONFIG_FILE")
CLOUDFRONT_URL=$(jq -r '.cloudfront_url' "$CONFIG_FILE")

echo
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Your Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo "  S3 Bucket:       $BUCKET_NAME"
echo "  CloudFront URL:  $CLOUDFRONT_URL"
echo "  Region:          $REGION"
echo "  Config File:     $CONFIG_FILE"
echo

# Create environment setup script
ENV_SCRIPT="load_cloudfront_env.sh"
cat > "$ENV_SCRIPT" << EOF
#!/bin/bash
# CloudFront + S3 Environment Configuration
# Source this file to load environment variables

export S3_BUCKET_NAME="$BUCKET_NAME"
export CLOUDFRONT_DOMAIN="$CLOUDFRONT_DOMAIN"
export S3_REGION="$REGION"
export UPLOAD_TO_S3="true"

echo "✅ CloudFront environment loaded"
echo "   Bucket: \$S3_BUCKET_NAME"
echo "   Domain: \$CLOUDFRONT_DOMAIN"
EOF

chmod +x "$ENV_SCRIPT"

echo -e "${GREEN}✓ Environment script created: $ENV_SCRIPT${NC}"
echo

# Instructions
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Next Steps${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo -e "${YELLOW}⏱  Wait 10-15 minutes for CloudFront deployment to complete${NC}"
echo
echo "Then, to use:"
echo
echo "1. Load environment variables:"
echo -e "   ${GREEN}source $ENV_SCRIPT${NC}"
echo
echo "2. Run tests and upload reports:"
echo -e "   ${GREEN}./tests/run_tests.sh unit${NC}"
echo
echo "3. View reports at:"
echo -e "   ${GREEN}$CLOUDFRONT_URL/index.html${NC}"
echo
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Security Features${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo "✅ S3 bucket is PRIVATE (no public access)"
echo "✅ HTTPS enforced (TLS 1.2+)"
echo "✅ Global CDN for fast access"
echo "✅ Only CloudFront can access S3"
echo
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo -e "${GREEN}🎉 Your test reports are now secure!${NC}"
echo

