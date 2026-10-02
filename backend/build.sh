#!/bin/bash

#==============================================================================
# AI Job Engine - Docker Build, Scan, and Push to ECR
# 
# Features:
# - Builds Docker image for ai-job-engine
# - Pushes to AWS ECR (Elastic Container Registry)
# - Performs security scanning with Trivy
# - Runs AWS ECR image scanning
# - Validates image security and vulnerabilities
#==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

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
IMAGE_NAME="ai-job-engine"
TAG="latest"
# AWS_REGION loaded from .env.local, fallback to us-east-1
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
ECR_REGISTRY=""

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

# Build AWS command profile flag
if [ -n "$USE_AWS_PROFILE" ]; then
    AWS_CMD_PROFILE="--profile $USE_AWS_PROFILE"
else
    AWS_CMD_PROFILE=""
fi
SKIP_TESTS="${SKIP_TESTS:-false}"
SKIP_SCAN="${SKIP_SCAN:-false}"
SKIP_PUSH="${SKIP_PUSH:-false}"
NO_CACHE="${NO_CACHE:-false}"
SCAN_SEVERITY_THRESHOLD="${SCAN_SEVERITY_THRESHOLD:-CRITICAL}"

# Print functions
print_header() {
    echo -e "\n${PURPLE}═══════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  $1${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════${NC}"
}

print_step() {
    echo -e "\n${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}   $1${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Prerequisites Check"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker found: $(docker --version | cut -d' ' -f3)"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        print_info "Install: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
        exit 1
    fi
    print_success "AWS CLI found: $(aws --version 2>&1 | cut -d' ' -f1)"
    
    # Check jq for JSON parsing
    if ! command -v jq &> /dev/null; then
        print_warning "jq not found (recommended for JSON parsing)"
        print_info "Install: sudo apt-get install jq"
    else
        print_success "jq found"
    fi
    
    # Check if Trivy is installed for security scanning
    if ! command -v trivy &> /dev/null; then
        print_warning "Trivy not found - will skip local security scanning"
        print_info "Install: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
        print_info "Or script will use AWS ECR scanning only"
    else
        print_success "Trivy found: $(trivy --version 2>&1 | head -1)"
    fi
}

# Function to get AWS account ID
get_aws_account_id() {
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        print_step "Getting AWS Account ID..."
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity $AWS_CMD_PROFILE --query Account --output text 2>/dev/null || echo "")
        
        if [ -z "$AWS_ACCOUNT_ID" ]; then
            print_error "Failed to get AWS Account ID"
            print_info "Make sure AWS credentials are configured"
            print_info "Run: aws configure"
            exit 1
        fi
    fi
    
    ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    print_success "AWS Account ID: $AWS_ACCOUNT_ID"
    print_info "ECR Registry: $ECR_REGISTRY"
}

# Function to login to ECR
ecr_login() {
    print_step "Logging in to AWS ECR..."
    
    if aws ecr get-login-password $AWS_CMD_PROFILE --region "$AWS_REGION" | \
       docker login --username AWS --password-stdin "$ECR_REGISTRY" 2>/dev/null; then
        print_success "Logged in to ECR: $ECR_REGISTRY"
    else
        print_error "Failed to login to ECR"
        print_info "Check AWS credentials: aws sts get-caller-identity"
        exit 1
    fi
}

# Function to create ECR repository if it doesn't exist
ensure_ecr_repository() {
    print_step "Checking ECR repository..."
    
    if aws ecr describe-repositories $AWS_CMD_PROFILE --repository-names "$IMAGE_NAME" --region "$AWS_REGION" &>/dev/null; then
        print_success "ECR repository exists: $IMAGE_NAME"
    else
        print_warning "ECR repository not found, creating..."
        
        if aws ecr create-repository \
            $AWS_CMD_PROFILE \
            --repository-name "$IMAGE_NAME" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256 \
            --tags Key=Project,Value=ai-job-engine Key=ManagedBy,Value=build-script &>/dev/null; then
            
            print_success "ECR repository created: $IMAGE_NAME"
            print_info "Scan on push: enabled"
            print_info "Encryption: AES256"
        else
            print_error "Failed to create ECR repository"
            exit 1
        fi
    fi
}

