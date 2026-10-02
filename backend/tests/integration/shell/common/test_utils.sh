#!/bin/bash

#==============================================================================
# Common Test Utilities for Integration Tests
#==============================================================================
# This file contains shared functions used across all shell integration tests
#==============================================================================

# Color codes for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export BLUE='\033[0;34m'
export YELLOW='\033[1;33m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export MAGENTA='\033[0;35m'
export NC='\033[0m' # No Color
export BOLD='\033[1m'

# Test configuration defaults
export DEFAULT_URL="${DEFAULT_URL:-http://localhost:8000}"
export SERVER_URL="${SERVER_URL:-$DEFAULT_URL}"
export API_KEY="${API_KEY:-super-secret}"
export TEST_TIMEOUT="${TEST_TIMEOUT:-30}"
export VERBOSE="${VERBOSE:-false}"
export DEBUG="${DEBUG:-false}"
export JSON_OUTPUT="${JSON_OUTPUT:-false}"

# Test counters
export TOTAL_TESTS=0
export PASSED_TESTS=0
export FAILED_TESTS=0
export SKIPPED_TESTS=0
export TEST_START_TIME=""
export TEST_END_TIME=""

# AWS Configuration
export AWS_REGION="${AWS_REGION:-us-east-1}"
export DYNAMODB_TABLE="${DYNAMODB_TABLE:-TransformationSystem}"

# Logging configuration
export LOG_DIR="${LOG_DIR:-$(pwd)/logs}"
export LOG_FILE=""
export EXECUTION_ID=""

#==============================================================================
# Logging Functions
#==============================================================================

# Initialize logging for a test
init_logging() {
    local test_name="${1:-test}"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    EXECUTION_ID="${test_name}_${timestamp}"
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/${test_name}_${timestamp}.log"
    
    echo "=== Integration Test: $test_name ===" > "$LOG_FILE"
    echo "Timestamp: $(date)" >> "$LOG_FILE"
    echo "Server URL: $SERVER_URL" >> "$LOG_FILE"
    echo "Execution ID: $EXECUTION_ID" >> "$LOG_FILE"
    echo "===========================================" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
}

# Print test header
print_test_header() {
    local header="$1"
    if [ "$JSON_OUTPUT" != "true" ]; then
        echo ""
        echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}${BOLD}║ $header${NC}"
        echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
    fi
}

# Log to file
log_to_file() {
    local level="$1"
    local message="$2"
    if [ -n "$LOG_FILE" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') | $level | $message" >> "$LOG_FILE"
    fi
}

# Log info message
log_info() {
    local message="$1"
    if [ "$JSON_OUTPUT" != "true" ]; then
        echo -e "${BLUE}ℹ️  $message${NC}"
    fi
    log_to_file "INFO" "$message"
}

# Log success message
log_success() {
    local message="$1"
    if [ "$JSON_OUTPUT" != "true" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    fi
    log_to_file "SUCCESS" "$message"
}

# Log error message
log_error() {
    local message="$1"
    if [ "$JSON_OUTPUT" != "true" ]; then
        echo -e "${RED}❌ $message${NC}" >&2
    fi
    log_to_file "ERROR" "$message"
}

# Log warning message
log_warning() {
    local message="$1"
    if [ "$JSON_OUTPUT" != "true" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    fi
    log_to_file "WARNING" "$message"
}

# Log step message
log_step() {
    local message="$1"
    if [ "$JSON_OUTPUT" != "true" ]; then
        echo -e "${PURPLE}🔄 $message${NC}"
    fi
    log_to_file "STEP" "$message"
}

# Log debug message (only if DEBUG=true)
log_debug() {
    local message="$1"
    if [ "$DEBUG" = "true" ]; then
        if [ "$JSON_OUTPUT" != "true" ]; then
            echo -e "${CYAN}[DEBUG] $message${NC}"
        fi
    fi
    log_to_file "DEBUG" "$message"
}

#==============================================================================
# Test Execution Functions
#==============================================================================

# Start a test
start_test() {
    local test_name="$1"
    TEST_START_TIME=$(date +%s)
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$JSON_OUTPUT" != "true" ]; then
        echo -e "\n${PURPLE}📋 TEST: $test_name${NC}"
        echo "================================"
    fi
    log_to_file "TEST_START" "$test_name"
}

# End a test
end_test() {
    local test_name="$1"
    local status="$2"  # "passed", "failed", or "skipped"
    
    TEST_END_TIME=$(date +%s)
    local duration=$((TEST_END_TIME - TEST_START_TIME))
    
    case "$status" in
        "passed")
            PASSED_TESTS=$((PASSED_TESTS + 1))
            log_success "Test passed: $test_name (${duration}s)"
            ;;
        "failed")
            FAILED_TESTS=$((FAILED_TESTS + 1))
            log_error "Test failed: $test_name (${duration}s)"
            ;;
        "skipped")
            SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
            log_warning "Test skipped: $test_name"
            ;;
    esac
    
    log_to_file "TEST_END" "$test_name - Status: $status - Duration: ${duration}s"
}

