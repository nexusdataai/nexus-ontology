/**
 * Call Processing Journey Types
 * 
 * This module defines the data structures for managing call processing
 * journeys that process Webex Contact Center calls through analytics pipelines.
 */

// ============================================================================
// Core Types
// ============================================================================

export type JourneyType = 'call-processing' | 'operation-management' | 'semantic-rag' | 'order-to-cash' | 'demand-forecasting' | 'inventory-optimization' | 'procurement-analytics' | 'production-quality' | 'supply-chain-risk' | 'customer-360' | 'esg-sustainability';

export type JourneyStatus = 
  | 'created'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type StageStatus = 'pending' | 'running' | 'completed' | 'failed';

export type LogLevel = 'info' | 'warning' | 'error' | 'debug';

export type SortOption = 'date' | 'status' | 'duration';

// ============================================================================
// Configuration Types
// ============================================================================

export interface CallProcessingConfig {
  minutesBack: number;
  transcribe: boolean;
  registerGlue: boolean;
  runAnalysis: boolean;
  skipProcessed: boolean;
  s3Bucket?: string;
  awsRegion?: string;
  wxccMode?: 'simulator' | 'real' | 'inherit_global';
}

// ============================================================================
// Metrics Types
// ============================================================================

export interface JourneyMetrics {
  totalJobs: number;
  completedJobs: number;
  failedJobs: number;
  runningJobs: number;
  pendingJobs: number;
  
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
  errorRate: number;
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

// ============================================================================
// Stage Types
// ============================================================================

export interface JourneyStage {
  id: string;
  name: string;
  description: string;
  status: StageStatus;
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
  status: StageStatus;
  progress: number;
  
  startTime?: string;
  endTime?: string;
  duration?: string;
  
  logsCount: number;
  errorMessage?: string;
}

// ============================================================================
// Job Types
// ============================================================================

export interface JobExecution {
  id: string;
  jobId?: string;  // Full job ID for API calls
  job_id?: string; // Raw backend rows may still carry the snake_case id
  journeyId?: string; // Not set by the job-history mapper in callProcessingJourneyService
  stageId: string;
  status: StageStatus;
  
  startTime: Date;
  endTime?: Date;
  duration?: string;
  
  // Call processing metrics
  metrics: JobMetrics;

  // Item counters the job service maps from the backend row
  itemsProcessed?: number;
  itemsTotal?: number;

  // Report data
  report?: JobReport;

  // Phase-2 (React Tool Improvement): when the JourneyExecutorBridge
  // pauses a Copilot saved-journey run on awaiting_step_approval, it
  // stashes the pending-step payload on the JobExecution row so the
  // studio's status poll can render an inline PendingStepCard. The
  // bridge clears this back to null on resume / reject.
  pending_step?: any;
  pendingStep?: any;
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

// ============================================================================
// Log Types
// ============================================================================

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  stepId?: string;
  // Optional: entries built from SSE log events carry no stage or job id.
  stageId?: string;
  jobId?: string;
}

// ============================================================================
// Main Journey Type
// ============================================================================

export interface CallProcessingJourney {
  id: string;
  name: string;
  type: JourneyType;
  status: JourneyStatus;
  overallProgress: number;
  currentStageIndex: number;
  
