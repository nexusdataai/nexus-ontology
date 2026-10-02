# `logs_and_reports_tool`

**Purpose:** Comprehensive logs and reports management for TMF ODA journey jobs. Supports log retrieval, searching, filtering, report generation, performance analysis, and error pattern detection.

## Parameters

### Common Parameters
- `action` (required) - Action to perform (see Actions section)
- `journey_id` - Journey ID (required for most operations)
- `job_id` - Job ID (required for job-specific operations)
- `stage_name` - Stage name (required for get_job_logs, add_log_entry)
- `step_name` - Step name (for specific step logs)

### Log Operation Parameters
- `log_level` - Log level: error, warning, info, debug
- `log_message` - Log message text (for add_log_entry)
- `search_query` - Search query string (for search_logs)
- `log_source` - Log source identifier (default: "system")
- `log_details` - Additional log details as dict

### Report Operation Parameters
- `report_type` - Report type: summary, performance, error_analysis, custom, timeline, metrics
- `report_title` - Report title (for create_job_report)
- `report_content` - Report content data as dict (for create_job_report)
- `report_summary` - Report summary text

### Export Parameters
- `output_file` - Output file path (for export operations)
- `export_format` - Export format: json, csv, txt, html (default: json)

### Filter Parameters
- `level_filter` - Filter logs by level (error, warning, info, debug)
- `step_filter` - Filter logs by step name
- `start_time` - Start time filter (ISO 8601 format)
- `end_time` - End time filter (ISO 8601 format)

### Pagination Parameters
- `limit` - Result limit (default: 100, max: 1000)
- `offset` - Result offset (default: 0)

---

## Actions (16 Total)

### Log Operations (7 actions)

#### `get_job_logs`
Get all logs for a specific job and stage.

**Required Parameters:**
- `journey_id`
- `job_id`
- `stage_name`

**Optional Parameters:**
- `step_name` - Filter by specific step

