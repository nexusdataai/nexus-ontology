#!/bin/bash
#
# Convenient script to run BDD tests for Journey Manager CLI
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TAGS=""
FEATURES=""
FORMAT="pretty"
PARALLEL=false
STOP_ON_FAILURE=false
DRY_RUN=false

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

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Run BDD tests for Journey Manager CLI

OPTIONS:
    -t, --tags TAGS         Run scenarios with specific tags (comma-separated)
    -f, --feature FEATURE   Run specific feature file
    -s, --scenario NAME     Run specific scenario (requires -f)
    -p, --parallel         Run tests in parallel
    -d, --dry-run          Only parse features, don't execute
    --format FORMAT        Output format (pretty, json, junit) [default: pretty]
    --stop-on-failure      Stop on first failure
    --list-features        List all available features
    --list-scenarios FEAT  List scenarios in a feature
    -h, --help            Show this help message

EXAMPLES:
    # Run all tests
    $0

    # Run only journey management tests
    $0 -f journey_management

    # Run tests with specific tags
    $0 -t @journey,@create

    # Run tests excluding certain tags
    $0 -t ~@slow,~@wip

    # Run specific scenario
    $0 -f journey_management -s "Create a new journey successfully"

    # Run tests in parallel with JSON output
    $0 -p --format json

    # List all features
    $0 --list-features
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tags)
            TAGS="$2"
            shift 2
            ;;
        -f|--feature)
            FEATURES="$2"
            shift 2
            ;;
        -s|--scenario)
            SCENARIO="$2"
            shift 2
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --stop-on-failure)
            STOP_ON_FAILURE=true
            shift
            ;;
        --list-features)
            LIST_FEATURES=true
            shift
            ;;
        --list-scenarios)
            LIST_SCENARIOS="$2"
            shift 2
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

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_error "Virtual environment not found!"
    print_info "Creating virtual environment..."
    uv venv
fi

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root for uv run
cd "$PROJECT_ROOT"

# Check if behave is installed
if ! uv run behave --version &> /dev/null; then
    print_error "Behave not installed!"
    print_info "Installing dependencies..."
    uv sync
fi

print_info "Using uv run for BDD tests..."

# Create HTML report directory
HTML_REPORT_DIR="$PROJECT_ROOT/test_reports/bdd"
mkdir -p "$HTML_REPORT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
HTML_REPORT="$HTML_REPORT_DIR/bdd_test_report_$TIMESTAMP.html"
JSON_REPORT="$HTML_REPORT_DIR/bdd_test_raw_$TIMESTAMP.json"
JSON_FINAL="$HTML_REPORT_DIR/bdd_test_results.json"

# Build behave command with JSON formatter
# Run from tests/bdd directory but using project root's uv environment
cd "$SCRIPT_DIR"

# Use uv run to ensure correct environment
CMD="uv run behave"

# Add JSON formatter (behave's built-in)  
CMD="$CMD -f json -o $JSON_REPORT"

# Add JSON.pretty formatter for better formatting
CMD="$CMD -f json.pretty -o ${JSON_REPORT%.json}_pretty.json"

# Add console formatter for real-time output
CMD="$CMD -f pretty"

# Handle list operations
if [ "$LIST_FEATURES" = true ]; then
    behave --dry-run --no-summary
    exit 0
fi

if [ -n "$LIST_SCENARIOS" ]; then
    behave features/$LIST_SCENARIOS --dry-run --no-summary
    exit 0
fi

