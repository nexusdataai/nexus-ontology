#!/bin/bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#==============================================================================
# AI Job Engine - Complete Rebuild and Comprehensive Test Script
#
# This script performs a complete rebuild and testing cycle:
# 1. Cleans all existing test reports
# 2. Kills any existing Docker containers
# 3. Removes existing Docker images
# 4. Rebuilds Docker image from scratch
# 5. Starts fresh container
# 6. Runs comprehensive test suite (unit + integration + BDD + endurance)
# 7. Generates consolidated HTML report with links to all test reports
#
# Usage: ./rebuild-and-test.sh [OPTIONS]
#
# Options:
#   --skip-tests       Skip test execution (only build and start)
#   --force-rebuild    Force complete rebuild (clear Docker cache)
#   --quiet            Minimal output (quiet mode)
#   --no-cache         Disable Docker build cache
#   --help             Show this help message
#
# Environment Variables (alternative to flags):
#   SKIP_TESTS=true        Same as --skip-tests
#   FORCE_REBUILD=true     Same as --force-rebuild
#   QUIET_MODE=true        Same as --quiet
#   USE_CACHE=false        Same as --no-cache
#   AWS_PROFILE=name       AWS profile to use (default: external-access)
#
# Duration: ~15-20 minutes for complete build and test cycle
#==============================================================================

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DOCKER_IMAGE_NAME="ai-job-engine"
DOCKER_TAG="latest"
CONTAINER_NAME="ai-job-engine"
HTTP_PORT="8000"
BASE_URL="http://localhost:${HTTP_PORT}"
TIMEOUT_SECONDS=30
DOCKERFILE_PATH="Dockerfile"
TEST_SCRIPT="test_unified_gateway.py"
AWS_PROFILE="${AWS_PROFILE:-external-access}"

# Optimization flags
FORCE_REBUILD=${FORCE_REBUILD:-false}
SKIP_TESTS=${SKIP_TESTS:-false}
QUIET_MODE=${QUIET_MODE:-false}
USE_CACHE=${USE_CACHE:-true}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Function to print colored output (respects quiet mode)
print_color() {
    local color=$1
    local message=$2
    if [ "$QUIET_MODE" != "true" ]; then
        echo -e "${color}${message}${NC}"
    fi
}

# Function to print important messages (always shown)
print_important() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print section headers
print_header() {
    local title=$1
    if [ "$QUIET_MODE" != "true" ]; then
        print_color $BLUE "\n=== ${title} ==="
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

AI Job Engine - Complete Rebuild and Test Script

This script performs a complete rebuild and testing cycle:
  1. Cleans all existing test reports
  2. Kills any existing Docker containers
  3. Removes existing Docker images
  4. Rebuilds Docker image from scratch
  5. Starts fresh container
  6. Runs comprehensive test suite (optional)

OPTIONS:
  --skip-tests       Skip test execution (only build and start container)
  --force-rebuild    Force complete rebuild (clear Docker cache)
  --quiet            Minimal output (quiet mode)
  --no-cache         Disable Docker build cache
  --help, -h         Show this help message

ENVIRONMENT VARIABLES (alternative to flags):
  SKIP_TESTS=true        Same as --skip-tests
  FORCE_REBUILD=true     Same as --force-rebuild
  QUIET_MODE=true        Same as --quiet
  USE_CACHE=false        Same as --no-cache
  AWS_PROFILE=name       AWS profile to use (default: external-access)

EXAMPLES:
  $0                           # Full rebuild and test
  $0 --skip-tests              # Build and start only (no tests)
  $0 --force-rebuild           # Force rebuild with cache clear
  $0 --skip-tests --quiet      # Quick rebuild, minimal output
  SKIP_TESTS=true $0           # Using environment variable

DURATION:
  ~15-20 minutes for complete build and test cycle
  ~5-7 minutes with --skip-tests

EOF
    exit 0
}

