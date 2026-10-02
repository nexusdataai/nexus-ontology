# Journey Job Management Test Scripts

This directory contains test scripts for validating job management functionality in the Journey Management System.

## Overview

These scripts test various aspects of job operations available through the `journeys_tool` MCP tool, including job execution, status updates, metrics retrieval, and batch operations.

## Available Test Scripts

### 1. `test_run_job_action.sh` 🚀

**Purpose:** Tests the `run_job` action functionality which allows execution of transformation jobs via MCP protocol.

**Features:**
- Tests run_job action with various parameters
- Tests different trigger types (system, user, api, cli)
- Validates error handling for invalid inputs
- Creates test journey automatically if none exists
- Comprehensive result reporting with pass/fail statistics
- Logs test results to file

**Usage:**
```bash
# Auto-select or create journey
./test_run_job_action.sh

# Use specific journey
./test_run_job_action.sh JRN-ABC123

# Enable debug output
DEBUG=true ./test_run_job_action.sh
```

**Test Coverage:**
- ✅ Basic job execution with system trigger
- ✅ User-triggered job execution
- ✅ API-triggered job execution
- ✅ Custom reason messages
- ✅ Multiple stage support
- ✅ Invalid journey ID handling
- ✅ Invalid stage ID handling
- ✅ Empty parameter validation

---

### 2. `test_journey_inspection_operations.sh` 📊

**Purpose:** Interactive test script for journey inspection and reporting operations.

**Features:**
- Interactive journey selection from database
- Tests journey analysis operations
- Visual progress indicators
- Comprehensive error handling

**Operations Tested:**
- List journey rules (`list_rules`)
- Dashboard analytics (`dashboard`)
- Journey summary (`get_journey_summary`)
- Comprehensive journey data (`get_comprehensive`)
- Error handling for invalid actions

**Note:** Despite the original name, this script does NOT test job execution. It focuses on journey inspection and reporting.

**Usage:**
```bash
./test_journey_inspection_operations.sh                    # Interactive mode
./test_journey_inspection_operations.sh JRN-ABC123         # Test specific journey
```

---

### 3. `test_journeys_job_operations.sh` 🔧

**Purpose:** Tests job-related operations available via the `journeys_tool`.

**Features:**
- Tests all job management endpoints
- Validates response formats
- Tests with realistic job IDs
- Comprehensive metrics validation

**Test Coverage:**
- Job status updates
- Job metrics retrieval
- Job timeline tracking
- Batch job cancellation
- Dashboard analytics
- Journey summaries

**Usage:**
```bash
./test_journeys_job_operations.sh
```

---

## Configuration

All scripts use the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_URL` | `http://localhost:8000` | MCP server endpoint |
| `API_KEY` | `super-secret` | API authentication key |
| `LOG_DIR` | `/opt/mycode/trilogy/nexus-backend/logs` | Directory for test logs |

## Prerequisites

1. **MCP Server Running:**
   ```bash
   cd /opt/mycode/trilogy/nexus-backend
   .venv/bin/python mcp_http_gateway.py --host 0.0.0.0 --port 8000
   ```

2. **Dependencies:**
   - `curl` - For making HTTP requests
   - `jq` - For JSON parsing
   - `bash` - Shell interpreter

3. **AWS Credentials:**
   - Valid AWS credentials for DynamoDB access
   - Run `./aws-login.sh` if credentials expired

## Test Results

All test scripts provide:
- ✅ Color-coded output for easy reading
- 📊 Pass/fail statistics
- 📝 Detailed error messages
- 📁 Log files for debugging

## Common Issues & Solutions

### Issue 1: No Journeys Found
**Solution:** Scripts will automatically create test journeys if configured.

### Issue 2: AWS Credentials Expired
**Solution:** Run `./aws-login.sh` to refresh credentials.

### Issue 3: MCP Server Not Running
**Solution:** Start the server using the command in Prerequisites.

### Issue 4: JSON Parsing Errors
**Solution:** Check if stages are outputting to stdout (should use stderr).

## Development Guidelines

When creating new test scripts:

1. **Use Common Functions:**
   - `log_message()` for consistent output
   - `parse_mcp_response()` for JSON handling
   - Color codes for visual feedback

2. **Track Test Results:**
   - Count total/passed/failed tests
   - Calculate pass percentages
   - Provide clear summaries

3. **Handle Errors Gracefully:**
   - Check for null/empty responses
   - Validate JSON before parsing
   - Provide helpful error messages

4. **Log Everything:**
   - Save detailed logs to files
   - Include timestamps
   - Preserve for debugging

## Contributing

To add new test scripts:

1. Create script in this directory
2. Follow naming convention: `test_<feature>.sh`
3. Make executable: `chmod +x test_<feature>.sh`
4. Update this README with documentation
5. Test thoroughly before committing

## Related Documentation

- [Journey Tool Documentation](/opt/mycode/trilogy/nexus-backend/doc/mcp-tools/journeys-tool.md)
- [MCP Server Setup](/opt/mycode/trilogy/nexus-backend/README.md)
- [Journey Management Scripts](/opt/mycode/trilogy/nexus-backend/scripts/journey-scripts/README.md)
