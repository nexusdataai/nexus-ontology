# Implementation Plan: WXCC Simulator UI

## Overview

This implementation plan breaks down the WXCC Simulator UI feature into discrete coding tasks. The approach is incremental, starting with the service layer, then building UI components, and finally integrating everything into the AI Workspace.

## Tasks

- [x] 1. Create WXCC Simulator Service
  - [x] 1.1 Create wxccSimulatorService.ts with type definitions
    - Create `src/services/wxccSimulatorService.ts`
    - Define TypeScript interfaces matching backend models (Task, Recording, SimulatorStatus, etc.)
    - Implement base service class with configuration loading
    - _Requirements: 2.1, 3.1, 7.2_

  - [x] 1.2 Implement status and health check methods
    - Implement `getStatus()` method calling `/v1/sim/admin/status`
    - Implement `healthCheck()` method calling `/v1/sim/health`
    - Add error handling for connection and auth failures
    - _Requirements: 2.1, 2.2, 10.1, 10.2_

  - [x] 1.3 Implement task fetching methods
    - Implement `getTasks()` method calling `/v1/tasks` with auth header
    - Implement `getCaptures()` method calling `/v1/captures/query`
    - Handle pagination and filtering parameters
    - _Requirements: 3.1, 3.2, 7.3_

  - [x] 1.4 Implement admin operation methods
    - Implement `seedData()` method calling `/v1/sim/admin/seed`
    - Implement `resetData()` method calling `/v1/sim/admin/reset`
    - Implement `getRecordingUrl()` helper for audio URLs
    - _Requirements: 5.3, 6.3, 8.1_

  - [x] 1.5 Write unit tests for wxccSimulatorService
    - Test getStatus() response parsing
    - Test getTasks() with various parameters
    - Test error handling for network failures
    - Test error handling for auth failures
    - _Requirements: 10.2, 10.3_

- [x] 2. Create SimulatorStatusCard Component
  - [x] 2.1 Create SimulatorStatusCard.tsx
    - Create `src/components/wxcc-simulator/SimulatorStatusCard.tsx`
    - Display status fields: enabled, org_id, bucket, task_count, recording_count
    - Show loading skeleton during fetch
    - Show warning state when simulator is disabled
    - _Requirements: 2.1, 2.2, 2.4_

  - [x] 2.2 Add refresh functionality
    - Add refresh button with loading state
    - Implement onRefresh callback
    - _Requirements: 2.3_

  - [x] 2.3 Write property test for status display completeness
    - **Property 1: Status Display Completeness**
    - **Validates: Requirements 2.1**

- [x] 3. Create SimulatorStatistics Component
  - [x] 3.1 Create SimulatorStatistics.tsx
    - Create `src/components/wxcc-simulator/SimulatorStatistics.tsx`
    - Calculate and display total tasks count
    - Display tasks by status breakdown (completed, abandoned, transferred)
    - Display tasks by direction breakdown (inbound, outbound)
    - _Requirements: 9.1_

  - [x] 3.2 Write property test for statistics accuracy
    - **Property 10: Statistics Accuracy**
    - **Validates: Requirements 9.1**

- [x] 4. Create TasksTable Component
  - [x] 4.1 Create TasksTable.tsx with basic structure
    - Create `src/components/wxcc-simulator/TasksTable.tsx`
    - Implement table with columns: ID, Status, Direction, Origin, Destination, Queue, Agent, Recording
    - Add status icons/colors for completed (green), abandoned (red), transferred (blue)
    - Add recording indicator icon when task has recordings
    - _Requirements: 3.1, 3.4, 3.5_

  - [x] 4.2 Implement sorting and pagination
    - Sort tasks by createdTime descending (newest first)
    - Add pagination controls
    - _Requirements: 3.2_

  - [x] 4.3 Implement row selection
    - Make rows clickable
    - Highlight selected row
    - Call onTaskSelect callback
    - _Requirements: 7.1_

  - [x] 4.4 Add empty state
    - Display message when no tasks exist
    - Include guidance to seed data
    - _Requirements: 3.3_

  - [x] 4.5 Write property tests for TasksTable
    - **Property 2: Task Table Column Completeness**
    - **Property 3: Task Sorting Order**
    - **Property 4: Status Visual Indicators**
    - **Property 5: Recording Indicator Accuracy**
    - **Validates: Requirements 3.1, 3.2, 3.4, 3.5**

