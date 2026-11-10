/**
 * AI Health Central monitoring panel (AI-OPs plane, Phase 1).
 *
 * Reads plane-by-plane health snapshots from `/api/v1/ai-health/*` and
 * renders a per-plane card grid + a "Run now" button + a small sparkline
 * of recent snapshots.
 */

import { useEffect, useMemo, useState } from 'react';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Icon, type IconName } from '@/components/ds/Icon';
import { InlineError, StatusPill } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { cn } from '@/lib/utils';
import {
  aiHealthService,
  HealthSnapshot,
  HealthVerdict,
  PlaneKey,
  PlaneSnapshot,
} from '@/services/aiHealthService';

const PLANE_META: { key: PlaneKey; label: string; icon: IconName; what: string }[] = [
  { key: 'data', label: 'Data Plane', icon: 'database', what: 'Sources, mapping rules and pipelines' },
  { key: 'control', label: 'Control Plane', icon: 'layers', what: 'Knowledge index and graph' },
  { key: 'reasoning', label: 'Reasoning', icon: 'brain-ai', what: 'Agents, tools and model latency' },
  { key: 'workspace', label: 'Workspace', icon: 'apps', what: 'Solutions, journeys and dashboards' },
  { key: 'ai_ops', label: 'AI Ops', icon: 'activity', what: 'Diagnostics, tests and alarms' },
];

const BAR: Record<string, string> = { healthy: 'bg-success', degraded: 'bg-warning', unhealthy: 'bg-destructive' };
const metricLabel = (k: string) => {
  const s = k.replace(/_/g, ' ').replace(/\b24h\b/, '(24 h)').replace(/\bms\b/, '(ms)').replace(/\bp95\b/i, 'P95').replace(/\bfdw\b/i, 'Virtual').replace(/\bapis\b/i, 'APIs');
  return s.charAt(0).toUpperCase() + s.slice(1);
};
const metricValue = (v: unknown) => (typeof v === 'number' ? v.toLocaleString('en-US') : String(v));

/** Status-page style history: one slot per check, newest on the right. */
function History({ items }: { items: HealthSnapshot[] }) {
  if (items.length === 0) return <p className="text-sm text-muted-foreground">No history yet.</p>;
  const ordered = items.slice().reverse();
  const healthy = ordered.filter(s => s.verdict === 'healthy').length;
  const fmt = (iso: string) => { const d = new Date(iso); return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }); };
  return (
    <div>
      <div className="flex h-9 items-stretch gap-[3px]" role="img" aria-label={`${healthy} of ${ordered.length} recent checks were healthy`}>
        {ordered.map((s, i) => (
          <span
            key={s.iso_ts + i}
            title={`${fmt(s.iso_ts)}: ${s.verdict}`}
            className={cn('rise min-w-[3px] flex-1 rounded-[2px] hover:brightness-125', BAR[s.verdict as string] || 'bg-surface-3')}
            style={{ ['--i' as any]: i * 0.25 }}
          />
        ))}
      </div>
      <div className="mt-2 flex items-center justify-between gap-4 text-xs text-muted-foreground">
        <span>{fmt(ordered[0].iso_ts)}</span>
        <span><span className="num font-medium text-foreground">{Math.round((healthy / ordered.length) * 100)}%</span> of the last {ordered.length} checks were healthy</span>
        <span>Now</span>
      </div>
    </div>
  );
}

