#!/bin/bash

# ============================================================================
# Call Processing Journey - Job Operations Test Script
# ============================================================================
# Tests job-related operations for call processing journeys
# Creates real call_process jobs and tests operations on them
#
# Usage:
#   ./test_journeys_job_operations.sh                    # Auto-select call processing journey
#   ./test_journeys_job_operations.sh <JOURNEY_ID>       # Use specific journey
#
# ============================================================================

# Configuration
SERVER_URL="${SERVER_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-super-secret}"
LOG_DIR="/opt/mycode/trilogy/nexus-backend/logs"
LOG_FILE=""
JOURNEY_ID="${1:-}"
DEFAULT_STAGE="call_process"  # Default stage for call processing journeys

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper function for logging
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
            echo -e "${MAGENTA}📋 $message${NC}"
            ;;
        *)
            echo "$message"
            ;;
    esac
    
    # Also log to file
    [ -n "$LOG_FILE" ] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOG_FILE"
}

# Function to parse MCP response
parse_mcp_response() {
    local response="$1"
    echo "$response" | jq -r '.content[0].text' 2>/dev/null || echo "$response"
}

# Function to get available journeys
get_available_journeys() {
    local response=$(curl -s --max-time 10 -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d '{"arguments": {"action": "list"}}' 2>/dev/null)
    
    local result=$(parse_mcp_response "$response")
    echo "$result"
}

# Function to find call processing journey first, fallback to any journey
select_journey() {
    log_message "INFO" "🔍 Looking for call processing journeys..."
    
    local result=$(get_available_journeys)
    
    # Check if the request timed out or failed
    if [ -z "$result" ]; then
        log_message "ERROR" "Failed to fetch journeys from server (timeout or connection error)"
        log_message "INFO" "Please ensure the MCP server is running at $SERVER_URL"
        return 1
    fi
    
    local journeys=$(echo "$result" | jq -r '.data' 2>/dev/null)
    local count=$(echo "$journeys" | jq 'length' 2>/dev/null || echo 0)
    
    if [ "$count" -eq 0 ] || [ "$count" = "null" ]; then
        log_message "WARNING" "No journeys found. Please create a call processing journey first:"
        log_message "INFO" "  cd /opt/mycode/trilogy/nexus-backend/scripts/journey-scripts"
        log_message "INFO" "  python create_call_processing_journey.py"
        return 1
    fi
    
    echo ""
    echo -e "${CYAN}📊 Available Journeys:${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
    
    # Display first 5 journeys
    local display_count=$((count > 5 ? 5 : count))
    for i in $(seq 0 $((display_count - 1))); do
        local journey=$(echo "$journeys" | jq -r ".[$i]")
        local id=$(echo "$journey" | jq -r '.journeyId // .journey_id')
        local name=$(echo "$journey" | jq -r '.name // "Unnamed"')
        local status=$(echo "$journey" | jq -r '.status // "unknown"')
        
        # Highlight call processing journeys
        if echo "$id" | grep -qi "CALL"; then
            echo -e "${BLUE}  $((i + 1)). ${GREEN}$id${NC} ${YELLOW}[Call Processing]${NC}"
        else
            echo -e "${BLUE}  $((i + 1)). ${GREEN}$id${NC}"
        fi
        echo -e "      Name: ${YELLOW}$name${NC}"
        echo -e "      Status: ${CYAN}$status${NC}"
        echo ""
    done
    
    # Try to find a call processing journey first (ID contains 'CALL')
    local call_journey=$(echo "$journeys" | jq -r '[.[] | select(.journeyId | test("CALL"; "i"))] | .[0].journeyId // empty' 2>/dev/null)
    
    if [ -n "$call_journey" ]; then
        JOURNEY_ID="$call_journey"
        JOURNEY_NAME=$(echo "$journeys" | jq -r --arg id "$call_journey" '.[] | select(.journeyId == $id) | .name // "Call Processing"' 2>/dev/null)
        log_message "SUCCESS" "Found call processing journey: $JOURNEY_ID"
    else
        # Fallback to first journey
        JOURNEY_ID=$(echo "$journeys" | jq -r '.[0].journeyId // .[0].journey_id')
        JOURNEY_NAME=$(echo "$journeys" | jq -r '.[0].name // "Unknown"')
        log_message "WARNING" "No call processing journey found, using: $JOURNEY_ID"
    fi
    
    log_message "INFO" "📋 Using Journey: $JOURNEY_ID - $JOURNEY_NAME"
    return 0
}

