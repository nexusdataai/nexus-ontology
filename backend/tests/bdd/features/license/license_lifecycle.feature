Feature: License Lifecycle
  As a system administrator
  I want to manage the complete license lifecycle
  So that I can maintain proper license management

  Background:
    Given the backend service is running
    And I have a valid API key "super-secret"

  @license @api @lifecycle @smoke
  Scenario: Complete license lifecycle - activate, use, deactivate
    # Step 1: Verify no license
    Given no license is currently activated
    When I query the license status via API
    Then the license status should be "not_activated"
    
    # Step 2: Activate license
    Given I have a valid enterprise license key
    When I activate the license via API
    Then the response should be successful
    And I save the license ID
    
    # Step 3: Verify active
    When I query the license status via API
    Then the license status should be "active"
    
    # Step 4: Check feature access
    When I check access to feature "journeys"
    Then the feature should be allowed
    
    # Step 5: Validate license
    When I validate the license via API
    Then the license should be valid
    
    # Step 6: Deactivate
    When I deactivate the license with reason "Lifecycle test complete"
    Then the response should be successful
    
    # Step 7: Verify deactivated
    When I query the license status via API
    Then the license status should be either "not_activated" or "deactivated"
    
    # Step 8: Verify audit trail
    When I retrieve the audit logs
    Then the audit logs should contain entries for the complete lifecycle

  @license @api @lifecycle @reactivation
  Scenario: Reactivate license after deactivation
    Given a valid enterprise license is activated
    When I deactivate the license with reason "Reactivation test"
    Then the response should be successful
    When I activate the same license via API again
    Then the response should be successful
    And the license status should be "active"

  @license @api @lifecycle @tier-change
  Scenario: Upgrade license tier
    Given a valid basic license is activated
    When I check access to feature "advanced_analytics"
    Then the feature should not be allowed
    When I deactivate the license with reason "Upgrading"
    Then the response should be successful
    Given I have a valid enterprise license key
    When I activate the license via API
    Then the response should be successful
    When I check access to feature "advanced_analytics"
    Then the feature should be allowed
