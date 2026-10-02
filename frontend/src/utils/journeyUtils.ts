/**
 * Journey Utility Functions
 * 
 * Utility functions for filtering, sorting, and calculating statistics
 * for call processing journeys.
 */

import {
  CallProcessingJourney,
  JobExecution,
  JourneyFilter,
  JourneyStatus,
  JourneyAction,
  SortOption,
  StageStatus
} from '../types/callProcessingJourney';

// ============================================================================
// Filter Functions
// ============================================================================

/**
 * Filter journeys based on search query, status, and type filters
 * 
 * Property 3: Filter Correctness
 * - If a search query is provided, all displayed journeys should have names containing the query (case-insensitive)
 * - If a status filter is selected, all displayed journeys should have that exact status
 * - If a type filter is selected, all displayed journeys should be of that exact type
 * - The intersection of all filters should be correctly computed
 */
export function filterJourneys(
  journeys: CallProcessingJourney[],
  filter: JourneyFilter
): CallProcessingJourney[] {
  return journeys.filter(journey => {
    // Search query filter (case-insensitive)
    if (filter.searchQuery) {
      const query = filter.searchQuery.toLowerCase();
      if (!journey.name.toLowerCase().includes(query)) {
        return false;
      }
    }

    // Status filter
    if (filter.statusFilter) {
      if (journey.status !== filter.statusFilter) {
        return false;
      }
    }

    // Type filter
    if (filter.typeFilter) {
      if (journey.type !== filter.typeFilter) {
        return false;
      }
    }

    return true;
  });
}

// ============================================================================
// Sort Functions
// ============================================================================

/**
 * Sort jobs based on the specified criteria
 * 
 * Property 7: Job History Sorting Correctness
 * - Sort by 'date' → jobs ordered by startTime (descending)
 * - Sort by 'status' → jobs grouped by status in order: running, pending, completed, failed
 * - Sort by 'duration' → jobs ordered by duration (descending)
 */
export function sortJobs(
  jobs: JobExecution[],
  sortBy: SortOption
): JobExecution[] {
  const sortedJobs = [...jobs];

  switch (sortBy) {
    case 'date':
      // Sort by startTime descending (most recent first)
      return sortedJobs.sort((a, b) => {
        const dateA = new Date(a.startTime).getTime();
        const dateB = new Date(b.startTime).getTime();
        return dateB - dateA;
      });

    case 'status':
      // Sort by status priority: running > pending > completed > failed
      const statusOrder: Record<StageStatus, number> = {
        running: 0,
        pending: 1,
        completed: 2,
        failed: 3,
      };
      return sortedJobs.sort((a, b) => {
        return statusOrder[a.status] - statusOrder[b.status];
      });

    case 'duration':
      // Sort by duration descending (longest first)
      return sortedJobs.sort((a, b) => {
        const durationA = parseDuration(a.duration);
        const durationB = parseDuration(b.duration);
        return durationB - durationA;
      });

    default:
      return sortedJobs;
  }
}

/**
 * Parse duration string to milliseconds
 * Supports formats: "1h 30m", "45m", "30s", "1h 30m 45s"
 */
export function parseDuration(duration?: string): number {
  if (!duration) return 0;

  let totalMs = 0;
  
  // Match hours
  const hoursMatch = duration.match(/(\d+)h/);
  if (hoursMatch) {
    totalMs += parseInt(hoursMatch[1], 10) * 60 * 60 * 1000;
  }

  // Match minutes
  const minutesMatch = duration.match(/(\d+)m/);
  if (minutesMatch) {
    totalMs += parseInt(minutesMatch[1], 10) * 60 * 1000;
  }

  // Match seconds
  const secondsMatch = duration.match(/(\d+)s/);
  if (secondsMatch) {
    totalMs += parseInt(secondsMatch[1], 10) * 1000;
  }

  return totalMs;
}

/**
 * Format milliseconds to duration string
 */
export function formatDuration(ms: number): string {
  if (ms <= 0) return '0s';

  const hours = Math.floor(ms / (60 * 60 * 1000));
  const minutes = Math.floor((ms % (60 * 60 * 1000)) / (60 * 1000));
  const seconds = Math.floor((ms % (60 * 1000)) / 1000);

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (seconds > 0 || parts.length === 0) parts.push(`${seconds}s`);

  return parts.join(' ');
}

// ============================================================================
// Statistics Functions
// ============================================================================

/**
 * Aggregate statistics for a set of job executions
 * 
 * Property 8: Aggregate Statistics Calculation
 * - totalCallsProcessed = sum of all jobs' processedSuccessfully
 * - successRate = (completedJobs / totalJobs) * 100
 * - averageProcessingTime = sum of all durations / totalJobs
 */
export interface AggregateStats {
  totalJobs: number;
  completedJobs: number;
  failedJobs: number;
  runningJobs: number;
  pendingJobs: number;
  totalCallsProcessed: number;
  totalCallsFetched: number;
  totalTranscripts: number;
  totalAnalyzed: number;
  totalErrors: number;
  successRate: number;
  averageProcessingTime: number;
  totalProcessingTime: number;
}

