# Capability Management System - Unit Tests

## Overview

This directory contains comprehensive unit tests for the Business Capability Management System. The tests cover all scripts in `/scripts/capability-scripts/` and ensure proper functionality of capability management, component management, job execution, and performance metrics tracking.

## Test Structure

```
tests/unit/capability/
├── __init__.py                          # Package initialization
├── conftest.py                          # Shared pytest fixtures
├── test_manage_capability.py            # Tests for capability management
├── test_manage_components.py            # Tests for component management  
├── test_manage_implementation_jobs.py   # Tests for job management
├── test_manage_performance_metrics.py   # Tests for metrics management
├── run_tests.py                         # Test runner script
└── README.md                            # This file
```

## Test Coverage

### 1. test_manage_capability.py
**Module Tested**: `manage_capability.py`
- **Classes**: `CapabilityManager`, `InteractiveCapabilityWizard`
- **Test Cases**: 25+ tests
- **Coverage Areas**:
  - CRUD operations for capabilities
  - Health score calculation
  - Component associations
  - Search and filtering
  - Business domain management
  - Error handling

### 2. test_manage_components.py  
**Module Tested**: `manage_components.py`
- **Classes**: `ComponentManager`, `InteractiveComponentWizard`
- **Test Cases**: 25+ tests
- **Coverage Areas**:
  - Component CRUD operations
  - Dependency management
  - Health monitoring
  - Configuration management
  - Artifact storage (S3)
  - Component type filtering

### 3. test_manage_implementation_jobs.py
**Module Tested**: `manage_implementation_jobs.py`
- **Classes**: `ImplementationJobManager`
- **Test Cases**: 30+ tests
- **Coverage Areas**:
  - Job lifecycle management
  - Deployment strategies
  - Rollback operations
  - Job validation
  - Artifact management
  - Job scheduling
  - Metrics recording

### 4. test_manage_performance_metrics.py
**Module Tested**: `manage_performance_metrics.py`
- **Classes**: `PerformanceMetricsManager`
- **Test Cases**: 25+ tests
- **Coverage Areas**:
  - Metric recording (latency, throughput, errors)
  - Aggregation and statistics
  - Percentile calculations
  - Trend analysis
  - Anomaly detection
  - Metric archival
  - Health score calculation

## Running the Tests

### Using the Test Runner Script

```bash
cd /opt/mycode/ptr/ai-job-engine/tests/unit/capability

# Run all tests
python run_tests.py

# Run with coverage
python run_tests.py --coverage

# Run specific test file
python run_tests.py test_manage_capability.py

# Run tests matching pattern
python run_tests.py -k "test_create"

# Run with verbose output
python run_tests.py -v

# Stop on first failure
python run_tests.py --fail-fast
```

### Using pytest Directly

```bash
cd /opt/mycode/ptr/ai-job-engine

# Run all capability tests
.venv/bin/python -m pytest tests/unit/capability/ -v

# Run specific test file
.venv/bin/python -m pytest tests/unit/capability/test_manage_capability.py -v

# Run with coverage
.venv/bin/python -m pytest tests/unit/capability/ \
  --cov=scripts/capability-scripts \
  --cov-report=html \
  --cov-report=term

# Run specific test
.venv/bin/python -m pytest tests/unit/capability/test_manage_capability.py::TestCapabilityManager::test_create_capability_success -v
```

### Using the Main Test Runner

```bash
cd /opt/mycode/ptr/ai-job-engine
./tests/run_tests.sh capability-unit
```

## Test Fixtures (conftest.py)

The `conftest.py` file provides shared fixtures for all tests:

### Mock Services
- `mock_dynamodb_table` - Mock DynamoDB table operations
- `mock_dynamodb_resource` - Mock DynamoDB resource
- `mock_dynamodb_client` - Mock DynamoDB client
- `mock_s3_client` - Mock S3 client operations
- `mock_boto3_session` - Complete mocked AWS session

