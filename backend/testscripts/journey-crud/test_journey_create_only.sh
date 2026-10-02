#!/bin/bash

# Journey Creation Test (No Cleanup)
# Creates a journey with default stages but leaves data in DynamoDB for inspection

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"

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
    echo -e "${CYAN}Journey Creation Test (No Cleanup)${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC} $0 [URL]"
    echo ""
    echo -e "${YELLOW}Arguments:${NC}"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  $0                                    # Test on localhost:8000"
    echo -e "  $0 http://192.168.1.100:8000          # Test on remote server"
    echo -e "  $0 https://api.company.com            # Use HTTPS connection"
    echo ""
    echo -e "${YELLOW}Description:${NC}"
    echo -e "  Creates a journey with default stages but leaves data in DynamoDB for inspection."
    echo -e "  This test does NOT clean up the created journey."
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
                echo -e "${RED}❌ Unknown option: $1${NC}"
                echo -e "${YELLOW}💡 Use URL format instead: $0 http://host:port${NC}"
                show_usage
                exit 1
                ;;
            *)
                echo -e "${RED}❌ Unknown argument: $1${NC}"
                echo -e "${YELLOW}💡 Use URL format: $0 http://host:port${NC}"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Logging configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/test_journey_create_$(date +%Y-%m-%d_%H-%M-%S).log"
EXECUTION_ID="CREATE_$(date +%s)"

# Initialize logging
setup_logging() {
    echo "=== Journey Creation Test Log - $(date) ===" > "$LOG_FILE"
    echo "Execution ID: $EXECUTION_ID" >> "$LOG_FILE"
    echo "Server URL: $SERVER_URL" >> "$LOG_FILE"
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

log_info() {
    local message="$1"
    echo -e "${CYAN}ℹ️  $message${NC}"
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

# API helper functions
call_api() {
    local action="$1"
    local data="$2"
    # Wrap the data in arguments for MCP
    local wrapped_data="{\"arguments\": $data}"
    log_debug "API Call - Action: $action, Data: $wrapped_data"
    local response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: super-secret" \
        -d "$wrapped_data")
    log_debug "API Response: $response"
    echo "$response"
}

check_api_success() {
    local response="$1"
    # Check for MCP wrapped response
    local result_text=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null)
    if [ -z "$result_text" ] || [ "$result_text" = "null" ]; then
        return 1
    fi
    echo "$result_text" | jq -e '.status == "success"' >/dev/null 2>&1
}

get_total_dynamodb_records() {
    local count=$(aws dynamodb scan \
        --table-name TransformationSystem \
        --select COUNT \
        --output json 2>/dev/null | jq -r '.Count // 0')
    echo "${count:-0}"
}

get_journey_record_count() {
    local journey_id="$1"
    # PK format in DynamoDB is "JOURNEY#JRN-xxx" (includes JRN- prefix)
    local count=$(aws dynamodb scan \
        --table-name TransformationSystem \
        --filter-expression "begins_with(PK, :pk)" \
        --expression-attribute-values "{\":pk\":{\"S\":\"JOURNEY#$journey_id\"}}" \
        --select COUNT \
        --output json 2>/dev/null | jq -r '.Count // 0')
    echo "${count:-0}"
}

# Parse command line arguments first
parse_arguments "$@"

# Initialize logging
setup_logging

# Test Header
echo -e "${PURPLE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              🏗️  Journey Creation Test (Persistent)        ║"
echo "║           Create Journey + Stages (No Cleanup)              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

log_info "Starting Journey Creation Test"
log_info "Execution ID: $EXECUTION_ID"
log_info "Log file: $LOG_FILE"

# Phase 1: Initial State
echo -e "${PURPLE}📊 PHASE 1: Initial State Assessment${NC}"
echo "=================================================="
log_step "Getting initial DynamoDB record count"
INITIAL_DB_COUNT=$(get_total_dynamodb_records)
log_info "Initial DynamoDB records: $INITIAL_DB_COUNT"

log_step "Getting initial journey count via API"
INITIAL_COUNT_RESPONSE=$(call_api "list" '{"action": "list"}')
if check_api_success "$INITIAL_COUNT_RESPONSE"; then
    result_text=$(echo "$INITIAL_COUNT_RESPONSE" | jq -r '.content[0].text' 2>/dev/null)
    INITIAL_JOURNEY_COUNT=$(echo "$result_text" | jq -r '.total_count // 0')
    log_info "Initial journey count: $INITIAL_JOURNEY_COUNT"
else
    log_warning "Could not get initial journey count"
    INITIAL_JOURNEY_COUNT=0
fi

# Phase 2: Journey Creation
echo -e "\n${PURPLE}🆕 PHASE 2: Journey Creation with Comprehensive Metadata${NC}"
echo "=============================================================="

log_step "Creating journey with comprehensive metadata and stages"

CREATE_DATA='{
    "action": "create",
    "journey_data": {
        "name": "TMF ODA Schema Transformation",
        "description": "Comprehensive transformation of legacy database schema to TMF ODA compliance standards",
        "odaComponentType": "customer-management",
        "priority": "high",
        "stages": [
            {"stageId": "raw_analysis", "name": "Raw Analysis", "description": "Analyze raw data", "order": 1},
            {"stageId": "stripped_schema", "name": "Stripped Schema", "description": "Strip schema details", "order": 2},
            {"stageId": "tmf_mapping", "name": "TMF Mapping", "description": "Map to TMF standards", "order": 3},
            {"stageId": "migration_planning", "name": "Migration Planning", "description": "Plan migration", "order": 4},
            {"stageId": "data_migration", "name": "Data Migration", "description": "Execute migration", "order": 5},
            {"stageId": "verification_validation", "name": "Verification", "description": "Validate results", "order": 6}
        ]
    }
}'