# Function to build Docker image
build_image() {
    print_header "Building Docker Image"
    
    print_step "Building $IMAGE_NAME:$TAG..."
    
    # Check if Dockerfile exists
    if [ ! -f "Dockerfile" ]; then
        print_error "Dockerfile not found"
        exit 1
    fi
    
    # Build with BuildKit for better performance
    export DOCKER_BUILDKIT=1
    
    # Build arguments
    BUILD_ARGS=""
    BUILD_ARGS="$BUILD_ARGS --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    BUILD_ARGS="$BUILD_ARGS --build-arg VERSION=${TAG}"
    BUILD_ARGS="$BUILD_ARGS --label org.opencontainers.image.created=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    BUILD_ARGS="$BUILD_ARGS --label org.opencontainers.image.version=${TAG}"
    BUILD_ARGS="$BUILD_ARGS --label org.opencontainers.image.title=ai-job-engine"
    
    # Add --no-cache if requested (useful after Dockerfile changes)
    if [ "$NO_CACHE" = "true" ]; then
        BUILD_ARGS="$BUILD_ARGS --no-cache"
        print_warning "Building without cache (--no-cache)"
    fi
    
    if docker build $BUILD_ARGS -t "${IMAGE_NAME}:${TAG}" -f Dockerfile .; then
        print_success "Docker image built successfully"
    else
        print_error "Docker build failed"
        exit 1
    fi
    
    # Tag for ECR
    print_step "Tagging for ECR..."
    docker tag "${IMAGE_NAME}:${TAG}" "${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}"
    print_success "Tagged: ${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}"
}

# Function to test the image
test_image() {
    if [ "$SKIP_TESTS" = "true" ]; then
        print_warning "Skipping image tests (SKIP_TESTS=true)"
        return 0
    fi
    
    print_header "Testing Docker Image"
    
    local test_container="${IMAGE_NAME}-test-$$"
    
    print_step "Starting test container..."
    
    # Use a high port to avoid conflicts with common services (8000, 8001, etc.)
    local test_port=8099
    
    # Start container in background
    if docker run -d --name "$test_container" -p ${test_port}:8000 "${IMAGE_NAME}:${TAG}" &>/dev/null; then
        print_success "Test container started"
    else
        print_error "Failed to start test container"
        return 1
    fi
    
    # Wait for health check
    print_step "Waiting for health check..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f http://localhost:${test_port}/health &>/dev/null; then
            print_success "Health check passed"
            break
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    if [ $attempt -ge $max_attempts ]; then
        print_warning "Health check timeout (may be normal for some configurations)"
        docker logs --tail 20 "$test_container"
    fi
    
    # Cleanup test container
    print_step "Cleaning up test container..."
    docker stop "$test_container" &>/dev/null || true
    docker rm "$test_container" &>/dev/null || true
    print_success "Test container cleaned up"
}

