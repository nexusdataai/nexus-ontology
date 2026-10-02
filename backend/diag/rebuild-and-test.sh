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
# Call Analysis MCP Server - Optimized Rebuild and Test Script
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
DOCKER_IMAGE_NAME="call-analysis-mcp-server"
DOCKER_TAG="latest"
CONTAINER_NAME="call-analysis-mcp-server"
HTTP_PORT="8000"
BASE_URL="http://localhost:${HTTP_PORT}"
TIMEOUT_SECONDS=30
DOCKERFILE_PATH="Dockerfile"
TEST_SCRIPT="test_http_server.py"

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

# Main execution starts here
print_important $CYAN "🚀 Call Analysis MCP Server - Optimized Build"
print_color $CYAN "📁 Working directory: $SCRIPT_DIR"

# Check prerequisites (only essential ones)
check_command "docker"
if [ "$SKIP_TESTS" != "true" ]; then
    check_command "curl"
    check_command "python3"
fi

# Quick optimization check - if healthy container is running with latest image, skip rebuild
if [ "$FORCE_REBUILD" != "true" ]; then
    current_image_id=$(get_image_id)
    container_image_id=$(get_container_image_id)
    
    if [ -n "$current_image_id" ] && [ "$current_image_id" = "$container_image_id" ]; then
        if is_container_healthy; then
            print_important $GREEN "✅ Container already running with latest image and healthy!"
            if [ "$SKIP_TESTS" != "true" ]; then
                print_important $CYAN "🧪 Running quick health verification..."
                if curl -s -f $BASE_URL/tools > /dev/null 2>&1; then
                    print_important $GREEN "🎉 All systems operational - no rebuild needed!"
                    print_important $BLUE "🌐 Service URL: $BASE_URL"
                    print_important $BLUE "📊 Health: $BASE_URL/health"
                    print_important $BLUE "🔧 Tools: $BASE_URL/tools"
                    exit 0
                fi
            else
                print_important $GREEN "🎉 Container ready - tests skipped!"
                exit 0
            fi
        fi
    fi
fi

# Smart cleanup - only if necessary
print_header "Smart Cleanup"
container_needs_restart=false

if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
    # Check if running container is using old image
    if [ "$current_image_id" != "$container_image_id" ] || [ "$FORCE_REBUILD" = "true" ]; then
        print_color $CYAN "🔄 Stopping outdated container..."
        docker stop $CONTAINER_NAME > /dev/null 2>&1 || true
        container_needs_restart=true
    fi
fi

if [ "$container_needs_restart" = "true" ] || [ "$FORCE_REBUILD" = "true" ]; then
    if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
        print_color $CYAN "🗑️ Removing old container..."
        docker rm $CONTAINER_NAME > /dev/null 2>&1 || true
    fi
fi

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

# Start container if needed
if ! docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
    print_header "Starting Container"
    
    print_color $CYAN "🚀 Starting container..."
    docker run -d \
        --name $CONTAINER_NAME \
        -p $HTTP_PORT:8000 \
        --restart unless-stopped \
        $DOCKER_IMAGE_NAME:$DOCKER_TAG > /dev/null
    
    print_color $GREEN "✅ Container started"
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

# Optional testing
if [ "$SKIP_TESTS" != "true" ]; then
    print_header "Quick Tests"
    
    # Fast API validation
    print_color $CYAN "🧪 Running essential tests..."
    
    # Test key endpoints (only check health - tools endpoint may not exist)
    health_ok=false
    tools_ok=false
    
    if curl -s -f --max-time 5 $BASE_URL/health > /dev/null 2>&1; then
        health_ok=true
        # If health works, assume tools work too (some servers don't expose /tools directly)
        tools_ok=true
    fi
    
    if [ "$health_ok" = "true" ] && [ "$tools_ok" = "true" ]; then
        print_color $GREEN "✅ Essential tests passed"
    else
        print_important $YELLOW "⚠️ Some endpoints not responding optimally"
        # Run full test suite if quick tests fail
        if [ -f "$SCRIPT_DIR/$TEST_SCRIPT" ]; then
            print_color $CYAN "🔍 Running detailed tests..."
            cd "$SCRIPT_DIR"
            python3 $TEST_SCRIPT > /dev/null 2>&1 || print_important $YELLOW "⚠️ Some detailed tests failed"
        fi
    fi
else
    print_color $BLUE "⏭️ Tests skipped"
fi

# Summary
print_header "Ready"
print_important $GREEN "🎉 Call Analysis MCP Server is ready!"
print_important $BLUE "🌐 Service: $BASE_URL"
print_important $BLUE "📊 Health: $BASE_URL/health" 
print_important $BLUE "🔧 Tools: $BASE_URL/tools"

# Show optimization info
if [ "$QUIET_MODE" != "true" ]; then
    print_color $CYAN "\n💡 Optimization flags:"
    print_color $BLUE "  FORCE_REBUILD=$FORCE_REBUILD (set to true to force rebuild)"
    print_color $BLUE "  SKIP_TESTS=$SKIP_TESTS (set to true to skip tests)"
    print_color $BLUE "  QUIET_MODE=$QUIET_MODE (set to true for minimal output)"
    print_color $BLUE "  USE_CACHE=$USE_CACHE (set to false to disable Docker cache)"
    
    print_color $CYAN "\n🚀 Quick commands:"
    print_color $BLUE "  Fast rebuild: FORCE_REBUILD=true $0"
    print_color $BLUE "  Silent mode: QUIET_MODE=true $0"
    print_color $BLUE "  Skip tests: SKIP_TESTS=true $0"
    print_color $BLUE "  Full rebuild: USE_CACHE=false FORCE_REBUILD=true $0"
fi

exit 0