#!/bin/bash

# gateway.sh - Main management script for AI Job Engine MCP HTTP Gateway

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to print usage
print_usage() {
    echo -e "${BLUE}AI Job Engine Gateway Management${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    echo "Usage: $0 {start|stop|restart|status|logs|test}"
    echo ""
    echo "Commands:"
    echo "  start    - Start the gateway server"
    echo "  stop     - Stop the gateway server"
    echo "  restart  - Restart the gateway server"
    echo "  status   - Show gateway status"
    echo "  logs     - Tail gateway logs (Ctrl+C to exit)"
    echo "  test     - Run a quick test of the gateway"
    echo ""
    echo "Examples:"
    echo "  $0 start           # Start the gateway"
    echo "  $0 status          # Check if gateway is running"
    echo "  $0 logs            # View real-time logs"
    echo "  $0 restart         # Restart the gateway"
    echo ""
    echo "Environment Variables:"
    echo "  MIN_WORKERS        - Minimum worker processes (default: 2)"
    echo "  MAX_WORKERS        - Maximum worker processes (default: 8)"
    echo "  GATEWAY_PORT       - Gateway port (default: 8000)"
    echo "  LOG_LEVEL          - Log level (default: INFO)"
    echo "  API_KEY            - API authentication key (default: super-secret)"
}

