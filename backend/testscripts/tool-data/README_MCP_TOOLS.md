# TMF ODA Transformer MCP Server - Tool Testing Scripts

This directory contains comprehensive shell scripts for testing and documenting all MCP (Model Context Protocol) tools available in the TMF ODA Transformer server.

## 📋 Available Scripts

### 🔍 Tool Discovery & Listing

#### `list_all_tools.sh`
**Purpose**: Lists all available MCP tools with their basic information and status
**Features**:
- Server health checks
- Tool endpoint discovery 
- Accessibility testing
- Tool categorization
- API documentation generation

**Usage**:
```bash
./list_all_tools.sh                          # Local server (localhost:8000)
./list_all_tools.sh http://192.168.1.100:8000  # Remote server
./list_all_tools.sh https://example.com:8080   # Remote server with HTTPS
```

**Output**:
- Complete list of 7 MCP tools
- Tool descriptions and endpoints
- Availability status for each tool
- Quick API reference

---

### 📖 Detailed Tool Information

#### `get_tool_details.sh`
**Purpose**: Get detailed information for specific MCP tools
**Features**:
- Tool-specific parameter documentation
- Request/response examples
- Endpoint testing
- Usage guidelines

**Usage**:
```bash
./get_tool_details.sh [tool-name]               # Local server
./get_tool_details.sh raw-analysis              # Specific tool on local server
./get_tool_details.sh all                       # All tools on local server
./get_tool_details.sh http://remote-host:8080 journeys  # Specific tool on remote server
./get_tool_details.sh https://example.com:8000 all      # All tools on remote server
```

**Available Tools**:
- `raw-analysis` - Execute raw analysis stage
- `stripped-schema` - Execute schema stripping stage
- `run-jobs` - Execute any transformation stage
- `journeys` - Journey lifecycle management
- `get-job-logs` - Retrieve execution logs (legacy)
- `logs-and-reports` - Enhanced logs and reports
- `test-runner` - Validation testing
- `all` - Show details for all tools

---

### 📋 Parameter Reference

#### `show_tool_parameters.sh`
**Purpose**: Shows detailed parameter information for all MCP tools
**Features**:
- Complete parameter documentation
- Data type specifications
- Required vs optional parameters
- Validation rules
- JSON payload examples

**Usage**:
```bash
./show_tool_parameters.sh                       # Local server (localhost:8000)
./show_tool_parameters.sh http://192.168.1.100:8000     # Remote server
./show_tool_parameters.sh https://example.com:3000      # Remote server with custom port
```

**Output**:
- Parameter details for all 7 tools
- Quick reference guide
- Validation guidelines
- Copy-paste examples

---

### 🧪 Comprehensive Testing

#### `test_tool_availability.sh`
**Purpose**: Comprehensive testing of all MCP tools
**Features**:
- Server connectivity tests
- Tool endpoint functionality
- Parameter validation
- Response format validation
- Integration testing
- Error handling tests
- Performance metrics
- Detailed test reporting

**Usage**:
```bash
./test_tool_availability.sh                     # Local server (localhost:8000)
./test_tool_availability.sh http://10.0.0.50:8000        # Remote server
./test_tool_availability.sh https://staging.company.com:8080  # Remote staging server
```

**Test Categories**:
1. **Server Connectivity** - Basic server health and endpoint availability
2. **Tool Functionality** - Individual tool testing (OPTIONS, POST, JSON handling)
3. **Parameter Validation** - Required parameter checking and format validation
4. **Response Format** - JSON structure and status field validation
5. **Integration Scenarios** - Cross-tool functionality testing
6. **Error Handling** - 404s, invalid methods, timeouts
7. **Performance** - Response time measurements

---

## 🚀 Quick Start Guide

### 1. Check Server Status
```bash
# Local server
./list_all_tools.sh

# Remote server
./list_all_tools.sh http://your-server.com:8080
```

### 2. Get Tool Overview
```bash
# Local server - see all available tools and their status
./list_all_tools.sh

# Remote server - check tools on production/staging
./list_all_tools.sh http://prod-server.company.com:8000
```

### 3. Get Specific Tool Information
```bash
# Local server - get detailed info for a specific tool
./get_tool_details.sh raw-analysis

# Remote server - get tool info from remote environment
./get_tool_details.sh http://staging.company.com:8080 journeys
```

### 4. View Parameters Reference
```bash
# Local server - see parameter documentation for all tools
./show_tool_parameters.sh

# Remote server - check parameters on remote server
./show_tool_parameters.sh https://example.com:3000
```

### 5. Run Comprehensive Tests
```bash
# Local server - test all tools comprehensively
./test_tool_availability.sh

# Remote server - run full test suite on remote environment
./test_tool_availability.sh http://prod-server.company.com:8000
```

