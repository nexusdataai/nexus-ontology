#!/bin/bash

#############################################
# AI Job Engine - Comprehensive Test Runner
# Runs unit, integration, and BDD tests
#############################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Test configuration
export SERVER_URL="${SERVER_URL:-http://localhost:8000}"
CURL_INSECURE="${CURL_INSECURE:-false}"
RUN_UNIT_TESTS="${RUN_UNIT_TESTS:-true}"
RUN_INTEGRATION_TESTS="${RUN_INTEGRATION_TESTS:-false}"
RUN_BDD_TESTS="${RUN_BDD_TESTS:-false}"
RUN_PERFORMANCE_TESTS="${RUN_PERFORMANCE_TESTS:-false}"

# S3 upload configuration
UPLOAD_TO_S3="${UPLOAD_TO_S3:-false}"
S3_BUCKET_NAME="${S3_BUCKET_NAME:-}"
S3_REGION="${S3_REGION:-us-east-1}"
S3_REPORTS_PREFIX="${S3_REPORTS_PREFIX:-test-reports}"
CLOUDFRONT_DOMAIN="${CLOUDFRONT_DOMAIN:-}"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  AI JOB ENGINE - COMPREHENSIVE TEST RUNNER${NC}"
echo -e "${BLUE}================================================${NC}"

# Function to print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "=== Quick Tests (< 1 minute) ==="
    echo "  smoke             Run smoke tests only - fast sanity check (default)"
    echo "  quick             Alias for smoke test"
    echo ""
    echo "=== Test Suites ==="
    echo "  all               Run complete test suite (unit + integration + BDD + full endurance)"
    echo "  all-quick         Run all tests with 1-minute endurance (recommended for quick validation)"
    echo "  full              Complete suite with AWS refresh and gateway restart"
    echo "  unit              Run all unit tests"
    echo "  integration       Run all integration tests (shell + Python)"
    echo "  bdd               Run all BDD tests"
    echo "  endurance         Run full endurance/stability tests"
    echo ""
    echo "=== Integration Test Types ==="
    echo "  integration-shell Run shell integration tests only"
    echo "  integration-python Run Python integration tests only"
    echo ""
    echo "=== Domain-specific Tests ==="
    echo "  journey           Run all journey tests (unit + integration + BDD)"
    echo "  journey-unit      Run journey unit tests only"
    echo "  journey-integration Run journey integration tests"
    echo "  journey-bdd       Run journey BDD tests only"
    echo "  capability        Run all capability tests"
    echo "  capability-unit   Run capability unit tests only"
    echo "  capability-bdd    Run capability BDD tests only"
    echo ""
    echo "=== Call Processing Tests ==="
    echo "  call-process      Run all call-process tests (unit + integration + BDD)"
    echo "  call-process-unit Run call-process unit tests only"
    echo "  call-process-integration Run call-process integration tests"
    echo "  call-process-bdd  Run call-process BDD tests only"
    echo "  call-process-endurance Run call-process endurance tests"
    echo ""
    echo "=== Special Options ==="
    echo "  coverage          Run with coverage report"
    echo "  performance       Include performance tests"
    echo "  aws-refresh       Refresh AWS credentials only"
    echo "  server-restart    Restart gateway server only"
    echo "  server-check      Check if server is running"
    echo "  consolidated-report Generate consolidated HTML report"
    echo "  upload-to-s3      Upload existing reports to S3"
    echo "  clean             Clean test artifacts"
    echo "  help              Show this help message"
    echo ""
    echo "=== Advanced Options ==="
    echo "  --server, -s URL  Set server URL for remote testing (default: http://localhost:8000)"
    echo "  --insecure, -k    Skip SSL certificate verification (for ALB/internal URLs)"
    echo "  --upload, -u      Automatically upload reports to CloudFront"
    echo "  Multiple types    Comma-separated: unit,integration,bdd"
    echo ""
    echo "=== Environment Variables ==="
    echo "  SERVER_URL        Server URL for integration tests (default: http://localhost:8000)"
    echo "  VERBOSE           Enable verbose output (true/false)"
    echo "  JSON_OUTPUT       Output results as JSON (true/false)"
    echo "  UPLOAD_TO_S3      Upload reports to S3 after generation (true/false)"
    echo "  S3_BUCKET_NAME    S3 bucket name for report uploads"
    echo "  S3_REGION         AWS region for S3 bucket (default: us-east-1)"
    echo "  CLOUDFRONT_DOMAIN CloudFront domain for private S3 buckets"
    echo ""
    echo "=== Examples ==="
    echo "  $0                    # Run smoke tests (default, < 1 min)"
    echo "  $0 all-quick          # All tests with 1-min endurance (recommended)"
    echo "  $0 smoke              # Run smoke tests explicitly"
    echo "  $0 unit               # Run all unit tests"
    echo "  $0 integration        # Run integration tests"
    echo "  $0 bdd                # Run BDD tests"
    echo "  $0 all                # Run complete test suite (long endurance)"
    echo "  $0 full               # Complete suite with AWS + gateway setup"
    echo "  $0 coverage           # Run with coverage report"
    echo ""
    echo "=== New: Multiple Tests with Upload ⭐ ==="
    echo "  $0 unit --upload                  # Run unit tests and upload to CloudFront"
    echo "  $0 integration --upload           # Run integration tests and upload"
    echo "  $0 unit,integration --upload      # Run both and upload ⭐"
    echo "  $0 unit,integration,bdd --upload  # Run all three and upload"
    echo "  $0 unit,integration -u            # Short form with -u flag"
    echo "  $0 aws-refresh        # Refresh AWS credentials"
    echo "  $0 server-restart     # Restart gateway server"
    echo "  $0 consolidated-report # Generate consolidated report"
    echo "  $0 upload-to-s3       # Upload reports to S3"
    echo ""
    echo "=== Remote Server Testing ==="
    echo "  $0 integration -s http://remote:8000      # Test against remote server"
    echo "  $0 bdd --server https://staging.example.com  # BDD tests on staging"
    echo "  $0 endurance -s http://192.168.1.100:8000    # Endurance test remote"
    echo "  $0 integration,bdd -s http://prod:8000 -u    # Multiple tests on remote + upload"
    echo "  $0 integration -s https://alb-url.amazonaws.com -k  # Skip SSL verification"
    echo ""
    echo "  NOTE: Unit tests CANNOT run against remote servers (they mock all dependencies)"
    echo "        Only integration, BDD, and endurance tests support remote testing."
    echo ""
    echo "  SERVER_URL=http://staging:8000 $0 integration  # Alternative: env variable"
    echo "  UPLOAD_TO_S3=true S3_BUCKET_NAME=my-reports $0 unit  # Run tests and upload to S3"
}

