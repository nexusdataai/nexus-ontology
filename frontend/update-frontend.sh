#!/bin/bash

# =============================================================================
# Quick Frontend Update Script
# Updates only the UI code without touching infrastructure
# =============================================================================
# Usage: ./update-frontend.sh <environment>
# Example: ./update-frontend.sh dev
#          ./update-frontend.sh stage
#          ./update-frontend.sh prod
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
CAPABILITY_NAME="call-processing"
REGION="${AWS_REGION:-us-east-1}"
CLOUDFRONT_REGION="us-east-1"  # CloudFront distributions are global, managed in us-east-1

# AWS Profile - use 'external-access' by default for local, empty for CI/CD
# Set AWS_PROFILE="none" to use environment credentials (GitHub Actions OIDC)
if [ -z "${AWS_PROFILE+x}" ]; then
    # AWS_PROFILE not set at all - use default for local development
    AWS_PROFILE="external-access"
elif [ "$AWS_PROFILE" = "none" ] || [ "$AWS_PROFILE" = "" ]; then
    # Explicitly set to empty or "none" - unset to use environment credentials
    unset AWS_PROFILE
fi

# Flag to track if we're using profile or environment credentials
USE_AWS_PROFILE="${AWS_PROFILE:-}"

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Show usage
usage() {
    cat << EOF
Usage: $(basename "$0") <environment> [options]

Update frontend code for a specific environment.

ENVIRONMENTS:
  dev     Deploy to call-dev.totogicore.com
  stage   Deploy to call-stage.totogicore.com  
  prod    Deploy to call.totogicore.com

OPTIONS:
  --skip-build       Skip npm build (use existing dist/)
  --skip-config      Skip config.json generation (use existing)
  --skip-invalidate  Skip CloudFront cache invalidation
  --profile NAME     AWS profile to use (default: external-access)
  --dry-run          Show what would be done without doing it
  -h, --help         Show this help message

EXAMPLES:
  $(basename "$0") dev                    # Full update to dev
  $(basename "$0") prod --skip-build      # Deploy existing build to prod
  $(basename "$0") dev --dry-run          # Preview dev deployment

EOF
}

# Parse arguments
ENVIRONMENT=""
SKIP_BUILD=false
SKIP_CONFIG=false
SKIP_INVALIDATE=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        dev|stage|prod|test)
            ENVIRONMENT="$1"
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-config)
            SKIP_CONFIG=true
            shift
            ;;
        --skip-invalidate)
            SKIP_INVALIDATE=true
            shift
            ;;
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate environment
if [ -z "$ENVIRONMENT" ]; then
    log_error "Environment not specified"
    usage
    exit 1
fi

# Set environment-specific values
case "$ENVIRONMENT" in
    dev)
        FRONTEND_DOMAIN="call-dev.totogicore.com"
        API_URL="https://call-api-dev.totogicore.com"
        ;;
    test)
        FRONTEND_DOMAIN="call-test.totogicore.com"
        API_URL="https://call-api-test.totogicore.com"
        ;;
    stage)
        FRONTEND_DOMAIN="call-stage.totogicore.com"
        API_URL="https://call-api-stage.totogicore.com"
        ;;
    prod)
        FRONTEND_DOMAIN="call.totogicore.com"
        API_URL="https://call-api.totogicore.com"
        ;;
    *)
        log_error "Invalid environment: $ENVIRONMENT"
        exit 1
        ;;
esac

S3_BUCKET="${CAPABILITY_NAME}-${ENVIRONMENT}-frontend"

# Get project root (directory where this script lives)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "=============================================="
echo "  Frontend Update: $ENVIRONMENT"
echo "=============================================="
echo "  Domain:     $FRONTEND_DOMAIN"
echo "  API URL:    $API_URL"
echo "  S3 Bucket:  $S3_BUCKET"
if [ -n "$USE_AWS_PROFILE" ]; then
    echo "  Auth:       AWS Profile ($USE_AWS_PROFILE)"
else
    echo "  Auth:       Environment credentials (OIDC)"
fi
echo "=============================================="
echo ""

# Verify AWS credentials
log_info "Verifying AWS credentials..."
if [ -n "$USE_AWS_PROFILE" ]; then
    # Use profile-based authentication (local deployment)
    if ! aws sts get-caller-identity --profile "$USE_AWS_PROFILE" > /dev/null 2>&1; then
        log_error "AWS credentials not valid. Run aws-login or configure credentials."
        exit 1
    fi
    AWS_CMD_PROFILE="--profile $USE_AWS_PROFILE"
else
    # Use environment-based authentication (GitHub Actions OIDC)
    log_info "Using environment credentials (AWS_ACCESS_KEY_ID set: $([ -n \"$AWS_ACCESS_KEY_ID\" ] && echo 'yes' || echo 'no'))"
    if ! aws sts get-caller-identity --region "$REGION" 2>&1; then
        log_error "AWS credentials not valid. Check OIDC configuration."
        exit 1
    fi
    AWS_CMD_PROFILE=""