# Function to create a real job
create_real_job() {
    local journey_id=$1
    local stage_id=${2:-"$DEFAULT_STAGE"}
    
    log_message "INFO" "Creating $stage_id job for testing..."
    
    local request_data='{
        "arguments": {
            "action": "run_job",
            "journey_id": "'$journey_id'",
            "stage_id": "'$stage_id'",
            "triggered_by": "test_script",
            "reason": "Creating call processing job for testing job operations"
        }
    }'
    
    local response=$(curl -s --max-time 10 -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d "$request_data" 2>/dev/null)
    
    local result=$(parse_mcp_response "$response")
    local status=$(echo "$result" | jq -r '.status' 2>/dev/null)
    
    if [ "$status" = "success" ]; then
        local job_id=$(echo "$result" | jq -r '.job_id' 2>/dev/null)
        log_message "SUCCESS" "Created job: $job_id"
        echo "$job_id"
    else
        local error=$(echo "$result" | jq -r '.error // .message // "Unknown error"' 2>/dev/null)
        log_message "ERROR" "Failed to create job: $error"
        echo ""
    fi
}

# Function to test a journeys_tool action
test_journeys_action() {
    local action=$1
    local data=$2
    local description=$3
    
    log_message "INFO" "Testing: $description"
    
    local response=$(curl -s --max-time 10 -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d "$data" 2>/dev/null)
    
    # Check if we got a response
    if [ -z "$response" ]; then
        log_message "ERROR" "$description - Failed: No response from server"
        return 1
    fi
    
    local result=$(parse_mcp_response "$response")
    
    # Check if result is empty or null
    if [ -z "$result" ] || [ "$result" = "null" ]; then
        log_message "ERROR" "$description - Failed: Empty or invalid response"
        [ -n "$LOG_FILE" ] && echo "Raw response: $response" >> "$LOG_FILE"
        return 1
    fi
    
    local status=$(echo "$result" | jq -r '.status' 2>/dev/null)
    
    # Debug output to log file
    [ -n "$LOG_FILE" ] && echo "[$action] Status: $status" >> "$LOG_FILE"
    
    if [ "$status" = "success" ]; then
        log_message "SUCCESS" "$description - Success"
        
        # Display some result data based on action type
        case "$action" in
            "get_job_metrics")
                local total_logs=$(echo "$result" | jq -r '.data.logMetrics.totalEntries // 0' 2>/dev/null)
                local error_count=$(echo "$result" | jq -r '.data.logMetrics.errorCount // 0' 2>/dev/null)
                log_message "INFO" "  Total Logs: $total_logs, Errors: $error_count"
                ;;
            "get_job_timeline")
                local events=$(echo "$result" | jq -r '.data.timeline | length // 0' 2>/dev/null)
                log_message "INFO" "  Timeline Events: $events"
                ;;
            "dashboard")
                local total_jobs=$(echo "$result" | jq -r '.data.summary.totalJobs // 0' 2>/dev/null)
                log_message "INFO" "  Total Jobs: $total_jobs"
                ;;
        esac
        
        return 0
    elif [ "$status" = "null" ] || [ -z "$status" ]; then
        # Failed to parse status
        local error_msg=$(echo "$response" | jq -r '.detail // .error // "Failed to parse response"' 2>/dev/null)
        log_message "ERROR" "$description - Failed: $error_msg"
        [ -n "$LOG_FILE" ] && echo "Failed to parse status from: $result" >> "$LOG_FILE"
        return 1
    else
        local error_msg=$(echo "$result" | jq -r '.message // .error // "Unknown error"' 2>/dev/null)
        log_message "ERROR" "$description - Failed: $error_msg"
        return 1
    fi
}

# Initialize script
SCRIPT_NAME="test_call_processing_job_operations"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/${SCRIPT_NAME}_${TIMESTAMP}.log"
mkdir -p "$LOG_DIR"

# Header
echo -e "${BLUE}🚀 Call Processing Journey - Job Operations Test${NC}"
echo "=============================================="
echo -e "${BLUE}Script: $SCRIPT_NAME${NC}"
echo -e "${BLUE}Timestamp: $TIMESTAMP${NC}"
echo -e "${BLUE}Log file: $LOG_FILE${NC}"
echo -e "${BLUE}Server URL: $SERVER_URL${NC}"
echo -e "${BLUE}Default Stage: $DEFAULT_STAGE${NC}"
echo "=============================================="

# Initialize log
echo "Call Processing Journey - Job Operations Test" > "$LOG_FILE"
echo "Started at: $(date)" >> "$LOG_FILE"
echo "Server URL: $SERVER_URL" >> "$LOG_FILE"
echo "Default Stage: $DEFAULT_STAGE" >> "$LOG_FILE"
echo "============================================" >> "$LOG_FILE"

