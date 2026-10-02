# Implementation Plan: Call Processing Journeys

## Overview

This implementation plan breaks down the Call Processing Journeys feature into discrete, incremental coding tasks. Each task builds on previous work, ensuring no orphaned code. The implementation follows a bottom-up approach: types → services → components → integration.

## Tasks

- [x] 1. Set up types and data models
  - [x] 1.1 Create callProcessingJourney.ts type definitions
    - Define JourneyType, JourneyStatus, CallProcessingJourney interfaces
    - Define JourneyStage, StageStep, JobExecution interfaces
    - Define JobMetrics, JobReport, LogEntry interfaces
    - Define stage constants for call-processing and operation-management
    - _Requirements: 5.2, 5.3, 9.1_

  - [x] 1.2 Write property test for journey type stage mapping
    - **Property 5: Journey Type Determines Stages**
    - **Validates: Requirements 5.1, 9.1**

- [x] 2. Implement service layer
  - [x] 2.1 Create callProcessingJourneyService.ts
    - Implement base service class with HTTP client
    - Implement listJourneys, getJourney, createJourney, deleteJourney methods
    - Implement journey action methods: start, pause, resume, cancel, retry
    - Implement stage operations: getStages, getStageSteps, runStageJob
    - Implement job operations: getJobHistory, getJobStatus, getJobReport
    - Implement getStepLogs and healthCheck methods
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 2.2 Write unit tests for service layer
    - Test API endpoint calls with correct parameters
    - Test error handling for network failures
    - _Requirements: 8.6_

- [x] 3. Implement utility functions
  - [x] 3.1 Create journey filter and sort utilities
    - Implement filterJourneys function with search, status, type filters
    - Implement sortJobs function with date, status, duration options
    - Implement calculateAggregateStats function
    - Implement getAvailableActions function based on journey status
    - _Requirements: 2.2, 2.3, 2.4, 7.1-7.5, 10.5, 10.6_

  - [x] 3.2 Write property test for filter correctness
    - **Property 3: Filter Correctness**
    - **Validates: Requirements 2.2, 2.3, 2.4**

  - [x] 3.3 Write property test for action availability
    - **Property 6: Action Availability by Journey Status**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

  - [x] 3.4 Write property test for sorting correctness
    - **Property 7: Job History Sorting Correctness**
    - **Validates: Requirements 10.5**

  - [x] 3.5 Write property test for aggregate statistics
    - **Property 8: Aggregate Statistics Calculation**
    - **Validates: Requirements 10.6**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement base journey components
  - [x] 5.1 Create JourneyCard component
    - Display journey name, ID, status badge, progress bar
    - Display current stage and creation time
    - Add action buttons (View Studio, Start, Pause, etc.)
    - Apply animated progress indicator for running journeys
    - _Requirements: 2.5, 2.6_

  - [x] 5.2 Write property test for journey card display completeness
    - **Property 2: Journey List Display Completeness**
    - **Validates: Requirements 2.1, 2.5**

  - [x] 5.3 Create StageIndicator component
    - Display stage name and status
    - Apply correct color based on status (green/blue/gray/red)
    - _Requirements: 5.5_

  - [x] 5.4 Write property test for stage status visual indicators
    - **Property 4: Stage Status Visual Indicator Correctness**
    - **Validates: Requirements 5.5**

- [x] 6. Implement JourneyListView component
  - [x] 6.1 Create JourneyListView component
    - Implement search input for journey name filtering
    - Implement status filter dropdown
    - Implement type filter dropdown
    - Display filtered journey cards in grid layout
    - Add "New Call Processing Journey" button
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.7_

  - [x] 6.2 Write unit tests for JourneyListView
    - Test filter interactions
    - Test empty state display
    - _Requirements: 2.1_

