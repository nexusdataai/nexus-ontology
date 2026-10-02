Feature: Job Lifecycle Management
  As a transformation manager
  I want to manage job execution and lifecycle
  So that I can control and monitor transformation jobs

  Background:
    Given the MCP server is running
    And a journey exists with configured stages
    And I have valid authentication

  @job @execution @trigger
  Scenario Outline: Execute job with different trigger types
    Given a journey "JRN-TEST-001" has stages configured
    When I execute a job on stage "raw_analysis" triggered by "<trigger>" with reason "<reason>"
    Then the job should start successfully
    And the job should have ID starting with "JOB-"
    And the job metadata should record trigger type "<trigger>"
    And the job should be in "pending" or "running" status
    
    Examples:
      | trigger | reason                          |
      | system  | Automated system execution      |
      | user    | Manual user-initiated execution |
      | api     | API-triggered execution         |
      | cli     | Command-line execution          |
      | test    | Test execution                  |

  @job @execution @basic
  Scenario: Execute job with minimal parameters
    Given a journey "JRN-TEST-002" exists
    And the journey has stage "raw_analysis"
    When I execute a job on stage "raw_analysis" triggered by "system"
    Then the job should start successfully
    And I should receive a job ID
    And the job should be trackable

  @job @execution @detailed
  Scenario: Execute job with detailed reason
    Given a journey "JRN-TEST-003" exists
    When I execute a job with parameters:
      | parameter    | value                                              |
      | stage_id     | raw_analysis                                       |
      | triggered_by | cli                                                |
      | reason       | Detailed execution for audit trail and compliance |
    Then the job should start successfully
    And the reason should be recorded in job metadata

  @job @execution @multiple_stages
  Scenario: Execute jobs on different stages
    Given a journey "JRN-TEST-004" has multiple stages
    When I execute a job on stage "raw_analysis"
    And I execute a job on stage "stripped_schema"
    And I execute a job on stage "tmf_mapping"
    Then all jobs should start successfully
    And each job should be for the correct stage

  @job @status @update
  Scenario: Update job status
    Given a job "JOB-STATUS-001" is running
    When I update the job status to "running" with progress 50
    Then the status update should succeed
    And the job progress should be 50 percent

  @job @status @progression
  Scenario: Job status progression
    Given a job "JOB-PROG-001" exists for lifecycle testing
    When I update the job status to "running" with progress 25
    And I update the job status to "running" with progress 50
    And I update the job status to "running" with progress 75
    And I update the job status to "completed" with progress 100
    Then all status updates should succeed
    And the final status should be "completed"

  @job @status @with_message
  Scenario: Update job status with current step
    Given a job "JOB-STEP-001" is running
    When I update the job status with:
      | field        | value                      |
      | job_status   | running                    |
      | progress     | 60                         |
      | current_step | Processing schema mapping  |
    Then the status should be updated
    And the current step should be recorded

  @job @metrics
  Scenario: Retrieve job metrics
    Given a job "JOB-METRICS-001" has completed
    When I request metrics for the job
    Then I should receive metrics including:
      | metric              |
      | totalExecutionTime  |
      | recordsProcessed    |
      | errorCount          |
      | warningCount        |
      | stageMetrics        |
      | logMetrics          |

  @job @metrics @performance
  Scenario: Get job performance metrics
    Given a job "JOB-PERF-001" has completed with timing data
    When I request job metrics
    Then the metrics should include:
      | field                |
      | executionStartTime   |
      | executionEndTime     |
      | totalDuration        |
      | stageExecutionTimes  |
      | recordsPerSecond     |

  @job @timeline
  Scenario: Retrieve job timeline
    Given a job "JOB-TIMELINE-001" has execution history for timeline
    When I request the job timeline
    Then I should receive timeline events including:
      | event_type      |
      | job_created     |
      | job_started     |
      | stage_started   |
      | stage_completed |
      | status_updated  |

  @job @timeline @detailed
  Scenario: Get detailed job timeline with timestamps
    Given a job "JOB-TIMELINE-002" has completed
    When I request the detailed job timeline
    Then each timeline event should have:
      | field       |
      | timestamp   |
      | event_type  |
      | description |
      | details     |

  @job @batch @cancel
  Scenario: Batch cancel multiple jobs
    Given a journey has 5 running jobs
    When I batch cancel 3 jobs with reason "Testing batch cancellation"
    Then 3 jobs should be marked as cancelled
    And the cancellation reason should be recorded
    And remaining 2 jobs should continue running

  @job @batch @cancel_all
  Scenario: Cancel all jobs for a journey
    Given a journey "JRN-BATCH-001" has multiple running jobs
    When I batch cancel all jobs with reason "Emergency stop"
    Then all jobs should be cancelled
    And the cancellation should be logged

  @job @batch @operations
  Scenario: Batch job status updates
    Given multiple jobs are running
    When I batch update job statuses
    Then all updates should succeed
    And each job should reflect its new status

  @job @list
  Scenario: List all jobs for a journey
    Given a journey "JRN-LIST-001" has 10 jobs
    When I list all jobs for the journey
    Then I should receive 10 job records
    And each job should have basic metadata

  @job @list @filter
  Scenario: Filter jobs by status
    Given a journey has jobs in various statuses
    When I list jobs filtered by status "completed"
    Then I should receive only completed jobs
    And running jobs should not be included

  @job @list @pagination
  Scenario: Paginate through large job list
    Given a journey has 100 jobs
    When I list jobs with limit 20 and offset 0
    Then I should receive 20 jobs
    When I list jobs with limit 20 and offset 20
    Then I should receive the next 20 jobs

  @job @dashboard
  Scenario: Get job dashboard for journey
    Given a journey "JRN-DASH-001" has multiple jobs
    When I request the journey dashboard
    Then the dashboard should include:
      | section            |
      | summary            |
      | jobStatistics      |
      | recentJobs         |
      | errorSummary       |
      | performanceMetrics |

  @job @summary
  Scenario: Get journey summary with job stats
    Given a journey "JRN-SUMMARY-001" has completed jobs
    When I request the journey summary
    Then the summary should include:
      | field           |
      | totalJobs       |
      | completedJobs   |
      | failedJobs      |
      | runningJobs     |
      | pendingJobs     |
      | averageDuration |

  @job @error_handling @invalid_journey
  Scenario: Handle job execution on invalid journey
    When I try to execute a job on non-existent journey "INVALID-JRN"
    Then I should receive an error response
    And the error should indicate "Journey not found"

  @job @error_handling @invalid_stage
  Scenario: Handle job execution on invalid stage
    Given a journey "JRN-ERR-001" exists
    When I try to execute a job on non-existent stage "invalid_stage_xyz"
    Then I should receive an error response
    And the error should indicate invalid stage

  @job @error_handling @empty_params
  Scenario: Handle empty journey ID
    When I try to execute a job with empty journey ID
    Then I should receive a validation error
    And the error should indicate required parameter missing

  @job @error_handling @empty_stage
  Scenario: Handle empty stage ID
    Given a journey "JRN-ERR-002" exists
    When I try to execute a job with empty stage ID
    Then I should receive a validation error
    And the error should indicate stage ID required

  @job @error_handling @invalid_status
  Scenario: Handle invalid status update
    Given a job "JOB-ERR-001" exists for lifecycle testing
    When I try to update job status to "invalid_status"
    Then I should receive a validation error
    And the error should list valid status values

  @job @concurrent
  Scenario: Handle concurrent job executions
    Given a journey "JRN-CONCURRENT-001" exists
    When I execute 3 jobs simultaneously on different stages
    Then all 3 jobs should start successfully
    And each job should have a unique ID
    And there should be no race conditions

  @job @retries
  Scenario: Job execution with retries
    Given a job configuration with retry policy
    When a job fails during execution
    Then the system should retry according to policy
    And retry attempts should be logged

  @job @workflow
  Scenario: Complete job lifecycle workflow
    Given a journey "JRN-WORKFLOW-001" is ready
    When I execute a job on stage "raw_analysis"
    And I monitor the job status
    And I retrieve job metrics periodically
    And I check the job timeline
    Then I should have complete visibility into job execution
    And all operations should complete successfully

  @job @cleanup
  Scenario: Clean up completed jobs
    Given a journey has 50 completed jobs older than 30 days
    When I request cleanup of old jobs
    Then old jobs should be archived or removed
    And recent jobs should remain accessible

  @job @monitoring
  Scenario: Monitor job health
    Given multiple jobs are running
    When I request job health status
    Then I should receive health metrics for each job
    And stuck jobs should be identified
    And performance issues should be flagged

