/**
 * CopilotSavedJourneysSection
 *
 * Lists journeys saved by the AI Copilot ("Save as Journey") via the
 * Phase 2 /api/v1/control-plane/journeys endpoints, as a list of rows:
 * run one in place (the result opens under its row), open it in the
 * Journey Studio, or delete it.
 */

import { useEffect, useMemo, useState } from 'react';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { CodeBlock, InlineError, SearchInput, StatusPill, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { StepRail } from './studio/StepPipeline';
import { dayAndTime, humanize } from './studio/format';
import { apiClient } from '@/services/apiClient';
import { useToast } from '@/hooks/use-toast';
import { PendingStepCard } from '@/components/journey-builder/PendingStepCard';
import { JourneyStudioView } from './JourneyStudioView';
import { confirmDialog } from '@/components/ds/confirm';

interface SavedJourney {
  journey_id: string;
  title?: string;
  kind?: string;
  solution_id?: string;
  tags?: string[];
  step_count?: number;
  createdAt?: string;
  updatedAt?: string;
  createdBy?: string;
}

interface CopilotStepRecord {
  step_id: string;
  tool?: string;
  status?: 'completed' | 'failed' | 'rejected' | string;
  duration_ms?: number;
  result_preview?: string;
  result?: any;
  error?: string;
}

interface RunResult {
  // ``/journeys/{id}/run`` returns through the Copilot engine, so the
  // resume handle here is the engine ``session_id``, not the yaml-runner
  // ``run_id``. We keep both names so the inline approval card (which
  // expects a generic ``runId``) renders correctly.
  session_id?: string;
  run_id?: string;
  status?: string;
  pending_step?: any;
  steps?: CopilotStepRecord[];
  summary?: string;
  error?: string;
}

interface JobMetricsByJourney {
  totalJobs: number;
  completedJobs: number;
  runningJobs: number;
  failedJobs: number;
  averageJobDurationMs: number;
}

interface Props {
  /** When set, render the studio detail view for this journey id
   *  instead of the card grid. AIAutomationPage threads this through
   *  ``?journeyId=`` so the deep-link is shareable. */
  selectedJourneyId?: string;
  /** Called when the user clicks "Journey Studio" on a card. The
   *  parent should update the route so the back-button + URL stay
   *  consistent. */
  onSelectJourney?: (journeyId: string | null) => void;
}

export function CopilotSavedJourneysSection({
  selectedJourneyId,
  onSelectJourney,
}: Props = {}) {
  const [journeys, setJourneys] = useState<SavedJourney[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [runResults, setRunResults] = useState<Record<string, RunResult>>({});
  // Two per-journey UI toggles: ``stepsOpen`` controls the run-details
  // drill-down; ``stepBodyOpen`` controls per-step result body expand.
  const [stepsOpen, setStepsOpen] = useState<Record<string, boolean>>({});
  const [stepBodyOpen, setStepBodyOpen] = useState<Record<string, boolean>>({});
  // Per-journey jobs aggregate fetched from /api/v1/journeys/{id}/jobs
  // (same ai-engine framework regular Journeys use). Drives the
  // Jobs / Done / Running / Failed / Success Rate / Avg Duration
  // numbers on each card. Bridge writes JobExecution rows in the
  // transformation-system DDB whenever a saved journey runs.
  const [jobMetrics, setJobMetrics] = useState<Record<string, JobMetricsByJourney>>({});
  const { toast } = useToast();
  // The last list load failed (shown as an error with a retry).
  const [loadFailed, setLoadFailed] = useState(false);

  const load = async () => {
    setLoading(true);
    setLoadFailed(false);
    try {
      const data = await apiClient.get(
        `/api/v1/control-plane/journeys${search ? `?search=${encodeURIComponent(search)}` : ''}`,
      ) as { journeys: SavedJourney[]; total: number };
      setJourneys(data.journeys || []);
      // Fetch per-journey jobs in parallel so cards can show
      // Done/Running/Failed/SuccessRate/AvgDuration the same way
      // regular Journeys cards do. We swallow per-journey errors
      // (journey may have been mirrored but never run yet -> 404).
      const fetched = await Promise.all((data.journeys || []).map(async (j) => {
        try {
          const res = await apiClient.get(
            `/api/v1/journeys/${encodeURIComponent(j.journey_id)}/jobs?limit=200`,
          ) as { data?: any[]; jobs?: any[] } | any[];
          const rows: any[] = Array.isArray(res)
            ? res
            : ((res as any)?.data || (res as any)?.jobs || []);
          const total = rows.length;
          const done = rows.filter(r => r?.status === 'completed').length;
          const running = rows.filter(
            r => r?.status === 'running' || r?.status === 'in_progress',
          ).length;
          const failed = rows.filter(r => r?.status === 'failed').length;
          const durations = rows
            .map(r => r?.metrics?.durationSeconds || 0)
            .filter(v => v > 0);
          const avgMs = durations.length
            ? (durations.reduce((a, b) => a + b, 0) / durations.length) * 1000
            : 0;
          return [j.journey_id, {
            totalJobs: total,
            completedJobs: done,
            runningJobs: running,
            failedJobs: failed,
            averageJobDurationMs: avgMs,
          }] as const;
        } catch {
          return [j.journey_id, {
            totalJobs: 0, completedJobs: 0, runningJobs: 0,
            failedJobs: 0, averageJobDurationMs: 0,
          }] as const;
        }
      }));
      const map: Record<string, JobMetricsByJourney> = {};
      for (const [id, m] of fetched) map[id] = m;
      setJobMetrics(map);
    } catch (e: any) {
      toast({ title: 'Failed to load journeys', description: e.message, variant: 'destructive' });
      setJourneys([]);
      setLoadFailed(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // Helper for the card body -- mirrors JourneyCard's success-rate math.
  const successRateOf = (m: JobMetricsByJourney): number => {
    if (m.totalJobs <= 0) return 0;
    const denom = Math.max(m.completedJobs + m.failedJobs, 1);
    return Math.round((m.completedJobs * 100) / denom);
  };
  const fmtAvg = (ms: number): string => {
    if (!ms || ms <= 0) return '0s';
    const s = Math.round(ms / 1000);
    if (s < 60) return `${s}s`;
    return `${Math.floor(s / 60)}m ${s % 60}s`;
  };

  // Studio deep-link: short-circuit the rest of the render when
  // ``selectedJourneyId`` is set. We render the same JourneyStudioView
  // the legacy Journeys tab uses -- it auto-detects Copilot saved
  // journeys via the foundry-workspace probe and switches its step
  // source / Run dispatcher accordingly. Single React component drives
  // both surfaces.
  if (selectedJourneyId) {
    return (
      <JourneyStudioView
        journeyId={selectedJourneyId}
        onBack={() => onSelectJourney?.(null)}
      />
    );
  }

  const handleRun = async (j: SavedJourney) => {
    setRunningId(j.journey_id);
    try {
      const data = await apiClient.post(
        `/api/v1/control-plane/journeys/${j.journey_id}/run`,
        { inputs: {} },
        { timeout: 300000 },
      ) as RunResult;
      setRunResults(prev => ({ ...prev, [j.journey_id]: data }));
      if (data.error) {
        toast({ title: 'Run failed', description: data.error, variant: 'destructive' });
      } else if (data.status === 'awaiting_step_approval') {
        toast({
          title: 'Awaiting approval',
          description: `${j.title}: paused at "${data.pending_step?.step_name || data.pending_step?.step_id}". Approve / reject inline below.`,
        });
      } else {
        toast({
          title: 'Journey complete',
          description: data.summary || `${j.title || j.journey_id} executed.`,
        });
      }
    } catch (e: any) {
      toast({ title: 'Run failed', description: e.message, variant: 'destructive' });
    } finally {
      setRunningId(null);
    }
  };

  const handleApprove = async (journeyId: string, sessionId: string, stepId: string, approved: boolean) => {
    try {
      const data = await apiClient.post(
        `/api/v1/control-plane/copilot-journey/${encodeURIComponent(sessionId)}/approve-step`,
        { step_id: stepId, approved },
        { timeout: 300000 },
      ) as RunResult;
      // Preserve session_id on the next state snapshot so further
      // approvals on the same paused journey keep working.
      setRunResults(prev => ({ ...prev, [journeyId]: { ...data, session_id: sessionId } }));
      if (data.error) {
        toast({ title: 'Resume failed', description: data.error, variant: 'destructive' });
      } else if (data.status === 'awaiting_step_approval') {
        toast({
          title: 'Next approval needed',
          description: `paused at "${data.pending_step?.step_name || data.pending_step?.step_id}"`,
        });
      } else if (approved) {
        toast({ title: 'Journey complete', description: data.summary || 'Resumed and finished.' });
      } else {
        toast({ title: 'Step rejected', description: 'Run halted.', variant: 'destructive' });
      }
    } catch (e: any) {
      toast({ title: 'Approve failed', description: e.message, variant: 'destructive' });
    }
  };

  const handleDelete = async (j: SavedJourney) => {
    if (!(await confirmDialog({ title: `Delete journey "${j.title || j.journey_id}"?`, description: 'This cannot be undone.', destructive: true }))) return;
    try {
      await apiClient.delete(`/api/v1/control-plane/journeys/${j.journey_id}`);
      toast({ title: 'Journey deleted', description: j.title || j.journey_id });
      load();
    } catch (e: any) {
      toast({ title: 'Delete failed', description: e.message, variant: 'destructive' });
    }
  };

  const filtered = journeys;

  // Presentation only below this line.
  const firstLoad = loading && journeys.length === 0;
  const ROW_GRID = 'lg:grid lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_150px_auto] lg:items-center lg:gap-6';
  const ms = (v?: number) => (typeof v !== 'number' ? '' : v < 1000 ? `${Math.round(v)} ms` : `${(v / 1000).toFixed(1)} s`);

  return (
    <div data-testid="copilot-saved-journeys">
      <div className="flex flex-col gap-1">
        <h2 className="text-md font-medium text-foreground">Saved from Copilot</h2>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Plans you saved as journeys. Run one here, or open it in the studio to schedule it and follow each run.
        </p>
      </div>

      <Toolbar className="mt-5">
        <form onSubmit={(e) => { e.preventDefault(); load(); }} className="w-full sm:w-auto">
          <SearchInput value={search} onChange={setSearch} placeholder="Search saved journeys" />
        </form>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          <Icon name="search" /> Search
        </Button>
        <ToolbarSpacer />
        <span className="num text-sm text-muted-foreground">{journeys.length} {journeys.length === 1 ? 'journey' : 'journeys'}</span>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          <Icon name="refresh" className={loading ? 'animate-spin' : undefined} /> Refresh
        </Button>
      </Toolbar>

      <div className="mt-4">
        {loadFailed && !loading ? (
          <InlineError onRetry={load}>The saved journeys could not be loaded.</InlineError>
        ) : firstLoad ? (
          <div className="overflow-hidden rounded-xl border border-border bg-card">
            {[0, 1, 2, 3].map(i => (
              <div key={i} className="flex items-center gap-6 border-b border-border px-5 py-4 last:border-b-0">
                <div className="min-w-0 flex-1 space-y-2"><Skeleton className="h-4 w-56 max-w-full" /><Skeleton className="h-3 w-72 max-w-full" /></div>
                <Skeleton className="hidden h-4 w-32 lg:block" />
                <Skeleton className="hidden h-8 w-28 lg:block" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon="chat-bot"
            title={search ? 'No saved journeys match' : 'No saved journeys yet'}
            description={search ? 'Try another search.' : 'Plan a journey with the AI Copilot, then choose "Save as journey". It will be listed here.'}
          />
        ) : (
          <div className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
            <div className={cn('hidden border-b border-border bg-surface-2 px-5 py-2 text-xs font-medium text-muted-foreground', ROW_GRID)} aria-hidden="true">
              <span>Journey</span>
              <span>Runs</span>
              <span>Updated</span>
              <span className="w-[188px]" />
            </div>
            <div className="divide-y divide-border">
              {filtered.map((j, index) => {
                const last = runResults[j.journey_id];
                const m = jobMetrics[j.journey_id] || {
                  totalJobs: 0, completedJobs: 0, runningJobs: 0,
                  failedJobs: 0, averageJobDurationMs: 0,
                };
                const isRunning = runningId === j.journey_id;
                const meta = [
                  j.solution_id ? humanize(j.solution_id) : '',
                  typeof j.step_count === 'number' && j.step_count > 0 ? `${j.step_count} ${j.step_count === 1 ? 'step' : 'steps'}` : '',
                  j.kind && j.kind !== j.solution_id ? humanize(j.kind) : '',
                  j.createdBy ? `by ${j.createdBy}` : '',
                ].filter(Boolean).join(' · ');
                const steps = last && Array.isArray(last.steps) ? last.steps : [];
                const detailsOpen = !!stepsOpen[j.journey_id];
                return (
                  <article key={j.journey_id} className="rise" style={{ ['--i' as any]: index }}>
                    <div className={cn('group px-4 py-4 transition-colors duration-150 hover:bg-surface-2/60 sm:px-5', ROW_GRID)}>
                      <div className="min-w-0">
                        <button
                          type="button"
                          onClick={() => onSelectJourney?.(j.journey_id)}
                          className="block max-w-full truncate rounded-sm text-left text-md font-medium text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          {j.title || j.journey_id}
                        </button>
                        {meta && <p className="mt-0.5 truncate text-sm text-muted-foreground">{meta}</p>}
                        <p className="mono-id mt-1 truncate" title={j.journey_id}>{j.journey_id}</p>
                      </div>

                      <div className="mt-3 min-w-0 text-sm lg:mt-0">
                        {m.totalJobs === 0 ? (
                          <span className="text-muted-foreground">No runs yet</span>
                        ) : (
                          <>
                            <p className="text-foreground">
                              <span className="num font-medium">{successRateOf(m)}%</span>{' '}
                              <span className="text-muted-foreground">of <span className="num">{m.totalJobs}</span> {m.totalJobs === 1 ? 'run' : 'runs'} succeeded</span>
                            </p>
                            <p className="mt-0.5 text-xs text-muted-foreground">
                              {m.runningJobs > 0 && <span className="num text-primary dark:text-brand-hi">{m.runningJobs} running, </span>}
                              {m.failedJobs > 0 && <span className="num text-destructive">{m.failedJobs} failed, </span>}
                              <span className="num">about {fmtAvg(m.averageJobDurationMs)} each</span>
                            </p>
                          </>
                        )}
                      </div>

                      <p className="num mt-3 text-xs text-muted-foreground lg:mt-0">
                        {j.updatedAt ? dayAndTime(j.updatedAt) : 'Not recorded'}
                      </p>

                      <div className="mt-3 flex items-center justify-end gap-1 lg:mt-0 lg:w-[188px]">
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => handleDelete(j)}
                          aria-label={`Delete ${j.title || j.journey_id}`}
                          className="h-8 w-8 text-subtle-foreground hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 lg:opacity-0 lg:group-hover:opacity-100"
                        >
                          <Icon name="trash" className="h-3.5 w-3.5" />
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleRun(j)} disabled={isRunning}>
                          <Icon name={isRunning ? 'spinner' : 'play'} className={isRunning ? 'animate-spin' : undefined} /> {isRunning ? 'Running' : 'Run'}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => onSelectJourney?.(j.journey_id)}>
                          Open <Icon name="arrow-right" className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>

                    {/* Result of the run started from this row */}
                    {last && (
                      <div className="animate-fade-up border-t border-border bg-surface-2/40 px-4 py-3 sm:px-5">
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm">
                          {last.error ? (
                            <>
                              <StatusPill status="failed" />
                              <span className="min-w-0 text-destructive">{last.error}</span>
                            </>
                          ) : last.status === 'awaiting_step_approval' ? (
                            <>
                              <StatusPill status="awaiting_approval">Waiting for approval</StatusPill>
                              <span className="min-w-0 text-muted-foreground">Paused at {last.pending_step?.step_name || last.pending_step?.step_id}</span>
                            </>
                          ) : (
                            <>
                              <StatusPill status="completed" />
                              <span className="min-w-0 text-foreground">{last.summary || `Completed ${(last.steps || []).length} steps`}</span>
                            </>
                          )}
                          {steps.length > 0 && (
                            <button
                              type="button"
                              aria-expanded={detailsOpen}
                              className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                              onClick={() => setStepsOpen((curr) => ({ ...curr, [j.journey_id]: !curr[j.journey_id] }))}
                            >
                              {detailsOpen ? 'Hide' : 'Show'} {steps.length} {steps.length === 1 ? 'step' : 'steps'}
                              <Icon name={detailsOpen ? 'chevron-up' : 'chevron-down'} className="h-3 w-3" />
                            </button>
                          )}
                        </div>

                        {last.status === 'awaiting_step_approval' && last.pending_step && last.session_id && (
                          <PendingStepCard
                            runId={last.session_id}
                            pending={last.pending_step}
                            onApprove={(stepId) => handleApprove(j.journey_id, last.session_id!, stepId, true)}
                            onReject={(stepId) => handleApprove(j.journey_id, last.session_id!, stepId, false)}
                            className="mt-3"
                          />
                        )}

                        {steps.length > 0 && detailsOpen && (
                          <div className="mt-4 max-w-3xl">
                            {last.session_id && <p className="mb-3 text-xs text-muted-foreground">Session <span className="mono-id">{last.session_id}</span></p>}
                            <StepRail
                              items={steps.map((s, idx) => {
                                const key = `${j.journey_id}:${s.step_id}:${idx}`;
                                const open = !!stepBodyOpen[key];
                                const isFailed = s.status === 'failed' || !!s.error;
                                const isRejected = s.status === 'rejected';
                                const hasBody = !!s.error || !!s.result_preview || s.result !== undefined;
                                return {
                                  id: key,
                                  status: isFailed ? 'failed' : isRejected ? 'rejected' : 'completed',
                                  title: <span className="font-mono text-xs">{s.step_id}</span>,
                                  meta: (
                                    <>
                                      {s.tool && <span className="mono-id">{s.tool}</span>}
                                      {typeof s.duration_ms === 'number' && <span className="num">{ms(s.duration_ms)}</span>}
                                    </>
                                  ),
                                  action: hasBody ? (
                                    <button
                                      type="button"
                                      aria-expanded={open}
                                      className="font-medium text-primary underline-offset-4 hover:underline dark:text-brand-hi"
                                      onClick={() => setStepBodyOpen((curr) => ({ ...curr, [key]: !curr[key] }))}
                                    >
                                      {open ? 'Hide result' : 'Result'}
                                    </button>
                                  ) : undefined,
                                  body: (
                                    <>
                                      {isRejected && !s.error && <span className="text-warning">Rejected at the approval gate.</span>}
                                      {!open && s.error && <span className="line-clamp-1 text-destructive">{s.error}</span>}
                                      {!open && !s.error && s.result_preview && <span className="line-clamp-1">{s.result_preview}</span>}
                                      {open && (
                                        <div className="mt-1 space-y-2">
                                          {s.error && <span className="block whitespace-pre-wrap text-destructive">{s.error}</span>}
                                          {s.result_preview && !s.error && <span className="block whitespace-pre-wrap text-foreground">{s.result_preview}</span>}
                                          {s.result !== undefined && (
                                            <CodeBlock maxHeight={200} wrap>{typeof s.result === 'string' ? s.result : JSON.stringify(s.result, null, 2)}</CodeBlock>
                                          )}
                                        </div>
                                      )}
                                    </>
                                  ),
                                };
                              })}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
