# Design Document: Call Processing Journeys

## Overview

This design document describes the architecture and implementation approach for the Call Processing Journeys feature in nexus-ui. The feature adds a comprehensive journey management system integrated as a new tab within the AIWorkspace component, enabling users to create, monitor, and manage call processing and operation management journeys.

The implementation follows a component-based architecture with clear separation between UI components, state management, and backend service integration. It leverages the existing nexus-backend call processing stage infrastructure.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AIWorkspace                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  Tabs: Instructions | Chatbot | Debug | Simulator | [Journeys]      ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                      JourneysPanel                                   ││
│  │  ┌─────────────────────────────────────────────────────────────────┐││
│  │  │  View: [Journey List] | [Journey Studio]                        │││
│  │  └─────────────────────────────────────────────────────────────────┘││
│  │                                                                      ││
│  │  ┌─────────────────────┐  ┌─────────────────────────────────────────┐│
│  │  │   JourneyListView   │  │          JourneyStudioView              ││
│  │  │  ┌───────────────┐  │  │  ┌─────────────────────────────────────┐││
│  │  │  │ Filters/Search│  │  │  │ Overview Dashboard                  │││
│  │  │  └───────────────┘  │  │  └─────────────────────────────────────┘││
│  │  │  ┌───────────────┐  │  │  ┌─────────────────────────────────────┐││
│  │  │  │ Journey Cards │  │  │  │ Stage Navigation                    │││
│  │  │  │  - Card 1     │  │  │  └─────────────────────────────────────┘││
│  │  │  │  - Card 2     │  │  │  ┌─────────────────────────────────────┐││
│  │  │  │  - ...        │  │  │  │ Stage Detail Panel                  │││
│  │  │  └───────────────┘  │  │  │  - Steps List                       │││
│  │  │  ┌───────────────┐  │  │  │  - Job History                      │││
│  │  │  │ Create Button │  │  │  │  - Actions                          │││
│  │  │  └───────────────┘  │  │  └─────────────────────────────────────┘││
│  │  └─────────────────────┘  └─────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. AIWorkspace Enhancement

The existing AIWorkspace component will be extended to include a new "Journeys" tab.

```typescript
// Updated TAB_CONFIGS in AIWorkspace.tsx
export type TabId = 'instructions' | 'chatbot' | 'debug' | 'simulator' | 'journeys';

export const TAB_CONFIGS: TabConfig[] = [
  // ... existing tabs
  {
    id: 'journeys',
    label: 'Journeys',
    icon: <GitBranch className="h-4 w-4" />,
    description: 'Manage call processing and operation journeys'
  }
];
```

### 2. JourneysPanel Component

Main container component that manages navigation between list and studio views.

```typescript
interface JourneysPanelProps {
  // Optional initial journey ID to open in studio
  initialJourneyId?: string;
}

interface JourneysPanelState {
  view: 'list' | 'studio';
  selectedJourneyId: string | null;
  filters: JourneyFilter;
}
```

### 3. JourneyListView Component

Displays the list of journeys with filtering and search capabilities.

```typescript
interface JourneyListViewProps {
  onSelectJourney: (journeyId: string) => void;
  onCreateJourney: () => void;
}
```

### 4. JourneyStudioView Component

Detailed journey monitoring and management interface.

```typescript
interface JourneyStudioViewProps {
  journeyId: string;
  onBack: () => void;
}

interface JourneyStudioState {
  journey: CallProcessingJourney | null;
  stages: JourneyStage[];
  currentStageIndex: number;
  stageSteps: Record<string, StageStep[]>;
  jobHistory: JobExecution[];
  isLoading: boolean;
  isPolling: boolean;
}
```

### 5. CreateJourneyDialog Component

Modal dialog for creating new call processing journeys.

```typescript
interface CreateJourneyDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (journey: CallProcessingJourney) => void;
}

interface CreateJourneyFormData {
  name: string;
  minutesBack: number;
  transcribe: boolean;
  registerGlue: boolean;
  runAnalysis: boolean;
  skipProcessed: boolean;
}
```

### 6. StageDetailPanel Component

Displays detailed information about a selected stage.

