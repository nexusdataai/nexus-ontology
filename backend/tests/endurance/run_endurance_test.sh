#!/bin/bash
#
# BDD Endurance Test Runner Script
# Main entry point for running endurance tests with comprehensive monitoring
#

set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default values
CONFIG_FILE="$SCRIPT_DIR/endurance_config.yaml"
DURATION_MINUTES=""
TEST_MODE=false
DASHBOARD_ONLY=false
CLEANUP=true
VERBOSE=false
PARALLEL=1
PYTHON_CMD=""

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_header() {
    echo -e "\n${BOLD}${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}    $1${NC}"
    echo -e "${BOLD}${MAGENTA}═══════════════════════════════════════════════════════════════${NC}\n"
}

# Function to display usage
usage() {
    cat << EOF
${BOLD}Usage:${NC} $0 [OPTIONS]

${BOLD}Run BDD endurance tests with comprehensive monitoring${NC}

${BOLD}OPTIONS:${NC}
    -c, --config FILE       Configuration file (default: endurance_config.yaml)
    -d, --duration MINUTES  Override test duration in minutes
    -t, --test              Run quick 5-minute test
    -p, --parallel N        Number of parallel test instances
    -D, --dashboard         Launch dashboard only (no tests)
    --no-cleanup           Skip cleanup after test
    -v, --verbose          Enable verbose output
    -h, --help             Show this help message

${BOLD}EXAMPLES:${NC}
    # Run default 30-minute endurance test
    $0

    # Run quick 5-minute test
    $0 --test

    # Run 60-minute test with custom config
    $0 --duration 60 --config custom_config.yaml

    # Run with 4 parallel instances
    $0 --parallel 4

    # Launch monitoring dashboard only
    $0 --dashboard

${BOLD}ENVIRONMENT VARIABLES:${NC}
    AWS_REGION          AWS region for testing (default: us-east-1)
    DYNAMODB_TABLE      DynamoDB table name
    S3_BUCKET           S3 bucket for test data
    SLACK_WEBHOOK_URL   Slack webhook for notifications
    SMTP_USERNAME       SMTP username for email alerts
    SMTP_PASSWORD       SMTP password for email alerts

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -d|--duration)
            DURATION_MINUTES="$2"
            shift 2
            ;;
        -t|--test)
            TEST_MODE=true
            DURATION_MINUTES=5
            shift
            ;;
        -p|--parallel)
            PARALLEL="$2"
            shift 2
            ;;
        -D|--dashboard)
            DASHBOARD_ONLY=true
            shift
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Function to find Python command
find_python() {
    # Check for virtual environment first
    if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
        PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python"
    elif [ -f "$PROJECT_ROOT/venv/bin/python" ]; then
        PYTHON_CMD="$PROJECT_ROOT/venv/bin/python"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python not found. Please install Python 3.8+"
        exit 1
    fi
    
    print_info "Using Python: $PYTHON_CMD"
    $PYTHON_CMD --version
}

# Function to check dependencies
check_dependencies() {
    print_header "Checking Dependencies"
    
    find_python
    
    # Check required Python packages
    print_info "Checking Python packages..."
    
    local missing_packages=()
    
    # Check each required package
    for package in behave pexpect psutil boto3 yaml; do
        if ! $PYTHON_CMD -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        print_error "Missing Python packages: ${missing_packages[*]}"
        print_info "Installing missing packages..."
        
        if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
            $PYTHON_CMD -m pip install -r "$PROJECT_ROOT/requirements.txt"
        else
            $PYTHON_CMD -m pip install "${missing_packages[@]}"
        fi
    else
        print_success "All required Python packages are installed"
    fi
    
    # Check if BDD tests exist
    if [ ! -d "$PROJECT_ROOT/tests/bdd" ]; then
        print_error "BDD tests directory not found: $PROJECT_ROOT/tests/bdd"
        exit 1
    fi
    
    # Check if config file exists
    if [ ! -f "$CONFIG_FILE" ]; then
        print_warning "Config file not found: $CONFIG_FILE"
        print_info "Using default configuration"
    fi
}

