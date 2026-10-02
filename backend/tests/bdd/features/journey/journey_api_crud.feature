Feature: Journey CRUD Operations via REST API
  As a developer integrating with the AI Job Engine
  I want to manage journeys via REST API
  So that I can create, read, update, and delete transformation journeys programmatically

  Background:
    Given the backend service is running
    And I have a valid API key "super-secret"

  @journey @api @create @smoke
  Scenario: Create a new journey successfully
    When I create a journey with:
      | field            | value                              |
      | name             | Test Payment Journey               |
      | description      | API test journey for payment system |
      | odaComponentType | payment-management                 |
      | priority         | high                               |
      | createdBy        | api-test-user                      |
    Then the response should be successful
    And the journey ID should start with "JRN-"
    And the journey should exist in DynamoDB
    And the journey status should be "pending"
  
  @journey @api @create @dynamodb @verification
  Scenario: Create journey with DynamoDB record verification
    Given I track the initial DynamoDB record count for journeys
    When I create a journey with name "DynamoDB Test Journey" and component "customer-management"
    Then the response should be successful
    And the DynamoDB journey record count should increase by at least 1
    And 6 default stages should be created automatically
    And the total DynamoDB records should increase by at least 7

  @journey @api @create @validation
  Scenario: Create journey with missing required field
    When I create a journey with:
      | field       | value                    |
      | description | Missing name field       |
      | priority    | high                     |
    Then the response should fail with error containing "name"

  @journey @api @list @smoke
  Scenario: List all journeys
    Given 3 test journeys exist
    When I list all journeys
    Then the response should be successful
    And the response should contain at least 3 journeys
    And each journey should have required fields:
      | field            |
      | journeyId        |
      | name             |
      | status           |
      | odaComponentType |
      | priority         |

  @journey @api @list @filter
  Scenario: List journeys with status filter
    Given a journey "JRN-FILTER-01" exists
    And a journey "JRN-FILTER-02" exists
    When I update journey "JRN-FILTER-01" with:
      | field  | value   |
      | status | running |
    Then the response should be successful
    When I list all journeys
    Then the response should be successful
    And the response should contain at least 2 journeys

  @journey @api @read @smoke
  Scenario: Read specific journey
    Given a journey "JRN-READ-TEST" exists
    When I get journey "JRN-READ-TEST"
    Then the response should be successful
    And the response should have field "data.journeyId"
    And the response field "data.journeyId" should be "JRN-READ-TEST"

  @journey @api @read @error
  Scenario: Read non-existent journey
    When I get journey "JRN-DOES-NOT-EXIST"
    Then the response should fail with error containing "not found"

  @journey @api @update @smoke
  Scenario: Update journey metadata
    Given a journey "JRN-UPDATE-TEST" exists
    When I update journey "JRN-UPDATE-TEST" with:
      | field       | value                    |
      | status      | running                  |
      | priority    | critical                 |
      | description | Updated via API test     |
    Then the response should be successful
    When I get journey "JRN-UPDATE-TEST"
    Then the response should be successful
    And the response field "data.status" should be "running"
    And the response field "data.priority" should be "critical"

  @journey @api @update @error
  Scenario: Update non-existent journey
    When I update journey "JRN-NONEXISTENT" with:
      | field    | value   |
      | status   | running |
    Then the response should fail with error containing "not found"

  @journey @api @delete @smoke
  Scenario: Delete journey successfully
    Given a journey "JRN-DELETE-TEST" exists
    When I delete journey "JRN-DELETE-TEST"
    Then the response should be successful
    And the journey should not exist in DynamoDB

  @journey @api @delete @error
  Scenario: Delete non-existent journey
    When I delete journey "JRN-NEVER-EXISTED"
    Then the response should fail with error containing "not found"

  @journey @api @lifecycle
  Scenario: Complete journey lifecycle (Create → Update → Delete)
    # Create
    When I create a journey with:
      | field            | value                     |
      | name             | Lifecycle Test Journey    |
      | odaComponentType | customer-management       |
      | priority         | medium                    |
    Then the response should be successful
    And the journey ID should start with "JRN-"
    
    # Read
    When I get journey "{last_journey_id}"
    Then the response should be successful
    And the response field "data.name" should be "Lifecycle Test Journey"
    
    # Update
    When I update journey "{last_journey_id}" with:
      | field    | value      |
      | status   | running    |
      | priority | high       |
    Then the response should be successful
    
    # Verify update
    When I get journey "{last_journey_id}"
    Then the response should be successful
    And the response field "data.status" should be "running"
    
    # Delete
    When I delete journey "{last_journey_id}"
    Then the response should be successful
    And the journey should not exist in DynamoDB

  @journey @api @lifecycle @dynamodb @comprehensive
  Scenario: Complete CRUD lifecycle with DynamoDB verification
    # Track initial state
    Given I track the initial DynamoDB record count
    And I track the initial API journey count
    
    # Phase 1: Create with stages
    When I create a journey with name "CRUD Lifecycle Test" and component "product-management"
    Then the response should be successful
    And the journey should have ID starting with "JRN-"
    And 6 default stages should be created
    And DynamoDB records should increase by at least 7
    And API journey count should increase by 1
    
    # Phase 2: Update journey
    When I update the created journey with:
      | field       | value                           |
      | description | UPDATED: CRUD lifecycle test    |
      | priority    | critical                        |
      | version     | 1.1.0                          |
    Then the response should be successful
    
    # Phase 3: Verify update
    When I read the created journey
    Then the journey description should contain "UPDATED"
    And the journey version should be "1.1.0"
    And the journey priority should be "critical"
    
    # Phase 4: Delete journey
    When I delete the created journey with confirmation
    Then the response should be successful
    And all journey-specific records should be removed from DynamoDB
    And DynamoDB record count should return to initial value
    And API journey count should return to initial value

  @journey @api @delete @cascading
  Scenario: Delete journey with cascading record cleanup
    Given I track journey-specific record count
    When I create a journey with default stages
    And I track the journey-specific records
    Then journey records should include at least 7 items
    When I delete the journey with confirm flag
    Then all journey-specific DynamoDB records should be deleted
    And journey-specific record count should be 0

  @journey @api @validation
  Scenario: Validate journey data constraints
    When I create a journey with:
      | field            | value                |
      | name             | Test                 |
      | odaComponentType | invalid-component    |
      | priority         | super-urgent         |
    Then the response should fail with error containing "invalid"

  @journey @api @concurrent
  Scenario: Create multiple journeys concurrently
    When I create a journey with:
      | field            | value          |
      | name             | Concurrent 1   |
      | odaComponentType | test-1         |
    Then the response should be successful
    When I create a journey with:
      | field            | value          |
      | name             | Concurrent 2   |
      | odaComponentType | test-2         |
    Then the response should be successful
    When I list all journeys
    Then the response should be successful
    And the response should contain at least 2 journeys

