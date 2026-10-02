# AI Job Engine Test Suite

## Overview

This directory contains the comprehensive test suite for the AI Job Engine, organized by test type to provide complete coverage from unit tests to end-to-end integration tests.

**Test Pass Rate**: 100% ✅  
**Total Test Coverage**: Unit + BDD + Integration tests

## Test Structure

```
tests/
├── unit/                              # Unit tests (isolated component testing)
│   ├── journey/                       # Journey management unit tests
│   │   ├── test_journey_model.py
│   │   ├── test_journeys.py
│   │   ├── test_run_jobs.py
│   │   ├── test_logs_and_reports_model.py
│   │   └── test_logs_and_reports_service.py
│   │
│   ├── capability/                    # Capability management unit tests
│   │   ├── test_capability.py
│   │   ├── test_components.py
│   │   ├── test_implementation_jobs.py
│   │   ├── test_performance_metrics.py
│   │   └── test_all.py
│   │
│   └── call_process/                  # ✨ Call-process stage unit tests
│       ├── conftest.py                # Mock fixtures (WXCC API, S3, DynamoDB)
│       ├── test_call_processor.py     # CallProcessor class tests
│       └── test_call_process_stage.py # CallProcessStage class tests
│
├── bdd/                               # Behavior-Driven Development tests
│   ├── features/                      # Feature files (Gherkin)
│   │   ├── journey/                   # Journey features
│   │   │   ├── journey_management.feature
│   │   │   ├── stage_management.feature
│   │   │   ├── rules_management.feature
│   │   │   └── job_execution.feature
│   │   │
│   │   ├── capability/                # Capability features
│   │   │   └── (feature files)
│   │   │
│   │   └── call_process/              # ✨ Call-process BDD features
    │   │       ├── call_processing.feature     # Task fetch, dedup, recording, metadata
    │   │       ├── call_analysis.feature       # AI analysis, compliance, sentiment
    │   │       └── live_call_processing.feature # 🔴 Live end-to-end tests
│   │
│   ├── steps/                         # Step definitions
│   │   ├── common_steps.py            # Shared steps for all domains
│   │   ├── journey/                   # Journey-specific steps
│   │   │   ├── journey_steps.py
│   │   │   └── stage_steps.py
│   │   │
│   │   ├── capability/                # Capability-specific steps
│   │   │   └── (step files)
│   │   │
│   │   ├── call_process_steps.py       # ✨ Call-process step definitions (mocked)
    │   │   └── live_call_process_steps.py  # 🔴 Live call-process steps (real services)
│   │
│   ├── support/                       # Shared BDD utilities
│   │   ├── cli_wrapper.py
│   │   ├── mock_cli_manager.py
│   │   ├── test_cli_adapter.py
│   │   ├── aws_mock_manager.py
│   │   └── test_data_manager.py
│   │
│   └── environment.py                 # BDD configuration
│
├── integration/                       # ✨ Integration tests (end-to-end)
│   ├── shell/                         # Shell script integration tests
│   │   ├── common/                    # Common test utilities
│   │   │   └── test_utils.sh          # Shared bash functions
│   │   ├── journey/                   # Journey integration tests
│   │   │   ├── test_crud_lifecycle.sh
│   │   │   ├── test_mcp_http.sh
│   │   │   ├── test_second_brain.sh
│   │   │   └── test_basic_journey.sh
│   │   ├── jobs/                      # Job operation tests
│   │   │   ├── test_run_job.sh
│   │   │   └── test_job_inspection.sh
│   │   ├── logs/                      # Logs and reports tests
│   │   │   └── test_logs_tool.sh
│   │   └── tools/                     # Tool validation tests
│   │       └── test_tool_availability.sh
│   │
│   ├── python/                        # Python integration tests
│   │   ├── mcp/                       # MCP tool integration
│   │   │   ├── test_journey_crud_integration.py
│   │   │   ├── test_journey_jobs_integration.py
│   │   │   ├── test_logs_reports_integration.py
│   │   │   ├── test_tool_availability.py
│   │   │   └── test_journey_tool_integration.py
│   │   ├── api/                       # REST API integration
│   │   └── workflows/                 # End-to-end workflows
│   │
│   ├── call_process/                  # ✨ Call-process integration tests
    │   │   ├── conftest.py                    # Moto-based AWS mocks + live fixtures
    │   │   ├── test_call_process_integration.py # Mocked integration tests
    │   │   └── test_live_call_processing.py   # 🔴 Live end-to-end tests (--run-live)
│   │
│   ├── fixtures/                      # Test fixtures
│   ├── conftest.py                    # Pytest configuration
│   ├── run_integration_tests.sh       # ✨ Main integration test runner
│   ├── MIGRATION_STATUS.md            # ✨ Migration documentation
│   └── README.md                      # Integration test guide
│
├── endurance/                         # Endurance/stress tests
│   ├── call_process_config.yaml       # ✨ Call-process endurance config
│   └── (other endurance test files)
│
├── run_tests.sh                       # Main test runner script
├── conftest.py                        # Root pytest configuration
├── requirements-test.txt              # Test dependencies
└── README.md                          # This file
```

