/**
 * Property-Based Tests for Journey Utility Functions
 * 
 * Feature: call-processing-journeys
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import {
  filterJourneys,
  sortJobs,
  calculateAggregateStats,
  getAvailableActions,
  parseDuration,
} from '../journeyUtils';
import {
  CallProcessingJourney,
  JobExecution,
  JourneyStatus,
  JourneyType,
  JourneyAction,
  StageStatus,
} from '../../types/callProcessingJourney';

// Arbitraries (Test Data Generators)
const journeyStatusArbitrary = fc.constantFrom<JourneyStatus>(
  'created', 'running', 'paused', 'completed', 'failed', 'cancelled'
);

const journeyTypeArbitrary = fc.constantFrom<JourneyType>(
  'call-processing', 'operation-management'
);

const stageStatusArbitrary = fc.constantFrom<StageStatus>(
  'pending', 'running', 'completed', 'failed'
);

const jobMetricsArbitrary = fc.record({
  tasksFetched: fc.nat({ max: 1000 }),
  newTasks: fc.nat({ max: 1000 }),
  skippedTasks: fc.nat({ max: 1000 }),
  processedSuccessfully: fc.nat({ max: 1000 }),
  failed: fc.nat({ max: 100 }),
  transcriptsCollected: fc.nat({ max: 1000 }),
  analyzed: fc.nat({ max: 1000 }),
});


const durationArbitrary = fc.oneof(
  fc.constant(undefined),
  fc.tuple(
    fc.nat({ max: 23 }),
    fc.nat({ max: 59 }),
    fc.nat({ max: 59 })
  ).map(([h, m, s]) => {
    const parts: string[] = [];
    if (h > 0) parts.push(`${h}h`);
    if (m > 0) parts.push(`${m}m`);
    if (s > 0 || parts.length === 0) parts.push(`${s}s`);
    return parts.join(' ');
  })
);

const jobExecutionArbitrary: fc.Arbitrary<JobExecution> = fc.record({
  id: fc.uuid(),
  journeyId: fc.uuid(),
  stageId: fc.string({ minLength: 1, maxLength: 50 }),
  status: stageStatusArbitrary,
  startTime: fc.date({ min: new Date('2024-01-01'), max: new Date('2025-12-31') }),
  endTime: fc.option(fc.date({ min: new Date('2024-01-01'), max: new Date('2025-12-31') }), { nil: undefined }),
  duration: durationArbitrary,
  metrics: jobMetricsArbitrary,
  report: fc.constant(undefined),
});

const journeyMetricsArbitrary = fc.record({
  totalJobs: fc.nat({ max: 100 }),
  completedJobs: fc.nat({ max: 100 }),
  failedJobs: fc.nat({ max: 50 }),
  runningJobs: fc.nat({ max: 10 }),
  pendingJobs: fc.nat({ max: 10 }),
  totalCallsFetched: fc.nat({ max: 10000 }),
  totalCallsProcessed: fc.nat({ max: 10000 }),
  totalCallsAnalyzed: fc.nat({ max: 10000 }),
  totalErrors: fc.nat({ max: 1000 }),
  totalTranscripts: fc.nat({ max: 10000 }),
  successRate: fc.float({ min: 0, max: 100 }),
  averageJobDuration: fc.nat({ max: 3600000 }),
  totalExecutionTime: fc.nat({ max: 86400000 }),
  errorRate: fc.float({ min: 0, max: 100 }),
});

const journeyArbitrary: fc.Arbitrary<CallProcessingJourney> = fc.record({
  id: fc.uuid(),
  name: fc.string({ minLength: 1, maxLength: 100 }),
  type: journeyTypeArbitrary,
  status: journeyStatusArbitrary,
  overallProgress: fc.integer({ min: 0, max: 100 }),
  currentStageIndex: fc.integer({ min: 0, max: 4 }),
  config: fc.record({
    minutesBack: fc.integer({ min: 1, max: 10080 }),
    transcribe: fc.boolean(),
    registerGlue: fc.boolean(),
    runAnalysis: fc.boolean(),
    skipProcessed: fc.boolean(),
    s3Bucket: fc.option(fc.string(), { nil: undefined }),
    awsRegion: fc.option(fc.string(), { nil: undefined }),
  }),
  createdAt: fc.date({ min: new Date('2024-01-01'), max: new Date('2025-12-31') }),
  startedAt: fc.option(fc.date(), { nil: undefined }),
  completedAt: fc.option(fc.date(), { nil: undefined }),
  metrics: journeyMetricsArbitrary,
  stages: fc.constant([]),
});


// Property 3: Filter Correctness
describe('Property 3: Filter Correctness', () => {
  /**
   * Feature: call-processing-journeys, Property 3: Filter Correctness
   * **Validates: Requirements 2.2, 2.3, 2.4**
   */
  it('should return only journeys matching all applied filters', () => {
    fc.assert(
      fc.property(
        fc.array(journeyArbitrary, { minLength: 0, maxLength: 20 }),
        fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: undefined }),
        fc.option(journeyStatusArbitrary, { nil: undefined }),
        fc.option(journeyTypeArbitrary, { nil: undefined }),
        (journeys, searchQuery, statusFilter, typeFilter) => {
          const filtered = filterJourneys(journeys, {
            searchQuery,
            statusFilter,
            typeFilter,
          });

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

  it('should include all journeys that match the filters', () => {
    fc.assert(
      fc.property(
        fc.array(journeyArbitrary, { minLength: 0, maxLength: 20 }),
        fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: undefined }),
        fc.option(journeyStatusArbitrary, { nil: undefined }),
        fc.option(journeyTypeArbitrary, { nil: undefined }),
        (journeys, searchQuery, statusFilter, typeFilter) => {
          const filtered = filterJourneys(journeys, {
            searchQuery,
            statusFilter,
            typeFilter,
          });

          const expectedMatches = journeys.filter(journey => {
            const matchesSearch = !searchQuery ||
              journey.name.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesStatus = !statusFilter || journey.status === statusFilter;
            const matchesType = !typeFilter || journey.type === typeFilter;
            return matchesSearch && matchesStatus && matchesType;
          });

          return filtered.length === expectedMatches.length;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should return all journeys when no filters are applied', () => {
    fc.assert(
      fc.property(
        fc.array(journeyArbitrary, { minLength: 0, maxLength: 20 }),
        (journeys) => {
          const filtered = filterJourneys(journeys, {});
          return filtered.length === journeys.length;
        }
      ),
      { numRuns: 100 }
    );
  });
});


// Property 6: Action Availability by Journey Status
describe('Property 6: Action Availability by Journey Status', () => {
  /**
   * Feature: call-processing-journeys, Property 6: Action Availability
   * **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
   */
  const expectedActions: Record<JourneyStatus, JourneyAction[]> = {
    created: ['start', 'cancel'],
    running: ['pause', 'cancel'],
    paused: ['resume', 'cancel'],
    completed: [],
    failed: ['retry'],
    cancelled: [],
  };

  it('should return correct actions for any journey status', () => {
    fc.assert(
      fc.property(
        journeyStatusArbitrary,
        (status) => {
          const actions = getAvailableActions(status);
          const expected = expectedActions[status];
          if (actions.length !== expected.length) return false;
          return expected.every(action => actions.includes(action));
        }
      ),
      { numRuns: 100 }
    );
  });

  it('created status should have start and cancel actions', () => {
    const actions = getAvailableActions('created');
    expect(actions).toContain('start');
    expect(actions).toContain('cancel');
    expect(actions).toHaveLength(2);
  });

  it('running status should have pause and cancel actions', () => {
    const actions = getAvailableActions('running');
    expect(actions).toContain('pause');
    expect(actions).toContain('cancel');
    expect(actions).toHaveLength(2);
  });

  it('completed status should have no actions', () => {
    const actions = getAvailableActions('completed');
    expect(actions).toHaveLength(0);
  });

  it('failed status should have retry action', () => {
    const actions = getAvailableActions('failed');
    expect(actions).toContain('retry');
    expect(actions).toHaveLength(1);
  });
});


// Property 7: Job History Sorting Correctness
describe('Property 7: Job History Sorting Correctness', () => {
  /**
   * Feature: call-processing-journeys, Property 7: Sorting Correctness
   * **Validates: Requirements 10.5**
   */
  it('should sort by date in descending order', () => {
    fc.assert(
      fc.property(
        fc.array(jobExecutionArbitrary, { minLength: 2, maxLength: 20 }),
        (jobs) => {
          const sorted = sortJobs(jobs, 'date');
          for (let i = 0; i < sorted.length - 1; i++) {
            const current = new Date(sorted[i].startTime).getTime();
            const next = new Date(sorted[i + 1].startTime).getTime();
            if (current < next) return false;
          }
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should sort by status in priority order', () => {
    fc.assert(
      fc.property(
        fc.array(jobExecutionArbitrary, { minLength: 2, maxLength: 20 }),
        (jobs) => {
          const sorted = sortJobs(jobs, 'status');
          const statusOrder: Record<StageStatus, number> = {
            running: 0,
            pending: 1,
            completed: 2,
            failed: 3,
          };
          for (let i = 0; i < sorted.length - 1; i++) {
            if (statusOrder[sorted[i].status] > statusOrder[sorted[i + 1].status]) {
              return false;
            }
          }
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should sort by duration in descending order', () => {
    fc.assert(
      fc.property(
        fc.array(jobExecutionArbitrary, { minLength: 2, maxLength: 20 }),
        (jobs) => {
          const sorted = sortJobs(jobs, 'duration');
          for (let i = 0; i < sorted.length - 1; i++) {
            const currentDuration = parseDuration(sorted[i].duration);
            const nextDuration = parseDuration(sorted[i + 1].duration);
            if (currentDuration < nextDuration) return false;
          }
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should preserve all jobs after sorting', () => {
    fc.assert(
      fc.property(
        fc.array(jobExecutionArbitrary, { minLength: 0, maxLength: 20 }),
        fc.constantFrom<'date' | 'status' | 'duration'>('date', 'status', 'duration'),
        (jobs, sortBy) => {
          const sorted = sortJobs(jobs, sortBy);
          return sorted.length === jobs.length;
        }
      ),
      { numRuns: 100 }
    );
  });
});


// Property 8: Aggregate Statistics Calculation
describe('Property 8: Aggregate Statistics Calculation', () => {
  /**
   * Feature: call-processing-journeys, Property 8: Aggregate Stats
   * **Validates: Requirements 10.6**
   */
  it('should correctly sum totalCallsProcessed from all jobs', () => {
    fc.assert(
      fc.property(
        fc.array(jobExecutionArbitrary, { minLength: 0, maxLength: 20 }),
        (jobs) => {
          const stats = calculateAggregateStats(jobs);
          const expectedTotal = jobs.reduce(
            (sum, job) => sum + job.metrics.processedSuccessfully,
            0
          );
          return stats.totalCallsProcessed === expectedTotal;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should correctly calculate successRate', () => {
    fc.assert(
      fc.property(
        fc.array(jobExecutionArbitrary, { minLength: 1, maxLength: 20 }),
        (jobs) => {
          const stats = calculateAggregateStats(jobs);
          const completedCount = jobs.filter(j => j.status === 'completed').length;
          const expectedRate = (completedCount / jobs.length) * 100;
          return Math.abs(stats.successRate - expectedRate) < 0.001;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should correctly count jobs by status', () => {
    fc.assert(
      fc.property(
        fc.array(jobExecutionArbitrary, { minLength: 0, maxLength: 20 }),
        (jobs) => {
          const stats = calculateAggregateStats(jobs);
          const expectedCompleted = jobs.filter(j => j.status === 'completed').length;
          const expectedFailed = jobs.filter(j => j.status === 'failed').length;
          const expectedRunning = jobs.filter(j => j.status === 'running').length;
          const expectedPending = jobs.filter(j => j.status === 'pending').length;

          return (
            stats.completedJobs === expectedCompleted &&
            stats.failedJobs === expectedFailed &&
            stats.runningJobs === expectedRunning &&
            stats.pendingJobs === expectedPending &&
            stats.totalJobs === jobs.length
          );
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should return zero values for empty job list', () => {
    const stats = calculateAggregateStats([]);
    expect(stats.totalJobs).toBe(0);
    expect(stats.successRate).toBe(0);
    expect(stats.totalCallsProcessed).toBe(0);
  });
});
