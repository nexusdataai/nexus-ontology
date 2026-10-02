# BDD Endurance Testing Framework

## Overview

The BDD Endurance Testing Framework is a comprehensive solution for running continuous Behavior-Driven Development (BDD) tests to assess the long-term stability, performance, and reliability of the Journey Manager CLI and MCP server. It runs tests continuously for a specified duration (default 30 minutes) while monitoring system health metrics to detect memory leaks, performance degradation, and resource exhaustion issues.

## Key Features

- **Continuous Test Execution**: Runs BDD tests for configurable durations (default 30 minutes)
- **Health Monitoring**: Tracks CPU, memory, file descriptors, and other system resources
- **Performance Analysis**: Identifies performance degradation and resource leaks
- **Flaky Test Detection**: Automatically identifies tests with inconsistent results
- **Real-time Dashboard**: Web-based monitoring dashboard for live test progress
- **Comprehensive Reporting**: HTML and JSON reports with visualizations and recommendations
- **CI/CD Integration**: GitHub Actions workflow for automated testing
- **Configurable Strategies**: Sequential, random, or weighted test execution

## Quick Start

### Prerequisites

1. Python 3.8 or higher
2. Virtual environment with required packages:
   ```bash
   cd /opt/mycode/ptr/ai-job-engine
   source .venv/bin/activate
   pip install -r tests/requirements-test.txt
   ```

### Running Tests

#### Quick 5-minute Test
```bash
cd tests/endurance
./run_endurance_test.sh --test
```

#### Full 30-minute Endurance Test
```bash
./run_endurance_test.sh
```

#### Custom Duration
```bash
./run_endurance_test.sh --duration 60  # 60 minutes
```

#### With Parallel Execution
```bash
./run_endurance_test.sh --parallel 4  # 4 parallel instances
```

#### Dashboard Only Mode
```bash
./run_endurance_test.sh --dashboard
# Access at http://localhost:8080
```

## Configuration

The framework uses `endurance_config.yaml` for configuration. Key settings include:

### Test Duration
```yaml
endurance:
  duration_minutes: 30  # Test duration
```

### Test Strategy
```yaml
test_strategy:
  type: "weighted"  # sequential, random, or weighted
  weights:
    journey_management: 0.4  # 40% of tests
    stage_management: 0.3    # 30% of tests
    job_execution: 0.2       # 20% of tests
    error_scenarios: 0.1     # 10% of tests
```

### Health Monitoring
```yaml
health_monitoring:
  enabled: true
  interval_seconds: 10
  metrics:
    - cpu
    - memory
    - file_descriptors
    - threads
```

### Alert Thresholds
```yaml
thresholds:
  cpu_percent: 80.0
  memory_gb: 4.0
  memory_growth_mb_per_hour: 100
  file_descriptors: 1000
```

## Architecture

### Core Components

1. **bdd_endurance_runner.py**
   - Orchestrates test execution
   - Implements test rotation strategies
   - Manages parallel execution
   - Generates execution reports

2. **server_health_monitor.py**
   - Monitors system resources (CPU, memory, I/O)
   - Tracks application metrics
   - Detects resource leaks
   - Generates health alerts

3. **result_aggregator.py**
   - Collects test results
   - Analyzes failure patterns
   - Identifies flaky tests
   - Calculates performance trends

4. **endurance_report.py**
   - Generates HTML reports
   - Creates JSON exports
   - Produces visualizations
   - Provides recommendations

5. **Dashboard (HTML/JS)**
   - Real-time monitoring
   - Live metrics updates
   - Interactive charts
   - Alert notifications

## Test Execution Strategies

### Sequential
Tests run in order, cycling through all scenarios:
```yaml
test_strategy:
  type: "sequential"
```

### Random
Tests selected randomly for each iteration:
```yaml
test_strategy:
  type: "random"
```

### Weighted
Tests selected based on configured weights:
```yaml
test_strategy:
  type: "weighted"
  weights:
    critical_paths: 0.6
    edge_cases: 0.3
    error_scenarios: 0.1
```

## Health Monitoring

The framework monitors multiple system metrics:

### System Metrics
- CPU usage (overall and per-core)
- Memory (RSS, VMS, available)
- Swap usage
- Disk I/O
- Network I/O
- File descriptors
- Thread count
- Process count

### Application Metrics
- MCP server response times
- Database connections
- Active CLI processes
- DynamoDB operations
- S3 operation latencies

### Resource Leak Detection
- Memory growth rate analysis
- File descriptor leak detection
- Thread leak identification
- Zombie process detection

## Reports and Analysis

### Report Types

All reports are saved to `test_reports/endurance/` (relative to project root)

1. **HTML Report**
   - Interactive visualizations
   - Performance graphs
   - Test result tables
   - Health metrics charts
   - Recommendations

2. **JSON Report**
   - Machine-readable format
   - Complete test data
   - Metrics history
   - CI/CD integration

3. **JUnit XML**
   - CI/CD compatibility
   - Test suite results
   - Failure details

### Key Metrics

- **Pass Rate**: Percentage of successful tests
- **Execution Time**: Average, min, max, P95
- **Flaky Tests**: Tests with inconsistent results
- **Performance Trends**: Degradation over time
- **Resource Usage**: Peak and average values
- **Error Patterns**: Common failure causes

