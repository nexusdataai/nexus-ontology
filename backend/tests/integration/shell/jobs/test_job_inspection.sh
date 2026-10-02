#!/bin/bash

# Journey Inspection Operations Test Script
# Tests journey inspection and reporting operations available through journeys_tool
# Tests: list_rules, dashboard, get_journey_summary, get_comprehensive, error handling

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"
ECHO_JSON=false

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
    echo -e "Journey Inspection Operations Test Script"
    echo ""
    echo -e "Usage: $0 [URL] [journey_id]"
    echo ""
    echo -e "Arguments:"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo -e "  journey_id             Journey ID to test with (optional)"
    echo ""
    echo -e "Examples:"
    echo -e "  $0                                            # Test on localhost:8000"
    echo -e "  $0 http://192.168.1.100:8000                  # Test on remote server"
    echo -e "  $0 http://18.191.87.212:8000 JRN-DEMO-001     # Test specific journey on remote server"
    echo -e "  $0 https://api.company.com                    # Use HTTPS connection"
    echo ""
    echo -e "Description:"
    echo -e "  Tests journey inspection and reporting operations including dashboard,"
    echo -e "  summary, rules listing, and comprehensive data retrieval."
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
                # This is the journey_id
                TEST_JOURNEY_ID="$1"
                shift
                ;;
        esac
    done
}

# Setup logging
SCRIPT_NAME="test_journey_inspection"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="/opt/mycode/ptr/ai-job-engine/logs"
LOG_FILE="$LOG_DIR/${SCRIPT_NAME}_${TIMESTAMP}.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Stats tracking
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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOG_FILE"
}

# Function to parse MCP response
parse_mcp_response() {
    local response="$1"
    echo "$response" | jq -r '.content[0].text' 2>/dev/null || echo "$response"
}

