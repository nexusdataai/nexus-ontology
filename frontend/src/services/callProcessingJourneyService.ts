/**
 * Call Processing Journey Service
 * 
 * Service layer for managing call processing journeys.
 * Communicates with nexus-backend via HTTP API endpoints.
 */

import {
  CallProcessingJourney,
  JourneyStage,
  JourneyType,
  JourneyStatus,
  StageStep,
  JobExecution,
  JobReport,
  LogEntry,
  JourneyFilter,
  CreateJourneyRequest,
  JourneyAction,
  AggregateReport,
  createInitialStages,
  createDefaultMetrics
} from '../types/callProcessingJourney';

// ============================================================================
// Backend Response Types
// ============================================================================

interface BackendJourney {
  journeyId: string;
  name: string;
  description?: string;
  status: string;
  odaComponentType?: string;
  solution_id?: string;
  overallProgress?: number;
  createdAt?: string;
  updatedAt?: string;
  stages?: BackendStage[];
  metadata?: Record<string, unknown>;
}

interface BackendStage {
  stageId: string;
  name: string;
  description?: string;
  order: number;
  status?: string;
  progress?: number;
}

// ============================================================================
// Types
// ============================================================================

export interface ServiceError {
  message: string;
  code?: string;
  details?: string;
  retryable: boolean;
}

export interface ServiceResponse<T> {
  data?: T;
  error?: ServiceError;
  success: boolean;
}

// ============================================================================
// Backend to Frontend Mapper
// ============================================================================

function mapBackendJourneyToFrontend(backend: BackendJourney): CallProcessingJourney {
  // Backend can return data in two formats:
  // 1. Flat: { journeyId, name, status, ... } (from list)
  // 2. Nested: { metadata: { journeyId, name, status, ... }, stages, ... } (from get by id)
  const meta = (backend as any).metadata || backend;
  const journeyId = meta.journeyId || backend.journeyId;
  const name = meta.name || backend.name;
  const rawStatus = meta.status || backend.status;
  const odaType = meta.odaComponentType || backend.odaComponentType;
  const solutionId = (meta as any).solution_id || (backend as any).solution_id;
  const createdAt = backend.createdAt || meta.createdAt;
  const updatedAt = backend.updatedAt || meta.updatedAt;
  const overallProgress = meta.overallProgress ?? backend.overallProgress ?? 0;
  
  // Map status - backend uses lowercase, frontend has specific values
  const statusMap: Record<string, JourneyStatus> = {
    'pending': 'created',
    'created': 'created',
    'running': 'running',
    'in_progress': 'running',
    'paused': 'paused',
    'completed': 'completed',
    'done': 'completed',
    'failed': 'failed',
    'error': 'failed',
    'cancelled': 'cancelled',
    'canceled': 'cancelled',
  };
  
  const status: JourneyStatus = statusMap[rawStatus?.toLowerCase()] || 'created';
  
  // Map type - default to call-processing
  const type: JourneyType = odaType === 'OPERATION_MANAGEMENT' 
    ? 'operation-management' 
    : 'call-processing';
  
  // Map stages from backend or create default ones
  const stages: JourneyStage[] = backend.stages?.map((s, index) => ({
    id: s.stageId,
    name: s.name,
    description: s.description || '',
    status: (s.status as 'pending' | 'running' | 'completed' | 'failed') || 'pending',
    progress: s.progress || 0,
    order: s.order ?? index,
    jobCount: 0,
    completedJobs: 0,
    failedJobs: 0,
  })) || createInitialStages(type);
  
  // Calculate current stage index based on status
  let currentStageIndex = 0;
  for (let i = 0; i < stages.length; i++) {
    if (stages[i].status === 'running') {
      currentStageIndex = i;
      break;
    }
    if (stages[i].status === 'completed') {
      currentStageIndex = i;
    }
  }
  
  // Extract job statistics from backend (fallback to 0)
  const totalJobs = (backend as any).totalJobs ?? meta.totalJobs ?? 0;
  const completedJobs = (backend as any).completedJobs ?? meta.completedJobs ?? 0;
  const failedJobs = (backend as any).failedJobs ?? meta.failedJobs ?? 0;
  const runningJobs = totalJobs - completedJobs - failedJobs;
  
  console.log(`📊 Journey metrics for ${name}:`, {
    totalJobs,
    completedJobs,
    failedJobs,
    runningJobs,
    source: totalJobs > 0 ? 'FROM_BACKEND_DATABASE' : 'DEFAULT_ZERO'
  });
  
  return {
    id: journeyId,
    name: name,
    type,
    status,
    overallProgress,
    currentStageIndex,
    solutionId,
    config: {
      minutesBack: 60,
      transcribe: true,
      registerGlue: true,
      runAnalysis: true,
      skipProcessed: true,
    },
    createdAt: createdAt ? new Date(createdAt) : new Date(),
    startedAt: status !== 'created' ? new Date(createdAt || Date.now()) : undefined,
    completedAt: status === 'completed' ? new Date(updatedAt || Date.now()) : undefined,
    metrics: {
      ...createDefaultMetrics(),
      totalJobs,
      completedJobs,
      failedJobs,
      runningJobs: runningJobs > 0 ? runningJobs : 0,
      successRate: totalJobs > 0 ? (completedJobs * 100) / totalJobs : 0,
    },
    stages,
  };
}

