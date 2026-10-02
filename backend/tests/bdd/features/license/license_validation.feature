Feature: License Validation
  As a system operator
  I want all protected API endpoints to require a valid license
  So that only licensed instances can access the system's capabilities

  Background:
    Given the backend service is running
    And I have a valid API key "super-secret"

  @license @api @validation @smoke
  Scenario: Validate an active license
    Given a valid enterprise license is activated
    When I validate the license via API
    Then the response should be successful
    And the license should be valid
    And the license status should be "active"
    And can_write should be true

  @license @api @validation
  Scenario: Validate when no license is activated
    Given no license is currently activated
    When I validate the license via API
    Then the response should be successful
    And the license should not be valid
    And the license status should be "not_activated"

  @license @mcp @validation
  Scenario: Validate license via MCP tool
    Given a valid enterprise license is activated
    When I validate the license via MCP tool
    Then the MCP response should be successful
    And the license should be valid

  @license @api @validation @cache
  Scenario: Validation results are cached
    Given a valid enterprise license is activated
    When I validate the license via API
    Then the response should be successful
    When I validate the license via API again
    Then the response should be successful
    And the validation should use cached result
