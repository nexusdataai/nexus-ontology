Feature: License Status
  As a UI developer
  I want to query the current license status
  So that I can display license information and validity to users

  Background:
    Given the backend service is running
    And I have a valid API key "super-secret"

  @license @api @status @smoke
  Scenario: Get status with active license
    Given a valid enterprise license is activated
    When I query the license status via API
    Then the response should be successful
    And the license status should be "active"
    And the response should contain:
      | field          |
      | license_id     |
      | tier           |
      | holder_name    |
      | activated_at   |
      | expires_at     |
      | days_remaining |
      | features       |

  @license @api @status
  Scenario: Get status without any license activated
    Given no license is currently activated
    When I query the license status via API
    Then the response should be successful
    And the license status should be "not_activated"
    And the response should contain activation instructions

  @license @api @status @warning
  Scenario: Get status shows expiration warning for expiring license
    Given a license expiring in 7 days is activated
    When I query the license status via API
    Then the response should be successful
    And the is_expiring_soon flag should be true
    And the response should contain an expiration warning

  @license @mcp @status
  Scenario: Get status via MCP tool
    Given a valid enterprise license is activated
    When I query the license status via MCP tool
    Then the MCP response should be successful
    And the license status should be "active"

  @license @api @status @features
  Scenario: Status includes enabled features for tier
    Given a valid enterprise license is activated
    When I query the license status via API
    Then the response should be successful
    And the features list should not be empty