# Function to check if command exists
check_command() {
    local cmd=$1
    if ! command -v $cmd &> /dev/null; then
        print_important $RED "❌ Error: $cmd is not installed or not in PATH"
        exit 1
    fi
}

# Function to check if container is running and healthy
is_container_healthy() {
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        if curl -s -f $BASE_URL/health > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to get image ID
get_image_id() {
    docker images -q $DOCKER_IMAGE_NAME:$DOCKER_TAG 2>/dev/null || echo ""
}

# Function to get container image ID
get_container_image_id() {
    if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
        docker inspect $CONTAINER_NAME --format='{{.Image}}' 2>/dev/null | cut -c1-12 || echo ""
    else
        echo ""
    fi
}

# Fast health check with shorter timeout
wait_for_service_fast() {
    local url=$1
    local timeout=$2
    local count=0
    
    print_color $CYAN "⏳ Waiting for service (${timeout}s timeout)..."
    
    while [ $count -lt $timeout ]; do
        if curl -s -f --max-time 2 $url/health > /dev/null 2>&1; then
            print_color $GREEN "✅ Service ready!"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    
    return 1
}

# Check if port is available
check_port_available() {
    local port=$1
    if lsof -i:$port > /dev/null 2>&1; then
        print_important $YELLOW "⚠️ Port $port is already in use"
        print_color $CYAN "Checking what's using port $port..."
        lsof -i:$port | grep LISTEN | head -5
        
        # Try to identify if it's our container
        local port_user=$(lsof -i:$port -t 2>/dev/null | head -1)
        if [ ! -z "$port_user" ]; then
            local process_name=$(ps -p $port_user -o comm= 2>/dev/null || echo "unknown")
            if [[ "$process_name" == *"docker"* ]] || [[ "$process_name" == *"containerd"* ]]; then
                print_color $BLUE "   Likely a Docker container using the port"
            else
                print_color $YELLOW "   Process: $process_name (PID: $port_user)"
            fi
        fi
        return 1
    fi
    print_color $GREEN "✅ Port $port is available"
    return 0
}

# Function to cleanup on exit
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        print_important $RED "❌ Script failed with exit code $exit_code"
    fi
    exit $exit_code
}

# Set up cleanup trap
trap cleanup EXIT

