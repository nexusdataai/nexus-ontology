import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import {
  Play, Loader2, CheckCircle, XCircle, Clock, ExternalLink,
  FlaskConical, Link2, BarChart3, RefreshCw,
} from 'lucide-react';
import { apiRequest } from '@/services/apiClient';

const TEST_CATEGORIES = [
  { id: 'unit', label: 'Unit Tests', description: 'Component-level test coverage', color: 'text-emerald-400' },
  { id: 'integration', label: 'Integration Tests', description: 'End-to-end API & service tests', color: 'text-blue-400' },
  { id: 'bdd', label: 'BDD Tests', description: 'Behavior-driven scenarios', color: 'text-amber-400' },
  { id: 'endurance', label: 'Endurance Tests', description: 'Performance & stability tests', color: 'text-purple-400' },
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
  const [latestRun, setLatestRun] = useState<WorkflowRun | null>(null);
  const [recentRuns, setRecentRuns] = useState<WorkflowRun[]>([]);
  const [results, setResults] = useState<Record<string, CategoryResult>>({});
  const [dashboardUrl, setDashboardUrl] = useState('');
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
      return data.status;
    } catch {
      return 'none';
    }
  }, []);

  const fetchResults = useCallback(async () => {
    try {
      const data = await apiRequest<any>('/api/v1/tests/results', { requireAuth: false });
      setResults(data.categories || {});
      setDashboardUrl(data.dashboard_url || '');
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

  const statusBadge = (status: RunStatus) => {
    switch (status) {
      case 'queued':
        return <Badge variant="outline" className="gap-1 text-yellow-400 border-yellow-400/40"><Clock className="h-3 w-3" />Queued</Badge>;
      case 'in_progress':
        return <Badge variant="outline" className="gap-1 text-blue-400 border-blue-400/40"><Loader2 className="h-3 w-3 animate-spin" />Running</Badge>;
      case 'completed':
        return <Badge variant="outline" className="gap-1 text-emerald-400 border-emerald-400/40"><CheckCircle className="h-3 w-3" />Passed</Badge>;
      case 'failure':
        return <Badge variant="outline" className="gap-1 text-red-400 border-red-400/40"><XCircle className="h-3 w-3" />Failed</Badge>;
      default:
        return <Badge variant="outline" className="gap-1 text-muted-foreground">No runs</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <FlaskConical className="h-5 w-5" /> Test Reports
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Run backend test suites and view reports
          </p>
        </div>
        {dashboardUrl && (
          <button
            onClick={() => window.open(dashboardUrl, '_blank')}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-purple-600/20 text-purple-300 hover:bg-purple-600/30 transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" /> Open Dashboard
          </button>
        )}
      </div>

      {/* Run Tests Card */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Run Tests</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {TEST_CATEGORIES.map(cat => (
              <button
                key={cat.id}
                onClick={() => toggleCategory(cat.id)}
                disabled={isRunning}
                className={`
                  rounded-lg border p-3 text-left transition-all text-sm
                  ${selected.has(cat.id)
                    ? 'border-blue-500/60 bg-blue-500/10'
                    : 'border-border hover:border-muted-foreground/40'
                  }
                  ${isRunning ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                `}
              >
                <div className={`font-medium ${cat.color}`}>{cat.label}</div>
                <div className="text-[11px] text-muted-foreground mt-0.5">{cat.description}</div>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunTests}
              disabled={triggering || isRunning || selected.size === 0}
              className="flex items-center gap-2 px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {triggering || isRunning
                ? <><Loader2 className="h-4 w-4 animate-spin" /> {triggering ? 'Triggering...' : 'Running...'}</>
                : <><Play className="h-4 w-4" /> Run Tests</>
              }
            </button>
            <button
              onClick={() => { fetchStatus(); fetchResults(); }}
              className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
              title="Refresh"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            {statusBadge(runStatus)}
          </div>

          {error && (
            <div className="text-sm text-red-400 bg-red-400/10 rounded-md px-3 py-2">{error}</div>
          )}
        </CardContent>
      </Card>

      {/* Latest Run */}
      {latestRun && (
        <Card className="border-border bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              Latest Run
              <a href={latestRun.html_url} target="_blank" rel="noopener noreferrer"
                className="text-xs text-blue-400 hover:underline flex items-center gap-1">
                <Link2 className="h-3 w-3" /> GitHub
              </a>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-muted-foreground text-xs">Status</div>
                <div className="mt-0.5">{statusBadge(latestRun.conclusion as RunStatus || latestRun.status as RunStatus)}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Triggered by</div>
                <div className="mt-0.5 font-medium">{latestRun.actor}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Started</div>
                <div className="mt-0.5">{latestRun.started_at ? new Date(latestRun.started_at).toLocaleString() : '-'}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Updated</div>
                <div className="mt-0.5">{latestRun.updated_at ? new Date(latestRun.updated_at).toLocaleString() : '-'}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <BarChart3 className="h-4 w-4" /> Available Reports
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {TEST_CATEGORIES.map(cat => {
              const r = results[cat.id];
              return (
                <div key={cat.id} className={`rounded-lg border p-4 ${r?.available ? 'border-border' : 'border-border/50 opacity-60'}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className={`font-medium text-sm ${cat.color}`}>{cat.label}</div>
                      {r?.available && r.timestamp && (
                        <div className="text-[11px] text-muted-foreground mt-0.5">Last run: {r.timestamp}</div>
                      )}
                      {!r?.available && (
                        <div className="text-[11px] text-muted-foreground mt-0.5">No reports available</div>
                      )}
                    </div>
                    {r?.available && r.report_url && (
                      <button
                        onClick={() => window.open(r.report_url, '_blank')}
                        className="flex items-center gap-1 text-xs px-2.5 py-1 rounded bg-blue-600/20 text-blue-300 hover:bg-blue-600/30 transition-colors"
                      >
                        <ExternalLink className="h-3 w-3" /> View
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Recent Runs */}
      {recentRuns.length > 1 && (
        <Card className="border-border bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Recent Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recentRuns.map(run => (
                <div key={run.run_id} className="flex items-center justify-between text-sm py-1.5 border-b border-border/50 last:border-0">
                  <div className="flex items-center gap-3">
                    {statusBadge(run.conclusion as RunStatus || run.status as RunStatus)}
                    <span className="text-muted-foreground text-xs">{run.actor}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">
                      {run.started_at ? new Date(run.started_at).toLocaleString() : '-'}
                    </span>
                    <a href={run.html_url} target="_blank" rel="noopener noreferrer"
                      className="text-blue-400 hover:underline text-xs">
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
