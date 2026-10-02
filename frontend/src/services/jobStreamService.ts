/**
 * Job Stream Service - SSE client for real-time job progress updates
 * 
 * This service connects to the backend SSE endpoint to receive real-time
 * updates about job progress, including:
 * - Step status changes (running, completed, failed)
 * - Real-time log entries from step execution
 * - Individual task processing progress
 * - Job completion notifications
 */

import { LogEntry } from '../types/callProcessingJourney';

// SSE Event Types
export type SSEEventType = 'step_status' | 'log' | 'task_progress' | 'job_complete' | 'error';

// Event Data Types
export interface StepStatusEvent {
  step_id: string;
  // Note: backend may send 'in_progress' which should be treated as 'running'
  status: 'pending' | 'running' | 'in_progress' | 'completed' | 'failed';
  step_index: number;
  progress: number;
  message?: string;
  timestamp: string;
}

export interface LogEvent {
  step_id: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
}

export interface TaskProgressEvent {
  step_id: string;
  task_id: string;
  current: number;
  total: number;
  percentage: number;
  status: 'processing' | 'completed' | 'failed';
  timestamp: string;
}

export interface JobCompleteEvent {
  status: 'completed' | 'failed';
  duration: number;
  metrics: {
    itemsProcessed: number;
    itemsTotal: number;
  };
  timestamp: string;
}

export interface ErrorEvent {
  message: string;
  timestamp: string;
}

// Event Handlers
export interface JobStreamHandlers {
  onStepStatus?: (data: StepStatusEvent) => void;
  onLog?: (data: LogEvent) => void;
  onTaskProgress?: (data: TaskProgressEvent) => void;
  onJobComplete?: (data: JobCompleteEvent) => void;
  onError?: (error: Error) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
}

// Connection State
export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

// Config loading (same pattern as other services)
interface ServiceConfig {
  baseUrl: string;
  timeout: number;
}

const DEFAULT_API_URL = '';  // Empty = use nginx proxy to internal backend service
let cachedConfig: ServiceConfig | null = null;

async function loadConfig(): Promise<ServiceConfig> {
  if (cachedConfig) {
    return cachedConfig;
  }

  try {
    const response = await fetch('/config.json', {
      cache: 'no-store',
      headers: { 'Accept': 'application/json' }
    });

    if (response.ok) {
      const config = await response.json();
      cachedConfig = {
        baseUrl: config.api?.baseUrl || DEFAULT_API_URL,
        timeout: config.api?.timeout || 30000
      };
      return cachedConfig;
    }
  } catch (error) {
    console.warn('⚠️ Error loading config.json for job stream:', error);
  }

  return {
    baseUrl: import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_URL || DEFAULT_API_URL,
    timeout: 30000
  };
}

/**
 * JobStreamService - Manages SSE connections for real-time job updates
 * 
 * Usage:
 * ```typescript
 * const stream = new JobStreamService();
 * stream.connect('JRN-123', 'JOB-456', {
 *   onStepStatus: (data) => console.log('Step update:', data),
 *   onLog: (data) => console.log('Log:', data),
 *   onTaskProgress: (data) => console.log('Task progress:', data),
 *   onJobComplete: (data) => console.log('Job complete:', data),
 *   onError: (error) => console.error('Error:', error),
 * });
 * 
 * // Later...
 * stream.disconnect();
 * ```
 */
class JobStreamService {
  private eventSource: EventSource | null = null;
  private baseUrl: string = DEFAULT_API_URL;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 2000;
  private currentJobId: string | null = null;
  private currentJourneyId: string | null = null;
  private handlers: JobStreamHandlers = {};
  private connectionState: ConnectionState = 'disconnected';
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private configLoaded: boolean = false;

  constructor() {
    // Load config asynchronously
    this.initConfig();
  }

  private async initConfig(): Promise<void> {
    const config = await loadConfig();
    this.baseUrl = config.baseUrl;
    this.configLoaded = true;
  }

  private async ensureConfigLoaded(): Promise<void> {
    if (!this.configLoaded) {
      await this.initConfig();
    }
  }

  /**
   * Get the current connection state
   */
  getConnectionState(): ConnectionState {
    return this.connectionState;
  }

  /**
   * Check if currently connected
   */
  isConnected(): boolean {
    return this.connectionState === 'connected' && this.eventSource !== null;
  }