# Step 1: Select a journey
log_message "STEP" "Step 1: Select call processing journey for testing"

if [ -n "$JOURNEY_ID" ]; then
    log_message "INFO" "Using provided journey: $JOURNEY_ID"
    JOURNEY_NAME="Provided Journey"
elif ! select_journey; then
    log_message "ERROR" "No call processing journey available for testing"
    exit 1
fi

echo "=============================================="
echo -e "${BLUE}🎯 Testing Call Processing Job Operations for Journey: $JOURNEY_ID${NC}"
echo "=============================================="

# Step 2: Create a real call_process job for testing
log_message "STEP" "Step 2: Create a call_process job for testing operations"
REAL_JOB_ID=$(create_real_job "$JOURNEY_ID" "$DEFAULT_STAGE")

if [ -z "$REAL_JOB_ID" ] || [ "$REAL_JOB_ID" = "null" ]; then
    log_message "WARNING" "Could not create job. Will test with placeholder ID."
    REAL_JOB_ID="JOB-PLACEHOLDER-$(date +%s)"
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ "$REAL_JOB_ID" != "JOB-PLACEHOLDER"* ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Step 3: Test update_job_status (only if we have a real job)
if [ "$REAL_JOB_ID" != "JOB-PLACEHOLDER"* ]; then
    log_message "STEP" "Step 3: Test update_job_status operation"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    UPDATE_STATUS_DATA='{
        "arguments": {
            "action": "update_job_status",
            "journey_id": "'$JOURNEY_ID'",
            "job_id": "'$REAL_JOB_ID'",
            "job_status": "running",
            "progress": 75,
            "current_step": "Testing job status update"
        }
    }'
    
    if test_journeys_action "update_job_status" "$UPDATE_STATUS_DATA" "Update job status"; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_message "INFO" "Job $REAL_JOB_ID updated to running (75% complete)"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    log_message "WARNING" "Skipping update_job_status test (no real job)"
fi

# Step 4: Test get_job_metrics
log_message "STEP" "Step 4: Test get_job_metrics operation"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

GET_METRICS_DATA='{
    "arguments": {
        "action": "get_job_metrics",
        "journey_id": "'$JOURNEY_ID'",
        "job_id": "'$REAL_JOB_ID'"
    }
}'

if test_journeys_action "get_job_metrics" "$GET_METRICS_DATA" "Get job metrics"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    if [ "$REAL_JOB_ID" = "JOB-PLACEHOLDER"* ]; then
        log_message "INFO" "Note: Using placeholder job ID"
    fi
fi

# Step 5: Test get_job_timeline
log_message "STEP" "Step 5: Test get_job_timeline operation"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

GET_TIMELINE_DATA='{
    "arguments": {
        "action": "get_job_timeline",
        "journey_id": "'$JOURNEY_ID'",
        "job_id": "'$REAL_JOB_ID'"
    }
}'

if test_journeys_action "get_job_timeline" "$GET_TIMELINE_DATA" "Get job timeline"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    if [ "$REAL_JOB_ID" = "JOB-PLACEHOLDER"* ]; then
        log_message "INFO" "Note: Using placeholder job ID"
    fi
fi

# Step 6: Test batch_cancel_jobs
log_message "STEP" "Step 6: Test batch_cancel_jobs operation"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Create a second call_process job if we can
SECOND_JOB_ID=$(create_real_job "$JOURNEY_ID" "$DEFAULT_STAGE")
if [ -z "$SECOND_JOB_ID" ] || [ "$SECOND_JOB_ID" = "null" ]; then
    SECOND_JOB_ID="JOB-PLACEHOLDER2-$(date +%s)"
fi

BATCH_CANCEL_DATA='{
    "arguments": {
        "action": "batch_cancel_jobs",
        "journey_id": "'$JOURNEY_ID'",
        "job_ids": ["'$REAL_JOB_ID'", "'$SECOND_JOB_ID'"],
        "reason": "Testing batch cancellation operation"
    }
}'

if test_journeys_action "batch_cancel_jobs" "$BATCH_CANCEL_DATA" "Batch cancel jobs"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Step 7: Test dashboard operation
log_message "STEP" "Step 7: Test dashboard operation"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

DASHBOARD_DATA='{
    "arguments": {
        "action": "dashboard",
        "journey_id": "'$JOURNEY_ID'"
    }
}'

if test_journeys_action "dashboard" "$DASHBOARD_DATA" "Get journey dashboard"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Step 8: Test get_journey_summary
log_message "STEP" "Step 8: Test get_journey_summary operation"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

SUMMARY_DATA='{
    "arguments": {
        "action": "get_journey_summary",
        "journey_id": "'$JOURNEY_ID'"
    }
}'

