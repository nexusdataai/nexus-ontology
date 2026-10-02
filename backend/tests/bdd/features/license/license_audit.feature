Feature: License Audit Trail
  As a compliance officer
  I want a complete audit trail of license events
  So that I can track license usage and compliance

  Background:
    Given the backend service is running
    And I have a valid API key "super-secret"

  @license @api @audit @smoke
  Scenario: Retrieve audit logs
    Given a valid enterprise license is activated
    When I retrieve the audit logs
    Then the response should be successful
    And the response should contain audit entries
    And each audit entry should have required fields:
      | field       |
      | event_id    |
      | timestamp   |
      | event_type  |

  @license @api @audit @pagination
  Scenario: Audit logs support pagination
    Given a valid enterprise license is activated
    And multiple license operations have been performed
    When I retrieve the audit logs with limit 5
    Then the response should be successful
    And the page_size should be 5

  @license @api @audit @events
  Scenario: All license operations create audit entries
    Given no license is currently activated
    When I activate a valid enterprise license
    Then the audit logs should contain an entry with event type "license_activated"
    When I validate the license via API
    Then the audit logs should contain an entry with event type "license_validated"
    When I deactivate the license with reason "Audit test"
    Then the audit logs should contain an entry with event type "license_deactivated"

  @license @mcp @audit
  Scenario: Retrieve audit logs via MCP tool
    Given a valid enterprise license is activated
    When I retrieve the audit logs via MCP tool
    Then the MCP response should be successful
    And the response should contain audit entries

  @license @api @audit @filter
  Scenario: Audit logs can be filtered by date
    Given a valid enterprise license is activated
    And multiple license operations have been performed
    When I retrieve the audit logs with date filter
    Then the response should be successful
    And all entries should be within the date range
