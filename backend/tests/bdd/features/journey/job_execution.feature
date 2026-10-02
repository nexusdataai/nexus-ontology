Feature: Job Execution and Monitoring
  As a transformation manager
  I want to execute and monitor transformation jobs
  So that I can process data through the defined journey stages

  Background:
    Given the Journey Manager CLI is running
    And I am authenticated as "test-user@example.com"
    And a journey "JRN-EXEC-TEST" exists 
    And the journey has configured stages and rules
    And the journey is selected as current

  @execution @single_stage
  Scenario: Execute a single stage
    Given the stage "raw_analysis" is ready for execution
    When I navigate to "Job Execution"
    And I select "Execute Single Stage"
    And I choose stage "raw_analysis"
    And I confirm execution parameters:
      | parameter        | value                    |
      | input_location  | s3://data/input/raw.json |
      | output_location | s3://data/output/       |
      | retry_on_failure| yes                     |
    Then I should see "Job started successfully"
    And a job ID should be generated starting with "JOB-"
    And the job status should show "running"

  @execution @full_journey
  Scenario: Execute complete journey
    Given all stages are configured and enabled
    When I navigate to "Job Execution"
    And I select "Execute Journey"
    And I confirm journey execution with options:
      | option              | value |
      | skip_completed     | yes   |
      | stop_on_error      | no    |
      | parallel_stages    | yes   |
    Then I should see "Journey execution started"
    And the first stage should begin execution
    And progress should be tracked for each stage

  @execution @monitoring
  Scenario: Monitor running job progress
    Given a job is currently running for stage "tmf_mapping"
    When I navigate to "Job Execution"
    And I select "Monitor Jobs"
    Then I should see the running job with:
      | field             | visible |
      | Job ID            | yes     |
      | Stage Name        | yes     |
      | Status            | yes     |
      | Progress %        | yes     |
      | Records Processed | yes     |
      | Start Time        | yes     |
      | Elapsed Time      | yes     |
    And the progress should update in real-time

  @execution @pause_resume
  Scenario: Pause and resume job execution
    Given a job is running for the journey
    When I navigate to "Job Execution"
    And I select "Pause Job"
    And I confirm the pause action
    Then the job status should change to "paused"
    And no new records should be processed
    When I select "Resume Job"
    Then the job should continue from where it paused
    And the status should change back to "running"

  @execution @cancel
  Scenario: Cancel running job
    Given a job is running with ID "JOB-TEST-001"
    When I navigate to "Job Execution"
    And I select "Cancel Job"
    And I choose job "JOB-TEST-001"
    And I confirm cancellation
    Then I should see "Job cancelled successfully"
    And the job status should be "cancelled"
    And partial results should be preserved

  @execution @retry
  Scenario: Retry failed job
    Given a job has failed with ID "JOB-TEST-002"
    When I navigate to "Job Execution"
    And I select "Retry Failed Job"
    And I choose job "JOB-TEST-002"
    And I select retry options:
      | option           | value           |
      | retry_from      | point_of_failure|
      | max_retries     | 3              |
      | backoff_strategy| exponential    |
    Then a new job should be created
    And it should start from the failure point
    And the original job should be linked

  @execution @logs
  Scenario: View job execution logs
    Given a completed job exists with logs
    When I navigate to "Logs & Reports"
    And I select "View Job Logs"
    And I choose a specific job
    Then I should see detailed logs including:
      | log_type        | content                    |
      | INFO           | Processing started         |
      | DEBUG          | Record validation details  |
      | WARNING        | Data quality issues        |
      | ERROR          | Failed record details      |
    And I should be able to filter by log level

  @execution @metrics
  Scenario: View execution metrics
    Given multiple jobs have been executed
    When I navigate to "Logs & Reports"
    And I select "Execution Metrics"
    Then I should see metrics including:
      | metric                | value_type |
      | Total Records        | number     |
      | Success Rate         | percentage |
      | Average Duration     | time       |
      | Error Rate          | percentage |
      | Throughput          | records/sec|
    And I should be able to view trends over time

  @execution @error_handling
  Scenario: Handle execution errors gracefully
    Given a job encounters an error during execution
    When the error occurs
    Then the error should be logged with details
    And the job should follow the configured error strategy:
      | strategy    | action                           |
      | retry      | Attempt retry with backoff       |
      | skip       | Skip record and continue         |
      | fail       | Stop execution and mark failed   |
    And error notifications should be sent

  @execution @dependencies
  Scenario: Execute stages with dependencies
    Given stage "tmf_mapping" depends on "stripped_schema" completion
    When executing the journey
    Then "stripped_schema" should execute first
    And "tmf_mapping" should wait for completion
    When "stripped_schema" completes successfully
    Then "tmf_mapping" should start automatically

  @execution @parallel
  Scenario: Execute independent stages in parallel
    Given stages "validation" and "analysis" have no dependencies
    When executing with parallel mode enabled
    Then both stages should start simultaneously
    And resources should be allocated appropriately
    And completion should wait for both stages

  @execution @schedule
  Scenario: Schedule job execution
    Given I want to schedule a recurring execution
    When I navigate to "Job Execution"
    And I select "Schedule Job"
    And I configure schedule:
      | field          | value              |
      | frequency      | daily             |
      | time          | 02:00 UTC         |
      | days          | weekdays          |
      | notification  | on_failure_only   |
    Then the schedule should be created
    And jobs should execute automatically
    And execution history should be maintained

  @execution @data_validation
  Scenario: Validate data before execution
    Given I am about to execute a stage
    When I enable pre-execution validation
    Then the system should:
      | check                    | action                |
      | Input file exists       | Verify S3 location    |
      | Schema compatibility    | Validate structure    |
      | Required fields present | Check completeness    |
      | Data format correct     | Verify formatting     |
    And validation errors should prevent execution
    And a validation report should be generated
