Feature: License Deactivation
  As a system administrator
  I want to deactivate a license
  So that I can transfer it to another instance or revoke access

  Background:
    Given the backend service is running
    And I have a valid API key "super-secret"

  @license @api @deactivation @smoke
  Scenario: Deactivate an active license
    Given a valid enterprise license is activated
    When I deactivate the license with reason "Transfer to new server"
    Then the response should be successful
    And the response should contain deactivation timestamp
    And the response should indicate can_reactivate is true
    When I query the license status via API
    Then the license status should be either "not_activated" or "deactivated"

  @license @api @deactivation @error
  Scenario: Attempt to deactivate when no license is active
    Given no license is currently activated
    When I deactivate the license with reason "Test"
    Then the response should fail with status code 403
    And the error code should be "LICENSE_NOT_ACTIVATED"

  @license @api @deactivation @cache
  Scenario: Deactivation clears cached license data
    Given a valid enterprise license is activated
    And the license is validated and cached
    When I deactivate the license with reason "Cache test"
    Then the response should be successful
    When I validate the license
    Then the license should not be valid

  @license @mcp @deactivation
  Scenario: Deactivate license via MCP tool
    Given a valid enterprise license is activated
    When I deactivate the license via MCP tool with reason "MCP test"
    Then the MCP response should be successful

  @license @api @deactivation @audit
  Scenario: Deactivation creates audit log entry
    Given a valid enterprise license is activated
    When I deactivate the license with reason "Audit test"
    Then the response should be successful
    When I retrieve the audit logs
    Then the audit logs should contain an entry with event type "license_deactivated"
