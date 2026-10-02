#!/bin/bash

# Journey MCP Tool HTTP Test Script
# Comprehensive test of all journey management operations via HTTP endpoint

set -e

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test configuration
TEST_JOURNEY_NAME="MCP HTTP Test Journey $(date +%s)"
TEST_DESCRIPTION="Comprehensive MCP HTTP API test journey"
ODA_COMPONENT_TYPE="customer-management"

# Logging configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/test_journey_mcp_http_$(date +%Y-%m-%d_%H-%M-%S).log"

# Logging functions
log_to_file() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $1 | $2" >> "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
    log_to_file "INFO" "$1"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    log_to_file "SUCCESS" "$1"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    log_to_file "ERROR" "$1"
}

log_step() {
    echo -e "${PURPLE}🔄 $1${NC}"
    log_to_file "STEP" "$1"
}

# Initialize log
echo "=== Journey MCP HTTP Test Log - $(date) ===" > "$LOG_FILE"
echo "Server URL: $SERVER_URL" >> "$LOG_FILE"
echo "================================================" >> "$LOG_FILE"

# Test Header
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║         🧪 Journey MCP Tool HTTP API Test Suite            ║${NC}"
echo -e "${YELLOW}║  Testing all journey operations via REST HTTP endpoint     ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

log_info "Starting Journey MCP HTTP Test"
log_info "Log file: $LOG_FILE"
log_info "Endpoint: $SERVER_URL/tools/journeys_tool"

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper function to make API calls
call_journey_api() {
    local payload="$1"
    # Wrap in arguments for MCP
    local wrapped_payload="{\"arguments\": $payload}"
    curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: super-secret" \
        -d "$wrapped_payload"
}

# Helper to check success
check_success() {
    local response="$1"
    # Check for MCP wrapped response
    local result_text=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null)
    if [ -z "$result_text" ] || [ "$result_text" = "null" ]; then
        return 1
    fi
    local status=$(echo "$result_text" | jq -r '.status // "error"')
    [ "$status" = "success" ]
}

# =============================================================================
# TEST 1: LIST JOURNEYS
# =============================================================================
echo -e "\n${PURPLE}📋 TEST 1: List All Journeys${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Listing all journeys"

LIST_RESPONSE=$(call_journey_api '{"action": "list"}')
echo "$LIST_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if check_success "$LIST_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    INITIAL_COUNT=$(echo "$LIST_RESPONSE" | jq -r '.result.data | length')
    log_success "List journeys successful - Found: $INITIAL_COUNT journeys"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "List journeys failed"
fi

# =============================================================================
# TEST 2: CREATE JOURNEY
# =============================================================================
echo -e "\n${PURPLE}🆕 TEST 2: Create New Journey${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Creating journey with metadata"

CREATE_PAYLOAD=$(cat <<EOF
{
    "action": "create",
    "name": "$TEST_JOURNEY_NAME",
    "description": "$TEST_DESCRIPTION",
    "odaComponentType": "$ODA_COMPONENT_TYPE",
    "priority": "high"
}
EOF
)

CREATE_RESPONSE=$(call_journey_api "$CREATE_PAYLOAD")
echo "$CREATE_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if check_success "$CREATE_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    result_text=$(echo "$CREATE_RESPONSE" | jq -r '.content[0].text' 2>/dev/null)
    JOURNEY_ID=$(echo "$result_text" | jq -r '.journey_id')
    log_success "Journey created successfully: $JOURNEY_ID"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "Journey creation failed"
    exit 1
fi

# =============================================================================
# TEST 3: READ JOURNEY
# =============================================================================
echo -e "\n${PURPLE}📖 TEST 3: Read Journey Details${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Reading journey details"

READ_RESPONSE=$(call_journey_api "{\"action\": \"read\", \"journey_id\": \"$JOURNEY_ID\"}")
echo "$READ_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if check_success "$READ_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_success "Journey retrieved successfully"
    
    # Display journey info
    JOURNEY_NAME=$(echo "$READ_RESPONSE" | jq -r '.result.data.metadata.name')
    JOURNEY_STATUS=$(echo "$READ_RESPONSE" | jq -r '.result.data.metadata.status')
    log_info "  Name: $JOURNEY_NAME"
    log_info "  Status: $JOURNEY_STATUS"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "Read journey failed"
fi

# =============================================================================
# TEST 4: ADD DEFAULT STAGES
# =============================================================================
echo -e "\n${PURPLE}🏗️  TEST 4: Add Default Stages${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Adding 6 default stages"

STAGES_RESPONSE=$(call_journey_api "{\"action\": \"add_default_stages\", \"journey_id\": \"$JOURNEY_ID\"}")
echo "$STAGES_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if check_success "$STAGES_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_success "Default stages added successfully"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "Add default stages failed"
fi

# =============================================================================
# TEST 5: LIST STAGES
# =============================================================================
echo -e "\n${PURPLE}📋 TEST 5: List Journey Stages${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Listing journey stages"

LIST_STAGES_RESPONSE=$(call_journey_api "{\"action\": \"list_stages\", \"journey_id\": \"$JOURNEY_ID\"}")
echo "$LIST_STAGES_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if check_success "$LIST_STAGES_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    STAGES_COUNT=$(echo "$LIST_STAGES_RESPONSE" | jq -r '.result.data | length')
    log_success "Stages listed successfully - Found: $STAGES_COUNT stages"
    
    # Show stage names
    echo "$LIST_STAGES_RESPONSE" | jq -r '.result.data[] | "  - \(.stageId): \(.name)"' | head -6
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "List stages failed"
fi

# =============================================================================
# TEST 6: ADD RULE
# =============================================================================
echo -e "\n${PURPLE}🧠 TEST 6: Add Second Brain Rule${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Adding custom Second Brain rule"