## Test Types Explained

### 1. Unit Tests (`unit/`)
**Purpose**: Test individual components in isolation with mocked dependencies

**Characteristics**:
- Fast execution (milliseconds)
- Isolated (no external dependencies)
- Mock AWS services (using moto)
- Focus on business logic

**Run**:
```bash
pytest tests/unit/ -v
```

### 2. BDD Tests (`bdd/`)
**Purpose**: Test user behavior and scenarios using Gherkin (Given/When/Then)

**Characteristics**:
- Human-readable scenarios
- Acceptance criteria validation
- Cross-component workflows
- Business stakeholder friendly

**Run**:
```bash
cd tests/bdd && behave
```

### 3. Integration Tests (`integration/`) ✨ NEW
**Purpose**: Test complete system with real AWS services and MCP protocol

**Characteristics**:
- Real AWS DynamoDB access
- Complete HTTP/MCP protocol testing
- End-to-end workflows
- Hybrid shell + Python approach
- **100% pass rate** (9/9 tests)

**Run**:
```bash
cd tests/integration
./run_integration_tests.sh
```

**Report Output**:
- Console output (real-time)
- JSON report (`logs/integration-tests/`)
- HTML report (`test_reports/integration/`) ✨ NEW

### 4. Live Tests 🔴 NEW
**Purpose**: Test against real Webex CC and AWS services

**Characteristics**:
- Uses real AWS services (S3, DynamoDB, Glue, Athena)
- Connects to real or simulated Webex CC
- Validates end-to-end data flow
- Requires valid credentials

**Run pytest**:
```bash
pytest tests/integration/call_process/test_live_call_processing.py -v --run-live
```

**Run BDD**:
```bash
BEHAVE_RUN_LIVE=true behave tests/bdd/features/call_process/live_call_processing.feature --tags=@live
```

### 5. Endurance Tests (`endurance/`)
**Purpose**: Test system stability under sustained load

**Characteristics**:
- Long-running tests
- High volume operations
- Resource monitoring
- Stress testing

---

## Running Tests

### Quick Start

```bash
# Run all unit tests
./run_tests.sh unit

# Run all BDD tests
./run_tests.sh bdd

# Run all integration tests (with HTML reports!)
cd integration && ./run_integration_tests.sh
```

### Integration Tests (Recommended for End-to-End Validation)

The integration test suite is the most comprehensive, testing the complete system:

```bash
cd /opt/mycode/ptr/ai-job-engine/tests/integration

# Run all integration tests
./run_integration_tests.sh

# Run with custom server URL
SERVER_URL=http://192.168.1.100:8000 ./run_integration_tests.sh

# Run with timeout (default 60s)
TEST_TIMEOUT=120 ./run_integration_tests.sh

# Skip shell tests
SKIP_SHELL_TESTS=true ./run_integration_tests.sh

# Skip Python tests
SKIP_PYTHON_TESTS=true ./run_integration_tests.sh

# Verbose mode
VERBOSE=true ./run_integration_tests.sh
```

**Output**:
```
📊 Test Summary
  Total Tests:    9
  Passed:         9
  Failed:         0
  Pass Rate:      100%

📊 HTML report saved to:
   test_reports/integration/integration_test_report_20251203_154346.html
✅ All integration tests passed!
```

### Unit Tests

```bash
# All unit tests
pytest tests/unit/ -v

# Journey unit tests
pytest tests/unit/journey/ -v

# Capability unit tests
pytest tests/unit/capability/ -v

# Specific test file
pytest tests/unit/journey/test_journey_model.py -v

# With coverage
pytest tests/unit/ --cov=src --cov-report=html
```

### BDD Tests

```bash
# All BDD tests
cd tests/bdd && behave

# Journey BDD tests
cd tests/bdd && behave features/journey/

# Specific feature
cd tests/bdd && behave features/journey/journey_management.feature

# With tags
cd tests/bdd && behave --tags=@critical
```

### Call-Process Tests ✨ NEW

Use the main test runner for call-process tests:

```bash
# All call-process tests (unit + integration + BDD)
./run_tests.sh call-process

# Call-process unit tests only
./run_tests.sh call-process-unit

# Call-process integration tests only
./run_tests.sh call-process-integration

# Call-process BDD tests only
./run_tests.sh call-process-bdd

# Call-process endurance tests
./run_tests.sh call-process-endurance
```

