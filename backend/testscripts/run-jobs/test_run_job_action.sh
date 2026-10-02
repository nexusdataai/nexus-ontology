#!/bin/bash

# ============================================================================
# Test Script: run_job Action via REST API
# ============================================================================
# Purpose: Tests running transformation jobs via REST API, specifically
# for the call_process stage in call processing journeys.
#
# Usage:
#   ./test_run_job_action.sh                    # Auto-select call processing journey
#   ./test_run_job_action.sh <JOURNEY_ID>       # Use specific journey
#   ./test_run_job_action.sh <JOURNEY_ID> <STAGE_ID>  # Use specific journey and stage
#
# API Endpoints:
#   POST /api/v1/journeys/{journey_id}/jobs?stage_id=<stage>  # Start a job
#   GET  /api/v1/journeys/{journey_id}/jobs                   # List jobs
#   GET  /api/v1/journeys/{journey_id}/jobs/{job_id}/status   # Get job status
#
# Features:
# - Tests run_job via REST API (not MCP)
# - Specifically tests call_process stage
# - Tests different trigger types (system, user, api, ui)
# - Tests job status polling
# - Comprehensive result reporting
# ============================================================================

set -o pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Server Configuration - Both REST API and MCP are on port 8000 by default
REST_API_URL="${REST_API_URL:-http://localhost:8000}"
MCP_SERVER_URL="${MCP_SERVER_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-super-secret}"
JOURNEY_ID="${1:-}"
STAGE_ID="${2:-call_process}"  # Default to call_process stage

# Test Configuration
POLL_JOB_STATUS=true  # Poll for job completion status
POLL_TIMEOUT=60       # Seconds to wait for job completion
POLL_INTERVAL=5       # Seconds between status polls

# Log Configuration
LOG_DIR="/opt/mycode/trilogy/nexus-backend/logs"
LOG_FILE="${LOG_DIR}/test_run_job_$(date +%Y%m%d_%H%M%S).log"

# ============================================================================
# COLOR CODES & FORMATTING
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ============================================================================
# TEST TRACKING
# ============================================================================

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0
TEST_START_TIME=$(date +%s)

# Job tracking
LAST_JOB_ID=""
LAST_STATUS_URL=""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Logging function
log_message() {
    local level=$1
    shift
    local message="$@"
    
    case "$level" in
        ERROR)
            echo -e "${RED}❌ $message${NC}"
            ;;
        SUCCESS)
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        WARNING)
            echo -e "${YELLOW}⚠️ $message${NC}"
            ;;
        INFO)
            echo -e "${BLUE}ℹ️ $message${NC}"
            ;;
        STEP)
            echo -e "${CYAN}📋 $message${NC}"
            ;;
        HEADER)
            echo -e "${MAGENTA}${BOLD}$message${NC}"
            ;;
        *)
            echo "$message"
            ;;
    esac
    
    # Also log to file if LOG_FILE exists
    if [ -n "$LOG_FILE" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOG_FILE" 2>/dev/null
    fi
}

# Parse REST API response
parse_api_response() {
    local response="$1"
    echo "$response"
}

# Parse MCP response (for journey listing)
parse_mcp_response() {
    local response="$1"
    echo "$response" | jq -r '.content[0].text' 2>/dev/null || echo "$response"
}

