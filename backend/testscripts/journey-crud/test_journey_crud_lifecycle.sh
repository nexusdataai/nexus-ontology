#!/bin/bash

# Journey CRUD Lifecycle Test
# Tests complete journey lifecycle: Create → Update → Delete
# Verifies all related records are properly managed

set -e

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"
TEST_JOURNEY_NAME="Test Journey CRUD $(date +%s)"
TEST_DESCRIPTION="Comprehensive CRUD test journey with full lifecycle validation"
ODA_COMPONENT_TYPE="product-management"

# Function to parse URL and extract components
parse_url() {
    local url="$1"
    
    # Remove protocol (http:// or https://)
    local url_no_protocol="${url#http://}"
    url_no_protocol="${url_no_protocol#https://}"
    
    # Extract host and port
    if [[ "$url_no_protocol" == *":"* ]]; then
        HOST="${url_no_protocol%:*}"
        PORT="${url_no_protocol#*:}"
        # Remove any path after port
        PORT="${PORT%%/*}"
    else
        HOST="$url_no_protocol"
        # Remove any path after host
        HOST="${HOST%%/*}"
        PORT="8000"  # Default port
    fi
    
    # Reconstruct the URL
    if [[ "$url" == https://* ]]; then
        SERVER_URL="https://$HOST:$PORT"
    else
        SERVER_URL="http://$HOST:$PORT"
    fi
}

# Function to show usage
show_usage() {
    echo -e "Journey CRUD Lifecycle Test"
    echo ""
    echo -e "Usage: $0 [URL]"
    echo ""
    echo -e "Arguments:"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo ""
    echo -e "Examples:"
    echo -e "  $0                                    # Test on localhost:8000"
    echo -e "  $0 http://192.168.1.100:8000          # Test on remote server"
    echo -e "  $0 https://api.company.com            # Use HTTPS connection"
    echo ""
    echo -e "Description:"
    echo -e "  Tests complete journey lifecycle: Create → Update → Delete → Verify"
    echo -e "  Verifies all related records are properly managed."
    echo ""
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_usage
                exit 0
                ;;
            http://*|https://*)
                parse_url "$1"
                shift
                ;;
            -*)
                echo -e "❌ Unknown option: $1"
                echo -e "💡 Use URL format instead: $0 http://host:port"
                show_usage
                exit 1
                ;;
            *)
                echo -e "❌ Unknown argument: $1"
                echo -e "💡 Use URL format: $0 http://host:port"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/test_journey_crud_$(date +%Y-%m-%d_%H-%M-%S).log"
EXECUTION_ID="CRUD_$(date +%s)"

# Initialize logging
setup_logging() {
    echo "=== Journey CRUD Lifecycle Test Log - $(date) ===" > "$LOG_FILE"
    echo "Execution ID: $EXECUTION_ID" >> "$LOG_FILE"
    echo "Server URL: $SERVER_URL" >> "$LOG_FILE"
    echo "Test Journey Name: $TEST_JOURNEY_NAME" >> "$LOG_FILE"
    echo "ODA Component Type: $ODA_COMPONENT_TYPE" >> "$LOG_FILE"
    echo "Log File: $LOG_FILE" >> "$LOG_FILE"
    echo "=========================================" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
}

# Enhanced logging functions
log_to_file() {
    local level="$1"
    local message="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $level | $message" >> "$LOG_FILE"
}

# Helper functions
log_info() {
    local message="$1"
    echo -e "${BLUE}ℹ️  $message${NC}"
    log_to_file "INFO" "$message"
}

log_success() {
    local message="$1"
    echo -e "${GREEN}✅ $message${NC}"
    log_to_file "SUCCESS" "$message"
}

log_error() {
    local message="$1"
    echo -e "${RED}❌ $message${NC}"
    log_to_file "ERROR" "$message"
}

log_warning() {
    local message="$1"
    echo -e "${YELLOW}⚠️  $message${NC}"
    log_to_file "WARNING" "$message"
}

log_step() {
    local message="$1"
    echo -e "${PURPLE}🔄 $message${NC}"
    log_to_file "STEP" "$message"
}

log_debug() {
    local message="$1"
    log_to_file "DEBUG" "$message"
}

# Function to get DynamoDB record count
get_dynamodb_count() {
    local count
    count=$(aws dynamodb scan \
        --table-name TransformationSystem \
        --select COUNT \
        --output json 2>/dev/null | jq -r '.Count // 0' 2>/dev/null)
    
    # Ensure we always return a valid number
    if [[ "$count" =~ ^[0-9]+$ ]]; then
        echo "$count"
    else
        log_debug "DynamoDB scan failed or returned invalid count: '$count'"
        echo "0"
    fi
}

# Function to get journey-specific record count
get_journey_record_count() {
    local journey_id="$1"
    
    # Validate input
    if [ -z "$journey_id" ]; then
        log_debug "get_journey_record_count: No journey_id provided"
        echo "0"
        return
    fi
    
    # Don't remove the JRN- prefix, use the full journey ID
    local count
    
    count=$(aws dynamodb query \
        --table-name TransformationSystem \
        --key-condition-expression "PK = :pk" \
        --expression-attribute-values "{\":pk\":{\"S\":\"JOURNEY#${journey_id}\"}}" \
        --select COUNT \
        --output json 2>/dev/null | jq -r '.Count // 0' 2>/dev/null)
    
    # Ensure we always return a valid number
    if [[ "$count" =~ ^[0-9]+$ ]]; then
        echo "$count"
    else
        log_debug "DynamoDB query failed or returned invalid count for journey $journey_id: '$count'"
        echo "0"
    fi
}

# Function to get journey count via API
get_api_journey_count() {
    local response
    response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: super-secret" \
        -d '{"arguments": {"action": "list"}}' 2>/dev/null)
    
    local count
    # Extract the MCP tool response from content[0].text and parse it
    local result_text=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null)
    count=$(echo "$result_text" | jq -r '.data | length' 2>/dev/null)
    
    # Ensure we always return a valid number
    if [[ "$count" =~ ^[0-9]+$ ]]; then
        echo "$count"
    else
        log_debug "API journey count failed or returned invalid count: '$count'"
        echo "0"
    fi
}

