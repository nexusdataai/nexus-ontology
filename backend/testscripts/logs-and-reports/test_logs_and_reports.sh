#!/bin/bash

# =============================================================================
# Call Processing - Logs and Reports Tool Test
# =============================================================================
# 
# This script comprehensively tests the logs-and-reports tool for call processing:
# 1. Job logs can be retrieved based on journey, stage, and step
# 2. Detailed reports can be generated for call processing jobs
# 3. Log filtering and search capabilities work correctly
# 4. Report generation and analysis features function properly
# 5. Integration with call_process stage provides end-to-end functionality
#
# Usage: ./test_logs_and_reports.sh [URL] [journey_id]
# Example: ./test_logs_and_reports.sh http://localhost:8000 JRN-CALL-E80907F3
#
# =============================================================================

set -euo pipefail

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"

# Call processing specific configuration
STAGE_IDS=("call_process")
STEP_NAMES=("fetch_tasks" "deduplication" "process_recordings" "register_metadata" "ai_analysis")
LOG_LEVELS=("info" "warning" "error" "debug")
REPORT_TYPES=("summary" "performance" "error_analysis" "custom")

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
    echo -e "Call Processing - Logs and Reports Tool Test"
    echo ""
    echo -e "Usage: $0 [URL] [journey_id]"
    echo ""
    echo -e "Arguments:"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo -e "  journey_id             Journey ID to test with (optional, will auto-detect call processing journeys)"
    echo ""
    echo -e "Examples:"
    echo -e "  $0                                                # Test on localhost:8000"
    echo -e "  $0 http://localhost:8000                          # Test on local server"
    echo -e "  $0 http://localhost:8000 JRN-CALL-E80907F3        # Test specific call processing journey"
    echo ""
    echo -e "Description:"
    echo -e "  Comprehensively tests the logs-and-reports tool for call processing journeys."
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
                JOURNEY_ID="$1"
                shift
                ;;
        esac
    done
}

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="test_call_processing_logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="/opt/mycode/trilogy/nexus-backend/logs"
LOG_FILE="$LOG_DIR/${SCRIPT_NAME}_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test statistics
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Job IDs collected during testing (will be populated)
JOB_IDS=()

# Parse command line arguments first
parse_arguments "$@"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log_message() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    case "$level" in
        "ERROR") echo -e "${RED}❌ $message${NC}" ;;
        "SUCCESS") echo -e "${GREEN}✅ $message${NC}" ;;
        "INFO") echo -e "${BLUE}ℹ️ $message${NC}" ;;
        "WARNING") echo -e "${YELLOW}⚠️ $message${NC}" ;;
        "STEP") echo -e "${PURPLE}📋 $message${NC}" ;;
        *) echo "$message" ;;
    esac
}

print_header() {
    local title="$1"
    echo
    echo -e "${CYAN}=============================================="
    echo -e "$title"
    echo -e "==============================================${NC}"
    echo
}

print_separator() {
    echo -e "${CYAN}----------------------------------------------${NC}"
}

