# Requirements Document

## Introduction

This specification defines the AI Workspace feature for the nexus-ui application. The AI Workspace provides a unified interface for configuring AI agent behavior, testing chatbot interactions, and debugging the backend gateway server (nexus-backend) which provides both REST APIs and MCP tools. Unlike the alert-engine-ui which has a separate MCP debug interface, this implementation integrates with the unified gateway server that exposes both `/api/v1/*` REST endpoints and `/tools/*` MCP tool endpoints.

## Glossary

- **AI_Workspace**: A tabbed container component providing access to Agent Instructions Editor, Chatbot Editor, and Backend Debug Platform
- **Agent_Instructions_Editor**: A markdown editor for configuring AI agent behavior and tool mappings
- **Chatbot_Editor**: A chat interface for testing AI assistant interactions
- **Backend_Debug_Platform**: A diagnostic interface for testing and monitoring the nexus-backend gateway server's API and MCP tool endpoints
- **Gateway_Server**: The nexus-backend unified HTTP gateway (`mcp_http_gateway.py`) that provides both REST APIs and MCP tools
- **MCP_Tool**: Model Context Protocol tool exposed via `/tools/{tool_name}` endpoint
- **REST_API**: Traditional REST endpoints exposed via `/api/v1/*` paths
- **Worker_Pool**: The backend's subprocess pool that manages MCP server instances
- **chatbotService**: The frontend service that handles AI chat interactions

## Requirements

### Requirement 1: AI Workspace Container

**User Story:** As a developer, I want a unified workspace for AI-related features, so that I can configure, test, and debug AI functionality from a single location.

#### Acceptance Criteria

1. THE AI_Workspace SHALL provide a tabbed interface with three tabs: "Agent Instructions", "Chatbot Editor", and "Backend Debug"
2. WHEN a user clicks on a tab, THE AI_Workspace SHALL display the corresponding content panel
3. THE AI_Workspace SHALL display a status bar showing the current active tab and connection status
4. THE AI_Workspace SHALL be accessible from the main application navigation

### Requirement 2: Agent Instructions Editor

**User Story:** As a developer, I want to edit AI agent instructions in markdown format, so that I can customize how the AI assistant behaves and which tools it uses.

#### Acceptance Criteria

1. THE Agent_Instructions_Editor SHALL load agent instructions from a markdown file on initialization
2. THE Agent_Instructions_Editor SHALL provide a textarea for editing markdown instructions
3. WHEN a user clicks "Apply Changes", THE Agent_Instructions_Editor SHALL update the chatbotService with new instructions
4. WHEN a user clicks "Reload from File", THE Agent_Instructions_Editor SHALL reload instructions from the source file
5. THE Agent_Instructions_Editor SHALL display line count and word count statistics
6. THE Agent_Instructions_Editor SHALL display the last updated timestamp
7. THE Agent_Instructions_Editor SHALL show success/error notifications using toast messages

### Requirement 3: Chatbot Editor

**User Story:** As a developer, I want to test chatbot interactions in a dedicated interface, so that I can verify AI responses and tool integrations work correctly.

#### Acceptance Criteria

1. THE Chatbot_Editor SHALL display a chat message history with user and assistant messages
2. WHEN a user sends a message, THE Chatbot_Editor SHALL call the chatbotService and display the response
3. THE Chatbot_Editor SHALL show a loading indicator while waiting for AI responses
4. WHEN a user clicks "Clear Chat", THE Chatbot_Editor SHALL reset the conversation history
5. THE Chatbot_Editor SHALL display message timestamps
6. THE Chatbot_Editor SHALL display message count statistics
7. WHEN the AI response contains a navigation action, THE Chatbot_Editor SHALL execute the navigation

### Requirement 4: Backend Debug Platform - Connection Testing

**User Story:** As a developer, I want to test connectivity to the backend gateway server, so that I can verify the server is running and accessible.

#### Acceptance Criteria

1. THE Backend_Debug_Platform SHALL display the current gateway server URL from configuration
2. WHEN a user clicks "Test Connection", THE Backend_Debug_Platform SHALL call the gateway's root endpoint (`/`) and display server information
3. WHEN a user clicks "Health Check", THE Backend_Debug_Platform SHALL call the `/health` endpoint and display worker pool status
4. THE Backend_Debug_Platform SHALL display connection status with visual indicators (connected/warning/error)
5. IF the connection test fails, THEN THE Backend_Debug_Platform SHALL display the error message and set status to error