```typescript
interface StageDetailPanelProps {
  stage: JourneyStage;
  steps: StageStep[];
  jobHistory: JobExecution[];
  onRunJob: () => void;
  onViewLogs: (stepId: string) => void;
}
```

### 7. JobHistoryPanel Component

Displays job execution history with metrics.

```typescript
interface JobHistoryPanelProps {
  jobs: JobExecution[];
  journeyType: JourneyType;
  onSelectJob: (jobId: string) => void;
  sortBy: 'date' | 'status' | 'duration';
  onSortChange: (sortBy: 'date' | 'status' | 'duration') => void;
}
```

### 8. LogsModal Component

Modal for viewing step logs.

```typescript
interface LogsModalProps {
  open: boolean;
  onClose: () => void;
  stepId: string;
  journeyId: string;
  stageId: string;
}
```

## Data Models

### Journey Types

```typescript
// src/types/callProcessingJourney.ts

export type JourneyType = 'call-processing' | 'operation-management';

export type JourneyStatus = 
  | 'created'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface CallProcessingJourney {
  id: string;
  name: string;
  type: JourneyType;
  status: JourneyStatus;
  overallProgress: number;
  currentStageIndex: number;
  
  // Configuration
  config: CallProcessingConfig;
  
  // Timing
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  
  // Metrics
  metrics: JourneyMetrics;
  
  // Stages
  stages: JourneyStage[];
}

export interface CallProcessingConfig {
  minutesBack: number;
  transcribe: boolean;
  registerGlue: boolean;
  runAnalysis: boolean;
  skipProcessed: boolean;
  s3Bucket?: string;
  awsRegion?: string;
}

export interface JourneyMetrics {
  totalJobs: number;
  completedJobs: number;
  failedJobs: number;
  runningJobs: number;
  
  // Call processing specific
  totalCallsFetched: number;
  totalCallsProcessed: number;
  totalCallsAnalyzed: number;
  totalErrors: number;
  totalTranscripts: number;
  
  // Performance
  successRate: number;
  averageJobDuration: number;
  totalExecutionTime: number;
}

export interface JourneyStage {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  order: number;
  
  startTime?: string;
  endTime?: string;
  duration?: string;
  
  jobCount: number;
  completedJobs: number;
  failedJobs: number;
}

export interface StageStep {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  
  startTime?: string;
  endTime?: string;
  duration?: string;
  
  logsCount: number;
  errorMessage?: string;
}

export interface JobExecution {
  id: string;
  journeyId: string;
  stageId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  
  startTime: Date;
  endTime?: Date;
  duration?: string;
  
  // Call processing metrics
  metrics: JobMetrics;
  
  // Report data
  report?: JobReport;
}

export interface JobMetrics {
  tasksFetched: number;
  newTasks: number;
  skippedTasks: number;
  processedSuccessfully: number;
  failed: number;
  transcriptsCollected: number;
  analyzed: number;
}

export interface JobReport {
  executionSummary: {
    tasksFound: number;
    newTasks: number;
    skippedAlreadyProcessed: number;
    processedSuccessfully: number;
    failed: number;
    transcriptsCollected: number;
    analyzed: number;
  };
  glueTableState?: {
    total: number;
    withRecording: number;
    withTranscript: number;
    withAnalysis: number;
  };
  failedTasks?: Array<{
    taskId: string;
    errors: string[];
  }>;
}

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  stepId?: string;
  stageId: string;
  jobId: string;
}
```

### Call Processing Stage Definitions

