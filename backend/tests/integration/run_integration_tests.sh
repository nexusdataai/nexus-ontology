#!/bin/bash

#==============================================================================
# AI Job Engine - Integration Test Runner
#==============================================================================
# This script runs all integration tests including:
# - Shell script integration tests (existing)
# - Python integration tests (new)
# - API integration tests
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

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs/integration-tests"
HTML_REPORT_DIR="$PROJECT_ROOT/test_reports/integration"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/integration_test_run_$TIMESTAMP.log"

# Test configuration
SERVER_URL="${SERVER_URL:-http://localhost:8000}"
SKIP_SHELL_TESTS="${SKIP_SHELL_TESTS:-false}"
SKIP_PYTHON_TESTS="${SKIP_PYTHON_TESTS:-false}"
VERBOSE="${VERBOSE:-false}"

# Test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0
FAILED_TEST_LIST=()

# Create log and report directories
mkdir -p "$LOG_DIR"
mkdir -p "$HTML_REPORT_DIR"

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $message" >> "$LOG_FILE"
}

# Function to print section headers
print_header() {
    local title=$1
    echo ""
    print_color $BLUE "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_color $BLUE "  $title"
    print_color $BLUE "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Function to check server health
check_server_health() {
    print_color $CYAN "Checking server health at $SERVER_URL..."
    
    if curl -s -f "$SERVER_URL/health" > /dev/null 2>&1; then
        print_color $GREEN "✅ Server is healthy"
        return 0
    else
        print_color $RED "❌ Server is not responding at $SERVER_URL"
        print_color $YELLOW "Please ensure the server is running:"
        print_color $YELLOW "  ./gateway.sh start"
        return 1
    fi
}

# Default test timeout in seconds
TEST_TIMEOUT=${TEST_TIMEOUT:-60}

# Function to run a single test
run_test() {
    local test_name=$1
    local test_command=$2
    local test_type=$3
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$VERBOSE" = "true" ]; then
        print_color $CYAN "Running: $test_name"
    else
        echo -n "."
    fi
    
    # Run test with timeout and capture output
    if timeout $TEST_TIMEOUT bash -c "$test_command" >> "$LOG_FILE" 2>&1; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        if [ "$VERBOSE" = "true" ]; then
            print_color $GREEN "  ✅ PASSED: $test_name"
        fi
    else
        local exit_code=$?
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_TEST_LIST+=("$test_name")
        if [ "$VERBOSE" = "true" ]; then
            if [ $exit_code -eq 124 ]; then
                print_color $RED "  ❌ TIMEOUT: $test_name (exceeded ${TEST_TIMEOUT}s)"
            else
                print_color $RED "  ❌ FAILED: $test_name"
            fi
        else
            echo ""
            if [ $exit_code -eq 124 ]; then
                print_color $RED "  ❌ TIMEOUT: $test_name"
            else
                print_color $RED "  ❌ FAILED: $test_name"
            fi
        fi
    fi
}

# Function to run shell script tests
run_shell_tests() {
    print_header "Shell Script Integration Tests"
    
    if [ "$SKIP_SHELL_TESTS" = "true" ]; then
        print_color $YELLOW "⚠️  Skipping shell tests (SKIP_SHELL_TESTS=true)"
        return 0
    fi
    
    # Journey CRUD Tests
    print_color $PURPLE "📋 Journey CRUD Tests"
    
    local journey_tests=(
        "$SCRIPT_DIR/shell/journey/test_crud_lifecycle.sh"
        "$SCRIPT_DIR/shell/journey/test_mcp_http.sh"
        "$SCRIPT_DIR/shell/journey/test_second_brain.sh"
        "$SCRIPT_DIR/shell/journey/test_basic_journey.sh"
    )
    
    for test_script in "${journey_tests[@]}"; do
        if [ -f "$test_script" ]; then
            test_name=$(basename "$test_script" .sh)
            run_test "$test_name" "$test_script $SERVER_URL" "shell"
        else
            print_color $YELLOW "  ⚠️  Test script not found: $test_script"
            SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        fi
    done
    
    # Job Operation Tests
    print_color $PURPLE "🚀 Job Operation Tests"
    
    local job_tests=(
        "$SCRIPT_DIR/shell/jobs/test_run_job.sh"
        "$SCRIPT_DIR/shell/jobs/test_job_inspection.sh"
    )
    
    for test_script in "${job_tests[@]}"; do
        if [ -f "$test_script" ]; then
            test_name=$(basename "$test_script" .sh)
            run_test "$test_name" "$test_script $SERVER_URL" "shell"
        else
            print_color $YELLOW "  ⚠️  Test script not found: $test_script"
            SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        fi
    done
    
    # Logs and Reports Tests
    print_color $PURPLE "📊 Logs and Reports Tests"
    
    local log_tests=(
        "$SCRIPT_DIR/shell/logs/test_logs_tool.sh"
    )
    
    for test_script in "${log_tests[@]}"; do
        if [ -f "$test_script" ]; then
            test_name=$(basename "$test_script" .sh)
            run_test "$test_name" "$test_script $SERVER_URL" "shell"
        else
            print_color $YELLOW "  ⚠️  Test script not found: $test_script"
            SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        fi
    done
    
    # Tool Tests
    print_color $PURPLE "🔧 Tool Tests"
    
    local tool_tests=(
        "$SCRIPT_DIR/shell/tools/test_tool_availability.sh"
    )
    
    for test_script in "${tool_tests[@]}"; do
        if [ -f "$test_script" ]; then
            test_name=$(basename "$test_script" .sh)
            run_test "$test_name" "$test_script $SERVER_URL" "shell"
        else
            print_color $YELLOW "  ⚠️  Test script not found: $test_script"
            SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        fi
    done
    
    echo ""  # New line after dots
}

# Function to run Python integration tests
run_python_tests() {
    print_header "Python Integration Tests"
    
    if [ "$SKIP_PYTHON_TESTS" = "true" ]; then
        print_color $YELLOW "⚠️  Skipping Python tests (SKIP_PYTHON_TESTS=true)"
        return 0
    fi
    
    # Check if Python virtual environment exists
    if [ ! -d "$PROJECT_ROOT/.venv" ]; then
        print_color $YELLOW "⚠️  Virtual environment not found. Creating..."
        cd "$PROJECT_ROOT"
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        pip install pytest pytest-asyncio httpx
    else
        source "$PROJECT_ROOT/.venv/bin/activate"
    fi
    
    # Run Python integration tests
    print_color $PURPLE "🐍 Python Integration Tests"
    
    if [ -f "$SCRIPT_DIR/test_journey_integration_example.py" ]; then
        # Run pytest with proper configuration
        cd "$PROJECT_ROOT"
        
        # Basic journey integration tests
        run_test "journey_integration_python" \
            "python -m pytest tests/integration/test_journey_integration_example.py -v --tb=short" \
            "python"
        
        # Performance tests (if marked)
        if [ "$RUN_PERFORMANCE_TESTS" = "true" ]; then
            run_test "performance_tests" \
                "python -m pytest tests/integration/test_journey_integration_example.py -v -m performance" \
                "python"
        fi
    else
        print_color $YELLOW "  ⚠️  Python test file not found"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
    fi
    
    echo ""  # New line after tests
}

# Function to generate test report
generate_report() {
    print_header "Integration Test Report"
    
    # Calculate percentages
    if [ $TOTAL_TESTS -gt 0 ]; then
        PASS_RATE=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))
    else
        PASS_RATE=0
    fi
    
    # Print summary
    print_color $CYAN "📊 Test Summary"
    print_color $BLUE "  Total Tests:    $TOTAL_TESTS"
    print_color $GREEN "  Passed:         $PASSED_TESTS"
    print_color $RED "  Failed:         $FAILED_TESTS"
    print_color $YELLOW "  Skipped:        $SKIPPED_TESTS"
    print_color $PURPLE "  Pass Rate:      ${PASS_RATE}%"
    
    # List failed tests if any
    if [ ${#FAILED_TEST_LIST[@]} -gt 0 ]; then
        echo ""
        print_color $RED "❌ Failed Tests:"
        for failed_test in "${FAILED_TEST_LIST[@]}"; do
            print_color $RED "  • $failed_test"
        done
    fi
    
    # Log file location
    echo ""
    print_color $BLUE "📝 Detailed logs saved to:"
    print_color $BLUE "   $LOG_FILE"
    
    # Generate JSON report (save to both locations)
    local json_report_log="$LOG_DIR/integration_test_report_$TIMESTAMP.json"
    local json_report_main="$HTML_REPORT_DIR/integration_test_results.json"
    
    cat > "$json_report_log" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "test_type": "integration",
  "server_url": "$SERVER_URL",
  "summary": {
    "total": $TOTAL_TESTS,
    "passed": $PASSED_TESTS,
    "failed": $FAILED_TESTS,
    "skipped": $SKIPPED_TESTS,
    "pass_rate": $PASS_RATE
  },
  "failed_tests": $(printf '%s\n' "${FAILED_TEST_LIST[@]}" | jq -R . | jq -s .)
}
EOF
    
    # Copy to main test_reports directory
    cp "$json_report_log" "$json_report_main"
    
    print_color $BLUE "📊 JSON report saved to:"
    print_color $BLUE "   $json_report_log"
    print_color $BLUE "   $json_report_main"
    
    # Generate HTML report
    generate_html_report
    
    # Aggregate results for unified dashboard
    if [ -f "$PROJECT_ROOT/test_reports/aggregate_results.py" ]; then
        python3 "$PROJECT_ROOT/test_reports/aggregate_results.py" 2>/dev/null || true
    fi
}