# Add options
if [ -n "$TAGS" ]; then
    # Convert comma-separated tags to space-separated
    TAGS_ARRAY=(${TAGS//,/ })
    for tag in "${TAGS_ARRAY[@]}"; do
        CMD="$CMD --tags $tag"
    done
fi

if [ -n "$FEATURES" ]; then
    CMD="behave features/$FEATURES -f html -o $HTML_REPORT -f pretty"
    if [ -n "$TAGS" ]; then
        for tag in "${TAGS_ARRAY[@]}"; do
            CMD="$CMD --tags $tag"
        done
    fi
fi

if [ -n "$SCENARIO" ]; then
    if [ -z "$FEATURES" ]; then
        print_error "Scenario option requires feature to be specified"
        exit 1
    fi
    CMD="$CMD --name \"$SCENARIO\""
fi

if [ "$PARALLEL" = true ]; then
    print_warning "Parallel execution not supported with HTML reports, ignoring"
fi

if [ "$DRY_RUN" = true ]; then
    CMD="$CMD --dry-run"
fi

if [ "$STOP_ON_FAILURE" = true ]; then
    CMD="$CMD --stop"
fi

# Run tests
print_info "Running BDD tests..."
print_info "Command: $CMD"
echo

# Execute tests and capture exit code
eval $CMD
EXIT_CODE=$?

# Inform about HTML report
if [ -f "$HTML_REPORT" ]; then
    echo
    print_info "📊 HTML report saved to: $HTML_REPORT"
fi

# Generate enhanced HTML report from JSON
if [ -f "$JSON_REPORT" ] || [ -f "${JSON_REPORT%.json}_pretty.json" ]; then
    print_info "Generating enhanced HTML report..."
    
    # Use pretty JSON if available, otherwise regular JSON
    INPUT_JSON="$JSON_REPORT"
    if [ -f "${JSON_REPORT%.json}_pretty.json" ]; then
        INPUT_JSON="${JSON_REPORT%.json}_pretty.json"
    fi
    
    ENHANCED_HTML="$HTML_REPORT_DIR/bdd_report_enhanced_$TIMESTAMP.html"
    
    python3 "$SCRIPT_DIR/enhanced_report_generator.py" \
        --input "$INPUT_JSON" \
        --output "$ENHANCED_HTML" \
        --title "BDD Test Report"
    
    if [ -f "$ENHANCED_HTML" ]; then
        print_info "📊 Enhanced HTML report: $ENHANCED_HTML"
        
        # Create symlink for easy access
        ln -sf "$(basename $ENHANCED_HTML)" "$HTML_REPORT_DIR/index.html"
        print_info "📊 Quick access: $HTML_REPORT_DIR/index.html"
        
        # Also keep the filename in a variable for later
        HTML_REPORT="$ENHANCED_HTML"
    fi
fi

# Convert behave JSON to standardized format
if [ -f "$JSON_REPORT" ]; then
    print_info "Converting BDD JSON to standardized format..."
    python3 << 'CONVERT_SCRIPT'
import json
import sys
from datetime import datetime

try:
    # Read behave JSON
    with open("$JSON_REPORT", "r") as f:
        behave_data = json.load(f)
    
    # Extract summary
    total_scenarios = 0
    passed_scenarios = 0
    failed_scenarios = 0
    error_scenarios = 0
    total_steps = 0
    passed_steps = 0
    failed_steps = 0
    
    for feature in behave_data:
        for scenario in feature.get("elements", []):
            if scenario.get("type") == "scenario":
                total_scenarios += 1
                status = scenario.get("status", "error")
                if status == "passed":
                    passed_scenarios += 1
                elif status == "failed":
                    failed_scenarios += 1
                else:
                    error_scenarios += 1
                
                for step in scenario.get("steps", []):
                    total_steps += 1
                    step_status = step.get("result", {}).get("status", "error")
                    if step_status == "passed":
                        passed_steps += 1
                    elif step_status == "failed":
                        failed_steps += 1
    
    # Calculate duration
    duration = behave_data[0].get("duration", 0) if behave_data else 0
    
    # Create standardized JSON
    standardized = {
        "timestamp": datetime.now().isoformat(),
        "test_type": "bdd",
        "summary": {
            "total_features": len(behave_data),
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_scenarios,
            "failed_scenarios": failed_scenarios,
            "error_scenarios": error_scenarios,
            "total_steps": total_steps,
            "passed_steps": passed_steps,
            "failed_steps": failed_steps,
            "pass_rate": round((passed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0, 1),
            "duration": duration
        },
        "features": behave_data
    }
    
    # Write standardized JSON
    with open("$JSON_FINAL", "w") as f:
        json.dump(standardized, f, indent=2)
    
    print("✅ JSON conversion complete")
except Exception as e:
    print(f"⚠️ JSON conversion failed: {e}")
    sys.exit(0)  # Don't fail the whole test run
CONVERT_SCRIPT
    
    if [ -f "$JSON_FINAL" ]; then
        print_info "📊 JSON report saved to: $JSON_FINAL"
    fi
fi

# Aggregate results for unified dashboard
if [ -f "$PROJECT_ROOT/test_reports/aggregate_results.py" ]; then
    print_info "Aggregating results for unified dashboard..."
    python3 "$PROJECT_ROOT/test_reports/aggregate_results.py" 2>/dev/null || true
fi

# Print summary
echo
if [ $EXIT_CODE -eq 0 ]; then
    print_success "All tests passed!"
else
    print_error "Some tests failed!"
fi

# Show report location if JSON format was used
if [ "$FORMAT" = "json" ] || [ "$FORMAT" = "junit" ]; then
    LATEST_REPORT=$(ls -td test_reports/bdd_* 2>/dev/null | head -1)
    if [ -n "$LATEST_REPORT" ]; then
        print_info "Test reports available at: $LATEST_REPORT"
        
        # If JSON format and HTML report exists, show it
        if [ "$FORMAT" = "json" ] && [ -f "$LATEST_REPORT/report.html" ]; then
            print_info "HTML report: $LATEST_REPORT/report.html"
            
            # Offer to open in browser if on desktop
            if command -v xdg-open &> /dev/null; then
                read -p "Open HTML report in browser? (y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    xdg-open "$LATEST_REPORT/report.html"
                fi
            elif command -v open &> /dev/null; then
                read -p "Open HTML report in browser? (y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    open "$LATEST_REPORT/report.html"
                fi
            fi
        fi
    fi
fi

exit $EXIT_CODE