```typescript
export const CALL_PROCESSING_STAGES: Omit<JourneyStage, 'status' | 'progress' | 'jobCount' | 'completedJobs' | 'failedJobs'>[] = [
  {
    id: 'fetch_tasks',
    name: 'Fetch Tasks',
    description: 'Fetch tasks from Webex CC for configured time period',
    order: 0
  },
  {
    id: 'deduplication',
    name: 'Deduplication Check',
    description: 'Check DynamoDB for already-processed tasks',
    order: 1
  },
  {
    id: 'process_recordings',
    name: 'Process Recordings',
    description: 'Download, transcribe, and upload recordings to S3',
    order: 2
  },
  {
    id: 'register_metadata',
    name: 'Register Metadata',
    description: 'Create metadata JSON and register Glue partitions',
    order: 3
  },
  {
    id: 'ai_analysis',
    name: 'AI Analysis',
    description: 'Run comprehensive GPT analysis on transcripts',
    order: 4
  }
];

export const OPERATION_MANAGEMENT_STAGES: Omit<JourneyStage, 'status' | 'progress' | 'jobCount' | 'completedJobs' | 'failedJobs'>[] = [
  {
    id: 'configuration',
    name: 'Configuration',
    description: 'Configure operation parameters',
    order: 0
  },
  {
    id: 'execution',
    name: 'Execution',
    description: 'Execute the operation',
    order: 1
  },
  {
    id: 'validation',
    name: 'Validation',
    description: 'Validate operation results',
    order: 2
  },
  {
    id: 'completion',
    name: 'Completion',
    description: 'Finalize and report',
    order: 3
  }
];
```

## Service Layer

### CallProcessingJourneyService

```typescript
// src/services/callProcessingJourneyService.ts

class CallProcessingJourneyService {
  private baseUrl: string;
  private cache: Map<string, CallProcessingJourney>;
  
  constructor() {
    this.baseUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
    this.cache = new Map();
  }
  
  // Journey CRUD
  async listJourneys(filter?: JourneyFilter): Promise<CallProcessingJourney[]>;
  async getJourney(journeyId: string): Promise<CallProcessingJourney | null>;
  async createJourney(request: CreateJourneyRequest): Promise<CallProcessingJourney>;
  async deleteJourney(journeyId: string): Promise<boolean>;
  
  // Journey Actions
  async startJourney(journeyId: string): Promise<void>;
  async pauseJourney(journeyId: string): Promise<void>;
  async resumeJourney(journeyId: string): Promise<void>;
  async cancelJourney(journeyId: string): Promise<void>;
  async retryJourney(journeyId: string): Promise<void>;
  
  // Stage Operations
  async getStages(journeyId: string): Promise<JourneyStage[]>;
  async getStageSteps(journeyId: string, stageId: string): Promise<StageStep[]>;
  async runStageJob(journeyId: string, stageId: string): Promise<JobExecution>;
  
  // Job Operations
  async getJobHistory(journeyId: string): Promise<JobExecution[]>;
  async getJobStatus(journeyId: string, jobId: string): Promise<JobExecution>;
  async getJobReport(journeyId: string, jobId: string): Promise<JobReport>;
  
  // Logs
  async getStepLogs(journeyId: string, stageId: string, stepId: string): Promise<LogEntry[]>;
  
  // Health
  async healthCheck(): Promise<boolean>;
}

export const callProcessingJourneyService = new CallProcessingJourneyService();
```

### API Endpoints (Backend Integration)

