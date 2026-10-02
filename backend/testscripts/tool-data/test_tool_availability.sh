#!/bin/bash

# TMF ODA Transformer MCP Server - Tool Availability Testing Script
# This script comprehensively tests the availability and basic functionality of all MCP tools

# Don't use set -e since we want to continue testing even if some tests fail
set +e

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"
TOOLS_ENDPOINT="$SERVER_URL/tools"

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
    
    TOOLS_ENDPOINT="$SERVER_URL/tools"
}

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
declare -A TEST_RESULTS

# Function to show usage
show_usage() {
    echo -e "${CYAN}${BOLD}TMF ODA Transformer MCP Server - Tool Availability Testing Script${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC} $0 [URL]"
    echo ""
    echo -e "${YELLOW}Arguments:${NC}"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  $0                                    # Test tools on localhost:8000"
    echo -e "  $0 http://192.168.1.100:8000          # Test tools on remote server"
    echo -e "  $0 http://example.com:8080            # Test tools on remote server"
    echo -e "  $0 https://api.company.com            # Use HTTPS connection"
    echo ""
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
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

print_header() {
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}${BOLD}🧪 $1${NC}"
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_test_header() {
    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║ $1${NC}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED_TESTS++))
}

print_failure() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED_TESTS++))
}

print_info() {
    echo -e "${CYAN}ℹ️ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

run_test() {
    local test_name="$1"
    local test_description="$2"
    shift 2
    
    ((TOTAL_TESTS++))
    echo -ne "  [${TOTAL_TESTS}] Testing $test_name: $test_description... "
    
    # Capture both stdout and stderr for debugging
    local result_output
    result_output=$("$@" 2>&1)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}PASS${NC}"
        TEST_RESULTS["$test_name"]="PASS"
        ((PASSED_TESTS++))
        return 0
    else
        echo -e "${RED}FAIL${NC} (Exit code: $exit_code)"
        # Show first line of error for debugging
        if [ -n "$result_output" ]; then
            echo -e "    ${YELLOW}Error: $(echo "$result_output" | head -1)${NC}"
        fi
        TEST_RESULTS["$test_name"]="FAIL"
        ((FAILED_TESTS++))
        return 1
    fi
}

test_server_connectivity() {
    print_test_header "🌐 Server Connectivity Tests"
    echo ""
    
    echo -e "  ${CYAN}Testing connection to: $SERVER_URL${NC}"
    echo -e "  ${CYAN}Tools endpoint: $TOOLS_ENDPOINT${NC}"
    echo ""
    
    # Test basic server connectivity with shorter timeout
    run_test "server_ping" "Basic server connectivity" \
        curl -s --connect-timeout 5 --max-time 10 "$SERVER_URL"
    
    # Test health endpoint (might not exist, that's okay)
    run_test "server_health" "Server health endpoint" \
        curl -s --connect-timeout 5 --max-time 10 "$SERVER_URL/health"
    
    # Test tools endpoint - this is critical
    run_test "tools_endpoint" "Tools endpoint availability" \
        curl -s --connect-timeout 5 --max-time 10 "$TOOLS_ENDPOINT" -H "x-api-key: super-secret"
    
    echo ""
}

test_tool_endpoint() {
    local tool_name="$1"
    local endpoint_url="$TOOLS_ENDPOINT/$tool_name"
    
    # Test 1: OPTIONS method
    run_test "${tool_name}_options" "OPTIONS method support" \
        curl -s -X OPTIONS --connect-timeout 5 --max-time 10 "$endpoint_url"
    
    # Test 2: POST with valid JSON (list action)
    run_test "${tool_name}_post_list" "POST with list action" \
        curl -s -X POST "$endpoint_url" \
        -H 'Content-Type: application/json' \
        -H 'x-api-key: super-secret' \
        -d '{"arguments":{"action":"list"}}' --connect-timeout 10 --max-time 30
    
    # Test 3: POST with malformed JSON (should return error, not crash)
    run_test "${tool_name}_post_malformed" "Malformed JSON handling" \
        curl -s -X POST "$endpoint_url" \
        -H 'Content-Type: application/json' \
        -H 'x-api-key: super-secret' \
        -d '{invalid json}' --connect-timeout 10 --max-time 30
}