- [x] 7. Implement CreateJourneyDialog component
  - [x] 7.1 Create CreateJourneyDialog component
    - Implement form with journey name input
    - Add minutes_back number input
    - Add toggle switches for transcribe, registerGlue, runAnalysis, skipProcessed
    - Implement form validation
    - Handle submit with API call
    - Display error messages on failure
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 7.2 Write property test for API payload correctness
    - **Property 9: API Payload Correctness for Journey Creation**
    - **Validates: Requirements 3.3, 8.3**

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement JourneyStudioView components
  - [x] 9.1 Create JourneyOverview component
    - Display journey name, status, overall progress
    - Display current stage indicator
    - Display performance metrics (success rate, avg duration, total time, error rate)
    - Display job summary (total, completed, failed, running, pending)
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 9.2 Create StageNavigation component
    - Display horizontal stage navigation bar
    - Show correct stages based on journey type
    - Handle stage click to select stage
    - Apply status indicators to each stage
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 9.3 Create StageDetailPanel component
    - Display stage name, description, status, progress, duration
    - Display list of steps with status and progress
    - Show log count badge for steps with logs
    - Add "Run Job" button
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

  - [x] 9.4 Create JobHistoryPanel component
    - Display job list with ID, start time, end time, duration, status
    - Display call processing metrics for each job
    - Implement expandable job details
    - Implement sorting by date, status, duration
    - Display aggregate statistics
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [x] 9.5 Create LogsModal component
    - Display log entries with timestamp, level, message
    - Apply color coding for log levels
    - _Requirements: 11.1, 11.2_

  - [x] 9.6 Create ReportPanel component
    - Display execution summary
    - Display call processing metrics
    - Display Glue table state statistics
    - Add download report button
    - _Requirements: 11.3, 11.4, 11.5, 11.6_

- [x] 10. Implement JourneyStudioView container
  - [x] 10.1 Create JourneyStudioView component
    - Integrate JourneyOverview, StageNavigation, StageDetailPanel
    - Integrate JobHistoryPanel, LogsModal, ReportPanel
    - Implement stage selection state
    - Implement polling for running jobs
    - Handle back navigation to list view
    - _Requirements: 4.4, 6.4, 12.1, 12.2, 12.3, 12.4_

  - [x] 10.2 Write unit tests for JourneyStudioView
    - Test stage navigation
    - Test polling start/stop
    - _Requirements: 12.1, 12.2, 12.4_

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement JourneysPanel and AIWorkspace integration
  - [x] 12.1 Create JourneysPanel component
    - Manage view state (list vs studio)
    - Manage selected journey ID
    - Manage filter state
    - Integrate JourneyListView and JourneyStudioView
    - Preserve state on view switches
    - _Requirements: 1.3, 1.4_

  - [x] 12.2 Write property test for state preservation
    - **Property 1: State Preservation on Tab Switch**
    - **Validates: Requirements 1.4**

  - [x] 12.3 Update AIWorkspace to add Journeys tab
    - Add 'journeys' to TabId type
    - Add Journeys tab configuration
    - Render JourneysPanel when Journeys tab is active
    - _Requirements: 1.1, 1.2_

  - [x] 12.4 Write unit tests for AIWorkspace integration
    - Test tab rendering
    - Test tab switching
    - _Requirements: 1.1, 1.2_

- [x] 13. Implement journey actions
  - [x] 13.1 Wire up journey action handlers
    - Implement start journey action
    - Implement pause journey action
    - Implement resume journey action
    - Implement cancel journey action
    - Implement retry journey action
    - Update UI after action completion
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 13.2 Write unit tests for journey actions
    - Test action button visibility by status
    - Test action API calls
    - _Requirements: 7.1-7.6_

- [x] 14. Implement error handling
  - [x] 14.1 Create JourneyErrorBoundary component
    - Implement error boundary for journey components
    - Display error messages with retry option
    - Handle network errors gracefully
    - _Requirements: 3.4, 8.6_

  - [x] 14.2 Add error handling to service layer
    - Add try-catch wrappers to all API calls
    - Implement retry logic for transient failures
    - Display appropriate error toasts
    - _Requirements: 8.6_

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation follows bottom-up approach: types → services → utilities → components → integration
