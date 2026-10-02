#!/bin/bash
# ============================================================================
# Stop LocalStack for nexus-backend (Linux/macOS)
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
REMOVE_VOLUMES=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -v|--volumes) REMOVE_VOLUMES=true ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --volumes  Remove volumes (delete all data)"
            echo "  -h, --help     Show this help message"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

echo -e "${CYAN}🛑 Stopping LocalStack for nexus-backend...${NC}"
echo ""

# Determine docker-compose command
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

cd "$PROJECT_ROOT"

if [ "$REMOVE_VOLUMES" = true ]; then
    echo -e "${YELLOW}Stopping services and removing volumes...${NC}"
    $COMPOSE_CMD -f docker-compose-localstack.yml down -v
    echo -e "${GREEN}✓ Services stopped and volumes removed${NC}"
else
    echo -e "${YELLOW}Stopping services...${NC}"
    $COMPOSE_CMD -f docker-compose-localstack.yml down
    echo -e "${GREEN}✓ Services stopped${NC}"
fi

echo ""
echo -e "${GREEN}✅ LocalStack stopped successfully${NC}"
echo ""
echo "To remove all data, run: $0 --volumes"
echo ""