# Function to setup environment
setup_environment() {
    print_header "Setting Up Environment"
    
    # Set Python path
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # Set default AWS region if not set
    export AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
    
    # Set test environment variables
    export ENDURANCE_TEST=true
    export TEST_MODE="${TEST_MODE}"
    
    # Create output directories
    mkdir -p "$PROJECT_ROOT/test_reports/endurance"
    mkdir -p "$PROJECT_ROOT/logs"
    
    print_success "Environment setup complete"
}

# Function to start monitoring dashboard
start_dashboard() {
    print_header "Starting Monitoring Dashboard"
    
    local dashboard_dir="$PROJECT_ROOT/test_reports/endurance/dashboard"
    local dashboard_script="$dashboard_dir/server.py"
    
    # Ensure dashboard directory exists
    mkdir -p "$dashboard_dir"
    
    # Copy dashboard files if they don't exist
    if [ ! -f "$dashboard_dir/index.html" ]; then
        if [ -f "$SCRIPT_DIR/dashboard/index.html" ]; then
            cp "$SCRIPT_DIR/dashboard/"* "$dashboard_dir/" 2>/dev/null || true
        fi
    fi
    
    if [ ! -f "$dashboard_script" ]; then
        print_warning "Dashboard server not found, creating simple HTTP server..."
        
        # Create simple dashboard server
        cat > "$dashboard_script" << 'EOFDASH'
#!/usr/bin/env python3
import http.server
import socketserver
import os

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"Dashboard running at http://localhost:{PORT}")
    httpd.serve_forever()
EOFDASH
        chmod +x "$dashboard_script"
    fi
    
    # Start dashboard in background
    $PYTHON_CMD "$dashboard_script" > "$PROJECT_ROOT/logs/dashboard.log" 2>&1 &
    local dashboard_pid=$!
    
    sleep 2
    
    if kill -0 $dashboard_pid 2>/dev/null; then
        print_success "Dashboard started (PID: $dashboard_pid)"
        print_info "Access dashboard at: http://localhost:8080"
        echo $dashboard_pid > "$PROJECT_ROOT/.dashboard.pid"
    else
        print_warning "Dashboard failed to start"
    fi
}

# Function to stop dashboard
stop_dashboard() {
    if [ -f "$PROJECT_ROOT/.dashboard.pid" ]; then
        local pid=$(cat "$PROJECT_ROOT/.dashboard.pid")
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            print_info "Dashboard stopped (PID: $pid)"
        fi
        rm -f "$PROJECT_ROOT/.dashboard.pid"
    fi
}