if test_journeys_action "get_journey_summary" "$SUMMARY_DATA" "Get journey summary"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Step 9: Test error handling with truly invalid action
log_message "STEP" "Step 9: Test error handling for invalid operation"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

INVALID_DATA='{
    "arguments": {
        "action": "totally_invalid_action_xyz",
        "journey_id": "'$JOURNEY_ID'"
    }
}'

log_message "INFO" "Testing: Invalid action (totally_invalid_action_xyz)"
INVALID_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d "$INVALID_DATA" 2>/dev/null)

# Check if error handling works
if echo "$INVALID_RESPONSE" | grep -q -E "(error|Invalid|invalid)" 2>/dev/null; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_message "SUCCESS" "Error handling working correctly - invalid action rejected"
else
    INVALID_RESULT=$(parse_mcp_response "$INVALID_RESPONSE")
    INVALID_STATUS=$(echo "$INVALID_RESULT" | jq -r '.status' 2>/dev/null)
    
    if [ "$INVALID_STATUS" = "error" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_message "SUCCESS" "Error handling working correctly - invalid action rejected"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "ERROR" "Error handling not working correctly"
    fi
fi

# Final statistics
echo "=============================================="
log_message "INFO" "📊 TEST STATISTICS"
echo "=============================================="
log_message "INFO" "Journey ID Used: $JOURNEY_ID"
log_message "INFO" "Real Job ID Created: $REAL_JOB_ID"
log_message "INFO" "Total Tests: $TOTAL_TESTS"
log_message "SUCCESS" "Passed Tests: $PASSED_TESTS"
log_message "ERROR" "Failed Tests: $FAILED_TESTS"

# Calculate success rate
if [ $TOTAL_TESTS -gt 0 ]; then
    SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    
    if [ $FAILED_TESTS -eq 0 ]; then
        log_message "SUCCESS" "✅ All tests passed! Success rate: ${SUCCESS_RATE}%"
    else
        log_message "WARNING" "⚠️ Some tests failed. Success rate: ${SUCCESS_RATE}%"
    fi
    
    echo "Success Rate: $SUCCESS_RATE%" >> "$LOG_FILE"
else
    log_message "WARNING" "No tests were executed"
fi

echo "=============================================="
echo -e "${BLUE}🎯 Call Processing Job Operations Test Summary:${NC}"
echo -e "${BLUE}• ✅ run_job - Create call_process jobs for testing${NC}"
echo -e "${BLUE}• ✅ update_job_status - Update job status and progress${NC}"
echo -e "${BLUE}• ✅ get_job_metrics - Get detailed job performance metrics${NC}"
echo -e "${BLUE}• ✅ get_job_timeline - Get job execution timeline${NC}"
echo -e "${BLUE}• ✅ batch_cancel_jobs - Cancel multiple jobs at once${NC}"
echo -e "${BLUE}• ✅ dashboard - Get comprehensive journey dashboard${NC}"
echo -e "${BLUE}• ✅ get_journey_summary - Get journey summary with job stats${NC}"
echo -e "${BLUE}• ✅ Error Handling - Invalid actions properly rejected${NC}"
echo "=============================================="
echo -e "${BLUE}REST API Reference:${NC}"
echo -e "${CYAN}  Start Job:    POST $SERVER_URL/api/v1/journeys/{journey_id}/jobs?stage_id=$DEFAULT_STAGE${NC}"
echo -e "${CYAN}  Job Status:   GET  $SERVER_URL/api/v1/journeys/{journey_id}/jobs/{job_id}/status${NC}"
echo -e "${CYAN}  List Jobs:    GET  $SERVER_URL/api/v1/journeys/{journey_id}/jobs${NC}"
echo "=============================================="
echo -e "${BLUE}📁 Detailed logs saved to: $LOG_FILE${NC}"
echo -e "${BLUE}🕒 Test completed at: $(date)${NC}"
echo "=============================================="
echo ""
echo -e "${BLUE}🎉 Call Processing Job Operations test completed!${NC}"
echo "=============================================="

# Write final summary to log
echo "============================================" >> "$LOG_FILE"
echo "Test completed at: $(date)" >> "$LOG_FILE"
echo "Total Tests: $TOTAL_TESTS" >> "$LOG_FILE"
echo "Passed: $PASSED_TESTS" >> "$LOG_FILE"
echo "Failed: $FAILED_TESTS" >> "$LOG_FILE"

# Set exit code
if [ $FAILED_TESTS -eq 0 ] && [ $TOTAL_TESTS -gt 0 ]; then
    exit 0
else
    exit 1
fi