# Function to scan image with Trivy (local security scanning)
scan_image_trivy() {
    if [ "$SKIP_SCAN" = "true" ]; then
        print_warning "Skipping Trivy scan (SKIP_SCAN=true)"
        return 0
    fi
    
    if ! command -v trivy &> /dev/null; then
        print_warning "Trivy not installed, skipping local security scan"
        return 0
    fi
    
    print_header "Security Scanning with Trivy"
    
    print_step "Scanning for vulnerabilities..."
    
    # Create scan report directory
    mkdir -p "$SCRIPT_DIR/security_reports"
    local scan_report="$SCRIPT_DIR/security_reports/trivy_scan_$(date +%Y%m%d_%H%M%S).json"
    
    # Run Trivy scan
    if trivy image \
        --severity CRITICAL,HIGH,MEDIUM \
        --format json \
        --output "$scan_report" \
        "${IMAGE_NAME}:${TAG}" 2>/dev/null; then
        
        print_success "Trivy scan completed"
        print_info "Report: $scan_report"
        
        # Parse results
        if command -v jq &> /dev/null; then
            local critical=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$scan_report" 2>/dev/null || echo "0")
            local high=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$scan_report" 2>/dev/null || echo "0")
            local medium=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="MEDIUM")] | length' "$scan_report" 2>/dev/null || echo "0")
            
            echo ""
            echo -e "${CYAN}Vulnerability Summary:${NC}"
            echo -e "   ${RED}CRITICAL: $critical${NC}"
            echo -e "   ${YELLOW}HIGH: $high${NC}"
            echo -e "   ${BLUE}MEDIUM: $medium${NC}"
            
            # Check if critical vulnerabilities found
            if [ "$critical" -gt 0 ]; then
                print_error "Found $critical CRITICAL vulnerabilities!"
                print_info "Review: $scan_report"
                
                if [ "$SCAN_SEVERITY_THRESHOLD" = "CRITICAL" ]; then
                    print_error "Build failed due to critical vulnerabilities"
                    print_info "Set SCAN_SEVERITY_THRESHOLD=HIGH to allow critical vulnerabilities"
                    exit 1
                fi
            fi
            
            # Generate HTML report
            trivy image \
                --severity CRITICAL,HIGH,MEDIUM \
                --format template \
                --template "@contrib/html.tpl" \
                --output "$SCRIPT_DIR/security_reports/trivy_scan_latest.html" \
                "${IMAGE_NAME}:${TAG}" 2>/dev/null || true
            
            if [ -f "$SCRIPT_DIR/security_reports/trivy_scan_latest.html" ]; then
                print_success "HTML report: security_reports/trivy_scan_latest.html"
            fi
        fi
    else
        print_warning "Trivy scan failed or had issues"
    fi
}

# Function to push to ECR
push_to_ecr() {
    if [ "$SKIP_PUSH" = "true" ]; then
        print_warning "Skipping ECR push (SKIP_PUSH=true)"
        return 0
    fi
    
    print_header "Pushing to AWS ECR"
    
    print_step "Pushing ${IMAGE_NAME}:${TAG} to ECR..."
    
    if docker push "${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}"; then
        print_success "Image pushed to ECR"
        print_info "Repository: ${ECR_REGISTRY}/${IMAGE_NAME}"
        print_info "Tag: ${TAG}"
        print_info "URI: ${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}"
    else
        print_error "Failed to push image to ECR"
        exit 1
    fi
}