---

## 🔧 TMF ODA Transformer MCP Tools

### Execution Tools
- **`raw-analysis`** - Execute raw analysis stage of TMF ODA transformation
- **`stripped-schema`** - Execute schema stripping stage
- **`run-jobs`** - Execute any transformation stage

### Management Tools
- **`journeys_tool`** - Comprehensive journey lifecycle management (CRUD operations for journeys, stages, rules, and job utilities)
- **`logs_and_reports_tool`** - Comprehensive logs and reports management (16 actions: log retrieval, searching, filtering, report generation, performance analysis, error pattern detection)

### Utility Tools (Legacy)
- **`get-job-logs`** - Retrieve detailed execution logs (legacy compatibility - use logs_and_reports_tool instead)
- **`test-runner`** - Comprehensive tool validation testing

---

## 🌐 Remote Execution Support

All scripts now support connecting to remote MCP servers using a single **URL parameter format**.

### Uniform Command Format

**All scripts now use the same simple format:**
```bash
./script_name.sh [URL] [additional_args]
```

### Examples Across All Script Categories

#### Tool Data Scripts
```bash
# Basic usage (local server)
./list_all_tools.sh
./get_tool_details.sh
./show_tool_parameters.sh
./test_tool_availability.sh

# Remote server usage
./list_all_tools.sh http://18.191.87.212:8000
./get_tool_details.sh http://192.168.1.100:8000 journeys
./show_tool_parameters.sh https://api.company.com:8080
./test_tool_availability.sh http://staging-server.com:3000
```

#### Journey CRUD Scripts
```bash
# Basic usage (local server)
./test_journey_create_only.sh
./test_journey_crud_lifecycle.sh
./test_second_brain.sh

# Remote server usage
./test_journey_create_only.sh http://18.191.87.212:8000
./test_journey_crud_lifecycle.sh http://192.168.1.100:8000
./test_second_brain.sh https://prod-server.company.com
```

#### Logs and Reports Scripts
```bash
# Basic usage (local server)
./test_logs_and_reports.sh
./test_logs_and_reports.sh JRN-DEMO-001

# Remote server usage
./test_logs_and_reports.sh http://18.191.87.212:8000
./test_logs_and_reports.sh http://192.168.1.100:8000 JRN-DEMO-001
./test_logs_and_reports.sh https://api.company.com JRN-PROD-123
```

#### Run Jobs Scripts
```bash
# Basic usage (local server)
./test_enhanced_run_jobs.sh
./test_enhanced_run_jobs.sh JRN-DEMO-001

# Remote server usage
./test_enhanced_run_jobs.sh http://18.191.87.212:8000
./test_enhanced_run_jobs.sh http://192.168.1.100:8000 JRN-DEMO-001
./test_enhanced_run_jobs.sh https://staging-env.company.com JRN-TEST-001
```

### URL Format Support

**Supported URL formats:**
- `http://host:port` - Standard HTTP connection
- `https://host:port` - Secure HTTPS connection
- `http://host` - Uses default port 8000
- `https://host` - Uses default port 8000

### Migration from Old Formats

**Before (inconsistent formats):**
```bash
# Old host/port format (tool-data scripts)
./list_all_tools.sh -h 192.168.1.100 -p 9000
./get_tool_details.sh --host example.com --port 8080

# Old hardcoded localhost (other scripts)
# Required manual editing of SERVER_URL in scripts
```

**After (uniform URL format):**
```bash
# New unified URL format (all scripts)
./list_all_tools.sh http://192.168.1.100:8000
./get_tool_details.sh http://example.com:8080
./test_journey_create_only.sh http://192.168.1.100:8000
./test_logs_and_reports.sh http://example.com:8080
```

### Benefits of Uniform URL Format

- **🎯 Consistency**: Same format across all 15+ test scripts
- **🚀 Simplicity**: Single URL parameter instead of separate host/port
- **🔒 Security**: Support for both HTTP and HTTPS
- **⚡ Speed**: No need to edit scripts or remember different parameter formats
- **🌐 Flexibility**: Easy switching between local, staging, and production environments
- **📝 Documentation**: Clear, predictable usage patterns

### Help and Usage

Every script supports `--help` for usage information:
```bash
./list_all_tools.sh --help
./test_journey_create_only.sh --help
./test_logs_and_reports.sh --help
./test_enhanced_run_jobs.sh --help
```

---

## 📊 Server Configuration

**Default Settings**:
- Server URL: `http://localhost:8000` (when no URL provided)
- All scripts fall back to localhost if no URL is specified

