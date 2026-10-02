Feature: Journey Management Operations
  As a transformation manager
  I want to manage journeys through the CLI
  So that I can orchestrate ODA component transformations

  Background:
    Given the Journey Manager CLI is running
    And I am authenticated as "test-user@example.com"
    And test data is initialized in DynamoDB

  @journey @create
  Scenario: Create a new journey successfully
    Given I am on the main menu
    When I navigate to "Journey Operations"
    And I select "Create New Journey" 
    And I enter the following journey details:
      | field         | value                           |
      | name          | Test Payment Journey            |
      | description   | BDD test journey for payments   |
      | component     | Payment Management              |
      | priority      | high                           |
    Then I should see "Journey created successfully"
    And the journey should be saved with ID starting with "JRN-"
    And the journey status should be "pending"

  @journey @create @validation
  Scenario: Validate required fields when creating journey
    Given I am on the main menu
    When I navigate to "Journey Operations"
    And I select "Create New Journey"
    And I submit without entering required fields
    Then I should see an error message "Journey name is required"
    And no journey should be created

  @journey @list
  Scenario: List all journeys with pagination
    Given the following journeys exist:
      | name                | status    | component               | priority |
      | Payment Journey     | running   | Payment Management      | high     |
      | Customer Journey    | completed | Customer Management     | medium   |
      | Inventory Journey   | pending   | Inventory Control       | low      |
      | Order Journey       | failed    | Service Order Management| critical |
    When I navigate to "Journey Operations"
    And I select "List All Journeys"
    Then I should see a list containing 4 journeys
    And each journey should display name, status, component, and priority

  @journey @list @filter
  Scenario: Filter journeys by status
    Given multiple journeys exist with different statuses
    When I navigate to "Journey Operations" 
    And I select "List All Journeys"
    And I filter by status "running"
    Then I should see only journeys with status "running"
    And the filter should be indicated in the display

  @journey @select
  Scenario: Select a journey for management
    Given a journey "JRN-TEST-001" exists with name "Test Journey"
    When I navigate to "Journey Operations"
    And I select "Select Journey"
    And I choose journey "JRN-TEST-001" from the list
    Then the journey "Test Journey" should be set as current
    And I should see "Journey selected: Test Journey"
    And stage management options should become available

  @journey @update
  Scenario: Update journey properties
    Given a journey "JRN-TEST-002" exists
    And the journey is selected as current
    When I navigate to "Journey Operations"
    And I select "Update Journey"
    And I update the following fields:
      | field       | value                    |
      | status      | running                  |
      | priority    | critical                 |
      | description | Updated test description |
    Then I should see "Journey updated successfully"
    And the journey should reflect the new values

  @journey @delete
  Scenario: Delete journey with confirmation
    Given a journey "JRN-TEST-003" exists
    And the journey is selected as current
    When I navigate to "Journey Operations"
    And I select "Delete Journey"
    And I confirm the deletion warning
    And I type "DELETE" to confirm
    Then I should see "Journey deleted successfully"
    And the journey should no longer exist in the system

  @journey @clone
  Scenario: Clone existing journey
    Given a journey exists with complete configuration
    And the journey is selected as current
    When I navigate to "Journey Operations"
    And I select "Clone Journey"
    And I provide new journey name "Cloned Test Journey"
    Then I should see "Journey cloned successfully"
    And a new journey should exist with the same configuration
    And the new journey should have a different ID

  @journey @export
  Scenario: Export journey configuration
    Given a journey exists with stages and rules
    And the journey is selected as current
    When I navigate to "Journey Operations"
    And I select "Export Journey"
    And I specify filename "test_journey_export.json"
    Then the journey should be exported to "test_journey_export.json"
    And the file should contain complete journey configuration
    And I should see "Journey exported successfully"

  @journey @import
  Scenario: Import journey from file
    Given a valid journey configuration file "import_test.json" exists
    When I navigate to "Journey Operations"
    And I select "Import Journey"
    And I specify the import file "import_test.json"
    And I choose to generate a new journey ID
    Then I should see "Journey imported successfully"
    And the imported journey should be available in the list
    And all stages and rules should be imported correctly

  @journey @navigation
  Scenario: Navigate between journey menus
    Given I am on the main menu
    When I navigate to "Journey Operations"
    Then I should see the journey operations menu
    When I go back to main menu
    Then I should be on the main menu
    And I should see all main menu options

  @journey @error
  Scenario: Handle network errors gracefully
    Given a journey "JRN-TEST-004" exists
    And the network connection is interrupted
    When I try to update the journey
    Then I should see an error message about connection issues
    And the CLI should remain responsive
    And I should be able to retry the operation