# API helper functions
call_api() {
    local action="$1"
    local data="$2"
    log_debug "API Call - Action: $action, Data: $data"
    # Wrap data in arguments for MCP tool
    local wrapped_data="{\"arguments\": $data}"
    local response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: super-secret" \
        -d "$wrapped_data")
    log_debug "API Response: $response"
    echo "$response"
}

# Function to extract journey ID from response
extract_journey_id() {
    # Extract the MCP tool response from content[0].text and parse it
    local result_text=$(echo "$1" | jq -r '.content[0].text' 2>/dev/null)
    echo "$result_text" | jq -r '.journey_id // .journeyId // empty'
}

# Function to check API response status
check_api_success() {
    local response="$1"
    # Extract the MCP tool response from content[0].text and parse it
    local result_text=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null)
    local status=$(echo "$result_text" | jq -r '.status // empty' 2>/dev/null)
    
    if [ "$status" = "success" ]; then
        return 0
    else
        log_error "API call failed: $(echo "$result_text" | jq -r '.message // "Unknown error"' 2>/dev/null)"
        return 1
    fi
}

# Parse command line arguments first
parse_arguments "$@"

# Initialize logging
setup_logging

# Test Header
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║              🔄 Journey CRUD Lifecycle Test                 ║${NC}"
echo -e "${YELLOW}║          Create → Update → Delete → Verify                  ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

log_info "Starting Journey CRUD Lifecycle Test"
log_info "Execution ID: $EXECUTION_ID"
log_info "Log file: $LOG_FILE"
log_info "Test Journey Name: $TEST_JOURNEY_NAME"

# Phase 1: Initial State
echo -e "\n${PURPLE}📊 PHASE 1: Initial State Assessment${NC}"
echo "=================================================="

log_step "Getting initial DynamoDB record count"
INITIAL_DB_COUNT=$(get_dynamodb_count)
log_info "Initial DynamoDB records: $INITIAL_DB_COUNT"

log_step "Getting initial journey count via API"
INITIAL_JOURNEY_COUNT=$(get_api_journey_count)
log_info "Initial journey count: $INITIAL_JOURNEY_COUNT"

# Phase 2: Journey Creation
echo -e "\n${PURPLE}🆕 PHASE 2: Journey Creation with Metadata${NC}"
echo "=============================================="

