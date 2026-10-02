/**
 * Transformation Journey Management Types
 * 
 * This module defines the data structures for managing long-running
 * transformation journeys that can span weeks or months.
 */

export type JourneyStatus = 
  | 'created'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type JourneyPriority = 'low' | 'medium' | 'high' | 'urgent';

export type TransformationType = 'schema-based' | 'database-analysis';

export interface JourneyStage {
  id: string;
  name: string;
  status: JourneyStatus;
  startTime?: Date;
  endTime?: Date;
  duration?: string;
  progress: number; // 0-100
  currentStep?: string;
  totalSteps: number;
  completedSteps: number;
  logs: JourneyLog[];
  canSkip: boolean;
  requiresApproval: boolean;
  approvedBy?: string;
  approvedAt?: Date;
  errorMessage?: string;
  artifacts?: JourneyArtifact[];
}

export interface JourneyLog {
  id: string;
  timestamp: Date;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  details?: any;
  stageId: string;
  stepId?: string;
}

export interface JourneyArtifact {
  id: string;
  type: 'report' | 'schema' | 'mapping' | 'script' | 'log' | 'config';
  name: string;
  description: string;
  filePath?: string;
  size?: number;
  createdAt: Date;
  downloadUrl?: string;
}

export interface JourneySource {
  type: TransformationType;
  // For schema-based transformations
  schemaId?: string;
  schemaName?: string;
  schemaVersion?: string;
  // For database-analysis transformations
  databaseId?: string;
  databaseName?: string;
  databaseType?: string;
  connectionString?: string;
}

export interface JourneyConfiguration {
  timeout: number;
  maxDepth: number;
  includeDocumentation: boolean;
  includeExamples: boolean;
  validateEndpoints: boolean;
  generateMigrationScripts: boolean;
  performDataSampling: boolean;
  tmfSpecVersion: string;
  outputFormat: 'json' | 'xml' | 'yaml';
  // Additional configuration options
  retryAttempts: number;
  notificationSettings: {
    emailOnCompletion: boolean;
    emailOnError: boolean;
    slackWebhook?: string;
  };
}

export interface JourneyMetrics {
  totalTables: number;
  processedTables: number;
  totalRelationships: number;
  processedRelationships: number;
  totalEndpoints: number;
  processedEndpoints: number;
  estimatedTimeRemaining?: string;
  averageProcessingRate?: number; // tables per hour
  peakMemoryUsage?: number;
  totalCpuTime?: number;
}

export interface TransformationJourney {
  /** Unique journey identifier */
  id: string;
  
  /** Human-readable journey name */
  name: string;
  
  /** Journey description */
  description: string;
  
  /** Current journey status */
  status: JourneyStatus;
  
  /** Journey priority level */
  priority: JourneyPriority;
  
  /** Transformation source (schema or database) */
  source: JourneySource;
  
  /** Journey configuration */
  configuration: JourneyConfiguration;
  
  /** All stages in this transformation */
  stages: JourneyStage[];
  
  /** Current active stage index */
  currentStageIndex: number;
  
  /** Overall journey progress (0-100) */
  overallProgress: number;
  
  /** Journey metrics and statistics */
  metrics: JourneyMetrics;
  
  /** Journey timing information */
  timing: {
    createdAt: Date;
    startedAt?: Date;
    pausedAt?: Date;
    resumedAt?: Date;
    completedAt?: Date;
    estimatedCompletionAt?: Date;
    totalDuration?: string;
  };
  
  /** Journey ownership and permissions */
  ownership: {
    createdBy: string;
    assignedTo?: string;
    team?: string;
    department?: string;
  };
  
  /** Journey metadata */
  metadata: {
    version: number;
    lastUpdated: Date;
    tags: string[];
    customerName?: string;
    projectCode?: string;
    budgetCode?: string;
    environmentType: 'development' | 'staging' | 'production';
  };
  
  /** Journey dependencies */
  dependencies?: {
    dependsOn: string[]; // Other journey IDs
    blockedBy: string[]; // Issues blocking this journey
    blocks: string[]; // Journeys this one is blocking
  };
  
  /** Resume information */
  resumeInfo?: {
    canResume: boolean;
    resumeFromStage: string;
    resumeNotes?: string;
    lastCheckpoint?: Date;
    stateSnapshot?: any;
  };
  
  /** Journey history and audit trail */
  history: JourneyHistoryEntry[];
}

export interface JourneyHistoryEntry {
  id: string;
  timestamp: Date;
  action: 'created' | 'started' | 'paused' | 'resumed' | 'completed' | 'failed' | 'cancelled' | 'stage-completed' | 'configuration-updated';
  performedBy: string;
  details: string;
  oldValue?: any;
  newValue?: any;
}

export interface JourneySummary {
  id: string;
  name: string;
  status: JourneyStatus;
  source: JourneySource;
  currentStage: string;
  overallProgress: number;
  createdAt: Date;
  estimatedCompletion?: Date;
  priority: JourneyPriority;
  customerName?: string;
}

export interface JourneyFilter {
  status?: JourneyStatus[];
  priority?: JourneyPriority[];
  transformationType?: TransformationType[];
  createdBy?: string;
  assignedTo?: string;
  customerName?: string;
  dateRange?: {
    start: Date;
    end: Date;
  };
  tags?: string[];
}

export interface JourneySearchResult {
  journeys: JourneySummary[];
  totalCount: number;
  filteredCount: number;
  facets: {
    statusCounts: Record<JourneyStatus, number>;
    priorityCounts: Record<JourneyPriority, number>;
    typeCounts: Record<TransformationType, number>;
  };
}

// Utility types for journey operations
export interface CreateJourneyRequest {
  name: string;
  description: string;
  priority: JourneyPriority;
  source: JourneySource;
  configuration: JourneyConfiguration;
  metadata: {
    tags: string[];
    customerName?: string;
    projectCode?: string;
    environmentType: 'development' | 'staging' | 'production';
  };
}

export interface UpdateJourneyRequest {
  id: string;
  name?: string;
  description?: string;
  priority?: JourneyPriority;
  assignedTo?: string;
  tags?: string[];
  version: number; // For optimistic locking
}

export interface JourneyActionRequest {
  id: string;
  action: 'start' | 'pause' | 'resume' | 'cancel' | 'retry';
  reason?: string;
  options?: any;
} 