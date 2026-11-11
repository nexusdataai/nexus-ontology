import { useState, useEffect, useMemo } from 'react';
import { apiClient } from '@/services/apiClient';
import type { AppConfig } from '@/config/appRegistry';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { Chips, SearchInput, StatusPill, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { cn } from '@/lib/utils';

interface Props { app: AppConfig; }

const LEVELS = ['critical', 'high', 'medium', 'low'] as const;
const LEVEL_BG: Record<string, string> = { critical: 'bg-destructive', high: 'bg-warning', medium: 'bg-warning/60', low: 'bg-border-strong' };
const sevOf = (a: any) => String(a?.severity || 'low').toLowerCase();
const words = (s?: string) => String(s || 'alert').replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());

/** Reports: every alert raised by the solution's monitoring rules. */
export function AppAlerts({ app }: Props) {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [level, setLevel] = useState<string>('all');
  const [query, setQuery] = useState('');

  const loadAlerts = () => {
    setLoading(true);
    apiClient.get(`/api/v1/apps/${app.id}/alerts`)
      .then((d: any) => setAlerts(d.alerts || []))
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadAlerts(); }, [app.id]);

  const counts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const a of alerts) m[sevOf(a)] = (m[sevOf(a)] || 0) + 1;
    return m;
  }, [alerts]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rank = (a: any) => LEVELS.indexOf(sevOf(a) as any);
    return alerts
      .filter(a => (level === 'all' || sevOf(a) === level) && (!q || `${a.type} ${a.entity_id} ${a.description} ${a.action}`.toLowerCase().includes(q)))
      .sort((a, b) => rank(a) - rank(b));
  }, [alerts, level, query]);

  const total = alerts.length || 1;

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-8 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-lg font-medium tracking-tight text-foreground">Reports and alerts</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Everything the monitoring rules of {app.name} have raised, most urgent first.</p>
        </div>
        <Button variant="outline" onClick={loadAlerts} disabled={loading}>
          <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
        </Button>
      </header>

      {loading ? (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-72 w-full rounded-xl" />
        </div>
      ) : alerts.length === 0 ? (
        <EmptyState icon="check-circle" title="No open alerts" description="Run the solution's automation journey. Anything that breaks a monitoring rule is reported here." />
      ) : (
        <>
          {/* Severity mix: one bar, one sentence */}
          <section className="rounded-xl border border-border bg-card p-5 shadow-xs">
            <p className="text-sm text-muted-foreground">
              <span className="num text-3xl font-medium tracking-tight text-foreground">{alerts.length}</span>
              <span className="ml-2">open alerts</span>
              {(counts.critical || 0) + (counts.high || 0) > 0 && (
                <span className="ml-1">· <span className="num font-medium text-foreground">{(counts.critical || 0) + (counts.high || 0)}</span> critical or high</span>
              )}
            </p>
            <div className="mt-4 flex h-2 gap-0.5 overflow-hidden rounded-full" role="img" aria-label="Alerts by severity">
              {LEVELS.filter(l => counts[l]).map((l, i) => (
                <span key={l} className={cn('grow-x h-full first:rounded-l-full last:rounded-r-full', LEVEL_BG[l])} style={{ width: `${(counts[l] / total) * 100}%`, ['--i' as any]: i }} />
              ))}
            </div>
            <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-1.5 text-sm">
              {LEVELS.map(l => (
                <li key={l} className="flex items-center gap-2 text-muted-foreground">
                  <span className={cn('h-2 w-2 rounded-[2px]', LEVEL_BG[l])} aria-hidden="true" />
                  <span className="capitalize">{l}</span>
                  <span className="num font-medium text-foreground">{counts[l] || 0}</span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <Toolbar>
              <Chips
                label="Filter by severity"
                value={level}
                onChange={setLevel}
                options={[{ value: 'all', label: 'All', count: alerts.length }, ...LEVELS.filter(l => counts[l]).map(l => ({ value: l as string, label: l.charAt(0).toUpperCase() + l.slice(1), count: counts[l] }))]}
              />
              <ToolbarSpacer />
              <SearchInput value={query} onChange={setQuery} placeholder="Search alerts" className="w-full sm:w-64" />
            </Toolbar>

            <div className="mt-3 overflow-hidden rounded-xl border border-border bg-card shadow-xs">
              {visible.length === 0 ? (
                <p className="px-5 py-10 text-center text-sm text-muted-foreground">No alerts match this filter.</p>
              ) : (
                <ul className="divide-y divide-border">
                  {visible.map((alert, i) => (
                    <li key={i} className="rise grid gap-x-6 gap-y-1.5 px-5 py-4 md:grid-cols-[120px_minmax(0,1fr)_auto]" style={{ ['--i' as any]: Math.min(i, 10) }}>
                      <div><StatusPill status={sevOf(alert)} variant="soft" /></div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground">{words(alert.type)}</p>
                        {(alert.description || alert.message) && <p className="mt-1 text-sm text-muted-foreground">{alert.description || alert.message}</p>}
                        {alert.action && (
                          <p className="mt-2 flex items-start gap-1.5 text-sm text-foreground">
                            <Icon name="arrow-right" className="mt-1 h-3 w-3 shrink-0 text-primary dark:text-brand-hi" />
                            <span>{alert.action}</span>
                          </p>
                        )}
                      </div>
                      {alert.entity_id && <span className="font-mono text-xs text-muted-foreground md:text-right">{alert.entity_id}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