# Function to refresh AWS credentials
refresh_aws_credentials() {
    echo -e "${YELLOW}Refreshing AWS credentials...${NC}"
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        echo -e "${YELLOW}⚠ AWS CLI not found, skipping credential refresh${NC}"
        return 0
    fi
    
    # Check if credentials script exists
    if [ -f "$PROJECT_ROOT/scripts/refresh_aws_creds.sh" ]; then
        echo -e "${CYAN}Running AWS credential refresh script...${NC}"
        bash "$PROJECT_ROOT/scripts/refresh_aws_creds.sh"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ AWS credentials refreshed${NC}"
        else
            echo -e "${YELLOW}⚠ AWS credential refresh failed, continuing...${NC}"
        fi
    else
        # Try to refresh using AWS SSO or default profile
        if aws sts get-caller-identity &> /dev/null; then
            echo -e "${GREEN}✓ AWS credentials are valid${NC}"
        else
            echo -e "${YELLOW}⚠ AWS credentials may be expired${NC}"
            echo -e "${YELLOW}  Run: aws sso login${NC}"
        fi
    fi
    
    echo ""
}

# Function to restart gateway server
restart_gateway_server() {
    echo -e "${YELLOW}Restarting gateway server...${NC}"
    
    # Check if gateway script exists
    if [ ! -f "$PROJECT_ROOT/gateway.sh" ]; then
        echo -e "${YELLOW}⚠ Gateway script not found at $PROJECT_ROOT/gateway.sh${NC}"
        return 0
    fi
    
    # Stop existing gateway
    echo -e "${CYAN}Stopping existing gateway...${NC}"
    bash "$PROJECT_ROOT/gateway.sh" stop 2>/dev/null || true
    sleep 2
    
    # Start gateway
    echo -e "${CYAN}Starting gateway server...${NC}"
    bash "$PROJECT_ROOT/gateway.sh" start
    
    # Wait for server to be ready
    echo -e "${CYAN}Waiting for server to be ready...${NC}"
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$SERVER_URL/health" &> /dev/null; then
            echo -e "${GREEN}✓ Gateway server is ready at $SERVER_URL${NC}"
            echo ""
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    echo ""
    echo -e "${YELLOW}⚠ Gateway server did not respond after ${max_attempts}s${NC}"
    echo ""
    return 1
}

# Function to check environment
check_environment() {
    echo -e "${YELLOW}Checking environment...${NC}"
    
    # Check for virtual environment and use it if available
    if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
        export PYTHON="$PROJECT_ROOT/.venv/bin/python"
        export PIP="$PROJECT_ROOT/.venv/bin/pip"
        echo -e "${GREEN}✓ Using virtual environment (.venv)${NC}"
    elif [ -f "$PROJECT_ROOT/venv/bin/python" ]; then
        export PYTHON="$PROJECT_ROOT/venv/bin/python"
        export PIP="$PROJECT_ROOT/venv/bin/pip"
        echo -e "${GREEN}✓ Using virtual environment (venv)${NC}"
    elif [ -f "/opt/venv/bin/python" ]; then
        export PYTHON="/opt/venv/bin/python"
        export PIP="/opt/venv/bin/pip"
        echo -e "${GREEN}✓ Using virtual environment (/opt/venv)${NC}"
    else
        export PYTHON="python3"
        export PIP="pip3"
        echo -e "${YELLOW}⚠ No virtual environment found, using system Python${NC}"
    fi
    
    # Check Python
    if ! $PYTHON --version &> /dev/null; then
        echo -e "${RED}Error: Python not accessible${NC}"
        exit 1
    fi
    
    # Check pytest
    if ! $PYTHON -m pytest --version &> /dev/null 2>&1; then
        echo -e "${YELLOW}Warning: pytest not installed in environment${NC}"
        echo -e "${YELLOW}Installing test dependencies...${NC}"
        $PIP install -q pytest pytest-cov pytest-mock pytest-asyncio httpx moto boto3 pytest-html pytest-json-report
    fi
    
    # Check behave for BDD tests
    if [ "$RUN_BDD_TESTS" = "true" ] && ! $PYTHON -m behave --version &> /dev/null 2>&1; then
        echo -e "${YELLOW}Warning: behave not installed in environment${NC}"
        echo -e "${YELLOW}Installing: $PIP install behave${NC}"
        $PIP install -q behave
    fi
    
    echo -e "${GREEN}✓ Environment ready${NC}"
    echo ""
}

# Function to check server status
check_server() {
    echo -e "${CYAN}Checking server at $SERVER_URL...${NC}"
    
    # Build curl options
    local curl_opts="-s -f"
    if [ "$CURL_INSECURE" = "true" ]; then
        curl_opts="$curl_opts -k"
        echo -e "${YELLOW}(SSL verification disabled)${NC}"
    fi
    
    if curl $curl_opts "$SERVER_URL/health" &> /dev/null; then
        echo -e "${GREEN}✓ Server is running at $SERVER_URL${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Server is not responding at $SERVER_URL${NC}"
        echo -e "${YELLOW}  Start the server with: cd $PROJECT_ROOT && ./gateway.sh start${NC}"
        if [ "$CURL_INSECURE" != "true" ]; then
            echo -e "${YELLOW}  For SSL issues, try: $0 <test> -s $SERVER_URL -k${NC}"
        fi
        return 1
    fi
}

# Function to run unit tests for a specific domain
run_unit_tests() {
    local domain=$1
    local coverage=$2
    
    echo -e "${CYAN}Running $domain unit tests...${NC}"
    
    local test_path="$SCRIPT_DIR/unit/$domain"
    if [ ! -d "$test_path" ]; then
        echo -e "${YELLOW}No unit tests found for $domain${NC}"
        return 0
    fi
    
    if [ "$coverage" = "true" ]; then
        $PYTHON -m pytest "$test_path" -v --cov=src --cov-report=term-missing --cov-report=html
    else
        $PYTHON -m pytest "$test_path" -v
    fi
    
    return $?
}