**Example Request:**
```json
{
  "action": "get_job_logs",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "stage_name": "raw_analysis"
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Retrieved 145 log entries for job JOB-456",
    "operation": "get_job_logs",
    "data": {
      "jobId": "JOB-456",
      "stageId": "raw_analysis",
      "totalLogs": 145,
      "logs": [
        {
          "timestamp": "2025-11-01T20:00:15.234Z",
          "level": "info",
          "step": "schema_extraction",
          "message": "Starting schema extraction from source database",
          "source": "system",
          "details": {
            "database": "legacy_catalog",
            "table_count": 45
          }
        }
      ],
      "summary": {
        "errorCount": 2,
        "warningCount": 8,
        "infoCount": 120,
        "debugCount": 15
      }
    },
    "metadata": {
      "total_count": 145,
      "job_id": "JOB-456",
      "stage_name": "raw_analysis"
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

#### `add_log_entry`
Add a new log entry to a job.

**Required Parameters:**
- `journey_id`
- `job_id`
- `stage_name`
- `step_name`
- `log_level` (error, warning, info, debug)
- `log_message`

**Optional Parameters:**
- `log_source` (default: "system")
- `log_details` - Additional context as dict

**Example Request:**
```json
{
  "action": "add_log_entry",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "stage_name": "raw_analysis",
  "step_name": "schema_extraction",
  "log_level": "info",
  "log_message": "Successfully extracted 45 tables from source database",
  "log_details": {
    "tables_extracted": 45,
    "duration_seconds": 12.5
  }
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Log entry added successfully for job JOB-456",
    "operation": "add_log_entry",
    "data": {
      "jobId": "JOB-456",
      "stepName": "schema_extraction",
      "level": "info",
      "added": true
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

#### `search_logs`
Search through logs with query and filters.

**Required Parameters:**
- `journey_id`
- `search_query` - Text to search for in log messages

**Optional Parameters:**
- `job_id` - Filter by specific job
- `level_filter` - Filter by log level
- `step_filter` - Filter by step name
- `limit` - Maximum results (default: 100)

**Example Request:**
```json
{
  "action": "search_logs",
  "journey_id": "JRN-ABC123",
  "search_query": "failed to parse",
  "level_filter": "error",
  "limit": 50
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Found 12 matching log entries",
    "operation": "search_logs",
    "data": {
      "totalMatches": 12,
      "logs": [
        {
          "jobId": "JOB-456",
          "timestamp": "2025-11-01T20:05:23.456Z",
          "level": "error",
          "step": "schema_parsing",
          "message": "Failed to parse column definition: invalid_column",
          "source": "parser"
        }
      ],
      "filters": {
        "search_query": "failed to parse",
        "level": "error"
      }
    },
    "metadata": {
      "total_count": 12,
      "search_query": "failed to parse",
      "filters": {
        "level": "error"
      }
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

#### `get_logs_by_level`
Get all logs filtered by specific level.

**Required Parameters:**
- `journey_id`
- `log_level` (error, warning, info, debug)

**Optional Parameters:**
- `job_id` - Filter by specific job
- `limit` - Maximum results (default: 100)

**Example Request:**
```json
{
  "action": "get_logs_by_level",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "log_level": "error",
  "limit": 20
}
```

#### `export_job_logs`
Export job logs to a file in various formats.

**Required Parameters:**
- `journey_id`
- `job_id`
- `output_file` - Path to output file

**Optional Parameters:**
- `export_format` - Format: json, csv, txt, html (default: json)

**Example Request:**
```json
{
  "action": "export_job_logs",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "output_file": "/tmp/job_logs.json",
  "export_format": "json"
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Logs exported successfully to /tmp/job_logs.json",
    "operation": "export_job_logs",
    "data": {
      "jobId": "JOB-456",
      "outputFile": "/tmp/job_logs.json",
      "format": "json",
      "exported": true
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

#### `get_error_summary`
Get comprehensive error and warning summary for a job.

**Required Parameters:**
- `journey_id`
- `job_id`

**Example Request:**
```json
{
  "action": "get_error_summary",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Error summary generated: 5 errors, 12 warnings",
    "operation": "get_error_summary",
    "data": {
      "summary": {
        "journeyId": "JRN-ABC123",
        "jobId": "JOB-456",
        "totalErrors": 5,
        "totalWarnings": 12,
        "errorCategories": {
          "parsing_error": 3,
          "validation_error": 2
        },
        "errorsByStep": {
          "schema_parsing": 3,
          "data_validation": 2
        },
        "generatedAt": "2025-11-01T20:30:00Z"
      },
      "recentErrors": [
        {
          "timestamp": "2025-11-01T20:15:23Z",
          "level": "error",
          "step": "schema_parsing",
          "message": "Failed to parse column: invalid_type"
        }
      ],
      "recentWarnings": [
        {
          "timestamp": "2025-11-01T20:10:15Z",
          "level": "warning",
          "step": "data_validation",
          "message": "Missing optional field: description"
        }
      ]
    },
    "metadata": {
      "total_errors": 5,
      "total_warnings": 12
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

#### `list_available_logs`
List all available log sources for a journey or specific job.

**Required Parameters:**
- `journey_id`

**Optional Parameters:**
- `job_id` - Filter by specific job

**Example Request:**
```json
{
  "action": "list_available_logs",
  "journey_id": "JRN-ABC123"
}
```

---

### Report Operations (7 actions)

#### `get_job_reports`
Get all reports for a specific job.

**Required Parameters:**
- `journey_id`
- `job_id`

**Optional Parameters:**
- `stage_name` - Filter by specific stage

**Example Request:**
```json
{
  "action": "get_job_reports",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Retrieved 3 reports for job JOB-456",
    "operation": "get_job_reports",
    "data": {
      "totalReports": 3,
      "reports": [
        {
          "reportId": "RPT-789",
          "jobId": "JOB-456",
          "reportType": "performance",
          "title": "Performance Analysis Report",
          "summary": "Job completed in 125.5 seconds with 2 errors",
          "generatedAt": "2025-11-01T20:25:00Z",
          "status": "generated"
        }
      ]
    },
    "metadata": {
      "total_count": 3,
      "job_id": "JOB-456"
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

#### `create_job_report`
Create a custom report for a job.

**Required Parameters:**
- `journey_id`
- `job_id`
- `report_type` (summary, performance, error_analysis, custom, timeline, metrics)
- `report_title`
- `report_content` - Report data as dict

**Optional Parameters:**
- `report_summary` - Brief summary text

**Example Request:**
```json
{
  "action": "create_job_report",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "report_type": "custom",
  "report_title": "Data Quality Assessment",
  "report_summary": "Assessment of data quality issues found during transformation",
  "report_content": {
    "total_records": 10000,
    "issues_found": 45,
    "quality_score": 99.55,
    "recommendations": [
      "Review records with missing product descriptions",
      "Validate price ranges for outliers"
    ]
  }
}
```

#### `generate_summary_report`
Generate comprehensive summary report for a job.

**Required Parameters:**
- `journey_id`
- `job_id`

**Example Request:**
```json
{
  "action": "generate_summary_report",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Summary report generated for job JOB-456",
    "operation": "generate_summary_report",
    "data": {
      "reportId": "RPT-890",
      "jobId": "JOB-456",
      "reportType": "summary",
      "generatedAt": "2025-11-01T20:30:00Z",
      "summary": {
        "jobStatus": "completed",
        "totalDuration": 125.5,
        "stepsCompleted": 8,
        "totalLogs": 145,
        "errors": 2,
        "warnings": 8,
        "recordsProcessed": 10000
      },
      "highlights": [
        "Job completed successfully in 125.5 seconds",
        "Processed 10,000 records",
        "2 errors encountered and logged",
        "8 warnings requiring review"
      ]
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

#### `generate_performance_report`
Generate detailed performance analysis report.

**Required Parameters:**
- `journey_id`
- `job_id`

**Example Request:**
```json
{
  "action": "generate_performance_report",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Performance report generated with 5 recommendations",
    "operation": "generate_performance_report",
    "data": {
      "reportId": "RPT-891",
      "jobId": "JOB-456",
      "reportType": "performance_analysis",
      "generatedAt": "2025-11-01T20:30:00Z",
      "executionSummary": {
        "totalDuration": 125.5,
        "averageStepDuration": 15.7,
        "slowestStep": "schema_parsing",
        "fastestStep": "initialization"
      },
      "performanceMetrics": {
        "throughput": 79.6,
        "recordsPerSecond": 79.6,
        "errorRate": 0.02,
        "memoryUsage": "512MB",
        "cpuUtilization": "45%"
      },
      "logAnalysis": {
        "totalLogs": 145,
        "logsPerStep": 18.1,
        "errorDensity": 1.4
      },
      "recommendations": [
        "Optimize schema_parsing step (took 45s, 35% of total time)",
        "Consider parallel processing for data transformation",
        "Review memory usage patterns for potential optimization",
        "Add caching for repeated schema lookups",
        "Increase batch size for better throughput"
      ]
    },
    "metadata": {
      "recommendations_count": 5
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

#### `generate_error_analysis_report`
Generate detailed error analysis report.

**Required Parameters:**
- `journey_id`
- `job_id`

**Example Request:**
```json
{
  "action": "generate_error_analysis_report",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Error analysis report generated for job JOB-456",
    "operation": "generate_error_analysis_report",
    "data": {
      "summary": {
        "totalErrors": 5,
        "totalWarnings": 12,
        "errorCategories": {
          "parsing_error": 3,
          "validation_error": 2
        },
        "errorsByStep": {
          "schema_parsing": 3,
          "data_validation": 2
        }
      },
      "recentErrors": [
        {
          "timestamp": "2025-11-01T20:15:23Z",
          "level": "error",
          "step": "schema_parsing",
          "message": "Failed to parse column: invalid_type"
        }
      ],
      "errorPatterns": {
        "mostCommonError": "parsing_error",
        "errorTrend": "decreasing",
        "criticalErrors": 0
      }
    },
    "metadata": {
      "total_errors": 5,
      "total_warnings": 12
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

#### `list_available_reports`
List all available reports for a journey or specific job.

**Required Parameters:**
- `journey_id`

**Optional Parameters:**
- `job_id` - Filter by specific job

**Example Request:**
```json
{
  "action": "list_available_reports",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}
```

#### `export_reports`
Export reports to a file.

**Required Parameters:**
- `journey_id`
- `job_id`
- `output_file` - Path to output file

**Optional Parameters:**
- `stage_name` - Filter by specific stage
- `export_format` - Format: json (default: json)

**Example Request:**
```json
{
  "action": "export_reports",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "output_file": "/tmp/reports.json",
  "export_format": "json"
}
```

---

### Analysis Operations (2 actions)

#### `analyze_job_performance`
Perform detailed performance analysis of a job.

**Required Parameters:**
- `journey_id`
- `job_id`

**Example Request:**
```json
{
  "action": "analyze_job_performance",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Performance analysis completed for job JOB-456",
    "operation": "analyze_job_performance",
    "data": {
      "job_id": "JOB-456",
      "stage_id": "raw_analysis",
      "status": "completed",
      "progress": 100,
      "duration": 125.5,
      "totalLogs": 145,
      "errorCount": 2,
      "warningCount": 8,
      "performanceMetrics": {
        "throughput": 79.6,
        "errorRate": 0.02,
        "averageStepDuration": 15.7
      },
      "bottlenecks": [
        {
          "step": "schema_parsing",
          "duration": 45.2,
          "percentOfTotal": 36.0
        }
      ]
    },
    "metadata": {
      "duration": 125.5,
      "error_rate": 0.02
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

#### `analyze_error_patterns`
Analyze error patterns across jobs to identify trends and common issues.

**Required Parameters:**
- `journey_id`

**Optional Parameters:**
- `job_id` - Analyze specific job (otherwise analyzes all jobs)

**Example Request:**
```json
{
  "action": "analyze_error_patterns",
  "journey_id": "JRN-ABC123"
}
```

**Example Response:**
```json
{
  "result": {
    "status": "success",
    "message": "Error pattern analysis completed: 15 errors analyzed",
    "operation": "analyze_error_patterns",
    "data": {
      "errorCategories": {
        "parsing_error": 8,
        "validation_error": 5,
        "network_error": 2
      },
      "errorsByStep": {
        "schema_parsing": 8,
        "data_validation": 5,
        "api_call": 2
      },
      "totalErrors": 15,
      "totalWarnings": 28,
      "recentErrors": [
        {
          "jobId": "JOB-456",
          "timestamp": "2025-11-01T20:15:23Z",
          "level": "error",
          "step": "schema_parsing",
          "message": "Failed to parse column: invalid_type"
        }
      ],
      "recentWarnings": [],
      "analysis": {
        "mostCommonCategory": "parsing_error",
        "mostProblematicStep": "schema_parsing"
      }
    },
    "metadata": {
      "total_errors": 15,
      "total_warnings": 28
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

---

## Data Models

### Log Levels
- `debug` - Debug-level information
- `info` - Informational messages
- `warning` - Warning messages
- `error` - Error messages

### Export Formats
- `json` - JSON format (default)
- `csv` - Comma-separated values
- `txt` - Plain text format
- `html` - HTML formatted output

### Report Types
- `summary` - Job summary report
- `performance` - Performance analysis report
- `error_analysis` - Error analysis report
- `custom` - Custom report type
- `timeline` - Timeline report
- `metrics` - Metrics report

---

## Response Format (Rule 9.1)

All operations return a standardized response following Rule 9.1:

```json
{
  "result": {
    "status": "success" | "error",
    "message": "Human-readable message",
    "operation": "action_name",
    "data": { /* operation-specific data */ },
    "metadata": { /* additional metadata */ },
    "error_code": "ERROR_CODE (only if status=error)",
    "error_details": { /* error details (only if status=error) */ }
  },
  "timestamp": "ISO8601_timestamp"
}
```

**Success Response Example:**
```json
{
  "result": {
    "status": "success",
    "message": "Retrieved 145 log entries for job JOB-456",
    "operation": "get_job_logs",
    "data": { /* logs data */ },
    "metadata": {
      "total_count": 145
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

**Error Response Example:**
```json
{
  "result": {
    "status": "error",
    "message": "journey_id is required for action 'get_job_logs'",
    "operation": "get_job_logs",
    "error_code": "VALIDATION_ERROR",
    "error_details": {
      "error": "journey_id is required for action 'get_job_logs'"
    }
  },
  "timestamp": "2025-11-01T20:30:00Z"
}
```

---

## What It Does

1. **Log Management** - Retrieve, add, search, and filter job execution logs
2. **Report Generation** - Generate summary, performance, and error analysis reports
3. **Log Export** - Export logs in multiple formats (JSON, CSV, TXT, HTML)
4. **Report Export** - Export reports to files for archival or sharing
5. **Performance Analysis** - Analyze job performance metrics and identify bottlenecks
6. **Error Pattern Detection** - Identify error trends and common issues across jobs
7. **Data Aggregation** - Aggregate logs and metrics for comprehensive analysis
8. **Validation** - Uses Pydantic models to validate all parameters
9. **Async Operations** - All operations run asynchronously via LogsAndReportsService
10. **Decimal Conversion** - Automatically converts DynamoDB Decimal types to float

---

## Error Handling

The tool provides detailed error responses for:
- **Validation Errors** - Missing or invalid required parameters
- **Retrieval Errors** - Failed to retrieve logs or reports
- **Not Found Errors** - Logs or reports not found
- **Export Errors** - Failed to export logs or reports
- **Internal Errors** - Unexpected errors during processing

Error codes:
- `VALIDATION_ERROR` - Parameter validation failed
- `RETRIEVAL_FAILED` - Failed to retrieve data
- `NOT_FOUND` - Requested data not found
- `EXPORT_FAILED` - Export operation failed
- `ADD_FAILED` - Failed to add log entry
- `CREATE_FAILED` - Failed to create report
- `GENERATION_FAILED` - Failed to generate report
- `ANALYSIS_FAILED` - Failed to perform analysis
- `INTERNAL_ERROR` - Unexpected internal error
- `UNSUPPORTED_FORMAT` - Export format not supported

---

## Implementation Details

- **Service Layer**: Uses `LogsAndReportsService` for all DynamoDB and S3 operations
- **Model Layer**: Uses Pydantic models for validation (`LogsAndReportsActionRequest`)
- **Response Format**: Follows Rule 9.1 standardized format with camelCase fields
- **Async Execution**: All operations run asynchronously using `asyncio.to_thread`
- **DynamoDB Storage**: Logs and reports stored in `TransformationSystem` table
- **S3 Integration**: Log files stored in S3 buckets for archival
- **Decimal Handling**: Automatically converts DynamoDB Decimal types for JSON serialization
- **MCP Protocol**: Fully compliant with MCP tool protocol for Cursor integration

---

## Best Practices

1. **Use appropriate log levels** - Debug for development, Info for normal ops, Warning for issues, Error for failures
2. **Add context in log_details** - Include relevant data (IDs, counts, durations) for better debugging
3. **Generate reports after job completion** - Create performance and error analysis reports for post-mortem
4. **Export logs for long-term storage** - Use CSV or JSON export for archival purposes
5. **Search with specific queries** - Use focused search queries and filters for better performance
6. **Monitor error patterns** - Regularly analyze error patterns to identify systemic issues
7. **Set appropriate limits** - Use limit parameter to control result set size for large log volumes
8. **Use ISO 8601 timestamps** - Always use ISO 8601 format for time filters (YYYY-MM-DDTHH:MM:SSZ)
9. **Leverage metadata** - Check metadata in responses for total counts and filter information
10. **Combine operations** - Use search + error summary + performance report for comprehensive analysis

---

## Common Use Cases

### Use Case 1: Debugging Failed Job
```json
// 1. Get error summary
{
  "action": "get_error_summary",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}

// 2. Search for specific error
{
  "action": "search_logs",
  "journey_id": "JRN-ABC123",
  "search_query": "parsing error",
  "level_filter": "error"
}

// 3. Get all error logs
{
  "action": "get_logs_by_level",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "log_level": "error"
}
```

### Use Case 2: Performance Optimization
```json
// 1. Generate performance report
{
  "action": "generate_performance_report",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}

// 2. Analyze job performance
{
  "action": "analyze_job_performance",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}
```

### Use Case 3: Audit and Compliance
```json
// 1. Export all logs
{
  "action": "export_job_logs",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "output_file": "/audit/job_456_logs.json",
  "export_format": "json"
}

// 2. Generate summary report
{
  "action": "generate_summary_report",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456"
}

// 3. Export reports
{
  "action": "export_reports",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "output_file": "/audit/job_456_reports.json"
}
```

### Use Case 4: Real-time Monitoring
```json
// 1. Add log entry during execution
{
  "action": "add_log_entry",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "stage_name": "raw_analysis",
  "step_name": "data_extraction",
  "log_level": "info",
  "log_message": "Processing batch 5 of 10",
  "log_details": {
    "batch_number": 5,
    "records_processed": 5000,
    "progress": 50
  }
}

// 2. Get recent logs
{
  "action": "get_job_logs",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "stage_name": "raw_analysis"
}
```

---

## Integration with Journey Tool

The `logs_and_reports_tool` works seamlessly with `journeys_tool`:

1. **Journey → Job → Logs** - After creating a journey and running jobs, use this tool to monitor execution
2. **Job Metrics** - Use `journeys_tool` for job status, this tool for detailed logs and reports
3. **Error Analysis** - Cross-reference job failures from `journeys_tool` with error logs from this tool
4. **Performance Tracking** - Track job metrics in `journeys_tool`, analyze performance with this tool

**Workflow Example:**
```
1. Create journey (journeys_tool: create)
2. Add stages (journeys_tool: add_default_stages)
3. Run job (separate job execution)
4. Monitor logs (logs_and_reports_tool: get_job_logs)
5. Analyze errors (logs_and_reports_tool: get_error_summary)
6. Generate reports (logs_and_reports_tool: generate_performance_report)
7. Update job status (journeys_tool: update_job_status)
8. Export for archival (logs_and_reports_tool: export_job_logs)
```
