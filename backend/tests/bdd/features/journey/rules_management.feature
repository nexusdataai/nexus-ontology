Feature: Second Brain Rules Management
  As a transformation manager
  I want to manage transformation rules through the CLI
  So that I can configure how data is transformed between systems

  Background:
    Given the Journey Manager CLI is running
    And I am authenticated as "test-user@example.com"
    And a journey "JRN-RULES-TEST" exists
    And the journey "JRN-RULES-TEST" is selected as current
    And the journey has stages including "tmf_mapping"

  @rules @create @field_mapping
  Scenario: Create field mapping rule
    Given I am on the main menu
    When I navigate to "Second Brain Rules"
    And I select "Create Rule"
    And I choose stage "tmf_mapping"
    And I select rule type "field_mapping"
    And I enter the following rule details:
      | field               | value                           |
      | ruleName           | Map Customer ID                 |
      | description        | Map legacy customer ID to TMF   |
      | priority           | 90                             |
      | sourceField        | customer.legacy_id             |
      | targetField        | partyRole.id                   |
      | transformationType | custom                         |
    Then I should see "Rule created successfully"
    And the rule should be added to the stage
    And the rule should be active by default

  @rules @create @validation
  Scenario: Create validation rule
    Given I am on the main menu
    When I navigate to "Second Brain Rules"
    And I select "Create Rule"
    And I choose stage "data_validation"
    And I select rule type "validation_rules"
    And I enter the following rule details:
      | field            | value                             |
      | ruleName        | Validate Email Format             |
      | description     | Ensure email addresses are valid  |
      | priority        | 100                              |
      | field           | contact.email                    |
      | validationType  | regex                            |
      | validationValue | ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ |
    Then I should see "Rule created successfully"
    And the validation rule should be configured

  @rules @create @data_filter
  Scenario: Create data filter rule
    Given I am on the main menu
    When I navigate to "Second Brain Rules"
    And I select "Create Rule"
    And I choose stage "raw_analysis"
    And I select rule type "data_filter"
    And I enter the following rule details:
      | field          | value                              |
      | ruleName      | Filter Active Customers            |
      | description   | Include only active customer records|
      | priority      | 80                                |
      | filterField   | customer.status                   |
      | filterOperator| equals                            |
      | filterValue   | ACTIVE                            |
    Then I should see "Rule created successfully"
    And the filter should be applied during execution

  @rules @list
  Scenario: View all rules for a stage
    Given the stage "tmf_mapping" has the following rules:
      | ruleName             | ruleType      | priority | enabled |
      | Map Customer ID      | field_mapping | 90      | true    |
      | Map Product Code     | field_mapping | 85      | true    |
      | Validate Dates       | validation    | 100     | false   |
      | Filter Test Data     | data_filter   | 70      | true    |
    When I navigate to "Second Brain Rules"
    And I select "List Rules"
    And I choose stage "tmf_mapping"
    Then I should see 4 rules sorted by priority
    And disabled rules should be clearly marked
    And each rule should show its type and configuration

  @rules @update
  Scenario: Update existing rule
    Given a rule "Map Customer ID" exists in stage "tmf_mapping"
    When I navigate to "Second Brain Rules"
    And I select "Update Rule"
    And I choose rule "Map Customer ID"
    And I update the following fields:
      | field          | value                    |
      | priority      | 95                       |
      | targetField   | party.partyId           |
      | description   | Updated mapping for v2   |
    Then I should see "Rule updated successfully"
    And the rule should reflect the changes

  @rules @enable_disable
  Scenario: Enable and disable rules
    Given a rule "Validate Dates" exists and is disabled
    When I navigate to "Second Brain Rules"
    And I select "Enable/Disable Rule"
    And I choose rule "Validate Dates"
    And I enable the rule
    Then I should see "Rule enabled successfully"
    And the rule should be active
    When I disable it again
    Then the rule should be inactive

  @rules @delete
  Scenario: Delete rule with confirmation
    Given a rule "Test Rule" exists in stage "tmf_mapping"
    When I navigate to "Second Brain Rules"
    And I select "Delete Rule"
    And I choose rule "Test Rule"
    And I confirm the deletion
    Then I should see "Rule deleted successfully"
    And the rule should no longer exist

  @rules @priority
  Scenario: Manage rule priorities
    Given multiple rules exist with different priorities
    When I navigate to "Second Brain Rules"
    And I select "Manage Priorities"
    And I reorder rules by priority:
      | rule               | new_priority |
      | Critical Validation| 100         |
      | Important Mapping  | 90          |
      | Standard Filter    | 50          |
    Then I should see "Priorities updated successfully"
    And rules should execute in priority order

  @rules @test
  Scenario: Test rule against sample data
    Given a field mapping rule exists
    When I navigate to "Second Brain Rules"
    And I select "Test Rule"
    And I choose the field mapping rule
    And I provide sample input data:
      """
      {
        "customer": {
          "legacy_id": "CUST-12345",
          "name": "John Doe"
        }
      }
      """
    Then I should see the transformation result:
      """
      {
        "partyRole": {
          "id": "CUST-12345"
        }
      }
      """
    And any errors should be displayed

  @rules @import_export
  Scenario: Export and import rules
    Given multiple rules exist for a stage
    When I navigate to "Second Brain Rules"
    And I select "Export Rules"
    And I choose stage "tmf_mapping"
    And I specify filename "tmf_rules_export.json"
    Then the rules should be exported
    When I import rules from "tmf_rules_export.json"
    Then the rules should be imported successfully
    And I should be prompted about handling duplicates

  @rules @search
  Scenario: Search and filter rules
    Given many rules exist across stages
    When I navigate to "Second Brain Rules"
    And I select "Search Rules"
    And I search for "customer"
    Then I should see all rules containing "customer"
    When I filter by rule type "field_mapping"
    Then I should see only field mapping rules
    When I filter by enabled status
    Then I should see only enabled rules

  @rules @validation_errors
  Scenario: Handle validation errors in rules
    Given I am creating a new rule
    When I try to save with invalid data:
      | field        | value  | issue              |
      | priority     | 150    | out of range       |
      | sourceField  |        | required field     |
      | regex        | [invalid| invalid pattern   |
    Then I should see specific validation errors
    And the rule should not be saved
    And I should be able to correct the errors
