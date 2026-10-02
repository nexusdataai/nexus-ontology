# AI Job Engine - Integration Tests

## 📋 Overview

This directory contains comprehensive integration tests for the AI Job Engine, organized into shell-based and Python-based test suites. These tests verify the complete system functionality including MCP tools, REST APIs, and service layer operations.

## 🏗️ Directory Structure

```
tests/integration/
├── shell/                    # Shell-based integration tests
│   ├── common/              # Shared utilities for shell tests
│   │   └── test_utils.sh    # Common functions and helpers
│   ├── journey/             # Journey management tests
│   │   ├── test_crud_lifecycle.sh    # Complete CRUD lifecycle
│   │   ├── test_mcp_http.sh          # MCP HTTP gateway tests
│   │   └── test_second_brain.sh      # Second Brain rules tests
│   ├── jobs/                # Job execution tests
│   │   ├── test_run_job.sh           # run_job action tests
│   │   └── test_job_inspection.sh    # Job inspection operations
│   ├── logs/                # Logs and reports tests
│   │   └── test_logs_tool.sh         # Logs tool tests
│   └── tools/               # Tool discovery tests
│       └── test_tool_availability.sh # Tool availability tests
├── python/                   # Python-based integration tests
│   ├── services/            # Service layer tests
│   │   └── test_journey_service_integration.py
│   ├── mcp/                 # MCP tool tests
│   │   ├── test_journey_tool_integration.py     # Journey tool tests
│   │   ├── test_journey_crud_integration.py     # CRUD lifecycle tests
│   │   ├── test_journey_jobs_integration.py     # Job operation tests
│   │   ├── test_logs_reports_integration.py     # Logs tool tests
│   │   └── test_tool_availability.py            # Tool discovery tests
│   ├── api/                 # REST API tests
│   │   └── test_journey_api_integration.py
│   ├── workflows/           # End-to-end workflow tests
│   └── performance/         # Performance tests
├── fixtures/                 # Test data and fixtures
├── utils/                    # Test utilities
├── conftest.py              # Pytest configuration
├── run_all_tests.sh         # Master test runner
├── requirements-test.txt    # Test dependencies
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.9+** installed
2. **Virtual environment** activated
3. **Server running** at http://localhost:8000
4. **AWS credentials** configured (or use mocked AWS)

### Install Dependencies

```bash
# Create virtual environment (if not exists)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r tests/integration/requirements-test.txt
```

### Run All Tests

```bash
# Run all integration tests
./tests/integration/run_all_tests.sh

# Run with specific server
./tests/integration/run_all_tests.sh --server http://staging:8000

# Run only shell tests
./tests/integration/run_all_tests.sh --shell-only

# Run only Python tests
./tests/integration/run_all_tests.sh --python-only

# Include performance tests
./tests/integration/run_all_tests.sh --performance

# Verbose output
./tests/integration/run_all_tests.sh --verbose
```

## 🧪 Test Categories

### Shell Integration Tests

Located in `shell/` directory, these tests use bash scripts with curl to test HTTP endpoints.

#### Journey Tests (`shell/journey/`)
- **test_crud_lifecycle.sh** - Complete CRUD operations with DynamoDB validation
- **test_mcp_http.sh** - MCP tool testing via HTTP endpoints
- **test_second_brain.sh** - Second Brain rules management (add, update, delete rules)

#### Job Tests (`shell/jobs/`)
- **test_run_job.sh** - Job execution with different trigger types (system, user, api)
- **test_job_inspection.sh** - Job inspection and reporting operations (dashboard, summary, comprehensive data)

#### Logs Tests (`shell/logs/`)
- **test_logs_tool.sh** - Logs and reports management (add, search, reports)

#### Tools Tests (`shell/tools/`)
- **test_tool_availability.sh** - Tool discovery, availability, and error handling

#### Running Individual Shell Tests

```bash
# Run specific shell test
./tests/integration/shell/journey/test_crud_lifecycle.sh

# Run with custom server
./tests/integration/shell/journey/test_mcp_http.sh http://staging:8000
```

### Python Integration Tests

Located in `python/` directory, these tests use pytest with async support.

#### Service Layer Tests (`python/services/`)
Tests direct service interactions with DynamoDB:
- Journey CRUD operations
- Stage management
- Rule management
- Export/Import functionality

#### MCP Tool Tests (`python/mcp/`)
Tests MCP tool functionality via HTTP gateway:
- **test_journey_tool_integration.py** - Journey tool operations
- **test_journey_crud_integration.py** - CRUD lifecycle with DynamoDB verification
- **test_journey_jobs_integration.py** - Job execution and inspection operations
- **test_logs_reports_integration.py** - Logs tool operations
- **test_tool_availability.py** - Tool discovery and error handling

#### REST API Tests (`python/api/`)
Tests REST API endpoints directly:
- CRUD operations
- Pagination and filtering
- Error handling
- Content negotiation

#### Running Python Tests

```bash
# Run all Python tests
pytest tests/integration/python -v

# Run specific test module
pytest tests/integration/python/services/test_journey_service_integration.py -v

# Run with markers
pytest tests/integration/python -m "not performance" -v

# Run in parallel (requires pytest-xdist)
pytest tests/integration/python -n auto -v