Or run directly with pytest/behave:

```bash
# Unit tests
pytest tests/unit/call_process/ -v

# Integration tests
pytest tests/integration/call_process/ -v

# BDD tests
behave tests/bdd/features/call_process/

# BDD with specific tags
behave tests/bdd/features/call_process/ --tags=@call_process
behave tests/bdd/features/call_process/ --tags=@analysis

# With coverage
pytest tests/unit/call_process/ --cov=src/stages/call-process --cov-report=html
```

### Live Tests (Real Webex CC + AWS Services) 🔴 NEW

Live tests run against actual Webex CC (or simulator) and real AWS services:

```bash
# Live pytest integration tests
pytest tests/integration/call_process/test_live_call_processing.py -v --run-live

# Live BDD tests
BEHAVE_RUN_LIVE=true behave tests/bdd/features/call_process/live_call_processing.feature --tags=@live

# Specific live scenarios
BEHAVE_RUN_LIVE=true behave tests/bdd/features/call_process/live_call_processing.feature --tags=@live --tags=@smoke
BEHAVE_RUN_LIVE=true behave tests/bdd/features/call_process/live_call_processing.feature --tags=@live --tags=@complete
```

**Available Live BDD Tags**:
| Tag | Description |
|-----|-------------|
| `@live` | All live tests (required) |
| `@smoke` | Connectivity smoke test (Webex, S3, DynamoDB) |
| `@fetch` | Fetch tasks from Webex CC |
| `@dedup` | Deduplication testing |
| `@process` | Recording processing with transcription |
| `@metadata` | Glue registration |
| `@analysis` | AI analysis on transcripts |
| `@complete` | Full lifecycle test |
| `@verify` | S3 artifact verification |
| `@athena` | Athena query verification |
| `@slow` | Long-running tests |

**Live Test Prerequisites**:
- Valid AWS credentials (run `aws-login.sh` if needed)
- `.env` configured in `scripts/call-scripts/.env`
- Backend server running (for simulator mode)
- OpenAI API key (for AI analysis tests)

---

## Test Coverage

### Integration Tests (100% Pass Rate) ✅

**Shell Tests (8 tests)**:
- Journey CRUD lifecycle (create, read, update, delete)
- MCP HTTP operations
- Second Brain rules management
- Basic journey operations & error handling
- Job execution
- Job inspection operations
- Logs and reports (26/26 operations tested)
- Tool availability validation

**Python Tests (1 suite)**:
- Journey creation via MCP tool
- REST API operations (if available)
- Stage workflows
- Concurrent operations
- Error handling
- Export/import functionality

**Coverage Areas**:
- ✅ Journey CRUD operations
- ✅ Stage orchestration
- ✅ Rule management (Second Brain)
- ✅ Job execution and inspection
- ✅ Logs and reports (all 26 operations)
- ✅ Tool discovery and validation
- ✅ Error handling
- ✅ MCP protocol compliance
- ✅ Concurrent operations
- ✅ Export/import

### Unit Tests

**Journey Unit Tests**:
- Data model validation (Pydantic models)
- Service layer business logic
- Job execution logic
- Logging and reporting

**Capability Unit Tests**:
- CRUD operations
- Component management
- Job lifecycle
- Performance metrics

### Call-Process Tests ✨ NEW

The call-process stage has comprehensive tests for Webex CC call processing:

**Unit Tests** (`tests/unit/call_process/`):
- `TestCallProcessConfig` - Configuration handling
- `TestCallProcessor` - Core processor logic (fetch, dedup, process, analyze)
- `TestCallProcessStage` - Stage integration with journey system
- Error handling and edge cases

**Integration Tests** (`tests/integration/call_process/`):
- `test_call_process_integration.py` - Mocked integration tests with moto
- `test_live_call_processing.py` 🔴 - Live end-to-end tests (use `--run-live`)
  - `TestLiveCallProcessingLifecycle` - Step-by-step lifecycle testing
  - `TestLiveCompleteLifecycle` - Full pipeline in one test
  - `TestLiveS3Verification` - S3 artifact verification
  - `TestLiveAthenaQuery` - Athena query verification
  - `test_live_smoke_test` - Quick connectivity check

**BDD Tests** (`tests/bdd/features/call_process/`):
- `call_processing.feature` - 16 scenarios for task fetch, dedup, recording processing
- `call_analysis.feature` - 16 scenarios for AI analysis, compliance, sentiment
- `live_call_processing.feature` 🔴 - 11 live scenarios (use `BEHAVE_RUN_LIVE=true`)
  - Smoke test (Webex, S3, DynamoDB connectivity)
  - Complete lifecycle test
  - Error recovery scenarios
  - Performance testing