log_step "Creating journey with comprehensive metadata and stages"

CREATE_DATA='{
    "action": "create",
    "journey_data": {
        "name": "'"$TEST_JOURNEY_NAME"'",
        "description": "'"$TEST_DESCRIPTION"'",
        "odaComponentType": "'"$ODA_COMPONENT_TYPE"'",
        "priority": "high",
        "stages": [
            {"stageId": "raw_analysis", "name": "Raw Analysis", "order": 1},
            {"stageId": "stripped_schema", "name": "Stripped Schema", "order": 2},
            {"stageId": "tmf_mapping", "name": "TMF Mapping", "order": 3},
            {"stageId": "migration_planning", "name": "Migration Planning", "order": 4},
            {"stageId": "data_migration", "name": "Data Migration", "order": 5},
            {"stageId": "verification_validation", "name": "Verification", "order": 6}
        ]
    }
}'

CREATE_RESPONSE=$(call_api "create" "$CREATE_DATA")

if check_api_success "$CREATE_RESPONSE"; then
    JOURNEY_ID=$(extract_journey_id "$CREATE_RESPONSE")
    if [ -n "$JOURNEY_ID" ]; then
        log_success "Journey created successfully: $JOURNEY_ID"
        
        # Extract stages information from create response
        # Extract from MCP wrapped response
        CREATE_RESULT_TEXT=$(echo "$CREATE_RESPONSE" | jq -r '.content[0].text' 2>/dev/null)
        STAGES_ADDED=$(echo "$CREATE_RESULT_TEXT" | jq -r '.totalStages // 6' 2>/dev/null)
        TOTAL_STAGES=$STAGES_ADDED
        log_info "Journey created with $STAGES_ADDED stages"
    else
        log_error "Journey created but no ID returned"
        exit 1
    fi
else
    log_error "Failed to create journey"
    exit 1
fi

# Verify both journey and stages in DynamoDB
log_step "Verifying journey and stages creation in DynamoDB"
JOURNEY_RECORDS_AFTER_STAGES=$(get_journey_record_count "$JOURNEY_ID")
log_info "Journey records after creation: $JOURNEY_RECORDS_AFTER_STAGES"

# Ensure STAGES_ADDED is a valid number
STAGES_ADDED=${STAGES_ADDED:-6}
EXPECTED_RECORDS=$((1 + STAGES_ADDED))  # 1 metadata + stages
log_info "Expected records: ~$EXPECTED_RECORDS (1 metadata + $STAGES_ADDED stages)"

# Ensure variables are valid numbers before comparison
JOURNEY_RECORDS_AFTER_STAGES=${JOURNEY_RECORDS_AFTER_STAGES:-0}
EXPECTED_RECORDS=${EXPECTED_RECORDS:-0}

if [ "$JOURNEY_RECORDS_AFTER_STAGES" -ge "$EXPECTED_RECORDS" ]; then
    log_success "Journey and stages verified in DynamoDB: $JOURNEY_RECORDS_AFTER_STAGES records"
else
    log_warning "Expected ~$EXPECTED_RECORDS records but found $JOURNEY_RECORDS_AFTER_STAGES"
fi

# Phase 4: Journey Update
echo -e "\n${PURPLE}🔄 PHASE 3: Journey Metadata Update${NC}"
echo "==================================="

log_step "Updating journey metadata"

UPDATE_DATA="{
    \"action\": \"update\",
    \"journey_id\": \"$JOURNEY_ID\",
    \"journey_data\": {
        \"description\": \"UPDATED: $TEST_DESCRIPTION - Modified in CRUD test\",
        \"priority\": \"critical\",
        \"estimatedDuration\": \"3h 15m\",
        \"tags\": [\"test\", \"crud\", \"validation\", \"updated\"],
        \"version\": \"1.1.0\",
        \"lastModified\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
        \"status\": \"active\"
    }
}"

UPDATE_RESPONSE=$(call_api "update" "$UPDATE_DATA")

if check_api_success "$UPDATE_RESPONSE"; then
    log_success "Journey metadata updated successfully"
else
    log_error "Failed to update journey metadata"
    exit 1
fi

# Phase 5: Verification of Update
echo -e "\n${PURPLE}🔍 PHASE 4: Update Verification${NC}"
echo "============================="

log_step "Verifying journey update via API"