// ============================================================================
// Service Class
// ============================================================================

class CallProcessingJourneyService {
  private baseUrl: string = '';  // Empty = use nginx proxy to internal backend service
  private cache: Map<string, CallProcessingJourney>;
  private defaultTimeout: number = 30000;
  private configLoaded: boolean = false;

  constructor() {
    this.cache = new Map();
    this.loadConfig();
  }

  private async loadConfig(): Promise<void> {
    if (this.configLoaded) return;
    try {
      const { getConfig } = await import('./configService');
      const config = await getConfig();
      this.baseUrl = config.api?.baseUrl || import.meta.env.VITE_API_BASE_URL || '';
      this.defaultTimeout = config.api?.timeout || 30000;
      console.log('✅ CallProcessingJourneyService config loaded, baseUrl:', this.baseUrl || '(same origin)');
    } catch (e) {
      this.baseUrl = import.meta.env.VITE_API_BASE_URL || '';
      this.defaultTimeout = parseInt(import.meta.env.VITE_API_TIMEOUT || '30000', 10);
      console.warn('⚠️ Failed to load journey service config, using env defaults');
    }
    this.configLoaded = true;
  }

  private async ensureConfig(): Promise<void> {
    if (!this.configLoaded) {
      await this.loadConfig();
    }
  }