CREATE_RESPONSE=$(call_api "create" "$CREATE_DATA")
echo "DEBUG: CREATE_RESPONSE=$CREATE_RESPONSE"

if check_api_success "$CREATE_RESPONSE"; then
    result_text=$(echo "$CREATE_RESPONSE" | jq -r '.content[0].text' 2>/dev/null)
    JOURNEY_ID=$(echo "$result_text" | jq -r '.journey_id')
    log_success "Journey created successfully: $JOURNEY_ID"
else
    log_error "Failed to create journey"
    echo "$CREATE_RESPONSE" | jq -r '.result.message // "Unknown error"'
    exit 1
fi

# Phase 3: Verify Stages
echo -e "\n${PURPLE}🏗️  PHASE 3: Verifying Transformation Stages${NC}"
echo "===================================================="

log_step "Verifying stages created with journey"

# Stages are now provided in journey_data.stages during creation
READ_DATA="{
    \"action\": \"read\",
    \"journey_id\": \"$JOURNEY_ID\"
}"

READ_RESPONSE=$(call_api "read" "$READ_DATA")

if check_api_success "$READ_RESPONSE"; then
    result_text=$(echo "$READ_RESPONSE" | jq -r '.content[0].text' 2>/dev/null)
    TOTAL_STAGES=$(echo "$result_text" | jq -r '.data.stages | length // 0')
    STAGE_NAMES=$(echo "$result_text" | jq -r '.data.stages[].stageId' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
    log_success "Journey created with $TOTAL_STAGES stages"
    log_info "Stages: $STAGE_NAMES"
else
    log_warning "Failed to verify stages"
    TOTAL_STAGES=0
fi

# Phase 4: Final Verification
echo -e "\n${PURPLE}📊 PHASE 4: Final State Verification${NC}"
echo "====================================="

log_step "Verifying journey and stages creation in DynamoDB"
FINAL_DB_COUNT=$(get_total_dynamodb_records)
JOURNEY_RECORDS=$(get_journey_record_count "$JOURNEY_ID")
log_info "Total DynamoDB records: $FINAL_DB_COUNT"
log_info "Journey-specific records: $JOURNEY_RECORDS"

FINAL_COUNT_RESPONSE=$(call_api "list" '{"action": "list"}')
if check_api_success "$FINAL_COUNT_RESPONSE"; then
    result_text=$(echo "$FINAL_COUNT_RESPONSE" | jq -r '.content[0].text' 2>/dev/null)
    FINAL_JOURNEY_COUNT=$(echo "$result_text" | jq -r '.total_count // 0')
    log_info "API journey count: $FINAL_JOURNEY_COUNT"
else
    log_warning "Could not get final journey count"
    FINAL_JOURNEY_COUNT=0
fi

# Summary
echo -e "\n${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    📋 CREATION RESULTS                       ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║ Journey ID: $JOURNEY_ID"
echo "║ Creation: ✅ SUCCESS"
echo "║ Default Stages: ${TOTAL_STAGES:-0} stages created"
echo "║ DynamoDB Records Created: $((FINAL_DB_COUNT - INITIAL_DB_COUNT))"
echo "║ Journey-Specific Records: $JOURNEY_RECORDS"
echo "║ API Journey Count: $FINAL_JOURNEY_COUNT"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}🎉 JOURNEY CREATION COMPLETED - DATA PERSISTED IN DYNAMODB! 🎉${NC}"
echo -e "${CYAN}💡 To view the data in DynamoDB:${NC}"
echo -e "${CYAN}   aws dynamodb scan --table-name TransformationSystem --query 'Items[*].[PK.S,SK.S,EntityType.S]' --output table${NC}"
echo -e "${CYAN}💡 To clean up later, run: ./clean_journeys_data.sh${NC}" 

# Final logging
log_success "Journey Creation Test Completed Successfully"
log_info "Journey ID: $JOURNEY_ID"
log_info "Total DynamoDB records created: $((FINAL_DB_COUNT - INITIAL_DB_COUNT))"
log_info "Journey-specific records: $JOURNEY_RECORDS"
log_info "Test execution completed at: $(date)"
log_info "Log file saved to: $LOG_FILE"

echo ""
echo -e "${CYAN}📋 Test logs saved to: $LOG_FILE${NC}" 