# Generate coverage report
pytest tests/integration/python --cov=src --cov-report=html
```

## 📊 Test Configuration

### Environment Variables

```bash
# Server configuration
export SERVER_URL=http://localhost:8000

# Test selection
export RUN_SHELL_TESTS=true
export RUN_PYTHON_TESTS=true
export RUN_PERFORMANCE_TESTS=false

# AWS configuration
export USE_MOCK_AWS=true
export AWS_REGION=us-east-1
export DYNAMODB_TABLE=TransformationSystem

# Output configuration
export VERBOSE=false
export JSON_OUTPUT=false
export GENERATE_REPORT=true
```

### Pytest Configuration

Configure via `pytest.ini` or command line:

```ini
[tool:pytest]
markers =
    integration: Integration test
    performance: Performance test
    slow: Slow running test
    requires_aws: Requires AWS services

testpaths = tests/integration/python
python_files = test_*.py
python_classes = Test*
python_functions = test_*

asyncio_mode = auto
```

## 🔧 Writing New Tests

### Shell Test Template

```bash
#!/bin/bash

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/test_utils.sh"

# Test configuration
TEST_NAME="my_test"

# Test function
test_my_feature() {
    start_test "My Feature Test"
    
    # Make API call
    local response=$(make_post_request "/endpoint" '{"key":"value"}')
    
    # Validate response
    if check_response_success "$response"; then
        log_success "Test passed"
        end_test "My Feature Test" "passed"
        return 0
    else
        log_error "Test failed"
        end_test "My Feature Test" "failed"
        return 1
    fi
}

# Main execution
main() {
    setup_test_environment "$TEST_NAME" "${1:-$DEFAULT_URL}"
    test_my_feature
    cleanup_test_environment
}

main "$@"
```

### Python Test Template

```python
import pytest
import asyncio

@pytest.mark.integration
class TestMyFeature:
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client, cleanup_manager):
        self.client = api_client
        self.cleanup = cleanup_manager
    
    @pytest.mark.asyncio
    async def test_my_feature(self):
        # Arrange
        test_data = {"key": "value"}
        
        # Act
        response = await self.client.post("/endpoint", json=test_data)
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
```

## 📈 Test Reports

After running tests, reports are generated in `logs/integration-tests/`:

- **JSON Report** - Machine-readable test results
- **HTML Report** - Human-readable test summary
- **Log File** - Detailed test execution logs

View HTML report:
```bash
open logs/integration-tests/*_report.html
```

## 🔍 Debugging Tests

### Enable Verbose Output

```bash
# Shell tests
export VERBOSE=true
export DEBUG=true

# Python tests
pytest tests/integration/python -vvv --tb=long
```

### Run Single Test

```bash
# Shell test
bash -x tests/integration/shell/journey/test_crud_lifecycle.sh

# Python test
pytest tests/integration/python/services/test_journey_service_integration.py::TestJourneyServiceIntegration::test_create_journey_with_dynamodb -vvv
```

### Check Server Logs

```bash
# View gateway logs
docker logs ai-job-engine -f

# View test logs
tail -f logs/integration-tests/*.log
```

## 🚦 CI/CD Integration

### GitHub Actions

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Start Services
      run: |
        docker-compose up -d
        ./gateway.sh start
    
    - name: Run Integration Tests
      run: |
        ./tests/integration/run_all_tests.sh --json > results.json
    
    - name: Upload Results
      uses: actions/upload-artifact@v2
      with:
        name: test-results
        path: |
          results.json
          logs/integration-tests/
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    stages {
        stage('Setup') {
            steps {
                sh 'docker-compose up -d'
                sh './gateway.sh start'
            }
        }
        
        stage('Integration Tests') {
            steps {
                sh './tests/integration/run_all_tests.sh'
            }
        }
        
        stage('Publish Results') {
            steps {
                publishHTML([
                    reportDir: 'logs/integration-tests',
                    reportFiles: '*_report.html',
                    reportName: 'Integration Test Report'
                ])
            }
        }
    }
    
    post {
        always {
            sh 'docker-compose down'
        }
    }
}
```

## ⚠️ Common Issues

### Server Not Responding
```bash
# Check server status
curl http://localhost:8000/health

# Start server
cd /opt/mycode/ptr/ai-job-engine
./gateway.sh start
```

### Permission Denied
```bash
# Make scripts executable
chmod +x tests/integration/**/*.sh
```

### Module Not Found
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r tests/integration/requirements-test.txt
```

### DynamoDB Connection Error
```bash
# Use mocked DynamoDB
export USE_MOCK_AWS=true

# Or configure AWS credentials
export AWS_REGION=us-east-1
aws configure
```

## 📚 Additional Resources

- [Integration Testing Guide](../../INTEGRATION_TESTING_GUIDE.md)
- [MCP Tool Documentation](../../testscripts/tool-data/README_MCP_TOOLS.md)
- [API Documentation](../../doc/api/README.md)
- [pytest Documentation](https://docs.pytest.org/)

## 🤝 Contributing

When adding new integration tests:

1. Follow the existing structure and naming conventions
2. Use appropriate markers (`@pytest.mark.integration`, etc.)
3. Add cleanup for any created resources
4. Update this README with new test descriptions
5. Ensure tests can run independently
6. Add appropriate logging and error messages

## 📝 License

Part of the AI Job Engine project.
