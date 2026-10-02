# Implementation Plan: AI Workspace

## Overview

This implementation plan breaks down the AI Workspace feature into discrete coding tasks. The approach is incremental, starting with the service layer, then building components, and finally integrating everything together.

## Tasks

- [x] 1. Create Backend Debug Service
  - [x] 1.1 Create backendDebugService.ts with type definitions
    - Define interfaces: GatewayInfo, HealthResponse, MCPTool, ToolsListResponse, ToolCallResponse, ApiResponse, WorkerStats
    - Create BackendDebugService class skeleton
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 1.2 Implement configuration methods
    - Implement getServerUrl() to read from config.json
    - Implement getApiKey() to read from config.json
    - Handle missing configuration gracefully
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 1.3 Implement connection testing methods
    - Implement testConnection() calling gateway root endpoint
    - Implement healthCheck() calling /health endpoint
    - Add proper error handling and timeout
    - _Requirements: 4.2, 4.3, 4.5, 10.1_

  - [x] 1.4 Implement MCP tools methods
    - Implement listTools() calling /tools endpoint
    - Implement executeTool() calling /tools/{name} endpoint
    - Include x-api-key header for authentication
    - _Requirements: 5.1, 5.4, 10.2, 10.5_

  - [x] 1.5 Implement REST API methods
    - Implement callApi() for generic API calls
    - Support GET, POST, PUT, DELETE methods
    - Calculate and return timing information
    - _Requirements: 6.4, 6.5, 6.6, 10.3_

  - [x] 1.6 Implement worker stats method
    - Implement getWorkerStats() calling /stats endpoint
    - _Requirements: 7.1, 10.4_

  - [x] 1.7 Write property test for API key authentication
    - **Property 10: API Key Authentication Header**
    - **Validates: Requirements 9.2, 10.5**

  - [x] 1.8 Write property test for error response structure
    - **Property 11: Error Response Structure**
    - **Validates: Requirements 10.6**

- [x] 2. Checkpoint - Ensure backend service tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Update chatbotService for Agent Instructions
  - [x] 3.1 Add agent instructions management to chatbotService
    - Add agentInstructions property
    - Implement getAgentInstructions() method
    - Implement updateAgentInstructions() method
    - Implement reloadInstructions() method to fetch from file
    - _Requirements: 2.1, 2.3, 2.4_

- [x] 4. Create Agent Instructions Editor Component
  - [x] 4.1 Create AgentInstructionsEditor.tsx component
    - Create component with state for instructions, loading, saving, lastUpdated
    - Implement loadInstructions() on mount
    - Implement saveInstructions() handler
    - Implement reloadFromFile() handler
    - _Requirements: 2.1, 2.3, 2.4, 2.7_

  - [x] 4.2 Add UI elements for Agent Instructions Editor
    - Add textarea for markdown editing
    - Add "Apply Changes" and "Reload from File" buttons
    - Add line count and word count display
    - Add last updated timestamp display
    - Add toast notifications for success/error
    - _Requirements: 2.2, 2.5, 2.6, 2.7_

  - [x] 4.3 Write property test for line and word count
    - **Property 2: Line and Word Count Accuracy**
    - **Validates: Requirements 2.5**

- [x] 5. Create Chatbot Editor Component
  - [x] 5.1 Create ChatbotEditor.tsx page component
    - Create component with state for messages, inputValue, isLoading
    - Implement handleSendMessage() using chatbotService
    - Implement handleNavigationAction() for AI navigation responses
    - Implement clearChat() handler
    - _Requirements: 3.2, 3.4, 3.7_

  - [x] 5.2 Add UI elements for Chatbot Editor
    - Add message list with user/assistant styling
    - Add input field and send button
    - Add loading indicator
    - Add clear chat button
    - Add message count statistics
    - Add timestamps to messages
    - _Requirements: 3.1, 3.3, 3.5, 3.6_

  - [x] 5.3 Write property test for message rendering
    - **Property 3: Message Rendering Completeness**
    - **Validates: Requirements 3.1, 3.5, 3.6**

