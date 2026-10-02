# Implementation Plan: License Management UI

## Overview

This implementation plan breaks down the License Management feature into discrete coding tasks. The feature adds a License tab to the Settings page, integrating with the backend License API at `/api/v1/license/*`. Tasks are ordered to build incrementally, with core service and types first, followed by UI components, and finally integration.

## Tasks

- [x] 1. Set up project structure and type definitions
  - [x] 1.1 Create license types and interfaces
    - Create `src/types/license.ts` with all TypeScript interfaces
    - Define LicenseStatus, LicenseTier, LicenseEventType enums
    - Define API request/response types matching backend models
    - Define component prop interfaces
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1_

  - [x] 1.2 Create license service
    - Create `src/services/licenseService.ts`
    - Implement getStatus(), activateLicense(), deactivateLicense(), renewLicense()
    - Implement getAuditLogs(), checkFeatureAccess(), validateLicense()
    - Add validation result caching with TTL
    - Use config.json for API base URL (same pattern as backendDebugService)
    - _Requirements: 7.1, 7.3, 7.4_

  - [x] 1.3 Write unit tests for license service
    - Test API call methods with mocked fetch
    - Test caching behavior
    - Test error handling
    - **Property 9: Validation Cache Behavior**
    - **Validates: Requirements 7.3**

- [x] 2. Implement LicenseStatusCard component
  - [x] 2.1 Create LicenseStatusCard component
    - Create `src/components/settings/license/LicenseStatusCard.tsx`
    - Display license status with color-coded indicator
    - Show tier, holder name, expiration date
    - Display days remaining and expiration warning
    - Handle loading and error states
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 2.2 Write property test for status indicator mapping
    - **Property 1: Status Indicator Mapping**
    - Generate random status values, verify correct indicator
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5**

  - [x] 2.3 Write property test for days remaining display
    - **Property 8: Days Remaining Display**
    - Generate active statuses with various days_remaining
    - **Validates: Requirements 1.6, 1.7**

- [x] 3. Implement LicenseActivationForm component
  - [x] 3.1 Create LicenseActivationForm component
    - Create `src/components/settings/license/LicenseActivationForm.tsx`
    - Input field for license key with validation
    - Optional instance ID field
    - Submit button with loading state
    - Display activation success/error messages
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 3.2 Write property test for license key validation
    - **Property 2: License Key Validation**
    - Generate invalid key formats, verify validation error
    - **Validates: Requirements 2.2**

  - [x] 3.3 Write property test for loading state
    - **Property 4: Loading State UI**
    - Test button disabled and spinner shown during activation
    - **Validates: Requirements 2.6**

- [x] 4. Implement LicenseRenewalForm component
  - [x] 4.1 Create LicenseRenewalForm component
    - Create `src/components/settings/license/LicenseRenewalForm.tsx`
    - Input field for renewal key
    - Submit button with loading state
    - Display current expiration and new expiration after renewal
    - Hide form when no license is activated
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 4.2 Write property test for disabled when not activated
    - **Property 5: Disabled When Not Activated**
    - Test form hidden when status is not_activated
    - **Validates: Requirements 4.4**

- [x] 5. Implement LicenseDeactivateDialog component
  - [x] 5.1 Create LicenseDeactivateDialog component
    - Create `src/components/settings/license/LicenseDeactivateDialog.tsx`
    - Confirmation dialog with reason input
    - Confirm/Cancel buttons
    - Loading state during deactivation
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 5.2 Write unit tests for deactivation dialog
    - Test dialog opens on deactivate click
    - Test reason is required
    - Test API call on confirm
    - _Requirements: 3.1, 3.2_

- [x] 6. Implement AuditLogTable component
  - [x] 6.1 Create AuditLogTable component
    - Create `src/components/settings/license/AuditLogTable.tsx`
    - Table with timestamp, event type, result columns
    - Event type icons mapping
    - Expandable rows for details
    - Pagination controls
    - Date range filter
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 6.2 Write property test for audit log rendering
    - **Property 7: Audit Log Entry Rendering**
    - Generate random audit entries, verify fields rendered
    - **Validates: Requirements 5.1, 5.5**

- [x] 7. Implement FeatureAccessList component
  - [x] 7.1 Create FeatureAccessList component
    - Create `src/components/settings/license/FeatureAccessList.tsx`
    - List features with tier requirements
    - Visual distinction for accessible vs inaccessible
    - Upgrade message for higher-tier features
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 7.2 Write property test for feature access display
    - **Property 6: Feature Access Display**
    - Generate tier combinations, verify styling
    - **Validates: Requirements 6.2, 6.3, 6.4**

- [x] 8. Implement LicensePage container component
  - [x] 8.1 Create LicensePage component
    - Create `src/components/settings/license/LicensePage.tsx`
    - Orchestrate all child components
    - Manage state for status, loading, errors
    - Handle refresh and data fetching
    - Sections: Status, Activation/Renewal, Audit Logs, Features
    - _Requirements: 1.1, 7.1, 8.1, 8.2, 8.3, 8.4_

  - [x] 8.2 Write property test for error display
    - **Property 3: Error Display Consistency**
    - Generate error responses, verify message and code shown
    - **Validates: Requirements 2.3, 3.4, 4.3, 7.2, 8.2**

  - [x] 8.3 Write property test for network error handling
    - **Property 10: Network Error Handling**
    - Simulate network errors, verify error message and retry button
    - **Validates: Requirements 8.1, 8.3**

- [x] 9. Integrate with Settings page
  - [x] 9.1 Add License tab to Settings page
    - Update `src/pages/Settings.tsx`
    - Add License tab with Key icon
    - Import and render LicensePage component
    - Add role-based access control (Admin/Executive only)
    - _Requirements: 1.1_

  - [x] 9.2 Create index export file
    - Create `src/components/settings/license/index.ts`
    - Export all license components
    - _Requirements: N/A_

- [x] 10. Checkpoint - Ensure all tests pass
  - All 38 tests pass (15 service tests, 12 status card tests, 11 activation form tests)

- [ ] 11. Integration testing and polish
  - [ ] 11.1 Write integration tests for activation flow
    - Test full activation flow: enter key → submit → verify status update
    - _Requirements: 2.1, 2.4_

  - [ ] 11.2 Write integration tests for deactivation flow
    - Test full deactivation flow: click → confirm → verify status update
    - _Requirements: 3.2, 3.3_

  - [ ] 11.3 Add error help links
    - Add contextual help links for common error codes
    - _Requirements: 8.4_

- [ ] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for comprehensive testing
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design
- Use existing UI components (Card, Button, Input, Badge, Table) from shadcn/ui
- Follow existing patterns from BackendDebugPlatform and WXCCSimulatorPanel
- License service uses same config.json pattern as other services
