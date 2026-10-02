# Python Integration Tests

Comprehensive Python integration tests for the AI Job Engine.

## Overview

These tests verify the complete system functionality including MCP tools, REST APIs, and service layer operations through the HTTP gateway.

## Test Structure

```
tests/integration/python/
├── utils/                          # Test utilities
│   ├── response_validator.py      # Response format validation
│   └── test_helpers.py            # Helper functions
├── fixtures/                       # Test data fixtures
│   ├── journey_fixtures.py        # Journey test data
│   └── logs_fixtures.py           # Logs test data
├── mcp/                           # MCP tool tests
│   ├── test_journey_crud.py       # Journey CRUD operations
│   ├── test_journey_stages.py     # Stage management
│   ├── test_journey_rules.py      # Rule management
│   ├── test_journey_utilities.py  # Utility operations
│   ├── test_journey_jobs.py       # Job execution
│   ├── test_logs_operations.py    # Log operations
│   ├── test_reports_operations.py # Report operations
│   ├── test_analysis_operations.py # Analysis operations
│   └── test_tool_discovery.py     # Tool discovery
└── api/                           # REST API tests
    ├── test_journey_rest_api.py   # Journey REST endpoints
    └── test_health_api.py         # Health endpoints
```

## Running Tests

### Run All Python Tests

```bash
cd /opt/mycode/ptr/ai-job-engine
pytest tests/integration/python -v
```

### Run Specific Test Module

```bash
# Journey CRUD tests
pytest tests/integration/python/mcp/test_journey_crud.py -v

# Logs operations tests
pytest tests/integration/python/mcp/test_logs_operations.py -v

# Health API tests
pytest tests/integration/python/api/test_health_api.py -v
```

### Run Tests by Category

```bash
# All MCP tool tests
pytest tests/integration/python/mcp -v

# All REST API tests
pytest tests/integration/python/api -v
```

### Run Tests with Markers

```bash
# Integration tests only
pytest tests/integration/python -m integration -v

# Exclude performance tests
pytest tests/integration/python -m "not performance" -v
```

## Test Categories

### MCP Tool Tests (mcp/)

#### Journey CRUD (`test_journey_crud.py`)
- **test_create_journey** - Basic journey creation
- **test_create_journey_validation** - Field validation
- **test_read_journey** - Read existing journey
- **test_read_nonexistent_journey** - Error handling
- **test_update_journey** - Update operations
- **test_delete_journey** - Delete operations
- **test_list_journeys** - List with filters
- **test_list_journeys_with_filters** - Filtered listing

#### Journey Stages (`test_journey_stages.py`)
- **test_list_stages** - List all stages
- **test_add_stage** - Add custom stage
- **test_add_default_stages** - Add standard TMF stages
- **test_update_stage** - Update stage properties
- **test_delete_stage** - Remove stage

#### Journey Rules (`test_journey_rules.py`)
- **test_list_rules** - List Second Brain rules
- **test_add_rule** - Add new rule
- **test_add_stage_specific_rule** - Stage-specific rules
- **test_update_rule** - Update existing rule
- **test_delete_rule** - Remove rule
- **test_filter_rules_by_type** - Filter by rule type

#### Journey Utilities (`test_journey_utilities.py`)
- **test_dashboard** - Dashboard aggregations
- **test_get_journey_summary** - Journey summary
- **test_get_comprehensive** - Complete journey data
- **test_export_complete** - Export to file
- **test_import_complete** - Import from file

#### Journey Jobs (`test_journey_jobs.py`)
- **test_run_job_system_trigger** - System-triggered jobs
- **test_run_job_user_trigger** - User-triggered jobs
- **test_run_job_api_trigger** - API-triggered jobs
- **test_update_job_status** - Update job progress
- **test_get_job_metrics** - Job performance metrics
- **test_get_job_timeline** - Execution timeline
- **test_batch_cancel_jobs** - Cancel multiple jobs

#### Logs Operations (`test_logs_operations.py`)
- **test_get_job_logs** - Retrieve job logs
- **test_add_log_entry** - Add log entry
- **test_search_logs** - Search through logs
- **test_get_logs_by_level** - Filter by level
- **test_export_job_logs** - Export logs
- **test_get_error_summary** - Error analysis

#### Reports Operations (`test_reports_operations.py`)
- **test_get_job_reports** - Get reports for job
- **test_create_job_report** - Create custom report
- **test_generate_summary_report** - Generate summary
- **test_generate_performance_report** - Performance analysis
- **test_generate_error_analysis_report** - Error analysis

#### Analysis Operations (`test_analysis_operations.py`)
- **test_analyze_job_performance** - Performance metrics
- **test_analyze_error_patterns** - Error patterns

#### Tool Discovery (`test_tool_discovery.py`)
- **test_list_tools** - List available tools
- **test_journeys_tool_schema** - Tool schema validation
- **test_logs_tool_schema** - Tool schema validation
- **test_tool_error_handling** - Error scenarios

### REST API Tests (api/)

#### Journey REST API (`test_journey_rest_api.py`)
- **test_create_journey_via_rest** - POST /api/v1/journeys/
- **test_get_journey_via_rest** - GET /api/v1/journeys/{id}
- **test_list_journeys_via_rest** - GET /api/v1/journeys/
- **test_update_journey_via_rest** - PUT /api/v1/journeys/{id}
- **test_delete_journey_via_rest** - DELETE /api/v1/journeys/{id}

