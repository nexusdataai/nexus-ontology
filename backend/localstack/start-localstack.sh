#!/bin/bash
# ============================================================================
# Start LocalStack for nexus-backend development (Linux/macOS)
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🚀 Starting LocalStack for nexus-backend...${NC}"
echo ""

# Check Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker is running
if ! docker info &> /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Check docker-compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo -e "${RED}❌ docker-compose is not installed.${NC}"
    exit 1
fi

# Determine docker-compose command
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo -e "${GREEN}✓ docker-compose available${NC}"
echo ""

# Start services
echo -e "${YELLOW}Starting LocalStack services...${NC}"
cd "$PROJECT_ROOT"
$COMPOSE_CMD -f docker-compose-localstack.yml up -d

# Wait for LocalStack to be healthy
echo ""
echo -e "${YELLOW}⏳ Waiting for LocalStack to be healthy...${NC}"
timeout=60
while [ $timeout -gt 0 ]; do
    if curl -s http://localhost:4566/_localstack/health 2>/dev/null | grep -q '"dynamodb"'; then
        break
    fi
    echo "  Waiting... ($timeout seconds remaining)"
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    echo -e "${RED}❌ LocalStack failed to start within timeout${NC}"
    echo "   Check logs: docker logs nexus-localstack"
    exit 1
fi

echo -e "${GREEN}✓ LocalStack is healthy${NC}"

# Run initialization script
echo ""
echo -e "${YELLOW}Running initialization script...${NC}"
"$SCRIPT_DIR/localstack-init.sh"

echo ""
echo -e "${GREEN}✅ LocalStack is ready!${NC}"
echo ""
echo -e "${CYAN}📍 Service URLs:${NC}"
echo "   LocalStack Gateway:  http://localhost:4566"
echo "   DynamoDB Admin:      http://localhost:8001"
echo ""
echo -e "${CYAN}🔧 Environment variables to set:${NC}"
echo "   export USE_LOCALSTACK=true"
echo "   export LOCALSTACK_HOST=localhost"
echo ""
echo -e "${CYAN}📝 Or copy the example env file:${NC}"
echo "   cp .env.localstack.example .env.local"
echo ""