READ_DATA="{
    \"action\": \"read\",
    \"journey_id\": \"$JOURNEY_ID\"
}"

READ_RESPONSE=$(call_api "read" "$READ_DATA")

if check_api_success "$READ_RESPONSE"; then
    # Extract from MCP wrapped response
    READ_RESULT_TEXT=$(echo "$READ_RESPONSE" | jq -r '.content[0].text' 2>/dev/null)
    UPDATED_DESCRIPTION=$(echo "$READ_RESULT_TEXT" | jq -r '.data.metadata.description // empty' 2>/dev/null)
    UPDATED_VERSION=$(echo "$READ_RESULT_TEXT" | jq -r '.data.metadata.version // empty' 2>/dev/null)
    
    if [[ "$UPDATED_DESCRIPTION" == *"UPDATED"* ]]; then
        log_success "Description update verified: ✓"
    else
        log_warning "Description update not reflected"
    fi
    
    if [ "$UPDATED_VERSION" = "1.1.0" ]; then
        log_success "Version update verified: ✓"
    else
        log_warning "Version update not reflected"
    fi
else
    log_error "Failed to verify journey update"
fi

# Phase 6: Pre-Delete State
echo -e "\n${PURPLE}📋 PHASE 5: Pre-Delete State Assessment${NC}"
echo "======================================="

# Get current state before deletion
CURRENT_DB_COUNT=$(get_dynamodb_count)
CURRENT_JOURNEY_RECORDS=$(get_journey_record_count "$JOURNEY_ID")

CURRENT_JOURNEY_COUNT=$(get_api_journey_count)

log_info "DynamoDB records before delete: $CURRENT_DB_COUNT"
log_info "Journey-specific records before delete: $CURRENT_JOURNEY_RECORDS"
log_info "Total journeys before delete: $CURRENT_JOURNEY_COUNT"

# Phase 7: Journey Deletion
echo -e "\n${PURPLE}🗑️  PHASE 6: Journey Deletion${NC}"
echo "=============================="

log_step "Deleting journey and all related records"

DELETE_DATA="{
    \"action\": \"delete\",
    \"journey_id\": \"$JOURNEY_ID\",
    \"confirm\": true
}"

DELETE_RESPONSE=$(call_api "delete" "$DELETE_DATA")

if check_api_success "$DELETE_RESPONSE"; then
    log_success "Delete API call successful"
else
    log_error "Failed to delete journey"
    exit 1
fi

# Phase 8: Post-Delete Verification
echo -e "\n${PURPLE}✅ PHASE 7: Post-Delete Verification${NC}"
echo "===================================="

log_step "Verifying complete deletion"

# Wait a moment for deletion to complete
sleep 2

# Check DynamoDB record counts
FINAL_DB_COUNT=$(get_dynamodb_count)
FINAL_JOURNEY_RECORDS=$(get_journey_record_count "$JOURNEY_ID")

# Check API journey count
LIST_RESPONSE_FINAL=$(call_api "list" '{"action": "list"}')
# Extract from MCP wrapped response
LIST_FINAL_RESULT_TEXT=$(echo "$LIST_RESPONSE_FINAL" | jq -r '.content[0].text' 2>/dev/null)
FINAL_JOURNEY_COUNT=$(echo "$LIST_FINAL_RESULT_TEXT" | jq -r '.metadata.total_count // 0' 2>/dev/null)

# Ensure all variables are valid numbers before calculations
CURRENT_DB_COUNT=${CURRENT_DB_COUNT:-0}
FINAL_DB_COUNT=${FINAL_DB_COUNT:-0}
CURRENT_JOURNEY_COUNT=${CURRENT_JOURNEY_COUNT:-0}
FINAL_JOURNEY_COUNT=${FINAL_JOURNEY_COUNT:-0}

# Calculate reductions
DB_REDUCTION=$((CURRENT_DB_COUNT - FINAL_DB_COUNT))
JOURNEY_COUNT_REDUCTION=$((CURRENT_JOURNEY_COUNT - FINAL_JOURNEY_COUNT))

log_info "DynamoDB records after delete: $FINAL_DB_COUNT"
log_info "Journey-specific records after delete: $FINAL_JOURNEY_RECORDS"
log_info "Total journeys after delete: $FINAL_JOURNEY_COUNT"

