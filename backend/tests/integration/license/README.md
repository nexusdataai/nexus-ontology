# License Integration Tests

Integration tests for the License Enablement feature.

## Overview

These tests verify the complete license management functionality including:
- License activation via REST API and MCP tool
- License validation and status checking
- License deactivation and renewal
- Feature tier gating
- Grace period handling
- Audit logging

## Prerequisites

1. Backend service running at `http://localhost:8000`
2. Python dependencies installed:
   ```bash
   pip install pytest pytest-asyncio httpx
   ```

## Running Tests

### Run all license integration tests:
```bash
cd nexus-backend
pytest tests/integration/license/ -v
```

### Run specific test class:
```bash
pytest tests/integration/license/test_license_integration.py::TestLicenseActivation -v
```

### Run with custom server URL:
```bash
TEST_BASE_URL=http://localhost:8080 pytest tests/integration/license/ -v
```

## Test Categories

| Test Class | Description |
|------------|-------------|
| `TestLicenseActivation` | License key activation tests |
| `TestLicenseStatus` | License status query tests |
| `TestLicenseDeactivation` | License deactivation tests |
| `TestLicenseRenewal` | License renewal tests |
| `TestFeatureGating` | Feature tier access tests |
| `TestLicenseValidation` | License validation tests |
| `TestAuditLogging` | Audit trail tests |
| `TestLicenseLifecycle` | Complete lifecycle tests |
| `TestMCPToolIntegration` | MCP tool interface tests |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_BASE_URL` | `http://localhost:8000` | Backend service URL |
| `TEST_TIMEOUT` | `30` | Request timeout in seconds |
| `API_KEY` | `super-secret` | API authentication key |

## Test Fixtures

The tests use pytest fixtures for:
- License key generation (valid, expired, expiring soon)
- API client setup
- License state cleanup between tests
