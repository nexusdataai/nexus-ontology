#!/bin/bash

# Basic incremental test for MCP gateway server
# Tests each operation step by step

# Don't exit on error - we want to run all tests
set +e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
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

test_endpoint() {
    local test_name="$1"
    local endpoint="$2"
    local expected_success="$3"
    
    echo -ne "  Testing $test_name... "
    
    # Make the request
    response=$(curl -s -X GET "$SERVER_URL$endpoint" -H "x-api-key: $API_KEY" 2>/dev/null || true)
    
    if [ -n "$response" ]; then
        # Check if response contains expected elements
        if [ "$expected_success" = "true" ]; then
            echo -e "${GREEN}✅ PASSED${NC}"
            ((PASSED++))
        else
            echo -e "${YELLOW}⚠️ UNEXPECTED SUCCESS${NC}"
            ((FAILED++))
        fi
    else
        if [ "$expected_success" = "false" ]; then
            echo -e "${GREEN}✅ PASSED (Expected failure)${NC}"
            ((PASSED++))
        else
            echo -e "${RED}❌ FAILED${NC}"
            ((FAILED++))
        fi
    fi
}

test_tool_operation() {
    local test_name="$1"
    local tool_name="$2"
    local payload="$3"
    local expected_field="$4"
    
    echo -ne "  Testing $test_name... "
    
    # Make the request
    response=$(curl -s -X POST "$SERVER_URL/tools/$tool_name" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d "$payload" 2>/dev/null || true)
    
    if [ -z "$response" ]; then
        echo -e "${RED}❌ FAILED (No response)${NC}"
        ((FAILED++))
        return
    fi
    
    # Check for expected field in response
    if echo "$response" | jq -e "$expected_field" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo "    Response: $(echo "$response" | jq -c '.' 2>/dev/null || echo "$response" | head -c 100)"
        ((FAILED++))
    fi
}

# Main test execution
print_header "BASIC MCP GATEWAY SERVER TESTS"

echo -e "${BLUE}🔧 Testing server: $SERVER_URL${NC}"
echo -e "${BLUE}🔑 Using API key: ${API_KEY:0:5}...${NC}"
echo ""

# Test 1: Basic connectivity
echo -e "${CYAN}1. Basic Connectivity Tests:${NC}"
test_endpoint "Server root" "/" true
test_endpoint "Health check" "/health" true
echo ""

# Test 2: Tool discovery
echo -e "${CYAN}2. Tool Discovery:${NC}"
echo -ne "  Fetching tool list... "
tools_response=$(curl -s "$SERVER_URL/tools" -H "x-api-key: $API_KEY" 2>/dev/null || true)
if echo "$tools_response" | jq -e '.tools | length > 0' > /dev/null 2>&1; then
    tool_count=$(echo "$tools_response" | jq '.tools | length')
    echo -e "${GREEN}✅ PASSED ($tool_count tools found)${NC}"
    ((PASSED++))
    
    # List the tools
    echo -e "  Tools discovered:"
    echo "$tools_response" | jq -r '.tools[].name' | while read -r tool; do
        echo -e "    • ${CYAN}$tool${NC}"
    done
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi
echo ""

# Test 3: Tool operations
echo -e "${CYAN}3. Basic Tool Operations:${NC}"

# Test list action
test_tool_operation "List journeys" "journeys_tool" \
    '{"arguments": {"action": "list"}}' \
    '.content[0].text | fromjson | .status'

# Test read non-existent
test_tool_operation "Read non-existent journey" "journeys_tool" \
    '{"arguments": {"action": "read", "journey_id": "NONEXISTENT-123"}}' \
    '.content[0].text | fromjson | select(.status == "error")'

# Test invalid action
test_tool_operation "Invalid action handling" "journeys_tool" \
    '{"arguments": {"action": "invalid_action"}}' \
    '.content[0].text | fromjson | select(.status == "error")'

# Test logs tool with error summary instead (doesn't require journey_id)
test_tool_operation "Get error summary" "logs_and_reports_tool" \
    '{"arguments": {"action": "get_error_summary"}}' \
    '.content[0].text | fromjson | .result.status'

echo ""

# Test 4: API Key validation
echo -e "${CYAN}4. API Key Validation:${NC}"
echo -ne "  Testing without API key... "
response=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/tools" 2>/dev/null || true)
if [ "$response" = "422" ]; then
    echo -e "${GREEN}✅ PASSED (Correctly rejected)${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED (Expected 422, got $response)${NC}"
    ((FAILED++))
fi

echo -ne "  Testing with wrong API key... "
response=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/tools" -H "x-api-key: wrong-key" 2>/dev/null || true)
if [ "$response" = "401" ]; then
    echo -e "${GREEN}✅ PASSED (Correctly rejected)${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED (Expected 401, got $response)${NC}"
    ((FAILED++))
fi
echo ""

# Test 5: Response format validation
echo -e "${CYAN}5. Response Format Validation:${NC}"
echo -ne "  Checking MCP response structure... "
response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "list"}}' 2>/dev/null || true)

if echo "$response" | jq -e '.content[0].type == "text"' > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi
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
    echo -e "${GREEN}${BOLD}✅ ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}The MCP gateway server is working correctly.${NC}"
    exit 0
else
    echo -e "${YELLOW}${BOLD}⚠️ SOME TESTS FAILED${NC}"
    echo -e "${YELLOW}Please review the failures above.${NC}"
    exit 1
fi