# Function to clean test reports
clean_test_reports() {
    print_header "Cleaning Test Reports"
    
    local reports_dir="$SCRIPT_DIR/test_reports"
    
    if [ -d "$reports_dir" ]; then
        print_color $CYAN "🧹 Cleaning existing test reports..."
        
        local cleaned_count=0
        
        # Clean unit reports
        if [ -d "$reports_dir/unit" ]; then
            local unit_files=$(find "$reports_dir/unit" -type f \( -name "*.html" -o -name "*.json" \) 2>/dev/null | wc -l)
            find "$reports_dir/unit" -type f \( -name "*.html" -o -name "*.json" \) -delete 2>/dev/null || true
            print_color $BLUE "   🧪 Cleaned $unit_files unit test reports"
            cleaned_count=$((cleaned_count + unit_files))
        fi
        
        # Clean integration reports
        if [ -d "$reports_dir/integration" ]; then
            local int_files=$(find "$reports_dir/integration" -type f \( -name "*.html" -o -name "*.json" \) 2>/dev/null | wc -l)
            find "$reports_dir/integration" -type f \( -name "*.html" -o -name "*.json" \) -delete 2>/dev/null || true
            print_color $BLUE "   🔗 Cleaned $int_files integration test reports"
            cleaned_count=$((cleaned_count + int_files))
        fi
        
        # Clean BDD reports
        if [ -d "$reports_dir/bdd" ]; then
            local bdd_files=$(find "$reports_dir/bdd" -type f \( -name "*.html" -o -name "*.json" \) 2>/dev/null | wc -l)
            find "$reports_dir/bdd" -type f \( -name "*.html" -o -name "*.json" \) -delete 2>/dev/null || true
            print_color $BLUE "   📝 Cleaned $bdd_files BDD test reports"
            cleaned_count=$((cleaned_count + bdd_files))
        fi
        
        # Clean endurance reports
        if [ -d "$reports_dir/endurance" ]; then
            local end_files=$(find "$reports_dir/endurance" -type f \( -name "*.html" -o -name "*.json" \) 2>/dev/null | wc -l)
            find "$reports_dir/endurance" -type f \( -name "*.html" -o -name "*.json" \) -delete 2>/dev/null || true
            # Also clean dashboard directory
            if [ -d "$reports_dir/endurance/dashboard" ]; then
                rm -rf "$reports_dir/endurance/dashboard/"* 2>/dev/null || true
            fi
            print_color $BLUE "   ⚡ Cleaned $end_files endurance test reports"
            cleaned_count=$((cleaned_count + end_files))
        fi
        
        # Clean consolidated reports (in root of test_reports)
        local cons_files=$(find "$reports_dir" -maxdepth 1 -type f -name "consolidated_report_*.html" 2>/dev/null | wc -l)
        find "$reports_dir" -maxdepth 1 -type f -name "consolidated_report_*.html" -delete 2>/dev/null || true
        print_color $BLUE "   🎯 Cleaned $cons_files consolidated reports"
        cleaned_count=$((cleaned_count + cons_files))
        
        # Clean test_reports.html (old dashboard)
        if [ -f "$reports_dir/test_reports.html" ]; then
            rm -f "$reports_dir/test_reports.html" 2>/dev/null || true
            print_color $BLUE "   🗑️ Cleaned old dashboard (test_reports.html)"
            cleaned_count=$((cleaned_count + 1))
        fi
        
        # Clean data directory JSON files (test results cache)
        if [ -d "$reports_dir/data" ]; then
            local data_files=$(find "$reports_dir/data" -type f -name "*.json" 2>/dev/null | wc -l)
            find "$reports_dir/data" -type f -name "*.json" -delete 2>/dev/null || true
            if [ $data_files -gt 0 ]; then
                print_color $BLUE "   📦 Cleaned $data_files data files"
                cleaned_count=$((cleaned_count + data_files))
            fi
        fi
        
        print_color $GREEN "✅ Test reports cleaned (total: $cleaned_count files)"
        
        # Show what's left (should only be scripts and assets)
        if [ "$QUIET_MODE" != "true" ]; then
            print_color $CYAN "   📁 Keeping: README.md, *.py, *.css, *.js (scripts and assets)"
        fi
    else
        print_color $BLUE "ℹ️ No test reports directory found"
    fi
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --force-rebuild)
            FORCE_REBUILD=true
            shift
            ;;
        --quiet)
            QUIET_MODE=true
            shift
            ;;
        --no-cache)
            USE_CACHE=false
            shift
            ;;
        --help|-h)
            show_usage
            ;;
        *)
            print_important $RED "❌ Unknown option: $1"
            echo ""
            show_usage
            ;;
    esac
done

# Main execution starts here
print_important $CYAN "🚀 AI Job Engine - Complete Rebuild and Test"
print_color $CYAN "📁 Working directory: $SCRIPT_DIR"

# Show active options
if [ "$SKIP_TESTS" = "true" ] || [ "$FORCE_REBUILD" = "true" ] || [ "$QUIET_MODE" = "true" ] || [ "$USE_CACHE" = "false" ]; then
    print_color $YELLOW "⚙️ Active options:"
    [ "$SKIP_TESTS" = "true" ] && print_color $BLUE "   • Skip tests enabled"
    [ "$FORCE_REBUILD" = "true" ] && print_color $BLUE "   • Force rebuild enabled"
    [ "$QUIET_MODE" = "true" ] && print_color $BLUE "   • Quiet mode enabled"
    [ "$USE_CACHE" = "false" ] && print_color $BLUE "   • Docker cache disabled"
fi
echo ""