# Assert equal
assert_equal() {
    local actual="$1"
    local expected="$2"
    local message="${3:-Values should be equal}"
    
    if [ "$actual" = "$expected" ]; then
        log_debug "✓ Assertion passed: $message"
        return 0
    else
        log_error "✗ Assertion failed: $message"
        log_error "  Expected: $expected"
        log_error "  Actual: $actual"
        return 1
    fi
}

# Assert contains
assert_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-String should contain substring}"
    
    if [[ "$haystack" == *"$needle"* ]]; then
        log_debug "✓ Assertion passed: $message"
        return 0
    else
        log_error "✗ Assertion failed: $message"
        log_error "  String: $haystack"
        log_error "  Should contain: $needle"
        return 1
    fi
}

# Assert not empty
assert_not_empty() {
    local value="$1"
    local message="${2:-Value should not be empty}"
    
    if [ -n "$value" ]; then
        log_debug "✓ Assertion passed: $message"
        return 0
    else
        log_error "✗ Assertion failed: $message"
        return 1
    fi
}

#==============================================================================
# URL and Server Functions
#==============================================================================

# Parse URL and extract components
parse_url() {
    local url="$1"
    
    # Remove protocol
    local url_no_protocol="${url#http://}"
    url_no_protocol="${url_no_protocol#https://}"
    
    # Extract host and port
    if [[ "$url_no_protocol" == *":"* ]]; then
        export HOST="${url_no_protocol%:*}"
        export PORT="${url_no_protocol#*:}"
        PORT="${PORT%%/*}"
    else
        export HOST="$url_no_protocol"
        HOST="${HOST%%/*}"
        export PORT="8000"
    fi
    
    # Reconstruct URL
    if [[ "$url" == https://* ]]; then
        export SERVER_URL="https://$HOST:$PORT"
    else
        export SERVER_URL="http://$HOST:$PORT"
    fi
    
    log_debug "Parsed URL: $SERVER_URL (Host: $HOST, Port: $PORT)"
}

# Check server health
check_server_health() {
    local url="${1:-$SERVER_URL}"
    local max_retries="${2:-3}"
    local retry_delay="${3:-2}"
    
    log_step "Checking server health at $url"
    
    for i in $(seq 1 $max_retries); do
        if curl -s -f -o /dev/null "$url/health" 2>/dev/null; then
            log_success "Server is healthy"
            return 0
        fi
        
        if [ $i -lt $max_retries ]; then
            log_warning "Server not responding (attempt $i/$max_retries), retrying in ${retry_delay}s..."
            sleep $retry_delay
        fi
    done
    
    log_error "Server is not responding at $url after $max_retries attempts"
    return 1
}

# Wait for condition
wait_for_condition() {
    local condition_cmd="$1"
    local timeout="${2:-30}"
    local message="${3:-Waiting for condition}"
    
    log_step "$message"
    
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if eval "$condition_cmd" 2>/dev/null; then
            log_success "Condition met after ${elapsed}s"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    
    log_error "Timeout waiting for condition after ${timeout}s"
    return 1
}

#==============================================================================
# HTTP Request Functions
#==============================================================================

# Make HTTP POST request
make_post_request() {
    local endpoint="$1"
    local payload="$2"
    local expected_status="${3:-200}"
    
    log_debug "POST $endpoint"
    log_debug "Payload: $payload"
    
    local response
    local status_code
    
    # Wrap payload in arguments for MCP endpoints
    local wrapped_payload
    if [[ "$endpoint" == /tools/* ]]; then
        wrapped_payload="{\"arguments\": $payload}"
    else
        wrapped_payload="$payload"
    fi
    
    # Make request and capture both response and status code
    # Include API key header for gateway authentication
    response=$(curl -s -w "\n__STATUS_CODE__:%{http_code}" \
        -X POST "$SERVER_URL$endpoint" \
        -H "Content-Type: application/json" \
        -H "x-api-key: ${API_KEY:-super-secret}" \
        -d "$wrapped_payload" 2>/dev/null)
    
    status_code=$(echo "$response" | grep "__STATUS_CODE__:" | cut -d: -f2)
    response=$(echo "$response" | grep -v "__STATUS_CODE__:")
    
    log_debug "Response: $response"
    log_debug "Status Code: $status_code"
    
    echo "$response"
    
    # Check status code if expected
    if [ -n "$expected_status" ] && [ "$status_code" != "$expected_status" ]; then
        log_error "Unexpected status code: $status_code (expected: $expected_status)"
        return 1
    fi
    
    return 0
}

# Make HTTP GET request
make_get_request() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    
    log_debug "GET $endpoint"
    
    local response
    local status_code
    
    # Include API key header for gateway authentication
    response=$(curl -s -w "\n__STATUS_CODE__:%{http_code}" \
        -X GET "$SERVER_URL$endpoint" \
        -H "Accept: application/json" \
        -H "x-api-key: ${API_KEY:-super-secret}" 2>/dev/null)
    
    status_code=$(echo "$response" | grep "__STATUS_CODE__:" | cut -d: -f2)
    response=$(echo "$response" | grep -v "__STATUS_CODE__:")
    
    log_debug "Response: $response"
    log_debug "Status Code: $status_code"
    
    echo "$response"
    
    if [ -n "$expected_status" ] && [ "$status_code" != "$expected_status" ]; then
        log_error "Unexpected status code: $status_code (expected: $expected_status)"
        return 1
    fi
    
    return 0
}

#==============================================================================
# JSON Processing Functions
#==============================================================================

# Extract JSON field value
get_json_field() {
    local json="$1"
    local field="$2"
    
    # First try to extract the nested JSON from MCP response format
    local content=$(echo "$json" | jq -r '.content[0].text // empty' 2>/dev/null)
    
    if [ -n "$content" ]; then
        # Parse field from the nested JSON
        echo "$content" | jq -r "$field" 2>/dev/null || echo ""
    else
        # Fallback to direct field access for non-MCP responses
        echo "$json" | jq -r "$field" 2>/dev/null || echo ""
    fi
}

# Check if response is successful
check_response_success() {
    local response="$1"
    local status=""
    
    # First try to extract the nested JSON from MCP response format
    local content=$(echo "$response" | jq -r '.content[0].text // empty' 2>/dev/null)
    
    if [ -n "$content" ]; then
        # Parse the nested JSON for status
        status=$(echo "$content" | jq -r '.status // "error"' 2>/dev/null)
    else
        # Fallback to direct result.status for non-MCP responses
        status=$(echo "$response" | jq -r '.result.status // "error"' 2>/dev/null)
    fi
    
    if [ "$status" = "success" ]; then
        return 0
    else
        return 1
    fi
}

# Check if response indicates error (inverse of check_response_success)
check_response_error() {
    local response="$1"
    
    if check_response_success "$response"; then
        return 1  # Success means no error
    else
        return 0  # Not success means error
    fi
}

# Extract error message from response
get_error_message() {
    local response="$1"
    
    # First try to extract the nested JSON from MCP response format
    local content=$(echo "$response" | jq -r '.content[0].text // empty' 2>/dev/null)
    
    if [ -n "$content" ]; then
        # Parse error from the nested JSON
        echo "$content" | jq -r '.message // .error // "Unknown error"' 2>/dev/null
    else
        # Fallback to direct error access for non-MCP responses
        echo "$response" | jq -r '.result.message // .error // .detail // "Unknown error"' 2>/dev/null
    fi
}

#==============================================================================
# DynamoDB Functions
#==============================================================================

# Get DynamoDB record count
get_dynamodb_count() {
    local table="${1:-$DYNAMODB_TABLE}"
    
    local count=$(aws dynamodb scan \
        --table-name "$table" \
        --select COUNT \
        --output json 2>/dev/null | jq -r '.Count // 0' 2>/dev/null)
    
    if [[ "$count" =~ ^[0-9]+$ ]]; then
        echo "$count"
    else
        echo "0"
    fi
}

# Get journey record count
get_journey_record_count() {
    local journey_id="$1"
    
    if [ -z "$journey_id" ]; then
        echo "0"
        return
    fi
    
    local count=$(aws dynamodb query \
        --table-name "$DYNAMODB_TABLE" \
        --key-condition-expression "PK = :pk" \
        --expression-attribute-values "{\":pk\":{\"S\":\"JOURNEY#${journey_id}\"}}" \
        --select COUNT \
        --output json 2>/dev/null | jq -r '.Count // 0' 2>/dev/null)
    
    if [[ "$count" =~ ^[0-9]+$ ]]; then
        echo "$count"
    else
        echo "0"
    fi
}

# Check if journey exists in DynamoDB
journey_exists_in_dynamodb() {
    local journey_id="$1"
    
    local count=$(get_journey_record_count "$journey_id")
    [ "$count" -gt 0 ]
}

# Clean up test journey
cleanup_journey() {
    local journey_id="$1"
    
    if [ -z "$journey_id" ]; then
        return 0
    fi
    
    log_debug "Cleaning up journey: $journey_id"
    
    local payload=$(cat <<EOF
{
    "action": "delete",
    "journey_id": "$journey_id",
    "confirm": true
}
EOF
    )
    
    make_post_request "/tools/journeys_tool" "$payload" > /dev/null 2>&1
    return 0
}

#==============================================================================
# Test Report Functions
#==============================================================================

# Generate test summary
generate_test_summary() {
    local test_suite="${1:-Integration Tests}"
    
    local total=$((PASSED_TESTS + FAILED_TESTS + SKIPPED_TESTS))
    local pass_rate=0
    if [ $total -gt 0 ]; then
        pass_rate=$((PASSED_TESTS * 100 / total))
    fi
    
    if [ "$JSON_OUTPUT" = "true" ]; then
        cat <<EOF
{
  "suite": "$test_suite",
  "timestamp": "$(date -Iseconds)",
  "server_url": "$SERVER_URL",
  "execution_id": "$EXECUTION_ID",
  "summary": {
    "total": $total,
    "passed": $PASSED_TESTS,
    "failed": $FAILED_TESTS,
    "skipped": $SKIPPED_TESTS,
    "pass_rate": $pass_rate
  },
  "log_file": "$LOG_FILE"
}
EOF
    else
        echo ""
        echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║              Test Summary: $test_suite              ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${BLUE}📊 Results:${NC}"
        echo -e "  Total Tests:  $total"
        echo -e "  ${GREEN}Passed:       $PASSED_TESTS${NC}"
        echo -e "  ${RED}Failed:       $FAILED_TESTS${NC}"
        echo -e "  ${YELLOW}Skipped:      $SKIPPED_TESTS${NC}"
        echo -e "  ${PURPLE}Pass Rate:    ${pass_rate}%${NC}"
        echo ""
        
        if [ -n "$LOG_FILE" ]; then
            echo -e "${BLUE}📝 Log file: $LOG_FILE${NC}"
        fi
        
        if [ $FAILED_TESTS -gt 0 ]; then
            echo ""
            echo -e "${RED}❌ Tests failed!${NC}"
            return 1
        else
            echo ""
            echo -e "${GREEN}✅ All tests passed!${NC}"
            return 0
        fi
    fi
}

#==============================================================================
# Utility Functions
#==============================================================================

# Generate unique test ID
generate_test_id() {
    local prefix="${1:-TEST}"
    echo "${prefix}_$(date +%s)_$$"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verify prerequisites
verify_prerequisites() {
    local missing=()
    
    # Check required commands
    for cmd in curl jq aws; do
        if ! command_exists "$cmd"; then
            missing+=("$cmd")
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required commands: ${missing[*]}"
        log_info "Please install missing commands and try again"
        return 1
    fi
    
    return 0
}

# Setup test environment
setup_test_environment() {
    local test_name="${1:-test}"
    
    # Initialize logging
    init_logging "$test_name"
    
    # Verify prerequisites
    if ! verify_prerequisites; then
        return 1
    fi
    
    # Parse URL if provided
    if [ -n "$2" ]; then
        parse_url "$2"
    fi
    
    # Check server health
    if ! check_server_health; then
        return 1
    fi
    
    # Reset test counters
    TOTAL_TESTS=0
    PASSED_TESTS=0
    FAILED_TESTS=0
    SKIPPED_TESTS=0
    
    return 0
}

# Cleanup test environment
cleanup_test_environment() {
    # Generate final report
    generate_test_summary
    local exit_code=$?
    
    # Cleanup any remaining test data
    # This can be extended based on specific needs
    
    return $exit_code
}

#==============================================================================
# Export Functions
#==============================================================================

# This ensures all functions are available to sourcing scripts
export -f init_logging log_to_file log_info log_success log_error log_warning log_step log_debug
export -f start_test end_test assert_equal assert_contains assert_not_empty
export -f parse_url check_server_health wait_for_condition
export -f make_post_request make_get_request
export -f get_json_field check_response_success get_error_message
export -f get_dynamodb_count get_journey_record_count journey_exists_in_dynamodb cleanup_journey
export -f generate_test_summary generate_test_id command_exists verify_prerequisites
export -f setup_test_environment cleanup_test_environment
