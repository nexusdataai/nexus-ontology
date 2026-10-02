# AI Job Engine - Test Runner Guide

## 🚀 Quick Start

The main test runner (`tests/run_tests.sh`) now provides a unified interface for running all types of tests: unit, integration, and BDD tests.

### Run All Tests
```bash
# Run everything (unit + integration + BDD)
./tests/run_tests.sh all

# Run with coverage report
./tests/run_tests.sh coverage
```

### Run Specific Test Types

#### Unit Tests
```bash
# Run all unit tests (default)
./tests/run_tests.sh
./tests/run_tests.sh unit

# Run specific domain unit tests
./tests/run_tests.sh journey-unit
./tests/run_tests.sh capability-unit
```

#### Integration Tests
```bash
# Run all integration tests (shell + Python)
./tests/run_tests.sh integration

# Run only shell integration tests
./tests/run_tests.sh integration-shell

# Run only Python integration tests
./tests/run_tests.sh integration-python

# Run with performance tests included
./tests/run_tests.sh performance

# Test against different server
SERVER_URL=http://staging:8000 ./tests/run_tests.sh integration
```

#### BDD Tests
```bash
# Run all BDD tests
./tests/run_tests.sh bdd

# Run specific domain BDD tests
./tests/run_tests.sh journey-bdd
./tests/run_tests.sh capability-bdd
```

### Domain-Specific Testing

#### Journey Tests
```bash
# Run ALL journey tests (unit + integration + BDD)
./tests/run_tests.sh journey

# Run specific journey test types
./tests/run_tests.sh journey-unit        # Unit tests only
./tests/run_tests.sh journey-integration # Integration tests only
./tests/run_tests.sh journey-bdd         # BDD tests only
```

#### Capability Tests
```bash
# Run ALL capability tests
./tests/run_tests.sh capability

# Run specific capability test types
./tests/run_tests.sh capability-unit     # Unit tests only
./tests/run_tests.sh capability-bdd      # BDD tests only
```

## 📁 Test Structure

```
tests/
├── run_tests.sh                 # Main test runner (UPDATED)
├── TEST_RUNNER_GUIDE.md         # This guide
├── unit/                        # Unit tests
│   ├── journey/                 # Journey unit tests
│   └── capability/              # Capability unit tests
├── integration/                 # Integration tests (NEW)
│   ├── run_all_tests.sh        # Integration test runner
│   ├── shell/                  # Shell-based tests
│   │   ├── common/             # Shared utilities
│   │   ├── journey/            # Journey integration tests
│   │   └── logs/               # Logs integration tests
│   ├── python/                 # Python-based tests
│   │   ├── services/           # Service layer tests
│   │   ├── mcp/                # MCP tool tests
│   │   └── api/                # REST API tests
│   └── conftest.py            # Pytest configuration
└── bdd/                        # BDD tests
    ├── features/               # Feature files
    └── steps/                  # Step definitions
```

## 🔧 Configuration

### Environment Variables

```bash
# Server configuration for integration tests
export SERVER_URL=http://localhost:8000

# Output options
export VERBOSE=true              # Detailed output
export JSON_OUTPUT=true          # JSON formatted results

# Test selection
export RUN_PERFORMANCE_TESTS=true  # Include performance tests
```

### Virtual Environment

The test runner automatically detects and uses virtual environments in this order:
1. `.venv/` (project root)
2. `venv/` (project root)
3. `/opt/venv/` (Docker container)
4. System Python (fallback)

## 🎯 Common Use Cases

### Development Workflow

```bash
# Quick unit test during development
./tests/run_tests.sh journey-unit

# Full test before committing
./tests/run_tests.sh journey

# Integration test after server changes
./tests/run_tests.sh integration
```

### CI/CD Pipeline

```bash
# Full test suite with coverage
./tests/run_tests.sh coverage

# Specific test stage
./tests/run_tests.sh unit          # Unit test stage
./tests/run_tests.sh integration   # Integration test stage
./tests/run_tests.sh bdd           # BDD test stage
```

### Debugging

```bash
# Check server status
./tests/run_tests.sh server-check

# Clean test artifacts
./tests/run_tests.sh clean

# Verbose output for debugging
VERBOSE=true ./tests/run_tests.sh integration
```

## 📊 Test Execution Flow

### `all` Command Flow
1. Check Python environment
2. Run all unit tests
3. Check server health (for integration)
4. Run all integration tests (shell + Python)
5. Run all BDD tests
6. Generate summary report

### `integration` Command Flow
1. Check Python environment
2. Verify server is running at SERVER_URL
3. Execute shell integration tests
4. Execute Python integration tests
5. Generate test report (JSON/HTML)

### `journey` Command Flow
1. Run journey unit tests
2. Check server for integration tests
3. Run journey shell integration tests
4. Run journey Python integration tests
5. Run journey BDD tests

## 🔍 Troubleshooting

### Server Not Running
```bash
# Check server status
./tests/run_tests.sh server-check

# Start the server
./gateway.sh start
```

### Missing Dependencies
```bash
# Install test dependencies
pip install -r tests/integration/requirements-test.txt
```

### Clean Environment
```bash
# Clean all test artifacts
./tests/run_tests.sh clean

# Fresh virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r tests/integration/requirements-test.txt
```

## 📈 Test Reports

### Coverage Reports
- **Terminal**: Shows coverage summary after tests
- **HTML**: Generated in `htmlcov/` directory
- **XML**: Generated as `coverage.xml` for CI tools

### Integration Test Reports
- **JSON**: `logs/integration-tests/*_report.json`
- **HTML**: `logs/integration-tests/*_report.html`
- **Logs**: `logs/integration-tests/*.log`

### BDD Reports
- **Console**: Progress format by default
- **JSON**: Can be enabled with `--format json`
- **HTML**: Available with `behave-html-formatter`

## 🚦 Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed
- `2`: Configuration or environment error

## 💡 Best Practices

1. **Always run unit tests first** - They're fast and catch basic issues
2. **Ensure server is running** before integration tests
3. **Use verbose mode** when debugging failures
4. **Run domain-specific tests** during development
5. **Run full suite** before merging code
6. **Clean artifacts** periodically to avoid conflicts

## 🔗 Related Documentation

- [Integration Testing Guide](../INTEGRATION_TESTING_GUIDE.md)
- [Integration Test README](integration/README.md)
- [BDD Test README](bdd/README.md)
- [Unit Test Guidelines](unit/README.md)