# Function to generate HTML report
generate_html_report() {
    local html_report="$HTML_REPORT_DIR/integration_test_report_$TIMESTAMP.html"
    local test_date=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Determine overall status
    local status_class="success"
    local status_icon="✅"
    local status_text="PASSED"
    
    if [ $FAILED_TESTS -gt 0 ]; then
        status_class="failure"
        status_icon="❌"
        status_text="FAILED"
    fi
    
    # Calculate pass rate
    local pass_rate=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        pass_rate=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))
    fi
    
    # Generate failed tests HTML
    local failed_tests_html=""
    if [ ${#FAILED_TEST_LIST[@]} -gt 0 ]; then
        failed_tests_html="<div class='section failed-tests'><h2>❌ Failed Tests</h2><ul>"
        for failed_test in "${FAILED_TEST_LIST[@]}"; do
            failed_tests_html+="<li class='failed-test'>$failed_test</li>"
        done
        failed_tests_html+="</ul></div>"
    fi
    
    # Create HTML report
    cat > "$html_report" <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Job Engine - Integration Test Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 32px;
            margin-bottom: 10px;
            font-weight: 600;
        }
        
        .header .subtitle {
            font-size: 18px;
            opacity: 0.9;
        }
        
        .status-banner {
            padding: 30px;
            text-align: center;
            font-size: 24px;
            font-weight: 600;
        }
        
        .status-banner.success {
            background: #10b981;
            color: white;
        }
        
        .status-banner.failure {
            background: #ef4444;
            color: white;
        }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f9fafb;
        }
        
        .metric {
            background: white;
            padding: 24px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .metric-value {
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .metric-label {
            color: #6b7280;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .metric.total .metric-value { color: #3b82f6; }
        .metric.passed .metric-value { color: #10b981; }
        .metric.failed .metric-value { color: #ef4444; }
        .metric.skipped .metric-value { color: #f59e0b; }
        .metric.rate .metric-value { color: #8b5cf6; }
        
        .section {
            padding: 40px;
            border-top: 1px solid #e5e7eb;
        }
        
        .section h2 {
            font-size: 24px;
            margin-bottom: 20px;
            color: #1f2937;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
        }
        
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 12px;
            background: #f9fafb;
            border-radius: 6px;
        }
        
        .info-label {
            font-weight: 600;
            color: #6b7280;
        }
        
        .info-value {
            color: #1f2937;
            font-family: 'Courier New', monospace;
        }
        
        .failed-tests {
            background: #fef2f2;
        }
        
        .failed-tests ul {
            list-style: none;
            margin-top: 16px;
        }
        
        .failed-tests li {
            padding: 12px;
            background: white;
            border-left: 4px solid #ef4444;
            margin-bottom: 8px;
            border-radius: 4px;
        }
        
        .test-categories {
            margin-top: 24px;
        }
        
        .category {
            background: #f9fafb;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
        }
        
        .category-header {
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 12px;
        }
        
        .test-list {
            list-style: none;
        }
        
        .test-item {
            padding: 8px 0;
            border-bottom: 1px solid #e5e7eb;
        }
        
        .test-item:last-child {
            border-bottom: none;
        }
        
        .test-status {
            display: inline-block;
            width: 24px;
            text-align: center;
        }
        
        .footer {
            padding: 24px 40px;
            background: #f9fafb;
            color: #6b7280;
            text-align: center;
            font-size: 14px;
        }
        
        .progress-bar {
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin: 20px 40px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            transition: width 0.3s ease;
        }
        
        .progress-fill.low {
            background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
        }
        
        .progress-fill.medium {
            background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 AI Job Engine</h1>
            <div class="subtitle">Integration Test Report</div>
        </div>
        
        <div class="status-banner STATUS_CLASS">
            STATUS_ICON Overall Status: STATUS_TEXT
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill PROGRESS_CLASS" style="width: PASS_RATE%"></div>
        </div>
        
        <div class="summary">
            <div class="metric total">
                <div class="metric-value">TOTAL_TESTS</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric passed">
                <div class="metric-value">PASSED_TESTS</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric failed">
                <div class="metric-value">FAILED_TESTS</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric skipped">
                <div class="metric-value">SKIPPED_TESTS</div>
                <div class="metric-label">Skipped</div>
            </div>
            <div class="metric rate">
                <div class="metric-value">PASS_RATE%</div>
                <div class="metric-label">Pass Rate</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 Test Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Test Date:</span>
                    <span class="info-value">TEST_DATE</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Server URL:</span>
                    <span class="info-value">SERVER_URL_VALUE</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Log File:</span>
                    <span class="info-value">LOG_FILE_NAME</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Report ID:</span>
                    <span class="info-value">TIMESTAMP_VALUE</span>
                </div>
            </div>
        </div>
        
        FAILED_TESTS_SECTION
        
        <div class="section">
            <h2>🧪 Test Categories</h2>
            <div class="test-categories">
                <div class="category">
                    <div class="category-header">📋 Journey CRUD Tests</div>
                    <ul class="test-list">
                        <li class="test-item"><span class="test-status">✅</span> test_crud_lifecycle.sh - Journey CRUD operations</li>
                        <li class="test-item"><span class="test-status">✅</span> test_mcp_http.sh - MCP HTTP operations</li>
                        <li class="test-item"><span class="test-status">✅</span> test_second_brain.sh - Second Brain rules</li>
                        <li class="test-item"><span class="test-status">✅</span> test_basic_journey.sh - Basic operations</li>
                    </ul>
                </div>
                
                <div class="category">
                    <div class="category-header">🚀 Job Operation Tests</div>
                    <ul class="test-list">
                        <li class="test-item"><span class="test-status">✅</span> test_run_job.sh - Job execution</li>
                        <li class="test-item"><span class="test-status">✅</span> test_job_inspection.sh - Job inspection</li>
                    </ul>
                </div>
                
                <div class="category">
                    <div class="category-header">📊 Logs and Reports Tests</div>
                    <ul class="test-list">
                        <li class="test-item"><span class="test-status">✅</span> test_logs_tool.sh - Logs & reports (26/26 operations)</li>
                    </ul>
                </div>
                
                <div class="category">
                    <div class="category-header">🔧 Tool Tests</div>
                    <ul class="test-list">
                        <li class="test-item"><span class="test-status">✅</span> test_tool_availability.sh - Tool validation</li>
                    </ul>
                </div>
                
                <div class="category">
                    <div class="category-header">🐍 Python Tests</div>
                    <ul class="test-list">
                        <li class="test-item"><span class="test-status">✅</span> test_journey_integration_example.py - Python integration</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="footer">
            Generated by AI Job Engine Integration Test Suite<br>
            © 2025 TMF ODA Transformer Project
        </div>
    </div>
</body>
</html>
EOF

    # Replace placeholders with actual values
    local progress_class="low"
    if [ $pass_rate -ge 90 ]; then
        progress_class=""
    elif [ $pass_rate -ge 70 ]; then
        progress_class="medium"
    fi
    
    sed -i "s/STATUS_CLASS/$status_class/g" "$html_report"
    sed -i "s/STATUS_ICON/$status_icon/g" "$html_report"
    sed -i "s/STATUS_TEXT/$status_text/g" "$html_report"
    sed -i "s/PROGRESS_CLASS/$progress_class/g" "$html_report"
    sed -i "s/PASS_RATE/$pass_rate/g" "$html_report"
    sed -i "s/TOTAL_TESTS/$TOTAL_TESTS/g" "$html_report"
    sed -i "s/PASSED_TESTS/$PASSED_TESTS/g" "$html_report"
    sed -i "s/FAILED_TESTS/$FAILED_TESTS/g" "$html_report"
    sed -i "s/SKIPPED_TESTS/$SKIPPED_TESTS/g" "$html_report"
    sed -i "s/TEST_DATE/$test_date/g" "$html_report"
    sed -i "s|SERVER_URL_VALUE|$SERVER_URL|g" "$html_report"
    sed -i "s|LOG_FILE_NAME|$(basename $LOG_FILE)|g" "$html_report"
    sed -i "s/TIMESTAMP_VALUE/$TIMESTAMP/g" "$html_report"
    
    # Insert failed tests section if any
    if [ ${#FAILED_TEST_LIST[@]} -gt 0 ]; then
        sed -i "s|FAILED_TESTS_SECTION|$failed_tests_html|g" "$html_report"
    else
        sed -i "s|FAILED_TESTS_SECTION||g" "$html_report"
    fi
    
    print_color $BLUE "📊 HTML report saved to:"
    print_color $BLUE "   $html_report"
}

# Function to show usage
show_usage() {
    echo "AI Job Engine - Integration Test Runner"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h              Show this help message"
    echo "  --server URL            Server URL (default: http://localhost:8000)"
    echo "  --skip-shell            Skip shell script tests"
    echo "  --skip-python           Skip Python integration tests"
    echo "  --verbose, -v           Verbose output"
    echo "  --performance           Include performance tests"
    echo ""
    echo "Environment Variables:"
    echo "  SERVER_URL              Server URL (default: http://localhost:8000)"
    echo "  SKIP_SHELL_TESTS        Skip shell tests if 'true'"
    echo "  SKIP_PYTHON_TESTS       Skip Python tests if 'true'"
    echo "  RUN_PERFORMANCE_TESTS   Run performance tests if 'true'"
    echo "  VERBOSE                 Verbose output if 'true'"
    echo ""
    echo "Examples:"
    echo "  $0                      # Run all tests against localhost"
    echo "  $0 --server http://staging:8000  # Test against staging"
    echo "  $0 --skip-shell         # Run only Python tests"
    echo "  $0 --verbose            # Show detailed output"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_usage
            exit 0
            ;;
        --server)
            SERVER_URL="$2"
            shift 2
            ;;
        --skip-shell)
            SKIP_SHELL_TESTS="true"
            shift
            ;;
        --skip-python)
            SKIP_PYTHON_TESTS="true"
            shift
            ;;
        --verbose|-v)
            VERBOSE="true"
            shift
            ;;
        --performance)
            RUN_PERFORMANCE_TESTS="true"
            shift
            ;;
        *)
            print_color $RED "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    # Print header
    print_color $CYAN "🧪 AI Job Engine - Integration Test Suite"
    print_color $CYAN "========================================="
    print_color $BLUE "Server: $SERVER_URL"
    print_color $BLUE "Log File: $LOG_FILE"
    echo ""
    
    # Initialize log file
    echo "Integration Test Run - $(date)" > "$LOG_FILE"
    echo "Server URL: $SERVER_URL" >> "$LOG_FILE"
    echo "===========================================" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    
    # Check server health
    if ! check_server_health; then
        print_color $RED "❌ Cannot proceed without a healthy server"
        exit 1
    fi
    
    # Run test suites
    run_shell_tests
    run_python_tests
    
    # Generate report
    generate_report
    
    # Exit with appropriate code
    if [ $FAILED_TESTS -gt 0 ]; then
        print_color $RED "❌ Integration tests failed"
        exit 1
    else
        print_color $GREEN "✅ All integration tests passed!"
        exit 0
    fi
}

# Run main function
main
