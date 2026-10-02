# Requirements Document

## Introduction

This document defines the requirements for implementing a Call Processing Journey feature within the nexus-ui application. The feature will provide a comprehensive journey management system for call processing workflows and operation management, integrated as a new tab within the existing AIWorkspace component. The system will leverage the existing nexus-backend call processing stage infrastructure.

## Glossary

- **Journey**: A long-running, multi-stage workflow that processes calls or manages operations
- **Journey_Studio**: A detailed monitoring and management interface for individual journeys
- **Call_Processing_Journey**: A journey type that processes Webex Contact Center calls through stages: fetch, deduplicate, transcribe, register, and analyze
- **Operation_Management_Journey**: A journey type for managing operational workflows like data migrations or system configurations
- **Stage**: A discrete phase within a journey (e.g., Fetch Tasks, Process Recordings)
- **Step**: A sub-unit of work within a stage
- **Job**: An execution instance of a stage
- **AIWorkspace**: The existing tabbed container component for AI-related tools

## Requirements

### Requirement 1: Journey Tab Integration in AIWorkspace

**User Story:** As a user, I want to access journey management from within the AIWorkspace, so that I can manage call processing and operation journeys alongside other AI tools.

#### Acceptance Criteria

1. WHEN the AIWorkspace component loads, THE System SHALL display a new "Journeys" tab alongside existing tabs (Agent Instructions, Chatbot Editor, Backend Debug, WXCC Simulator)
2. WHEN a user clicks the Journeys tab, THE System SHALL display the JourneysPanel component
3. THE JourneysPanel SHALL provide navigation between journey list view and journey studio view
4. WHEN switching between tabs, THE System SHALL preserve the journey panel state (selected journey, filters)

### Requirement 2: Journey List View

**User Story:** As a user, I want to see a list of all my journeys, so that I can monitor their status and manage them.

#### Acceptance Criteria

1. WHEN the journey list loads, THE System SHALL display all journeys with their name, status, progress, and type
2. WHEN a user searches by journey name, THE System SHALL filter the list to show only matching journeys
3. WHEN a user filters by status, THE System SHALL display only journeys with the selected status (created, running, paused, completed, failed, cancelled)
4. WHEN a user filters by journey type, THE System SHALL display only journeys of the selected type (call-processing, operation-management)
5. THE System SHALL display journey cards showing: journey name, ID, status badge, progress bar, current stage, creation time, and action buttons
6. WHEN a journey is running, THE System SHALL display an animated progress indicator
7. WHEN a user clicks "Journey Studio" on a journey card, THE System SHALL navigate to the Journey Studio view for that journey

### Requirement 3: Call Processing Journey Creation

**User Story:** As a user, I want to create new call processing journeys, so that I can process Webex CC calls through the analytics pipeline.

#### Acceptance Criteria

1. WHEN a user clicks "New Call Processing Journey", THE System SHALL display a journey creation dialog
2. THE creation dialog SHALL allow configuration of: journey name, time range (minutes_back), transcription enabled, Glue registration enabled, AI analysis enabled, and skip processed tasks option
3. WHEN a user submits the creation form with valid data, THE System SHALL create a new call processing journey via the backend API
4. IF the journey creation fails, THEN THE System SHALL display an error message with details
5. WHEN a journey is created successfully, THE System SHALL add it to the journey list and optionally navigate to Journey Studio

### Requirement 4: Journey Studio - Overview Dashboard

**User Story:** As a user, I want to see a comprehensive dashboard for a journey, so that I can understand its overall status and performance.

#### Acceptance Criteria

1. WHEN Journey Studio loads for a journey, THE System SHALL display the journey overview with name, status, overall progress, and current stage
2. THE System SHALL display performance metrics: success rate, average job duration, total execution time, error rate
3. THE System SHALL display job summary: total jobs, completed jobs, failed jobs, running jobs, pending jobs
4. WHEN the journey status changes, THE System SHALL update the dashboard in real-time or on manual refresh

### Requirement 5: Journey Studio - Stage Navigation

**User Story:** As a user, I want to navigate between journey stages, so that I can monitor and manage each stage independently.

#### Acceptance Criteria

1. THE System SHALL display a horizontal stage navigation bar showing all stages for the journey type
2. FOR call processing journeys, THE System SHALL display stages: Fetch Tasks, Deduplication Check, Process Recordings, Register Metadata, AI Analysis
3. FOR operation management journeys, THE System SHALL display stages: Configuration, Execution, Validation, Completion
4. WHEN a user clicks a stage, THE System SHALL display the stage detail panel for that stage
5. THE System SHALL visually indicate stage status: completed (green), running (blue), pending (gray), failed (red)