# Function to run smoke tests (quick sanity check)
run_smoke_tests() {
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  SMOKE TESTS (Quick Sanity Check)${NC}"
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    
    # Create HTML report directory
    local html_report_dir="$PROJECT_ROOT/test_reports/unit"
    mkdir -p "$html_report_dir"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local json_report="$html_report_dir/smoke_test_results.json"
    
    # Run a limited set of fast tests (first 10 tests or tests marked as smoke)
    # Using --maxfail=5 to stop after 5 failures for speed
    # Using -k to filter for quick tests if available, otherwise limit collection
    echo -e "${CYAN}Running quick smoke tests (max 1 minute)...${NC}"
    
    # Try to run tests marked with @smoke or just limit to first few
    $PYTHON -m pytest "$SCRIPT_DIR/unit" -v \
        --maxfail=5 \
        --timeout=60 \
        -k "model or test_journey_model or test_create" \
        --json-report \
        --json-report-file="$json_report" 2>/dev/null || \
    $PYTHON -m pytest "$SCRIPT_DIR/unit" -v \
        --maxfail=5 \
        --co -q 2>&1 | head -10 | xargs $PYTHON -m pytest -v \
        --json-report \
        --json-report-file="$json_report" 2>/dev/null || \
    $PYTHON -m pytest "$SCRIPT_DIR/unit/journey/test_journey_model.py" -v \
        --maxfail=3 \
        --json-report \
        --json-report-file="$json_report"
    
    local result=$?
    
    if [ -f "$json_report" ]; then
        echo -e "${BLUE}📊 Smoke test results saved to: $json_report${NC}"
        
        # Generate quick summary
        if command -v jq &> /dev/null; then
            local total=$(jq -r '.summary.total // 0' "$json_report" 2>/dev/null || echo "0")
            local passed=$(jq -r '.summary.passed // 0' "$json_report" 2>/dev/null || echo "0")
            echo -e "${GREEN}✓ Smoke tests: $passed/$total passed${NC}"
        fi
    fi
    
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✓ Smoke tests passed! Run './tests/run_tests.sh unit' for full test suite${NC}"
    else
        echo -e "${YELLOW}⚠ Some smoke tests failed. Check output above.${NC}"
    fi
    
    return $result
}

# Function to run all unit tests
run_all_unit_tests() {
    local coverage=$1
    
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  UNIT TESTS${NC}"
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    
    # Note: Unit tests do NOT connect to any server - they mock all dependencies
    if [ "$SERVER_URL" != "http://localhost:8000" ]; then
        echo -e "${YELLOW}Note: Unit tests run locally (mocked) - they do not use SERVER_URL${NC}"
        echo -e "${YELLOW}      Use integration/bdd/endurance tests for remote server testing${NC}"
        echo ""
    fi
    
    # Create HTML report directory
    local html_report_dir="$PROJECT_ROOT/test_reports/unit"
    mkdir -p "$html_report_dir"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local html_report="$html_report_dir/unit_test_report_$timestamp.html"
    local json_report="$html_report_dir/unit_test_results.json"
    
    if [ "$coverage" = "true" ]; then
        $PYTHON -m pytest "$SCRIPT_DIR/unit" -v \
            --cov=src \
            --cov-report=term-missing \
            --cov-report=html:htmlcov \
            --html="$html_report" \
            --self-contained-html \
            --json-report \
            --json-report-file="$json_report"
    else
        $PYTHON -m pytest "$SCRIPT_DIR/unit" -v \
            --html="$html_report" \
            --self-contained-html \
            --json-report \
            --json-report-file="$json_report"
    fi
    
    local result=$?
    
    if [ -f "$html_report" ]; then
        echo -e "${BLUE}📊 HTML report saved to: $html_report${NC}"
    fi
    
    if [ -f "$json_report" ]; then
        echo -e "${BLUE}📊 JSON report saved to: $json_report${NC}"
        
        # Generate enhanced unit test report
        echo -e "${CYAN}Generating enhanced unit test report...${NC}"
        local enhanced_report="$html_report_dir/unit_test_report_enhanced_$timestamp.html"
        $PYTHON "$SCRIPT_DIR/report_generators/generate_unit_report.py" \
            --input "$json_report" \
            --output "$enhanced_report" \
            --title "Unit Test Report" 2>/dev/null || true
        
        if [ -f "$enhanced_report" ]; then
            echo -e "${GREEN}✓ Enhanced report: $enhanced_report${NC}"
        fi
    fi
    
    # Upload to S3 if enabled (upload even if tests fail, report shows failures)
    if [ "$UPLOAD_TO_S3" = "true" ]; then
        echo ""
        echo -e "${CYAN}Uploading test reports (including failures) to CloudFront...${NC}"
        upload_reports_to_s3
    fi
    
    return $result
}

# Function to run integration tests
run_integration_tests() {
    local type=$1  # "all", "shell", or "python"
    
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  INTEGRATION TESTS${NC}"
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    
    # Check if server is running for integration tests
    if ! check_server; then
        echo -e "${RED}Integration tests require a running server${NC}"
        return 1
    fi
    
    # Create HTML report directory
    local html_report_dir="$PROJECT_ROOT/test_reports/integration"
    mkdir -p "$html_report_dir"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local json_report="$html_report_dir/integration_test_results.json"
    local html_report="$html_report_dir/integration_test_report_$timestamp.html"
    
    # Run Python integration tests with JSON report
    if [ "$type" = "python" ] || [ "$type" = "all" ]; then
        echo -e "${CYAN}Running Python integration tests...${NC}"
        echo -e "${CYAN}Server URL: $SERVER_URL${NC}"
        
        $PYTHON -m pytest "$SCRIPT_DIR/integration/python" -v \
            --server-url="$SERVER_URL" \
            --json-report \
            --json-report-file="$json_report" \
            --html="$html_report" \
            --self-contained-html 2>&1 || true
        
        local result=$?
        
        # Generate enhanced integration report
        if [ -f "$json_report" ]; then
            echo -e "${BLUE}📊 JSON report saved to: $json_report${NC}"
            
            echo -e "${CYAN}Generating enhanced integration test report...${NC}"
            local enhanced_report="$html_report_dir/integration_test_report_enhanced_$timestamp.html"
            $PYTHON "$SCRIPT_DIR/report_generators/generate_integration_report.py" \
                --input "$json_report" \
                --output "$enhanced_report" \
                --title "Integration Test Report" 2>/dev/null || true
            
            if [ -f "$enhanced_report" ]; then
                echo -e "${GREEN}✓ Enhanced integration report: $enhanced_report${NC}"
            fi
        fi
        
        # Upload to S3 if enabled
        if [ "$UPLOAD_TO_S3" = "true" ]; then
            echo ""
            echo -e "${CYAN}Uploading integration test reports to CloudFront...${NC}"
            upload_reports_to_s3
        fi
        
        return $result
    fi
    
    # Fallback to old runner for shell tests
    local integration_runner="$SCRIPT_DIR/integration/run_all_tests.sh"
    
    if [ ! -f "$integration_runner" ]; then
        echo -e "${YELLOW}Integration test runner not found${NC}"
        echo -e "${YELLOW}Expected at: $integration_runner${NC}"
        return 1
    fi
    
    # Build command based on type
    local cmd="$integration_runner --server $SERVER_URL"
    
    case "$type" in
        "shell")
            cmd="$cmd --shell-only"
            ;;
        "performance")
            cmd="$cmd --performance"
            ;;
    esac
    
    # Add verbose if set
    if [ "$VERBOSE" = "true" ]; then
        cmd="$cmd --verbose"
    fi
    
    # Add JSON output if set
    if [ "$JSON_OUTPUT" = "true" ]; then
        cmd="$cmd --json"
    fi
    
    # Run integration tests
    echo -e "${CYAN}Running: $cmd${NC}"
    bash $cmd
    return $?
}