# Function to get API journey count
get_api_journey_count() {
    local count_response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
      -H "Content-Type: application/json" \
      -H "x-api-key: super-secret" \
      -d '{"arguments": {"action": "list"}}' 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        local result=$(parse_mcp_response "$count_response")
        echo "$result" | jq -r '.data | length' 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Function to select journey from API
select_journey_from_api() {
    log_message "INFO" "🔍 Fetching available journeys from database..."
    
    # Get list of journeys from API
    local list_response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
      -H "Content-Type: application/json" \
      -H "x-api-key: super-secret" \
      -d '{"arguments": {"action": "list"}}' 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        log_message "ERROR" "Failed to fetch journeys from database"
        return 1
    fi
    
    # Parse MCP response
    local result=$(parse_mcp_response "$list_response")
    local status=$(echo "$result" | jq -r '.status' 2>/dev/null)
    
    if [ "$status" != "success" ]; then
        log_message "ERROR" "Could not retrieve journeys. Please ensure the MCP server is running."
        return 1
    fi
    
    local journeys=$(echo "$result" | jq -r '.data' 2>/dev/null)
    local journey_count=$(echo "$journeys" | jq 'length' 2>/dev/null || echo 0)
    
    if [ "$journey_count" -eq 0 ] || [ "$journey_count" = "null" ]; then
        log_message "WARNING" "No journeys found in database"
        return 1
    fi
    
    log_message "SUCCESS" "Found $journey_count journeys in database"
    echo ""
    echo -e "${CYAN}📊 Available Journeys:${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
    
    # Display up to 5 journeys
    local display_count=$((journey_count > 5 ? 5 : journey_count))
    for i in $(seq 0 $((display_count - 1))); do
        local journey=$(echo "$journeys" | jq -r ".[$i]")
        local id=$(echo "$journey" | jq -r '.journeyId // .journey_id // "N/A"')
        local name=$(echo "$journey" | jq -r '.name // "Unnamed"')
        local status=$(echo "$journey" | jq -r '.status // "unknown"')
        local component=$(echo "$journey" | jq -r '.odaComponentType // "N/A"' | tr '[:upper:]' '[:lower:]' | sed 's/_/-/g')
        local created=$(echo "$journey" | jq -r '.createdAt // "N/A"' | cut -d'T' -f1)
        
        echo -e "${BLUE}  $((i + 1)). ${GREEN}$id${NC}"
        echo -e "      Name: ${YELLOW}$name${NC}"
        echo -e "      Status: ${CYAN}$status${NC} | Component: $component"
        echo -e "      Created: $created"
        echo ""
    done
    
    echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $((display_count + 1)). ${YELLOW}Enter custom Journey ID${NC}"
    echo ""
    echo ""
    
    # Get user selection with timeout
    echo -n "Select journey (1-$((display_count + 1))): "
    read -t 10 selection
    
    if [ -z "$selection" ]; then
        # Auto-select first journey if no input
        log_message "INFO" "⏱️ No selection made, auto-selecting first journey"
        selection="1"
    fi
    
    if [ "$selection" -eq $((display_count + 1)) ] 2>/dev/null; then
        # Custom journey ID
        echo -n "Enter Journey ID: "
        read -t 30 JOURNEY_ID
        if [ -z "$JOURNEY_ID" ]; then
            log_message "WARNING" "No Journey ID entered"
            return 1
        fi
        log_message "INFO" "📋 Using custom Journey ID: $JOURNEY_ID"
    elif [ "$selection" -ge 1 ] && [ "$selection" -le "$display_count" ] 2>/dev/null; then
        # Selected from list
        local index=$((selection - 1))
        local journey=$(echo "$journeys" | jq -r ".[$index]")
        JOURNEY_ID=$(echo "$journey" | jq -r '.journeyId // .journey_id // "N/A"')
        local name=$(echo "$journey" | jq -r '.name // "Unnamed"')
        local status=$(echo "$journey" | jq -r '.status // "unknown"')
        log_message "INFO" "📋 Selected: $JOURNEY_ID - $name (Status: $status)"
    else
        log_message "WARNING" "Invalid selection: $selection"
        # Auto-select first journey
        local journey=$(echo "$journeys" | jq -r ".[0]")
        JOURNEY_ID=$(echo "$journey" | jq -r '.journeyId // .journey_id // "N/A"')
        local name=$(echo "$journey" | jq -r '.name // "Unnamed"')
        local status=$(echo "$journey" | jq -r '.status // "unknown"')
        log_message "INFO" "📋 Auto-selected: $JOURNEY_ID - $name (Status: $status)"
    fi
    
    log_message "INFO" "📋 Using Journey ID: $JOURNEY_ID"
    echo ""
}

# Parse command line arguments
parse_arguments "$@"

# Start header
echo -e "${BLUE}🚀 Testing Journey Inspection Operations${NC}"
echo "=============================================="
echo -e "${BLUE}Script: $SCRIPT_NAME${NC}"
echo -e "${BLUE}Timestamp: $TIMESTAMP${NC}"
echo -e "${BLUE}Log file: $LOG_FILE${NC}"
echo -e "${BLUE}Server URL: $SERVER_URL${NC}"
echo "=============================================="

# Initialize log file
echo "Journey Inspection Operations Test Log" > "$LOG_FILE"
echo "Started at: $(date)" >> "$LOG_FILE"
echo "Server URL: $SERVER_URL" >> "$LOG_FILE"
echo "============================================" >> "$LOG_FILE"

# Step 1: Get or select journey ID
log_message "STEP" "Step 1: Select Journey"
echo ""

# Check if journey ID was provided
if [ -n "$TEST_JOURNEY_ID" ]; then
    JOURNEY_ID="$TEST_JOURNEY_ID"
    log_message "SUCCESS" "Using provided Journey ID: $JOURNEY_ID"
else
    # Select journey from database
    if ! select_journey_from_api; then
        log_message "ERROR" "Failed to select journey"
        exit 1
    fi
fi

log_message "SUCCESS" "Using Journey ID: $JOURNEY_ID"

# Step 2: Verify journey exists
log_message "STEP" "Step 2: Verify Journey Exists"

VERIFY_DATA='{
    "arguments": {
        "action": "read",
        "journey_id": "'$JOURNEY_ID'"
    }
}'