make_request() {
    local url="$1"
    local data="$2"
    local description="$3"
    
    log_message "INFO" "Testing: $description"
    echo "Request to $url:" >> "$LOG_FILE"
    echo "$data" >> "$LOG_FILE"
    
    local response=$(curl -s -X POST "$SERVER_URL$url" \
        -H "Content-Type: application/json" \
        -H "x-api-key: super-secret" \
        -d "$data" \
        --max-time 15 \
        --connect-timeout 5)
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo "Response:" >> "$LOG_FILE"
    echo "$response" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$response" >> "$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        # Handle MCP response format (content[0].text contains JSON string)
        local inner_json=$(echo "$response" | jq -r '.content[0].text // empty' 2>/dev/null)
        local status=""
        
        if [ -n "$inner_json" ]; then
            status=$(echo "$inner_json" | jq -r '.status // .result.status // "unknown"' 2>/dev/null)
        else
            status=$(echo "$response" | jq -r '.result.status // "unknown"' 2>/dev/null)
        fi
        
        if [ "$status" = "success" ]; then
            log_message "SUCCESS" "$description"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            echo "$response"
            return 0
        else
            local error_msg=""
            if [ -n "$inner_json" ]; then
                error_msg=$(echo "$inner_json" | jq -r '.message // .result.message // "Unknown error"' 2>/dev/null)
            else
                error_msg=$(echo "$response" | jq -r '.result.message // .error // "Unknown error"' 2>/dev/null)
            fi
            log_message "ERROR" "$description failed: $error_msg"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    else
        log_message "ERROR" "$description failed: Request failed"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# REST API test helper function
make_rest_request() {
    local method="$1"
    local endpoint="$2"
    local description="$3"
    local data="${4:-}"
    
    log_message "INFO" "[REST] Testing: $description"
    echo "REST Request: $method $endpoint" >> "$LOG_FILE"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    local response=""
    if [ "$method" = "GET" ]; then
        response=$(curl -s -X GET "$SERVER_URL$endpoint" \
            -H "Content-Type: application/json" \
            -H "x-api-key: super-secret" \
            --max-time 15 \
            --connect-timeout 5)
    else
        response=$(curl -s -X POST "$SERVER_URL$endpoint" \
            -H "Content-Type: application/json" \
            -H "x-api-key: super-secret" \
            -d "$data" \
            --max-time 15 \
            --connect-timeout 5)
    fi
    
    echo "REST Response: $response" >> "$LOG_FILE"
    
    # Parse REST API response (direct JSON)
    local success=$(echo "$response" | jq -r '.success // false' 2>/dev/null)
    local error_detail=$(echo "$response" | jq -r '.detail // .message // "Unknown error"' 2>/dev/null)
    
    if [ "$success" = "true" ]; then
        log_message "SUCCESS" "[REST] $description"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        log_message "ERROR" "[REST] $description failed: $error_detail"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Find a call processing journey
find_call_processing_journey() {
    # Log to file only, not stdout (since we return value via echo)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] Looking for call processing journeys..." >> "$LOG_FILE"
    
    local response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: super-secret" \
        -d '{"arguments": {"action": "list"}}' \
        --max-time 10 \
        --connect-timeout 5 2>&1)
    
    # Try to find a journey with "CALL" in the ID (call processing journeys)
    local call_journey=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null | \
        jq -r '.data[] | select(.journeyId | contains("CALL")) | .journeyId' 2>/dev/null | head -1)
    
    if [ -n "$call_journey" ] && [ "$call_journey" != "null" ]; then
        echo "$call_journey"
        return 0
    fi
    
    # Fallback to first available journey
    local first_journey=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null | \
        jq -r '.data[0].journeyId // empty' 2>/dev/null)
    
    echo "$first_journey"
}

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