**Endurance Tests** (`tests/endurance/call_process_config.yaml`):
- 30-minute default run
- Weighted test distribution (40% recording, 20% analysis, etc.)
- Presets: quick (5min), stress (60min), stability (3hr), soak (8hr)

### BDD Tests

**Journey BDD Tests**:
- Complete journey lifecycle scenarios
- Stage management workflows
- Rule application scenarios
- Job execution workflows

---

## HTML Test Reports ✨ NEW

Integration tests automatically generate beautiful HTML reports on every run.

### Viewing Reports

```bash
# Open latest report
open /opt/mycode/ptr/ai-job-engine/test_reports/integration/integration_test_report_*.html

# Or with specific browser
firefox /opt/mycode/ptr/ai-job-engine/test_reports/integration/integration_test_report_*.html
```

### Report Features

- **Modern UI**: Gradient design with responsive layout
- **Visual Metrics**: Large, easy-to-read statistics
- **Progress Bar**: Color-coded pass rate visualization
- **Test Categories**: Organized by functionality
- **Failed Tests**: Detailed list (if any)
- **Shareable**: Send to team members or stakeholders

### Report Location

```
/opt/mycode/ptr/ai-job-engine/test_reports/integration/
└── integration_test_report_YYYYMMDD_HHMMSS.html
```

See [`test_reports/README.md`](../test_reports/README.md) for more details.

---

## AWS Credential Management ✨ NEW

Integration tests require valid AWS credentials. The system supports **zero-downtime credential refresh**:

### Before Running Tests

```bash
# Login to AWS (if needed)
cd /opt/mycode/ptr/ai-job-engine
./aws-login.sh

# Start the gateway
./gateway.sh start
```

### If Credentials Expire During Testing

```bash
# Refresh without restarting gateway
./refresh-aws-credentials.sh

# Or via API
curl -X POST http://localhost:8000/admin/refresh-aws-credentials \
  -H "x-api-key: super-secret"

# Then continue testing (no restart needed!)
```

See [`docs/AWS_CREDENTIALS_REFRESH.md`](../docs/AWS_CREDENTIALS_REFRESH.md) for complete guide.

---

## Environment Setup

### Prerequisites

```bash
# Python 3.11+ required
python --version

# Install test dependencies
pip install -r tests/requirements-test.txt

# For integration tests specifically
pip install -r tests/integration/requirements-test.txt
```

### Environment Variables

```bash
# For unit/BDD tests
export AWS_REGION=us-east-1
export TABLE_NAME=test_table
export PYTHONPATH=/opt/mycode/ptr/ai-job-engine:$PYTHONPATH

# For integration tests
export SERVER_URL=http://localhost:8000
export API_KEY=super-secret
export TEST_TIMEOUT=60
```

### AWS Configuration

Integration tests require AWS credentials:

```bash
# Configure AWS credentials
./aws-login.sh

# Or use environment variables
export AWS_ROLE_ARN=arn:aws:iam::ACCOUNT:role/ROLE_NAME
export AWS_REGION=us-east-2
export AWS_PROFILE=default
```

---

## Test Migration Status ✨

**Migration Complete**: December 3, 2025

All tests have been migrated from the legacy `testscripts/` directory to the unified `tests/integration/` structure.

### What Changed

**Before**:
- Tests in `testscripts/` (legacy location)
- Scattered organization
- No HTML reports

**After**:
- All tests in `tests/integration/` (unified location)
- Clear categorization by functionality
- Beautiful HTML reports auto-generated
- 100% test pass rate

### Legacy Directory

The `testscripts/` directory is now **legacy/reference only**:
- ✅ Original tests kept for reference
- ✅ Utility scripts still available
- ✅ Clear legacy notice: [`testscripts/README_LEGACY.md`](../testscripts/README_LEGACY.md)
- ❌ Do not add new tests there

See [`integration/MIGRATION_STATUS.md`](integration/MIGRATION_STATUS.md) for complete details.

---

## Running Different Test Suites

### 1. Unit Tests (Fast, Isolated)

**When to use**: Development, quick validation, CI/CD

```bash
# All unit tests
pytest tests/unit/ -v

# Journey tests only
pytest tests/unit/journey/ -v

# Capability tests only
pytest tests/unit/capability/ -v

# With coverage
pytest tests/unit/ --cov=src --cov-report=html

# Specific test
pytest tests/unit/journey/test_journeys.py::test_create_journey -v
```

**Execution Time**: ~5-30 seconds

### 2. BDD Tests (Human-Readable Scenarios)

**When to use**: Acceptance testing, stakeholder validation