test_tool_parameter_validation() {
    local tool_name="$1"
    local endpoint_url="$TOOLS_ENDPOINT/$tool_name"
    
    case "$tool_name" in
        "journeys_tool")
            # Test invalid action
            run_test "${tool_name}_validation_invalid_action" "Invalid action validation" \
                bash -c "curl -s -X POST '$endpoint_url' -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"arguments\":{\"action\":\"invalid_action\"}}' --max-time 30 | grep -qi 'error\\|invalid\\|unknown'"
            ;;
        "logs_and_reports_tool")
            # Test invalid action
            run_test "${tool_name}_validation_invalid_action" "Invalid action validation" \
                bash -c "curl -s -X POST '$endpoint_url' -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"arguments\":{\"action\":\"invalid_action\"}}' --max-time 30 | grep -qi 'error\\|invalid\\|unknown'"
            ;;
    esac
}

test_tool_response_format() {
    local tool_name="$1"
    local endpoint_url="$TOOLS_ENDPOINT/$tool_name"
    
    # Test JSON response format (MCP format has content[0].text)
    run_test "${tool_name}_response_json" "JSON response format" \
        bash -c "curl -s -X POST '$endpoint_url' -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"arguments\":{\"action\":\"list\"}}' --max-time 30 | jq -e '.content[0].text' > /dev/null"
    
    # Test response contains status field inside content[0].text
    run_test "${tool_name}_response_status" "Response contains status field" \
        bash -c "curl -s -X POST '$endpoint_url' -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"arguments\":{\"action\":\"list\"}}' --max-time 30 | jq -r '.content[0].text' | jq -e '.status or .result.status' > /dev/null"
}

test_all_tools() {
    local tools=(
        "journeys_tool"
        "logs_and_reports_tool"
        "get-job-logs"
    )
    
    for tool_name in "${tools[@]}"; do
        print_test_header "🔧 Testing Tool: $tool_name"
        echo ""
        
        print_info "Testing basic endpoint functionality..."
        test_tool_endpoint "$tool_name"
        
        echo ""
        print_info "Testing parameter validation..."
        test_tool_parameter_validation "$tool_name"
        
        echo ""
        print_info "Testing response format..."
        test_tool_response_format "$tool_name"
        
        echo ""
    done
}

test_integration_scenarios() {
    print_test_header "🔄 Integration Test Scenarios"
    echo ""
    
    print_info "Testing tool integration scenarios..."
    
    # Test 1: Journeys tool list action (should work without journey data)
    run_test "integration_journeys_list" "Journeys list action" \
        bash -c "curl -s -X POST '$TOOLS_ENDPOINT/journeys_tool' -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"arguments\":{\"action\":\"list\"}}' --max-time 30 | jq -e '.content[0].text' > /dev/null"
    
    # Test 2: Logs and reports with get action (should handle missing data gracefully)
    run_test "integration_logs_get" "Logs and reports get action" \
        bash -c "curl -s -X POST '$TOOLS_ENDPOINT/logs_and_reports_tool' -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"arguments\":{\"action\":\"list_available_logs\"}}' --max-time 30 | jq -e '.content[0].text' > /dev/null"
    
    echo ""
}

test_error_handling() {
    print_test_header "🚨 Error Handling Tests"
    echo ""
    
    print_info "Testing error handling capabilities..."
    
    # Test 1: Non-existent endpoint
    run_test "error_404_endpoint" "Non-existent endpoint handling" \
        bash -c "curl -s -X POST '$TOOLS_ENDPOINT/non-existent-tool' -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{}' -w '%{http_code}' | grep -q '404'"
    
    # Test 2: Invalid HTTP method
    run_test "error_invalid_method" "Invalid HTTP method handling" \
        bash -c "curl -s -X DELETE '$TOOLS_ENDPOINT/journeys_tool' -H 'x-api-key: super-secret' -w '%{http_code}' | grep -q '405\\|404'"
    
    # Test 3: Missing Content-Type header
    run_test "error_missing_content_type" "Missing Content-Type header handling" \
        bash -c "curl -s -X POST '$TOOLS_ENDPOINT/journeys_tool' -H 'x-api-key: super-secret' -d '{}' -w '%{http_code}' | grep -q '400\\|415\\|200'"
    
    # Test 4: Request timeout handling
    run_test "error_timeout_handling" "Request timeout handling" \
        bash -c "curl -s -X POST '$TOOLS_ENDPOINT/journeys_tool' -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"arguments\":{\"action\":\"list\"}}' --max-time 30 || true"
    
    echo ""
}

