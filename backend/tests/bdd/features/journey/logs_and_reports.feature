Feature: Job Logs and Reports Management
  As a transformation manager
  I want to manage job logs and generate reports
  So that I can monitor, debug, and analyze job executions

  Background:
    Given the MCP server is running
    And a journey exists with running jobs
    And I have valid authentication

  @logs @get_logs
  Scenario: Retrieve logs for a specific job and stage
    Given a job "JOB-001" exists in journey "JRN-TEST-001"
    And the job has completed stage "raw_analysis"
    When I request logs for job "JOB-001" and stage "raw_analysis"
    Then I should receive log entries for the job
    And each log entry should have:
      | field     |
      | timestamp |
      | level     |
      | message   |
      | source    |

  @logs @filter_step
  Scenario: Retrieve logs filtered by step name
    Given a job with logs from multiple steps
    When I request logs for job "JOB-001" stage "raw_analysis" and step "schema_parsing"
    Then I should receive only logs from step "schema_parsing"
    And logs from other steps should not be included

  @logs @search
  Scenario: Search logs with query string
    Given multiple jobs have generated logs
    When I search logs in journey "JRN-TEST-001" with query "schema"
    Then I should receive logs containing "schema" in the message
    And the results should be limited to 50 entries by default

  @logs @search @filter
  Scenario: Search logs with level and step filters
    Given multiple jobs with various log levels
    When I search logs with query "error" and level filter "error"
    Then I should receive only error-level logs
    And all logs should contain "error" in the message

  @logs @filter_level
  Scenario Outline: Filter logs by severity level
    Given multiple jobs with logs at various severity levels
    When I request logs for journey "JRN-TEST-001" filtered by level "<level>"
    Then I should receive only "<level>" level logs
    And the logs should be ordered by timestamp descending
    
    Examples:
      | level   |
      | error   |
      | warning |
      | info    |
      | debug   |

  @logs @error_summary
  Scenario: Get error summary for a job
    Given a job "JOB-002" has encountered errors
    When I request error summary for job "JOB-002"
    Then I should receive an error summary containing:
      | field               |
      | totalErrors         |
      | errorsByStage       |
      | errorsByType        |
      | mostRecentErrors    |
      | errorTimeline       |

  @logs @list_sources
  Scenario: List available log sources
    Given multiple jobs have generated logs
    When I request available log sources for journey "JRN-TEST-001"
    Then I should receive a list of log sources including:
      | source          |
      | system          |
      | stage_execution |
      | data_processing |
      | validation      |

  @logs @list_sources_job
  Scenario: List log sources for specific job
    Given a job "JOB-003" has generated logs
    When I request available log sources for job "JOB-003"
    Then I should receive only log sources used by that job

  @logs @add_entry
  Scenario: Add log entry programmatically
    Given a job "JOB-004" is running
    When I add a log entry with:
      | field      | value                           |
      | log_level  | info                            |
      | log_message| Custom log entry for testing    |
      | stage_name | raw_analysis                    |
      | log_source | test_script                     |
    Then the log entry should be saved successfully
    And I should be able to retrieve it in the job logs

  @logs @export
  Scenario Outline: Export job logs to different formats
    Given a job "JOB-005" has completed with logs
    When I export logs to file "<filename>" in format "<format>"
    Then the export should complete successfully
    And the file should exist at "<filename>"
    And the file should be in "<format>" format
    
    Examples:
      | filename              | format |
      | job_logs.json         | json   |
      | job_logs.csv          | csv    |
      | job_logs.txt          | txt    |
      | job_logs.html         | html   |

  @logs @pagination
  Scenario: Paginate through large log sets
    Given a job has generated 500 log entries
    When I request logs with limit 100 and offset 0
    Then I should receive 100 log entries
    When I request logs with limit 100 and offset 100
    Then I should receive the next 100 log entries
    And the results should not overlap with previous page

  @logs @time_filter
  Scenario: Filter logs by time range
    Given logs exist spanning multiple days
    When I request logs from "2024-12-01T00:00:00Z" to "2024-12-02T00:00:00Z"
    Then I should receive only logs within that time range
    And logs outside the range should be excluded

  @reports @get_reports
  Scenario: Retrieve all reports for a job
    Given a job "JOB-006" has generated multiple reports
    When I request reports for job "JOB-006"
    Then I should receive all available reports
    And each report should have:
      | field        |
      | reportId     |
      | reportType   |
      | reportTitle  |
      | createdAt    |
      | reportSummary|

  @reports @create_custom
  Scenario: Create custom report
    Given a job "JOB-007" has completed
    When I create a custom report with:
      | field          | value                              |
      | report_type    | custom                             |
      | report_title   | Custom Test Report                 |
      | report_summary | Test report for integration testing|
    And report content includes:
      | key        | value                |
      | test_data  | Integration test run |
      | status     | passed               |
    Then the report should be created successfully
    And I should receive a report ID

  @reports @generate_summary
  Scenario: Generate comprehensive summary report
    Given a job "JOB-008" has completed execution
    When I generate a summary report for job "JOB-008"
    Then the report should include:
      | section              |
      | jobMetadata          |
      | executionSummary     |
      | stageResults         |
      | recordsProcessed     |
      | errorsAndWarnings    |
      | performanceMetrics   |

  @reports @generate_performance
  Scenario: Generate performance analysis report
    Given a job "JOB-009" has completed with performance metrics
    When I generate a performance report for job "JOB-009"
    Then the report should include:
      | metric                |
      | totalExecutionTime    |
      | stageExecutionTimes   |
      | recordsPerSecond      |
      | bottleneckAnalysis    |
      | resourceUtilization   |

  @reports @generate_error_analysis
  Scenario: Generate error analysis report
    Given a job "JOB-010" has encountered various errors
    When I generate an error analysis report for job "JOB-010"
    Then the report should include:
      | section                 |
      | errorSummary            |
      | errorsByStage           |
      | errorPatterns           |
      | errorTimeline           |
      | resolutionSuggestions   |

  @reports @list_available
  Scenario: List all available report types
    Given reports exist for various jobs
    When I request available reports for journey "JRN-TEST-001"
    Then I should receive a list of available report types
    And I should see counts for each report type

  @reports @export
  Scenario: Export reports to file
    Given multiple reports exist for job "JOB-011"
    When I export reports to file "reports_export.json"
    Then all reports should be exported successfully
    And the export file should contain all report data

  @analysis @performance
  Scenario: Analyze job performance metrics
    Given a job "JOB-012" has completed with timing data
    When I analyze performance for job "JOB-012"
    Then I should receive performance analysis including:
      | metric                    |
      | overallPerformanceScore   |
      | slowestStages             |
      | performanceBottlenecks    |
      | comparisonToAverage       |
      | optimizationSuggestions   |

  @analysis @error_patterns
  Scenario: Analyze error patterns across jobs
    Given multiple jobs have encountered errors
    When I analyze error patterns for journey "JRN-TEST-001"
    Then I should receive pattern analysis including:
      | insight                  |
      | commonErrorMessages      |
      | errorFrequencyByStage    |
      | errorTrends              |
      | affectedRecordPatterns   |

  @logs @reports @integration
  Scenario: Complete logs and reports workflow
    Given a job "JOB-013" has completed execution
    When I retrieve all logs for the job
    And I generate a summary report
    And I generate an error analysis report
    And I export logs to JSON format
    And I export reports to JSON format
    Then all operations should complete successfully
    And I should have comprehensive job documentation

  @logs @error_handling
  Scenario: Handle missing job logs gracefully
    When I request logs for non-existent job "JOB-INVALID"
    Then I should receive an error response
    And the error message should indicate "Job not found"

  @reports @error_handling
  Scenario: Handle missing report gracefully
    When I request reports for non-existent job "JOB-INVALID"
    Then I should receive an error response
    And the error should be handled gracefully

  @logs @validation
  Scenario: Validate log level parameter
    When I try to filter logs with invalid level "invalid_level"
    Then I should receive a validation error
    And the error should list valid log levels

  @reports @validation
  Scenario: Validate report type parameter
    When I try to create a report with invalid type "invalid_type"
    Then I should receive a validation error
    And the error should list valid report types