```bash
# All BDD tests
cd tests/bdd && behave

# Journey scenarios
cd tests/bdd && behave features/journey/

# Specific feature
cd tests/bdd && behave features/journey/journey_management.feature

# Tagged scenarios
cd tests/bdd && behave --tags=@critical
cd tests/bdd && behave --tags=@smoke

# With verbose output
cd tests/bdd && behave -v
```

**Execution Time**: ~30-60 seconds

### 3. Integration Tests (Complete System Testing) ⭐ RECOMMENDED

**When to use**: Pre-deployment validation, system verification, regression testing

```bash
cd /opt/mycode/ptr/ai-job-engine/tests/integration

# Run all integration tests (generates HTML report)
./run_integration_tests.sh

# With custom configuration
SERVER_URL=http://10.0.0.3:8000 \
TEST_TIMEOUT=120 \
VERBOSE=true \
./run_integration_tests.sh

# Skip specific test types
SKIP_SHELL_TESTS=true ./run_integration_tests.sh
SKIP_PYTHON_TESTS=true ./run_integration_tests.sh
```

**Execution Time**: ~60-90 seconds

**Generates 3 Report Formats**:
1. Console output (real-time)
2. JSON report (`logs/integration-tests/`)
3. **HTML report** (`test_reports/integration/`) ✨

### 4. All Tests (Complete Validation)

```bash
# Run everything
cd /opt/mycode/ptr/ai-job-engine

# Unit tests
pytest tests/unit/ -v

# BDD tests
cd tests/bdd && behave && cd ../..

# Integration tests
cd tests/integration && ./run_integration_tests.sh && cd ../..
```

---

## Test Categories

### Unit Tests

#### Journey Unit Tests (`unit/journey/`)
- **test_journey_model.py**: Pydantic model validation
- **test_journeys.py**: Journey service business logic
- **test_run_jobs.py**: Job execution logic
- **test_logs_and_reports_model.py**: Logging model validation
- **test_logs_and_reports_service.py**: Logging service logic

#### Capability Unit Tests (`unit/capability/`)
- **test_capability.py**: Capability CRUD operations
- **test_components.py**: Component management
- **test_implementation_jobs.py**: Job lifecycle management
- **test_performance_metrics.py**: Metrics and monitoring
- **test_all.py**: Comprehensive test runner

### BDD Tests

#### Journey BDD Tests (`bdd/features/journey/`)
- **journey_management.feature**: Complete journey lifecycle
- **stage_management.feature**: Stage operations
- **rules_management.feature**: Second Brain rules
- **job_execution.feature**: Job execution workflows

### Integration Tests ✨

#### Shell Tests (`integration/shell/`)

**Journey Tests (4)**:
- **test_crud_lifecycle.sh**: Complete CRUD operations with DynamoDB verification
- **test_mcp_http.sh**: All MCP HTTP operations and actions
- **test_second_brain.sh**: Second Brain rule management
- **test_basic_journey.sh**: Basic operations and error handling

**Job Tests (2)**:
- **test_run_job.sh**: Job execution workflows
- **test_job_inspection.sh**: Job inspection operations

**Logs Tests (1)**:
- **test_logs_tool.sh**: All 26 log and report operations

**Tool Tests (1)**:
- **test_tool_availability.sh**: Tool discovery and validation

#### Python Tests (`integration/python/`)

**MCP Integration Tests**:
- **test_journey_crud_integration.py**: Journey CRUD via MCP
- **test_journey_jobs_integration.py**: Job operations via MCP
- **test_logs_reports_integration.py**: Logs/reports via MCP
- **test_tool_availability.py**: Tool discovery via MCP
- **test_journey_tool_integration.py**: Journey tool comprehensive tests

**API Integration Tests**:
- **test_journey_api_integration.py**: REST API testing

---

## Test Runner Scripts

### Main Test Runner (`run_tests.sh`)

Unified runner for unit and BDD tests:

```bash
./run_tests.sh all          # All unit + BDD tests
./run_tests.sh unit         # All unit tests
./run_tests.sh bdd          # All BDD tests
./run_tests.sh journey      # Journey tests (unit + BDD)
./run_tests.sh capability   # Capability tests (unit + BDD)
./run_tests.sh coverage     # With coverage report
./run_tests.sh clean        # Clean test artifacts
```

### Integration Test Runner (`integration/run_integration_tests.sh`)

Comprehensive runner for integration tests with HTML report generation:

```bash
cd tests/integration
./run_integration_tests.sh

# Configuration options
SERVER_URL=http://localhost:8000     # Gateway URL
TEST_TIMEOUT=60                       # Test timeout (seconds)
SKIP_SHELL_TESTS=false               # Skip shell tests
SKIP_PYTHON_TESTS=false              # Skip Python tests
VERBOSE=false                         # Verbose output
```