# Find call processing journey
find_call_processing_journey() {
    log_message "INFO" "Looking for call processing journey..."
    
    # Try REST API first to list journeys
    local response=$(curl -s -X GET "$REST_API_URL/api/v1/journeys" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        --max-time 10 \
        --connect-timeout 5 2>/dev/null)
    
    # Look for journeys with 'CALL' in the ID or 'call' in the name
    local journey_id=$(echo "$response" | jq -r '.data[]? | select(.journeyId | test("CALL"; "i")) | .journeyId' 2>/dev/null | head -1)
    
    if [ -n "$journey_id" ] && [ "$journey_id" != "null" ]; then
        log_message "SUCCESS" "Found call processing journey: $journey_id"
        echo "$journey_id"
        return 0
    fi
    
    # Fallback: try MCP endpoint
    response=$(curl -s -X POST "$MCP_SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d '{"arguments": {"action": "list"}}' \
        --max-time 10 \
        --connect-timeout 5 2>/dev/null)
    
    local result=$(parse_mcp_response "$response")
    journey_id=$(echo "$result" | jq -r '.data[]? | select(.journeyId | test("CALL"; "i")) | .journeyId' 2>/dev/null | head -1)
    
    if [ -n "$journey_id" ] && [ "$journey_id" != "null" ]; then
        log_message "SUCCESS" "Found call processing journey via MCP: $journey_id"
        echo "$journey_id"
        return 0
    fi
    
    # Return first available journey if no call processing journey found
    journey_id=$(echo "$result" | jq -r '.data[]?.journeyId' 2>/dev/null | head -1)
    if [ -n "$journey_id" ] && [ "$journey_id" != "null" ]; then
        log_message "WARNING" "No call processing journey found, using: $journey_id"
        echo "$journey_id"
        return 0
    fi
    
    echo ""
}

# Test run_job via REST API
test_run_job_rest() {
    local journey_id=$1
    local stage_id=$2
    local triggered_by=$3
    local reason=$4
    local test_name=$5
    local expect_failure=${6:-false}
    local wait_for_completion=${7:-false}
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    log_message "STEP" "Test $TOTAL_TESTS: $test_name"
    log_message "INFO" "  Journey: $journey_id"
    log_message "INFO" "  Stage: $stage_id"
    log_message "INFO" "  Triggered by: $triggered_by"
    log_message "INFO" "  API: POST $REST_API_URL/api/v1/journeys/$journey_id/jobs"
    
    # Build query parameters
    local query_params="stage_id=${stage_id}&triggered_by=${triggered_by:-api}"
    if [ -n "$reason" ]; then
        query_params="${query_params}&reason=$(echo "$reason" | jq -sRr @uri)"
    fi
    if [ "$wait_for_completion" = "true" ]; then
        query_params="${query_params}&wait_for_completion=true"
    fi
    
    local url="$REST_API_URL/api/v1/journeys/$journey_id/jobs?$query_params"
    
    # Debug output
    if [ "${DEBUG:-false}" = "true" ]; then
        echo "URL: $url" >&2
    fi
    
    local response
    response=$(curl -s -X POST "$url" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        --max-time 120 \
        --connect-timeout 5 2>&1)
    
    local curl_exit_code=$?
    
    # Check for curl timeout or connection errors
    if [ $curl_exit_code -eq 28 ]; then
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "ERROR" "  Request timed out"
        return 1
    elif [ $curl_exit_code -ne 0 ]; then
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "ERROR" "  Request failed with curl exit code: $curl_exit_code"
        return 1
    fi
    
    # Debug output
    if [ "${DEBUG:-false}" = "true" ]; then
        echo "Response: $response" >&2
    fi
    
    # Check for empty response
    if [ -z "$response" ]; then
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "ERROR" "  Empty response from server"
        return 1
    fi
    
    local success=$(echo "$response" | jq -r '.success' 2>/dev/null)
    local message=$(echo "$response" | jq -r '.message' 2>/dev/null)
    local job_id=$(echo "$response" | jq -r '.job_id' 2>/dev/null)
    local status_url=$(echo "$response" | jq -r '.status_url' 2>/dev/null)
    local job_status=$(echo "$response" | jq -r '.status' 2>/dev/null)
    
    if [ "$expect_failure" = "true" ]; then
        if [ "$success" != "true" ]; then
            PASSED_TESTS=$((PASSED_TESTS + 1))
            log_message "SUCCESS" "  Expected failure occurred: $message"
            return 0
        else
            FAILED_TESTS=$((FAILED_TESTS + 1))
            log_message "ERROR" "  Expected failure but got success!"
            return 1
        fi
    else
        if [ "$success" = "true" ]; then
            PASSED_TESTS=$((PASSED_TESTS + 1))
            log_message "SUCCESS" "  Job started successfully!"
            log_message "INFO" "    Job ID: $job_id"
            log_message "INFO" "    Status: $job_status"
            log_message "INFO" "    Status URL: $status_url"
            log_message "INFO" "    Message: $message"
            
            # Store job_id for later polling
            LAST_JOB_ID="$job_id"
            LAST_STATUS_URL="$status_url"
            
            return 0
        else
            FAILED_TESTS=$((FAILED_TESTS + 1))
            log_message "ERROR" "  Failed: $message"
            echo "$response" | jq '.' 2>/dev/null || echo "$response"
            return 1
        fi
    fi
}

# Poll job status via REST API
poll_job_status() {
    local journey_id=$1
    local job_id=$2
    local timeout=${3:-$POLL_TIMEOUT}
    
    log_message "INFO" "Polling job status for $job_id (timeout: ${timeout}s)..."
    
    local elapsed=0
    local status="running"
    
    while [ "$elapsed" -lt "$timeout" ] && [ "$status" = "running" ]; do
        sleep $POLL_INTERVAL
        elapsed=$((elapsed + POLL_INTERVAL))
        
        local response=$(curl -s -X GET "$REST_API_URL/api/v1/journeys/$journey_id/jobs/$job_id/status" \
            -H "Content-Type: application/json" \
            -H "x-api-key: $API_KEY" \
            --max-time 10 \
            --connect-timeout 5 2>/dev/null)
        
        status=$(echo "$response" | jq -r '.status // .data.status // "unknown"' 2>/dev/null)
        local progress=$(echo "$response" | jq -r '.progress // .data.progress // 0' 2>/dev/null)
        local current_step=$(echo "$response" | jq -r '.current_step // .data.currentStep // "unknown"' 2>/dev/null)
        
        log_message "INFO" "  [$elapsed/$timeout s] Status: $status | Progress: $progress% | Step: $current_step"
        
        if [ "$status" = "completed" ] || [ "$status" = "failed" ] || [ "$status" = "cancelled" ]; then
            break
        fi
    done
    
    if [ "$status" = "completed" ]; then
        log_message "SUCCESS" "Job completed successfully!"
        return 0
    elif [ "$status" = "failed" ]; then
        log_message "ERROR" "Job failed!"
        return 1
    elif [ "$status" = "cancelled" ]; then
        log_message "WARNING" "Job was cancelled"
        return 1
    else
        log_message "WARNING" "Job still running after timeout (status: $status)"
        return 2
    fi
}

# List jobs for a journey via REST API
list_jobs() {
    local journey_id=$1
    local limit=${2:-10}
    
    log_message "INFO" "Listing recent jobs for journey $journey_id..."
    
    local response=$(curl -s -X GET "$REST_API_URL/api/v1/journeys/$journey_id/jobs?limit=$limit" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        --max-time 10 \
        --connect-timeout 5 2>/dev/null)
    
    if [ -n "$response" ]; then
        echo "$response" | jq -r '.data[]? | "  \(.job_id // .jobId): \(.status) (\(.triggered_by // .triggeredBy // "unknown"))"' 2>/dev/null || echo "  No jobs found"
    else
        echo "  Failed to list jobs"
    fi
}

# Get available stages for a journey via REST API
get_journey_stages() {
    local journey_id=$1
    
    # Try REST API first
    local response=$(curl -s -X GET "$REST_API_URL/api/v1/journeys/$journey_id/stages" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        --max-time 10 \
        --connect-timeout 5 2>/dev/null)
    
    local stages=$(echo "$response" | jq -r '.data[]?.stageId // .data[]?.stage_id' 2>/dev/null)
    
    if [ -n "$stages" ] && [ "$stages" != "null" ]; then
        echo "$stages"
        return 0
    fi
    
    # Fallback to MCP
    response=$(curl -s -X POST "$MCP_SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d "{\"arguments\": {\"action\": \"list_stages\", \"journey_id\": \"$journey_id\"}}" \
        --max-time 10 \
        --connect-timeout 5 2>/dev/null)
    
    local result=$(parse_mcp_response "$response")
    stages=$(echo "$result" | jq -r '.data[]?.stageId' 2>/dev/null)
    
    if [ -n "$stages" ] && [ "$stages" != "null" ]; then
        echo "$stages"
    else
        # Default to call_process for call processing journeys
        echo "call_process"
    fi
}

# Get journey details via REST API
get_journey_details() {
    local journey_id=$1
    
    local response=$(curl -s -X GET "$REST_API_URL/api/v1/journeys/$journey_id" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        --max-time 10 \
        --connect-timeout 5 2>/dev/null)
    
    echo "$response"
}

# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================

# Create log directory if needed
mkdir -p "$LOG_DIR" 2>/dev/null

# Header
echo
log_message "HEADER" "╔══════════════════════════════════════════════════════════════════╗"
log_message "HEADER" "║      TESTING run_job via REST API - CALL PROCESSING STAGE       ║"
log_message "HEADER" "╚══════════════════════════════════════════════════════════════════╝"
echo
log_message "INFO" "REST API: $REST_API_URL"
log_message "INFO" "MCP Server: $MCP_SERVER_URL"
log_message "INFO" "Target Stage: $STAGE_ID"
log_message "INFO" "Log file: $LOG_FILE"
echo

# Step 1: Get or find call processing journey
log_message "HEADER" "── Step 1: Journey Selection ──"

if [ -z "$JOURNEY_ID" ]; then
    log_message "INFO" "No journey ID provided. Looking for call processing journey..."
    
    JOURNEY_ID=$(find_call_processing_journey)
    
    if [ -z "$JOURNEY_ID" ] || [ "$JOURNEY_ID" = "null" ]; then
        log_message "ERROR" "No journey found. Please create a call processing journey first:"
        log_message "INFO" "  cd /opt/mycode/trilogy/nexus-backend/scripts/journey-scripts"
        log_message "INFO" "  python create_call_processing_journey.py"
        exit 1
    fi
else
    log_message "INFO" "Using provided journey: $JOURNEY_ID"
fi

# Get journey details
log_message "INFO" "Fetching journey details..."
JOURNEY_DETAILS=$(get_journey_details "$JOURNEY_ID")
JOURNEY_NAME=$(echo "$JOURNEY_DETAILS" | jq -r '.data.name // .name // "Unknown"' 2>/dev/null)
log_message "INFO" "Journey Name: $JOURNEY_NAME"

# Get available stages for the journey
STAGES=$(get_journey_stages "$JOURNEY_ID")
if [ -z "$STAGES" ] || [ "$STAGES" = "null" ]; then
    log_message "WARNING" "No stages found for journey, using default: $STAGE_ID"
    STAGES="$STAGE_ID"
fi
log_message "INFO" "Available stages: $(echo $STAGES | tr '\n' ' ')"

# Verify target stage exists
if ! echo "$STAGES" | grep -q "^${STAGE_ID}$"; then
    log_message "WARNING" "Stage '$STAGE_ID' not in journey stages, but will try anyway"
fi
echo

# Step 2: List existing jobs
log_message "HEADER" "── Step 2: Existing Jobs ──"
list_jobs "$JOURNEY_ID" 5
echo

# Step 3: Test Suite - REST API Job Execution
log_message "HEADER" "── Step 3: REST API Job Execution Tests ──"
echo

# Test 1: Run call_process stage via REST API (UI trigger)
test_run_job_rest "$JOURNEY_ID" "$STAGE_ID" "ui" "UI triggered call processing" \
    "Run $STAGE_ID via REST API (UI trigger)"

# Optional: Poll for status if enabled
if [ "$POLL_JOB_STATUS" = "true" ] && [ -n "$LAST_JOB_ID" ]; then
    poll_job_status "$JOURNEY_ID" "$LAST_JOB_ID" 30
fi

echo

# Test 2: Run with API trigger
test_run_job_rest "$JOURNEY_ID" "$STAGE_ID" "api" "Automated API call" \
    "Run $STAGE_ID via REST API (API trigger)"
echo

# Test 3: Run with user trigger
test_run_job_rest "$JOURNEY_ID" "$STAGE_ID" "user" "Manual user execution" \
    "Run $STAGE_ID via REST API (User trigger)"
echo

# Test 4: Run with system trigger
test_run_job_rest "$JOURNEY_ID" "$STAGE_ID" "system" "Scheduled system job" \
    "Run $STAGE_ID via REST API (System trigger)"
echo

log_message "HEADER" "── Step 4: Error Handling Tests ──"
echo

# Test 5: Invalid journey ID
test_run_job_rest "INVALID-JRN-99999" "$STAGE_ID" "test" "Testing error handling" \
    "Invalid journey ID (should fail)" true
echo

# Test 6: Invalid stage ID
test_run_job_rest "$JOURNEY_ID" "invalid_stage_xyz" "test" "Testing error handling" \
    "Invalid stage ID (should fail)" true
echo

# Step 5: List jobs after tests
log_message "HEADER" "── Step 5: Jobs After Tests ──"
list_jobs "$JOURNEY_ID" 10
echo

# ============================================================================
# TEST SUMMARY
# ============================================================================

TEST_END_TIME=$(date +%s)
TEST_DURATION=$((TEST_END_TIME - TEST_START_TIME))

log_message "HEADER" "╔══════════════════════════════════════════════════════════════════╗"
log_message "HEADER" "║                         TEST SUMMARY                            ║"
log_message "HEADER" "╚══════════════════════════════════════════════════════════════════╝"
echo

# Calculate pass percentage
if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_PERCENTAGE=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))
else
    PASS_PERCENTAGE=0