### Requirement 5: Backend Debug Platform - MCP Tools Testing

**User Story:** As a developer, I want to list and execute MCP tools from the debug interface, so that I can test tool functionality without using the chatbot.

#### Acceptance Criteria

1. WHEN a user clicks "List Tools", THE Backend_Debug_Platform SHALL call `/tools` endpoint and display available MCP tools
2. THE Backend_Debug_Platform SHALL provide a dropdown to select an MCP tool for testing
3. THE Backend_Debug_Platform SHALL provide a JSON textarea for entering tool parameters
4. WHEN a user clicks "Execute Tool", THE Backend_Debug_Platform SHALL call `/tools/{tool_name}` with the provided parameters
5. THE Backend_Debug_Platform SHALL display tool execution results in a formatted output panel
6. WHEN a user clicks "Validate Params", THE Backend_Debug_Platform SHALL validate the JSON syntax and display validation result
7. IF tool execution fails, THEN THE Backend_Debug_Platform SHALL display the error details

### Requirement 6: Backend Debug Platform - REST API Testing

**User Story:** As a developer, I want to test REST API endpoints from the debug interface, so that I can verify API functionality and diagnose issues.

#### Acceptance Criteria

1. THE Backend_Debug_Platform SHALL display available REST API endpoint categories (journeys, analytics, auth, health, qa)
2. THE Backend_Debug_Platform SHALL provide input fields for API endpoint path and HTTP method selection
3. THE Backend_Debug_Platform SHALL provide a JSON textarea for request body (for POST/PUT/PATCH methods)
4. WHEN a user clicks "Execute API", THE Backend_Debug_Platform SHALL call the specified endpoint and display the response
5. THE Backend_Debug_Platform SHALL display response status code, headers, and body
6. THE Backend_Debug_Platform SHALL display request/response timing information

### Requirement 7: Backend Debug Platform - Worker Pool Monitoring

**User Story:** As a developer, I want to monitor the MCP worker pool status, so that I can diagnose performance issues and worker health.

#### Acceptance Criteria

1. WHEN a user clicks "Get Stats", THE Backend_Debug_Platform SHALL call `/stats` endpoint and display worker pool statistics
2. THE Backend_Debug_Platform SHALL display total workers, busy workers, total requests, and total errors
3. THE Backend_Debug_Platform SHALL display individual worker details including ID, busy status, request count, and last used time
4. THE Backend_Debug_Platform SHALL provide a refresh button to update worker statistics

### Requirement 8: Backend Debug Platform - Activity Logging

**User Story:** As a developer, I want to see a log of all debug operations, so that I can track what tests have been performed and their results.

#### Acceptance Criteria

1. THE Backend_Debug_Platform SHALL maintain an activity log of all debug operations
2. WHEN any debug operation is performed, THE Backend_Debug_Platform SHALL add a timestamped entry to the activity log
3. THE Backend_Debug_Platform SHALL display log entries with visual indicators for success/error/warning status
4. WHEN a user clicks "Clear Logs", THE Backend_Debug_Platform SHALL clear the activity log
5. THE Backend_Debug_Platform SHALL limit the activity log to the most recent 50 entries

### Requirement 9: Configuration Integration

**User Story:** As a developer, I want the debug platform to use the application's configuration, so that it connects to the correct backend server.

#### Acceptance Criteria

1. THE Backend_Debug_Platform SHALL read the gateway server URL from the application's config.json
2. THE Backend_Debug_Platform SHALL use the configured API key for authenticated requests
3. WHEN configuration is not available, THE Backend_Debug_Platform SHALL display a configuration error message
4. THE Backend_Debug_Platform SHALL allow manual override of the server URL for testing different environments

### Requirement 10: Backend Service Integration

**User Story:** As a developer, I want a backend service that handles all gateway communication, so that the debug platform has a clean separation of concerns.

#### Acceptance Criteria

1. THE Backend_Service SHALL provide methods for testing gateway connection
2. THE Backend_Service SHALL provide methods for listing and executing MCP tools
3. THE Backend_Service SHALL provide methods for calling REST API endpoints
4. THE Backend_Service SHALL provide methods for retrieving worker pool statistics
5. THE Backend_Service SHALL handle authentication using the configured API key
6. THE Backend_Service SHALL handle errors gracefully and return structured error responses