  // Canonical solution this journey belongs to (drives Studio KPI labels via journeyKpiCatalog).
  // Optional because older rows may not have it yet (backfill script handles those).
  solutionId?: string;
  
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

// ============================================================================
// Filter Types
// ============================================================================

export interface JourneyFilter {
  searchQuery?: string;
  statusFilter?: JourneyStatus;
  typeFilter?: JourneyType;
}

// ============================================================================
// Request/Response Types
// ============================================================================

export interface CreateJourneyStageRequest {
  stageId: string;
  name: string;
  order: number;
  description?: string;
  steps?: unknown[];
}

export interface CreateJourneyRequest {
  name: string;
  type: JourneyType;
  // Call-processing journeys send the full CallProcessingConfig; solution
  // journeys (O2C, semantic RAG, ...) send their own keys or an empty object.
  config: Partial<CallProcessingConfig> & { [key: string]: unknown };
  // Optional overrides the service forwards to the backend when present.
  odaComponentType?: string;
  stages?: CreateJourneyStageRequest[];
  solutionId?: string;
}

export interface CreateJourneyFormData {
  name: string;
  minutesBack: number;
  transcribe: boolean;
  registerGlue: boolean;
  runAnalysis: boolean;
  skipProcessed: boolean;
  wxccMode?: 'simulator' | 'real' | 'inherit_global';
}

// ============================================================================
// Action Types
// ============================================================================

export type JourneyAction = 'start' | 'pause' | 'resume' | 'cancel' | 'retry';

// ============================================================================
// Stage Constants
// ============================================================================

export interface StageDefinition {
  id: string;
  name: string;
  description: string;
  order: number;
}

export const CALL_PROCESSING_STAGES: StageDefinition[] = [
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
  },
  {
    id: 'crm_actions',
    name: 'CRM Actions',
    description: 'Create/update Salesforce leads and opportunities',
    order: 5
  }
];

export const OPERATION_MANAGEMENT_STAGES: StageDefinition[] = [
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

export const SEMANTIC_RAG_STAGES: StageDefinition[] = [
  { id: 'extract_unified_schema', name: 'Extract Unified Schema', description: 'Read canonical-entities.yaml into virtual entity docs', order: 0 },
  { id: 'resolve_fdw_mapping', name: 'Resolve FDW Mapping', description: 'Match schema entities to live FDW + simulator tables', order: 1 },
  { id: 'extract_mapping_rules', name: 'Extract Mapping Rules', description: 'Read active mapping rules and enrich schema docs', order: 2 },
  { id: 'extract_policies', name: 'Extract Policies', description: 'Parse business policy documents', order: 3 },
  { id: 'extract_workflows', name: 'Extract Workflows', description: 'Parse workflow definitions', order: 4 },
  { id: 'extract_integrations', name: 'Extract Integrations', description: 'Parse integration mappings', order: 5 },
  { id: 'normalize', name: 'Normalize (.onto)', description: 'Merge, deduplicate, produce .onto bundle', order: 6 },
  { id: 'enrich', name: 'LLM Enrichment', description: 'Generate semantic descriptions with LLM', order: 7 },
  { id: 'chunk_embed', name: 'Chunk & Embed', description: 'Semantic chunking + embedding generation', order: 8 },
  { id: 'load_vector', name: 'Load Vector DB', description: 'Upsert embeddings into pgvector', order: 9 },
  { id: 'index_nlq_exemplars', name: 'Index NLQ Exemplars', description: 'Generate NLP query exemplars from curated YAML + canonical schema templates and index for AI Query Builder', order: 10 },
  { id: 'load_graph', name: 'Load Graph DB', description: 'Load relationships into graph DB', order: 11 },
  { id: 'validate', name: 'Validate Quality', description: 'Run black-box test scenarios', order: 12 },
];

// ============================================================================
// Aggregate Report Types
// ============================================================================

// ---------------------------------------------------------------------------
// Journey-specific report envelope (Phase 3 / React-Tool-improvement plan)
// ---------------------------------------------------------------------------
//
// The backend report builder reads
// ``enterprise-knowledge/report-schemas/{solution_id}.yaml`` and returns
// a schema-driven envelope so the same React modal can render any
// journey type. The legacy ``AggregateReport`` interface stays defined
// below for any callers that still consume the old call-processing
// shape, but the modal (now JourneyReportModal) reads ``JourneyReport``.

export interface ReportKpiValue {
  key: string;
  label: string;
  icon?: string;
  format: 'percent' | 'integer' | 'duration' | 'currency' | 'decimal' | 'text' | string;
  value: number | string | null;
  status?: 'ok' | 'warn' | 'critical' | null;
}

export interface ReportSectionKpiGrid {
  id: string;
  title: string;
  kind: 'kpi_grid';
  description?: string | null;
  kpis: ReportKpiValue[];
}

export interface ReportSectionTable {
  id: string;
  title: string;
  kind: 'table';
  description?: string | null;
  columns: { key: string; label: string; format: string }[];
  rows: Array<Record<string, any>>;
}

export interface ReportSectionDistribution {
  id: string;
  title: string;
  kind: 'distribution';
  description?: string | null;
  buckets: { label: string; count: number; percentage: number }[];
  total: number;
}

export interface ReportSectionAlertsList {
  id: string;
  title: string;
  kind: 'alerts_list';
  description?: string | null;
  alerts: Array<Record<string, any>>;
  groups: { key: string; label: string; count: number }[];
}

export interface ReportSectionTimeline {
  id: string;
  title: string;
  kind: 'timeline';
  description?: string | null;
  events: Array<{
    fromState?: string;
    toState?: string;
    timestamp?: string;
    stepId?: string | null;
    reason?: string | null;
  }>;
}

export interface ReportSectionStepBreakdown {
  id: string;
  title: string;
  kind: 'step_breakdown';
  description?: string | null;
  steps: Array<{
    step_id: string;
    name: string;
    tool?: string | null;
    completed: number;
    failed: number;
    pending: number;
    other: number;
    total: number;
  }>;
}

export type ReportSection =
  | ReportSectionKpiGrid
  | ReportSectionTable
  | ReportSectionDistribution
  | ReportSectionAlertsList
  | ReportSectionTimeline
  | ReportSectionStepBreakdown
  | { id: string; title: string; kind: string; description?: string | null; [k: string]: any };

export interface JourneyReport {
  schema_version: string;
  journey_id: string;
  journey_title: string;
  solution_id?: string | null;
  title: string;
  icon?: string | null;
  summary_kpis: ReportKpiValue[];
  sections: ReportSection[];
  total_jobs: number;
  generated_at: string;
}


export interface AggregateReport {
  summary: {
    totalCalls: number;
    processedCalls: number;
    transcribedCalls: number;
    analyzedCalls: number;
    successCount: number;
    failedCount: number;
    noRecordingCount: number;
    skippedCount: number;
    successRate: number;
    avgProcessingTime: string;
    totalJobs: number;
  };
  processingPerformance: {
    avgProcessingTime: string;
    throughput: string;
    errorRate: string;
    stepAvgDurations: Record<string, string>;
  };
  grading: {
    avgScore: number;
    passRate: number;
    totalAnalyzed: number;
    passCount: number;
    elementScores: Record<string, number>;
  };
  callDistribution: Array<{
    callType: string;
    count: number;
    percentage: number;
    avgDuration: string;
  }>;
  sentimentBreakdown: Array<{
    label: string;
    value: number;
    percentage: number;
  }>;
  analysisFileCount: number;
  generatedAt: string;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get stages for a given journey type
 */
export function getStagesForJourneyType(type: JourneyType): StageDefinition[] {
  switch (type) {
    case 'call-processing': return CALL_PROCESSING_STAGES;
    case 'semantic-rag': return SEMANTIC_RAG_STAGES;
    default: return OPERATION_MANAGEMENT_STAGES;
  }
}

/**
 * Create initial stages for a journey
 */
export function createInitialStages(type: JourneyType): JourneyStage[] {
  const stageDefinitions = getStagesForJourneyType(type);
  return stageDefinitions.map(def => ({
    ...def,
    status: 'pending' as StageStatus,
    progress: 0,
    jobCount: 0,
    completedJobs: 0,
    failedJobs: 0
  }));
}

/**
 * Create default metrics
 */
export function createDefaultMetrics(): JourneyMetrics {
  return {
    totalJobs: 0,
    completedJobs: 0,
    failedJobs: 0,
    runningJobs: 0,
    pendingJobs: 0,
    totalCallsFetched: 0,
    totalCallsProcessed: 0,
    totalCallsAnalyzed: 0,
    totalErrors: 0,
    totalTranscripts: 0,
    successRate: 0,
    averageJobDuration: 0,
    totalExecutionTime: 0,
    errorRate: 0
  };
}
