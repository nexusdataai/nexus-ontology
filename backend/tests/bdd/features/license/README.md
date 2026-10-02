# License BDD Tests

Behavior-Driven Development tests for the License Enablement feature.

## Overview

These BDD tests verify license management functionality using Gherkin syntax.

## Feature Files

| Feature File | Description |
|--------------|-------------|
| `license_activation.feature` | License key activation scenarios |
| `license_status.feature` | License status query scenarios |
| `license_deactivation.feature` | License deactivation scenarios |
| `license_feature_gating.feature` | Feature tier access scenarios |
| `license_validation.feature` | License validation scenarios |
| `license_lifecycle.feature` | Complete lifecycle scenarios |
| `license_audit.feature` | Audit trail scenarios |

## Running Tests

### Run all license BDD tests:
```bash
cd nexus-backend
behave tests/bdd/features/license/
```

### Run specific feature:
```bash
behave tests/bdd/features/license/license_activation.feature
```

### Run with tags:
```bash
# Run only smoke tests
behave tests/bdd/features/license/ --tags=@smoke

# Run API tests only
behave tests/bdd/features/license/ --tags=@api

# Run MCP tool tests
behave tests/bdd/features/license/ --tags=@mcp
```

## Tags

| Tag | Description |
|-----|-------------|
| `@license` | All license tests |
| `@api` | REST API tests |
| `@mcp` | MCP tool tests |
| `@smoke` | Smoke tests (quick validation) |
| `@activation` | Activation tests |
| `@deactivation` | Deactivation tests |
| `@status` | Status query tests |
| `@feature` | Feature gating tests |
| `@validation` | Validation tests |
| `@audit` | Audit logging tests |
| `@lifecycle` | Lifecycle tests |
| `@error` | Error handling tests |

## Prerequisites

1. Backend service running at `http://localhost:8000`
2. Behave installed: `pip install behave`
3. Step definitions in `tests/bdd/steps/license_steps.py`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_URL` | `http://localhost:8000` | Backend service URL |
| `API_KEY` | `super-secret` | API authentication key |
