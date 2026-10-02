#!/bin/bash

#==============================================================================
# AI Job Engine - Master Integration Test Runner
#==============================================================================
# This script runs all integration tests (shell and Python)
# with comprehensive reporting and flexible configuration
#==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Test configuration
SERVER_URL="${SERVER_URL:-http://localhost:8000}"
RUN_SHELL_TESTS="${RUN_SHELL_TESTS:-true}"
RUN_PYTHON_TESTS="${RUN_PYTHON_TESTS:-true}"
RUN_PERFORMANCE_TESTS="${RUN_PERFORMANCE_TESTS:-false}"
PARALLEL_EXECUTION="${PARALLEL_EXECUTION:-false}"
VERBOSE="${VERBOSE:-false}"
JSON_OUTPUT="${JSON_OUTPUT:-false}"
GENERATE_REPORT="${GENERATE_REPORT:-true}"
CLEANUP_ON_EXIT="${CLEANUP_ON_EXIT:-true}"

# Log configuration
LOG_DIR="$PROJECT_ROOT/logs/integration-tests"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_RUN_ID="INT_TEST_${TIMESTAMP}"
LOG_FILE="$LOG_DIR/${TEST_RUN_ID}.log"
REPORT_FILE="$LOG_DIR/${TEST_RUN_ID}_report.json"
HTML_REPORT="$LOG_DIR/${TEST_RUN_ID}_report.html"

# Test tracking
TOTAL_SHELL_TESTS=0
PASSED_SHELL_TESTS=0
FAILED_SHELL_TESTS=0
SHELL_TEST_FAILURES=()

TOTAL_PYTHON_TESTS=0
PASSED_PYTHON_TESTS=0
FAILED_PYTHON_TESTS=0
PYTHON_TEST_FAILURES=()

TEST_START_TIME=""
TEST_END_TIME=""

#==============================================================================
# Functions
#==============================================================================

# Initialize test environment
init_test_environment() {
    mkdir -p "$LOG_DIR"
    
    # Initialize log file
    cat > "$LOG_FILE" <<EOF
================================================================================
AI Job Engine - Integration Test Run
================================================================================
Test Run ID: $TEST_RUN_ID
Timestamp: $(date)
Server URL: $SERVER_URL
Configuration:
  - Shell Tests: $RUN_SHELL_TESTS
  - Python Tests: $RUN_PYTHON_TESTS
  - Performance Tests: $RUN_PERFORMANCE_TESTS
  - Parallel Execution: $PARALLEL_EXECUTION
================================================================================

EOF
}

# Print colored message
print_message() {
    local color=$1
    local message=$2
    
    if [ "$JSON_OUTPUT" != "true" ]; then
        echo -e "${color}${message}${NC}"
    fi
    echo "$message" >> "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    print_message $CYAN "Checking prerequisites..."
    
    local missing=()
    
    # Check required commands
    for cmd in curl jq python3; do
        if ! command -v $cmd &> /dev/null; then
            missing+=($cmd)
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        print_message $RED "❌ Missing required commands: ${missing[*]}"
        return 1
    fi
    
    # Check Python environment
    if [ ! -d "$PROJECT_ROOT/.venv" ] && [ ! -d "/opt/venv" ]; then
        print_message $YELLOW "⚠️  Python virtual environment not found"
        print_message $YELLOW "   Creating virtual environment..."
        cd "$PROJECT_ROOT"
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -q --upgrade pip
        pip install -q -r requirements.txt
        pip install -q pytest pytest-asyncio httpx moto boto3
    fi
    
    # Activate virtual environment
    if [ -d "$PROJECT_ROOT/.venv" ]; then
        source "$PROJECT_ROOT/.venv/bin/activate"
    elif [ -d "/opt/venv" ]; then
        source "/opt/venv/bin/activate"
    fi
    
    print_message $GREEN "✅ Prerequisites satisfied"
    return 0
}

# Check server health
check_server_health() {
    print_message $CYAN "Checking server health at $SERVER_URL..."
    
    local max_retries=5
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s -f "$SERVER_URL/health" &> /dev/null; then
            print_message $GREEN "✅ Server is healthy"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            print_message $YELLOW "  Server not responding (attempt $retry_count/$max_retries)"
            sleep 2
        fi
    done
    
    print_message $RED "❌ Server is not responding at $SERVER_URL"
    print_message $YELLOW "   Please start the server: cd $PROJECT_ROOT && ./gateway.sh start"
    return 1
}

