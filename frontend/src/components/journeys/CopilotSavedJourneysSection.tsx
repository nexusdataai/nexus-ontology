/**
 * CopilotSavedJourneysSection
 *
 * Lists journeys saved by the AI Copilot ("Save as Journey") via the
 * Phase 2 /api/v1/control-plane/journeys endpoints. Renders above the
 * legacy JourneyListView so users can run / inspect / delete them
 * without leaving the Journeys tab.
 */

import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  Sparkles, Play, Trash2, RefreshCw, Loader2, Search, ChevronDown, ChevronRight, FileText,
  CheckCircle2, XCircle, MinusCircle, ListTree, Eye, Clock,
} from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { useToast } from '@/hooks/use-toast';
import { PendingStepCard } from '@/components/journey-builder/PendingStepCard';
import { JourneyStudioView } from './JourneyStudioView';

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

  const load = async () => {
    setLoading(true);
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
    if (!window.confirm(`Delete journey "${j.title || j.journey_id}"?`)) return;
    try {
      await apiClient.delete(`/api/v1/control-plane/journeys/${j.journey_id}`);
      toast({ title: 'Journey deleted', description: j.title || j.journey_id });
      load();
    } catch (e: any) {
      toast({ title: 'Delete failed', description: e.message, variant: 'destructive' });
    }
  };

  const filtered = journeys;

  return (
    <Card className="mb-4">
      <CardHeader
        className="pb-2 cursor-pointer select-none"
        onClick={() => setExpanded(v => !v)}
      >
        <CardTitle className="text-sm flex items-center gap-2">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          <Sparkles className="h-4 w-4 text-primary" />
          Copilot Saved Journeys
          <Badge variant="outline" className="ml-2 text-[10px]">{journeys.length}</Badge>
        </CardTitle>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0">
          <div className="flex gap-2 items-center mb-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                value={search}
                onChange={e => setSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && load()}
                placeholder="Search journeys..."
                className="text-sm pl-8 h-8"
              />
            </div>
            <Button size="sm" variant="outline" onClick={load} disabled={loading}>
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            </Button>
          </div>

          {filtered.length === 0 && !loading && (
            <div className="text-center py-6 text-muted-foreground text-sm">
              <FileText className="h-8 w-8 mx-auto mb-2 opacity-30" />
              <p>No saved journeys yet.</p>
              <p className="text-xs mt-1 opacity-60">
                Use the AI Copilot tab to plan a journey, then click "Save as Journey".
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map(j => {
              const last = runResults[j.journey_id];
              const m = jobMetrics[j.journey_id] || {
                totalJobs: 0, completedJobs: 0, runningJobs: 0,
                failedJobs: 0, averageJobDurationMs: 0,
              };
              return (
                <div
                  key={j.journey_id}
                  className="border rounded-lg p-3 bg-card hover:shadow-md transition-shadow flex flex-col gap-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-sm truncate">{j.title || j.journey_id}</span>
                        {j.kind && (
                          <Badge variant="outline" className="text-[9px]">{j.kind}</Badge>
                        )}
                        {j.solution_id && (
                          <Badge variant="outline" className="text-[9px]">{j.solution_id}</Badge>
                        )}
                        {typeof j.step_count === 'number' && j.step_count > 0 && (
                          <Badge variant="outline" className="text-[9px]">{j.step_count} steps</Badge>
                        )}
                      </div>
                      <div className="text-[10px] text-muted-foreground font-mono truncate mt-0.5">
                        id: {j.journey_id}
                      </div>
                    </div>
                  </div>

                  {/* Stats Grid (visual parity with JourneyCard).
                      Numbers come from /api/v1/journeys/{id}/jobs --
                      same ai-engine framework regular journeys use. */}
                  <div className="grid grid-cols-4 gap-2 text-center py-2 bg-muted/30 rounded-lg">
                    <div>
                      <p className="text-lg font-bold">{m.totalJobs}</p>
                      <p className="text-[10px] text-muted-foreground">Jobs</p>
                    </div>
                    <div>
                      <p className="text-lg font-bold text-green-500">{m.completedJobs}</p>
                      <p className="text-[10px] text-muted-foreground">Done</p>
                    </div>
                    <div>
                      <p className="text-lg font-bold text-blue-400">{m.runningJobs}</p>
                      <p className="text-[10px] text-muted-foreground">Running</p>
                    </div>
                    <div>
                      <p className="text-lg font-bold text-red-500">{m.failedJobs}</p>
                      <p className="text-[10px] text-muted-foreground">Failed</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-center py-2 bg-muted/30 rounded-lg">
                    <div>
                      <p className="text-lg font-bold text-purple-400">{successRateOf(m)}%</p>
                      <p className="text-[10px] text-muted-foreground">Success Rate</p>
                    </div>
                    <div>
                      <p className="text-lg font-bold text-indigo-400">{fmtAvg(m.averageJobDurationMs)}</p>
                      <p className="text-[10px] text-muted-foreground">Avg Duration</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                    <div className="flex items-center gap-1 truncate">
                      {j.createdBy && <span className="truncate">by {j.createdBy}</span>}
                    </div>
                    {j.updatedAt && (
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        <span>{new Date(j.updatedAt).toLocaleString()}</span>
                      </div>
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="hidden">{/* legacy spacing wrapper retained */}</div>
                      {last && (
                        <div className="mt-2 text-[11px]">
                          {last.error ? (
                            <Badge className="bg-red-500/15 text-red-500 border-red-500/30">Error: {last.error}</Badge>
                          ) : last.status === 'awaiting_step_approval' ? (
                            <Badge className="bg-amber-500/15 text-amber-500 border-amber-500/30">
                              Paused at {last.pending_step?.step_name || last.pending_step?.step_id}
                            </Badge>
                          ) : (
                            <Badge className="bg-green-500/15 text-green-500 border-green-500/30">
                              {last.summary || `Completed ${(last.steps || []).length} steps`}
                            </Badge>
                          )}
                        </div>
                      )}
                      {last?.status === 'awaiting_step_approval' && last.pending_step && last.session_id && (
                        <PendingStepCard
                          runId={last.session_id}
                          pending={last.pending_step}
                          onApprove={(stepId) => handleApprove(j.journey_id, last.session_id!, stepId, true)}
                          onReject={(stepId) => handleApprove(j.journey_id, last.session_id!, stepId, false)}
                          className="mt-2"
                        />
                      )}
                    {last && Array.isArray(last.steps) && last.steps.length > 0 && (
                      <div className="mt-2">
                        <button
                            type="button"
                            className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
                            onClick={() =>
                              setStepsOpen((curr) => ({ ...curr, [j.journey_id]: !curr[j.journey_id] }))
                            }
                          >
                            {stepsOpen[j.journey_id] ? (
                              <ChevronDown className="h-3 w-3" />
                            ) : (
                              <ChevronRight className="h-3 w-3" />
                            )}
                            <ListTree className="h-3 w-3" />
                            Run details ({last.steps.length} step{last.steps.length === 1 ? '' : 's'})
                            {last.session_id && (
                              <span className="font-mono text-[10px] opacity-60 ml-1">{last.session_id}</span>
                            )}
                          </button>
                          {stepsOpen[j.journey_id] && (
                            <div className="mt-2 space-y-1 rounded-md border bg-card/40 p-2">
                              {last.steps.map((s, idx) => {
                                const key = `${j.journey_id}:${s.step_id}:${idx}`;
                                const open = stepBodyOpen[key];
                                const isFailed = s.status === 'failed' || !!s.error;
                                const isRejected = s.status === 'rejected';
                                const StatusIcon = isFailed
                                  ? XCircle
                                  : isRejected
                                    ? MinusCircle
                                    : CheckCircle2;
                                const iconColour = isFailed
                                  ? 'text-red-400'
                                  : isRejected
                                    ? 'text-amber-400'
                                    : 'text-green-400';
                                return (
                                  <div key={key} className="rounded border bg-background/40">
                                    <button
                                      type="button"
                                      className="w-full flex items-center gap-2 px-2 py-1.5 text-left hover:bg-muted/30"
                                      onClick={() =>
                                        setStepBodyOpen((curr) => ({ ...curr, [key]: !curr[key] }))
                                      }
                                    >
                                      {open ? (
                                        <ChevronDown className="h-3 w-3 shrink-0" />
                                      ) : (
                                        <ChevronRight className="h-3 w-3 shrink-0" />
                                      )}
                                      <StatusIcon className={`h-3.5 w-3.5 shrink-0 ${iconColour}`} />
                                      <span className="font-mono text-[11px] truncate">
                                        {idx + 1}. {s.step_id}
                                      </span>
                                      {s.tool && (
                                        <Badge variant="outline" className="text-[9px] shrink-0">
                                          {s.tool}
                                        </Badge>
                                      )}
                                      {typeof s.duration_ms === 'number' && (
                                        <span className="ml-auto text-[10px] text-muted-foreground shrink-0">
                                          {s.duration_ms} ms
                                        </span>
                                      )}
                                    </button>
                                    {open && (
                                      <div className="px-2 pb-2 space-y-1">
                                        {s.error && (
                                          <div className="text-[11px] text-red-300 bg-red-500/10 border border-red-500/30 rounded p-2 whitespace-pre-wrap">
                                            {s.error}
                                          </div>
                                        )}
                                        {s.result_preview && !s.error && (
                                          <div className="text-[11px] text-muted-foreground bg-muted/30 rounded p-2 whitespace-pre-wrap">
                                            {s.result_preview}
                                          </div>
                                        )}
                                        {s.result !== undefined && (
                                          <pre className="text-[10px] font-mono bg-muted/30 p-2 max-h-48 overflow-auto whitespace-pre-wrap rounded">
{typeof s.result === 'string' ? s.result : JSON.stringify(s.result, null, 2)}
                                          </pre>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      )}
                  </div>{/* /min-w-0 flex-1 */}

                  {/* Action row (visual parity with JourneyCard).
                      ``Journey Studio`` deep-links to the per-journey
                      studio detail view via ?journeyId=. Run + Delete
                      remain inline for quick actions. */}
                  <div className="flex items-center gap-2 pt-2 border-t">
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => onSelectJourney?.(j.journey_id)}
                      className="flex-1"
                    >
                      <Eye className="h-3 w-3 mr-1" />
                      Journey Studio
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleRun(j)}
                      disabled={runningId === j.journey_id}
                    >
                      {runningId === j.journey_id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Play className="h-3.5 w-3.5" />
                      )}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(j)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-500/10"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