## Real-time Dashboard

Access the dashboard at `http://localhost:8080` during test execution.

Dashboard files are located in `test_reports/endurance/dashboard/` (relative to project root).

### Dashboard Features
- Live test progress
- Real-time metrics
- Performance charts
- Recent test results
- Active alerts
- System health status

### Dashboard Sections
1. **Test Progress**: Overall completion and iterations
2. **Metrics Grid**: Pass rate, health, performance, flaky tests
3. **Charts**: Pass rate and resource usage over time
4. **Recent Results**: Latest test executions
5. **Alerts**: Active warnings and errors

## CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/endurance-tests.yml`:

```yaml
name: Endurance Tests
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM
  workflow_dispatch:

jobs:
  endurance:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r tests/requirements-test.txt
      
      - name: Run endurance tests
        run: |
          cd tests/endurance
          ./run_endurance_test.sh --test
      
      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: endurance-reports
          path: test_reports/endurance/
```

## Troubleshooting

### Common Issues

#### 1. Tests Not Running
```bash
# Check Python environment
which python
python --version

# Verify dependencies
pip list | grep behave
pip list | grep psutil
```

#### 2. Dashboard Not Loading
```bash
# Check if port 8080 is in use
lsof -i :8080

# Use different port
export DASHBOARD_PORT=8081
./run_endurance_test.sh --dashboard
```

#### 3. Memory Issues
```bash
# Increase memory limits
export TEST_MEMORY_LIMIT=8G

# Run with reduced parallel instances
./run_endurance_test.sh --parallel 1
```

#### 4. Permission Errors
```bash
# Make scripts executable
chmod +x run_endurance_test.sh
chmod +x *.py
```

### Debug Mode

Enable verbose output for troubleshooting:
```bash
./run_endurance_test.sh --verbose
```

Check logs:
```bash
tail -f logs/endurance_*.log
tail -f logs/dashboard.log
```

## Performance Optimization

### Tips for Better Performance

1. **Optimize Test Selection**
   - Focus on critical paths
   - Reduce redundant scenarios
   - Use weighted strategy wisely

2. **Resource Management**
   - Close file handles properly
   - Clean up test data
   - Use connection pooling

3. **Parallel Execution**
   - Balance parallel instances
   - Monitor resource usage
   - Avoid resource contention

4. **Monitoring Overhead**
   - Adjust sampling intervals
   - Reduce metric collection
   - Use efficient data structures

## Best Practices

1. **Regular Execution**
   - Run weekly in CI/CD
   - Test after major changes
   - Monitor trends over time

2. **Baseline Establishment**
   - Create performance baselines
   - Document normal ranges
   - Track improvements

3. **Issue Investigation**
   - Analyze failure patterns
   - Review resource graphs
   - Check error logs

4. **Continuous Improvement**
   - Fix flaky tests
   - Optimize slow tests
   - Address resource leaks

## Advanced Usage

### Custom Test Scenarios

Add custom scenarios to the configuration:
```yaml
scenarios:
  include_features:
    - "custom_feature.feature"
  include_tags:
    - "@critical"
    - "@performance"
```

### Alert Notifications

Configure email or Slack alerts:
```yaml
alerts:
  channels:
    - email
    - slack
  email:
    smtp_server: "smtp.gmail.com"
    to_addresses:
      - "team@example.com"
```

### Export Results

Export results to external systems:
```yaml
ci_cd:
  upload_to_s3: true
  s3_results_bucket: "test-results"
  post_results: true
  results_endpoint: "https://api.example.com/results"
```

## Contributing

### Adding New Metrics

1. Update `server_health_monitor.py`:
   ```python
   def _collect_custom_metric(self):
       # Implement metric collection
       return metric_value
   ```

2. Add to configuration:
   ```yaml
   health_monitoring:
     metrics:
       - custom_metric
   ```

### Creating Custom Reports

1. Extend `endurance_report.py`:
   ```python
   def generate_custom_report(self):
       # Implement custom report
       pass
   ```

2. Update report configuration:
   ```yaml
   reporting:
     formats:
       - custom
   ```

## API Reference

### BDDEnduranceRunner

```python
runner = BDDEnduranceRunner(config_file='config.yaml')
runner.start(duration_minutes=30)
```

### ServerHealthMonitor

```python
monitor = ServerHealthMonitor(interval_seconds=10)
monitor.start_monitoring()
stats = monitor.get_summary_stats()
monitor.export_metrics('metrics.json')
```

### ResultAggregator

```python
aggregator = ResultAggregator()
aggregator.add_result(test_result)
summary = aggregator.get_summary()
flaky_tests = aggregator.identify_flaky_tests()
```

## Support

For issues or questions:
1. Check this documentation
2. Review test logs in `logs/`
3. Examine reports in `test_reports/endurance/`
4. Contact the development team

## License

This endurance testing framework is part of the AI Job Engine project and follows the same licensing terms.

## Changelog

### Version 1.0.0 (2024)
- Initial release
- Core functionality implementation
- Dashboard and reporting
- CI/CD integration

---

*Last Updated: December 2024*