export function AiHealthMonitoringPanel() {
  const [latest, setLatest] = useState<HealthSnapshot | null>(null);
  const [history, setHistory] = useState<HealthSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [l, ts] = await Promise.all([
        aiHealthService.latest('all'),
        aiHealthService.timeseries('all', 48),
      ]);
      setLatest(l && !l.empty ? l : null);
      setHistory(ts.items || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to load AI health');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const runNow = async () => {
    setRunning(true);
    try {
      const snap = await aiHealthService.runNow('all');
      setLatest(snap);
      await load();
    } catch (e: any) {
      setError(e?.message || 'Failed to trigger snapshot');
    } finally {
      setRunning(false);
    }
  };

  const rollup: HealthVerdict = (latest?.verdict as HealthVerdict) || 'unknown';
  const planes = latest?.planes || {};

  const recordedAt = useMemo(() => {
    if (!latest?.iso_ts) return null;
    try {
      return new Date(latest.iso_ts).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    } catch {
      return latest.iso_ts;
    }
  }, [latest]);

  const planeStatus = (k: PlaneKey): HealthVerdict => ((planes[k] as PlaneSnapshot | undefined)?.status as HealthVerdict) || 'unknown';
  const troubled = PLANE_META.filter(p => planeStatus(p.key) === 'degraded' || planeStatus(p.key) === 'unhealthy');
  const issues = PLANE_META.flatMap(p => ((planes[p.key] as PlaneSnapshot | undefined)?.errors || []).map(e => ({ plane: p.label, text: e, status: planeStatus(p.key) })));

  const headline =
    rollup === 'healthy' ? 'All systems are healthy'
    : rollup === 'unknown' ? 'Health has not been checked yet'
    : troubled.length === 1 ? `${troubled[0].label} needs attention`
    : `${troubled.length || 'Some'} areas need attention`;
  const tone = rollup === 'healthy' ? 'text-success' : rollup === 'degraded' ? 'text-warning' : rollup === 'unhealthy' ? 'text-destructive' : 'text-muted-foreground';

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-8">
      {/* Verdict */}
      <section className="rounded-2xl border border-border bg-card p-6 shadow-xs sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-x-8 gap-y-4">
          <div className="flex min-w-0 items-start gap-4">
            <span className={cn('relative mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full', tone)}>
              <span className="absolute inset-0 rounded-full bg-current opacity-10" aria-hidden="true" />
              {loading ? <Icon name="spinner" className="h-5 w-5 animate-spin" /> : <Icon name={rollup === 'healthy' ? 'check-circle' : rollup === 'unknown' ? 'info' : 'alert-triangle'} className="h-5 w-5" />}
            </span>
            <div className="min-w-0">
              {loading ? (
                <><Skeleton className="h-7 w-64" /><Skeleton className="mt-2 h-4 w-80" /></>
              ) : (
                <>
                  <h2 className="text-2xl font-medium tracking-tight text-foreground">{headline}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {recordedAt ? <>Last checked {recordedAt}{typeof latest?.elapsed_ms === 'number' && <>, took <span className="num">{latest.elapsed_ms}</span> ms</>}. </> : null}
                    A check runs every 15 minutes across all five areas of the platform.
                  </p>
                </>
              )}
            </div>
          </div>
          <Button variant="outline" onClick={runNow} disabled={running || loading}>
            <Icon name={running ? 'spinner' : 'refresh'} className={cn('h-3.5 w-3.5', running && 'animate-spin')} />
            {running ? 'Checking' : 'Check now'}
          </Button>
        </div>
        {!loading && latest && <div className="mt-7"><History items={history} /></div>}
      </section>

      {error && <InlineError onRetry={load}>{error}</InlineError>}

      {!loading && !latest && !error && (
        <EmptyState icon="heartbeat" title="No health checks recorded yet" description="Run the first check to see the state of every part of the platform." action={<Button onClick={runNow} disabled={running}>Check now</Button>} />
      )}

      {!loading && latest && (
        <>
          {issues.length > 0 && (
            <section>
              <h3 className="mb-3 text-md font-medium text-foreground">Needs attention</h3>
              <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-card shadow-xs">
                {issues.map((it, i) => (
                  <li key={i} className="rise flex flex-wrap items-start gap-x-4 gap-y-1 px-5 py-3.5" style={{ ['--i' as any]: i }}>
                    <StatusPill status={it.status} variant="soft" className="mt-0.5">{it.plane}</StatusPill>
                    <span className="min-w-0 flex-1 text-sm text-foreground">{it.text}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h3 className="mb-3 text-md font-medium text-foreground">By area</h3>
            <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-card shadow-xs">
              {PLANE_META.map((p, i) => {
                const snap = planes[p.key] as PlaneSnapshot | undefined;
                const counts = Object.entries(snap?.counts || {});
                return (
                  <li key={p.key} className="rise grid gap-x-8 gap-y-4 px-5 py-5 lg:grid-cols-[260px_minmax(0,1fr)]" style={{ ['--i' as any]: i }}>
                    <div className="flex items-start gap-3">
                      <Icon name={p.icon} className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground">{p.label}</p>
                        <p className="text-xs text-muted-foreground">{p.what}</p>
                        <StatusPill status={planeStatus(p.key)} className="mt-2" />
                      </div>
                    </div>
                    {counts.length === 0 ? (
                      <p className="self-center text-sm text-muted-foreground">No measurements recorded yet.</p>
                    ) : (
                      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
                        {counts.map(([k, v]) => (
                          <div key={k} className="min-w-0">
                            <dt className="truncate text-xs text-muted-foreground" title={metricLabel(k)}>{metricLabel(k)}</dt>
                            <dd className="num mt-0.5 text-lg font-medium tracking-tight text-foreground">{metricValue(v)}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