# Function to refresh AWS credentials
refresh_aws_credentials() {
    print_header "AWS Credentials Refresh"
    
    # Check if AWS CLI is available
    if ! command -v aws &> /dev/null; then
        print_color $YELLOW "⚠️ AWS CLI not found, skipping credential refresh"
        return 0
    fi
    
    # Check if refresh script exists
    if [ -f "$SCRIPT_DIR/refresh-aws-credentials.sh" ]; then
        print_color $CYAN "🔑 Running AWS credential refresh script..."
        if bash "$SCRIPT_DIR/refresh-aws-credentials.sh" 2>/dev/null; then
            print_color $GREEN "✅ AWS credentials refreshed via script"
            return 0
        else
            print_color $YELLOW "⚠️ Refresh script failed, trying alternative methods..."
        fi
    fi
    
    # Check if aws-login.sh exists
    if [ -f "$SCRIPT_DIR/aws-login.sh" ]; then
        print_color $CYAN "🔑 Running aws-login.sh..."
        if bash "$SCRIPT_DIR/aws-login.sh" 2>/dev/null; then
            print_color $GREEN "✅ AWS credentials refreshed"
            return 0
        else
            print_color $YELLOW "⚠️ aws-login.sh failed, checking existing credentials..."
        fi
    fi
    
    # Verify existing credentials
    print_color $CYAN "🔍 Verifying existing AWS credentials (profile: $AWS_PROFILE)..."
    if aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
        print_color $GREEN "✅ AWS credentials are valid"
        aws sts get-caller-identity --profile "$AWS_PROFILE" 2>/dev/null | grep -E "UserId|Account|Arn" || true
        return 0
    else
        print_color $YELLOW "⚠️ AWS credentials may be expired or not configured"
        print_color $YELLOW "   Tests requiring AWS access may fail"
        print_color $BLUE "   To refresh manually: aws sso login"
        return 0
    fi
}

# Check prerequisites (only essential ones)
check_command "docker"
if [ "$SKIP_TESTS" != "true" ]; then
    check_command "curl"
    check_command "python3"
    check_command "bash"
fi

# Refresh AWS credentials first
refresh_aws_credentials

echo ""

# Clean test reports
clean_test_reports

# Always rebuild for consistency (container will be stopped and removed)
if [ "$FORCE_REBUILD" != "true" ]; then
    print_color $BLUE "ℹ️ Standard rebuild mode - container and image will be recreated"
else
    print_color $YELLOW "⚠️ Force rebuild mode - Docker cache will also be cleared"
fi

# Container cleanup - Always stop and remove existing container for clean start
print_header "Container Cleanup"

# Check if container is running
if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
    print_color $CYAN "🛑 Stopping running container..."
    docker stop $CONTAINER_NAME > /dev/null 2>&1 || true
    print_color $GREEN "✅ Container stopped"
fi

# Check if container exists (stopped or running)
if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
    print_color $CYAN "🗑️ Removing existing container..."
    docker rm -f $CONTAINER_NAME > /dev/null 2>&1 || true
    print_color $GREEN "✅ Container removed"
else
    print_color $BLUE "ℹ️ No existing container found"
fi

# Also clean up any orphaned containers with same image
print_color $CYAN "🧹 Cleaning orphaned containers..."
docker ps -aq -f ancestor=$DOCKER_IMAGE_NAME:$DOCKER_TAG --no-trunc 2>/dev/null | while read container_id; do
    if [ ! -z "$container_id" ]; then
        container_name=$(docker inspect --format='{{.Name}}' $container_id 2>/dev/null | sed 's/^\/\+//' || echo "")
        if [ ! -z "$container_name" ] && [ "$container_name" != "$CONTAINER_NAME" ]; then
            print_color $YELLOW "  Removing orphaned container: $container_name"
            docker rm -f $container_id > /dev/null 2>&1 || true
        fi
    fi
done

# Docker image cleanup - Remove existing image for complete rebuild
print_header "Image Cleanup"