**Starting the Server**:
```bash
python -m awslabs.tmf_oda_transformer_mcp_server.mcp_http_server
```

---

## 🛠️ Prerequisites

### Required Tools
- `curl` - For HTTP requests
- `jq` - For JSON parsing
- `bash` - Shell environment

### Installation (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install curl jq
```

### Installation (macOS)
```bash
brew install curl jq
```

---

## 📚 Example Usage Scenarios

### Scenario 1: New Developer Setup
```bash
# 1. Check if server is running and tools are available
./list_all_tools.sh

# 2. Get familiar with available tools
./get_tool_details.sh all

# 3. Run quick tests to verify everything works
./test_tool_availability.sh
```

### Scenario 2: Debugging Tool Issues
```bash
# 1. Test specific tool that's having issues
./get_tool_details.sh journeys

# 2. Check parameter requirements
./show_tool_parameters.sh

# 3. Run comprehensive tests
./test_tool_availability.sh
```

### Scenario 3: Integration Testing
```bash
# 1. Verify all tools are accessible
./list_all_tools.sh

# 2. Run full test suite before deployment
./test_tool_availability.sh
```

---

## 🔍 Troubleshooting

### Common Issues

#### Server Not Running
```bash
# Error: MCP server is not accessible
# Solution: Start the server
python -m awslabs.tmf_oda_transformer_mcp_server.mcp_http_server
```

#### Tools Not Accessible
```bash
# Check server status first
curl -s http://localhost:8000

# Verify tools endpoint
curl -s http://localhost:8000/tools
```

#### Permission Issues
```bash
# Make scripts executable
chmod +x *.sh
```

### Debug Commands
```bash
# Test specific tool manually
curl -X POST http://localhost:8000/tools/raw-analysis \
  -H 'Content-Type: application/json' \
  -d '{"journey_id": "TEST-001"}'

# Check server logs
# (Refer to your server startup logs)
```

---

## 📊 Test Results Interpretation

### Success Rates
- **90%+**: Excellent - Ready for production
- **70-89%**: Good - Minor issues to address
- **<70%**: Critical issues - Requires investigation

### Common Test Failures
1. **Connectivity Issues** - Server not running or network problems
2. **Parameter Validation** - Missing required parameters
3. **Response Format** - JSON structure issues
4. **Performance** - Slow response times (>5 seconds)

---

## 🔄 Script Maintenance

### Updating Server URL
Edit the configuration section in each script:
```bash
SERVER_URL="http://your-server:port"
TOOLS_ENDPOINT="$SERVER_URL/tools"
```

### Adding New Tools
When new tools are added to the MCP server:
1. Update tool lists in all scripts
2. Add tool-specific parameter documentation
3. Add test cases for new tools

---

## 📞 Support

For issues with these testing scripts:
1. Check server logs for detailed error information
2. Verify all prerequisites are installed
3. Ensure MCP server is running and accessible
4. Review the troubleshooting section above

For TMF ODA Transformer specific issues:
- Refer to the main project documentation
- Check server configuration and AWS credentials
- Review journey and job management guides

---

## ✅ Script Summary

| Script | Purpose | Output | Time |
|--------|---------|--------|------|
| `list_all_tools.sh` | Tool discovery & overview | Tool list with status | ~30s |
| `get_tool_details.sh` | Detailed tool documentation | Comprehensive tool info | ~10s |
| `show_tool_parameters.sh` | Parameter reference | Complete parameter docs | ~5s |
| `test_tool_availability.sh` | Comprehensive testing | Full test report | ~2-5min |

**Total Testing Time**: ~3-6 minutes for complete MCP server validation

All scripts are designed to be:
- ✅ **Self-contained** - No external dependencies beyond curl/jq
- ✅ **Error-resilient** - Handle server issues gracefully
- ✅ **Informative** - Provide clear, actionable output
- ✅ **Fast** - Complete testing in under 5 minutes 

---

## 📊 Detailed Tool Documentation

### `logs_and_reports_tool`

**Purpose**: Comprehensive logs and reports management for TMF ODA journey jobs

**Category**: Management & Analysis

**Tool Name**: `logs_and_reports_tool`

**Endpoint**: `/tools/logs_and_reports_tool`

**Description**: Provides comprehensive log retrieval, searching, filtering, report generation, performance analysis, and error pattern detection for transformation jobs.

#### Actions Supported (16)

**Log Operations:**
1. **`get_job_logs`** - Retrieve logs for a specific job
   - Required: `journey_id`, `job_id`, `stage_name`
   - Optional: `step_name`, `limit`
   
2. **`add_log_entry`** - Add a log entry to a job
   - Required: `journey_id`, `job_id`, `stage_name`, `step_name`, `log_level`, `log_message`
   - Optional: `log_source`, `log_details`
   
3. **`search_logs`** - Search through logs with query
   - Required: `journey_id`, `search_query`
   - Optional: `job_id`, `level_filter`, `step_filter`, `limit`
   
4. **`get_logs_by_level`** - Filter logs by severity level
   - Required: `journey_id`, `log_level`
   - Optional: `job_id`, `limit`
   - Supported levels: `error`, `warning`, `info`, `debug`
   
5. **`export_job_logs`** - Export logs to file
   - Required: `journey_id`, `job_id`, `output_file`
   - Optional: `export_format` (json/csv/txt/html)
   
6. **`get_error_summary`** - Get error analysis summary
   - Required: `journey_id`
   - Optional: `job_id`
   
7. **`list_available_logs`** - List available log sources
   - Required: `journey_id`
   - Optional: `job_id`

**Report Operations:**
8. **`get_job_reports`** - Get reports for a job
   - Required: `journey_id`, `job_id`
   - Optional: `stage_name`
   
9. **`create_job_report`** - Create custom report
   - Required: `journey_id`, `job_id`, `report_type`, `report_title`, `report_content`
   - Optional: `report_summary`
   
10. **`generate_summary_report`** - Generate comprehensive job summary
    - Required: `journey_id`, `job_id`
    
11. **`generate_performance_report`** - Generate performance analysis
    - Required: `journey_id`, `job_id`
    
12. **`generate_error_analysis_report`** - Generate error analysis
    - Required: `journey_id`, `job_id`
    
13. **`list_available_reports`** - List available reports
    - Required: `journey_id`
    - Optional: `job_id`
    
14. **`export_reports`** - Export reports to file
    - Required: `journey_id`, `job_id`, `output_file`
    - Optional: `export_format`

**Analysis Operations:**
15. **`analyze_job_performance`** - Analyze performance metrics
    - Required: `journey_id`, `job_id`
    
16. **`analyze_error_patterns`** - Analyze error patterns
    - Required: `journey_id`
    - Optional: `job_id`

#### Example Usage

**Get Job Logs:**
```bash
curl -X POST http://localhost:8000/tools/logs_and_reports_tool \
  -H "Content-Type: application/json" \
  -d '{
    "action": "get_job_logs",
    "journey_id": "JRN-123",
    "job_id": "JOB-456",
    "stage_name": "raw_analysis"
  }'
