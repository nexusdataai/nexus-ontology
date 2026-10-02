Feature: Error Handling and Edge Cases
  As a developer using the AI Job Engine
  I want comprehensive error handling
  So that I can handle failures gracefully

  Background:
    Given the MCP server is running
    And I have valid authentication

  @error @invalid_action
  Scenario: Handle invalid action
    When I send a request with action "totally_invalid_action_xyz"
    Then I should receive an error response
    And the error should indicate "invalid"
    And the response should list valid actions

  @error @missing_parameter
  Scenario: Handle missing required parameter
    When I send a request to read a journey without journey_id
    Then I should receive a validation error
    And the error should indicate "journey_id"
    And the error should indicate "required"

  @error @invalid_journey_id
  Scenario: Handle invalid journey ID format
    When I try to read journey with ID "NOT-A-VALID-FORMAT"
    Then I should receive an error response
    And the error should indicate "not found"

  @error @non_existent_journey
  Scenario: Handle non-existent journey operations
    When I try to read journey "JRN-NONEXISTENT-999"
    Then I should receive an error response
    And the error should indicate "not found"
    And the error code should be "JOURNEY_NOT_FOUND"

  @error @non_existent_stage
  Scenario: Handle non-existent stage operations
    Given a journey "JRN-STAGE-ERR" exists
    When I try to execute job on stage "invalid_stage_xyz"
    Then I should receive an error response
    And the error should indicate invalid stage

  @error @non_existent_job
  Scenario: Handle non-existent job operations
    When I try to get logs for non-existent job "JOB-INVALID-999"
    Then I should receive an error response
    And the error should indicate "Job not found"

  @error @empty_values
  Scenario: Handle empty required values
    When I try to create a journey with empty name
    Then I should receive a validation error
    And the error should indicate name is required

  @error @null_values
  Scenario: Handle null values in required fields
    When I send a request with null values for required fields
    Then I should receive a validation error
    And invalid fields should be listed

  @error @invalid_data_types
  Scenario: Handle invalid data types
    When I send a request with:
      | field    | value      | correct_type |
      | priority | not-a-num  | number       |
      | status   | 123        | string       |
    Then I should receive a validation error
    And the error should indicate type mismatch

  @error @invalid_enum_values
  Scenario: Handle invalid enum values
    When I try to update journey status to "super_invalid_status"
    Then I should receive a validation error
    And the error should list valid status values

  @error @invalid_priority
  Scenario: Handle invalid priority values
    When I try to create journey with priority "ultra-mega-high"
    Then I should receive a validation error
    And the error should list valid priority values

  @error @malformed_json
  Scenario: Handle malformed JSON request
    When I send a malformed JSON request
    Then I should receive an error response
    And the error should indicate JSON parsing error

  @error @missing_api_key
  Scenario: Handle missing API key
    Given I remove the API key from headers
    When I try to list journeys
    Then I should receive an authentication error
    And HTTP status should be 401 or 403

  @error @invalid_api_key
  Scenario: Handle invalid API key
    Given I use an invalid API key "wrong-key-123"
    When I try to list journeys
    Then I should receive an authentication error

  @error @delete_without_confirmation
  Scenario: Handle delete without confirmation flag
    Given a journey "JRN-DELETE-NO-CONFIRM" exists
    When I try to delete the journey without confirmation
    Then I should receive an error response
    And the error should indicate confirmation required

  @error @update_immutable_fields
  Scenario: Handle update of immutable fields
    Given a journey "JRN-IMMUTABLE" exists
    When I try to update immutable fields:
      | field      | value           |
      | journeyId  | JRN-DIFFERENT   |
      | createdAt  | 2020-01-01      |
    Then the update should fail or ignore immutable fields
    And the original values should remain unchanged

  @error @concurrent_updates
  Scenario: Handle concurrent update conflicts
    Given a journey "JRN-CONCURRENT" exists
    When two users update the journey simultaneously
    Then one update should succeed
    And the other should handle the conflict appropriately

  @error @timeout
  Scenario: Handle operation timeout
    Given a journey with extremely large dataset
    When I request comprehensive data with short timeout
    Then I should receive a timeout error
    And the error should be handled gracefully

  @error @database_connection
  Scenario: Handle database connection errors
    Given the database connection is interrupted
    When I try to list journeys
    Then I should receive a service error
    And the error should indicate connectivity issue

  @error @partial_data
  Scenario: Handle partial data corruption
    Given a journey with corrupted records
    When I try to read the journey
    Then I should receive partial data
    And I should receive a data integrity error

  @error @circular_dependencies
  Scenario: Handle circular stage dependencies
    Given a journey with stages
    When I try to create circular dependencies
    Then the validation should prevent it
    And the error should explain the circular dependency

  @error @rate_limiting
  Scenario: Handle rate limit exceeded
    When I make 100 requests in 1 second
    Then some requests should be rate limited
    And rate limit error should be informative

  @error @large_payload
  Scenario: Handle excessively large payloads
    When I send a request with 10MB payload
    Then I should receive a payload size error
    And the error should indicate size limit

  @error @invalid_characters
  Scenario: Handle special characters in names
    When I create a journey with name containing special characters
    Then the system should either accept or reject appropriately
    And any rejection should be clearly explained

  @error @negative_numbers
  Scenario: Handle negative values where inappropriate
    When I try to set progress to -50
    Then I should receive a validation error
    And the error should indicate valid range

  @error @out_of_range
  Scenario: Handle out of range values
    When I try to set progress to 150
    Then I should receive a validation error
    And the error should indicate valid range is 0-100

  @error @duplicate_operations
  Scenario: Handle duplicate create operations
    Given a journey "JRN-DUP-001" exists
    When I try to create another journey with same ID
    Then the system should handle the duplicate appropriately

  @error @orphaned_resources
  Scenario: Handle orphaned resources
    Given orphaned job records exist without parent journey
    When I try to access the orphaned resources
    Then the system should handle gracefully
    And appropriate warnings should be issued

  @error @cascading_failures
  Scenario: Handle cascading operation failures
    Given a journey with dependent resources
    When a critical operation fails
    Then dependent operations should be handled appropriately
    And rollback should occur if necessary

  @error @recovery
  Scenario: Error recovery and retry logic
    Given an operation that can be retried
    When the operation fails temporarily
    Then the system should provide retry information
    And subsequent retry should succeed if issue resolved