fi
log_success "AWS credentials verified"

# Step 1: Build (optional)
if [ "$SKIP_BUILD" = false ]; then
    log_info "Building application..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would run: npm run build"
    else
        # Install dependencies if needed
        if [ ! -d "node_modules" ]; then
            log_info "Installing dependencies..."
            npm install
        fi
        
        npm run build
        
        if [ ! -d "dist" ]; then
            log_error "Build failed - dist directory not found"
            exit 1
        fi
        log_success "Build completed"
    fi
else
    log_info "Skipping build (--skip-build)"
    if [ ! -d "dist" ]; then
        log_error "dist directory not found. Remove --skip-build or run 'npm run build' first."
        exit 1
    fi
fi

# Step 2: Generate config.json (optional)
if [ "$SKIP_CONFIG" = false ]; then
    log_info "Generating config.json for $ENVIRONMENT..."
    
    CONFIG_CONTENT=$(cat << EOF
{
  "version": "1.0.0",
  "api": {
    "baseUrl": "$API_URL",
    "timeout": 30000
  },
  "dataSource": "api",
  "enableFallback": true
}
EOF
)
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would write config.json:"
        echo "$CONFIG_CONTENT" | head -10
        echo "..."
    else
        echo "$CONFIG_CONTENT" > dist/config.json
        log_success "config.json generated"
    fi
else
    log_info "Skipping config.json generation (--skip-config)"
fi

# Step 3: Sync to S3
log_info "Syncing to S3: s3://$S3_BUCKET/"

if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] Would run: aws s3 sync dist/ s3://$S3_BUCKET/ --delete $AWS_CMD_PROFILE"
else
    aws s3 sync dist/ "s3://$S3_BUCKET/" \
        --delete \
        $AWS_CMD_PROFILE \
        --cache-control "public, max-age=31536000" \
        --exclude "index.html" \
        --exclude "config.json"
    
    # Upload index.html and config.json with no-cache
    aws s3 cp dist/index.html "s3://$S3_BUCKET/index.html" \
        $AWS_CMD_PROFILE \
        --cache-control "no-cache, no-store, must-revalidate"
    
    aws s3 cp dist/config.json "s3://$S3_BUCKET/config.json" \
        $AWS_CMD_PROFILE \
        --cache-control "no-cache, no-store, must-revalidate"
    
    log_success "Files synced to S3"
fi

# Step 4: Invalidate CloudFront cache (optional)
if [ "$SKIP_INVALIDATE" = false ]; then
    log_info "Finding CloudFront distribution..."
    
    # Find CloudFront distribution by S3 bucket origin
    DISTRIBUTION_ID=$(aws cloudfront list-distributions \
        $AWS_CMD_PROFILE \
        --query "DistributionList.Items[?Origins.Items[?DomainName=='${S3_BUCKET}.s3.${REGION}.amazonaws.com' || DomainName=='${S3_BUCKET}.s3.amazonaws.com']].Id" \
        --output text 2>/dev/null || echo "")
    
    # Alternative: Find by alias (domain name)
    if [ -z "$DISTRIBUTION_ID" ] || [ "$DISTRIBUTION_ID" = "None" ]; then
        DISTRIBUTION_ID=$(aws cloudfront list-distributions \
            $AWS_CMD_PROFILE \
            --query "DistributionList.Items[?Aliases.Items[?contains(@, '$FRONTEND_DOMAIN')]].Id" \
            --output text 2>/dev/null || echo "")
    fi
    
    if [ -n "$DISTRIBUTION_ID" ] && [ "$DISTRIBUTION_ID" != "None" ]; then
        log_info "Found CloudFront distribution: $DISTRIBUTION_ID"
        
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] Would create invalidation for /*"
        else
            INVALIDATION_ID=$(aws cloudfront create-invalidation \
                --distribution-id "$DISTRIBUTION_ID" \
                --paths "/*" \
                $AWS_CMD_PROFILE \
                --query 'Invalidation.Id' \
                --output text)
            
            log_success "CloudFront invalidation created: $INVALIDATION_ID"
            log_info "Invalidation is in progress (usually takes 1-2 minutes)"
        fi
    else
        log_warning "CloudFront distribution not found. Skipping invalidation."
        log_warning "You may need to manually invalidate the cache."
    fi
else
    log_info "Skipping CloudFront invalidation (--skip-invalidate)"
fi

# Done!
echo ""
echo "=============================================="
if [ "$DRY_RUN" = true ]; then
    log_success "DRY RUN COMPLETE - No changes made"
else
    log_success "FRONTEND UPDATE COMPLETE!"
    echo ""
    echo "  URL: https://$FRONTEND_DOMAIN"
    echo ""
    echo "  Note: If you don't see changes immediately,"
    echo "        wait for CloudFront invalidation to complete"
    echo "        or clear your browser cache."
fi
echo "=============================================="