  // ==========================================================================
  // Private Helper Methods
  // ==========================================================================

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ServiceResponse<T>> {
    await this.ensureConfig();
    const url = `${this.baseUrl}${endpoint}`;
    console.log(`🔗 Making request to: ${url}`);
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.defaultTimeout);

      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        credentials: 'include',
        redirect: 'follow',
        cache: 'no-store',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      console.log(`📥 Response status: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error(`❌ Request failed:`, errorData);
        return {
          success: false,
          error: {
            message: errorData.message || `HTTP ${response.status}: ${response.statusText}`,
            code: `HTTP_${response.status}`,
            details: errorData.details,
            retryable: response.status >= 500 || response.status === 429,
          },
        };
      }

      const data = await response.json();
      console.log(`✅ Request succeeded:`, data);
      return { success: true, data };
    } catch (error) {
      console.error(`❌ Request error:`, error);
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          return {
            success: false,
            error: {
              message: 'Request timeout',
              code: 'TIMEOUT',
              retryable: true,
            },
          };
        }
        return {
          success: false,
          error: {
            message: error.message || 'Network error',
            code: 'NETWORK_ERROR',
            retryable: true,
          },
        };
      }
      return {
        success: false,
        error: {
          message: 'Unknown error occurred',
          code: 'UNKNOWN',
          retryable: false,
        },
      };
    }
  }

  // ==========================================================================
  // Journey CRUD Operations
  // ==========================================================================

  /**
   * List all journeys with optional filtering
   */
  async listJourneys(filter?: JourneyFilter): Promise<ServiceResponse<CallProcessingJourney[]>> {
    const params = new URLSearchParams();
    if (filter?.searchQuery) params.append('search', filter.searchQuery);
    if (filter?.statusFilter) params.append('status', filter.statusFilter);
    if (filter?.typeFilter) params.append('type', filter.typeFilter);

    const queryString = params.toString();
    const endpoint = `/api/v1/journeys/${queryString ? `?${queryString}` : ''}`;
    
    console.log('🚀 Calling listJourneys API:', this.baseUrl + endpoint);
    
    // Backend returns paginated response: { success, total, limit, offset, data }
    const response = await this.request<{ success: boolean; total: number; data: BackendJourney[] }>(endpoint);
    
    console.log('📥 listJourneys response:', response);
    
    if (response.success && response.data) {
      // Map backend format to frontend format
      const journeys = (response.data.data || []).map(mapBackendJourneyToFrontend);
      console.log('✅ Mapped journeys:', journeys.length);
      return { success: true, data: journeys };
    }
    
    console.log('❌ listJourneys failed:', response.error);
    return { success: response.success, error: response.error, data: [] };
  }

  /**
   * Get a single journey by ID
   */
  async getJourney(journeyId: string): Promise<ServiceResponse<CallProcessingJourney>> {
    // Check cache first
    const cached = this.cache.get(journeyId);
    if (cached) {
      return { success: true, data: cached };
    }

    const response = await this.request<{ success: boolean; data: BackendJourney }>(`/api/v1/journeys/${journeyId}`);
    
    if (response.success && response.data?.data) {
      const journey = mapBackendJourneyToFrontend(response.data.data);
      this.cache.set(journeyId, journey);
      return { success: true, data: journey };
    }
    
    return { success: false, error: response.error };
  }

  /**
   * Create a new journey
   */
  async createJourney(request: CreateJourneyRequest): Promise<ServiceResponse<CallProcessingJourney>> {
    // Transform frontend request to backend format
    // Backend expects: name, odaComponentType, description, metadata, and stages
    
    // Default stages for call-processing journey (backend requires at least one stage)
    const defaultStages = request.type === 'call-processing' ? [
      { stageId: 'fetch_tasks', name: 'Fetch Tasks', description: 'Fetch tasks from Webex CC', order: 0 },
      { stageId: 'deduplication', name: 'Deduplication Check', description: 'Check for already-processed tasks', order: 1 },
      { stageId: 'process_recordings', name: 'Process Recordings', description: 'Download and transcribe recordings', order: 2 },
      { stageId: 'register_metadata', name: 'Register Metadata', description: 'Create metadata and register in Glue', order: 3 },
      { stageId: 'ai_analysis', name: 'AI Analysis', description: 'Run GPT analysis on transcripts', order: 4 },
      { stageId: 'crm_actions', name: 'CRM Actions', description: 'Create/update Salesforce leads and opportunities', order: 5 },
    ] : [
      { stageId: 'configuration', name: 'Configuration', description: 'Configure operation parameters', order: 0 },
    ];

    // The frontend's `request.type` already names the solution canonically
    // (e.g. 'order-to-cash', 'demand-forecasting'), and matches the backend's
    // KPI catalog keys 1:1; a caller may also pass an explicit `solutionId`
    // override which wins.
    const requestSolutionId = (request as any).solutionId as string | undefined;
    const solutionId = requestSolutionId || request.type;

    const backendPayload = {
      name: request.name,
      odaComponentType: (request as any).odaComponentType
        || (request.type === 'call-processing' ? 'product-management' : 'service-management'),
      solution_id: solutionId,
      description: `Call processing journey with ${request.config.minutesBack} minutes lookback`,
      metadata: {
        config: request.config,
        frontendType: request.type,
        wxcc_mode: request.config.wxccMode || 'inherit_global',
      },
      stages: (request as any).stages || defaultStages,
    };

    const response = await this.request<{ success: boolean; journey_id: string; data: BackendJourney }>('/api/v1/journeys/', {
      method: 'POST',
      body: JSON.stringify(backendPayload),
    });

    if (response.success && response.data?.data) {
      const journey = mapBackendJourneyToFrontend(response.data.data);
      return { success: true, data: journey };
    }

    return { success: false, error: response.error };
  }

  /**
   * Delete a journey
   */
  async deleteJourney(journeyId: string): Promise<ServiceResponse<boolean>> {
    const response = await this.request<{ success: boolean }>(`/api/v1/journeys/${journeyId}`, {
      method: 'DELETE',
    });

    if (response.success) {
      this.cache.delete(journeyId);
    }

    return { ...response, data: response.success };
  }

  // ==========================================================================
  // Journey Action Operations
  // ==========================================================================

  /**
   * Perform an action on a journey
   */
  private async performAction(
    journeyId: string,
    action: JourneyAction
  ): Promise<ServiceResponse<CallProcessingJourney>> {
    const response = await this.request<BackendJourney>(
      `/api/v1/journeys/${journeyId}/${action}`,
      { method: 'POST' }
    );

    if (response.success && response.data) {
      const journey = mapBackendJourneyToFrontend(response.data);
      this.cache.set(journeyId, journey);
      return { success: true, data: journey };
    }

    return { success: false, error: response.error };
  }

  /**
   * Start a journey
   */
  async startJourney(journeyId: string): Promise<ServiceResponse<CallProcessingJourney>> {
    return this.performAction(journeyId, 'start');
  }

  /**
   * Pause a journey
   */
  async pauseJourney(journeyId: string): Promise<ServiceResponse<CallProcessingJourney>> {
    return this.performAction(journeyId, 'pause');
  }

  /**
   * Resume a journey
   */
  async resumeJourney(journeyId: string): Promise<ServiceResponse<CallProcessingJourney>> {
    return this.performAction(journeyId, 'resume');
  }

  /**
   * Cancel a journey
   */
  async cancelJourney(journeyId: string): Promise<ServiceResponse<CallProcessingJourney>> {
    return this.performAction(journeyId, 'cancel');
  }

  /**
   * Retry a failed journey
   */
  async retryJourney(journeyId: string): Promise<ServiceResponse<CallProcessingJourney>> {
    return this.performAction(journeyId, 'retry');
  }

  // ==========================================================================
  // Stage Operations
  // ==========================================================================

  /**
   * Get all stages for a journey
   */
  async getStages(journeyId: string): Promise<ServiceResponse<JourneyStage[]>> {
    const response = await this.request<{ success: boolean; stages: BackendStage[] }>(`/api/v1/journeys/${journeyId}/stages`);
    
    if (response.success && response.data?.stages) {
      const stages: JourneyStage[] = response.data.stages.map((s, index) => ({
        id: s.stageId,
        name: s.name,
        description: s.description || '',
        status: (s.status as 'pending' | 'running' | 'completed' | 'failed') || 'pending',
        progress: s.progress || 0,
        order: s.order ?? index,
        jobCount: 0,
        completedJobs: 0,
        failedJobs: 0,
      }));
      return { success: true, data: stages };
    }
    
    return { success: true, data: [] };
  }

  /**
   * Get steps for a specific stage
   */
  async getStageSteps(journeyId: string, stageId: string): Promise<ServiceResponse<StageStep[]>> {
    return this.request<StageStep[]>(`/api/v1/journeys/${journeyId}/stages/${stageId}/steps`);
  }

  /**
   * Run a job for a specific stage
   */
  async runStageJob(journeyId: string, stageId: string): Promise<ServiceResponse<JobExecution>> {
    // Use the correct backend endpoint: POST /jobs?stage_id=<stageId>
    return this.request<JobExecution>(`/api/v1/journeys/${journeyId}/jobs?stage_id=${stageId}&triggered_by=ui`, {
      method: 'POST',
    });
  }

  // ==========================================================================
  // Job Operations
  // ==========================================================================

  /**
   * Get job history for a journey
   */
  async getJobHistory(journeyId: string): Promise<ServiceResponse<JobExecution[]>> {
    const response = await this.request<{ success: boolean; jobs: any[] }>(`/api/v1/journeys/${journeyId}/jobs`);
    
    if (response.success && response.data?.jobs) {
      const jobs: JobExecution[] = response.data.jobs.map(j => ({
        id: j.jobId,
        jobId: j.jobId,
        stageId: j.stageId,
        stageName: j.stageName || j.stageId,
        status: j.status || 'pending',
        progress: j.progress || 0,
        startedAt: j.startTime ? new Date(j.startTime) : (j.startedAt ? new Date(j.startedAt) : undefined),
        startTime: j.startTime,
        completedAt: j.endTime ? new Date(j.endTime) : (j.completedAt ? new Date(j.completedAt) : undefined),
        endTime: j.endTime,
        duration: j.duration,
        triggeredBy: j.triggeredBy || 'api',
        itemsProcessed: j.itemsProcessed || 0,
        itemsTotal: j.itemsTotal || 0,
        errorCount: j.errorCount || 0,
        metrics: j.metrics || {},
        stepResults: j.stepResults || {},
      }));
      return { success: true, data: jobs };
    }
    
    return { success: true, data: [] };
  }

  /**
   * Get status of a specific job
   */
  async getJobStatus(journeyId: string, jobId: string): Promise<ServiceResponse<JobExecution>> {
    return this.request<JobExecution>(`/api/v1/journeys/${journeyId}/jobs/${jobId}/status`);
  }

  async cancelJob(journeyId: string, jobId: string): Promise<ServiceResponse<any>> {
    return this.request<any>(`/api/v1/journeys/${journeyId}/jobs/${jobId}/cancel`, { method: 'POST' });
  }

  /**
   * Get report for a specific job
   */
  async getJobReport(journeyId: string, jobId: string): Promise<ServiceResponse<JobReport>> {
    return this.request<JobReport>(`/api/v1/journeys/${journeyId}/jobs/${jobId}/report`);
  }

  async getAggregateReport(journeyId: string): Promise<ServiceResponse<AggregateReport>> {
    const response = await this.request<{ success: boolean; data: AggregateReport }>(
      `/api/v1/journeys/${journeyId}/aggregate-report`
    );
    if (response.success && response.data?.data) {
      return { success: true, data: response.data.data };
    }
    return { success: false, error: { message: 'Failed to load report', retryable: true } };
  }

  // ==========================================================================
  // Log Operations
  // ==========================================================================

  /**
   * Get logs for a specific step (legacy stage-based)
   */
  async getStepLogs(
    journeyId: string,
    stageId: string,
    stepId: string
  ): Promise<ServiceResponse<LogEntry[]>> {
    return this.request<LogEntry[]>(
      `/api/v1/journeys/${journeyId}/stages/${stageId}/steps/${stepId}/logs`
    );
  }

  /**
   * Get logs for a specific job
   * @param journeyId Journey ID
   * @param jobId Job ID
   * @param stepName Optional step name to filter logs
   * @param limit Max number of logs to return
   */
  async getJobLogs(
    journeyId: string,
    jobId: string,
    stepName?: string,
    limit: number = 500
  ): Promise<ServiceResponse<any>> {
    let endpoint = `/api/v1/journeys/${journeyId}/jobs/${jobId}/logs?limit=${limit}`;
    if (stepName) {
      endpoint += `&step_name=${encodeURIComponent(stepName)}`;
    }
    return this.request<any>(endpoint);
  }

  // ==========================================================================
  // Batch Schedule Operations
  // ==========================================================================

  async listSchedules(journeyId?: string): Promise<ServiceResponse<any[]>> {
    const params = journeyId ? `?journey_id=${encodeURIComponent(journeyId)}` : '';
    const response = await this.request<{ success: boolean; data: any[]; total: number }>(`/api/v1/schedules/${params}`);
    if (response.success && response.data) {
      return { success: true, data: response.data.data || [] };
    }
    return response as ServiceResponse<any[]>;
  }

  async getSchedule(scheduleId: string): Promise<ServiceResponse<any>> {
    const response = await this.request<{ success: boolean; data: any }>(`/api/v1/schedules/${scheduleId}`);
    if (response.success && response.data) {
      return { success: true, data: response.data.data };
    }
    return response as ServiceResponse<any>;
  }

  async createSchedule(config: {
    journey_id: string;
    stage_id: string;
    interval_minutes: number;
    enabled?: boolean;
    timezone?: string;
  }): Promise<ServiceResponse<any>> {
    const response = await this.request<{ success: boolean; data: any }>('/api/v1/schedules/', {
      method: 'POST',
      body: JSON.stringify(config),
    });
    if (response.success && response.data) {
      return { success: true, data: response.data.data };
    }
    return response as ServiceResponse<any>;
  }

  async updateSchedule(scheduleId: string, config: {
    interval_minutes?: number;
    enabled?: boolean;
    timezone?: string;
  }): Promise<ServiceResponse<any>> {
    const response = await this.request<{ success: boolean; data: any }>(`/api/v1/schedules/${scheduleId}`, {
      method: 'PUT',
      body: JSON.stringify(config),
    });
    if (response.success && response.data) {
      return { success: true, data: response.data.data };
    }
    return response as ServiceResponse<any>;
  }

  async deleteSchedule(scheduleId: string): Promise<ServiceResponse<any>> {
    return this.request<any>(`/api/v1/schedules/${scheduleId}`, { method: 'DELETE' });
  }

  async toggleSchedule(scheduleId: string): Promise<ServiceResponse<any>> {
    const response = await this.request<{ success: boolean; data: any }>(`/api/v1/schedules/${scheduleId}/toggle`, {
      method: 'POST',
    });
    if (response.success && response.data) {
      return { success: true, data: response.data.data };
    }
    return response as ServiceResponse<any>;
  }

  async resetSchedule(scheduleId: string): Promise<ServiceResponse<any>> {
    const response = await this.request<{ success: boolean; data: any }>(`/api/v1/schedules/${scheduleId}/reset`, {
      method: 'POST',
    });
    if (response.success && response.data) {
      return { success: true, data: response.data.data };
    }
    return response as ServiceResponse<any>;
  }

  async runScheduleNow(scheduleId: string): Promise<ServiceResponse<any>> {
    const response = await this.request<{ success: boolean; data: any }>(`/api/v1/schedules/${scheduleId}/run-now`, {
      method: 'POST',
    });
    if (response.success && response.data) {
      return { success: true, data: response.data.data };
    }
    return response as ServiceResponse<any>;
  }

  // ==========================================================================
  // Health Check
  // ==========================================================================

  /**
   * Check if the backend is available
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.request<{ status: string }>('/api/v1/health');
      return response.success;
    } catch {
      return false;
    }
  }

  // ==========================================================================
  // Cache Management
  // ==========================================================================

  /**
   * Clear the journey cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Invalidate a specific journey in the cache
   */
  invalidateJourney(journeyId: string): void {
    this.cache.delete(journeyId);
  }
}

// ============================================================================
// Singleton Export
// ============================================================================

export const callProcessingJourneyService = new CallProcessingJourneyService();

// ============================================================================
// Demo Data Generator (for development/testing)
// ============================================================================

export function createDemoJourney(
  id: string,
  name: string,
  type: 'call-processing' | 'operation-management' = 'call-processing',
  status: 'created' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled' = 'created'
): CallProcessingJourney {
  const stages = createInitialStages(type);
  
  // Update stage statuses based on journey status
  if (status === 'running') {
    stages[0].status = 'completed';
    stages[0].progress = 100;
    stages[1].status = 'running';
    stages[1].progress = 50;
  } else if (status === 'completed') {
    stages.forEach(stage => {
      stage.status = 'completed';
      stage.progress = 100;
    });
  } else if (status === 'failed') {
    stages[0].status = 'completed';
    stages[0].progress = 100;
    stages[1].status = 'failed';
    stages[1].progress = 30;
  }

  return {
    id,
    name,
    type,
    status,
    overallProgress: status === 'completed' ? 100 : status === 'running' ? 35 : 0,
    currentStageIndex: status === 'running' ? 1 : status === 'completed' ? stages.length - 1 : 0,
    config: {
      minutesBack: 60,
      transcribe: true,
      registerGlue: true,
      runAnalysis: true,
      skipProcessed: true,
    },
    createdAt: new Date(),
    startedAt: status !== 'created' ? new Date() : undefined,
    completedAt: status === 'completed' ? new Date() : undefined,
    metrics: {
      ...createDefaultMetrics(),
      totalJobs: status === 'completed' ? 5 : status === 'running' ? 2 : 0,
      completedJobs: status === 'completed' ? 5 : status === 'running' ? 1 : 0,
      totalCallsFetched: status === 'completed' ? 150 : status === 'running' ? 50 : 0,
      totalCallsProcessed: status === 'completed' ? 145 : status === 'running' ? 25 : 0,
      successRate: status === 'completed' ? 96.7 : status === 'running' ? 100 : 0,
    },
    stages,
  };
}

export default callProcessingJourneyService;