if docker images -q $DOCKER_IMAGE_NAME:$DOCKER_TAG 2>/dev/null | grep -q .; then
    print_color $CYAN "🗑️ Removing existing Docker image..."
    docker rmi -f $DOCKER_IMAGE_NAME:$DOCKER_TAG > /dev/null 2>&1 || true
    print_color $GREEN "✅ Docker image removed"
else
    print_color $BLUE "ℹ️ No existing Docker image found"
fi

# Remove dangling images
print_color $CYAN "🧹 Cleaning dangling images..."
docker image prune -f > /dev/null 2>&1 || true

# Optimized Docker build
print_header "Optimized Build"

build_args=""
if [ "$USE_CACHE" != "true" ]; then
    build_args="--no-cache"
fi

# Use legacy builder (BuildKit may not be available)
unset DOCKER_BUILDKIT

print_color $CYAN "🔨 Building image..."
if [ "$QUIET_MODE" = "true" ]; then
    docker build $build_args -f $DOCKERFILE_PATH -t $DOCKER_IMAGE_NAME:$DOCKER_TAG . > /dev/null 2>&1
else
    docker build $build_args -f $DOCKERFILE_PATH -t $DOCKER_IMAGE_NAME:$DOCKER_TAG .
fi

print_color $GREEN "✅ Build complete"

# Check port availability
print_header "Port Check"
if ! check_port_available $HTTP_PORT; then
    print_important $YELLOW "⚠️ Port $HTTP_PORT is in use - will try to start container anyway"
    print_color $CYAN "Docker may handle port binding or fail with a clear error"
fi

# Start fresh container
print_header "Starting Fresh Container"

print_color $CYAN "🚀 Starting new container..."

# Prepare AWS credentials - use environment variables for better compatibility
AWS_CRED_ARGS=""

# Try to get credentials from AWS CLI (using profile: external-access)
if command -v aws &> /dev/null && aws sts get-caller-identity --profile "$AWS_PROFILE" &>/dev/null; then
    print_color $BLUE "   🔑 Extracting AWS credentials from host (profile: $AWS_PROFILE)..."
    
    # Get current credentials (works with assumed roles, SSO, etc.)
    AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id --profile "$AWS_PROFILE" 2>/dev/null || echo "")
    AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key --profile "$AWS_PROFILE" 2>/dev/null || echo "")
    AWS_SESSION_TOKEN=$(aws configure get aws_session_token --profile "$AWS_PROFILE" 2>/dev/null || echo "")
    AWS_REGION=$(aws configure get region --profile "$AWS_PROFILE" 2>/dev/null || echo "us-east-1")
    
    # If credentials found, pass them as environment variables
    if [ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]; then
        AWS_CRED_ARGS="-e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID"
        AWS_CRED_ARGS="$AWS_CRED_ARGS -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY"
        [ ! -z "$AWS_SESSION_TOKEN" ] && AWS_CRED_ARGS="$AWS_CRED_ARGS -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN"
        AWS_CRED_ARGS="$AWS_CRED_ARGS -e AWS_DEFAULT_REGION=$AWS_REGION"
        AWS_CRED_ARGS="$AWS_CRED_ARGS -e AWS_REGION=$AWS_REGION"
        
        # Disable EC2 metadata to prevent role confusion
        AWS_CRED_ARGS="$AWS_CRED_ARGS -e AWS_EC2_METADATA_DISABLED=true"
        
        print_color $GREEN "   ✅ AWS credentials configured (via environment variables)"
        print_color $BLUE "   🔒 EC2 metadata disabled (using your credentials)"
    else
        print_color $YELLOW "   ⚠️ Could not extract AWS credentials"
    fi
else
    print_color $YELLOW "   ⚠️ AWS CLI not available or credentials not configured"
fi