log_message "INFO" "Verifying journey exists..."
VERIFY_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
  -H "Content-Type: application/json" \
  -H "x-api-key: super-secret" \
  -d "$VERIFY_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
VERIFY_RESULT=$(parse_mcp_response "$VERIFY_RESPONSE")
VERIFY_STATUS=$(echo "$VERIFY_RESULT" | jq -r '.status' 2>/dev/null)

if [ "$VERIFY_STATUS" = "success" ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_message "SUCCESS" "Journey verification successful"
    
    JOURNEY_NAME=$(echo "$VERIFY_RESULT" | jq -r '.data.name // "Unknown"')
    JOURNEY_STATUS=$(echo "$VERIFY_RESULT" | jq -r '.data.status // "Unknown"')
    TOTAL_STAGES=$(echo "$VERIFY_RESULT" | jq -r '.data.stages | length // 0' 2>/dev/null)
    
    log_message "INFO" "Journey Name: $JOURNEY_NAME"
    log_message "INFO" "Journey Status: $JOURNEY_STATUS"
    log_message "INFO" "Total Stages: $TOTAL_STAGES"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_message "ERROR" "Journey verification failed"
    ERROR_MSG=$(echo "$VERIFY_RESULT" | jq -r '.message // .error // "Unknown error"')
    log_message "ERROR" "Error: $ERROR_MSG"
fi

echo "=============================================="

# Step 3: List journey rules
log_message "STEP" "Step 3: List Journey Rules"

LIST_RULES_DATA='{
    "arguments": {
        "action": "list_rules",
        "journey_id": "'$JOURNEY_ID'"
    }
}'

log_message "INFO" "Fetching journey rules..."
LIST_RULES_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
  -H "Content-Type: application/json" \
  -H "x-api-key: super-secret" \
  -d "$LIST_RULES_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
LIST_RULES_RESULT=$(parse_mcp_response "$LIST_RULES_RESPONSE")
LIST_RULES_STATUS=$(echo "$LIST_RULES_RESULT" | jq -r '.status' 2>/dev/null)

if [ "$LIST_RULES_STATUS" = "success" ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_message "SUCCESS" "Rules listing successful"
    
    RULES_COUNT=$(echo "$LIST_RULES_RESULT" | jq -r '.data | length // 0' 2>/dev/null)
    log_message "INFO" "Total Rules Found: $RULES_COUNT"
    
    # Display first few rules if any
    if [ "$RULES_COUNT" -gt 0 ] && [ "$RULES_COUNT" != "null" ]; then
        echo -e "${CYAN}Sample Rules:${NC}"
        echo "$LIST_RULES_RESULT" | jq -r '.data[:3][] | "  - \(.title // "Untitled") (\(.type // "unknown"))"' 2>/dev/null
    fi
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_message "ERROR" "Rules listing failed"
    ERROR_MSG=$(echo "$LIST_RULES_RESULT" | jq -r '.message // .error // "Unknown error"')
    log_message "ERROR" "Error: $ERROR_MSG"
fi

echo "=============================================="

# Step 4: Get journey dashboard
log_message "STEP" "Step 4: Get Journey Dashboard"

DASHBOARD_DATA='{
    "arguments": {
        "action": "dashboard",
        "journey_id": "'$JOURNEY_ID'"
    }
}'

log_message "INFO" "Fetching journey dashboard..."
DASHBOARD_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
  -H "Content-Type: application/json" \
  -H "x-api-key: super-secret" \
  -d "$DASHBOARD_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
DASHBOARD_RESULT=$(parse_mcp_response "$DASHBOARD_RESPONSE")
DASHBOARD_STATUS=$(echo "$DASHBOARD_RESULT" | jq -r '.status' 2>/dev/null)

