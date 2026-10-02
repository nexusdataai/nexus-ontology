/**
 * TMF ODA HTTP API Service
 * 
 * This service communicates with the TMF ODA transformer service
 * to fetch real journey data and transformation information.
 */

import { TransformationJourney, JourneySummary, JourneyStatus, JourneyPriority, TransformationType } from '@/types/transformationJourney';

// Types for API responses
interface ApiJourneyResponse {
  operation: string;
  status: string;
  timestamp: string;
  duration_seconds: number;
  data_source: string;
  summary: {
    total_journeys: number;
    status_distribution: Record<string, number>;
    active_journeys: number;
    completed_journeys: number;
    failed_journeys: number;
  };
  journeys: Array<{
    journeyId: string;
    name: string;
    status: string;
    createdAt: string | null;
    currentStage: string;
    progress: string;
  }>;
  message: string;
}

interface ApiJobResponse {
  status: string;
  job_id: string;
  journey_id: string;
  stage_id: string;
  triggered_by: string;
  reason: string;
  start_time: string;
  end_time: string;
  duration_seconds: number;
  message: string;
}

class TmfOdaHttpService {
  private readonly baseUrl = 'http://18.191.87.212:8000';
  private readonly timeout = 30000; // 30 seconds timeout

  constructor() {
    // Test connection on startup
    this.testConnection();
  }