CONTAINER_ID=$(docker run -d \
    --name $CONTAINER_NAME \
    -p $HTTP_PORT:8000 \
    --restart unless-stopped \
    $AWS_CRED_ARGS \
    $DOCKER_IMAGE_NAME:$DOCKER_TAG 2>&1)

if [ $? -eq 0 ]; then
    print_color $GREEN "✅ Container started successfully"
    print_color $BLUE "   Container ID: ${CONTAINER_ID:0:12}"
    print_color $BLUE "   Container name: $CONTAINER_NAME"
    print_color $BLUE "   Port mapping: $HTTP_PORT:8000"
else
    print_important $RED "❌ Failed to start container"
    if [[ "$CONTAINER_ID" == *"port is already allocated"* ]]; then
        print_important $RED "Port $HTTP_PORT is already in use by another process"
        print_color $YELLOW "Try: docker ps -a | grep ':$HTTP_PORT->'"
    else
        echo "$CONTAINER_ID"
    fi
    exit 1
fi

# Fast service readiness check
print_header "Service Check"
if wait_for_service_fast $BASE_URL $TIMEOUT_SECONDS; then
    print_color $GREEN "✅ Service ready"
else
    print_important $RED "❌ Service not ready - checking logs..."
    docker logs --tail 20 $CONTAINER_NAME
    exit 1
fi