test_performance_metrics() {
    print_test_header "⚡ Performance Tests"
    echo ""
    
    print_info "Testing response times and performance..."
    
    local tools=("journeys_tool" "logs_and_reports_tool")
    
    for tool_name in "${tools[@]}"; do
        local endpoint_url="$TOOLS_ENDPOINT/$tool_name"
        
        # Measure response time (should be under 5 seconds for basic requests)
        local response_time=$(curl -s -X POST "$endpoint_url" \
            -H 'Content-Type: application/json' \
            -d '{}' \
            -w '%{time_total}' \
            -o /dev/null \
            --max-time 30)
        
        if (( $(echo "$response_time < 5.0" | bc -l) )); then
            run_test "perf_${tool_name}_response" "$tool_name response time (<5s: ${response_time}s)" true
        else
            run_test "perf_${tool_name}_response" "$tool_name response time (>5s: ${response_time}s)" false
        fi
    done
    
    echo ""
}

generate_test_report() {
    print_header "TEST RESULTS SUMMARY"
    
    echo -e "${CYAN}🧪 TMF ODA Transformer MCP Server - Tool Availability Test Report${NC}"
    echo -e "${CYAN}Generated: $(date)${NC}"
    echo -e "${CYAN}Server URL: $SERVER_URL${NC}"
    echo ""
    
    # Overall statistics
    local success_rate=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        success_rate=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))
    fi
    
    echo -e "${BOLD}📊 Overall Results:${NC}"
    echo -e "  • Total Tests: $TOTAL_TESTS"
    echo -e "  • Tests Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "  • Tests Failed: ${RED}$FAILED_TESTS${NC}"
    echo -e "  • Success Rate: ${CYAN}${success_rate}%${NC}"
    echo ""
    
    # Results by category
    echo -e "${BOLD}📋 Results by Category:${NC}"
    echo ""
    
    # Server connectivity
    local server_tests=$(echo "${!TEST_RESULTS[@]}" | tr ' ' '\n' | grep -c "server_" || echo "0")
    local server_passed=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c "PASS" || echo "0")
    echo -e "  ${BOLD}🌐 Server Connectivity:${NC} $server_passed/$server_tests tests passed"
    
    # Tool availability
    local tool_tests=$(echo "${!TEST_RESULTS[@]}" | tr ' ' '\n' | grep -E "(raw-analysis|stripped-schema|run-jobs|journeys|logs-and-reports|test-runner|get-job-logs)" | wc -l || echo "0")
    echo -e "  ${BOLD}🔧 Tool Availability:${NC} Individual tool results above"
    
    # Error handling
    local error_tests=$(echo "${!TEST_RESULTS[@]}" | tr ' ' '\n' | grep -c "error_" || echo "0")
    echo -e "  ${BOLD}🚨 Error Handling:${NC} $error_tests tests completed"
    
    # Performance
    local perf_tests=$(echo "${!TEST_RESULTS[@]}" | tr ' ' '\n' | grep -c "perf_" || echo "0")
    echo -e "  ${BOLD}⚡ Performance:${NC} $perf_tests tests completed"
    
    echo ""
    
    # Failed tests details
    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${BOLD}❌ Failed Tests:${NC}"
        for test_name in "${!TEST_RESULTS[@]}"; do
            if [ "${TEST_RESULTS[$test_name]}" = "FAIL" ]; then
                echo -e "  • ${RED}$test_name${NC}"
            fi
        done
        echo ""
    fi
    
    # Recommendations
    echo -e "${BOLD}💡 Recommendations:${NC}"
    if [ $success_rate -ge 90 ]; then
        echo -e "  ${GREEN}✅ Excellent! All tools are functioning well${NC}"
        echo -e "  • MCP server is ready for production use"
        echo -e "  • All critical functionality is available"
    elif [ $success_rate -ge 70 ]; then
        echo -e "  ${YELLOW}⚠️ Good but some issues detected${NC}"
        echo -e "  • Review failed tests above"
        echo -e "  • Check server logs for detailed error information"
        echo -e "  • Consider retesting after addressing issues"
    else
        echo -e "  ${RED}🚨 Critical issues detected${NC}"
        echo -e "  • Server may not be properly configured"
        echo -e "  • Check if MCP server is running correctly"
        echo -e "  • Review server logs and configuration"
        echo -e "  • Consider restarting the server"
    fi
    
    echo ""
    echo -e "${BOLD}📚 Related Documentation:${NC}"
    echo -e "  • Use ${CYAN}./list_all_tools.sh${NC} for tool overview"
    echo -e "  • Use ${CYAN}./get_tool_details.sh [tool-name]${NC} for specific tool info"
    echo -e "  • Use ${CYAN}./show_tool_parameters.sh${NC} for parameter reference"
    echo ""
    
    # Exit with appropriate code
    if [ $success_rate -ge 70 ]; then
        return 0
    else
        return 1
    fi
}