export function calculateAggregateStats(jobs: JobExecution[]): AggregateStats {
  if (jobs.length === 0) {
    return {
      totalJobs: 0,
      completedJobs: 0,
      failedJobs: 0,
      runningJobs: 0,
      pendingJobs: 0,
      totalCallsProcessed: 0,
      totalCallsFetched: 0,
      totalTranscripts: 0,
      totalAnalyzed: 0,
      totalErrors: 0,
      successRate: 0,
      averageProcessingTime: 0,
      totalProcessingTime: 0,
    };
  }

  const stats = jobs.reduce(
    (acc, job) => {
      // Count by status
      acc.totalJobs++;
      if (job.status === 'completed') acc.completedJobs++;
      if (job.status === 'failed') acc.failedJobs++;
      if (job.status === 'running') acc.runningJobs++;
      if (job.status === 'pending') acc.pendingJobs++;

      // Sum metrics
      acc.totalCallsProcessed += job.metrics.processedSuccessfully;
      acc.totalCallsFetched += job.metrics.tasksFetched;
      acc.totalTranscripts += job.metrics.transcriptsCollected;
      acc.totalAnalyzed += job.metrics.analyzed;
      acc.totalErrors += job.metrics.failed;

      // Sum duration
      acc.totalProcessingTime += parseDuration(job.duration);

      return acc;
    },
    {
      totalJobs: 0,
      completedJobs: 0,
      failedJobs: 0,
      runningJobs: 0,
      pendingJobs: 0,
      totalCallsProcessed: 0,
      totalCallsFetched: 0,
      totalTranscripts: 0,
      totalAnalyzed: 0,
      totalErrors: 0,
      totalProcessingTime: 0,
    }
  );

  // Calculate derived metrics
  const successRate = stats.totalJobs > 0
    ? (stats.completedJobs / stats.totalJobs) * 100
    : 0;

  const averageProcessingTime = stats.totalJobs > 0
    ? stats.totalProcessingTime / stats.totalJobs
    : 0;

  return {
    ...stats,
    successRate,
    averageProcessingTime,
  };
}

// ============================================================================
// Action Availability Functions
// ============================================================================

/**
 * Get available actions for a journey based on its status
 * 
 * Property 6: Action Availability by Journey Status
 * - 'created' → [start, cancel]
 * - 'running' → [pause, cancel]
 * - 'paused' → [resume, cancel]
 * - 'completed' → []
 * - 'failed' → [retry]
 * - 'cancelled' → []
 */
export function getAvailableActions(status: JourneyStatus): JourneyAction[] {
  switch (status) {
    case 'created':
      return ['start', 'cancel'];
    case 'running':
      return ['pause', 'cancel'];
    case 'paused':
      return ['resume', 'cancel'];
    case 'completed':
      return [];
    case 'failed':
      return ['retry'];
    case 'cancelled':
      return [];
    default:
      return [];
  }
}

/**
 * Check if a specific action is available for a journey status
 */
export function isActionAvailable(status: JourneyStatus, action: JourneyAction): boolean {
  return getAvailableActions(status).includes(action);
}

// ============================================================================
// Status Color Functions
// ============================================================================

/**
 * Get the color class for a stage status
 * 
 * Property 4: Stage Status Visual Indicator Correctness
 * - 'completed' → green indicator
 * - 'running' → blue indicator
 * - 'pending' → gray indicator
 * - 'failed' → red indicator
 */
export function getStageStatusColor(status: StageStatus): string {
  switch (status) {
    case 'completed':
      return 'text-green-500 bg-green-100';
    case 'running':
      return 'text-blue-500 bg-blue-100';
    case 'pending':
      return 'text-gray-500 bg-gray-100';
    case 'failed':
      return 'text-red-500 bg-red-100';
    default:
      return 'text-gray-500 bg-gray-100';
  }
}

/**
 * Get the border color class for a stage status
 */
export function getStageStatusBorderColor(status: StageStatus): string {
  switch (status) {
    case 'completed':
      return 'border-green-500';
    case 'running':
      return 'border-blue-500';
    case 'pending':
      return 'border-gray-300';
    case 'failed':
      return 'border-red-500';
    default:
      return 'border-gray-300';
  }
}

/**
 * Get the color class for a journey status badge
 */
export function getJourneyStatusColor(status: JourneyStatus): string {
  switch (status) {
    case 'created':
      return 'bg-gray-100 text-gray-800';
    case 'running':
      return 'bg-blue-100 text-blue-800';
    case 'paused':
      return 'bg-yellow-100 text-yellow-800';
    case 'completed':
      return 'bg-green-100 text-green-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    case 'cancelled':
      return 'bg-gray-100 text-gray-600';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

// ============================================================================
// Date/Time Formatting
// ============================================================================

/**
 * Format a date for display
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a date with time for display
 */
export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(d);
}
