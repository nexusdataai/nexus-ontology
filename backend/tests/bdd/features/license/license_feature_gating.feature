Feature: Feature Gating by License Tier
  As a product manager
  I want different license tiers to enable different features
  So that we can offer tiered pricing and functionality

  Background:
    Given the backend service is running
    And I have a valid API key "super-secret"

  @license @api @feature @smoke
  Scenario: Enterprise tier has access to all features
    Given a valid enterprise license is activated
    When I check access to feature "journeys"
    Then the feature should be allowed
    When I check access to feature "analytics"
    Then the feature should be allowed
    When I check access to feature "second_brain"
    Then the feature should be allowed
    When I check access to feature "export"
    Then the feature should be allowed

  @license @api @feature
  Scenario: Basic tier has limited feature access
    Given a valid basic license is activated
    When I check access to feature "journeys"
    Then the feature should be allowed
    When I check access to feature "advanced_analytics"
    Then the feature should not be allowed
    And the response should contain an upgrade message

  @license @api @feature
  Scenario: Professional tier has intermediate feature access
    Given a valid professional license is activated
    When I check access to feature "journeys"
    Then the feature should be allowed
    When I check access to feature "analytics"
    Then the feature should be allowed

  @license @api @feature @error
  Scenario: Feature check without active license
    Given no license is currently activated
    When I check access to feature "journeys"
    Then the feature should not be allowed
    And the response should indicate no active license

  @license @mcp @feature
  Scenario: Check feature access via MCP tool
    Given a valid enterprise license is activated
    When I check feature access via MCP tool for "journeys"
    Then the MCP response should be successful
    And the feature should be allowed

  @license @api @feature @tier
  Scenario: Feature check returns tier information
    Given a valid professional license is activated
    When I check access to feature "advanced_analytics"
    Then the response should contain required_tier
    And the response should contain current_tier