# Function to run specific journey integration tests
run_journey_integration_tests() {
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  JOURNEY INTEGRATION TESTS${NC}"
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    
    # Check server
    if ! check_server; then
        return 1
    fi
    
    # Run shell tests
    echo -e "${CYAN}Running Journey shell integration tests...${NC}"
    local shell_dir="$SCRIPT_DIR/integration/shell/journey"
    if [ -d "$shell_dir" ]; then
        for test_script in "$shell_dir"/*.sh; do
            if [ -f "$test_script" ]; then
                echo -e "${BLUE}  Running: $(basename $test_script)${NC}"
                bash "$test_script" "$SERVER_URL"
            fi
        done
    fi
    
    # Run Python tests
    echo -e "${CYAN}Running Journey Python integration tests...${NC}"
    $PYTHON -m pytest "$SCRIPT_DIR/integration/python/services/test_journey_service_integration.py" -v
    $PYTHON -m pytest "$SCRIPT_DIR/integration/python/mcp/test_journey_tool_integration.py" -v
    $PYTHON -m pytest "$SCRIPT_DIR/integration/python/api/test_journey_api_integration.py" -v
    
    return $?
}

# Function to run BDD tests for a specific domain
run_bdd_tests() {
    local domain=$1
    
    echo -e "${CYAN}Running $domain BDD tests...${NC}"
    
    # Use the dedicated BDD test runner with feature filter
    local bdd_runner="$SCRIPT_DIR/bdd/run_bdd_tests.sh"
    
    if [ -f "$bdd_runner" ]; then
        echo -e "${CYAN}Using BDD test runner for $domain features${NC}"
        bash "$bdd_runner" -f "$domain"
        return $?
    else
        # Fallback to direct behave call
        local feature_path="$SCRIPT_DIR/bdd/features/$domain"
        if [ ! -d "$feature_path" ]; then
            echo -e "${YELLOW}No BDD tests found for $domain${NC}"
            return 0
        fi
        
        cd "$PROJECT_ROOT"
        $PYTHON -m behave "$feature_path" --format progress
        local result=$?
        cd - > /dev/null
        return $result
    fi
}

# Function to run all BDD tests
run_all_bdd_tests() {
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  BDD TESTS${NC}"
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    
    local result=0
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    # Create BDD report directory
    local html_report_dir="$PROJECT_ROOT/test_reports/bdd"
    mkdir -p "$html_report_dir"
    
    local json_report="$html_report_dir/bdd_test_results_$timestamp.json"
    
    # Run BDD tests
    cd "$PROJECT_ROOT"
    echo -e "${CYAN}Running BDD tests with behave...${NC}"
    
    # Use the dedicated BDD runner which handles JSON output properly
    local bdd_runner="$SCRIPT_DIR/bdd/run_bdd_tests.sh"
    
    if [ -f "$bdd_runner" ]; then
        # Run BDD tests using the dedicated runner
        bash "$bdd_runner" 2>&1 || result=$?
        
        # Find the latest JSON output from BDD runner
        local latest_json=$(ls -t "$html_report_dir"/bdd_test_raw_*.json 2>/dev/null | head -1)
        if [ -n "$latest_json" ]; then
            json_report="$latest_json"
        fi
    else
        # Fallback: Try to run behave directly with json.pretty formatter
        echo -e "${YELLOW}Using fallback behave execution...${NC}"
        $PYTHON -m behave "$SCRIPT_DIR/bdd/features" \
            --format json.pretty \
            --outfile "$json_report" \
            --format progress \
            --no-capture 2>&1 || result=$?
    fi
    
    cd - > /dev/null
    
    # Generate enhanced BDD report if JSON exists
    if [ -f "$json_report" ]; then
        echo -e "${BLUE}📊 JSON report saved to: $json_report${NC}"
        
        echo -e "${CYAN}Generating enhanced BDD test report...${NC}"
        local enhanced_report="$html_report_dir/bdd_test_report_enhanced_$timestamp.html"
        $PYTHON "$SCRIPT_DIR/report_generators/generate_bdd_report.py" \
            --input "$json_report" \
            --output "$enhanced_report" \
            --title "BDD Test Report" 2>/dev/null || true
        
        if [ -f "$enhanced_report" ]; then
            echo -e "${GREEN}✓ Enhanced BDD report: $enhanced_report${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ No BDD JSON report generated${NC}"
    fi
    
    # Upload to S3 if enabled
    if [ "$UPLOAD_TO_S3" = "true" ]; then
        echo ""
        echo -e "${CYAN}Uploading BDD test reports to CloudFront...${NC}"
        upload_reports_to_s3
    fi
    
    return $result
}

# Function to run endurance tests
run_endurance_tests() {
    local time_limit=$1  # Optional time limit in seconds
    local result=0
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    if [ -n "$time_limit" ]; then
        echo -e "${PURPLE}  ENDURANCE TESTS (Quick ${time_limit}s)${NC}"
    else
        echo -e "${PURPLE}  ENDURANCE TESTS${NC}"
    fi
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    
    # Check server
    if ! check_server; then
        echo -e "${RED}Endurance tests require a running server${NC}"
        return 1
    fi
    
    local endurance_runner="$SCRIPT_DIR/endurance/run_endurance_test.sh"
    local html_report_dir="$PROJECT_ROOT/test_reports/endurance"
    mkdir -p "$html_report_dir"
    
    if [ -f "$endurance_runner" ]; then
        if [ -n "$time_limit" ]; then
            echo -e "${CYAN}Running endurance tests with ${time_limit}s timeout...${NC}"
            # Run with timeout
            timeout "${time_limit}s" bash "$endurance_runner" 2>/dev/null || true
            echo -e "${YELLOW}⏱ Endurance tests stopped after ${time_limit}s${NC}"
        else
            echo -e "${CYAN}Running full endurance test suite${NC}"
            bash "$endurance_runner" || result=$?
        fi
        
        # Find latest endurance JSON report
        local json_report=$(ls -t "$html_report_dir"/endurance_report_*.json 2>/dev/null | head -1)
        
        if [ -n "$json_report" ] && [ -f "$json_report" ]; then
            echo -e "${BLUE}📊 JSON report: $json_report${NC}"
            
            echo -e "${CYAN}Generating enhanced endurance test report...${NC}"
            local enhanced_report="$html_report_dir/endurance_test_report_enhanced_$timestamp.html"
            $PYTHON "$SCRIPT_DIR/report_generators/generate_endurance_report.py" \
                --input "$json_report" \
                --output "$enhanced_report" \
                --title "Endurance Test Report" 2>/dev/null || true
            
            if [ -f "$enhanced_report" ]; then
                echo -e "${GREEN}✓ Enhanced endurance report: $enhanced_report${NC}"
            fi
        fi
        
        # Upload to S3 if enabled
        if [ "$UPLOAD_TO_S3" = "true" ]; then
            echo ""
            echo -e "${CYAN}Uploading endurance test reports to CloudFront...${NC}"
            upload_reports_to_s3
        fi
        
        return $result
    else
        echo -e "${YELLOW}Endurance test runner not found${NC}"
        return 0
    fi
}

# Function to upload reports to S3
upload_reports_to_s3() {
    echo -e "${CYAN}Uploading test reports to S3/CloudFront...${NC}"
    
    if [ -z "$S3_BUCKET_NAME" ]; then
        echo -e "${YELLOW}⚠ S3_BUCKET_NAME not set, skipping upload${NC}"
        echo -e "${YELLOW}  Load environment: source tests/report_setup/load_cloudfront_env.sh${NC}"
        return 0
    fi
    
    local cloudfront_uploader="$SCRIPT_DIR/report_setup/upload_reports_to_cloudfront.sh"
    local report_dir="$PROJECT_ROOT/test_reports"
    
    # Check if CloudFront uploader exists
    if [ -f "$cloudfront_uploader" ]; then
        echo -e "${BLUE}Using CloudFront uploader${NC}"
        echo -e "${BLUE}S3 Bucket: $S3_BUCKET_NAME${NC}"
        echo -e "${BLUE}Region: $S3_REGION${NC}"
        if [ -n "$CLOUDFRONT_DOMAIN" ]; then
            echo -e "${BLUE}CloudFront: $CLOUDFRONT_DOMAIN${NC}"
        fi
        echo ""
        
        # Use the CloudFront uploader which handles everything
        bash "$cloudfront_uploader"
        return $?
    fi
    
    # Fallback: Direct AWS S3 upload (basic)
    echo -e "${YELLOW}⚠ CloudFront uploader not found, using direct S3 upload${NC}"
    
    # Find latest unit report
    local unit_report=$(ls -t "$report_dir/unit/unit_test_report_enhanced_"*.html 2>/dev/null | head -1)
    
    if [ -z "$unit_report" ]; then
        echo -e "${YELLOW}⚠ No reports found to upload${NC}"
        return 0
    fi
    
    echo -e "${CYAN}Uploading: $(basename "$unit_report")${NC}"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    if [ -n "$CLOUDFRONT_DOMAIN" ]; then
        # Upload with CloudFront path structure
        aws s3 cp "$unit_report" \
            "s3://$S3_BUCKET_NAME/${S3_REPORTS_PREFIX:-test-reports}/unit/$timestamp/report.html" \
            --content-type "text/html; charset=utf-8" \
            --region "$S3_REGION"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Report uploaded${NC}"
            echo -e "${BLUE}📊 View at: https://$CLOUDFRONT_DOMAIN/unit/$timestamp/report.html${NC}"
        fi
    else
        # Upload with basic S3 path
        aws s3 cp "$unit_report" \
            "s3://$S3_BUCKET_NAME/${S3_REPORTS_PREFIX:-test-reports}/unit/$timestamp/$(basename "$unit_report")" \
            --content-type "text/html" \
            --region "$S3_REGION"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Report uploaded${NC}"
        fi
    fi
    
    return $?
}

# Function to generate consolidated test report
generate_consolidated_report() {
    echo -e "${CYAN}Generating consolidated test report...${NC}"
    
    local report_dir="$PROJECT_ROOT/test_reports"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local consolidated_report="$report_dir/consolidated_report_$timestamp.html"
    
    # Find latest reports for each test type
    local unit_report=$(ls -t "$report_dir/unit/unit_test_report_enhanced_"*.html 2>/dev/null | head -1)
    local integration_report=$(ls -t "$report_dir/integration/integration_test_report_"*.html 2>/dev/null | head -1)
    local bdd_report="$report_dir/bdd/index.html"
    local endurance_report=$(ls -t "$report_dir/endurance/dashboard/"*.html 2>/dev/null | head -1)
    
    # Generate consolidated HTML report
    cat > "$consolidated_report" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consolidated Test Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f9fafb;
            color: #1f2937;
            line-height: 1.6;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 24px;
            text-align: center;
        }
        .header h1 { font-size: 36px; margin-bottom: 8px; }
        .header p { opacity: 0.9; }
        .container { max-width: 1200px; margin: 0 auto; padding: 40px 24px; }
        .report-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
            margin-top: 32px;
        }
        .report-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .report-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.15);
        }
        .report-card-header {
            padding: 24px;
            border-bottom: 1px solid #e5e7eb;
        }
        .report-icon {
            font-size: 48px;
            margin-bottom: 12px;
        }
        .report-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .report-description {
            color: #6b7280;
            font-size: 14px;
        }
        .report-card-body {
            padding: 24px;
        }
        .report-link {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            transition: background 0.3s;
        }
        .report-link:hover {
            background: #5a67d8;
        }
        .report-link.disabled {
            background: #9ca3af;
            cursor: not-allowed;
        }
        .status-available { color: #10b981; font-weight: 600; }
        .status-unavailable { color: #ef4444; font-weight: 600; }
        .footer {
            text-align: center;
            padding: 40px 24px;
            color: #6b7280;
        }
        .timestamp {
            background: white;
            padding: 16px 24px;
            border-radius: 8px;
            margin-bottom: 24px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Consolidated Test Report</h1>
        <p>AI Job Engine - Complete Test Suite Results</p>
    </div>
    
    <div class="container">
        <div class="timestamp">
            <strong>Generated:</strong> <span id="timestamp"></span>
        </div>
        
        <div class="report-grid">
            <!-- Unit Tests Card -->
            <div class="report-card">
                <div class="report-card-header">
                    <div class="report-icon">🧪</div>
                    <div class="report-title">Unit Tests</div>
                    <div class="report-description">Component-level test results with module breakdown</div>
                </div>
                <div class="report-card-body">
                    <p id="unit-status"></p>
                    <a href="UNIT_REPORT_PATH" class="report-link" id="unit-link">View Unit Test Report →</a>
                </div>
            </div>
            
            <!-- Integration Tests Card -->
            <div class="report-card">
                <div class="report-card-header">
                    <div class="report-icon">🔗</div>
                    <div class="report-title">Integration Tests</div>
                    <div class="report-description">API and service integration test results</div>
                </div>
                <div class="report-card-body">
                    <p id="integration-status"></p>
                    <a href="INTEGRATION_REPORT_PATH" class="report-link" id="integration-link">View Integration Report →</a>
                </div>
            </div>
            
            <!-- BDD Tests Card -->
            <div class="report-card">
                <div class="report-card-header">
                    <div class="report-icon">📝</div>
                    <div class="report-title">BDD Tests</div>
                    <div class="report-description">Behavior-driven development test scenarios</div>
                </div>
                <div class="report-card-body">
                    <p id="bdd-status"></p>
                    <a href="BDD_REPORT_PATH" class="report-link" id="bdd-link">View BDD Report →</a>
                </div>
            </div>
            
            <!-- Endurance Tests Card -->
            <div class="report-card">
                <div class="report-card-header">
                    <div class="report-icon">⚡</div>
                    <div class="report-title">Endurance Tests</div>
                    <div class="report-description">Long-running stability and performance tests</div>
                </div>
                <div class="report-card-body">
                    <p id="endurance-status"></p>
                    <a href="ENDURANCE_REPORT_PATH" class="report-link" id="endurance-link">View Endurance Report →</a>
                </div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>AI Job Engine Test Suite</p>
        <p>© 2025 TMF ODA Transformer Project</p>
    </div>
    
    <script>
        // Set timestamp
        document.getElementById('timestamp').textContent = new Date().toLocaleString();
        
        // Update status based on report availability
        function updateStatus(id, available) {
            const statusEl = document.getElementById(id + '-status');
            const linkEl = document.getElementById(id + '-link');
            if (available) {
                statusEl.innerHTML = '<span class="status-available">✓ Report Available</span>';
            } else {
                statusEl.innerHTML = '<span class="status-unavailable">✗ Report Not Available</span>';
                linkEl.classList.add('disabled');
                linkEl.onclick = function(e) { e.preventDefault(); };
            }
        }
        
        // Check which reports are available (will be replaced by script)
        updateStatus('unit', UNIT_AVAILABLE);
        updateStatus('integration', INTEGRATION_AVAILABLE);
        updateStatus('bdd', BDD_AVAILABLE);
        updateStatus('endurance', ENDURANCE_AVAILABLE);
    </script>
</body>
</html>
EOF

    # Replace placeholders with actual paths
    local unit_available="false"
    local integration_available="false"
    local bdd_available="false"
    local endurance_available="false"
    
    if [ -f "$unit_report" ]; then
        local unit_rel_path=$(realpath --relative-to="$report_dir" "$unit_report")
        sed -i "s|UNIT_REPORT_PATH|$unit_rel_path|g" "$consolidated_report"
        unit_available="true"
    else
        sed -i "s|UNIT_REPORT_PATH|#|g" "$consolidated_report"
    fi
    
    if [ -f "$integration_report" ]; then
        local integration_rel_path=$(realpath --relative-to="$report_dir" "$integration_report")
        sed -i "s|INTEGRATION_REPORT_PATH|$integration_rel_path|g" "$consolidated_report"
        integration_available="true"
    else
        sed -i "s|INTEGRATION_REPORT_PATH|#|g" "$consolidated_report"
    fi
    
    if [ -f "$bdd_report" ]; then
        local bdd_rel_path=$(realpath --relative-to="$report_dir" "$bdd_report")
        sed -i "s|BDD_REPORT_PATH|$bdd_rel_path|g" "$consolidated_report"
        bdd_available="true"
    else
        sed -i "s|BDD_REPORT_PATH|#|g" "$consolidated_report"
    fi
    
    if [ -f "$endurance_report" ]; then
        local endurance_rel_path=$(realpath --relative-to="$report_dir" "$endurance_report")
        sed -i "s|ENDURANCE_REPORT_PATH|$endurance_rel_path|g" "$consolidated_report"
        endurance_available="true"
    else
        sed -i "s|ENDURANCE_REPORT_PATH|#|g" "$consolidated_report"
    fi
    
    # Update availability flags
    sed -i "s|UNIT_AVAILABLE|$unit_available|g" "$consolidated_report"
    sed -i "s|INTEGRATION_AVAILABLE|$integration_available|g" "$consolidated_report"
    sed -i "s|BDD_AVAILABLE|$bdd_available|g" "$consolidated_report"
    sed -i "s|ENDURANCE_AVAILABLE|$endurance_available|g" "$consolidated_report"
    
    echo -e "${GREEN}✓ Consolidated report generated: $consolidated_report${NC}"
    echo -e "${BLUE}📊 View report: file://$consolidated_report${NC}"
    
    # Upload to S3 if enabled
    if [ "$UPLOAD_TO_S3" = "true" ]; then
        echo ""
        upload_reports_to_s3
    fi
}

# Function to clean test artifacts
clean_artifacts() {
    echo -e "${YELLOW}Cleaning test artifacts...${NC}"
    
    # Clean pytest cache
    find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$SCRIPT_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    
    # Clean coverage reports
    rm -rf "$PROJECT_ROOT/htmlcov" 2>/dev/null || true
    rm -f "$PROJECT_ROOT/.coverage" 2>/dev/null || true
    rm -rf "$PROJECT_ROOT/coverage.xml" 2>/dev/null || true
    
    # Clean BDD artifacts
    rm -rf "$SCRIPT_DIR/bdd/reports" 2>/dev/null || true
    
    # Clean test logs
    rm -rf "$PROJECT_ROOT/logs/test_*.log" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Cleaned test artifacts${NC}"
}

# Function to run all tests
run_all_tests() {
    local coverage=$1
    local endurance_time=$2  # Optional endurance time limit
    local failed=0
    
    if [ -n "$endurance_time" ]; then
        echo -e "${BLUE}Running ALL tests (with ${endurance_time}s endurance limit)...${NC}"
    else
    echo -e "${BLUE}Running ALL tests...${NC}"
    fi
    echo ""
    
    # Unit tests
    run_all_unit_tests "$coverage"
    [ $? -ne 0 ] && failed=1
    
    echo ""
    
    # Integration tests
    run_integration_tests "all"
    [ $? -ne 0 ] && failed=1
    
    echo ""
    
    # BDD tests
    run_all_bdd_tests
    [ $? -ne 0 ] && failed=1
    
    echo ""
    
    # Endurance tests
    if [ -n "$endurance_time" ]; then
        run_endurance_tests "$endurance_time"
    else
        run_endurance_tests
    fi
    [ $? -ne 0 ] && failed=1
    
    echo ""
    
    # Generate consolidated report
    generate_consolidated_report
    
    return $failed
}

# Function to run journey tests
run_journey_tests() {
    local failed=0
    
    echo -e "${BLUE}Running JOURNEY tests...${NC}"
    echo ""
    
    # Journey unit tests
    run_unit_tests "journey" false
    [ $? -ne 0 ] && failed=1
    
    echo ""
    
    # Journey integration tests
    run_journey_integration_tests
    [ $? -ne 0 ] && failed=1
    
    echo ""
    
    # Journey BDD tests
    run_bdd_tests "journey"
    [ $? -ne 0 ] && failed=1
    
    return $failed
}

# Function to run call-process integration tests
run_call_process_integration_tests() {
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  CALL-PROCESS INTEGRATION TESTS${NC}"
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    
    local html_report_dir="$PROJECT_ROOT/test_reports/call_process"
    mkdir -p "$html_report_dir"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local json_report="$html_report_dir/call_process_integration_results.json"
    local html_report="$html_report_dir/call_process_integration_report_$timestamp.html"
    
    echo -e "${CYAN}Running Call-Process Python integration tests...${NC}"
    
    $PYTHON -m pytest "$SCRIPT_DIR/integration/call_process" -v \
        --json-report \
        --json-report-file="$json_report" \
        --html="$html_report" \
        --self-contained-html 2>&1 || true
    
    local result=$?
    
    if [ -f "$html_report" ]; then
        echo -e "${BLUE}📊 HTML report saved to: $html_report${NC}"
    fi
    
    if [ -f "$json_report" ]; then
        echo -e "${BLUE}📊 JSON report saved to: $json_report${NC}"
    fi
    
    # Upload to S3 if enabled
    if [ "$UPLOAD_TO_S3" = "true" ]; then
        echo ""
        echo -e "${CYAN}Uploading call-process test reports to CloudFront...${NC}"
        upload_reports_to_s3
    fi
    
    return $result
}

# Function to run call-process BDD tests
run_call_process_bdd_tests() {
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  CALL-PROCESS BDD TESTS${NC}"
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    
    local result=0
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    local html_report_dir="$PROJECT_ROOT/test_reports/call_process"
    mkdir -p "$html_report_dir"
    
    local json_report="$html_report_dir/call_process_bdd_results_$timestamp.json"
    
    cd "$PROJECT_ROOT"
    echo -e "${CYAN}Running Call-Process BDD tests with behave...${NC}"
    
    $PYTHON -m behave "$SCRIPT_DIR/bdd/features/call_process" \
        --format json.pretty \
        --outfile "$json_report" \
        --format progress \
        --no-capture 2>&1 || result=$?
    
    cd - > /dev/null
    
    if [ -f "$json_report" ]; then
        echo -e "${BLUE}📊 JSON report saved to: $json_report${NC}"
    fi
    
    # Upload to S3 if enabled
    if [ "$UPLOAD_TO_S3" = "true" ]; then
        echo ""
        echo -e "${CYAN}Uploading call-process BDD reports to CloudFront...${NC}"
        upload_reports_to_s3
    fi
    
    return $result
}

# Function to run call-process endurance tests
run_call_process_endurance_tests() {
    local time_limit=$1
    local result=0
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  CALL-PROCESS ENDURANCE TESTS${NC}"
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    
    local html_report_dir="$PROJECT_ROOT/test_reports/call_process/endurance"
    mkdir -p "$html_report_dir"
    
    local config_file="$SCRIPT_DIR/endurance/call_process_config.yaml"
    
    if [ ! -f "$config_file" ]; then
        echo -e "${YELLOW}⚠ Call-process endurance config not found: $config_file${NC}"
        return 1
    fi
    
    echo -e "${CYAN}Using config: $config_file${NC}"
    
    # Run BDD endurance runner with call-process config
    local endurance_runner="$SCRIPT_DIR/endurance/bdd_endurance_runner.py"
    
    if [ -f "$endurance_runner" ]; then
        if [ -n "$time_limit" ]; then
            echo -e "${CYAN}Running call-process endurance with ${time_limit}s timeout...${NC}"
            timeout "${time_limit}s" $PYTHON "$endurance_runner" \
                --config "$config_file" 2>/dev/null || true
        else
            echo -e "${CYAN}Running full call-process endurance suite...${NC}"
            $PYTHON "$endurance_runner" --config "$config_file" || result=$?
        fi
    else
        echo -e "${YELLOW}⚠ Endurance runner not found: $endurance_runner${NC}"
        return 1
    fi
    
    return $result
}

# Function to run all call-process tests
run_call_process_tests() {
    local failed=0
    
    echo -e "${BLUE}Running CALL-PROCESS tests...${NC}"
    echo ""
    
    # Call-process unit tests
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  CALL-PROCESS UNIT TESTS${NC}"
    echo -e "${PURPLE}════════════════════════════════════════${NC}"
    
    local html_report_dir="$PROJECT_ROOT/test_reports/call_process"
    mkdir -p "$html_report_dir"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local json_report="$html_report_dir/call_process_unit_results.json"
    local html_report="$html_report_dir/call_process_unit_report_$timestamp.html"
    
    $PYTHON -m pytest "$SCRIPT_DIR/unit/call_process" -v \
        --json-report \
        --json-report-file="$json_report" \
        --html="$html_report" \
        --self-contained-html 2>&1 || true
    
    [ $? -ne 0 ] && failed=1
    
    if [ -f "$html_report" ]; then
        echo -e "${BLUE}📊 HTML report saved to: $html_report${NC}"
    fi
    
    echo ""
    
    # Call-process integration tests
    run_call_process_integration_tests
    [ $? -ne 0 ] && failed=1
    
    echo ""
    
    # Call-process BDD tests
    run_call_process_bdd_tests
    [ $? -ne 0 ] && failed=1
    
    return $failed
}

# Main execution
main() {
    # Parse arguments
    local auto_upload=false
    local test_command=""
    local custom_server_url=""
    local insecure_mode=false
    
    # Parse all arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            --upload|-u)
                auto_upload=true
                shift
                ;;
            --insecure|-k)
                insecure_mode=true
                shift
                ;;
            --server|-s)
                if [ -n "$2" ] && [ "${2:0:1}" != "-" ]; then
                    custom_server_url="$2"
                    shift 2
                else
                    echo -e "${RED}Error: --server requires a URL argument${NC}"
                    exit 1
                fi
                ;;
            -*)
                # Unknown flag - could be a test command like "-h"
                test_command="$1"
                shift
                ;;
            *)
                # Positional argument - test command
                if [ -z "$test_command" ]; then
                    test_command="$1"
                fi
                shift
                ;;
        esac
    done
    
    # Default to smoke tests if no command specified
    test_command="${test_command:-smoke}"
    
    # Apply custom server URL if provided
    if [ -n "$custom_server_url" ]; then
        export SERVER_URL="$custom_server_url"
        echo -e "${CYAN}Using remote server: ${SERVER_URL}${NC}"
    fi
    
    # Apply insecure mode if enabled
    if [ "$insecure_mode" = "true" ]; then
        export CURL_INSECURE="true"
        echo -e "${YELLOW}SSL certificate verification: DISABLED${NC}"
    fi
    
    # Add blank line after server/SSL info
    if [ -n "$custom_server_url" ] || [ "$insecure_mode" = "true" ]; then
        echo ""
    fi
    
    # If --upload flag is set, load CloudFront environment
    if [ "$auto_upload" = "true" ]; then
        echo -e "${CYAN}--upload flag detected, loading CloudFront environment...${NC}"
        if [ -f "$SCRIPT_DIR/report_setup/load_cloudfront_env.sh" ]; then
            source "$SCRIPT_DIR/report_setup/load_cloudfront_env.sh"
            echo ""
        else
            echo -e "${YELLOW}⚠ CloudFront environment not found, skipping auto-load${NC}"
            echo ""
        fi
    fi
    
    # Check environment
    check_environment
    
    # Handle comma-separated test types (e.g., unit,integration)
    if [[ "$test_command" == *","* ]]; then
        echo -e "${BLUE}Running multiple test types: $test_command${NC}"
        echo ""
        
        IFS=',' read -ra TEST_TYPES <<< "$test_command"
        local overall_failed=0
        
        # Temporarily disable per-test uploads - we'll do one upload at the end
        local saved_upload_setting="$UPLOAD_TO_S3"
        export UPLOAD_TO_S3="false"
        
        for test_type in "${TEST_TYPES[@]}"; do
            test_type=$(echo "$test_type" | xargs)  # Trim whitespace
            echo -e "${PURPLE}════════════════════════════════════════${NC}"
            echo -e "${PURPLE}  Running: $test_type${NC}"
            echo -e "${PURPLE}════════════════════════════════════════${NC}"
            echo ""
            
            case "$test_type" in
                unit)
                    run_all_unit_tests false
                    ;;
                integration)
                    run_integration_tests "all"
                    ;;
                integration-python)
                    run_integration_tests "python"
                    ;;
                integration-shell)
                    run_integration_tests "shell"
                    ;;
                bdd)
                    run_all_bdd_tests
                    ;;
                endurance)
                    run_endurance_tests
                    ;;
                *)
                    echo -e "${RED}Invalid test type: $test_type${NC}"
                    ;;
            esac
            
            [ $? -ne 0 ] && overall_failed=1
            echo ""
        done
        
        # Restore upload setting and do single upload at the end
        export UPLOAD_TO_S3="$saved_upload_setting"
        if [ "$UPLOAD_TO_S3" = "true" ]; then
            echo -e "${PURPLE}════════════════════════════════════════${NC}"
            echo -e "${PURPLE}  Uploading ALL reports to CloudFront${NC}"
            echo -e "${PURPLE}════════════════════════════════════════${NC}"
            echo ""
            upload_reports_to_s3
        fi
        
        # Store exit code
        exit_code=$overall_failed
    else
        # Original single command handling
        case "$test_command" in
        smoke|quick)
            run_smoke_tests
            ;;
        all-quick|quick-all)
            # All tests with 1-minute endurance limit
            echo -e "${BLUE}Running all tests with quick endurance (1 min)...${NC}"
            echo ""
            run_all_tests false 60  # 60 seconds endurance limit
            ;;
        all)
            run_all_tests false
            ;;
        all-full|full)
            # Full suite with AWS refresh and gateway restart
            refresh_aws_credentials
            restart_gateway_server
            run_all_tests false
            ;;
        unit)
            run_all_unit_tests false
            ;;
        integration)
            run_integration_tests "all"
            ;;
        integration-shell)
            run_integration_tests "shell"
            ;;
        integration-python)
            run_integration_tests "python"
            ;;
        bdd)
            run_all_bdd_tests
            ;;
        endurance)
            run_endurance_tests
            ;;
        journey)
            run_journey_tests
            ;;
        journey-unit)
            run_unit_tests "journey" false
            ;;
        journey-integration)
            run_journey_integration_tests
            ;;
        journey-bdd)
            run_bdd_tests "journey"
            ;;
        capability)
            run_unit_tests "capability" false
            echo ""
            run_bdd_tests "capability"
            ;;
        capability-unit)
            run_unit_tests "capability" false
            ;;
        capability-bdd)
            run_bdd_tests "capability"
            ;;
        call-process)
            run_call_process_tests
            ;;
        call-process-unit)
            echo -e "${PURPLE}════════════════════════════════════════${NC}"
            echo -e "${PURPLE}  CALL-PROCESS UNIT TESTS${NC}"
            echo -e "${PURPLE}════════════════════════════════════════${NC}"
            local html_report_dir="$PROJECT_ROOT/test_reports/call_process"
            mkdir -p "$html_report_dir"
            local timestamp=$(date +%Y%m%d_%H%M%S)
            local json_report="$html_report_dir/call_process_unit_results.json"
            local html_report="$html_report_dir/call_process_unit_report_$timestamp.html"
            $PYTHON -m pytest "$SCRIPT_DIR/unit/call_process" -v \
                --json-report \
                --json-report-file="$json_report" \
                --html="$html_report" \
                --self-contained-html
            ;;
        call-process-integration)
            run_call_process_integration_tests
            ;;
        call-process-bdd)
            run_call_process_bdd_tests
            ;;
        call-process-endurance)
            run_call_process_endurance_tests
            ;;
        coverage)
            run_all_tests true
            ;;
        performance)
            RUN_PERFORMANCE_TESTS=true
            run_integration_tests "performance"
            ;;
        server-check)
            check_server
            ;;
        server-restart)
            restart_gateway_server
            ;;
        aws-refresh)
            refresh_aws_credentials
            ;;
        consolidated-report)
            generate_consolidated_report
            ;;
        upload-to-s3)
            # Upload existing reports to S3
            UPLOAD_TO_S3=true
            upload_reports_to_s3
            ;;
        clean)
            clean_artifacts
            ;;
        help|--help|-h)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option: $1${NC}"
            usage
            exit 1
            ;;
        esac
        
        # Store exit code
        exit_code=$?
    fi
    
    # Print summary
    echo ""
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}════════════════════════════════════════${NC}"
        echo -e "${GREEN}  ✅ TESTS PASSED${NC}"
        echo -e "${GREEN}════════════════════════════════════════${NC}"
    else
        echo -e "${RED}════════════════════════════════════════${NC}"
        echo -e "${RED}  ❌ TESTS FAILED${NC}"
        echo -e "${RED}════════════════════════════════════════${NC}"
    fi
    
    exit $exit_code
}

# Run main function
main "$@"