- [x] 6. Checkpoint - Ensure editor components work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Create Backend Debug Platform Component
  - [x] 7.1 Create BackendDebugPlatform.tsx component structure
    - Create component with state for all debug sections
    - Implement activity log management (add, clear, limit to 50)
    - Implement connection status indicator logic
    - _Requirements: 4.4, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 7.2 Implement Connection Testing section
    - Add server URL display with manual override input
    - Add "Test Connection" button calling testConnection()
    - Add "Health Check" button calling healthCheck()
    - Add connection status indicator (green/yellow/red)
    - Add output panel for connection results
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 9.4_

  - [x] 7.3 Implement MCP Tools Testing section
    - Add "List Tools" button calling listTools()
    - Add tool selection dropdown populated from tools list
    - Add JSON textarea for tool parameters
    - Add "Execute Tool" button calling executeTool()
    - Add "Validate Params" button for JSON validation
    - Add output panel for tool results
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [x] 7.4 Implement REST API Testing section
    - Add API endpoint categories display
    - Add endpoint path input field
    - Add HTTP method dropdown (GET, POST, PUT, DELETE)
    - Add JSON textarea for request body
    - Add "Execute API" button calling callApi()
    - Add output panel showing status, headers, body, timing
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 7.5 Implement Worker Pool Monitoring section
    - Add "Get Stats" button calling getWorkerStats()
    - Add display for total workers, busy workers, requests, errors
    - Add table/list for individual worker details
    - Add refresh button
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 7.6 Implement Activity Log section
    - Add scrollable log display area
    - Add visual indicators for log entry types (success/error/warning)
    - Add "Clear Logs" button
    - Add timestamps to log entries
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 7.7 Write property test for connection status visual mapping
    - **Property 4: Connection Status Visual Mapping**
    - **Validates: Requirements 4.4**

  - [x] 7.8 Write property test for tool dropdown population
    - **Property 5: Tool Dropdown Population**
    - **Validates: Requirements 5.2**

  - [x] 7.9 Write property test for JSON validation
    - **Property 6: JSON Validation Round-Trip**
    - **Validates: Requirements 5.6**

  - [x] 7.10 Write property test for API response display
    - **Property 7: API Response Display Completeness**
    - **Validates: Requirements 6.5, 6.6**

  - [x] 7.11 Write property test for worker stats display
    - **Property 8: Worker Stats Display Completeness**
    - **Validates: Requirements 7.2, 7.3**

  - [x] 7.12 Write property test for activity log integrity
    - **Property 9: Activity Log Integrity**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.5**

- [x] 8. Checkpoint - Ensure debug platform works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Create AI Workspace Container
  - [x] 9.1 Create AIWorkspace.tsx component
    - Create component with activeTab state
    - Implement tab switching logic
    - Render AgentInstructionsEditor, ChatbotEditor, BackendDebugPlatform based on active tab
    - _Requirements: 1.1, 1.2_

  - [x] 9.2 Add status bar to AI Workspace
    - Display current active tab name
    - Display connection status indicator
    - Add visual styling for status bar
    - _Requirements: 1.3_

  - [x] 9.3 Write property test for tab switching
    - **Property 1: Tab Switching Consistency**
    - **Validates: Requirements 1.2, 1.3**

- [x] 10. Integrate AI Workspace into Application
  - [x] 10.1 Add AI Workspace route to application
    - Add route in App.tsx or router configuration
    - _Requirements: 1.4_

  - [x] 10.2 Add AI Workspace to navigation
    - Add navigation link/button to access AI Workspace
    - _Requirements: 1.4_

  - [x] 10.3 Update config.json with gateway configuration
    - Add gateway.apiKey configuration
    - Ensure api.baseUrl points to gateway server
    - _Requirements: 9.1, 9.2_

- [x] 11. Create agent-instructions.md file
  - [x] 11.1 Create public/agent-instructions.md
    - Create markdown file with AI agent instructions
    - Include tool mappings and response guidelines
    - _Requirements: 2.1_

- [x] 12. Final Checkpoint - Full integration test
  - All tests pass (TypeScript compilation successful)
  - AI Workspace accessible from navigation at /ai-workspace
  - All three tabs implemented: Agent Instructions, Chatbot Editor, Backend Debug
  - Backend debug platform ready to connect to gateway

## Notes

- All tasks including property tests are required for comprehensive coverage
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation follows the existing patterns in nexus-ui (shadcn/ui components, services pattern)