The service will communicate with nexus-backend via these endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/journeys` | List all journeys |
| GET | `/api/journeys/{id}` | Get journey details |
| POST | `/api/journeys` | Create new journey |
| DELETE | `/api/journeys/{id}` | Delete journey |
| POST | `/api/journeys/{id}/start` | Start journey |
| POST | `/api/journeys/{id}/pause` | Pause journey |
| POST | `/api/journeys/{id}/resume` | Resume journey |
| POST | `/api/journeys/{id}/cancel` | Cancel journey |
| GET | `/api/journeys/{id}/stages` | Get journey stages |
| GET | `/api/journeys/{id}/stages/{stageId}/steps` | Get stage steps |
| POST | `/api/journeys/{id}/stages/{stageId}/run` | Run stage job |
| GET | `/api/journeys/{id}/jobs` | Get job history |
| GET | `/api/journeys/{id}/jobs/{jobId}` | Get job details |
| GET | `/api/journeys/{id}/jobs/{jobId}/report` | Get job report |
| GET | `/api/journeys/{id}/stages/{stageId}/steps/{stepId}/logs` | Get step logs |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: State Preservation on Tab Switch

*For any* JourneysPanel state (selected journey, filters, view mode), switching to another AIWorkspace tab and back should preserve the exact same state.

**Validates: Requirements 1.4**

### Property 2: Journey List Display Completeness

*For any* journey in the system, when rendered in the journey list, the journey card should display all required fields: name, ID, status badge, progress bar, current stage, creation time, and type.

**Validates: Requirements 2.1, 2.5**

### Property 3: Filter Correctness

*For any* combination of search query, status filter, and type filter applied to a journey list:
- If a search query is provided, all displayed journeys should have names containing the query (case-insensitive)
- If a status filter is selected, all displayed journeys should have that exact status
- If a type filter is selected, all displayed journeys should be of that exact type
- The intersection of all filters should be correctly computed

**Validates: Requirements 2.2, 2.3, 2.4**

### Property 4: Stage Status Visual Indicator Correctness

*For any* stage with a given status, the visual indicator should match:
- 'completed' → green indicator
- 'running' → blue indicator  
- 'pending' → gray indicator
- 'failed' → red indicator

**Validates: Requirements 5.5**

### Property 5: Journey Type Determines Stages

*For any* journey, the stages displayed should match the journey type:
- 'call-processing' → [Fetch Tasks, Deduplication Check, Process Recordings, Register Metadata, AI Analysis]
- 'operation-management' → [Configuration, Execution, Validation, Completion]

**Validates: Requirements 5.1, 9.1**

### Property 6: Action Availability by Journey Status

*For any* journey with a given status, the available actions should be:
- 'created' → [start, cancel]
- 'running' → [pause, cancel]
- 'paused' → [resume, cancel]
- 'completed' → []
- 'failed' → [retry]
- 'cancelled' → []

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

### Property 7: Job History Sorting Correctness

*For any* list of jobs and sort criteria:
- Sort by 'date' → jobs ordered by startTime (descending)
- Sort by 'status' → jobs grouped by status in order: running, pending, completed, failed
- Sort by 'duration' → jobs ordered by duration (descending)

**Validates: Requirements 10.5**

### Property 8: Aggregate Statistics Calculation

*For any* set of job executions, the aggregate statistics should be correctly calculated:
- totalCallsProcessed = sum of all jobs' processedSuccessfully
- successRate = (completedJobs / totalJobs) * 100
- averageProcessingTime = sum of all durations / totalJobs

**Validates: Requirements 10.6**

### Property 9: API Payload Correctness for Journey Creation

*For any* valid CreateJourneyFormData, the API request payload should contain all form fields mapped to the correct API field names with correct types.

**Validates: Requirements 3.3, 8.3**

## Error Handling

### Network Errors

| Error Type | Handling Strategy |
|------------|-------------------|
| Backend unavailable | Display connection error toast, show retry button, disable actions |
| Request timeout | Show timeout message, allow retry |
| 401 Unauthorized | Redirect to login, clear session |
| 403 Forbidden | Display permission denied message |
| 404 Not Found | Display "Journey not found" message, navigate to list |
| 500 Server Error | Display generic error with details, log to console |

### Validation Errors

| Error Type | Handling Strategy |
|------------|-------------------|
| Empty journey name | Show inline validation error, disable submit |
| Invalid minutes_back | Show inline validation error (must be positive integer) |
| Duplicate journey name | Show error from backend response |

### State Errors

| Error Type | Handling Strategy |
|------------|-------------------|
| Invalid status transition | Display error message explaining valid transitions |
| Concurrent modification | Refresh journey data, show conflict message |
| Stale data | Auto-refresh on action failure, show stale data warning |

### Error Display Components

```typescript
interface ErrorState {
  hasError: boolean;
  errorType: 'network' | 'validation' | 'state' | 'unknown';
  message: string;
  details?: string;
  retryable: boolean;
  onRetry?: () => void;
}

