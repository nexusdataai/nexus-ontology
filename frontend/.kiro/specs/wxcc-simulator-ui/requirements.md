# Requirements Document

## Introduction

This document defines the requirements for adding a WXCC Simulator UI tab to the AI Workspace in the nexus-ui application. The WXCC Simulator provides a Webex Contact Center (WXCC) compatible API for testing call processing pipelines without access to the real WXCC system. This UI will allow users to manage simulator data, view tasks and recordings, seed test data, and monitor simulator status directly from the frontend.

## Glossary

- **WXCC**: Webex Contact Center - Cisco's cloud contact center solution
- **Simulator**: The WXCC Simulator backend service that provides mock WXCC API endpoints
- **Task**: A simulated call/contact record with metadata (origin, destination, status, queue, agent)
- **Recording**: An audio file associated with a task representing the call recording
- **Seeding**: The process of populating the simulator with sample test data
- **AI_Workspace**: The existing tabbed container component in nexus-ui for AI-related tools
- **Backend_Gateway**: The MCP HTTP gateway service that hosts the simulator API endpoints

## Requirements

### Requirement 1: Simulator Tab Integration

**User Story:** As a developer, I want to access the WXCC Simulator from the AI Workspace, so that I can manage test data without leaving the application.

#### Acceptance Criteria

1. THE AI_Workspace SHALL include a new "WXCC Simulator" tab alongside existing tabs (Agent Instructions, Chatbot Editor, Backend Debug)
2. WHEN a user clicks the WXCC Simulator tab, THE AI_Workspace SHALL display the simulator management interface
3. THE WXCC Simulator tab SHALL display an icon consistent with the existing tab design pattern

### Requirement 2: Simulator Status Display

**User Story:** As a developer, I want to see the current status of the WXCC Simulator, so that I can verify it is properly configured and operational.

#### Acceptance Criteria

1. WHEN the simulator tab is active, THE Simulator_UI SHALL display the current simulator status including enabled state, organization ID, S3 bucket, task count, and recording count
2. WHEN the simulator is not enabled or not configured, THE Simulator_UI SHALL display a clear warning message with configuration guidance
3. THE Simulator_UI SHALL provide a refresh button to manually update the status display
4. WHEN the status is refreshed, THE Simulator_UI SHALL show a loading indicator during the API call

### Requirement 3: Task List Display

**User Story:** As a developer, I want to view all tasks in the simulator, so that I can verify test data is correctly configured.

#### Acceptance Criteria

1. THE Simulator_UI SHALL display a paginated table of tasks showing: Task ID, Status, Direction, Origin, Destination, Queue, Agent, and Recording indicator
2. WHEN tasks exist in the simulator, THE Simulator_UI SHALL display them sorted by creation time (newest first)
3. WHEN no tasks exist, THE Simulator_UI SHALL display an empty state message with guidance to seed data
4. THE Simulator_UI SHALL display task status with visual indicators (icons/colors) for completed, abandoned, and transferred states
5. WHEN a task has associated recordings, THE Simulator_UI SHALL display a recording indicator icon

### Requirement 4: Task Filtering and Search

**User Story:** As a developer, I want to filter and search tasks, so that I can quickly find specific test data.

#### Acceptance Criteria

1. THE Simulator_UI SHALL provide filter controls for task status (completed, abandoned, transferred)
2. THE Simulator_UI SHALL provide filter controls for task direction (inbound, outbound)
3. THE Simulator_UI SHALL provide a search input to filter tasks by origin or destination phone number
4. WHEN filters are applied, THE Simulator_UI SHALL update the task list to show only matching tasks
5. THE Simulator_UI SHALL display the count of filtered results vs total tasks

### Requirement 5: Seed Data Functionality

**User Story:** As a developer, I want to seed the simulator with test data, so that I can quickly populate it for testing.

#### Acceptance Criteria

1. THE Simulator_UI SHALL provide a "Seed Data" action button
2. WHEN the Seed Data button is clicked, THE Simulator_UI SHALL display a configuration dialog with options for: number of tasks, days back, include recordings, and reset first
3. WHEN the user confirms seeding, THE Simulator_UI SHALL call the seed API endpoint and display progress
4. WHEN seeding completes successfully, THE Simulator_UI SHALL refresh the task list and display a success message
5. IF seeding fails, THEN THE Simulator_UI SHALL display an error message with details

### Requirement 6: Reset Simulator Functionality

**User Story:** As a developer, I want to reset the simulator, so that I can start fresh with clean test data.

#### Acceptance Criteria

1. THE Simulator_UI SHALL provide a "Reset" action button
2. WHEN the Reset button is clicked, THE Simulator_UI SHALL display a confirmation dialog warning about data loss
3. WHEN the user confirms reset, THE Simulator_UI SHALL call the reset API endpoint
4. WHEN reset completes successfully, THE Simulator_UI SHALL refresh the status and task list
5. IF reset fails, THEN THE Simulator_UI SHALL display an error message with details

### Requirement 7: Task Details View

**User Story:** As a developer, I want to view detailed information about a specific task, so that I can inspect its full metadata and recordings.

#### Acceptance Criteria

1. WHEN a user clicks on a task row, THE Simulator_UI SHALL display a details panel or modal showing all task attributes
2. THE task details view SHALL display: full task ID, timestamps, all attributes (status, direction, origin, destination, queue info, agent info)
3. WHEN the task has recordings, THE task details view SHALL list all associated recordings with playback controls
4. THE task details view SHALL provide a close/dismiss action to return to the task list

### Requirement 8: Recording Playback

**User Story:** As a developer, I want to play recordings directly in the UI, so that I can verify audio content without downloading files.

#### Acceptance Criteria

1. WHEN a recording is available, THE Simulator_UI SHALL provide an audio player control
2. THE audio player SHALL support play, pause, and seek functionality
3. THE audio player SHALL display the recording duration and current playback position
4. IF the recording fails to load, THEN THE Simulator_UI SHALL display an error message

### Requirement 9: Statistics Dashboard

**User Story:** As a developer, I want to see summary statistics about the simulator data, so that I can quickly understand the test data composition.

#### Acceptance Criteria

1. THE Simulator_UI SHALL display summary statistics including: total tasks, tasks by status breakdown, tasks by direction breakdown
2. THE statistics SHALL update when the task list is refreshed or after seeding/reset operations
3. THE statistics SHALL be displayed in a visually clear format (cards, charts, or summary boxes)

### Requirement 10: Error Handling and Connectivity

**User Story:** As a developer, I want clear feedback when the simulator backend is unavailable, so that I can troubleshoot connectivity issues.

#### Acceptance Criteria

1. WHEN the backend API is unreachable, THE Simulator_UI SHALL display a connection error state with retry option
2. WHEN API calls fail, THE Simulator_UI SHALL display user-friendly error messages
3. THE Simulator_UI SHALL not crash or become unresponsive when API errors occur
4. WHEN connectivity is restored, THE Simulator_UI SHALL allow the user to retry failed operations