if [ "$DASHBOARD_STATUS" = "success" ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_message "SUCCESS" "Dashboard retrieval successful"
    
    # Extract key metrics
    TOTAL_JOBS=$(echo "$DASHBOARD_RESULT" | jq -r '.data.summary.totalJobs // 0' 2>/dev/null)
    COMPLETED_JOBS=$(echo "$DASHBOARD_RESULT" | jq -r '.data.summary.completedJobs // 0' 2>/dev/null)
    FAILED_JOBS=$(echo "$DASHBOARD_RESULT" | jq -r '.data.summary.failedJobs // 0' 2>/dev/null)
    OVERALL_PROGRESS=$(echo "$DASHBOARD_RESULT" | jq -r '.data.summary.overallProgress // 0' 2>/dev/null)
    
    log_message "INFO" "Dashboard Metrics:"
    log_message "INFO" "  Total Jobs: $TOTAL_JOBS"
    log_message "INFO" "  Completed: $COMPLETED_JOBS"
    log_message "INFO" "  Failed: $FAILED_JOBS"
    log_message "INFO" "  Progress: ${OVERALL_PROGRESS}%"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_message "ERROR" "Dashboard retrieval failed"
    ERROR_MSG=$(echo "$DASHBOARD_RESULT" | jq -r '.message // .error // "Unknown error"')
    log_message "ERROR" "Error: $ERROR_MSG"
fi

echo "=============================================="

# Step 5: Get journey summary
log_message "STEP" "Step 5: Get Journey Summary"

SUMMARY_DATA='{
    "arguments": {
        "action": "get_journey_summary",
        "journey_id": "'$JOURNEY_ID'"
    }
}'

log_message "INFO" "Fetching journey summary..."
SUMMARY_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
  -H "Content-Type: application/json" \
  -H "x-api-key: super-secret" \
  -d "$SUMMARY_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
SUMMARY_RESULT=$(parse_mcp_response "$SUMMARY_RESPONSE")
SUMMARY_STATUS=$(echo "$SUMMARY_RESULT" | jq -r '.status' 2>/dev/null)

if [ "$SUMMARY_STATUS" = "success" ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_message "SUCCESS" "Journey summary retrieval successful"
    
    # Extract summary data
    JOBS_COUNT=$(echo "$SUMMARY_RESULT" | jq -r '.data.jobs | length // 0' 2>/dev/null)
    ACTIVE_STAGES=$(echo "$SUMMARY_RESULT" | jq -r '.data.activeStages // 0' 2>/dev/null)
    
    log_message "INFO" "Summary:"
    log_message "INFO" "  Jobs in Journey: $JOBS_COUNT"
    log_message "INFO" "  Active Stages: $ACTIVE_STAGES"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_message "ERROR" "Journey summary retrieval failed"
    ERROR_MSG=$(echo "$SUMMARY_RESULT" | jq -r '.message // .error // "Unknown error"')
    log_message "ERROR" "Error: $ERROR_MSG"
fi

echo "=============================================="

# Step 6: Get comprehensive journey data
log_message "STEP" "Step 6: Get Comprehensive Journey Data"

COMPREHENSIVE_DATA='{
    "arguments": {
        "action": "get_comprehensive",
        "journey_id": "'$JOURNEY_ID'"
    }
}'

log_message "INFO" "Fetching comprehensive journey data..."
COMPREHENSIVE_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
  -H "Content-Type: application/json" \
  -H "x-api-key: super-secret" \
  -d "$COMPREHENSIVE_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
COMPREHENSIVE_RESULT=$(parse_mcp_response "$COMPREHENSIVE_RESPONSE")
COMPREHENSIVE_STATUS=$(echo "$COMPREHENSIVE_RESULT" | jq -r '.status' 2>/dev/null)