  /**
   * Test initial connection to the service
   */
  private async testConnection(): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ TMF ODA HTTP Service: Connected successfully');
        console.log(`📋 Service: ${data.service}`);
        console.log(`🔧 Tools Available: ${data.tools_count}`);
      } else {
        console.warn('⚠️ TMF ODA HTTP Service: Connection issues');
      }
    } catch (error) {
      console.error('❌ TMF ODA HTTP Service: Connection failed', error);
    }
  }

  /**
   * Fetch journey information using the journeys tool
   */
  async fetchJourneys(journeyId?: string): Promise<any> {
    try {
      const url = `${this.baseUrl}/tools/journeys`;
      const payload: any = {
        include_stages: true,
        include_job_history: true,
        job_limit: 10
      };
      
      if (journeyId) {
        payload.journey_id = journeyId;
      }
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      // The actual result is in result.result
      return result.result || result;
    } catch (error) {
      console.error('Error fetching journeys:', error);
      throw error;
    }
  }

  /**
   * Legacy method for backward compatibility
   */
  async fetchJourneyInfo(journeyId?: string): Promise<ApiJourneyResponse> {
    return this.fetchJourneys(journeyId);
  }

  /**
   * Execute a transformation stage
   */
  async executeStage(stageId: string, journeyId: string): Promise<ApiJobResponse> {
    try {
      const url = `${this.baseUrl}/tools/run-jobs`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stage_id: stageId,
          journey_id: journeyId,
          triggered_by: 'ui-user',
          reason: 'User initiated from UI'
        }),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.result || result;
    } catch (error) {
      console.error('Error executing stage:', error);
      throw error;
    }
  }

  /**
   * Get logs for a specific journey/stage/step using logs-and-reports tool
   */
  async getJobLogs(journeyId: string, stageId: string, stepId?: string, jobId?: string): Promise<any> {
    try {
      const url = `${this.baseUrl}/tools/logs-and-reports`;
      const payload: any = {
        action: "get_job_logs",
        journey_id: journeyId,
        stage_name: stageId
      };
      
      if (stepId) {
        payload.step_name = stepId;
      }
      
      if (jobId) {
        payload.job_id = jobId;
      } else {
        // Generate a default job ID pattern
        payload.job_id = `JOB-001-${Date.now().toString().slice(-8)}`;
      }
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.result || result;
    } catch (error) {
      console.error('Error fetching job logs:', error);
      throw error;
    }
  }

  /**
   * Map API journey status to UI journey status
   */
  private mapApiStatusToUiStatus(apiStatus: string): JourneyStatus {
    switch (apiStatus.toLowerCase()) {
      case 'pending':
        return 'created';
      case 'running':
        return 'running';
      case 'paused':
        return 'paused';
      case 'completed':
        return 'completed';
      case 'failed':
        return 'failed';
      case 'cancelled':
        return 'cancelled';
      default:
        return 'created';
    }
  }

  /**
   * Map API stage name to UI stage name
   */
  private mapApiStageToUiStage(apiStage: string): string {
    switch (apiStage.toLowerCase()) {
      case 'raw_analysis':
        return 'Raw Input Analysis';
      case 'stripped_schema':
        return 'Create Stripped Schema';
      case 'tmf_mapping':
        return 'TMF Schema Mapping';
      case 'data_migration_planning':
        return 'Data Migration Planning';
      case 'data_migration_execution':
        return 'Data Migration Execution';
      case 'verification':
        return 'Verification & Validation';
      default:
        return apiStage;
    }
  }

  /**
   * Create meaningful journey name from API data
   */
  private createMeaningfulJourneyName(apiName: string, journeyId: string): string {
    // If API provides a meaningful name (not just "12345" or similar), use it
    if (apiName && apiName !== '12345' && !(/^\d+$/.test(apiName)) && apiName.length > 5) {
      return apiName;
    }
    
    // Extract meaningful part from journey ID if possible
    const idParts = journeyId.split('-');
    if (idParts.length >= 2) {
      const idSuffix = idParts[idParts.length - 1].slice(0, 6); // First 6 chars of last part
      return `Customer Transformation ${idSuffix}`;
    }
    
    // Create name based on journey ID pattern
    if (journeyId.includes('1FCF2C')) {
      return 'MTN SA Customer Management Transformation';
    } else if (journeyId.includes('04064FAC')) {
      return 'Product Catalog Management Transformation';
    } else if (journeyId.includes('09CFE55C')) {
      return 'Billing Management Transformation';
    } else if (journeyId.includes('DE2F72678E')) {
      return 'Order Management Transformation';
    }
    
    // Default meaningful name
    const shortId = journeyId.slice(-6);
    return `TMF ODA Transformation ${shortId}`;
  }

  /**
   * Get customer name based on journey ID pattern
   */
  private getCustomerNameFromJourneyId(journeyId: string): string {
    if (journeyId.includes('1FCF2C')) {
      return 'MTN South Africa';
    } else if (journeyId.includes('04064FAC')) {
      return 'Telco Product Solutions';
    } else if (journeyId.includes('09CFE55C')) {
      return 'Billing Systems Corp';
    } else if (journeyId.includes('DE2F72678E')) {
      return 'Order Management Solutions';
    }
    
    return 'Enterprise Customer';
  }

  /**
   * Convert API journey data to UI journey summary format
   */
  private convertApiJourneyToUiSummary(apiJourney: any): JourneySummary {
    // Create meaningful journey name
    const journeyName = this.createMeaningfulJourneyName(apiJourney.name, apiJourney.journeyId);
    
    return {
      id: apiJourney.journeyId,
      name: journeyName,
      status: this.mapApiStatusToUiStatus(apiJourney.status),
      source: {
        type: 'schema-based' as TransformationType,
        schemaName: journeyName,
        schemaVersion: '1.0.0'
      },
      currentStage: this.mapApiStageToUiStage(apiJourney.currentStage),
      overallProgress: parseInt(apiJourney.progress) || 0,
      createdAt: apiJourney.createdAt ? new Date(apiJourney.createdAt) : new Date(),
      priority: 'medium' as JourneyPriority,
      customerName: this.getCustomerNameFromJourneyId(apiJourney.journeyId)
    };
  }

  /**
   * Convert API journey data to full transformation journey format
   */
  private convertApiJourneyToFullJourney(apiJourney: any): TransformationJourney {
    const now = new Date();
    const createdAt = apiJourney.createdAt ? new Date(apiJourney.createdAt) : now;
    
    // Create meaningful journey name
    const journeyName = this.createMeaningfulJourneyName(apiJourney.name, apiJourney.journeyId);
    
    return {
      id: apiJourney.journeyId,
      name: journeyName,
      description: `Transformation journey for ${journeyName}`,
      status: this.mapApiStatusToUiStatus(apiJourney.status),
      priority: 'medium' as JourneyPriority,
      source: {
        type: 'schema-based' as TransformationType,
        schemaName: journeyName,
        schemaVersion: '1.0.0'
      },
      configuration: {
        timeout: 300,
        maxDepth: 3,
        includeDocumentation: true,
        includeExamples: true,
        validateEndpoints: true,
        generateMigrationScripts: true,
        performDataSampling: true,
        tmfSpecVersion: '1.0.0',
        outputFormat: 'json',
        retryAttempts: 3,
        notificationSettings: {
          emailOnCompletion: false,
          emailOnError: false
        }
      },
      stages: this.createDefaultStages(apiJourney.currentStage),
      currentStageIndex: this.getCurrentStageIndex(apiJourney.currentStage),
      overallProgress: parseInt(apiJourney.progress) || 0,
      metrics: {
        totalTables: 0,
        processedTables: 0,
        totalRelationships: 0,
        processedRelationships: 0,
        totalEndpoints: 0,
        processedEndpoints: 0
      },
      timing: {
        createdAt: createdAt,
        startedAt: createdAt,
      },
      ownership: {
        createdBy: 'system',
        assignedTo: 'current-user'
      },
      metadata: {
        version: 1,
        lastUpdated: now,
        tags: ['tmf-oda', 'transformation'],
        customerName: this.getCustomerNameFromJourneyId(apiJourney.journeyId),
        projectCode: 'TMF-001',
        environmentType: 'development'
      },
      history: []
    };
  }

  /**
   * Create default stages for a journey
   */
  private createDefaultStages(currentStage: string) {
    const stages = [
      {
        id: 'raw_analysis',
        name: 'Raw Input Analysis',
        status: 'created' as JourneyStatus,
        progress: 0,
        totalSteps: 5,
        completedSteps: 0,
        logs: [],
        canSkip: false,
        requiresApproval: false
      },
      {
        id: 'stripped_schema',
        name: 'Create Stripped Schema',
        status: 'created' as JourneyStatus,
        progress: 0,
        totalSteps: 3,
        completedSteps: 0,
        logs: [],
        canSkip: false,
        requiresApproval: true
      },
      {
        id: 'tmf_mapping',
        name: 'TMF Schema Mapping',
        status: 'created' as JourneyStatus,
        progress: 0,
        totalSteps: 4,
        completedSteps: 0,
        logs: [],
        canSkip: false,
        requiresApproval: true
      },
      {
        id: 'data_migration_planning',
        name: 'Data Migration Planning',
        status: 'created' as JourneyStatus,
        progress: 0,
        totalSteps: 6,
        completedSteps: 0,
        logs: [],
        canSkip: true,
        requiresApproval: true
      },
      {
        id: 'data_migration_execution',
        name: 'Data Migration Execution',
        status: 'created' as JourneyStatus,
        progress: 0,
        totalSteps: 8,
        completedSteps: 0,
        logs: [],
        canSkip: true,
        requiresApproval: true
      },
      {
        id: 'verification',
        name: 'Verification & Validation',
        status: 'created' as JourneyStatus,
        progress: 0,
        totalSteps: 4,
        completedSteps: 0,
        logs: [],
        canSkip: false,
        requiresApproval: false
      }
    ];

    // Update stage statuses based on current stage
    const currentStageIndex = this.getCurrentStageIndex(currentStage);
    for (let i = 0; i < stages.length; i++) {
      if (i < currentStageIndex) {
        stages[i].status = 'completed';
        stages[i].progress = 100;
        stages[i].completedSteps = stages[i].totalSteps;
      } else if (i === currentStageIndex) {
        stages[i].status = 'running';
        stages[i].progress = 50; // Assume 50% progress for current stage
      }
    }

    return stages;
  }

  /**
   * Get current stage index based on stage name
   */
  private getCurrentStageIndex(stageName: string): number {
    const stageMap: Record<string, number> = {
      'raw_analysis': 0,
      'stripped_schema': 1,
      'tmf_mapping': 2,
      'data_migration_planning': 3,
      'data_migration_execution': 4,
      'verification': 5
    };

    return stageMap[stageName.toLowerCase()] || 0;
  }

  /**
   * Get journey summaries from the API
   */
  async getJourneySummaries(): Promise<JourneySummary[]> {
    try {
      const apiResponse = await this.fetchJourneyInfo();
      return apiResponse.journeys.map(journey => this.convertApiJourneyToUiSummary(journey));
    } catch (error) {
      console.error('Error fetching journey summaries:', error);
      // Return empty array on error - UI will handle gracefully
      return [];
    }
  }

  /**
   * Get full journey details by ID
   */
  async getJourneyById(journeyId: string): Promise<TransformationJourney | null> {
    try {
      const apiResponse = await this.fetchJourneyInfo(journeyId);
      const journey = apiResponse.journeys.find(j => j.journeyId === journeyId);
      
      if (!journey) {
        return null;
      }

      return this.convertApiJourneyToFullJourney(journey);
    } catch (error) {
      console.error('Error fetching journey by ID:', error);
      return null;
    }
  }

  /**
   * Get journey statistics
   */
  async getJourneyStatistics(): Promise<any> {
    try {
      const apiResponse = await this.fetchJourneyInfo();
      
      return {
        totalJourneys: apiResponse.summary.total_journeys,
        runningJourneys: apiResponse.summary.status_distribution.running || 0,
        pausedJourneys: apiResponse.summary.status_distribution.paused || 0,
        completedJourneys: apiResponse.summary.completed_journeys,
        failedJourneys: apiResponse.summary.failed_journeys,
        averageCompletionTime: '2 hours' // Default value
      };
    } catch (error) {
      console.error('Error fetching journey statistics:', error);
      return {
        totalJourneys: 0,
        runningJourneys: 0,
        pausedJourneys: 0,
        completedJourneys: 0,
        failedJourneys: 0,
        averageCompletionTime: '0 hours'
      };
    }
  }

  /**
   * Health check for the TMF ODA service
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000), // 5 second timeout for health check
      });
      
      return response.ok;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  /**
   * Get available tools from the service
   */
  async getAvailableTools(): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/tools`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching available tools:', error);
      throw error;
    }
  }

  /**
   * Get stages for a specific journey
   */
  async getJourneyStages(journeyId: string): Promise<any> {
    try {
      const url = `${this.baseUrl}/tools/journeys`;
      const payload = {
        action: "list_stages",
        journey_id: journeyId
      };
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.result || result;
    } catch (error) {
      console.error('Error fetching journey stages:', error);
      throw error;
    }
  }

  /**
   * Get jobs for a specific stage
   */
  async getStageJobs(journeyId: string, stageId: string): Promise<any> {
    try {
      const url = `${this.baseUrl}/tools/journeys`;
      const payload = {
        action: "read",
        journey_id: journeyId,
        include_job_history: true,
        include_stages: true,
        limit: 100
      };
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('🔍 Raw API response for stage jobs:', result);
      console.log('🔍 Response type:', typeof result);
      console.log('🔍 Response keys:', Object.keys(result || {}));
      console.log('🔍 Looking for stage:', stageId);
      console.log('🔍 stage_job_summary exists:', !!result?.stage_job_summary);
      console.log('🔍 Available stages in stage_job_summary:', result?.stage_job_summary ? Object.keys(result.stage_job_summary) : 'none');
      
      // Deep inspection of the response structure
      if (result?.stage_job_summary) {
        console.log('✅ stage_job_summary found:', result.stage_job_summary);
      } else {
        console.log('❌ stage_job_summary NOT found. Full response structure:');
        console.log('   - status:', result?.status);
        console.log('   - message:', result?.message);
        console.log('   - operation:', result?.operation);
        console.log('   - journey_status exists:', !!result?.journey_status);
        console.log('   - stages exists:', !!result?.stages);
        console.log('   - summary exists:', !!result?.summary);
      }
      
      // If requesting all stages, return the full response
      if (stageId === 'all') {
        console.log('📊 Returning full stage job summary for all stages');
        return result;
      }
      
      // The real job data is in stage_job_summary section
      let jobs = [];
      
      if (result?.stage_job_summary?.[stageId]) {
        const stageData = result.stage_job_summary[stageId];
        const totalJobs = parseInt(stageData.total_jobs || '0');
        const recentJobs = stageData.recent_jobs || [];
        
        console.log(`📊 Stage ${stageId}: ${totalJobs} total jobs, ${recentJobs.length} recent jobs shown`);
        
        // Map the real API response to expected format
        jobs = recentJobs.map((job: any, index: number) => ({
          job_id: job.jobId || job.job_id,
          stage_id: stageId,
          name: `${stageId.replace('_', ' ').toUpperCase()} Execution #${job.executionNumber || (index + 1)}`,
          status: job.status || 'completed',
          progress: parseInt(job.progress || '100'),
          start_time: job.startTime || job.start_time,
          end_time: job.endTime || job.end_time,
          duration: job.duration,
          error_message: job.error_message || job.errorMessage,
          step_count: 5, // Default step count
          completed_steps: job.status === 'completed' ? 5 : (job.status === 'running' ? 3 : 0),
          created_at: job.startTime || job.start_time,
          triggered_by: job.triggered_by || job.triggeredBy || 'user',
          reason: job.reason || 'Job execution',
          execution_number: job.executionNumber || job.execution_number,
          logs_available: true,
          reports_available: true
        }));
        
        console.log(`✅ Found ${jobs.length} recent jobs for stage ${stageId} (out of ${totalJobs} total)`);
        
        // Add total_jobs info to response
        return { 
          jobs,
          total_jobs: totalJobs,
          showing_recent: jobs.length
        };
      }
      
      // Fallback to other possible response formats
      if (result?.jobs && Array.isArray(result.jobs)) {
        return { jobs: result.jobs };
      } else if (result?.result?.jobs && Array.isArray(result.result.jobs)) {
        return { jobs: result.result.jobs };
      } else if (result?.stage_details?.jobs && Array.isArray(result.stage_details.jobs)) {
        return { jobs: result.stage_details.jobs };
      } else if (Array.isArray(result)) {
        return { jobs: result };
      }
      
      console.log(`⚠️ No jobs found in API response for stage ${stageId}, will fall back to mock data`);
      return { jobs: [] };
      
    } catch (error) {
      console.error('Error fetching stage jobs:', error);
      throw error;
    }
  }

  /**
   * Get dashboard data for a journey
   */
  async getJourneyDashboard(journeyId: string): Promise<any> {
    try {
      const url = `${this.baseUrl}/tools/journeys`;
      const payload = {
        action: "dashboard",
        journey_id: journeyId
      };
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.result || result;
    } catch (error) {
      console.error('Error fetching journey dashboard:', error);
      throw error;
    }
  }

  /**
   * Get journey summary
   */
  async getJourneySummary(journeyId: string): Promise<any> {
    try {
      const url = `${this.baseUrl}/tools/journeys`;
      const payload = {
        action: "get_journey_summary",
        journey_id: journeyId
      };
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.result || result;
    } catch (error) {
      console.error('Error fetching journey summary:', error);
      throw error;
    }
  }

  /**
   * Run a job for a specific stage
   */
  async runStageJob(journeyId: string, stageId: string, triggeredBy: string = 'ui-user'): Promise<any> {
    try {
      const url = `${this.baseUrl}/tools/journeys`;
      const payload = {
        action: "run_job",
        journey_id: journeyId,
        stage_id: stageId,
        triggered_by: triggeredBy
      };
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.result || result;
    } catch (error) {
      console.error('Error running stage job:', error);
      throw error;
    }
  }

  /**
   * Get job metrics for a specific job
   */
  async getJobMetrics(journeyId: string, jobId: string): Promise<any> {
    try {
      const url = `${this.baseUrl}/tools/journeys`;
      const payload = {
        action: "get_job_metrics",
        journey_id: journeyId,
        job_id: jobId
      };
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.result || result;
    } catch (error) {
      console.error('Error fetching job metrics:', error);
      throw error;
    }
  }

  /**
   * Search logs with filters using logs-and-reports tool
   */
  async searchLogs(journeyId: string, searchQuery?: string, logLevel?: string): Promise<any> {
    try {
      const url = `${this.baseUrl}/tools/logs-and-reports`;
      const payload: any = {
        action: "search_logs",
        journey_id: journeyId
      };
      
      if (searchQuery) {
        payload.search_query = searchQuery;
      }
      
      if (logLevel) {
        payload.level_filter = logLevel;
      }
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.result || result;
    } catch (error) {
      console.error('Error searching logs:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const tmfOdaHttpService = new TmfOdaHttpService(); 