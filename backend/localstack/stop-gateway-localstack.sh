#!/bin/bash
# Stop Gateway and LocalStack services
# Usage: ./stop-gateway-localstack.sh [--volumes]
#   --volumes: Also remove LocalStack data volumes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🛑 Stopping Gateway + LocalStack..."
echo ""

cd "$PROJECT_ROOT"

# Stop Gateway
if [ -f .gateway.pid ]; then
    GATEWAY_PID=$(cat .gateway.pid)
    if kill -0 $GATEWAY_PID 2>/dev/null; then
        echo "Stopping Gateway (PID: $GATEWAY_PID)..."
        kill $GATEWAY_PID 2>/dev/null || true
        sleep 2
        # Force kill if still running
        if kill -0 $GATEWAY_PID 2>/dev/null; then
            kill -9 $GATEWAY_PID 2>/dev/null || true
        fi
        echo "✓ Gateway stopped"
    else
        echo "Gateway process not running (stale PID file)"
    fi
    rm -f .gateway.pid
else
    # Try to find and kill gateway process
    GATEWAY_PIDS=$(pgrep -f "mcp_http_gateway.py" 2>/dev/null || true)
    if [ -n "$GATEWAY_PIDS" ]; then
        echo "Stopping Gateway processes..."
        echo "$GATEWAY_PIDS" | xargs kill 2>/dev/null || true
        sleep 1
        echo "✓ Gateway stopped"
    else
        echo "No Gateway process found"
    fi
fi

# Clean up log files
rm -f gateway.log gateway-error.log 2>/dev/null || true

# Stop LocalStack
echo ""
echo "Stopping LocalStack..."

if [ "$1" = "--volumes" ] || [ "$1" = "-v" ]; then
    echo "Removing LocalStack with volumes..."
    docker compose -f docker-compose-localstack.yml down -v 2>/dev/null || true
    rm -rf localstack-data 2>/dev/null || true
    echo "✓ LocalStack stopped and volumes removed"
else
    docker compose -f docker-compose-localstack.yml down 2>/dev/null || true
    echo "✓ LocalStack stopped (data preserved)"
    echo "   Use --volumes to also remove data"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅ All services stopped"
echo "════════════════════════════════════════════════════════════"