if [ "$COMPREHENSIVE_STATUS" = "success" ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_message "SUCCESS" "Comprehensive data retrieval successful"
    
    # Check what data is included
    HAS_METADATA=$(echo "$COMPREHENSIVE_RESULT" | jq -r 'has("metadata")' 2>/dev/null)
    HAS_STAGES=$(echo "$COMPREHENSIVE_RESULT" | jq -r '.data | has("stages")' 2>/dev/null)
    HAS_RULES=$(echo "$COMPREHENSIVE_RESULT" | jq -r '.data | has("rules")' 2>/dev/null)
    HAS_JOBS=$(echo "$COMPREHENSIVE_RESULT" | jq -r '.data | has("jobs")' 2>/dev/null)
    
    log_message "INFO" "Comprehensive Data Includes:"
    [ "$HAS_METADATA" = "true" ] && log_message "INFO" "  ✓ Metadata"
    [ "$HAS_STAGES" = "true" ] && log_message "INFO" "  ✓ Stages"
    [ "$HAS_RULES" = "true" ] && log_message "INFO" "  ✓ Rules"
    [ "$HAS_JOBS" = "true" ] && log_message "INFO" "  ✓ Jobs"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_message "ERROR" "Comprehensive data retrieval failed"
    ERROR_MSG=$(echo "$COMPREHENSIVE_RESULT" | jq -r '.message // .error // "Unknown error"')
    log_message "ERROR" "Error: $ERROR_MSG"
fi

echo "=============================================="

# Step 7: Test error handling with invalid action
log_message "STEP" "Step 7: Test Error Handling"

INVALID_DATA='{
    "arguments": {
        "action": "invalid_action_xyz",
        "journey_id": "'$JOURNEY_ID'"
    }
}'

log_message "INFO" "Testing error handling with invalid action..."
INVALID_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
  -H "Content-Type: application/json" \
  -H "x-api-key: super-secret" \
  -d "$INVALID_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Check if we get an appropriate error
if echo "$INVALID_RESPONSE" | grep -q -E "(error|Invalid|invalid)" 2>/dev/null; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_message "SUCCESS" "Error handling working correctly"
    
    # Try to extract error message
    ERROR_MSG=$(echo "$INVALID_RESPONSE" | jq -r '.detail // .error // .message // "Validation error"' 2>/dev/null)
    log_message "INFO" "Error message: $ERROR_MSG"
else
    # Check MCP wrapped response
    INVALID_RESULT=$(parse_mcp_response "$INVALID_RESPONSE")
    INVALID_STATUS=$(echo "$INVALID_RESULT" | jq -r '.status' 2>/dev/null)
    
    if [ "$INVALID_STATUS" = "error" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_message "SUCCESS" "Error handling working correctly"
        ERROR_MSG=$(echo "$INVALID_RESULT" | jq -r '.message // .error // "Unknown error"')
        log_message "INFO" "Error message: $ERROR_MSG"
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
    
    echo "Success Rate: $SUCCESS_RATE" >> "$LOG_FILE"
else
    log_message "WARNING" "No tests were executed"
fi

echo "=============================================="
echo -e "${BLUE}🎯 Journey Inspection Operations Test Summary:${NC}"
echo -e "${BLUE}• ✅ Journey Verification - Tests journey lookup and validation${NC}"
echo -e "${BLUE}• ✅ Rules Listing - Tests listing Second Brain rules${NC}"
echo -e "${BLUE}• ✅ Dashboard Analytics - Tests dashboard data retrieval${NC}"
echo -e "${BLUE}• ✅ Journey Summary - Tests summary generation${NC}"
echo -e "${BLUE}• ✅ Comprehensive Data - Tests full journey data export${NC}"
echo -e "${BLUE}• ✅ Error Handling - Tests invalid action validation${NC}"
echo "=============================================="
echo -e "${BLUE}📁 Detailed logs saved to: $LOG_FILE${NC}"
echo -e "${BLUE}🕒 Test completed at: $(date)${NC}"
echo "=============================================="
echo ""
echo -e "${BLUE}🎉 Journey Inspection Operations test completed!${NC}"
echo "=============================================="

# Write final summary to log
echo "============================================" >> "$LOG_FILE"
echo "Test completed at: $(date)" >> "$LOG_FILE"
echo "Total Tests: $TOTAL_TESTS" >> "$LOG_FILE"
echo "Passed: $PASSED_TESTS" >> "$LOG_FILE"
echo "Failed: $FAILED_TESTS" >> "$LOG_FILE"

# Set exit code based on test results
if [ $FAILED_TESTS -eq 0 ] && [ $TOTAL_TESTS -gt 0 ]; then
    exit 0
else
    exit 1
fi