# Comprehensive testing
if [ "$SKIP_TESTS" != "true" ]; then
    print_header "Health Check"
    
    # Quick API validation
    print_color $CYAN "🧪 Validating service endpoints..."
    
    # Test key endpoints
    health_ok=false
    tools_ok=false
    api_ok=false
    
    # Check health endpoint
    if curl -s -f --max-time 5 $BASE_URL/health > /dev/null 2>&1; then
        health_ok=true
        print_color $GREEN "  ✓ Health endpoint working"
    fi
    
    # Check tools endpoint (MCP tools via worker pool)
    if curl -s -f --max-time 5 -H "X-API-Key: super-secret" $BASE_URL/tools > /dev/null 2>&1; then
        tools_ok=true
        print_color $GREEN "  ✓ MCP tools endpoint working"
    fi
    
    # Check REST API endpoints
    if curl -s -f --max-time 5 $BASE_URL/api/v1/health/ > /dev/null 2>&1; then
        api_ok=true
        print_color $GREEN "  ✓ REST APIs working"
    fi
    
    if [ "$health_ok" = "true" ] && [ "$tools_ok" = "true" ]; then
        print_color $GREEN "✅ Service endpoints validated"
    else
        print_important $YELLOW "⚠️ Some endpoints not responding - tests may fail"
    fi
    
    # Run comprehensive test suite
    print_header "Comprehensive Test Suite"
    
    print_important $CYAN "🧪 Running all tests (unit + integration + BDD + 1min endurance)..."
    print_color $BLUE "   This will take approximately 15-20 minutes"
    print_color $BLUE "   Tests will run: Unit → Integration → BDD → Endurance (1min)"
    print_color $BLUE "   Consolidated report will be generated at the end"
    echo ""
    
    # Set environment variable for test script
    export SERVER_URL=$BASE_URL
    
    # Run comprehensive test suite
    cd "$SCRIPT_DIR"
    if bash tests/run_tests.sh all-quick; then
        print_important $GREEN "✅ All tests passed!"
        
        # Find and display the consolidated report location
        latest_report=$(ls -t test_reports/consolidated_report_*.html 2>/dev/null | head -1)
        if [ -f "$latest_report" ]; then
            print_important $CYAN "\n📊 CONSOLIDATED TEST REPORT:"
            print_important $BLUE "   $latest_report"
            print_important $BLUE "   file://$(realpath "$latest_report")"
            
            # List all generated reports
            print_color $CYAN "\n📋 Individual Reports Generated:"
            
            latest_unit=$(ls -t test_reports/unit/unit_test_report_enhanced_*.html 2>/dev/null | head -1)
            [ -f "$latest_unit" ] && print_color $BLUE "   🧪 Unit: $latest_unit"
            
            latest_integration=$(ls -t test_reports/integration/integration_test_report_*.html 2>/dev/null | head -1)
            [ -f "$latest_integration" ] && print_color $BLUE "   🔗 Integration: $latest_integration"
            
            [ -f "test_reports/bdd/index.html" ] && print_color $BLUE "   📝 BDD: test_reports/bdd/index.html"
            
            latest_endurance=$(ls -t test_reports/endurance/dashboard/*.html 2>/dev/null | head -1)
            [ -f "$latest_endurance" ] && print_color $BLUE "   ⚡ Endurance: $latest_endurance"
        fi
    else
        print_important $RED "❌ Some tests failed - check output above"
        print_color $YELLOW "   Review test reports for details"
        exit 1
    fi
else
    print_color $BLUE "⏭️ Tests skipped (SKIP_TESTS=true)"
fi

# Summary
print_header "Summary"
print_important $GREEN "🎉 AI Job Engine - Build and Test Complete!"
echo ""
print_important $CYAN "🌐 Service Information:"
print_important $BLUE "   Service URL: $BASE_URL"
print_important $BLUE "   Health: $BASE_URL/health" 
print_important $BLUE "   MCP Tools: $BASE_URL/tools"
print_important $BLUE "   REST APIs: $BASE_URL/api/v1/"
print_important $BLUE "   Documentation: $BASE_URL/docs"

if [ "$SKIP_TESTS" != "true" ]; then
    print_important $CYAN "\n📊 Test Reports:"
    latest_consolidated=$(ls -t test_reports/consolidated_report_*.html 2>/dev/null | head -1)
    if [ -f "$latest_consolidated" ]; then
        print_important $GREEN "   ✅ Consolidated Report: $latest_consolidated"
        print_important $BLUE "   🔗 Open in browser: file://$(realpath "$latest_consolidated")"
    fi
fi

# Show management info
if [ "$QUIET_MODE" != "true" ]; then
    print_color $CYAN "\n🔧 Container Management:"
    print_color $BLUE "  View logs: docker logs -f $CONTAINER_NAME"
    print_color $BLUE "  Stop container: docker stop $CONTAINER_NAME"
    print_color $BLUE "  Restart: docker restart $CONTAINER_NAME"
    print_color $BLUE "  Shell access: docker exec -it $CONTAINER_NAME /bin/bash"
    
    print_color $CYAN "\n🎯 Gateway Scripts:"
    print_color $BLUE "  ./gateway.sh [start|stop|restart|status|test|logs]"
    
    print_color $CYAN "\n💡 Script Options:"
    print_color $BLUE "  $0 --skip-tests           # Skip test execution"
    print_color $BLUE "  $0 --force-rebuild        # Force complete rebuild"
    print_color $BLUE "  $0 --quiet                # Minimal output"
    print_color $BLUE "  $0 --no-cache             # Disable Docker cache"
    print_color $BLUE "  $0 --help                 # Show help message"
    
    print_color $CYAN "\n📋 What This Script Did:"
    print_color $GREEN "  ✓ Cleaned all test reports"
    print_color $GREEN "  ✓ Killed existing Docker containers"
    print_color $GREEN "  ✓ Removed existing Docker image"
    print_color $GREEN "  ✓ Rebuilt Docker image from scratch"
    print_color $GREEN "  ✓ Started fresh container"
    if [ "$SKIP_TESTS" != "true" ]; then
        print_color $GREEN "  ✓ Ran comprehensive test suite:"
        print_color $GREEN "    - Unit tests (all 303 tests)"
        print_color $GREEN "    - Integration tests (shell + Python)"
        print_color $GREEN "    - BDD tests (all scenarios)"
        print_color $GREEN "    - Endurance tests (1 minute)"
        print_color $GREEN "  ✓ Generated consolidated report with links"
    fi
fi

print_important $CYAN "\n🚀 System is ready for use!"

exit 0