**Features**:
- ✅ Automatic HTML report generation
- ✅ Multiple report formats (console, JSON, HTML)
- ✅ Test categorization
- ✅ Timeout handling
- ✅ Failed test tracking
- ✅ Health check validation

---

## Test Reports

### HTML Reports (Integration Tests Only)

Beautiful, professional HTML reports are automatically generated for integration tests.

**Location**: `/opt/mycode/ptr/ai-job-engine/test_reports/integration/`

**View Reports**:
```bash
# Open latest report
open test_reports/integration/integration_test_report_*.html

# List all reports
ls -lt test_reports/integration/*.html
```

**Report Contains**:
- Overall status banner (green/red)
- Visual metrics dashboard
- Progress bar (color-coded)
- Test categorization
- Failed test details (if any)
- Test information (date, server, log file)

### JSON Reports

Machine-readable reports for CI/CD:

**Location**: `logs/integration-tests/integration_test_report_TIMESTAMP.json`

```bash
# View JSON report
jq . logs/integration-tests/integration_test_report_*.json | head -20
```

### Coverage Reports (Unit Tests)

```bash
# Generate HTML coverage report
pytest tests/unit/ --cov=src --cov-report=html

# View coverage
open htmlcov/index.html
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Unit Tests
        run: |
          cd tests
          ./run_tests.sh unit
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup AWS
        run: ./aws-login.sh
      
      - name: Start Gateway
        run: ./gateway.sh start
      
      - name: Run Integration Tests
        run: |
          cd tests/integration
          ./run_integration_tests.sh
      
      - name: Upload HTML Report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: integration-test-report
          path: test_reports/integration/*.html
```

### GitLab CI

```yaml
test:
  script:
    - cd tests/integration
    - ./run_integration_tests.sh
  
  artifacts:
    when: always
    paths:
      - test_reports/integration/*.html
      - logs/integration-tests/*.json
```

---

## Writing New Tests

### Adding Unit Tests

1. Create test file in appropriate domain folder
2. Follow naming convention: `test_*.py`
3. Use pytest fixtures from `conftest.py`
4. Mock external dependencies (AWS, etc.)

**Example**:
```python
# tests/unit/journey/test_new_feature.py
import pytest
from src.services.journey_service import JourneyService

def test_new_feature():
    service = JourneyService()
    result = service.new_feature()
    assert result is not None
```

### Adding BDD Tests

1. Create feature file in appropriate domain folder
2. Write scenarios in Gherkin syntax
3. Implement step definitions
4. Reuse common steps when possible

**Example**:
```gherkin
# tests/bdd/features/journey/new_feature.feature
Feature: New Feature
  Scenario: Test new functionality
    Given a journey exists
    When I execute new feature
    Then the result should be successful
```

### Adding Integration Tests

#### Shell Integration Tests

1. Create test file in appropriate category folder
2. Source common utilities: `source "$SCRIPT_DIR/../common/test_utils.sh"`
3. Follow existing patterns
4. Use helper functions for API calls

**Example**:
```bash
# tests/integration/shell/journey/test_new_feature.sh
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/test_utils.sh"

test_new_feature() {
    start_test "New Feature"
    local response=$(make_post_request "/tools/journeys_tool" '{"action":"new_action"}')
    
    if check_response_success "$response"; then
        log_success "New feature works"
        end_test "New Feature" "passed"
        return 0
    else
        log_error "New feature failed"
        end_test "New Feature" "failed"
        return 1
    fi
}

main() {
    setup_test_environment
    test_new_feature
}

main "$@"
```

#### Python Integration Tests

1. Create test file in `python/mcp/` or `python/api/`
2. Use async/await patterns
3. Use fixtures from `conftest.py`
4. Follow existing test patterns

**Example**:
```python
# tests/integration/python/mcp/test_new_feature.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_new_feature(client: AsyncClient):
    response = await client.post("/tools/journeys_tool", 
        json={"arguments": {"action": "new_action"}})
    assert response.status_code == 200
```

---

## Shared Components

### Integration Test Utilities (`integration/shell/common/test_utils.sh`)

**Available Functions**:
- `setup_test_environment()` - Initialize test environment
- `make_post_request()` - Make HTTP POST request
- `make_get_request()` - Make HTTP GET request  
- `check_response_success()` - Check if response is successful
- `check_response_error()` - Check if response is error
- `get_json_field()` - Extract JSON field from response
- `get_error_message()` - Extract error message
- `journey_exists_in_dynamodb()` - Check journey in DynamoDB
- `log_info()`, `log_success()`, `log_error()`, `log_warning()` - Logging functions
- `start_test()`, `end_test()` - Test lifecycle management
- `print_test_header()` - Formatted headers
- And many more...