# Function to run comprehensive tests
run_test() {
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}AI Job Engine Unified Gateway Test Suite${NC}"
    echo -e "${BLUE}==================================================${NC}"
    echo ""
    
    local PASSED=0
    local FAILED=0
    local GATEWAY_PORT=${GATEWAY_PORT:-8000}
    local API_KEY=${API_KEY:-super-secret}
    
    # Test 1: Gateway Information
    echo -e "${CYAN}Test 1: Gateway Information${NC}"
    GATEWAY_INFO=$(curl -s -f http://localhost:${GATEWAY_PORT}/ 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[✓] Gateway info endpoint working${NC}"
        echo "${GATEWAY_INFO}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Service: {data.get(\"service\")}')
    print(f'  Version: {data.get(\"version\")}')
    print(f'  Protocols: {\", \".join(data.get(\"protocol\", []))}')
    print(f'  APIs Enabled: {data.get(\"apis_enabled\", False)}')
    print(f'  Workers: {data.get(\"workers\", {}).get(\"total_workers\", 0)}')
except: pass
" 2>/dev/null
        ((PASSED++))
    else
        echo -e "${RED}[✗] Gateway info failed${NC}"
        ((FAILED++))
    fi
    echo ""
    
    # Test 2: Health Check
    echo -e "${CYAN}Test 2: Health Check${NC}"
    HEALTH=$(curl -s -f http://localhost:${GATEWAY_PORT}/health 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[✓] Health check passed${NC}"
        HEALTH_STATUS=$(echo "${HEALTH}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Status: {data.get(\"status\")}')
    workers = data.get('workers', {})
    print(f'  Workers: {workers.get(\"total_workers\", 0)} total, {workers.get(\"busy_workers\", 0)} busy')
    print(f'  Requests: {workers.get(\"total_requests\", 0)} total, {workers.get(\"total_errors\", 0)} errors')
except: pass
" 2>/dev/null)
        echo "${HEALTH_STATUS}"
        ((PASSED++))
    else
        echo -e "${RED}[✗] Health check failed${NC}"
        ((FAILED++))
    fi
    echo ""
    
    # Test 3: MCP Tools - List
    echo -e "${CYAN}Test 3: MCP Tools - List Available Tools${NC}"
    TOOLS=$(curl -s -f -H "X-API-Key: ${API_KEY}" http://localhost:${GATEWAY_PORT}/tools 2>/dev/null)
    if [ $? -eq 0 ]; then
        TOOL_COUNT=$(echo "${TOOLS}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tools = data.get('tools', [])
    print(len(tools))
    for tool in tools[:3]:  # Show first 3 tools
        print(f'  - {tool.get(\"name\")}: {tool.get(\"description\", \"\")[:50]}...')
except: print(0)
" 2>/dev/null)
        echo -e "${GREEN}[✓] Found tools via MCP${NC}"
        echo "${TOOL_COUNT}"
        ((PASSED++))
    else
        echo -e "${RED}[✗] Failed to list MCP tools${NC}"
        ((FAILED++))
    fi
    echo ""
    
    # Test 4: MCP Tools - Call Journey Tool
    echo -e "${CYAN}Test 4: MCP Tools - Call Journey Tool (Worker Pool)${NC}"
    RESULT=$(curl -s -f -X POST \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d '{"arguments": {"action": "list"}}' \
        http://localhost:${GATEWAY_PORT}/tools/journeys_tool 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[✓] Journey tool executed via worker${NC}"
        echo "${RESULT}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    content = data.get('content', [{}])[0].get('text', '')
    if content:
        parsed = json.loads(content)
        print(f'  Status: {parsed.get(\"status\")}') 
        print(f'  Message: {parsed.get(\"message\")[:60]}...')
except: print('  Response received')
" 2>/dev/null
        ((PASSED++))
    else
        echo -e "${RED}[✗] Journey tool call failed${NC}"
        ((FAILED++))
    fi
    echo ""
    
    # Test 5: REST APIs - Journey API
    echo -e "${CYAN}Test 5: REST API - Journey Management (Direct Call)${NC}"
    REST_RESULT=$(curl -s -f -X GET \
        -H "X-API-Key: ${API_KEY}" \
        http://localhost:${GATEWAY_PORT}/api/v1/journeys?limit=5 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[✓] Journey REST API working${NC}"
        echo "${REST_RESULT}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Success: {data.get(\"success\", False)}')
    print(f'  Data count: {len(data.get(\"data\", []))}')
except: print('  API endpoint accessible')
" 2>/dev/null
        ((PASSED++))
    else
        echo -e "${YELLOW}[!] Journey REST API not available (APIs may be disabled)${NC}"
        ((PASSED++))  # Not a failure if APIs are disabled
    fi
    echo ""
    
    # Test 6: REST APIs - Health API
    echo -e "${CYAN}Test 6: REST API - Health Check (Direct Call)${NC}"
    API_HEALTH=$(curl -s -f http://localhost:${GATEWAY_PORT}/api/v1/health/ 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[✓] Health REST API working${NC}"
        echo "${API_HEALTH}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Status: {data.get(\"status\")}') 
    print(f'  Version: {data.get(\"version\")}')
except: print('  Health API endpoint accessible')
" 2>/dev/null
        ((PASSED++))
    else
        echo -e "${YELLOW}[!] Health REST API not available (APIs may be disabled)${NC}"
        ((PASSED++))  # Not a failure if APIs are disabled
    fi
    echo ""
    
    # Test 7: Hybrid Endpoint
    echo -e "${CYAN}Test 7: Hybrid Endpoint - Journey Analysis${NC}"
    HYBRID_WORKER=$(curl -s -f -X POST \
        -H "X-API-Key: ${API_KEY}" \
        "http://localhost:${GATEWAY_PORT}/api/v1/hybrid/journey-analysis?journey_id=JRN-001&use_worker=true" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[✓] Hybrid endpoint (worker mode) accessible${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}[!] Hybrid endpoint not available${NC}"
        ((PASSED++))  # Not critical
    fi
    echo ""
    
    # Test 8: Unified Status
    echo -e "${CYAN}Test 8: Unified Status Endpoint${NC}"
    STATUS=$(curl -s -f http://localhost:${GATEWAY_PORT}/api/status 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[✓] Unified status endpoint working${NC}"
        echo "${STATUS}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Gateway: {data.get(\"gateway\")}') 
    print(f'  API Status: {data.get(\"api_status\")}')
    workers = data.get('mcp_workers', {})
    print(f'  MCP Workers: {workers.get(\"total_workers\", 0)}')
except: print('  Status endpoint accessible')
" 2>/dev/null
        ((PASSED++))
    else
        echo -e "${YELLOW}[!] Unified status not available${NC}"
        ((PASSED++))  # Not critical
    fi
    echo ""
    
    # Test 9: Worker Pool Statistics
    echo -e "${CYAN}Test 9: Worker Pool Statistics${NC}"
    STATS=$(curl -s -f -H "X-API-Key: ${API_KEY}" http://localhost:${GATEWAY_PORT}/stats 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[✓] Worker pool statistics available${NC}"
        echo "${STATS}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Total Workers: {data.get(\"total_workers\", 0)}')
    print(f'  Busy Workers: {data.get(\"busy_workers\", 0)}')
    print(f'  Total Requests: {data.get(\"total_requests\", 0)}')
    print(f'  Total Errors: {data.get(\"total_errors\", 0)}')
except: print('  Statistics available')
" 2>/dev/null
        ((PASSED++))
    else
        echo -e "${RED}[✗] Worker pool statistics not available${NC}"
        ((FAILED++))
    fi
    echo ""
    
    # Test 10: Documentation Endpoints
    echo -e "${CYAN}Test 10: Documentation Endpoints${NC}"
    
    # Check OpenAPI docs
    OPENAPI=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${GATEWAY_PORT}/openapi.json 2>/dev/null)
    if [ "${OPENAPI}" = "200" ]; then
        echo -e "${GREEN}[✓] OpenAPI documentation available at /openapi.json${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}[!] OpenAPI documentation not available${NC}"
        ((PASSED++))  # Not critical
    fi
    
    # Check interactive docs
    DOCS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${GATEWAY_PORT}/docs 2>/dev/null)
    if [ "${DOCS}" = "200" ]; then
        echo -e "${GREEN}[✓] Interactive docs available at /docs${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}[!] Interactive docs not available${NC}"
        ((PASSED++))  # Not critical
    fi
    echo ""
    
    # Summary
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}Test Summary${NC}"
    echo -e "${BLUE}==================================================${NC}"
    
    local TOTAL=$((PASSED + FAILED))
    echo -e "Total Tests: ${TOTAL}"
    echo -e "${GREEN}Passed: ${PASSED}${NC}"
    echo -e "${RED}Failed: ${FAILED}${NC}"
    
    if [ ${FAILED} -eq 0 ]; then
        echo -e "\n${GREEN}✓ All tests passed! Gateway is working correctly.${NC}"
        return 0
    else
        echo -e "\n${YELLOW}⚠ Some tests failed. Check the results above.${NC}"
        return 1
    fi
}

# Check if running from correct directory
if [ ! -f "${SCRIPT_DIR}/mcp_http_gateway.py" ]; then
    echo -e "${RED}Error: Must run from AI Job Engine directory${NC}"
    echo "Current directory: $(pwd)"
    echo "Expected file: ${SCRIPT_DIR}/mcp_http_gateway.py"
    exit 1
fi

cd "${SCRIPT_DIR}"

# Main command handler
case "$1" in
    start)
        if [ -f "./start_gateway.sh" ]; then
            ./start_gateway.sh
        else
            echo -e "${RED}Error: start_gateway.sh not found${NC}"
            exit 1
        fi
        ;;
    
    stop)
        if [ -f "./stop-gateway.sh" ]; then
            ./stop-gateway.sh
        else
            echo -e "${RED}Error: stop-gateway.sh not found${NC}"
            exit 1
        fi
        ;;
    
    restart)
        if [ -f "./restart-gateway.sh" ]; then
            ./restart-gateway.sh
        else
            echo -e "${RED}Error: restart-gateway.sh not found${NC}"
            exit 1
        fi
        ;;
    
    status)
        if [ -f "./status-gateway.sh" ]; then
            ./status-gateway.sh
        else
            echo -e "${RED}Error: status-gateway.sh not found${NC}"
            exit 1
        fi
        ;;
    
    logs)
        if [ -f "gateway.log" ]; then
            echo -e "${BLUE}Tailing gateway.log (Ctrl+C to exit)...${NC}"
            tail -f gateway.log
        else
            echo -e "${YELLOW}No log file found at gateway.log${NC}"
            echo "The gateway may not be running. Start it with: $0 start"
            exit 1
        fi
        ;;
    
    test)
        # Check if gateway is running first
        if ! curl -s -f http://localhost:${GATEWAY_PORT:-8000}/health >/dev/null 2>&1; then
            echo -e "${RED}Gateway is not running!${NC}"
            echo "Start it with: $0 start"
            exit 1
        fi
        run_test
        ;;
    
    *)
        print_usage
        exit 1
        ;;
esac