// Error boundary for journey components
class JourneyErrorBoundary extends React.Component<Props, ErrorState> {
  static getDerivedStateFromError(error: Error): ErrorState;
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void;
  render(): ReactNode;
}
```

## Testing Strategy

### Overview

The testing strategy employs a dual approach combining unit tests for specific examples and edge cases with property-based tests for universal correctness properties. This ensures comprehensive coverage while maintaining test maintainability.

### Testing Framework

- **Unit Testing**: Vitest with React Testing Library
- **Property-Based Testing**: fast-check library for TypeScript
- **Component Testing**: @testing-library/react for UI components
- **API Mocking**: MSW (Mock Service Worker) for backend integration tests

### Unit Tests

Unit tests will cover:

1. **Component Rendering**
   - JourneysPanel renders correctly with initial state
   - JourneyListView displays journey cards
   - JourneyStudioView displays overview dashboard
   - CreateJourneyDialog form validation

2. **User Interactions**
   - Tab switching in AIWorkspace
   - Journey card click navigation
   - Filter and search interactions
   - Action button clicks

3. **Edge Cases**
   - Empty journey list
   - Journey with no stages
   - Network error states
   - Loading states

4. **Integration Points**
   - Service method calls with correct parameters
   - State updates after API responses
   - Polling start/stop behavior

### Property-Based Tests

Each correctness property will be implemented as a property-based test using fast-check:

```typescript
// Example: Property 3 - Filter Correctness
import * as fc from 'fast-check';

describe('Journey Filtering', () => {
  // Feature: call-processing-journeys, Property 3: Filter Correctness
  it('should return only journeys matching all applied filters', () => {
    fc.assert(
      fc.property(
        fc.array(journeyArbitrary),
        fc.option(fc.string()),
        fc.option(journeyStatusArbitrary),
        fc.option(journeyTypeArbitrary),
        (journeys, searchQuery, statusFilter, typeFilter) => {
          const filtered = filterJourneys(journeys, { searchQuery, statusFilter, typeFilter });
          
          return filtered.every(journey => {
            const matchesSearch = !searchQuery || 
              journey.name.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesStatus = !statusFilter || journey.status === statusFilter;
            const matchesType = !typeFilter || journey.type === typeFilter;
            return matchesSearch && matchesStatus && matchesType;
          });
        }
      ),
      { numRuns: 100 }
    );
  });
});
```

### Test Configuration

```typescript
// vitest.config.ts additions
export default defineConfig({
  test: {
    // ... existing config
    testTimeout: 10000, // Allow time for property tests
    coverage: {
      include: ['src/components/journeys/**', 'src/services/callProcessingJourneyService.ts'],
      exclude: ['**/*.test.ts', '**/*.spec.ts']
    }
  }
});
```

### Test File Structure

```
src/
├── components/
│   └── journeys/
│       ├── __tests__/
│       │   ├── JourneysPanel.test.tsx
│       │   ├── JourneyListView.test.tsx
│       │   ├── JourneyStudioView.test.tsx
│       │   ├── CreateJourneyDialog.test.tsx
│       │   └── properties/
│       │       ├── filterCorrectness.property.test.ts
│       │       ├── actionAvailability.property.test.ts
│       │       ├── sortingCorrectness.property.test.ts
│       │       └── aggregateStats.property.test.ts
├── services/
│   └── __tests__/
│       └── callProcessingJourneyService.test.ts
└── types/
    └── __tests__/
        └── callProcessingJourney.test.ts
```

### Arbitraries (Test Data Generators)

```typescript
// src/test/arbitraries/journeyArbitraries.ts
import * as fc from 'fast-check';

export const journeyStatusArbitrary = fc.constantFrom(
  'created', 'running', 'paused', 'completed', 'failed', 'cancelled'
);

export const journeyTypeArbitrary = fc.constantFrom(
  'call-processing', 'operation-management'
);

export const journeyArbitrary = fc.record({
  id: fc.uuid(),
  name: fc.string({ minLength: 1, maxLength: 100 }),
  type: journeyTypeArbitrary,
  status: journeyStatusArbitrary,
  overallProgress: fc.integer({ min: 0, max: 100 }),
  currentStageIndex: fc.integer({ min: 0, max: 4 }),
  createdAt: fc.date(),
  metrics: metricsArbitrary
});

export const jobExecutionArbitrary = fc.record({
  id: fc.uuid(),
  journeyId: fc.uuid(),
  stageId: fc.string(),
  status: fc.constantFrom('pending', 'running', 'completed', 'failed'),
  startTime: fc.date(),
  endTime: fc.option(fc.date()),
  metrics: jobMetricsArbitrary
});
```

### Test Coverage Requirements

- Minimum 80% line coverage for journey components
- 100% coverage for filter and sorting logic
- All 9 correctness properties must have passing property tests
- Integration tests for all API endpoints

