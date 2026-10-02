Feature: License Activation
  As a system administrator
  I want to activate the backend using a license key
  So that the system becomes operational and users can access its features

  Background:
    Given the backend service is running
    And I have a valid API key "super-secret"
    And no license is currently activated

  @license @api @activation @smoke
  Scenario: Activate a valid enterprise license key
    Given I have a valid enterprise license key
    When I activate the license via API
    Then the response should be successful
    And the license status should be "active"
    And the license tier should be "enterprise"
    And the response should contain license details:
      | field          |
      | license_id     |
      | tier           |
      | holder_name    |
      | expires_at     |
      | days_remaining |
      | features       |
      | is_active      |

  @license @api @activation
  Scenario: Activate a valid professional license key
    Given I have a valid professional license key
    When I activate the license via API
    Then the response should be successful
    And the license tier should be "professional"

  @license @api @activation
  Scenario: Activate a valid basic license key
    Given I have a valid basic license key
    When I activate the license via API
    Then the response should be successful
    And the license tier should be "basic"

  @license @api @activation @error
  Scenario: Attempt to activate an invalid license key format
    Given I have an invalid license key "invalid-key-format"
    When I activate the license via API
    Then the response should fail with status code 400
    And the error code should be "LICENSE_INVALID_FORMAT"

  @license @api @activation @error
  Scenario: Attempt to activate an expired license key
    Given I have an expired license key
    When I activate the license via API
    Then the response should fail with status code 400
    And the error code should be "LICENSE_EXPIRED"

  @license @api @activation @idempotent
  Scenario: Activating the same license twice returns existing activation
    Given I have a valid enterprise license key
    When I activate the license via API
    Then the response should be successful
    And I save the license ID
    When I activate the same license via API again
    Then the response should be successful
    And the license ID should match the saved license ID

  @license @mcp @activation
  Scenario: Activate license via MCP tool
    Given I have a valid enterprise license key
    When I activate the license via MCP tool
    Then the MCP response should be successful
    And the license status should be "active"

  @license @api @activation @audit
  Scenario: License activation creates audit log entry
    Given I have a valid enterprise license key
    When I activate the license via API
    Then the response should be successful
    When I retrieve the audit logs
    Then the audit logs should contain an entry with event type "license_activated"