- [x] 5. Create FilterControls Component
  - [x] 5.1 Create FilterControls.tsx
    - Create `src/components/wxcc-simulator/FilterControls.tsx`
    - Add status filter dropdown (All, Completed, Abandoned, Transferred)
    - Add direction filter dropdown (All, Inbound, Outbound)
    - Add search input for origin/destination filtering
    - Display filtered count vs total count
    - _Requirements: 4.1, 4.2, 4.3, 4.5_

  - [x] 5.2 Implement filter logic
    - Create filterTasks utility function
    - Apply status filter
    - Apply direction filter
    - Apply search query to origin and destination
    - _Requirements: 4.4_

  - [x] 5.3 Write property tests for filtering
    - **Property 6: Filter Correctness**
    - **Property 7: Filter Count Accuracy**
    - **Validates: Requirements 4.4, 4.5**

- [x] 6. Checkpoint - Core Components Complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Create TaskDetailsModal Component
  - [x] 7.1 Create TaskDetailsModal.tsx
    - Create `src/components/wxcc-simulator/TaskDetailsModal.tsx`
    - Display full task ID and all timestamps
    - Display all task attributes in organized sections
    - Add close button
    - _Requirements: 7.1, 7.2, 7.4_

  - [x] 7.2 Add recording list with playback
    - List all recordings associated with task
    - Include RecordingPlayer for each recording
    - _Requirements: 7.3_

  - [x] 7.3 Write property test for task details completeness
    - **Property 8: Task Details Completeness**
    - **Property 9: Recording List in Details**
    - **Validates: Requirements 7.2, 7.3**

- [x] 8. Create RecordingPlayer Component
  - [x] 8.1 Create RecordingPlayer.tsx
    - Create `src/components/wxcc-simulator/RecordingPlayer.tsx`
    - Use HTML5 audio element with controls
    - Display recording duration and current position
    - Handle loading and error states
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 9. Create Action Dialogs
  - [x] 9.1 Create SeedDataDialog.tsx
    - Create `src/components/wxcc-simulator/SeedDataDialog.tsx`
    - Add number input for task count (1-100)
    - Add number input for days back (0-30)
    - Add checkbox for include recordings
    - Add checkbox for reset first
    - Add confirm and cancel buttons
    - Show loading state during seeding
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 9.2 Create ResetConfirmDialog.tsx
    - Create `src/components/wxcc-simulator/ResetConfirmDialog.tsx`
    - Display warning about data loss
    - Add confirm and cancel buttons
    - _Requirements: 6.1, 6.2_

- [x] 10. Create WXCCSimulatorPanel Main Component
  - [x] 10.1 Create WXCCSimulatorPanel.tsx
    - Create `src/components/wxcc-simulator/WXCCSimulatorPanel.tsx`
    - Compose all child components
    - Manage state for tasks, status, filters, selected task
    - Handle loading and error states
    - _Requirements: 1.2, 2.1, 3.1_

  - [x] 10.2 Implement data fetching
    - Fetch status on mount
    - Fetch tasks on mount
    - Implement refresh functionality
    - _Requirements: 2.3, 9.2_

  - [x] 10.3 Implement action handlers
    - Handle seed data flow with success/error feedback
    - Handle reset flow with success/error feedback
    - Handle task selection to show details modal
    - _Requirements: 5.4, 5.5, 6.4, 6.5, 7.1_

  - [x] 10.4 Implement error handling
    - Display connection error state with retry
    - Display user-friendly error messages
    - Maintain UI stability on errors
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 10.5 Write property test for error resilience
    - **Property 11: Error Resilience**
    - **Validates: Requirements 10.3**

- [x] 11. Integrate into AIWorkspace
  - [x] 11.1 Update AIWorkspace.tsx
    - Add new tab configuration for WXCC Simulator
    - Import WXCCSimulatorPanel component
    - Add TabsContent for simulator tab
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 11.2 Write integration tests
    - Test tab navigation to simulator
    - Test data loading on tab activation
    - _Requirements: 1.1, 1.2_

- [x] 12. Final Checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all requirements are implemented
  - Test full user flow: view status → browse tasks → seed data → view details → play recording → reset

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using fast-check
- Unit tests validate specific examples and edge cases
- The service layer follows the pattern established by backendDebugService.ts
- UI components use existing shadcn/ui components (Table, Dialog, Button, etc.)