ADD_RULE_PAYLOAD=$(cat <<'EOF'
{
    "action": "add_rule",
    "journey_id": "JOURNEY_ID_PLACEHOLDER",
    "stage_id": "raw_analysis",
    "rule_data": {
        "title": "MCP HTTP Test Rule",
        "description": "Test rule added via MCP HTTP API",
        "type": "field_mapping",
        "priority": "high",
        "scope": "stage",
        "context": "Field mapping for raw analysis stage",
        "content": "Test rule content for field mapping"
    }
}
EOF
)

ADD_RULE_PAYLOAD="${ADD_RULE_PAYLOAD//JOURNEY_ID_PLACEHOLDER/$JOURNEY_ID}"

ADD_RULE_RESPONSE=$(call_journey_api "$ADD_RULE_PAYLOAD")
echo "$ADD_RULE_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if check_success "$ADD_RULE_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    RULE_ID=$(echo "$ADD_RULE_RESPONSE" | jq -r '.result.rule_id // "unknown"')
    log_success "Rule added successfully"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "Add rule failed"
fi

# =============================================================================
# TEST 7: LIST RULES
# =============================================================================
echo -e "\n${PURPLE}📋 TEST 7: List Second Brain Rules${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Listing Second Brain rules"

LIST_RULES_RESPONSE=$(call_journey_api "{\"action\": \"list_rules\", \"journey_id\": \"$JOURNEY_ID\"}")
echo "$LIST_RULES_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if check_success "$LIST_RULES_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    RULES_COUNT=$(echo "$LIST_RULES_RESPONSE" | jq -r '.result.data | length')
    log_success "Rules listed successfully - Found: $RULES_COUNT rules"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "List rules failed"
fi

# =============================================================================
# TEST 8: UPDATE JOURNEY
# =============================================================================
echo -e "\n${PURPLE}🔄 TEST 8: Update Journey Metadata${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Updating journey metadata"

UPDATE_PAYLOAD=$(cat <<EOF
{
    "action": "update",
    "journey_id": "$JOURNEY_ID",
    "journey_data": {
        "description": "UPDATED: $TEST_DESCRIPTION",
        "priority": "critical",
        "status": "running"
    }
}
EOF
)

UPDATE_RESPONSE=$(call_journey_api "$UPDATE_PAYLOAD")
echo "$UPDATE_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if check_success "$UPDATE_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_success "Journey updated successfully"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "Update journey failed"
fi

# =============================================================================
# TEST 9: GET DASHBOARD
# =============================================================================
echo -e "\n${PURPLE}📊 TEST 9: Get Journey Dashboard${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Getting journey dashboard view"

DASHBOARD_RESPONSE=$(call_journey_api "{\"action\": \"dashboard\", \"journey_id\": \"$JOURNEY_ID\"}")
echo "$DASHBOARD_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if check_success "$DASHBOARD_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_success "Dashboard retrieved successfully"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "Dashboard retrieval failed"
fi

# =============================================================================
# TEST 10: DELETE JOURNEY
# =============================================================================
echo -e "\n${PURPLE}🗑️  TEST 10: Delete Journey${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Deleting journey and all related data"

DELETE_RESPONSE=$(call_journey_api "{\"action\": \"delete\", \"journey_id\": \"$JOURNEY_ID\", \"confirm\": true}")
echo "$DELETE_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if check_success "$DELETE_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_success "Journey deleted successfully"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "Delete journey failed"
fi

# =============================================================================
# TEST 11: VERIFY DELETION
# =============================================================================
echo -e "\n${PURPLE}✅ TEST 11: Verify Journey Deletion${NC}"
echo "================================"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
log_step "Verifying journey is deleted"

sleep 1

VERIFY_RESPONSE=$(call_journey_api "{\"action\": \"read\", \"journey_id\": \"$JOURNEY_ID\"}")
echo "$VERIFY_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null

if ! check_success "$VERIFY_RESPONSE"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_success "Journey deletion verified (not found)"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "Journey still exists after deletion"
fi

# =============================================================================
# FINAL SUMMARY
# =============================================================================
echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     📊 TEST SUMMARY                          ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║ Total Tests:   $TOTAL_TESTS"
echo -e "${BLUE}║ ${GREEN}Passed:        $PASSED_TESTS${NC}"
echo -e "${BLUE}║ ${RED}Failed:        $FAILED_TESTS${NC}"
SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo -e "${BLUE}║ Success Rate:  $SUCCESS_RATE%"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"

# Test details
echo -e "\n${CYAN}📋 Tests Executed:${NC}"
echo "  1. ✅ List Journeys"
echo "  2. ✅ Create Journey"
echo "  3. ✅ Read Journey Details"
echo "  4. ✅ Add Default Stages (6 stages)"
echo "  5. ✅ List Stages"
echo "  6. ✅ Add Second Brain Rule"
echo "  7. ✅ List Rules"
echo "  8. ✅ Update Journey"
echo "  9. ✅ Get Dashboard"
echo " 10. ✅ Delete Journey"
echo " 11. ✅ Verify Deletion"

# Log summary
log_info "================================================"
log_info "TEST SUMMARY"
log_info "================================================"
log_info "Total Tests: $TOTAL_TESTS"
log_info "Passed: $PASSED_TESTS"
log_info "Failed: $FAILED_TESTS"
log_info "Success Rate: $SUCCESS_RATE%"
log_info "================================================"

echo -e "\n${CYAN}📁 Full test logs saved to: $LOG_FILE${NC}"

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 ALL TESTS PASSED! MCP HTTP API WORKING CORRECTLY! 🎉${NC}"
    exit 0
else
    echo -e "\n${RED}❌ SOME TESTS FAILED - CHECK LOG FOR DETAILS${NC}"
    exit 1
fi

