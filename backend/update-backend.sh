#!/bin/bash

# =============================================================================
# Quick Backend Update Script
# Builds Docker image, pushes to ECR, and updates ECS service
# =============================================================================
# Usage: ./update-backend.sh <environment>
# Example: ./update-backend.sh dev
#          ./update-backend.sh prod --skip-build
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load environment from .env.local if it exists
if [ -f ".env.local" ]; then
    echo -e "${BLUE}Loading configuration from .env.local...${NC}"
    # Export all variables from .env.local (skip comments and empty lines)
    set -a
    source <(grep -v '^#' .env.local | grep -v '^$' | sed 's/\r$//')
    set +a
fi

# Configuration - defaults will be overridden by .env.local if present
CAPABILITY_NAME="call-processing"
IMAGE_NAME="ai-job-engine"
AWS_REGION="${AWS_REGION:-us-east-1}"

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
log_header() { echo -e "\n${PURPLE}═══════════════════════════════════════════════════${NC}"; echo -e "${PURPLE}  $1${NC}"; echo -e "${PURPLE}═══════════════════════════════════════════════════${NC}"; }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "\n${CYAN}▶ $1${NC}"; }

# Show usage
usage() {
    cat << EOF
Usage: $(basename "$0") <environment> [options]

Build and deploy backend to a specific environment.

ENVIRONMENTS:
  dev     Deploy to call-processing-dev
  test    Deploy to call-processing-test
  stage   Deploy to call-processing-stage
  prod    Deploy to call-processing-prod

OPTIONS:
  --skip-build       Skip Docker build (just update ECS with existing image)
  --no-cache         Force Docker rebuild without cache (use after Dockerfile changes)
  --skip-scan        Skip security scanning during build
  --skip-test        Skip image testing during build
  --profile NAME     AWS profile to use (default: external-access)
  --region REGION    AWS region (default: us-east-1)
  --tag TAG          Docker image tag (default: latest)
  --force            Force new deployment even if image unchanged
  --wait             Wait for deployment to complete
  --dry-run          Show what would be done without doing it
  -h, --help         Show this help message

EXAMPLES:
  $(basename "$0") dev                    # Full build and deploy to dev
  $(basename "$0") dev --no-cache         # Rebuild without Docker cache (after Dockerfile changes)
  $(basename "$0") prod --skip-build      # Deploy existing image to prod
  $(basename "$0") dev --skip-scan        # Build without security scan
  $(basename "$0") dev --wait             # Deploy and wait for completion

EOF
}

# Parse arguments
ENVIRONMENT=""
SKIP_BUILD=false
NO_CACHE=false
SKIP_SCAN=false
SKIP_TEST=false
FORCE_DEPLOY=false
WAIT_DEPLOY=false
DRY_RUN=false
TAG="latest"

while [[ $# -gt 0 ]]; do
    case "$1" in
        dev|test|stage|prod)
            ENVIRONMENT="$1"
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --skip-scan)
            SKIP_SCAN=true
            shift
            ;;
        --skip-test)
            SKIP_TEST=true
            shift
            ;;
        --profile)
            USE_AWS_PROFILE="$2"
            AWS_PROFILE="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --force)
            FORCE_DEPLOY=true
            shift
            ;;
        --wait)
            WAIT_DEPLOY=true
            shift
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
ECS_CLUSTER="${CAPABILITY_NAME}-${ENVIRONMENT}-cluster"
ECS_SERVICE="${CAPABILITY_NAME}-${ENVIRONMENT}-service"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_header "Backend Update: $ENVIRONMENT"
echo ""
echo "  Environment:  $ENVIRONMENT"
echo "  ECS Cluster:  $ECS_CLUSTER"
echo "  ECS Service:  $ECS_SERVICE"
echo "  Image:        $IMAGE_NAME:$TAG"
if [ -n "$USE_AWS_PROFILE" ]; then
    echo "  AWS Profile:  $USE_AWS_PROFILE"
else
    echo "  AWS Auth:     Environment credentials (OIDC)"
fi
echo "  AWS Region:   $AWS_REGION"
echo "  Skip Build:   $SKIP_BUILD"
echo "  No Cache:     $NO_CACHE"
echo ""

# Verify AWS credentials
log_step "Verifying AWS credentials..."
if [ -n "$USE_AWS_PROFILE" ]; then
    # Use profile-based authentication (local deployment)
    if ! aws sts get-caller-identity --profile "$USE_AWS_PROFILE" > /dev/null 2>&1; then
        log_error "AWS credentials not valid. Run aws-login or configure credentials."
        exit 1
    fi
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile "$USE_AWS_PROFILE" --query Account --output text)
    AWS_CMD_PROFILE="--profile $USE_AWS_PROFILE"