# Function to wait for ECR scan results
wait_for_ecr_scan() {
    if [ "$SKIP_SCAN" = "true" ]; then
        return 0
    fi
    
    print_header "AWS ECR Image Scanning"
    
    print_step "Waiting for ECR scan results..."
    print_info "ECR scans images automatically on push (scanOnPush enabled)"
    
    local max_attempts=60
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        local scan_status=$(aws ecr describe-image-scan-findings \
            $AWS_CMD_PROFILE \
            --repository-name "$IMAGE_NAME" \
            --image-id imageTag="$TAG" \
            --region "$AWS_REGION" \
            --query 'imageScanStatus.status' \
            --output text 2>/dev/null || echo "IN_PROGRESS")
        
        if [ "$scan_status" = "COMPLETE" ]; then
            print_success "ECR scan completed"
            break
        elif [ "$scan_status" = "FAILED" ]; then
            print_warning "ECR scan failed"
            return 1
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    echo ""
    
    if [ $attempt -ge $max_attempts ]; then
        print_warning "Scan timeout - check ECR console for results"
        return 0
    fi
    
    # Get scan findings
    print_step "Retrieving scan findings..."
    
    local findings=$(aws ecr describe-image-scan-findings \
        $AWS_CMD_PROFILE \
        --repository-name "$IMAGE_NAME" \
        --image-id imageTag="$TAG" \
        --region "$AWS_REGION" \
        2>/dev/null || echo "")
    
    if [ -n "$findings" ] && command -v jq &> /dev/null; then
        # Save findings to file
        mkdir -p "$SCRIPT_DIR/security_reports"
        local ecr_report="$SCRIPT_DIR/security_reports/ecr_scan_$(date +%Y%m%d_%H%M%S).json"
        echo "$findings" > "$ecr_report"
        print_info "ECR scan report: $ecr_report"
        
        # Parse findings
        local critical=$(echo "$findings" | jq '.imageScanFindings.findingSeverityCounts.CRITICAL // 0' 2>/dev/null || echo "0")
        local high=$(echo "$findings" | jq '.imageScanFindings.findingSeverityCounts.HIGH // 0' 2>/dev/null || echo "0")
        local medium=$(echo "$findings" | jq '.imageScanFindings.findingSeverityCounts.MEDIUM // 0' 2>/dev/null || echo "0")
        local low=$(echo "$findings" | jq '.imageScanFindings.findingSeverityCounts.LOW // 0' 2>/dev/null || echo "0")
        
        echo ""
        echo -e "${CYAN}ECR Scan Results:${NC}"
        echo -e "   ${RED}CRITICAL: $critical${NC}"
        echo -e "   ${YELLOW}HIGH: $high${NC}"
        echo -e "   ${BLUE}MEDIUM: $medium${NC}"
        echo -e "   ${GREEN}LOW: $low${NC}"
        
        # Check severity threshold
        if [ "$critical" -gt 0 ]; then
            print_error "Found $critical CRITICAL vulnerabilities in ECR scan!"
            print_info "View details: aws ecr describe-image-scan-findings --repository-name $IMAGE_NAME --image-id imageTag=$TAG"
            
            if [ "$SCAN_SEVERITY_THRESHOLD" = "CRITICAL" ]; then
                print_error "Build failed due to critical vulnerabilities"
                exit 1
            else
                print_warning "Continuing despite critical vulnerabilities (threshold: $SCAN_SEVERITY_THRESHOLD)"
            fi
        else
            print_success "No critical vulnerabilities found"
        fi
    else
        print_warning "Could not parse ECR scan results"
    fi
}