### Requirement 6: Journey Studio - Stage Detail Panel

**User Story:** As a user, I want to see detailed information about a stage, so that I can understand its progress and troubleshoot issues.

#### Acceptance Criteria

1. WHEN a stage is selected, THE System SHALL display stage name, description, status, progress, and duration
2. THE System SHALL display a list of steps within the stage with their individual status and progress
3. WHEN a step has logs available, THE System SHALL display a log count badge and allow viewing logs
4. THE System SHALL display job history for the stage showing recent job executions
5. WHEN a user clicks "Run Job", THE System SHALL trigger a new job execution for the stage via the backend API

### Requirement 7: Journey Actions

**User Story:** As a user, I want to control journey execution, so that I can start, pause, resume, or cancel journeys as needed.

#### Acceptance Criteria

1. WHEN a journey is in "created" status, THE System SHALL allow the user to start the journey
2. WHEN a journey is in "running" status, THE System SHALL allow the user to pause the journey
3. WHEN a journey is in "paused" status, THE System SHALL allow the user to resume the journey
4. WHEN a journey is in "created", "running", or "paused" status, THE System SHALL allow the user to cancel the journey
5. WHEN a journey is in "failed" status, THE System SHALL allow the user to retry the journey
6. WHEN an action is performed, THE System SHALL update the journey status and refresh the display

### Requirement 8: Backend API Integration

**User Story:** As a developer, I want the UI to communicate with the nexus-backend, so that journey operations are persisted and executed.

#### Acceptance Criteria

1. THE System SHALL communicate with the backend via HTTP API endpoints for journey CRUD operations
2. WHEN fetching journeys, THE System SHALL call the backend journeys list endpoint
3. WHEN creating a journey, THE System SHALL call the backend journey creation endpoint with configuration
4. WHEN executing a stage job, THE System SHALL call the backend stage execution endpoint
5. WHEN fetching stage steps and logs, THE System SHALL call the backend stage details endpoint
6. IF the backend is unavailable, THEN THE System SHALL display a connection error and allow retry

### Requirement 9: Journey Type Detection

**User Story:** As a user, I want the system to automatically detect journey types, so that the correct stages and UI are displayed.

#### Acceptance Criteria

1. WHEN loading a journey, THE System SHALL detect if it is a call-processing or operation-management journey based on metadata
2. FOR call-processing journeys, THE System SHALL display call-specific stages and metrics (tasks fetched, recordings processed, transcripts generated)
3. FOR operation-management journeys, THE System SHALL display operation-specific stages and metrics
4. THE System SHALL allow manual override of journey type detection for edge cases

### Requirement 10: Job History and Metrics

**User Story:** As a user, I want to see all jobs that have run on a journey, so that I can track execution history and analyze performance over time.

#### Acceptance Criteria

1. THE System SHALL display a job history panel showing all jobs executed for the journey
2. FOR each job, THE System SHALL display: job ID, start time, end time, duration, and status
3. FOR call processing jobs, THE System SHALL display key metrics: calls fetched, calls processed, calls analyzed, errors count, transcripts generated
4. WHEN a user clicks on a job, THE System SHALL expand to show detailed job information
5. THE System SHALL allow sorting job history by date, status, or duration
6. THE System SHALL display aggregate statistics across all jobs: total calls processed, success rate, average processing time

### Requirement 11: Logs and Reports

**User Story:** As a user, I want to view logs and reports for journey stages, so that I can debug issues and understand processing results.

#### Acceptance Criteria

1. WHEN a user clicks "View Logs" for a step, THE System SHALL display a modal with step logs
2. THE logs modal SHALL display log entries with timestamp, level (info, warning, error), and message
3. WHEN a stage is completed, THE System SHALL allow downloading or viewing the stage report
4. THE report SHALL include execution summary, metrics, and any artifacts generated
5. FOR call processing jobs, THE report SHALL include: tasks found, new tasks, skipped tasks, processed successfully, failed tasks, transcripts collected, analyzed count
6. THE System SHALL display Glue table state statistics: total records, records with recording, records with transcript, records with analysis

### Requirement 12: Real-time Updates

**User Story:** As a user, I want to see journey progress updates, so that I can monitor long-running jobs without manual refresh.

#### Acceptance Criteria

1. WHEN a job is running, THE System SHALL poll for status updates at regular intervals (every 5 seconds)
2. WHEN a job completes or fails, THE System SHALL stop polling and display the final status
3. THE System SHALL provide a manual refresh button for on-demand updates
4. WHEN the user navigates away from Journey Studio, THE System SHALL stop polling to conserve resources
