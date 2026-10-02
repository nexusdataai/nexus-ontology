#!/bin/bash
# Start LocalStack and Gateway together for local development
# This script provides a single command to start the complete local development environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting LocalStack + Gateway for nexus-backend..."
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   See: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✓ Docker is running"

# Navigate to project root
cd "$PROJECT_ROOT"

# Start LocalStack
echo ""
echo "📦 Starting LocalStack..."
docker compose -f docker-compose-localstack.yml up -d

# Wait for LocalStack health
echo "⏳ Waiting for LocalStack to be healthy..."
timeout=60
while [ $timeout -gt 0 ]; do
    if curl -s http://localhost:4566/_localstack/health 2>/dev/null | grep -q '"dynamodb"'; then
        health_status=$(curl -s http://localhost:4566/_localstack/health 2>/dev/null | grep -o '"dynamodb": "[^"]*"' | cut -d'"' -f4)
        if [ "$health_status" = "running" ] || [ "$health_status" = "available" ]; then
            break
        fi
    fi
    sleep 2
    timeout=$((timeout - 2))
    echo -n "."
done
echo ""

if [ $timeout -le 0 ]; then
    echo "❌ LocalStack failed to start within timeout"
    echo "   Check logs: docker logs nexus-localstack"
    exit 1
fi

echo "✅ LocalStack is ready!"

# Ensure .env.local exists with LocalStack settings
if [ ! -f .env.local ]; then
    if [ -f .env.localstack.example ]; then
        echo ""
        echo "📝 Creating .env.local from template..."
        cp .env.localstack.example .env.local
        echo "✓ Created .env.local"
    else
        echo ""
        echo "⚠️  No .env.localstack.example found. Creating minimal .env.local..."
        cat > .env.local << 'EOF'
# LocalStack Configuration
USE_LOCALSTACK=true
LOCALSTACK_HOST=localhost
LOCALSTACK_PORT=4566
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
LOG_LEVEL=DEBUG
EOF
        echo "✓ Created minimal .env.local"
    fi
else
    # Ensure USE_LOCALSTACK is set to true
    if ! grep -q "USE_LOCALSTACK=true" .env.local; then
        echo ""
        echo "⚠️  .env.local exists but USE_LOCALSTACK may not be set to true"
        echo "   Please verify USE_LOCALSTACK=true in .env.local"
    fi
fi

# Start Gateway
echo ""
echo "🌐 Starting Gateway server..."

# Check if gateway is already running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  Gateway appears to be already running on port 8000"
    echo "   Stop it first or use a different port"
else
    # Start the gateway in background using uv run for proper virtual environment
    nohup uv run python mcp_http_gateway.py --host 0.0.0.0 --port 8000 > gateway.log 2>&1 &
    GATEWAY_PID=$!
    echo $GATEWAY_PID > .gateway.pid
    
    # Wait for gateway to be ready
    echo "⏳ Waiting for Gateway to start..."
    sleep 3
    
    gateway_timeout=30
    while [ $gateway_timeout -gt 0 ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            break
        fi
        sleep 1
        gateway_timeout=$((gateway_timeout - 1))
        echo -n "."
    done
    echo ""
    
    if [ $gateway_timeout -le 0 ]; then
        echo "❌ Gateway failed to start"
        echo "   Check logs: cat gateway.log"
        kill $GATEWAY_PID 2>/dev/null || true
        exit 1
    fi
fi

# Verify LocalStack health through gateway
echo ""
echo "🔍 Verifying LocalStack connectivity through Gateway..."
localstack_status=$(curl -s http://localhost:8000/health/localstack 2>/dev/null | grep -o '"status": "[^"]*"' | head -1 | cut -d'"' -f4)

if [ "$localstack_status" = "healthy" ]; then
    echo "✅ LocalStack connectivity verified!"
else
    echo "⚠️  LocalStack status: $localstack_status"
    echo "   Check: curl http://localhost:8000/health/localstack"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅ Gateway + LocalStack ready!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📍 Service URLs:"
echo "   Gateway:           http://localhost:8000"
echo "   API Docs:          http://localhost:8000/docs"
echo "   LocalStack:        http://localhost:4566"
echo "   DynamoDB Admin:    http://localhost:8001"
echo "   LocalStack Health: http://localhost:8000/health/localstack"
echo ""
echo "📋 Quick Commands:"
echo "   Test Gateway:      curl http://localhost:8000/health"
echo "   Test LocalStack:   curl http://localhost:8000/health/localstack"
echo "   View Gateway Logs: tail -f gateway.log"
echo "   Stop All:          ./localstack/stop-gateway-localstack.sh"
echo ""

if [ -f .gateway.pid ]; then
    echo "Gateway PID: $(cat .gateway.pid)"
fi