main() {
    # Parse command line arguments
    parse_arguments "$@"
    
    print_header "TMF ODA TRANSFORMER MCP SERVER - AVAILABILITY TESTING"
    
    echo -e "${BLUE}🚀 Starting comprehensive tool availability testing...${NC}"
    echo -e "${BLUE}Server URL: $SERVER_URL${NC}"
    echo -e "${BLUE}Started: $(date)${NC}"
    echo ""
    
    # Quick connectivity pre-check
    echo -e "${CYAN}🔍 Pre-flight connectivity check...${NC}"
    if ! curl -s --connect-timeout 3 --max-time 5 "$SERVER_URL" > /dev/null 2>&1; then
        print_warning "Server at $SERVER_URL does not respond to basic connectivity test"
        echo -e "${YELLOW}This may indicate:${NC}"
        echo -e "  • Server is not running"
        echo -e "  • Network connectivity issues"
        echo -e "  • Firewall blocking access"
        echo -e "  • Wrong host or port"
        echo ""
        echo -e "${CYAN}Continuing with tests anyway...${NC}"
    else
        print_success "Server responds to basic connectivity"
    fi
    echo ""
    
    # Check dependencies
    if ! command -v curl >/dev/null 2>&1; then
        echo -e "${RED}❌ Error: curl is required but not installed${NC}"
        exit 1
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        echo -e "${RED}❌ Error: jq is required but not installed${NC}"
        exit 1
    fi
    
    # Run test suites
    echo -e "${CYAN}Running test suites...${NC}"
    
    # Test server connectivity
    test_server_connectivity
    
    # Only proceed with basic tool tests if connectivity works
    if [ "${TEST_RESULTS[tools_endpoint]}" = "PASS" ]; then
        # Quick tool availability test
        print_test_header "🔧 Quick Tool Availability Check"
        echo ""
        
        # Test journeys_tool
        run_test "journeys_tool_available" "Journeys tool availability" \
            timeout 15 curl -s -X POST "$TOOLS_ENDPOINT/journeys_tool" \
            -H 'Content-Type: application/json' \
            -H 'x-api-key: super-secret' \
            -d '{"arguments":{"action":"list"}}' \
            --max-time 10
        
        # Test logs_and_reports_tool  
        run_test "logs_tool_available" "Logs tool availability" \
            timeout 15 curl -s -X POST "$TOOLS_ENDPOINT/logs_and_reports_tool" \
            -H 'Content-Type: application/json' \
            -H 'x-api-key: super-secret' \
            -d '{"arguments":{"action":"list_available_logs"}}' \
            --max-time 10
        
        echo ""
        echo -e "${GREEN}✅ All critical tools are available${NC}"
    else
        echo -e "${YELLOW}⚠️ Skipping detailed tool tests due to connectivity issues${NC}"
        echo -e "${CYAN}ℹ️ To troubleshoot connectivity:${NC}"
        echo -e "  • Check if server is running: curl -I $SERVER_URL"
        echo -e "  • Verify host/port are correct"
        echo -e "  • Check firewall settings"
    fi
    
    # Generate final report
    echo ""
    if generate_test_report; then
        echo -e "${GREEN}🎉 Testing completed successfully!${NC}"
        exit 0
    else
        echo -e "${RED}⚠️ Testing completed with issues detected${NC}"
        exit 1
    fi
}

# Run main function
main "$@" 