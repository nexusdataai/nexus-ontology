import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { Icon } from '@/components/ds/Icon';
import { InlineError, KeyValues, StatusPill } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { apiRequest } from '@/services/apiClient';

const TEST_CATEGORIES = [
  { id: 'unit', label: 'Unit tests', description: 'Each component on its own', color: '' },
  { id: 'integration', label: 'Integration tests', description: 'APIs and services working together', color: '' },
  { id: 'bdd', label: 'Behaviour tests', description: 'Business scenarios written as given, when, then', color: '' },
  { id: 'endurance', label: 'Endurance tests', description: 'Performance and stability over time', color: '' },
] as const;

type RunStatus = 'none' | 'queued' | 'in_progress' | 'completed' | 'failure' | 'cancelled';

interface WorkflowRun {
  run_id: number;
  status: string;
  conclusion: string | null;
  html_url: string;
  started_at: string | null;
  updated_at: string | null;
  actor: string;
  display_title: string;
}

interface CategoryResult {
  available: boolean;
  timestamp?: string;
  report_url?: string;
}

export function TestReportsPanel() {
  const [selected, setSelected] = useState<Set<string>>(new Set(['unit']));
  const [triggering, setTriggering] = useState(false);
  const [runStatus, setRunStatus] = useState<RunStatus>('none');
  // Set when the backend says test runs are not configured (503).
  const [notSetUp, setNotSetUp] = useState<string | null>(null);
  const [latestRun, setLatestRun] = useState<WorkflowRun | null>(null);
  const [recentRuns, setRecentRuns] = useState<WorkflowRun[]>([]);
  const [results, setResults] = useState<Record<string, CategoryResult>>({});
  // The report site ships with the product (public/test-reports), so it opens
  // from this installation and needs no outside hosting.
  const dashboardUrl = `${import.meta.env.BASE_URL}test-reports/index.html`;
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const toggleCategory = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const fetchStatus = useCallback(async () => {
    try {
      const data = await apiRequest<any>('/api/v1/tests/status', { requireAuth: false });
      setRunStatus(data.status === 'none' ? 'none' : data.conclusion || data.status);
      setLatestRun(data.latest_run || null);
      setRecentRuns(data.recent_runs || []);
      setNotSetUp(null);
      return data.status;
    } catch (e: any) {
      const msg = `${e?.message || ''} ${typeof e?.data?.detail === 'string' ? e.data.detail : ''}`;
      if (e?.status === 503 || /503|not configured/i.test(msg)) {
        setNotSetUp(/GITHUB_TOKEN/i.test(msg) ? 'the GitHub token that starts the test pipeline (GITHUB_TOKEN) is not set on the backend' : 'the test pipeline is not configured on the backend');
      }
      return 'none';
    }
  }, []);

  const fetchResults = useCallback(async () => {
    try {
      const data = await apiRequest<any>('/api/v1/tests/results', { requireAuth: false });
      setResults(data.categories || {});
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchResults();
  }, [fetchStatus, fetchResults]);

  useEffect(() => {
    if (runStatus === 'queued' || runStatus === 'in_progress') {
      pollRef.current = setInterval(async () => {
        const status = await fetchStatus();
        if (status === 'completed' || status === 'failure' || status === 'cancelled') {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          fetchResults();
        }
      }, 10_000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [runStatus, fetchStatus, fetchResults]);

  const handleRunTests = async () => {
    if (selected.size === 0) return;
    setTriggering(true);
    setError(null);
    try {
      await apiRequest('/api/v1/tests/run', {
        method: 'POST',
        body: JSON.stringify({ test_types: Array.from(selected) }),
        headers: { 'Content-Type': 'application/json' },
        requireAuth: false,
      });
      setRunStatus('queued');
      setTimeout(fetchStatus, 3000);
    } catch (e: any) {
      setError(e.message || 'Failed to trigger test run');
    } finally {
      setTriggering(false);
    }
  };

  const isRunning = runStatus === 'queued' || runStatus === 'in_progress';
  const STATUS_TEXT: Record<string, string> = { queued: 'Queued', in_progress: 'Running', completed: 'Passed', success: 'Passed', failure: 'Failed', cancelled: 'Cancelled', none: 'No runs yet' };
  const statusPill = (status: string, soft?: boolean) => (
    <StatusPill status={status === 'completed' ? 'success' : status === 'failure' ? 'failed' : status === 'none' ? 'neutral' : status} variant={soft ? 'soft' : 'dot'}>
      {STATUS_TEXT[status] || status.replace(/_/g, ' ')}
    </StatusPill>
  );
  const when = (iso?: string | null) => {
    if (!iso) return 'Not recorded';
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-xl font-medium tracking-tight text-foreground">Test reports</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Run the backend test suites and open their reports. Runs happen in the build pipeline and take a few minutes.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => { fetchStatus(); fetchResults(); }}>
            <Icon name="refresh" className="h-3.5 w-3.5" /> Refresh
          </Button>
          {dashboardUrl && (
            <Button variant="outline" onClick={() => window.open(dashboardUrl, '_blank')}>
              Open report dashboard <Icon name="external-link" className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </header>

      {error && <InlineError>{error}</InlineError>}
      {notSetUp && (
        <p role="status" className="rounded-lg border border-border bg-surface-2/60 px-4 py-3 text-sm text-muted-foreground">
          Test runs are not set up on this environment: {notSetUp}. Reports from earlier runs still open from the report dashboard.
        </p>
      )}

      {/* Choose suites and run */}
      <section className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3.5">
          <div>
            <h3 className="text-md font-medium text-foreground">Suites</h3>
            <p className="text-xs text-muted-foreground">Tick the suites to include in the next run.</p>
          </div>
          <div className="flex items-center gap-3">
            {statusPill(runStatus, true)}
            <Button onClick={handleRunTests} disabled={!!notSetUp || triggering || isRunning || selected.size === 0}>
              <Icon name={triggering || isRunning ? 'spinner' : 'play'} className={cn('h-3.5 w-3.5', (triggering || isRunning) && 'animate-spin')} />
              {triggering ? 'Starting' : isRunning ? 'Running' : selected.size > 1 ? `Run ${selected.size} suites` : 'Run suite'}
            </Button>
          </div>
        </div>
        <ul>
          {TEST_CATEGORIES.map((cat, i) => {
            const r = results[cat.id];
            const on = selected.has(cat.id);
            return (
              <li key={cat.id} className="rise flex flex-wrap items-center gap-4 border-b border-border px-5 py-3.5 last:border-b-0" style={{ ['--i' as any]: i }}>
                <label className={cn('flex min-w-0 flex-1 items-center gap-3.5', isRunning ? 'cursor-not-allowed opacity-60' : 'cursor-pointer')}>
                  <Checkbox checked={on} onCheckedChange={() => toggleCategory(cat.id)} disabled={isRunning} aria-label={`Include ${cat.label}`} />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-foreground">{cat.label}</span>
                    <span className="block truncate text-xs text-muted-foreground">{cat.description}</span>
                  </span>
                </label>
                <span className="w-48 shrink-0 text-xs text-muted-foreground">{r?.available ? <>Last report {r.timestamp || 'available'}</> : 'No report yet'}</span>
                {r?.available && r.report_url ? (
                  <Button variant="ghost" size="sm" onClick={() => window.open(r.report_url, '_blank')}>
                    View report <Icon name="external-link" className="h-3 w-3" />
                  </Button>
                ) : <span className="w-[108px]" aria-hidden="true" />}
              </li>
            );
          })}
        </ul>
      </section>

      {/* Latest run */}
      {latestRun && (
        <section>
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h3 className="text-md font-medium text-foreground">Latest run</h3>
            <a href={latestRun.html_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm text-primary underline-offset-4 hover:underline dark:text-brand-hi">
              Open in GitHub <Icon name="external-link" className="h-3 w-3" />
            </a>
          </div>
          <div className="rounded-xl border border-border bg-card px-5 py-1 shadow-xs">
            <KeyValues
              columns={2}
              items={[
                { label: 'Result', value: statusPill(latestRun.conclusion || latestRun.status) },
                { label: 'Started by', value: latestRun.actor },
                { label: 'Started', value: when(latestRun.started_at) },
                { label: 'Last update', value: when(latestRun.updated_at) },
              ]}
            />
          </div>
        </section>
      )}

      {/* History */}
      {recentRuns.length > 1 && (
        <section>
          <h3 className="mb-3 text-md font-medium text-foreground">Recent runs</h3>
          <ul className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
            {recentRuns.map(run => (
              <li key={run.run_id} className="flex flex-wrap items-center gap-4 border-b border-border px-5 py-3 last:border-b-0">
                <span className="w-28 shrink-0">{statusPill(run.conclusion || run.status)}</span>
                <span className="min-w-0 flex-1 truncate text-sm text-foreground">{run.display_title || 'Test run'}</span>
                <span className="text-xs text-muted-foreground">{run.actor}</span>
                <span className="w-32 text-right text-xs text-muted-foreground">{when(run.started_at)}</span>
                <a href={run.html_url} target="_blank" rel="noopener noreferrer" aria-label="Open this run in GitHub" className="rounded p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <Icon name="external-link" className="h-3.5 w-3.5" />
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