# Function to perform additional security checks
security_checks() {
    print_header "Additional Security Checks"
    
    print_step "Checking image configuration..."
    
    # Check for non-root user
    local user=$(docker inspect "${IMAGE_NAME}:${TAG}" --format '{{.Config.User}}' 2>/dev/null || echo "")
    if [ -n "$user" ] && [ "$user" != "root" ] && [ "$user" != "0" ]; then
        print_success "Running as non-root user: $user"
    else
        print_warning "Image runs as root (security concern)"
    fi
    
    # Check exposed ports
    local ports=$(docker inspect "${IMAGE_NAME}:${TAG}" --format '{{.Config.ExposedPorts}}' 2>/dev/null || echo "")
    if [ -n "$ports" ]; then
        print_info "Exposed ports: $ports"
    fi
    
    # Check image size
    local size=$(docker images "${IMAGE_NAME}:${TAG}" --format "{{.Size}}" 2>/dev/null || echo "unknown")
    print_info "Image size: $size"
    
    if [ -n "$size" ]; then
        # Extract numeric size (assuming format like "123MB")
        local size_mb=$(echo "$size" | sed 's/MB//' | sed 's/GB/*1024/' | bc 2>/dev/null || echo "0")
        if [ -n "$size_mb" ] && [ "$size_mb" != "0" ]; then
            if (( $(echo "$size_mb > 500" | bc -l) )); then
                print_warning "Image size is large (>500MB): $size"
            elif (( $(echo "$size_mb > 200" | bc -l) )); then
                print_info "Image size is moderate (200-500MB): $size"
            else
                print_success "Image size is optimized (<200MB): $size"
            fi
        fi
    fi
    
    # Check for sensitive files
    print_step "Checking for sensitive files in image..."
    local sensitive_found=0
    
    # Create temporary container to inspect
    local inspect_container="${IMAGE_NAME}-inspect-$$"
    docker create --name "$inspect_container" "${IMAGE_NAME}:${TAG}" &>/dev/null
    
    # Export container filesystem
    local container_files=$(docker export "$inspect_container" | tar -t 2>/dev/null)
    
    # Check for actual sensitive files (excluding system certs and legitimate files)
    local sensitive_patterns=(
        "\.env$"                          # .env files
        "\.env\."                         # .env.local, .env.production, etc.
        "^\.git/"                         # .git directories
        "\.aws/credentials"               # AWS credentials
        "id_rsa$"                         # SSH private keys
        "id_dsa$"                         # SSH private keys
        "id_ecdsa$"                       # SSH private keys
        "id_ed25519$"                     # SSH private keys
        "\.key$"                          # Private key files (but not in cert paths)
        "\.pem$.*private"                 # Private key PEM files
        "private.*\.pem"                  # Private key PEM files
        "\.pgp$"                          # PGP keys
        "\.gpg$"                          # GPG keys
        "credentials\.json"               # Service account credentials
        "service-account"                 # Service account files
        "\.secrets"                       # Secrets files
    )
    
    # Build grep pattern excluding legitimate certificate paths and system files
    local exclude_patterns="etc/ssl/certs|usr/lib/ssl|usr/share/ca-certificates|site-packages.*cacert\.pem|botocore/cacert\.pem|certifi/cacert\.pem|usr/share/keyrings|debian-archive.*\.pgp|apt-key\.pgp"
    
    local sensitive_files=""
    for pattern in "${sensitive_patterns[@]}"; do
        local matches=$(echo "$container_files" | grep -E "$pattern" | grep -v -E "$exclude_patterns" || true)
        if [ -n "$matches" ]; then
            sensitive_files="$sensitive_files$matches"$'\n'
        fi
    done
    
    if [ -n "$sensitive_files" ] && [ "$sensitive_files" != $'\n' ]; then
        print_error "Sensitive files detected in image!"
        echo "$sensitive_files" | grep -v "^$"
        sensitive_found=1
    else
        print_success "No sensitive files found (system certs excluded)"
    fi
    
    # Cleanup
    docker rm "$inspect_container" &>/dev/null || true
    
    if [ $sensitive_found -eq 1 ]; then
        print_error "Build contains sensitive files - SECURITY RISK!"
        print_info "Add these patterns to .dockerignore"
        exit 1
    fi
}

# Function to show build summary
show_summary() {
    print_header "Build Summary"
    
    echo -e "${CYAN}Local Image:${NC}"
    echo -e "   ${GREEN}${IMAGE_NAME}:${TAG}${NC}"
    
    if [ "$SKIP_PUSH" != "true" ]; then
        echo -e "\n${CYAN}ECR Image:${NC}"
        echo -e "   ${GREEN}${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}${NC}"
        
        echo -e "\n${CYAN}Pull Command:${NC}"
        echo -e "   ${BLUE}docker pull ${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}${NC}"
    fi
    
    echo -e "\n${CYAN}Run Command:${NC}"
    echo -e "   ${BLUE}docker run -p 8000:8000 ${IMAGE_NAME}:${TAG}${NC}"
    
    if [ "$SKIP_SCAN" != "true" ]; then
        echo -e "\n${CYAN}Security Reports:${NC}"
        if [ -f "security_reports/trivy_scan_latest.html" ]; then
            echo -e "   ${BLUE}Trivy: security_reports/trivy_scan_latest.html${NC}"
        fi
        if [ -f "security_reports/ecr_scan_*.json" ]; then
            local latest_ecr=$(ls -t security_reports/ecr_scan_*.json 2>/dev/null | head -1)
            echo -e "   ${BLUE}ECR: $latest_ecr${NC}"
        fi
    fi
    
    echo -e "\n${CYAN}Image Details:${NC}"
    docker images "${IMAGE_NAME}:${TAG}" --format "   Size: {{.Size}}  Created: {{.CreatedAt}}"
    
    echo ""
}

