Feature: Stage Management Operations
  As a transformation manager
  I want to manage journey stages through the CLI
  So that I can define and control the transformation workflow

  Background:
    Given the Journey Manager CLI is running
    And I am authenticated as "test-user@example.com"
    And a journey "JRN-STAGE-TEST" exists
    And the journey "JRN-STAGE-TEST" is selected as current

  @stage @create
  Scenario: Add a new stage to journey
    Given I am on the main menu
    When I navigate to "Stage Management"
    And I select "Add Stage"
    And I enter the following stage details:
      | field              | value                          |
      | stageId           | data_validation                |
      | stageName         | Data Validation Stage          |
      | description       | Validate input data quality    |
      | estimatedDuration | 2h                            |
      | canSkip          | no                            |
      | requiresApproval | yes                           |
    And I add the following steps:
      | name              | description                    | duration |
      | Schema Check      | Validate data schema          | 30m      |
      | Data Quality      | Check data completeness       | 1h       |
      | Report Generation | Generate validation report    | 30m      |
    Then I should see "Stage added successfully"
    And the stage should be added to the journey
    And the stage sequence should be updated

  @stage @list
  Scenario: View all stages in sequence
    Given the journey has the following stages:
      | stageId          | stageName              | sequenceOrder | status    |
      | raw_analysis     | Raw Data Analysis      | 1            | completed |
      | stripped_schema  | Schema Stripping       | 2            | running   |
      | tmf_mapping      | TMF Field Mapping      | 3            | pending   |
      | data_validation  | Data Validation        | 4            | pending   |
    When I navigate to "Stage Management"
    And I select "View Stages"
    Then I should see 4 stages in order
    And each stage should show its status and sequence
    And the current stage should be highlighted

  @stage @update
  Scenario: Update stage configuration
    Given the journey has a stage "data_validation"
    When I navigate to "Stage Management"
    And I select "Update Stage"
    And I choose stage "data_validation"
    And I update the following fields:
      | field              | value                     |
      | estimatedDuration | 4h                        |
      | requiresApproval  | no                        |
      | canSkip          | yes                       |
    Then I should see "Stage updated successfully"
    And the stage should reflect the new configuration

  @stage @delete
  Scenario: Remove stage from journey
    Given the journey has multiple stages including "test_stage"
    When I navigate to "Stage Management"
    And I select "Delete Stage"
    And I choose stage "test_stage" to delete
    And I confirm the deletion
    Then I should see "Stage removed successfully"
    And the stage should no longer be in the journey
    And the remaining stages should be resequenced

  @stage @reorder
  Scenario: Reorder stage sequence
    Given the journey has stages in order: "raw_analysis, stripped_schema, tmf_mapping, data_validation"
    When I navigate to "Stage Management"
    And I select "Reorder Stages"
    And I specify new order "raw_analysis, data_validation, stripped_schema, tmf_mapping"
    Then I should see "Stages reordered successfully"
    And the stages should be in the new sequence
    And stage dependencies should be validated

  @stage @dependencies
  Scenario: Configure stage dependencies
    Given the journey has multiple stages
    When I navigate to "Stage Management"
    And I select "Configure Dependencies"
    And I choose stage "tmf_mapping"
    And I set dependency on "stripped_schema" with condition "completed"
    Then I should see "Dependencies configured successfully"
    And the stage should not start until dependency is met

  @stage @enable_disable
  Scenario: Enable and disable stages
    Given the journey has an enabled stage "data_validation"
    When I navigate to "Stage Management"
    And I select "Enable/Disable Stage"
    And I choose to disable stage "data_validation"
    Then I should see "Stage disabled successfully"
    And the stage should be skipped during execution
    When I enable the stage again
    Then the stage should be included in execution

  @stage @view_details
  Scenario: View detailed stage information
    Given the journey has a configured stage "tmf_mapping"
    When I navigate to "Stage Management"
    And I select "View Stage Details"
    And I choose stage "tmf_mapping"
    Then I should see complete stage configuration including:
      | field              | visible |
      | Stage ID           | yes     |
      | Stage Name         | yes     |
      | Description        | yes     |
      | Sequence Order     | yes     |
      | Status            | yes     |
      | Estimated Duration | yes     |
      | Steps             | yes     |
      | Dependencies      | yes     |
      | Configuration     | yes     |

  @stage @execution_history
  Scenario: View stage execution history
    Given the stage "raw_analysis" has been executed multiple times
    When I navigate to "Stage Management"
    And I select "Stage History"
    And I choose stage "raw_analysis"
    Then I should see execution history with:
      | field          | visible |
      | Execution Date | yes     |
      | Duration      | yes     |
      | Status        | yes     |
      | Records       | yes     |
      | Errors        | yes     |

  @stage @validation
  Scenario: Validate stage configuration
    Given I am adding a new stage
    When I try to save with invalid configuration:
      | field     | value | issue            |
      | stageId   |       | missing required |
      | stageName |       | missing required |
      | duration  | abc   | invalid format   |
    Then I should see appropriate validation errors
    And the stage should not be saved

  @stage @template
  Scenario: Create stage from template
    Given stage templates are available
    When I navigate to "Stage Management"
    And I select "Add Stage"
    And I choose "Create from template"
    And I select template "Standard Data Validation"
    Then the stage form should be pre-populated
    And I should be able to customize the template values
    When I save the stage
    Then it should be created with template configuration
