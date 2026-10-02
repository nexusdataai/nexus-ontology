#!/bin/bash
# ============================================================================
# Reset LocalStack for nexus-backend (Linux/macOS)
# ============================================================================
# Completely resets LocalStack by:
# 1. Stopping all services (Gateway + LocalStack)
# 2. Removing Docker volumes and data
# 3. Restarting LocalStack with fresh state
# 4. Re-initializing all resources
#
# Usage:
#   ./reset-localstack.sh              # Full reset and restart
#   ./reset-localstack.sh --no-restart # Reset only, don't restart
#   ./reset-localstack.sh --data-only  # Clear data without stopping container
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

# Parse arguments
NO_RESTART=false
DATA_ONLY=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --no-restart) NO_RESTART=true ;;
        --data-only) DATA_ONLY=true ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-restart  Reset data but don't restart services"
            echo "  --data-only   Clear data without stopping container (uses AWS CLI)"
            echo "  -h, --help    Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0              # Full reset and restart"
            echo "  $0 --no-restart # Reset only"
            echo "  $0 --data-only  # Clear data in running LocalStack"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  Resetting LocalStack for nexus-backend${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""

cd "$PROJECT_ROOT"

export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"
export AWS_DEFAULT_REGION="us-east-1"
ENDPOINT="http://localhost:4566"

if [ "$DATA_ONLY" = true ]; then
    # Clear data without stopping container
    echo -e "${YELLOW}Clearing LocalStack data (container stays running)...${NC}"
    echo ""
    
    # Check if LocalStack is running
    if ! curl -s "$ENDPOINT/_localstack/health" | grep -q '"dynamodb"'; then
        echo -e "${RED}❌ LocalStack is not running. Start it first or use full reset.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ LocalStack is running${NC}"
    
    # Delete all items from DynamoDB tables
    echo ""
    echo -e "${YELLOW}Clearing DynamoDB tables...${NC}"
    
    for table in "TransformationSystem" "nexus-dev-wxcc-task-tracking"; do
        echo "  Clearing table: $table"
        
        if [ "$table" = "TransformationSystem" ]; then
            # Scan and delete items with PK/SK
            items=$(aws dynamodb scan --endpoint-url "$ENDPOINT" --table-name "$table" --output json 2>/dev/null | jq -r '.Items[] | "\(.PK.S)|\(.SK.S)"' 2>/dev/null || true)
            count=0
            while IFS='|' read -r pk sk; do
                if [ -n "$pk" ] && [ -n "$sk" ]; then
                    aws dynamodb delete-item --endpoint-url "$ENDPOINT" --table-name "$table" \
                        --key "{\"PK\":{\"S\":\"$pk\"},\"SK\":{\"S\":\"$sk\"}}" 2>/dev/null || true
                    count=$((count + 1))
                fi
            done <<< "$items"
            echo -e "    ${GREEN}✓ Cleared $count items${NC}"
        else
            # Scan and delete items with task_id
            items=$(aws dynamodb scan --endpoint-url "$ENDPOINT" --table-name "$table" --output json 2>/dev/null | jq -r '.Items[].task_id.S' 2>/dev/null || true)
            count=0
            while read -r task_id; do
                if [ -n "$task_id" ]; then
                    aws dynamodb delete-item --endpoint-url "$ENDPOINT" --table-name "$table" \
                        --key "{\"task_id\":{\"S\":\"$task_id\"}}" 2>/dev/null || true
                    count=$((count + 1))
                fi
            done <<< "$items"
            echo -e "    ${GREEN}✓ Cleared $count items${NC}"
        fi
    done
    
    # Clear S3 buckets
    echo ""
    echo -e "${YELLOW}Clearing S3 buckets...${NC}"
    
    for bucket in "transformation-journey-logs" "transformation-journey-reports" "nexus-dev-wxcc-recordings" "nexus-dev-wxcc-transcripts" "nexus-dev-wxcc-simulator" "test-reports"; do
        echo "  Clearing bucket: $bucket"
        aws s3 rm "s3://$bucket" --endpoint-url "$ENDPOINT" --recursive 2>/dev/null || true
        echo -e "    ${GREEN}✓ Cleared${NC}"
    done
    
    echo ""
    echo -e "${GREEN}✅ LocalStack data cleared!${NC}"
    echo ""
    echo "Resources are empty but still exist. Run seed script to add test data:"
    echo "  python localstack/seed-localstack-data.py"
    exit 0
fi

# Full reset - stop everything first
echo -e "${YELLOW}Step 1: Stopping all services...${NC}"

# Stop Gateway if running
if [ -f .gateway.pid ]; then
    GATEWAY_PID=$(cat .gateway.pid 2>/dev/null || true)
    if [ -n "$GATEWAY_PID" ] && kill -0 "$GATEWAY_PID" 2>/dev/null; then
        echo "  Stopping Gateway (PID: $GATEWAY_PID)..."
        kill "$GATEWAY_PID" 2>/dev/null || true
        sleep 2
        kill -9 "$GATEWAY_PID" 2>/dev/null || true
    fi
    rm -f .gateway.pid
fi

# Clean up gateway logs
rm -f gateway.log gateway-error.log 2>/dev/null || true

# Stop LocalStack and remove volumes
echo "  Stopping LocalStack and removing volumes..."
docker compose -f docker-compose-localstack.yml down -v 2>/dev/null || true

echo -e "${GREEN}✓ Services stopped${NC}"

# Remove local data directory
echo ""
echo -e "${YELLOW}Step 2: Removing local data...${NC}"

if [ -d "localstack-data" ]; then
    rm -rf localstack-data
    echo -e "${GREEN}✓ Removed localstack-data directory${NC}"
else
    echo -e "${GREEN}✓ No local data to remove${NC}"
fi

# Remove any orphaned Docker volumes
echo ""
echo -e "${YELLOW}Step 3: Cleaning up Docker resources...${NC}"
docker volume prune -f 2>/dev/null || true
echo -e "${GREEN}✓ Docker volumes cleaned${NC}"

if [ "$NO_RESTART" = true ]; then
    echo ""
    echo -e "${CYAN}==========================================${NC}"
    echo -e "${GREEN}  ✅ LocalStack reset complete!${NC}"
    echo -e "${CYAN}==========================================${NC}"
    echo ""
    echo "To start LocalStack again, run:"
    echo "  ./localstack/start-localstack.sh"
    echo ""
    echo "Or to start with Gateway:"
    echo "  ./localstack/start-gateway-localstack.sh"
    exit 0
fi

# Restart LocalStack
echo ""
echo -e "${YELLOW}Step 4: Starting fresh LocalStack...${NC}"

docker compose -f docker-compose-localstack.yml up -d

# Wait for health
echo "  Waiting for LocalStack to be healthy..."
timeout=60
while [ $timeout -gt 0 ]; do
    if curl -s "$ENDPOINT/_localstack/health" 2>/dev/null | grep -q '"dynamodb"'; then
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
    echo -n "."
done
echo ""

if [ $timeout -le 0 ]; then
    echo -e "${RED}❌ LocalStack failed to start${NC}"
    echo "   Check logs: docker logs nexus-localstack"
    exit 1
fi

echo -e "${GREEN}✓ LocalStack is healthy${NC}"

# Re-initialize resources
echo ""
echo -e "${YELLOW}Step 5: Initializing resources...${NC}"
"$SCRIPT_DIR/localstack-init.sh"

echo ""
echo -e "${CYAN}==========================================${NC}"
echo -e "${GREEN}  ✅ LocalStack reset and ready!${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""
echo "Service URLs:"
echo "  LocalStack Gateway:  http://localhost:4566"
echo "  DynamoDB Admin:      http://localhost:8001"
echo ""
echo "To seed test data:"
echo "  python localstack/seed-localstack-data.py"
echo ""
echo "To start Gateway:"
echo "  ./localstack/start-gateway-localstack.sh"
echo ""