### BDD Support (`bdd/support/`)

**Shared Utilities**:
- `cli_wrapper.py` - Wraps CLI commands for testing
- `mock_cli_manager.py` - Mock CLI functionality
- `test_cli_adapter.py` - Adapter for different interfaces
- `aws_mock_manager.py` - AWS service mocking
- `test_data_manager.py` - Test data management

### Common Steps (`bdd/steps/common_steps.py`)

Reusable step definitions across all BDD features.

---

## Test Requirements

### Required Software

- Python 3.11+
- pytest 8.4+
- behave (for BDD tests)
- httpx (for async HTTP clients)
- boto3 (for AWS integration)
- jq (for shell tests)
- curl (for shell tests)
- aws-cli (for integration tests)

### Required Services

**For Integration Tests**:
- AI Job Engine Gateway running on `http://localhost:8000`
- AWS DynamoDB access (TransformationSystem table)
- Valid AWS credentials

**For Unit/BDD Tests**:
- No external services required (uses mocking)

---

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
export PYTHONPATH=/opt/mycode/ptr/ai-job-engine:$PYTHONPATH
```

#### 2. Missing Dependencies
```bash
pip install -r tests/requirements-test.txt
pip install -r tests/integration/requirements-test.txt
```

#### 3. AWS Credential Issues
```bash
# For integration tests
./aws-login.sh
./refresh-aws-credentials.sh

# For unit tests (use mocking)
# No real AWS credentials needed
```

#### 4. Gateway Not Running
```bash
# Check if gateway is running
curl http://localhost:8000/health

# Start gateway
./gateway.sh start

# Restart if needed
./gateway.sh restart
```

#### 5. Integration Tests Failing
```bash
# Check AWS credentials
aws sts get-caller-identity

# Refresh credentials
./refresh-aws-credentials.sh

# Check gateway health
curl http://localhost:8000/health

# View detailed logs
tail -f logs/integration-tests/integration_test_run_*.log
```

#### 6. BDD Step Not Found
- Check step definition file is in correct location
- Verify step regex matches feature file exactly
- Ensure `environment.py` loads all step files

#### 7. Live Tests Skipped or Failing 🔴
```bash
# Check AWS credentials
aws sts get-caller-identity

# Refresh if expired
./aws-login.sh

# Check .env configuration
cat scripts/call-scripts/.env | grep -E "^(AWS_|WXCC_|OPENAI_)"

# Ensure backend is running (for simulator mode)
curl http://localhost:8000/health

# Run with verbose output
pytest tests/integration/call_process/test_live_call_processing.py -v --run-live -s
BEHAVE_RUN_LIVE=true behave tests/bdd/features/call_process/live_call_processing.feature --tags=@live -v
```

#### 8. Live Tests - ExpiredToken Errors
Live tests gracefully skip when AWS tokens expire:
```bash
# Refresh AWS credentials
./aws-login.sh

# Or use the refresh script
./refresh-aws-credentials.sh

# Re-run tests
pytest tests/integration/call_process/test_live_call_processing.py -v --run-live
```

---

## Test Best Practices

### For All Tests
- ✅ Test one thing per test function/scenario
- ✅ Use descriptive test names
- ✅ Clean up test data after tests
- ✅ Use fixtures for setup/teardown
- ✅ Mock external dependencies when possible

### For Unit Tests
- ✅ Test in isolation (mock dependencies)
- ✅ Fast execution (<100ms per test)
- ✅ High coverage (aim for 80%+)
- ✅ Test edge cases and errors

### For BDD Tests
- ✅ Write from user perspective
- ✅ Use business language (not technical)
- ✅ Keep scenarios focused
- ✅ Reuse common steps

### For Integration Tests
- ✅ Test real workflows
- ✅ Use real services (DynamoDB, etc.)
- ✅ Clean up created resources
- ✅ Check both API response and database state
- ✅ Test error handling thoroughly

---

## Test Execution Matrix

| Test Type | Speed | Coverage | Dependencies | Use Case |
|-----------|-------|----------|--------------|----------|
| Unit | Fast (5-30s) | High | None (mocked) | Development, CI/CD |
| BDD | Medium (30-60s) | Medium | None (mocked) | Acceptance testing |
| Integration | Slower (60-90s) | Complete | Gateway + AWS | Pre-deployment, Regression |
| **Live** 🔴 | Medium (5-10s) | Complete | Real AWS + Webex | System validation |
| Endurance | Very slow (minutes) | Stress | Gateway + AWS | Performance validation |

### Running Live Tests

**Prerequisites**:
```bash
# Ensure AWS credentials are valid
aws sts get-caller-identity