# Function to run endurance tests
run_endurance_tests() {
    print_header "Running Endurance Tests"
    
    # Build command
    local cmd="$PYTHON_CMD $SCRIPT_DIR/bdd_endurance_runner.py"
    
    if [ -f "$CONFIG_FILE" ]; then
        cmd="$cmd --config $CONFIG_FILE"
    fi
    
    if [ -n "$DURATION_MINUTES" ]; then
        cmd="$cmd --duration $DURATION_MINUTES"
    fi
    
    if [ "$TEST_MODE" = true ]; then
        cmd="$cmd --test"
        print_info "Running in TEST mode (5 minutes)"
    fi
    
    # Set parallel instances in config
    if [ "$PARALLEL" -gt 1 ]; then
        print_info "Running with $PARALLEL parallel instances"
        export ENDURANCE_PARALLEL=$PARALLEL
    fi
    
    # Log file
    local log_file="$PROJECT_ROOT/logs/endurance_$(date +%Y%m%d_%H%M%S).log"
    
    print_info "Starting endurance test..."
    print_info "Command: $cmd"
    print_info "Log file: $log_file"
    
    # Run tests
    if [ "$VERBOSE" = true ]; then
        $cmd 2>&1 | tee "$log_file"
    else
        $cmd > "$log_file" 2>&1 &
        local test_pid=$!
        
        # Show progress
        local spinner=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
        local spin_idx=0
        
        while kill -0 $test_pid 2>/dev/null; do
            printf "\r${CYAN}[${spinner[$spin_idx]}]${NC} Test running... (tail -f $log_file to monitor)"
            spin_idx=$(( (spin_idx + 1) % ${#spinner[@]} ))
            sleep 0.5
        done
        
        wait $test_pid
        local exit_code=$?
        
        printf "\r"
        if [ $exit_code -eq 0 ]; then
            print_success "Endurance test completed successfully"
        else
            print_error "Endurance test failed with exit code: $exit_code"
        fi
    fi
}

# Function to generate summary report
generate_summary() {
    print_header "Generating Summary Report"
    
    # Find latest report files
    local report_dir="$PROJECT_ROOT/test_reports/endurance"
    local latest_json=$(ls -t "$report_dir"/endurance_report_*.json 2>/dev/null | head -1)
    local latest_html=$(ls -t "$report_dir"/endurance_report_*.html 2>/dev/null | head -1)
    
    if [ -f "$latest_json" ]; then
        print_info "Latest JSON report: $latest_json"
        
        # Extract key metrics using Python
        $PYTHON_CMD << EOF
import json

with open('$latest_json', 'r') as f:
    data = json.load(f)
    
summary = data.get('summary', {})
health = data.get('health', {})

print("\n${BOLD}Test Summary:${NC}")
print(f"  Total Tests: {summary.get('total_tests', 0)}")
print(f"  Passed: {summary.get('passed', 0)}")
print(f"  Failed: {summary.get('failed', 0)}")
print(f"  Pass Rate: {summary.get('pass_rate', 0):.1f}%")
print(f"  Flaky Tests: {summary.get('flaky_tests_count', 0)}")

if health:
    print(f"\n${BOLD}Health Status:${NC}")
    print(f"  System Healthy: {'✓' if health.get('is_healthy', True) else '✗'}")
    print(f"  Alerts: {len(health.get('alerts', []))}")
    
    cpu = health.get('summary', {}).get('cpu', {})
    memory = health.get('summary', {}).get('memory_gb', {})
    if cpu:
        print(f"  CPU - Mean: {cpu.get('mean', 0):.1f}%, Max: {cpu.get('max', 0):.1f}%")
    if memory:
        print(f"  Memory - Mean: {memory.get('mean', 0):.2f}GB, Max: {memory.get('max', 0):.2f}GB")

recommendations = data.get('recommendations', [])
if recommendations:
    print(f"\n${BOLD}Recommendations:${NC}")
    for rec in recommendations[:5]:
        print(f"  • {rec}")
EOF
    fi
    
    if [ -f "$latest_html" ]; then
        print_info "\nHTML Report: file://$latest_html"
        
        # Open in browser if available
        if command -v xdg-open &> /dev/null; then
            xdg-open "$latest_html" 2>/dev/null &
        elif command -v open &> /dev/null; then
            open "$latest_html" 2>/dev/null &
        fi
    fi
}

# Function to cleanup
cleanup() {
    if [ "$CLEANUP" = true ]; then
        print_header "Cleaning Up"
        
        # Stop dashboard
        stop_dashboard
        
        # Kill any remaining test processes
        pkill -f "bdd_endurance_runner.py" 2>/dev/null || true
        pkill -f "journey-manager.py" 2>/dev/null || true
        
        # Clean up temp files
        rm -f "$PROJECT_ROOT"/.dashboard.pid
        rm -f "$PROJECT_ROOT"/.endurance.lock
        
        print_success "Cleanup complete"
    fi
}

# Trap for cleanup on exit
trap cleanup EXIT INT TERM

# Main execution
main() {
    print_header "BDD Endurance Test Suite"
    print_info "Starting at $(date)"
    
    # Check dependencies
    check_dependencies
    
    # Setup environment
    setup_environment
    
    if [ "$DASHBOARD_ONLY" = true ]; then
        # Launch dashboard only
        start_dashboard
        print_info "Dashboard running. Press Ctrl+C to stop."
        wait
    else
        # Start dashboard if not in test mode
        if [ "$TEST_MODE" = false ]; then
            start_dashboard
        fi
        
        # Run endurance tests
        run_endurance_tests
        
        # Generate summary
        generate_summary
    fi
    
    print_info "Completed at $(date)"
}

# Run main function
main