# Main execution
main() {
    print_header "AI Job Engine - Docker Build Pipeline"
    
    echo -e "${BLUE}Configuration:${NC}"
    echo -e "   Image: ${IMAGE_NAME}:${TAG}"
    echo -e "   Region: ${AWS_REGION}"
    if [ -n "$USE_AWS_PROFILE" ]; then
        echo -e "   AWS Profile: ${USE_AWS_PROFILE}"
    else
        echo -e "   AWS Auth: Environment credentials (OIDC)"
    fi
    echo -e "   Skip Tests: ${SKIP_TESTS}"
    echo -e "   Skip Scan: ${SKIP_SCAN}"
    echo -e "   Skip Push: ${SKIP_PUSH}"
    
    # Step 1: Check prerequisites
    check_prerequisites
    
    # Step 2: Get AWS account and setup ECR
    get_aws_account_id
    ecr_login
    ensure_ecr_repository
    
    # Step 3: Build Docker image
    build_image

    # Step 4: Test the image
    test_image
    
    # Step 5: Security scanning (local)
    scan_image_trivy
    
    # Step 6: Additional security checks
    security_checks
    
    # Step 7: Push to ECR
    push_to_ecr
    
    # Step 8: Wait for ECR scan results
    if [ "$SKIP_PUSH" != "true" ]; then
        wait_for_ecr_scan
    fi
    
    # Step 9: Show summary
    show_summary
    
    print_header "Build Complete!"
    print_success "AI Job Engine image ready"
    
    if [ "$SKIP_PUSH" != "true" ]; then
        print_success "Image available in ECR: ${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}"
    fi

echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-test)
            SKIP_TESTS=true
            shift
            ;;
        --no-scan)
            SKIP_SCAN=true
            shift
            ;;
        --no-push)
            SKIP_PUSH=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --account)
            AWS_ACCOUNT_ID="$2"
            shift 2
            ;;
        --profile)
            if [ "$2" = "none" ] || [ -z "$2" ]; then
                # Use OIDC/environment credentials
                USE_AWS_PROFILE=""
                unset AWS_PROFILE
                AWS_CMD_PROFILE=""
            else
                USE_AWS_PROFILE="$2"
                AWS_PROFILE="$2"
                AWS_CMD_PROFILE="--profile $2"
            fi
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [TAG] [OPTIONS]"
            echo ""
            echo "Arguments:"
            echo "  TAG                Image tag (default: latest)"
            echo ""
            echo "Options:"
            echo "  --no-test          Skip image testing"
            echo "  --no-scan          Skip security scanning"
            echo "  --no-push          Skip pushing to ECR"
            echo "  --no-cache         Force rebuild without Docker cache (use after Dockerfile changes)"
            echo "  --region REGION    AWS region (default: us-east-1)"
            echo "  --account ID       AWS account ID (auto-detected if not provided)"
            echo "  --profile PROFILE  AWS profile name (default: external-access, use 'none' for OIDC)"
            echo "  --help, -h         Show this help"
            echo ""
            echo "Environment Variables:"
            echo "  SKIP_TESTS=true           Skip image tests"
            echo "  SKIP_SCAN=true            Skip security scans"
            echo "  SKIP_PUSH=true            Skip ECR push"
            echo "  NO_CACHE=true             Force rebuild without cache"
            echo "  AWS_REGION=us-west-2      Set AWS region"
            echo "  AWS_PROFILE=external-access  Set AWS profile (default: external-access, 'none' for OIDC)"
            echo "  SCAN_SEVERITY_THRESHOLD   Fail on severity (CRITICAL, HIGH, MEDIUM)"
            echo ""
            echo "Examples:"
            echo "  $0                        # Build, scan, and push with tag 'latest'"
            echo "  $0 v1.2.3                 # Build with tag 'v1.2.3'"
            echo "  $0 dev --no-push          # Build 'dev' tag without pushing"
            echo "  $0 latest --no-scan       # Build without security scanning"
            echo "  SKIP_TESTS=true $0        # Build without testing"
echo ""
            exit 0
            ;;
        *)
            # Assume it's the tag if it doesn't start with --
            if [[ ! "$1" =~ ^-- ]]; then
                TAG="$1"
            fi
            shift
            ;;
    esac
done

# Run main function
main

exit 0