# Ensure .env is configured
cat scripts/call-scripts/.env | grep -E "^(AWS_|WXCC_|OPENAI_)"
```

**pytest Live Tests**:
```bash
# All live tests
pytest tests/integration/call_process/test_live_call_processing.py -v --run-live

# Smoke test only
pytest tests/integration/call_process/test_live_call_processing.py::test_live_smoke_test -v --run-live

# Full lifecycle
pytest tests/integration/call_process/test_live_call_processing.py::TestLiveCompleteLifecycle -v --run-live
```

**BDD Live Tests**:
```bash
# All live scenarios
BEHAVE_RUN_LIVE=true behave tests/bdd/features/call_process/live_call_processing.feature --tags=@live

# Smoke test
BEHAVE_RUN_LIVE=true behave tests/bdd/features/call_process/live_call_processing.feature --tags=@live --tags=@smoke

# Complete lifecycle
BEHAVE_RUN_LIVE=true behave tests/bdd/features/call_process/live_call_processing.feature --tags=@live --tags=@complete
```

---

## Test Data Management

### Unit Tests
- Use in-memory data
- Mock AWS responses
- Test data in test files

### BDD Tests
- Test data in `support/test_data_manager.py`
- Reusable scenarios
- Mock external services

### Integration Tests
- Real DynamoDB data (cleaned up after tests)
- Real journey/job/stage records
- Auto-generated test data with timestamps
- Cleanup on test completion

---

## Continuous Integration

### Pre-Commit Testing

```bash
# Before committing code
pytest tests/unit/ -v                   # Fast validation
cd tests/integration && ./run_integration_tests.sh  # Full validation
```

### CI Pipeline Stages

**Stage 1: Fast Tests**
```bash
pytest tests/unit/ -v --tb=short
```

**Stage 2: Acceptance Tests**
```bash
cd tests/bdd && behave
```

**Stage 3: Integration Tests**
```bash
cd tests/integration && ./run_integration_tests.sh
```

**Stage 4: Generate Reports**
- HTML reports auto-generated
- Upload as CI artifacts
- Publish to GitHub Pages (optional)

---

## Performance

### Test Execution Times

- **Unit Tests**: ~5-30 seconds (800+ tests)
- **BDD Tests**: ~30-60 seconds (50+ scenarios)
- **Integration Tests**: ~60-90 seconds (9 test suites, 26+ operations)
- **Full Suite**: ~2-3 minutes total

### Optimization Tips

- Run unit tests frequently (fast feedback)
- Run integration tests before PRs (complete validation)
- Use test markers to run subsets: `pytest -m "not slow"`
- Parallel execution: `pytest -n auto`

---

## Related Documentation

### Test Documentation
- [`integration/README.md`](integration/README.md) - Integration test guide
- [`integration/MIGRATION_STATUS.md`](integration/MIGRATION_STATUS.md) - Migration details
- [`test_reports/README.md`](../test_reports/README.md) - Report documentation

### System Documentation
- [Main README](../README.md) - Project overview
- [`docs/AWS_CREDENTIALS_REFRESH.md`](../docs/AWS_CREDENTIALS_REFRESH.md) - Credential management
- [`testscripts/README_LEGACY.md`](../testscripts/README_LEGACY.md) - Legacy test location

---

## Contributing

When adding new tests:

1. **Choose the right test type**:
   - Unit: Fast, isolated component testing
   - BDD: User scenarios and acceptance criteria
   - Integration: End-to-end system testing

2. **Place in correct location**:
   - Unit: `tests/unit/{domain}/`
   - BDD: `tests/bdd/features/{domain}/`
   - Integration: `tests/integration/shell/{category}/` or `tests/integration/python/`

3. **Follow conventions**:
   - Naming: `test_*.py` or `test_*.sh`
   - Documentation: Update README with new test descriptions
   - Utilities: Reuse existing helper functions

4. **Ensure quality**:
   - Tests pass locally before committing
   - Add appropriate markers/tags
   - Include error handling
   - Clean up test data

---

## Support

For questions or issues:

1. Check this README for guidance
2. Review integration test guide: [`integration/README.md`](integration/README.md)
3. Check test logs in `logs/` directory
4. Review HTML reports in `test_reports/integration/`
5. Consult main project README

---

**Last Updated**: December 21, 2025  
**Test Pass Rate**: 100% (all test types)  
**Integration Tests**: 9/9 passing  
**Live Tests**: pytest + BDD with `--run-live` / `BEHAVE_RUN_LIVE=true` 🔴  
**HTML Reports**: Auto-generated ✅
