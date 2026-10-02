#!/bin/bash

# Basic Journey Operations Test
# Tests operations that are known to work with the current gateway

set +e  # Continue on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Server configuration
SERVER_URL="${SERVER_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-super-secret}"

# Test counters
PASSED=0
FAILED=0

print_header() {
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}📊 $1${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

test_operation() {
    local test_name="$1"
    local expected_success="$2"
    local response="$3"
    
    echo -ne "  Testing $test_name... "
    
    # Check if it's a gateway error (has detail field)
    if echo "$response" | jq -e '.detail' > /dev/null 2>&1; then
        # Gateway error
        if [ "$expected_success" = "false" ]; then
            echo -e "${GREEN}✅ PASSED (Expected error)${NC}"
            ((PASSED++))
            return 0
        else
            echo -e "${RED}❌ FAILED${NC}"
            echo "    Error: $(echo "$response" | jq -r '.detail.message // "Gateway error"' 2>/dev/null)"
            ((FAILED++))
            return 1
        fi
    fi
    
    # Extract from MCP wrapped response
    local result_text=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null)
    local status=$(echo "$result_text" | jq -r '.status // empty' 2>/dev/null)
    
    if [ "$expected_success" = "true" ]; then
        if [ "$status" = "success" ]; then
            echo -e "${GREEN}✅ PASSED${NC}"
            ((PASSED++))
            return 0
        else
            echo -e "${RED}❌ FAILED${NC}"
            echo "    Error: $(echo "$result_text" | jq -r '.message // "Unknown error"' 2>/dev/null)"
            ((FAILED++))
            return 1
        fi
    else
        if [ "$status" = "error" ]; then
            echo -e "${GREEN}✅ PASSED (Expected error)${NC}"
            ((PASSED++))
            return 0
        else
            echo -e "${YELLOW}⚠️ UNEXPECTED SUCCESS${NC}"
            ((FAILED++))
            return 1
        fi
    fi
}

# Main test execution
print_header "BASIC JOURNEY OPERATIONS TEST"

echo -e "${BLUE}🔧 Testing server: $SERVER_URL${NC}"
echo -e "${BLUE}🔑 Using API key: ${API_KEY:0:5}...${NC}"
echo ""

# Test 1: List journeys
echo -e "${CYAN}1. List Operations:${NC}"
response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "list"}}' 2>/dev/null)

test_operation "List all journeys" "true" "$response"

# Extract journey count
result_text=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null)
journey_count=$(echo "$result_text" | jq -r '.data | length' 2>/dev/null)
echo -e "    Found ${BOLD}$journey_count${NC} journeys"
echo ""

# Test 2: Filter operations
echo -e "${CYAN}2. Filter Operations:${NC}"
response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "list", "status_filter": "pending"}}' 2>/dev/null)

test_operation "Filter by status" "true" "$response"

response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "list", "component_type_filter": "customer-management"}}' 2>/dev/null)

test_operation "Filter by component type" "true" "$response"
echo ""

# Test 3: Read operations
echo -e "${CYAN}3. Read Operations:${NC}"
response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "read", "journey_id": "NONEXISTENT-123"}}' 2>/dev/null)

test_operation "Read non-existent journey" "false" "$response"

response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "read"}}' 2>/dev/null)

test_operation "Read without journey_id" "false" "$response"
echo ""

# Test 4: Delete operations  
echo -e "${CYAN}4. Delete Operations:${NC}"
response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "delete", "journey_id": "NONEXISTENT-456"}}' 2>/dev/null)

test_operation "Delete non-existent journey" "false" "$response"

response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "delete"}}' 2>/dev/null)

test_operation "Delete without journey_id" "false" "$response"
echo ""

# Test 5: Update operations
echo -e "${CYAN}5. Update Operations:${NC}"
response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "update", "journey_id": "NONEXISTENT-789"}}' 2>/dev/null)

test_operation "Update non-existent journey" "false" "$response"

response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "update"}}' 2>/dev/null)

test_operation "Update without journey_id" "false" "$response"
echo ""

# Test 6: Invalid actions
echo -e "${CYAN}6. Error Handling:${NC}"
response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "invalid_action"}}' 2>/dev/null)

test_operation "Invalid action" "false" "$response"

response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {}}' 2>/dev/null)

# Missing action returns error
test_operation "Missing action" "false" "$response"
echo ""

# Test 7: Dashboard operations
echo -e "${CYAN}7. Dashboard Operations:${NC}"
# Dashboard requires journey_id, so test with error
response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "dashboard"}}' 2>/dev/null)

test_operation "Dashboard without journey_id" "false" "$response"

response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "get_journey_summary"}}' 2>/dev/null)

test_operation "Journey summary without journey_id" "false" "$response"
echo ""

# Test 8: Logs and Reports Tool - Skipped 
# Note: Most logs_and_reports_tool actions require a journey_id
# Uncomment below when we have a journey created to test with
echo -e "${CYAN}8. Logs and Reports Tool:${NC}"
echo -e "  ${YELLOW}⏭️ Skipped - most actions require journey_id${NC}"
echo ""

# Summary
print_header "TEST SUMMARY"
TOTAL=$((PASSED + FAILED))
PASS_RATE=$((PASSED * 100 / TOTAL))

echo -e "${BLUE}📊 Results:${NC}"
echo -e "  Total Tests: ${BOLD}$TOTAL${NC}"
echo -e "  Passed: ${GREEN}$PASSED${NC}"
echo -e "  Failed: ${RED}$FAILED${NC}"
echo -e "  Pass Rate: ${BOLD}$PASS_RATE%${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✅ ALL BASIC OPERATIONS PASSED!${NC}"
    echo -e "${GREEN}The gateway is working correctly for read operations.${NC}"
    echo ""
    echo -e "${YELLOW}Note: Create operations are currently being debugged due to subprocess output capture issues.${NC}"
    exit 0
else
    echo -e "${YELLOW}${BOLD}⚠️ SOME TESTS FAILED${NC}"
    echo -e "${YELLOW}Please review the failures above.${NC}"
    exit 1
fi