fi

# Display results with appropriate colors
echo -e "${BOLD}Test Results:${NC}"
echo -e "  Journey:        ${CYAN}$JOURNEY_ID${NC}"
echo -e "  Target Stage:   ${CYAN}$STAGE_ID${NC}"
echo -e "  Total Tests:    ${CYAN}$TOTAL_TESTS${NC}"
echo -e "  Passed:         ${GREEN}$PASSED_TESTS${NC}"
echo -e "  Failed:         ${RED}$FAILED_TESTS${NC}"
echo -e "  Skipped:        ${YELLOW}$SKIPPED_TESTS${NC}"
echo -e "  Pass Rate:      ${BOLD}${PASS_PERCENTAGE}%${NC}"
echo -e "  Duration:       ${CYAN}${TEST_DURATION}s${NC}"
echo

# REST API Reference
echo -e "${BOLD}REST API Reference:${NC}"
echo -e "  Start Job:      ${CYAN}POST $REST_API_URL/api/v1/journeys/{journey_id}/jobs?stage_id=$STAGE_ID${NC}"
echo -e "  List Jobs:      ${CYAN}GET  $REST_API_URL/api/v1/journeys/{journey_id}/jobs${NC}"
echo -e "  Job Status:     ${CYAN}GET  $REST_API_URL/api/v1/journeys/{journey_id}/jobs/{job_id}/status${NC}"
echo

# Example cURL command
echo -e "${BOLD}Example cURL:${NC}"
echo -e "  ${YELLOW}curl -X POST \"$REST_API_URL/api/v1/journeys/$JOURNEY_ID/jobs?stage_id=$STAGE_ID&triggered_by=ui\"${NC}"
echo

# Overall status
if [ $FAILED_TESTS -eq 0 ] && [ $TOTAL_TESTS -gt 0 ]; then
    log_message "SUCCESS" "ALL TESTS PASSED! 🎉"
    EXIT_CODE=0
else
    log_message "ERROR" "SOME TESTS FAILED"
    EXIT_CODE=1
fi

echo
log_message "INFO" "Test log saved to: $LOG_FILE"
echo

exit $EXIT_CODE