  /**
   * Connect to the SSE stream for a specific job
   */
  connect(journeyId: string, jobId: string, handlers: JobStreamHandlers): void {
    // Disconnect any existing connection
    this.disconnect();

    this.currentJourneyId = journeyId;
    this.currentJobId = jobId;
    this.handlers = handlers;
    this.reconnectAttempts = 0;

    // Ensure config is loaded before connecting
    this.ensureConfigLoaded().then(() => {
      this.establishConnection();
    });
  }

  /**
   * Establish the SSE connection
   */
  private establishConnection(): void {
    if (!this.currentJourneyId || !this.currentJobId) {
      console.error('Cannot establish connection without journeyId and jobId');
      return;
    }

    const url = `${this.baseUrl}/api/v1/journeys/${this.currentJourneyId}/jobs/${this.currentJobId}/stream`;
    console.log(`📡 Connecting to SSE stream: ${url}`);

    this.connectionState = 'connecting';

    try {
      this.eventSource = new EventSource(url);

      // Connection opened
      this.eventSource.onopen = () => {
        console.log(`✅ SSE stream connected for job ${this.currentJobId}`);
        this.connectionState = 'connected';
        this.reconnectAttempts = 0;
        this.handlers.onConnected?.();
      };

      // Handle step_status events
      this.eventSource.addEventListener('step_status', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as StepStatusEvent;
          console.log('📊 Step status:', data);
          this.handlers.onStepStatus?.(data);
        } catch (e) {
          console.error('Error parsing step_status event:', e);
        }
      });

      // Handle log events
      this.eventSource.addEventListener('log', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as LogEvent;
          console.log('📝 Log:', data.level, data.message);
          this.handlers.onLog?.(data);
        } catch (e) {
          console.error('Error parsing log event:', e);
        }
      });

      // Handle task_progress events
      this.eventSource.addEventListener('task_progress', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as TaskProgressEvent;
          console.log('📈 Task progress:', data);
          this.handlers.onTaskProgress?.(data);
        } catch (e) {
          console.error('Error parsing task_progress event:', e);
        }
      });

      // Handle job_complete events
      this.eventSource.addEventListener('job_complete', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as JobCompleteEvent;
          console.log('🎉 Job complete:', data);
          this.handlers.onJobComplete?.(data);
          // Auto-disconnect on job completion
          this.disconnect();
        } catch (e) {
          console.error('Error parsing job_complete event:', e);
        }
      });

      // Handle error events
      this.eventSource.addEventListener('error', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as ErrorEvent;
          console.error('❌ SSE error event:', data);
          this.handlers.onError?.(new Error(data.message));
        } catch (e) {
          // Ignore parse errors for error events
        }
      });

      // Handle connection errors
      this.eventSource.onerror = (error) => {
        console.error('❌ SSE connection error:', error);
        this.connectionState = 'error';

        // Check if EventSource is closed
        if (this.eventSource?.readyState === EventSource.CLOSED) {
          console.log('SSE connection closed, attempting reconnect...');
          this.attemptReconnect();
        }
      };

    } catch (error) {
      console.error('Failed to create EventSource:', error);
      this.connectionState = 'error';
      this.handlers.onError?.(error instanceof Error ? error : new Error('Failed to connect'));
    }
  }

  /**
   * Attempt to reconnect after a connection failure
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached, falling back to polling');
      this.handlers.onError?.(new Error('Max reconnect attempts reached'));
      this.disconnect();
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`🔄 Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);

    this.reconnectTimeout = setTimeout(() => {
      this.establishConnection();
    }, delay);
  }

  /**
   * Disconnect from the SSE stream
   */
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.eventSource) {
      console.log(`📡 Disconnecting SSE stream for job ${this.currentJobId}`);
      this.eventSource.close();
      this.eventSource = null;
    }

    this.connectionState = 'disconnected';
    this.currentJobId = null;
    this.currentJourneyId = null;
    this.handlers.onDisconnected?.();
  }

  /**
   * Update event handlers (useful for updating callbacks without reconnecting)
   */
  updateHandlers(handlers: Partial<JobStreamHandlers>): void {
    this.handlers = { ...this.handlers, ...handlers };
  }
}

// Singleton instance
export const jobStreamService = new JobStreamService();

// Export class for testing or creating multiple instances
export { JobStreamService };

// Helper function to convert LogEvent to LogEntry format
export function logEventToLogEntry(event: LogEvent): LogEntry {
  return {
    timestamp: event.timestamp,
    level: event.level,
    message: event.message,
  };
}