### Sample Data
- `sample_capability_data` - Example capability with all fields
- `sample_component_data` - Example software component
- `sample_dependency_data` - Component dependency example
- `sample_job_data` - Implementation job example
- `sample_metric_data` - Performance metric example
- `sample_health_metric` - Health score data
- `sample_configuration_rule` - Configuration rule example

### Helper Functions
- `create_capability_item()` - Create DynamoDB capability item
- `create_component_item()` - Create DynamoDB component item
- `create_job_item()` - Create DynamoDB job item
- `create_metric_item()` - Create DynamoDB metric item

## Test Patterns

### 1. DynamoDB Mocking
All tests mock DynamoDB operations to avoid real AWS calls:
```python
def test_create_capability(self, mock_dynamodb_table):
    mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
    result = self.manager.create_capability(data)
    assert result is not None
```

### 2. S3 Mocking
S3 operations for artifact storage are mocked:
```python
def test_store_artifact(self, mock_s3_client):
    mock_s3_client.put_object.return_value = {'ETag': '"test-etag"'}
    result = self.manager.store_artifact(component_id, artifact)
    assert result is True
```

### 3. Error Handling
Each test module includes error scenarios:
```python
def test_update_non_existent_capability(self, mock_dynamodb_table):
    mock_dynamodb_table.get_item.return_value = {'Item': None}
    result = self.manager.update_capability('NON-EXISTENT', {})
    assert result is False
```

### 4. Data Validation
Tests validate data structures and business rules:
```python
def test_validate_configuration(self):
    valid_config = {'port': 8080, 'replicas': 3}
    assert self.manager.validate_configuration(valid_config) is True
```

## Coverage Goals

- **Line Coverage**: Target > 80%
- **Branch Coverage**: Target > 70%
- **Function Coverage**: Target > 90%

View coverage report:
```bash
# Generate HTML coverage report
python run_tests.py --coverage

# Open report
open htmlcov/index.html
```

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run Capability Tests
  run: |
    cd tests/unit/capability
    python run_tests.py --coverage
```

```groovy
// Jenkins example
stage('Test Capability Management') {
    steps {
        sh 'cd tests/unit/capability && python run_tests.py --coverage'
    }
}
```

## Adding New Tests

When adding new functionality to capability scripts:

1. **Create Test File**: Follow naming convention `test_<script_name>.py`
2. **Import Script**: Add proper import with sys.path adjustment
3. **Create Test Class**: Name it `Test<ClassName>`
4. **Use Fixtures**: Leverage shared fixtures from conftest.py
5. **Mock AWS Services**: Never make real AWS calls
6. **Test Edge Cases**: Include error scenarios and validation
7. **Document Tests**: Add docstrings explaining test purpose

Example template:
```python
"""
Unit tests for new_feature.py
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../scripts/capability-scripts'))

from new_feature import NewFeatureManager


class TestNewFeatureManager:
    @pytest.fixture(autouse=True)
    def setup(self, mock_dynamodb_table):
        self.manager = NewFeatureManager()
        self.manager.table = mock_dynamodb_table
    
    def test_feature_success(self):
        """Test successful feature execution."""
        # Test implementation
        pass
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure sys.path includes scripts directory
   - Check virtual environment is activated

2. **Mock Not Working**
   - Verify patch decorator targets correct module
   - Check mock setup in fixture

3. **Test Failures**
   - Review actual vs expected mock behavior
   - Check data structure matches implementation

4. **Coverage Low**
   - Add tests for error paths
   - Include edge cases
   - Test all public methods

## Contributing

When contributing tests:
1. Follow existing patterns
2. Maintain > 80% coverage
3. Include positive and negative test cases
4. Update this README if adding new test files
5. Ensure all tests pass before submitting

## Support

For issues or questions about the tests:
- Check test output for specific failures
- Review mock setup in conftest.py
- Consult implementation in scripts/capability-scripts/
- Run with -v flag for detailed output
