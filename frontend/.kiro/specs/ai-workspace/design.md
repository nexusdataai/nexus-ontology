# Design Document: AI Workspace

## Overview

The AI Workspace feature provides a unified interface for configuring AI agent behavior, testing chatbot interactions, and debugging the nexus-backend gateway server. It consists of three main components organized in a tabbed interface:

1. **Agent Instructions Editor** - Configure AI agent behavior via markdown
2. **Chatbot Editor** - Test AI assistant interactions
3. **Backend Debug Platform** - Diagnose and test API/MCP tools

The design follows the existing patterns in nexus-ui, leveraging the existing `chatbotService`, `apiClient`, and UI component library (shadcn/ui).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI Workspace                              │
│  ┌─────────────────┬─────────────────┬─────────────────────────┐│
│  │ Agent           │ Chatbot         │ Backend Debug           ││
│  │ Instructions    │ Editor          │ Platform                ││
│  └────────┬────────┴────────┬────────┴────────────┬────────────┘│
│           │                 │                     │              │
│           ▼                 ▼                     ▼              │
│  ┌────────────────┐ ┌──────────────┐ ┌─────────────────────────┐│
│  │ chatbotService │ │chatbotService│ │ backendDebugService     ││
│  │ (instructions) │ │ (messages)   │ │                         ││
│  └────────────────┘ └──────────────┘ └───────────┬─────────────┘│
│                                                   │              │
└───────────────────────────────────────────────────┼──────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │   nexus-backend Gateway     │
                                    │   (mcp_http_gateway.py)       │
                                    │                               │
                                    │  ┌─────────┐  ┌─────────────┐ │
                                    │  │ /tools  │  │ /api/v1/*   │ │
                                    │  │ MCP     │  │ REST APIs   │ │
                                    │  └─────────┘  └─────────────┘ │
                                    │                               │
                                    │  ┌─────────────────────────┐  │
                                    │  │ Worker Pool (MCP)       │  │
                                    │  └─────────────────────────┘  │
                                    └───────────────────────────────┘
```

## Components and Interfaces

### 1. AIWorkspace Component

**File:** `src/components/AIWorkspace.tsx`

```typescript
interface AIWorkspaceProps {
  onNavigate?: (tab: string) => void;
}

type ActiveTab = 'instructions' | 'chat' | 'debug';

interface AIWorkspaceState {
  activeTab: ActiveTab;
}
```

**Responsibilities:**
- Render tabbed interface with three tabs
- Manage active tab state
- Display status bar with current tab and connection status
- Pass navigation callback to child components

### 2. AgentInstructionsEditor Component

**File:** `src/components/AgentInstructionsEditor.tsx`

```typescript
interface AgentInstructionsEditorState {
  instructions: string;
  isLoading: boolean;
  isSaving: boolean;
  lastUpdated: Date | null;
}
```

**Responsibilities:**
- Load instructions from `/public/agent-instructions.md`
- Provide markdown textarea for editing
- Calculate and display line/word count
- Save instructions to chatbotService
- Reload instructions from file
- Display toast notifications for success/error

### 3. ChatbotEditor Component

**File:** `src/pages/ChatbotEditor.tsx`

```typescript
interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

interface ChatbotEditorProps {
  onNavigate?: (tab: string) => void;
}

interface ChatbotEditorState {
  messages: Message[];
  inputValue: string;
  isLoading: boolean;
}
```

**Responsibilities:**
- Display chat message history
- Send messages via chatbotService
- Handle navigation actions from AI responses
- Clear chat functionality
- Display message statistics

### 4. BackendDebugPlatform Component

**File:** `src/components/BackendDebugPlatform.tsx`

```typescript
type ConnectionStatus = 'connected' | 'warning' | 'error';

interface LogEntry {
  timestamp: Date;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
}

interface WorkerStats {
  total_workers: number;
  busy_workers: number;
  total_requests: number;
  total_errors: number;
  worker_details: WorkerDetail[];
}

interface WorkerDetail {
  id: number;
  busy: boolean;
  requests: number;
  errors: number;
  last_used: string;
}

interface BackendDebugPlatformState {
  serverUrl: string;
  connectionStatus: ConnectionStatus;
  availableTools: MCPTool[];
  selectedTool: string;
  toolParams: string;
  apiEndpoint: string;
  apiMethod: 'GET' | 'POST' | 'PUT' | 'DELETE';
  apiBody: string;
  workerStats: WorkerStats | null;
  activityLog: LogEntry[];
  outputPanels: {
    connection: string;
    tools: string;
    api: string;
    stats: string;
  };
}
```

**Responsibilities:**
- Connection testing (root `/` and `/health` endpoints)
- MCP tools listing and execution
- REST API endpoint testing
- Worker pool statistics monitoring
- Activity logging

### 5. BackendDebugService

**File:** `src/services/backendDebugService.ts`

```typescript
interface GatewayInfo {
  service: string;
  version: string;
  protocol: string[];
  transport: string[];
  streaming: boolean;
  apis_enabled: boolean;
  workers: WorkerStats;
  endpoints: Record<string, string | null>;
  timestamp: string;
}

interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  workers: WorkerStats;
  timestamp: string;
}

interface MCPTool {
  name: string;
  description?: string;
  inputSchema?: Record<string, any>;
}

interface ToolsListResponse {
  tools: MCPTool[];
}

interface ToolCallResponse {
  content: Array<{
    type: string;
    text?: string;
    data?: any;
  }>;
  isError?: boolean;
}

interface ApiResponse<T = any> {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: T;
  timing: number;
}

class BackendDebugService {
  // Configuration
  getServerUrl(): Promise<string>;
  getApiKey(): Promise<string>;
  
  // Connection testing
  testConnection(): Promise<GatewayInfo>;
  healthCheck(): Promise<HealthResponse>;
  
  // MCP Tools
  listTools(): Promise<ToolsListResponse>;
  executeTool(toolName: string, args: Record<string, any>): Promise<ToolCallResponse>;
  
  // REST APIs
  callApi<T>(endpoint: string, method: string, body?: any): Promise<ApiResponse<T>>;
  
  // Worker stats
  getWorkerStats(): Promise<WorkerStats>;
}
```

## Data Models

### Gateway Server Endpoints

Based on `mcp_http_gateway.py`:

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/` | GET | Server info and capabilities | No |
| `/health` | GET | Health check with worker status | No |
| `/tools` | GET | List available MCP tools | Yes |
| `/tools/{name}` | POST | Execute MCP tool | Yes |
| `/stats` | GET | Worker pool statistics | Yes |
| `/api/v1/journeys/*` | Various | Journey management APIs | Yes |
| `/api/v1/analytics/*` | Various | Analytics APIs | Yes |
| `/api/v1/auth/*` | Various | Authentication APIs | Yes |
| `/api/v1/health/*` | Various | Health check APIs | No |
| `/api/v1/qa/*` | Various | QA Analytics APIs | Yes |

### Configuration Schema

**File:** `public/config.json` (extension)

```json
{
  "api": {
    "baseUrl": "http://localhost:8000",
    "timeout": 30000
  },
  "gateway": {
    "apiKey": "super-secret"
  }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Tab Switching Consistency

*For any* tab in the AI Workspace (instructions, chat, debug), clicking on that tab SHALL result in the corresponding content panel being displayed and the status bar reflecting the active tab.

**Validates: Requirements 1.2, 1.3**

### Property 2: Line and Word Count Accuracy

*For any* text string in the Agent Instructions Editor, the displayed line count SHALL equal the number of newline characters plus one, and the word count SHALL equal the number of whitespace-separated tokens.

**Validates: Requirements 2.5**

### Property 3: Message Rendering Completeness

*For any* list of chat messages, all messages SHALL be rendered with correct sender styling (user/assistant), visible timestamps, and the message count SHALL equal the actual number of messages in the list.

**Validates: Requirements 3.1, 3.5, 3.6**

### Property 4: Connection Status Visual Mapping

*For any* connection state (connected, warning, error), the Backend Debug Platform SHALL display the corresponding visual indicator (green, yellow, red) consistently.

**Validates: Requirements 4.4**

### Property 5: Tool Dropdown Population

*For any* list of MCP tools returned from the `/tools` endpoint, all tools SHALL appear as selectable options in the tool dropdown.

**Validates: Requirements 5.2**

### Property 6: JSON Validation Round-Trip

*For any* valid JSON string entered in the tool parameters textarea, parsing and re-stringifying SHALL produce an equivalent JSON structure. For any invalid JSON string, validation SHALL return an error.

**Validates: Requirements 5.6**

### Property 7: API Response Display Completeness

*For any* API response, the Backend Debug Platform SHALL display the status code, response headers, response body, and timing information.

**Validates: Requirements 6.5, 6.6**

### Property 8: Worker Stats Display Completeness

*For any* worker statistics response, the Backend Debug Platform SHALL display total workers, busy workers, total requests, total errors, and details for each individual worker.

**Validates: Requirements 7.2, 7.3**

### Property 9: Activity Log Integrity

*For any* sequence of debug operations, all operations SHALL be logged with timestamps, the log SHALL maintain chronological order, entries SHALL have correct status indicators, and the log SHALL contain at most 50 entries (most recent).

**Validates: Requirements 8.1, 8.2, 8.3, 8.5**

### Property 10: API Key Authentication Header

*For any* authenticated request to the gateway server, the `x-api-key` header SHALL be included with the configured API key value.

**Validates: Requirements 9.2, 10.5**

### Property 11: Error Response Structure

*For any* error scenario in the Backend Debug Service, the returned error SHALL contain a structured response with error message and appropriate error type.

**Validates: Requirements 10.6**

## Error Handling

### Connection Errors

| Error Type | Handling |
|------------|----------|
| Network unreachable | Display "Cannot connect to server" with error status |
| Timeout | Display "Request timed out" with warning status |
| 401 Unauthorized | Display "Invalid API key" with error status |
| 5xx Server Error | Display server error message with error status |

### Tool Execution Errors

| Error Type | Handling |
|------------|----------|
| Invalid JSON params | Display JSON parse error before execution |
| Tool not found | Display "Tool not found" error |
| Tool execution error | Display error from tool response |

### API Errors

| Error Type | Handling |
|------------|----------|
| Invalid endpoint | Display 404 error |
| Invalid method | Display method not allowed error |
| Request body parse error | Display JSON parse error |

## Testing Strategy

### Unit Tests

Unit tests will verify specific examples and edge cases:

1. **Component Rendering**
   - AIWorkspace renders all three tabs
   - AgentInstructionsEditor renders textarea and buttons
   - BackendDebugPlatform renders all sections

2. **User Interactions**
   - Tab switching updates active tab state
   - Button clicks trigger appropriate handlers
   - Input changes update state

3. **Service Methods**
   - BackendDebugService methods return expected types
   - Error handling returns structured errors

### Property-Based Tests

Property-based tests will use a testing library (e.g., fast-check) to verify universal properties:

1. **Property 2: Line/Word Count** - Generate random strings and verify counts
2. **Property 6: JSON Validation** - Generate random JSON and verify round-trip
3. **Property 9: Activity Log** - Generate random operation sequences and verify log integrity
4. **Property 10: API Key Header** - Generate random requests and verify header presence

### Integration Tests

1. **End-to-end flow**: Tab navigation → content display → status bar update
2. **Chatbot flow**: Send message → receive response → display message
3. **Debug flow**: Test connection → list tools → execute tool → view results

### Test Configuration

- Use Vitest as the test runner (already configured in nexus-ui)
- Use React Testing Library for component tests
- Use fast-check for property-based tests
- Mock fetch calls for service tests