else
    # Use environment-based authentication (GitHub Actions OIDC)
    log_info "Using environment credentials (AWS_ACCESS_KEY_ID set: $([ -n \"$AWS_ACCESS_KEY_ID\" ] && echo 'yes' || echo 'no'))"
    if ! aws sts get-caller-identity --region "$AWS_REGION" > /dev/null 2>&1; then
        log_error "AWS credentials not valid. Check OIDC configuration."
        exit 1
    fi
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_CMD_PROFILE=""
fi
log_success "AWS credentials verified (Account: $AWS_ACCOUNT_ID)"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Step 1: Build and push Docker image (optional)
if [ "$SKIP_BUILD" = false ]; then
    log_step "Building and pushing Docker image..."
    
    BUILD_ARGS=""
    [ "$NO_CACHE" = true ] && BUILD_ARGS="$BUILD_ARGS --no-cache"
    [ "$SKIP_SCAN" = true ] && BUILD_ARGS="$BUILD_ARGS --no-scan"
    [ "$SKIP_TEST" = true ] && BUILD_ARGS="$BUILD_ARGS --no-test"
    # Pass profile to build.sh - use "none" for OIDC credentials
    if [ -n "$USE_AWS_PROFILE" ]; then
        BUILD_ARGS="$BUILD_ARGS --profile $USE_AWS_PROFILE"
    else
        BUILD_ARGS="$BUILD_ARGS --profile none"
    fi
    BUILD_ARGS="$BUILD_ARGS --region $AWS_REGION"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would run: ./build.sh $TAG $BUILD_ARGS"
    else
        if [ -f "./build.sh" ]; then
            chmod +x ./build.sh
            ./build.sh "$TAG" $BUILD_ARGS
            log_success "Docker image built and pushed"
        else
            log_error "build.sh not found in $SCRIPT_DIR"
            exit 1
        fi
    fi
else
    log_info "Skipping build (--skip-build)"
    log_info "Will use existing image: ${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}"
fi

# Step 2: Verify ECS cluster and service exist
log_step "Verifying ECS cluster and service..."

if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] Would verify cluster: $ECS_CLUSTER"
    log_info "[DRY-RUN] Would verify service: $ECS_SERVICE"
else
    # Check cluster
    if ! aws ecs describe-clusters --clusters "$ECS_CLUSTER" $AWS_CMD_PROFILE --region "$AWS_REGION" --query "clusters[0].status" --output text 2>/dev/null | grep -q "ACTIVE"; then
        log_error "ECS cluster not found or not active: $ECS_CLUSTER"
        exit 1
    fi
    log_success "ECS cluster found: $ECS_CLUSTER"
    
    # Check service
    SERVICE_STATUS=$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" $AWS_CMD_PROFILE --region "$AWS_REGION" --query "services[0].status" --output text 2>/dev/null || echo "NOT_FOUND")
    if [ "$SERVICE_STATUS" != "ACTIVE" ]; then
        log_error "ECS service not found or not active: $ECS_SERVICE (status: $SERVICE_STATUS)"
        exit 1
    fi
    log_success "ECS service found: $ECS_SERVICE"
fi

# Step 3: Update ECS service to force new deployment
log_step "Updating ECS service..."

if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] Would run: aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE --force-new-deployment"
else
    # Force new deployment
    aws ecs update-service \
        --cluster "$ECS_CLUSTER" \
        --service "$ECS_SERVICE" \
        --force-new-deployment \
        $AWS_CMD_PROFILE \
        --region "$AWS_REGION" \
        --output text \
        --query 'service.deployments[0].id' > /dev/null
    
    log_success "ECS service update triggered"
    
    # Get deployment info
    DEPLOYMENT_INFO=$(aws ecs describe-services \
        --cluster "$ECS_CLUSTER" \
        --services "$ECS_SERVICE" \
        $AWS_CMD_PROFILE \
        --region "$AWS_REGION" \
        --query "services[0].deployments[?status=='PRIMARY'].[id,runningCount,desiredCount,rolloutState]" \
        --output text)
    
    log_info "Deployment: $DEPLOYMENT_INFO"
fi

# Step 4: Wait for deployment (optional)
if [ "$WAIT_DEPLOY" = true ] && [ "$DRY_RUN" = false ]; then
    log_step "Waiting for deployment to complete..."
    log_info "This may take 2-5 minutes..."
    
    # Wait for service to stabilize
    if aws ecs wait services-stable \
        --cluster "$ECS_CLUSTER" \
        --services "$ECS_SERVICE" \
        $AWS_CMD_PROFILE \
        --region "$AWS_REGION" 2>/dev/null; then
        log_success "Deployment completed successfully!"
    else
        log_warning "Deployment may still be in progress. Check AWS Console."
    fi
    
    # Show final status
    FINAL_STATUS=$(aws ecs describe-services \
        --cluster "$ECS_CLUSTER" \
        --services "$ECS_SERVICE" \
        $AWS_CMD_PROFILE \
        --region "$AWS_REGION" \
        --query "services[0].deployments[0].[status,runningCount,desiredCount]" \
        --output text)
    log_info "Final status: $FINAL_STATUS"
fi

# Done!
log_header "Backend Update Complete!"

if [ "$DRY_RUN" = true ]; then
    log_success "DRY RUN - No changes made"
else
    echo ""
    echo "  ✅ Image:    ${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}"
    echo "  ✅ Cluster:  $ECS_CLUSTER"
    echo "  ✅ Service:  $ECS_SERVICE"
    echo ""
    
    if [ "$WAIT_DEPLOY" = false ]; then
        log_info "Deployment is in progress. To check status:"
        echo ""
        echo "  aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE \\"
        if [ -n "$USE_AWS_PROFILE" ]; then
            echo "      --profile $USE_AWS_PROFILE --region $AWS_REGION \\"
        else
            echo "      --region $AWS_REGION \\"
        fi
        echo "      --query 'services[0].deployments'"
        echo ""
    fi
    
    # Show API endpoint
    case "$ENVIRONMENT" in
        dev)  API_URL="https://call-api-dev.totogicore.com" ;;
        test) API_URL="https://call-api-test.totogicore.com" ;;
        stage) API_URL="https://call-api-stage.totogicore.com" ;;
        prod) API_URL="https://call-api.totogicore.com" ;;
    esac
    
    log_info "API endpoint: $API_URL"
    log_info "Health check: $API_URL/health"
fi