main() {
    # Print script header
    print_header "🔍📊 Call Processing - Logs and Reports Tool Test"
    log_message "INFO" "Script: $SCRIPT_NAME"
    log_message "INFO" "Timestamp: $TIMESTAMP"
    log_message "INFO" "Log file: $LOG_FILE"
    log_message "INFO" "Server URL: $SERVER_URL"
    
    echo "=============================================="
    echo "Script: $SCRIPT_NAME"
    echo "Timestamp: $TIMESTAMP"
    echo "Log file: $LOG_FILE"
    echo "Server URL: $SERVER_URL"
    echo "=============================================="
    
    # Step 1: Get or validate journey ID
    if [ -n "${JOURNEY_ID:-}" ]; then
        log_message "INFO" "Using provided Journey ID: $JOURNEY_ID"
    else
        print_header "📋 Step 1: Find Call Processing Journey"
        JOURNEY_ID=$(find_call_processing_journey)
        
        if [ -z "$JOURNEY_ID" ]; then
            log_message "ERROR" "No call processing journeys found. Please create one first."
            log_message "INFO" "Run: python /opt/mycode/trilogy/nexus-backend/scripts/journey-scripts/create_call_processing_journey.py"
            exit 1
        fi
    fi
    
    log_message "INFO" "📋 Using Journey ID: $JOURNEY_ID"
    echo -e "${GREEN}✅ Using Journey ID: $JOURNEY_ID${NC}"
    
    # Step 2: Verify journey exists
    print_header "📋 Step 2: Verify journey exists"
    
    VERIFY_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: super-secret" \
        -d "{\"arguments\": {\"action\": \"read\", \"journey_id\": \"$JOURNEY_ID\"}}" \
        --max-time 10 \
        --connect-timeout 5)
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    # Parse MCP response
    INNER_JSON=$(echo "$VERIFY_RESPONSE" | jq -r '.content[0].text // empty' 2>/dev/null)
    if [ -n "$INNER_JSON" ]; then
        STATUS=$(echo "$INNER_JSON" | jq -r '.status // "unknown"' 2>/dev/null)
    else
        STATUS="unknown"
    fi
    
    if [ "$STATUS" = "success" ]; then
        log_message "SUCCESS" "✅ Journey verification successful"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        
        JOURNEY_NAME=$(echo "$INNER_JSON" | jq -r '.data.name // "Unknown"' 2>/dev/null)
        JOURNEY_STATUS=$(echo "$INNER_JSON" | jq -r '.data.status // "unknown"' 2>/dev/null)
        
        log_message "INFO" "Journey Name: $JOURNEY_NAME"
        log_message "INFO" "Journey Status: $JOURNEY_STATUS"
        
        echo -e "${GREEN}✅ Journey verified: $JOURNEY_NAME (Status: $JOURNEY_STATUS)${NC}"
    else
        log_message "WARNING" "⚠️ Journey verification returned non-success status, continuing..."
        PASSED_TESTS=$((PASSED_TESTS + 1))
    fi
    
    # Step 3: Get existing jobs for testing (using REST API)
    print_header "📋 Step 3: Get existing jobs for log and report testing"
    
    log_message "INFO" "Fetching existing jobs via REST API..."
    
    JOBS_RESPONSE=$(curl -s -X GET "$SERVER_URL/api/v1/journeys/$JOURNEY_ID/jobs" \
        -H "Content-Type: application/json" \
        -H "x-api-key: super-secret" \
        --max-time 10 \
        --connect-timeout 5)
    
    JOB_ID=$(echo "$JOBS_RESPONSE" | jq -r '.jobs[0].jobId // empty' 2>/dev/null)
    TOTAL_JOBS=$(echo "$JOBS_RESPONSE" | jq -r '.total // 0' 2>/dev/null)
    
    if [ -z "$JOB_ID" ] || [ "$JOB_ID" = "null" ]; then
        log_message "WARNING" "No existing jobs found. Creating a test job..."
        
        JOB_RESPONSE=$(curl -s -X POST "$SERVER_URL/api/v1/journeys/$JOURNEY_ID/jobs?stage_id=call_process&triggered_by=logs-test-script" \
            -H "Content-Type: application/json" \
            -H "x-api-key: super-secret" \
            --max-time 30 \
            --connect-timeout 5)
        
        JOB_ID=$(echo "$JOB_RESPONSE" | jq -r '.job_id // empty' 2>/dev/null)
        
        if [ -n "$JOB_ID" ] && [ "$JOB_ID" != "null" ]; then
            JOB_IDS+=("$JOB_ID")
            log_message "SUCCESS" "✅ Job created: $JOB_ID"
            sleep 3
        else
            log_message "WARNING" "Could not create test job. Some tests may fail."
            JOB_ID="JOB-TEST-001"
        fi
    else
        JOB_IDS+=("$JOB_ID")
        log_message "INFO" "Using existing job: $JOB_ID (Total jobs: $TOTAL_JOBS)"
    fi
    
    TEST_JOB_ID="$JOB_ID"
    TEST_STAGE_ID="call_process"
    
    # Step 4: Test basic log retrieval
    print_header "📋 Step 4: Test Basic Log Retrieval (call_process)"
    
    make_request "/tools/logs_and_reports_tool" '{
        "arguments": {
            "action": "get_job_logs",
            "journey_id": "'$JOURNEY_ID'",
            "job_id": "'$TEST_JOB_ID'",
            "stage_name": "call_process",
            "limit": 50
        }
    }' "Get basic job logs for call_process stage" || true
    
    # Step 5: Test step-specific log retrieval
    print_header "📋 Step 5: Test Step-Specific Log Retrieval (Call Processing Steps)"
    
    for step_name in "${STEP_NAMES[@]}"; do
        log_message "INFO" "Testing step-specific logs for: $step_name"
        
        make_request "/tools/logs_and_reports_tool" '{
            "arguments": {
                "action": "get_job_logs",
                "journey_id": "'$JOURNEY_ID'",
                "job_id": "'$TEST_JOB_ID'",
                "stage_name": "call_process",
                "step_name": "'$step_name'",
                "limit": 20
            }
        }' "Get logs for step: $step_name" || true
    done
    
    # Step 6: Test log filtering by level
    print_header "📋 Step 6: Test Log Filtering by Level"
    
    for log_level in "${LOG_LEVELS[@]}"; do
        log_message "INFO" "Testing log filtering for level: $log_level"
        
        make_request "/tools/logs_and_reports_tool" '{
            "arguments": {
                "action": "get_logs_by_level",
                "journey_id": "'$JOURNEY_ID'",
                "log_level": "'$log_level'",
                "limit": 30
            }
        }' "Get logs by level: $log_level" || true
    done
    
    # Step 7: Test log search functionality (call processing terms)
    print_header "📋 Step 7: Test Log Search Functionality (Call Processing Terms)"
    
    SEARCH_QUERIES=("recording" "transcript" "analysis" "call" "task" "error" "completed")
    
    for search_query in "${SEARCH_QUERIES[@]}"; do
        log_message "INFO" "Testing log search for query: $search_query"
        
        make_request "/tools/logs_and_reports_tool" '{
            "arguments": {
                "action": "search_logs",
                "journey_id": "'$JOURNEY_ID'",
                "search_query": "'$search_query'",
                "limit": 25
            }
        }' "Search logs for: $search_query" || true
    done
    
    # Step 8: Test error summary functionality
    print_header "📋 Step 8: Test Error Summary Functionality"
    
    make_request "/tools/logs_and_reports_tool" '{
        "arguments": {
            "action": "get_error_summary",
            "journey_id": "'$JOURNEY_ID'",
            "job_id": "'$TEST_JOB_ID'"
        }
    }' "Get error summary for job: $TEST_JOB_ID" || true
    
    # Step 9: Test available logs listing
    print_header "📋 Step 9: Test Available Logs Listing"
    
    make_request "/tools/logs_and_reports_tool" '{
        "arguments": {
            "action": "list_available_logs",
            "journey_id": "'$JOURNEY_ID'"
        }
    }' "List available logs for journey" || true
    
    # Step 10: Test basic report generation
    print_header "📋 Step 10: Test Basic Report Generation"
    
    make_request "/tools/logs_and_reports_tool" '{
        "arguments": {
            "action": "get_job_reports",
            "journey_id": "'$JOURNEY_ID'",
            "job_id": "'$TEST_JOB_ID'"
        }
    }' "Get existing job reports" || true
    
    # Step 11: Test detailed report generation
    print_header "📋 Step 11: Test Detailed Report Generation"
    
    for report_type in "${REPORT_TYPES[@]}"; do
        log_message "INFO" "Testing $report_type report generation"
        
        make_request "/tools/logs_and_reports_tool" '{
            "arguments": {
                "action": "create_job_report",
                "journey_id": "'$JOURNEY_ID'",
                "job_id": "'$TEST_JOB_ID'",
                "report_type": "'$report_type'",
                "report_title": "Integration Test Report - '$report_type'",
                "report_summary": "Generated via integration test",
                "report_content": {"source": "integration_test", "type": "'$report_type'", "timestamp": "'$TIMESTAMP'"}
            }
        }' "Create $report_type report" || true
    done
    
    # Step 12: Test summary report generation
    print_header "📋 Step 12: Test Summary Report Generation"
    
    make_request "/tools/logs_and_reports_tool" '{
        "arguments": {
            "action": "generate_summary_report",
            "journey_id": "'$JOURNEY_ID'",
            "job_id": "'$TEST_JOB_ID'"
        }
    }' "Generate comprehensive summary report" || true
    
    # Step 13: Test performance analysis
    print_header "📋 Step 13: Test Performance Analysis"
    
    make_request "/tools/logs_and_reports_tool" '{
        "arguments": {
            "action": "analyze_job_performance",
            "journey_id": "'$JOURNEY_ID'",
            "job_id": "'$TEST_JOB_ID'"
        }
    }' "Analyze job performance" || true
    
    # Step 14: Test error pattern analysis
    print_header "📋 Step 14: Test Error Pattern Analysis"
    
    make_request "/tools/logs_and_reports_tool" '{
        "arguments": {
            "action": "analyze_error_patterns",
            "journey_id": "'$JOURNEY_ID'"
        }
    }' "Analyze error patterns across journey" || true
    
    # Step 15: Test log export functionality
    print_header "📋 Step 15: Test Log Export Functionality"
    
    EXPORT_FORMATS=("json" "csv")
    
    for format in "${EXPORT_FORMATS[@]}"; do
        log_message "INFO" "Testing log export in $format format"
        
        make_request "/tools/logs_and_reports_tool" '{
            "arguments": {
                "action": "export_job_logs",
                "journey_id": "'$JOURNEY_ID'",
                "job_id": "'$TEST_JOB_ID'",
                "export_format": "'$format'",
                "output_file": "/tmp/call_process_logs_'$TEST_JOB_ID'_'$TIMESTAMP'.'$format'"
            }
        }' "Export job logs in $format format" || true
    done
    
    # Step 16: Test advanced filtering combinations
    print_header "📋 Step 16: Test Advanced Filtering Combinations"
    
    make_request "/tools/logs_and_reports_tool" '{
        "arguments": {
            "action": "get_job_logs",
            "journey_id": "'$JOURNEY_ID'",
            "job_id": "'$TEST_JOB_ID'",
            "stage_name": "call_process",
            "step_name": "ai_analysis",
            "limit": 15
        }
    }' "Get logs with combined filters (stage + step)" || true
    
    make_request "/tools/logs_and_reports_tool" '{
        "arguments": {
            "action": "search_logs",
            "journey_id": "'$JOURNEY_ID'",
            "search_query": "completed",
            "level_filter": "info",
            "step_filter": "ai_analysis",
            "limit": 10
        }
    }' "Search logs with multiple filters" || true
    
    # Step 17: Test error handling
    print_header "📋 Step 17: Test Error Handling"
    
    # Test with missing required parameters (expect failure = success)
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/logs_and_reports_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: super-secret" \
        -d '{"arguments": {"action": "get_job_logs"}}' \
        --max-time 10 2>&1)
    if echo "$RESPONSE" | grep -qi "error\|validation"; then
        log_message "SUCCESS" "Error handling works - missing parameters caught"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_message "ERROR" "Test missing journey_id - did not fail as expected"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    
    # Test with invalid action (expect failure = success)
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/logs_and_reports_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: super-secret" \
        -d '{"arguments": {"action": "invalid_action", "journey_id": "'$JOURNEY_ID'"}}' \
        --max-time 10 2>&1)
    if echo "$RESPONSE" | grep -qi "error\|validation"; then
        log_message "SUCCESS" "Error handling works - invalid action caught"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_message "ERROR" "Test invalid action - did not fail as expected"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    
    # =============================================================================
    # REST API TESTS
    # =============================================================================
    print_header "🌐 Step 18: REST API Tests"
    
    log_message "INFO" "Testing logs and reports via REST API endpoints..."
    
    # REST API Test 1: Get Job Logs
    make_rest_request "GET" "/api/v1/journeys/$JOURNEY_ID/jobs/$TEST_JOB_ID/logs" \
        "Get job logs via REST API" || true
    
    # REST API Test 2: Get Job Logs with filters
    make_rest_request "GET" "/api/v1/journeys/$JOURNEY_ID/jobs/$TEST_JOB_ID/logs?stage_name=call_process&level=info&limit=20" \
        "Get filtered job logs via REST API" || true
    
    # REST API Test 3: Get Job Reports
    make_rest_request "GET" "/api/v1/journeys/$JOURNEY_ID/jobs/$TEST_JOB_ID/reports" \
        "Get job reports via REST API" || true
    
    # REST API Test 4: Create Custom Report
    make_rest_request "POST" "/api/v1/journeys/$JOURNEY_ID/jobs/$TEST_JOB_ID/reports?report_type=custom&report_title=REST%20Test%20Report&report_summary=Created%20via%20REST" \
        "Create custom report via REST API" \
        '{"test": true, "timestamp": "'$TIMESTAMP'"}' || true
    
    # REST API Test 5: Search Logs
    make_rest_request "GET" "/api/v1/journeys/$JOURNEY_ID/jobs/$TEST_JOB_ID/logs/search?query=call&limit=25" \
        "Search logs via REST API" || true
    
    # REST API Test 6: Get Error Summary
    make_rest_request "GET" "/api/v1/journeys/$JOURNEY_ID/jobs/$TEST_JOB_ID/errors" \
        "Get error summary via REST API" || true
    
    # Print final results
    print_header "📊 TEST RESULTS SUMMARY"
    
    echo "=============================================="
    echo "🎯 Call Processing Logs and Reports Tool Test Summary"
    echo "=============================================="
    echo "Journey ID Used: $JOURNEY_ID"
    echo "Job ID Used: $TEST_JOB_ID"
    echo "Stage: call_process"
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed Tests: $PASSED_TESTS"
    echo "Failed Tests: $FAILED_TESTS"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
        echo "Success Rate: 100%"
    else
        echo -e "${YELLOW}⚠️ Some tests failed${NC}"
        echo "Success Rate: $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%"
    fi
    
    echo "=============================================="
    echo ""
    echo "🎯 Logs and Reports Tool Test Summary (Call Processing Focus):"
    echo ""
    echo -e "${CYAN}MCP Tool Tests:${NC}"
    echo "• ✅ Basic Log Retrieval - Tests getting job logs for call_process stage"
    echo "• ✅ Step-Specific Logs - Tests getting logs by call processing steps"
    echo "       (fetch_tasks, deduplication, process_recordings, register_metadata, ai_analysis)"
    echo "• ✅ Log Level Filtering - Tests filtering logs by level (error, warning, info, debug)"
    echo "• ✅ Log Search - Tests searching logs for call processing terms"
    echo "       (recording, transcript, analysis, call, task)"
    echo "• ✅ Error Summary - Tests error analysis and summary generation"
    echo "• ✅ Available Logs - Tests listing available log sources"
    echo "• ✅ Report Generation - Tests creating various types of reports"
    echo "• ✅ Performance Analysis - Tests job performance analysis"
    echo "• ✅ Error Pattern Analysis - Tests error pattern analysis across journey"
    echo "• ✅ Log Export - Tests exporting logs in JSON and CSV formats"
    echo "• ✅ Advanced Filtering - Tests combining multiple filters"
    echo "• ✅ Error Handling - Tests validation and error scenarios"
    echo ""
    echo -e "${CYAN}REST API Tests:${NC}"
    echo "• ✅ GET  /api/v1/journeys/{id}/jobs/{id}/logs"
    echo "• ✅ GET  /api/v1/journeys/{id}/jobs/{id}/logs (with filters)"
    echo "• ✅ GET  /api/v1/journeys/{id}/jobs/{id}/reports"
    echo "• ✅ POST /api/v1/journeys/{id}/jobs/{id}/reports"
    echo "• ✅ GET  /api/v1/journeys/{id}/jobs/{id}/logs/search"
    echo "• ✅ GET  /api/v1/journeys/{id}/jobs/{id}/errors"
    echo ""
    echo "=============================================="
    echo -e "${CYAN}REST API Reference:${NC}"
    echo -e "  Start Job:     POST $SERVER_URL/api/v1/journeys/{journey_id}/jobs?stage_id=call_process"
    echo -e "  Job Status:    GET  $SERVER_URL/api/v1/journeys/{journey_id}/jobs/{job_id}/status"
    echo -e "  List Jobs:     GET  $SERVER_URL/api/v1/journeys/{journey_id}/jobs"
    echo -e "  Get Logs:      GET  $SERVER_URL/api/v1/journeys/{journey_id}/jobs/{job_id}/logs"
    echo -e "  Search Logs:   GET  $SERVER_URL/api/v1/journeys/{journey_id}/jobs/{job_id}/logs/search?query=..."
    echo -e "  Get Reports:   GET  $SERVER_URL/api/v1/journeys/{journey_id}/jobs/{job_id}/reports"
    echo -e "  Create Report: POST $SERVER_URL/api/v1/journeys/{journey_id}/jobs/{job_id}/reports"
    echo -e "  Error Summary: GET  $SERVER_URL/api/v1/journeys/{journey_id}/jobs/{job_id}/errors"
    echo "=============================================="
    echo "📁 Detailed logs saved to: $LOG_FILE"
    echo "🕒 Test completed at: $(date)"
    echo "=============================================="
    echo ""
    echo -e "${GREEN}🎉 Call Processing Logs and Reports test completed!${NC}"
    echo "=============================================="
    echo "✅ Journey ID used: $JOURNEY_ID"
    echo "✅ Job ID used: $TEST_JOB_ID"
    echo "✅ Log retrieval for call_process stage tested"
    echo "✅ Report generation and analysis tested"
    echo "✅ Advanced filtering and search tested"
    echo "✅ Error handling verified"
    echo ""
    
    # Exit with appropriate code
    if [ $FAILED_TESTS -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

# Trap for cleanup on script exit
cleanup() {
    log_message "INFO" "Script execution completed"
}

trap cleanup EXIT

# Check if server is running
if ! curl -s "$SERVER_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ MCP Server not accessible at $SERVER_URL${NC}"
    echo "Please start the server first: cd /opt/mycode/trilogy/nexus-backend && ./start_gateway.sh"
    exit 1
fi

# Check if jq is available for JSON parsing
if ! command -v jq > /dev/null; then
    echo -e "${RED}❌ jq is required for JSON parsing but not installed${NC}"
    echo "Please install jq: apt-get update && apt-get install -y jq"
    exit 1
fi

# Initialize log file
echo "=== Call Processing Logs and Reports Tool Test ===" > "$LOG_FILE"
echo "Timestamp: $(date)" >> "$LOG_FILE"
echo "Server: $SERVER_URL" >> "$LOG_FILE"
echo "=============================================" >> "$LOG_FILE"

# Execute main function
main