#### Health API (`test_health_api.py`)
- **test_health_endpoint** - GET /health
- **test_readiness_endpoint** - GET /ready
- **test_stats_endpoint** - GET /stats
- **test_docs_endpoint** - GET /docs

## Response Format

All MCP tool responses follow this format:

```python
{
  "status": "success" | "error",
  "message": "Human readable message",
  "operation": "action_name",
  "journey_id": "JRN-123",  # snake_case fields
  "data": {...},
  "error": "Error details if status=error"
}
```

### Field Naming Convention

**IMPORTANT:** Tests use **snake_case** field naming to match current implementation:
- `journey_id` (not `journeyId`)
- `stage_id` (not `stageId`)
- `job_id` (not `jobId`)
- `log_level` (not `logLevel`)

## HTTP Request Format

### MCP Tool Calls

```python
response = await client.post(
    "/tools/journeys_tool",
    json={"arguments": {
        "action": "create",
        "name": "Test Journey",
        "odaComponentType": "product-catalog"
    }},
    headers={"x-api-key": "super-secret"}
)

# Response is direct tool response (NO "result" wrapper)
result = response.json()
assert result["status"] == "success"
assert result["journey_id"].startswith("JRN-")
```

### REST API Calls

```python
response = await client.post(
    "/api/v1/journeys/",
    json={
        "name": "Test Journey",
        "odaComponentType": "product-catalog"
    },
    headers={"x-api-key": "super-secret"}
)
```

## Configuration

### Prerequisites

```bash
# Server must be running
curl http://localhost:8000/health

# Install test dependencies
pip install -r tests/integration/requirements-test.txt
```

### Environment Variables

```bash
export SERVER_URL=http://localhost:8000
export TEST_TIMEOUT=30
export USE_MOCK_AWS=true
```

### Pytest Configuration

From `pytest.ini` or command line:

```ini
[tool:pytest]
markers =
    integration: Integration test
    performance: Performance test  
    slow: Slow running test
    requires_aws: Requires AWS services

testpaths = tests/integration/python
python_files = test_*.py
asyncio_mode = auto
```

## Writing New Tests

### Test Template

```python
import pytest
from ..utils.response_validator import validate_success_response
from ..utils.test_helpers import extract_journey_id

@pytest.mark.integration
class TestMyFeature:
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client, cleanup_manager):
        self.client = api_client
        self.cleanup = cleanup_manager
        self.created_journeys = []
    
    def teardown_method(self, method):
        for journey_id in self.created_journeys:
            self.cleanup("journey", journey_id)
    
    @pytest.mark.asyncio
    async def test_my_operation(self):
        # Arrange
        response = await self.client.post(
            "/tools/journeys_tool",
            json={"arguments": {
                "action": "create",
                "name": "Test",
                "odaComponentType": "test"
            }}
        )
        
        # Act
        assert response.status_code == 200
        result = response.json()
        
        # Assert
        validate_success_response(result, "create")
        journey_id = extract_journey_id(result)
        self.created_journeys.append(journey_id)
        self.cleanup("journey", journey_id)
```

### Best Practices

1. **Use fixtures** - Leverage existing fixtures from `fixtures/` directory
2. **Validate responses** - Use `response_validator` functions
3. **Cleanup resources** - Always track and cleanup created journeys/jobs
4. **Test both success and error** - Test happy path and error scenarios
5. **Use snake_case** - Match current implementation field naming
6. **Handle async properly** - Use `@pytest.mark.asyncio` decorator
7. **Be specific** - One test per operation or scenario

## Troubleshooting

### Server Not Running

```bash
# Check health
curl http://localhost:8000/health

# Start server
cd /opt/mycode/ptr/ai-job-engine
./gateway.sh start
```

### Import Errors

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r tests/integration/requirements-test.txt
```

### Test Failures

```bash
# Run with verbose output
pytest tests/integration/python -vvv

# Run single test with full traceback
pytest tests/integration/python/mcp/test_journey_crud.py::TestJourneyCRUD::test_create_journey -vvv --tb=long

# View logs
tail -f logs/integration-tests/*.log
```

### Cleanup Issues

```bash
# Manually cleanup test data
./gateway.sh status
docker logs ai-job-engine
```

## Integration with CI/CD

### GitHub Actions

```yaml
- name: Run Integration Tests
  run: |
    ./gateway.sh start
    pytest tests/integration/python -v
```

### Test Reports

After running tests, reports are available in:
- `logs/integration-tests/INT_TEST_*_report.json`
- `logs/integration-tests/INT_TEST_*_report.html`

## Related Documentation

- [Integration Tests Main README](../README.md)
- [Integration Tests Assessment](../../../INTEGRATION_TESTS_ASSESSMENT.md)
- [MCP Tool Documentation](../../../testscripts/tool-data/README_MCP_TOOLS.md)

## Maintenance

### When Adding New Features

1. Add test fixtures to `fixtures/`
2. Add validation functions to `utils/response_validator.py`
3. Create focused test file in appropriate directory
4. Update this README with new tests
5. Run full test suite to ensure no regressions

### Test Coverage Goals

- **All MCP tool actions**: 100% coverage
- **All REST endpoints**: 100% coverage
- **Error scenarios**: All common errors tested
- **Integration scenarios**: Key workflows tested end-to-end

## Contact

For issues or questions about integration tests, see:
- Integration test logs in `logs/integration-tests/`
- Main test runner: `tests/integration/run_all_tests.sh`
- Test assessment: `INTEGRATION_TESTS_ASSESSMENT.md`