echo -e "\n${BLUE}📊 DELETION ANALYSIS${NC}"
echo "===================="
echo "DynamoDB reduction: $DB_REDUCTION records"
echo "Journey count reduction: $JOURNEY_COUNT_REDUCTION"
echo "Journey-specific records remaining: $FINAL_JOURNEY_RECORDS"
echo "Expected deletion: ~$((1 + ${STAGES_ADDED:-6})) records (1 metadata + ${STAGES_ADDED:-6} stages)"

# Phase 9: Results Summary
echo -e "\n${PURPLE}🎯 PHASE 8: CRUD Lifecycle Results Summary${NC}"
echo "==========================================="

# Validation checks
ALL_CHECKS_PASSED=true

# Ensure variable is a valid number before comparison
JOURNEY_COUNT_REDUCTION=${JOURNEY_COUNT_REDUCTION:-0}

if [ "$JOURNEY_COUNT_REDUCTION" -eq 1 ]; then
    log_success "API count correctly reduced by 1"
else
    log_error "API count reduction incorrect: expected 1, got $JOURNEY_COUNT_REDUCTION"
    ALL_CHECKS_PASSED=false
fi

# Ensure variable is a valid number before comparison
FINAL_JOURNEY_RECORDS=${FINAL_JOURNEY_RECORDS:-0}

if [ "$FINAL_JOURNEY_RECORDS" -eq 0 ]; then
    log_success "All journey-specific records removed from DynamoDB"
else
    log_error "Journey records still remain in DynamoDB: $FINAL_JOURNEY_RECORDS"
    ALL_CHECKS_PASSED=false
fi

EXPECTED_DELETION=$((1 + ${STAGES_ADDED:-6}))
if [ "$DB_REDUCTION" -ge "$EXPECTED_DELETION" ]; then
    log_success "DynamoDB records properly deleted: $DB_REDUCTION records (expected: ~$EXPECTED_DELETION)"
elif [ "$DB_REDUCTION" -gt 0 ]; then
    log_warning "Some DynamoDB records deleted: $DB_REDUCTION records (expected: ~$EXPECTED_DELETION)"
else
    log_error "No DynamoDB records were deleted"
    ALL_CHECKS_PASSED=false
fi

# Final summary box
echo -e "\n${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    📋 FINAL RESULTS                          ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║ Journey ID: $JOURNEY_ID"
echo "║ Creation: ✅ SUCCESS"
echo "║ Default Stages: ${STAGES_ADDED:-0}/${TOTAL_STAGES:-6} stages added"
echo "║ Update: ✅ SUCCESS"
echo "║ Deletion: ✅ SUCCESS"
echo "║ API Count Change: $JOURNEY_COUNT_REDUCTION"
echo "║ DynamoDB Records Deleted: $DB_REDUCTION (expected: ~$EXPECTED_DELETION)"
echo "║ Journey Records Remaining: $FINAL_JOURNEY_RECORDS"

if [ "$ALL_CHECKS_PASSED" = true ]; then
    echo "║ Overall Status: 🎉 ALL TESTS PASSED"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${GREEN}🎉 CRUD LIFECYCLE TEST COMPLETED SUCCESSFULLY! 🎉${NC}"
    
    # Final success logging
    log_success "CRUD Lifecycle Test Completed Successfully"
    log_info "Journey created: $JOURNEY_ID"
    log_info "Stages added: ${STAGES_ADDED:-6}"
    log_info "DynamoDB records deleted: $DB_REDUCTION"
    log_info "Test execution completed at: $(date)"
    log_info "Log file saved to: $LOG_FILE"
    
    echo ""
    echo -e "${CYAN}📋 Test logs saved to: $LOG_FILE${NC}"
    exit 0
else
    echo "║ Overall Status: ❌ SOME TESTS FAILED"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${RED}❌ CRUD LIFECYCLE TEST FAILED - CHECK ERRORS ABOVE${NC}"
    
    # Final failure logging
    log_error "CRUD Lifecycle Test Failed"
    log_error "One or more validation checks failed"
    log_info "Test execution completed at: $(date)"
    log_info "Log file saved to: $LOG_FILE"
    
    echo ""
    echo -e "${CYAN}📋 Test logs saved to: $LOG_FILE${NC}"
    exit 1
fi 