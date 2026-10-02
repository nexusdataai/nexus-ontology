#!/bin/bash
# ============================================================================
# LocalStack Test Automation Runner (Linux/macOS)
# ============================================================================
# Wrapper script for running LocalStack test automation on Unix systems.
# Passes all arguments to the Python runner module.
#
# Usage:
#   ./run-localstack-tests.sh [test_types] [options]
#
# Examples:
#   ./run-localstack-tests.sh all
#   ./run-localstack-tests.sh integration bdd
#   ./run-localstack-tests.sh all --upload
#   ./run-localstack-tests.sh bdd --tags smoke,regression
#   ./run-localstack-tests.sh endurance --duration 300
#   ./run-localstack-tests.sh all --skip-localstack --skip-gateway
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  LocalStack Test Automation Runner"
echo "============================================"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check if uv is available
USE_UV=false
if command -v uv &> /dev/null; then
    USE_UV=true
fi

# Build and execute command
if [ "$USE_UV" = true ]; then
    echo "Running: uv run python -m tests.localstack_automation.runner $@"
    echo ""
    uv run python -m tests.localstack_automation.runner "$@"
else
    echo "Note: 'uv' not found, using python directly"
    echo "Running: python -m tests.localstack_automation.runner $@"
    echo ""
    python -m tests.localstack_automation.runner "$@"
fi

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test run completed successfully"
else
    echo "❌ Test run failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