```

**Search Logs:**
```bash
curl -X POST http://localhost:8000/tools/logs_and_reports_tool \
  -H "Content-Type: application/json" \
  -d '{
    "action": "search_logs",
    "journey_id": "JRN-123",
    "search_query": "error",
    "level_filter": "error",
    "limit": 50
  }'
```

**Generate Performance Report:**
```bash
curl -X POST http://localhost:8000/tools/logs_and_reports_tool \
  -H "Content-Type: application/json" \
  -d '{
    "action": "generate_performance_report",
    "journey_id": "JRN-123",
    "job_id": "JOB-456"
  }'
```

**Get Error Summary:**
```bash
curl -X POST http://localhost:8000/tools/logs_and_reports_tool \
  -H "Content-Type: application/json" \
  -d '{
    "action": "get_error_summary",
    "journey_id": "JRN-123",
    "job_id": "JOB-456"
  }'
```

#### Response Format (Rule 9.1 Compliant)

All responses follow the standardized format:

**Success Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Retrieved 45 log entries for job JOB-456",
    "operation": "get_job_logs",
    "data": {...},
    "metadata": {
      "total_count": 45,
      "job_id": "JOB-456"
    }
  },
  "timestamp": "2025-10-13T10:00:00Z"
}
```

**Error Response:**
```json
{
  "result": {
    "status": "error",
    "message": "Job not found",
    "operation": "get_job_logs",
    "error_code": "NOT_FOUND",
    "error_details": {}
  },
  "timestamp": "2025-10-13T10:00:00Z"
}
```

#### Testing

**Integration Test Script:**
```bash
# Local server
cd testscripts/logs-and-reports
./test_logs_and_reports_tool.sh

# With specific journey
./test_logs_and_reports_tool.sh http://localhost:8000 JRN-123

# Remote server
./test_logs_and_reports_tool.sh http://18.191.87.212:8000 JRN-PROD-001
```

**Test Coverage:**
- ✅ All 16 actions tested
- ✅ Parameter validation
- ✅ Error handling
- ✅ Response format compliance (Rule 9.1)
- ✅ Field naming compliance (Rule 9.2 - camelCase)
- ✅ Multiple export formats
- ✅ Advanced filtering combinations

---