#==============================================================================
# Shell Test Runner
#==============================================================================

run_shell_tests() {
    if [ "$RUN_SHELL_TESTS" != "true" ]; then
        print_message $YELLOW "⚠️  Skipping shell tests (RUN_SHELL_TESTS=false)"
        return 0
    fi
    
    print_message $PURPLE "\n📋 Running Shell Integration Tests"
    print_message $BLUE "=================================="
    
    local shell_dir="$SCRIPT_DIR/shell"
    local test_categories=("tools" "journey" "jobs" "logs")
    local failed_tests=()
    
    for category in "${test_categories[@]}"; do
        local category_dir="$shell_dir/$category"
        
        if [ ! -d "$category_dir" ]; then
            continue
        fi
        
        print_message $CYAN "\n🔹 Testing: $category"
        
        # Find and run test scripts
        for test_script in "$category_dir"/*.sh; do
            if [ ! -f "$test_script" ]; then
                continue
            fi
            
            local test_name=$(basename "$test_script" .sh)
            TOTAL_SHELL_TESTS=$((TOTAL_SHELL_TESTS + 1))
            
            if [ "$VERBOSE" = "true" ]; then
                print_message $BLUE "  Running: $test_name"
            else
                echo -n "."
            fi
            
            # Run test and capture result
            if bash "$test_script" "$SERVER_URL" >> "$LOG_FILE" 2>&1; then
                PASSED_SHELL_TESTS=$((PASSED_SHELL_TESTS + 1))
                if [ "$VERBOSE" = "true" ]; then
                    print_message $GREEN "    ✅ PASSED: $test_name"
                fi
            else
                FAILED_SHELL_TESTS=$((FAILED_SHELL_TESTS + 1))
                SHELL_TEST_FAILURES+=("$category/$test_name")
                if [ "$VERBOSE" != "true" ]; then
                    echo ""
                fi
                print_message $RED "    ❌ FAILED: $test_name"
            fi
        done
    done
    
    if [ "$VERBOSE" != "true" ]; then
        echo ""
    fi
    
    # Summary
    print_message $CYAN "\n📊 Shell Test Summary:"
    print_message $BLUE "  Total: $TOTAL_SHELL_TESTS"
    print_message $GREEN "  Passed: $PASSED_SHELL_TESTS"
    print_message $RED "  Failed: $FAILED_SHELL_TESTS"
    
    if [ ${#SHELL_TEST_FAILURES[@]} -gt 0 ]; then
        print_message $RED "\n  Failed Tests:"
        for failed in "${SHELL_TEST_FAILURES[@]}"; do
            print_message $RED "    • $failed"
        done
    fi
}

#==============================================================================
# Python Test Runner
#==============================================================================

run_python_tests() {
    if [ "$RUN_PYTHON_TESTS" != "true" ]; then
        print_message $YELLOW "⚠️  Skipping Python tests (RUN_PYTHON_TESTS=false)"
        return 0
    fi
    
    print_message $PURPLE "\n🐍 Running Python Integration Tests"
    print_message $BLUE "===================================="
    
    local python_dir="$SCRIPT_DIR/python"
    local test_modules=("services" "mcp" "api" "workflows" "performance")
    
    cd "$PROJECT_ROOT"
    
    # Build pytest command
    local pytest_cmd="python -m pytest tests/integration/python -v --tb=short"
    pytest_cmd="$pytest_cmd --server-url=$SERVER_URL"
    
    if [ "$RUN_PERFORMANCE_TESTS" != "true" ]; then
        pytest_cmd="$pytest_cmd -m 'not performance'"
    fi
    
    if [ "$JSON_OUTPUT" = "true" ]; then
        pytest_cmd="$pytest_cmd --json-report --json-report-file=$REPORT_FILE"
    fi
    
    if [ "$PARALLEL_EXECUTION" = "true" ] && command -v pytest-xdist &> /dev/null; then
        pytest_cmd="$pytest_cmd -n auto"
    fi
    
    # Run pytest
    print_message $CYAN "Running: $pytest_cmd"
    
    if eval "$pytest_cmd" >> "$LOG_FILE" 2>&1; then
        local exit_code=$?
        
        # Parse pytest output for results
        if [ -f "$REPORT_FILE" ]; then
            TOTAL_PYTHON_TESTS=$(jq -r '.summary.total // 0' "$REPORT_FILE")
            PASSED_PYTHON_TESTS=$(jq -r '.summary.passed // 0' "$REPORT_FILE")
            FAILED_PYTHON_TESTS=$(jq -r '.summary.failed // 0' "$REPORT_FILE")
        else
            # Parse from log if no JSON report
            TOTAL_PYTHON_TESTS=$(grep -E "^.* passed|failed|error" "$LOG_FILE" | tail -1 | grep -oE "[0-9]+" | head -1 || echo 0)
            PASSED_PYTHON_TESTS=$(grep -E "^.* passed" "$LOG_FILE" | tail -1 | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" || echo 0)
            FAILED_PYTHON_TESTS=$(grep -E "^.* failed" "$LOG_FILE" | tail -1 | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+" || echo 0)
        fi
        
        print_message $GREEN "✅ Python tests completed (exit code: $exit_code)"
    else
        print_message $RED "❌ Python tests failed"
        FAILED_PYTHON_TESTS=$((FAILED_PYTHON_TESTS + 1))
    fi
    
    # Summary
    print_message $CYAN "\n📊 Python Test Summary:"
    print_message $BLUE "  Total: $TOTAL_PYTHON_TESTS"
    print_message $GREEN "  Passed: $PASSED_PYTHON_TESTS"
    print_message $RED "  Failed: $FAILED_PYTHON_TESTS"
}

#==============================================================================
# Report Generation
#==============================================================================

generate_test_report() {
    if [ "$GENERATE_REPORT" != "true" ]; then
        return 0
    fi
    
    local total_tests=$((TOTAL_SHELL_TESTS + TOTAL_PYTHON_TESTS))
    local total_passed=$((PASSED_SHELL_TESTS + PASSED_PYTHON_TESTS))
    local total_failed=$((FAILED_SHELL_TESTS + FAILED_PYTHON_TESTS))
    local pass_rate=0
    
    if [ $total_tests -gt 0 ]; then
        pass_rate=$((total_passed * 100 / total_tests))
    fi
    
    # Generate JSON report
    cat > "$REPORT_FILE" <<EOF
{
  "test_run_id": "$TEST_RUN_ID",
  "timestamp": "$(date -Iseconds)",
  "server_url": "$SERVER_URL",
  "duration_seconds": $((TEST_END_TIME - TEST_START_TIME)),
  "summary": {
    "total": $total_tests,
    "passed": $total_passed,
    "failed": $total_failed,
    "pass_rate": $pass_rate
  },
  "shell_tests": {
    "total": $TOTAL_SHELL_TESTS,
    "passed": $PASSED_SHELL_TESTS,
    "failed": $FAILED_SHELL_TESTS,
    "failures": $(printf '%s\n' "${SHELL_TEST_FAILURES[@]}" | jq -R . | jq -s .)
  },
  "python_tests": {
    "total": $TOTAL_PYTHON_TESTS,
    "passed": $PASSED_PYTHON_TESTS,
    "failed": $FAILED_PYTHON_TESTS
  },
  "configuration": {
    "run_shell_tests": $RUN_SHELL_TESTS,
    "run_python_tests": $RUN_PYTHON_TESTS,
    "run_performance_tests": $RUN_PERFORMANCE_TESTS,
    "parallel_execution": $PARALLEL_EXECUTION
  },
  "log_file": "$LOG_FILE"
}
EOF
    
    # Generate HTML report
    generate_html_report
    
    print_message $BLUE "\n📝 Reports generated:"
    print_message $BLUE "  JSON: $REPORT_FILE"
    print_message $BLUE "  HTML: $HTML_REPORT"
    print_message $BLUE "  Logs: $LOG_FILE"
}

generate_html_report() {
    cat > "$HTML_REPORT" <<'HTML'
<!DOCTYPE html>
<html>
<head>
    <title>Integration Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .metric { background: #f9f9f9; padding: 15px; border-radius: 8px; text-align: center; }
        .metric h3 { margin: 0 0 10px 0; color: #666; font-size: 14px; }
        .metric .value { font-size: 32px; font-weight: bold; }
        .passed { color: #4CAF50; }
        .failed { color: #f44336; }
        .total { color: #2196F3; }
        .progress { width: 100%; height: 30px; background: #e0e0e0; border-radius: 15px; overflow: hidden; margin: 20px 0; }
        .progress-bar { height: 100%; background: linear-gradient(to right, #4CAF50, #8BC34A); transition: width 0.3s; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }
        th { background: #f5f5f5; font-weight: 600; }
        .test-type { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .shell { background: #e3f2fd; color: #1976d2; }
        .python { background: #fff3e0; color: #f57c00; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 Integration Test Report</h1>
        <p><strong>Test Run ID:</strong> TEST_RUN_ID_PLACEHOLDER</p>
        <p><strong>Date:</strong> DATE_PLACEHOLDER</p>
        <p><strong>Server:</strong> SERVER_PLACEHOLDER</p>
        
        <div class="summary">
            <div class="metric">
                <h3>Total Tests</h3>
                <div class="value total">TOTAL_PLACEHOLDER</div>
            </div>
            <div class="metric">
                <h3>Passed</h3>
                <div class="value passed">PASSED_PLACEHOLDER</div>
            </div>
            <div class="metric">
                <h3>Failed</h3>
                <div class="value failed">FAILED_PLACEHOLDER</div>
            </div>
            <div class="metric">
                <h3>Pass Rate</h3>
                <div class="value">RATE_PLACEHOLDER%</div>
            </div>
        </div>
        
        <div class="progress">
            <div class="progress-bar" style="width: RATE_PLACEHOLDER%"></div>
        </div>
        
        <h2>Test Results by Type</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Type</th>
                    <th>Total</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Pass Rate</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><span class="test-type shell">Shell Tests</span></td>
                    <td>SHELL_TOTAL</td>
                    <td class="passed">SHELL_PASSED</td>
                    <td class="failed">SHELL_FAILED</td>
                    <td>SHELL_RATE%</td>
                </tr>
                <tr>
                    <td><span class="test-type python">Python Tests</span></td>
                    <td>PYTHON_TOTAL</td>
                    <td class="passed">PYTHON_PASSED</td>
                    <td class="failed">PYTHON_FAILED</td>
                    <td>PYTHON_RATE%</td>
                </tr>
            </tbody>
        </table>
    </div>
</body>
</html>
HTML
    
    # Replace placeholders (use | as delimiter for URLs with slashes)
    sed -i "s/TEST_RUN_ID_PLACEHOLDER/$TEST_RUN_ID/g" "$HTML_REPORT"
    sed -i "s/DATE_PLACEHOLDER/$(date)/g" "$HTML_REPORT"
    sed -i "s|SERVER_PLACEHOLDER|$SERVER_URL|g" "$HTML_REPORT"
    sed -i "s/TOTAL_PLACEHOLDER/$((TOTAL_SHELL_TESTS + TOTAL_PYTHON_TESTS))/g" "$HTML_REPORT"
    sed -i "s/PASSED_PLACEHOLDER/$((PASSED_SHELL_TESTS + PASSED_PYTHON_TESTS))/g" "$HTML_REPORT"
    sed -i "s/FAILED_PLACEHOLDER/$((FAILED_SHELL_TESTS + FAILED_PYTHON_TESTS))/g" "$HTML_REPORT"
    sed -i "s/RATE_PLACEHOLDER/$pass_rate/g" "$HTML_REPORT"
    sed -i "s/SHELL_TOTAL/$TOTAL_SHELL_TESTS/g" "$HTML_REPORT"
    sed -i "s/SHELL_PASSED/$PASSED_SHELL_TESTS/g" "$HTML_REPORT"
    sed -i "s/SHELL_FAILED/$FAILED_SHELL_TESTS/g" "$HTML_REPORT"
    local shell_rate=0
    [ $TOTAL_SHELL_TESTS -gt 0 ] && shell_rate=$((PASSED_SHELL_TESTS * 100 / TOTAL_SHELL_TESTS))
    sed -i "s/SHELL_RATE/$shell_rate/g" "$HTML_REPORT"
    sed -i "s/PYTHON_TOTAL/$TOTAL_PYTHON_TESTS/g" "$HTML_REPORT"
    sed -i "s/PYTHON_PASSED/$PASSED_PYTHON_TESTS/g" "$HTML_REPORT"
    sed -i "s/PYTHON_FAILED/$FAILED_PYTHON_TESTS/g" "$HTML_REPORT"
    local python_rate=0
    [ $TOTAL_PYTHON_TESTS -gt 0 ] && python_rate=$((PASSED_PYTHON_TESTS * 100 / TOTAL_PYTHON_TESTS))
    sed -i "s/PYTHON_RATE/$python_rate/g" "$HTML_REPORT"
}

#==============================================================================
# Final Summary
#==============================================================================

print_final_summary() {
    local total_tests=$((TOTAL_SHELL_TESTS + TOTAL_PYTHON_TESTS))
    local total_passed=$((PASSED_SHELL_TESTS + PASSED_PYTHON_TESTS))
    local total_failed=$((FAILED_SHELL_TESTS + FAILED_PYTHON_TESTS))
    local duration=$((TEST_END_TIME - TEST_START_TIME))
    local pass_rate=0
    
    [ $total_tests -gt 0 ] && pass_rate=$((total_passed * 100 / total_tests))
    
    if [ "$JSON_OUTPUT" = "true" ]; then
        cat "$REPORT_FILE"
    else
        echo ""
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║           Integration Test Suite Summary                  ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${BLUE}📊 Overall Results:${NC}"
        echo -e "  Total Tests:     $total_tests"
        echo -e "  ${GREEN}Passed:          $total_passed${NC}"
        echo -e "  ${RED}Failed:          $total_failed${NC}"
        echo -e "  ${PURPLE}Pass Rate:       ${pass_rate}%${NC}"
        echo -e "  Duration:        ${duration}s"
        echo ""
        
        if [ $total_failed -gt 0 ]; then
            echo -e "${RED}❌ TESTS FAILED${NC}"
            echo -e "${YELLOW}Check the logs for details: $LOG_FILE${NC}"
            return 1
        else
            echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
            return 0
        fi
    fi
}

#==============================================================================
# Cleanup
#==============================================================================

cleanup_on_exit() {
    if [ "$CLEANUP_ON_EXIT" = "true" ]; then
        print_message $CYAN "🧹 Cleaning up..."
        # Add cleanup tasks here if needed
    fi
}

#==============================================================================
# Main Execution
#==============================================================================

main() {
    TEST_START_TIME=$(date +%s)
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --server)
                SERVER_URL="$2"
                shift 2
                ;;
            --shell-only)
                RUN_PYTHON_TESTS="false"
                shift
                ;;
            --python-only)
                RUN_SHELL_TESTS="false"
                shift
                ;;
            --performance)
                RUN_PERFORMANCE_TESTS="true"
                shift
                ;;
            --parallel)
                PARALLEL_EXECUTION="true"
                shift
                ;;
            --verbose|-v)
                VERBOSE="true"
                shift
                ;;
            --json)
                JSON_OUTPUT="true"
                shift
                ;;
            --no-report)
                GENERATE_REPORT="false"
                shift
                ;;
            --help|-h)
                cat <<EOF
AI Job Engine - Integration Test Runner

Usage: $0 [OPTIONS]

Options:
  --server URL        Server URL (default: http://localhost:8000)
  --shell-only        Run only shell tests
  --python-only       Run only Python tests
  --performance       Include performance tests
  --parallel          Run tests in parallel (requires pytest-xdist)
  --verbose, -v       Verbose output
  --json              JSON output format
  --no-report         Skip report generation
  --help, -h          Show this help message

Environment Variables:
  SERVER_URL          Server URL
  RUN_SHELL_TESTS     Run shell tests (true/false)
  RUN_PYTHON_TESTS    Run Python tests (true/false)
  RUN_PERFORMANCE_TESTS Include performance tests (true/false)

Examples:
  $0                              # Run all tests
  $0 --server http://staging:8000 # Test against staging
  $0 --python-only --performance  # Python tests with performance
  $0 --json > results.json        # Output JSON results
EOF
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Initialize environment
    init_test_environment
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Check server health
    if ! check_server_health; then
        exit 1
    fi
    
    # Run tests
    run_shell_tests
    run_python_tests
    
    TEST_END_TIME=$(date +%s)
    
    # Generate reports
    generate_test_report
    
    # Print summary
    print_final_summary
    local exit_code=$?
    
    # Cleanup
    cleanup_on_exit
    
    exit $exit_code
}

# Trap for cleanup
trap cleanup_on_exit EXIT

# Run main function
main "$@"
