# BDD Testing for Journey Manager CLI

This directory contains Behavior-Driven Development (BDD) tests for the Journey Manager CLI using the Behave framework with pexpect for interactive CLI testing.

## Overview

The BDD testing framework allows us to test the interactive Journey Manager CLI by:
- Spawning the CLI process and controlling it programmatically
- Sending inputs to handle prompts and menu navigation
- Validating outputs and state changes
- Using mocked AWS services to avoid real resource creation

## Directory Structure

```
tests/bdd/
├── features/               # Gherkin feature files
│   ├── journey_management.feature
│   ├── stage_management.feature
│   ├── rules_management.feature
│   └── job_execution.feature
├── steps/                  # Step definitions
│   ├── common_steps.py     # Shared steps
│   ├── journey_steps.py    # Journey-specific steps
│   └── stage_steps.py      # Stage-specific steps
├── support/                # Support modules
│   ├── cli_wrapper.py      # CLI interaction layer
│   ├── test_data_manager.py # Test data management
│   └── aws_mock_manager.py # AWS service mocking
├── environment.py          # Behave hooks and setup
└── README.md              # This file
```

## Prerequisites

1. Python 3.9+ installed
2. Virtual environment activated
3. Dependencies installed:
   ```bash
   uv sync
   ```

## Running Tests

### Using the Shell Script (Recommended)

```bash
# Run all tests
./run_bdd_tests.sh

# Run specific feature
./run_bdd_tests.sh -f journey_management

# Run with specific tags
./run_bdd_tests.sh -t @journey,@create

# Run excluding certain tags
./run_bdd_tests.sh -t ~@slow,~@wip

# Run specific scenario
./run_bdd_tests.sh -f journey_management -s "Create a new journey successfully"

# Run in parallel
./run_bdd_tests.sh -p

# Generate JSON report
./run_bdd_tests.sh --format json

# List all features
./run_bdd_tests.sh --list-features

# List scenarios in a feature
./run_bdd_tests.sh --list-scenarios journey_management
```

### Using Python Script Directly

```bash
# Run all tests
python run_bdd_tests.py

# Run with tags
python run_bdd_tests.py --tags @journey @create

# Run specific features
python run_bdd_tests.py --features journey_management stage_management

# Generate reports
python run_bdd_tests.py --format json
python run_bdd_tests.py --format junit

# Parallel execution
python run_bdd_tests.py --parallel
```

### Using Behave Directly

```bash
# Run all tests
behave tests/bdd/features

# Run specific feature
behave tests/bdd/features/journey_management.feature

# Run with tags
behave --tags=@journey --tags=@create

# Dry run to validate features
behave --dry-run

# Stop on first failure
behave --stop
```

## Writing Tests

### Feature Files

Feature files are written in Gherkin syntax:

```gherkin
Feature: Journey Management Operations
  As a transformation manager
  I want to manage journeys through the CLI
  So that I can orchestrate ODA transformations

  Background:
    Given the Journey Manager CLI is running
    And I am authenticated as "test-user@example.com"

  @journey @create
  Scenario: Create a new journey
    Given I am on the main menu
    When I navigate to "Journey Operations"
    And I select "Create New Journey"
    And I enter the following journey details:
      | field       | value                |
      | name        | Test Journey         |
      | description | Test description     |
    Then I should see "Journey created successfully"
```

### Step Definitions

Step definitions map Gherkin steps to Python code:

```python
from behave import given, when, then

@given('the Journey Manager CLI is running')
def step_start_cli(context):
    """Start the CLI process"""
    context.cli.start()
    context.cli.wait_for_prompt(['Main Menu'])

@when('I navigate to "{menu_option}"')
def step_navigate_menu(context, menu_option):
    """Navigate to menu option"""
    menu_map = {
        'Journey Operations': '1',
        'Stage Management': '2'
    }
    context.cli.send_input(menu_map[menu_option])
```

## Test Organization

### Tags

Use tags to organize and filter tests:
- `@journey` - Journey-related tests
- `@stage` - Stage management tests
- `@rules` - Rules management tests
- `@execution` - Job execution tests
- `@create`, `@update`, `@delete` - CRUD operations
- `@validation` - Input validation tests
- `@error` - Error handling tests
- `@slow` - Long-running tests
- `@wip` - Work in progress (skip in CI)

### Test Data

Test data is managed through:
1. **TestDataManager** - Creates and manages test fixtures
2. **Mocked DynamoDB** - Stores test data in memory
3. **Context sharing** - Passes data between steps

Example:
```python
# Create test journey in Given step
journey = context.test_data.create_journey({
    'journeyId': 'JRN-TEST-001',
    'name': 'Test Journey'
})
context.test_journey_id = journey['journeyId']
```

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Manual workflow dispatch

See `.github/workflows/bdd-tests.yml` for configuration.

### Running in CI

```yaml
- name: Run BDD tests
  run: |
    source .venv/bin/activate
    python run_bdd_tests.py --format json --tags ~@slow
```

## Debugging Tests

### Enable CLI Output

```python
# In environment.py or step definition
context.cli.start(log_output=True)
```

### Save Output on Failure

Failed scenarios automatically save CLI output to `test_reports/`.

### Interactive Debugging

```python
# Add breakpoint in step
import pdb; pdb.set_trace()

# Print current CLI output
print(context.cli.get_current_output())

# Manually interact with CLI
context.cli.send_input('1')
context.cli.wait_for_prompt(['Select'])
```

## Best Practices

1. **Keep scenarios focused** - Test one behavior per scenario
2. **Use descriptive names** - Scenario names should explain the test
3. **Reuse common steps** - Use Background and common_steps.py
4. **Mock external services** - Always use mocked AWS services
5. **Clean up test data** - Use after_scenario hooks
6. **Handle timeouts** - Set appropriate timeouts for operations
7. **Validate both success and failure** - Test error scenarios

## Troubleshooting

### CLI Process Issues

```bash
# Kill stuck processes
pkill -f journey-manager

# Check process status
ps aux | grep journey-manager
```

### Timeout Errors

Increase timeout in CLI wrapper:
```python
context.cli = JourneyManagerCLI(timeout=60)  # 60 seconds
```

### AWS Mock Issues

Ensure environment variables are set:
```python
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['MOTO_DYNAMODB_USE_DOCKER'] = 'false'
```

## Contributing

1. Write feature file for new functionality
2. Implement step definitions
3. Add appropriate tags
4. Test locally: `./run_bdd_tests.sh -f your_feature`
5. Ensure all tests pass before submitting PR
