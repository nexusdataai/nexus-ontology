import { useEffect, useMemo, useState } from 'react';
import type { AppConfig } from '@/config/appRegistry';
import { getWidgetsForApp } from '@/config/dashboardWidgets';
import { apiClient } from '@/services/apiClient';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon, type IconName } from '@/components/ds/Icon';
import { StatusPill, KeyValues } from '@/components/ds/kit';
import { DashboardRenderer } from '../DashboardRenderer';

interface Props {
  app: AppConfig;
  onNavigate: (section: string, tab?: string) => void;
}

interface Alert { type?: string; severity?: string; entity_id?: string; description?: string; action?: string }

const SHORTCUTS: { id: string; label: string; desc: string; icon: IconName }[] = [
  { id: 'analytics', label: 'Process analytics', desc: 'KPIs against target, charts and the records behind them', icon: 'chart-bar' },
  { id: 'workflows', label: 'Workflow actions', desc: 'What the automation did, and under which policy', icon: 'workflow' },
  { id: 'reports', label: 'Reports and alerts', desc: 'Everything raised by the monitoring rules', icon: 'bell' },
  { id: 'tools-catalogue', label: 'Tools', desc: 'Agent tools this solution is allowed to use', icon: 'wrench' },
];

const STAGES: { label: string; icon: IconName }[] = [
  { label: 'Source data', icon: 'database' },
  { label: 'Knowledge graph', icon: 'graph' },
  { label: 'AI reasoning', icon: 'brain-ai' },
  { label: 'Actions', icon: 'bolt' },
];

const sevRank: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
const sevOf = (a: Alert) => String(a.severity || 'low').toLowerCase();
const words = (s?: string) => String(s || '').replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());

/** Business Insights: the state of the solution right now, in one screen. */
export function AppOverview({ app, onNavigate }: Props) {
  const AppIcon = app.icon;
  const sectionIds = new Set([...app.sections.map(s => s.id), 'tools-catalogue']);
  const shortcuts = SHORTCUTS.filter(s => sectionIds.has(s.id));
  const kpiWidgets = useMemo(() => getWidgetsForApp(app.id).filter(w => w.type === 'kpi_card' && w.query.entity && !(w.config as any).placeholder), [app.id]);

  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  useEffect(() => {
    let cancelled = false;
    setAlerts(null);
    apiClient.get(`/api/v1/apps/${app.id}/alerts`)
      .then((d: any) => { if (!cancelled) setAlerts(d?.alerts || []); })
      .catch(() => { if (!cancelled) setAlerts([]); });
    return () => { cancelled = true; };
  }, [app.id]);

  const sorted = useMemo(() => [...(alerts || [])].sort((a, b) => (sevRank[sevOf(a)] ?? 9) - (sevRank[sevOf(b)] ?? 9)), [alerts]);
  const urgent = sorted.filter(a => sevOf(a) === 'critical' || sevOf(a) === 'high').length;
  const available = app.status === 'available';

  return (
    <div className="page-end mx-auto w-full max-w-[1400px] space-y-10 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      {/* Identity and the one-line state */}
      <header className="flex flex-wrap items-start justify-between gap-x-8 gap-y-5">
        <div className="flex min-w-0 items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-border bg-card text-primary shadow-xs dark:text-brand-hi">
            <AppIcon className="h-6 w-6" strokeWidth={1.5} />
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <h1 className="text-lg font-medium tracking-tight text-foreground">{app.name}</h1>
              {available ? <StatusPill status="active" live tone="success">Running</StatusPill> : <StatusPill tone="neutral">Coming soon</StatusPill>}
            </div>
            <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">{app.description}</p>
            <div className="mt-3 text-sm text-foreground">
              {alerts === null ? (
                <Skeleton className="inline-block h-4 w-64 align-middle" />
              ) : sorted.length === 0 ? (
                'Nothing needs your attention right now.'
              ) : (
                <>
                  <span className="num font-medium">{sorted.length}</span> open {sorted.length === 1 ? 'alert' : 'alerts'}
                  {urgent > 0 && <>, <span className="num font-medium text-destructive">{urgent}</span> to look at today</>}.
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {sectionIds.has('reports') && <Button variant="outline" onClick={() => onNavigate('reports')}>View alerts</Button>}
          <Button onClick={() => onNavigate('analytics')}>
            Open analytics <Icon name="arrow-right" className="h-3.5 w-3.5" />
          </Button>
        </div>
      </header>

      {/* Live KPIs against target */}
      <section>
        <h2 className="mb-3 text-md font-medium text-foreground">Performance against target</h2>
        {kpiWidgets.length > 0 ? (
          <DashboardRenderer appId={app.id} widgets={kpiWidgets} />
        ) : (
          <dl className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-border bg-border shadow-xs sm:grid-cols-2 xl:grid-cols-4">
            {app.kpis.map(kpi => (
              <div key={kpi.label} className="bg-card p-5">
                <dt className="text-sm text-muted-foreground">{kpi.label}</dt>
                <dd className="num mt-2 text-3xl font-medium tracking-tight text-subtle-foreground">—</dd>
                <p className="mt-4 text-xs text-muted-foreground">Target <span className="num text-foreground">{kpi.target}</span></p>
              </div>
            ))}
          </dl>
        )}
      </section>

      <div className="grid gap-x-12 gap-y-10 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        {/* Needs attention */}
        <section className="min-w-0">
          <div className="flex items-baseline justify-between border-b border-border pb-2.5">
            <h2 className="text-md font-medium text-foreground">Needs attention</h2>
            {sorted.length > 4 && sectionIds.has('reports') && (
              <button type="button" onClick={() => onNavigate('reports')} className="text-sm text-primary underline-offset-4 hover:underline dark:text-brand-hi">
                All {sorted.length} alerts
              </button>
            )}
          </div>
          {alerts === null ? (
            <div className="space-y-4 py-4">{[0, 1, 2].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>
          ) : sorted.length === 0 ? (
            <p className="py-8 text-sm text-muted-foreground">All clear. New alerts appear here after each automation run.</p>
          ) : (
            <ul className="divide-y divide-border">
              {sorted.slice(0, 4).map((a, i) => (
                <li key={i} className="rise py-3.5" style={{ ['--i' as any]: i }}>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <StatusPill status={sevOf(a)} variant="soft" />
                    <span className="text-sm font-medium text-foreground">{words(a.type || 'alert')}</span>
                    {a.entity_id && <span className="ml-auto font-mono text-xs text-muted-foreground">{a.entity_id}</span>}
                  </div>
                  {a.description && <p className="mt-1.5 text-sm text-muted-foreground">{a.description}</p>}
                  {a.action && (
                    <p className="mt-1.5 flex items-start gap-1.5 text-xs text-foreground">
                      <Icon name="arrow-right" className="mt-0.5 h-3 w-3 shrink-0 text-primary dark:text-brand-hi" />
                      <span>{a.action}</span>
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* How it works + facts */}
        <aside className="min-w-0 space-y-8">
          <section>
            <h2 className="border-b border-border pb-2.5 text-md font-medium text-foreground">How this solution works</h2>
            <ol className="mt-5 flex items-start">
              {STAGES.map((s, i) => (
                <li key={s.label} className="relative flex flex-1 flex-col items-center text-center">
                  {i > 0 && (
                    <svg className="absolute right-1/2 top-5 h-px w-full -translate-y-1/2 overflow-visible text-primary dark:text-brand-hi" aria-hidden="true">
                      <line x1="22" x2="100%" y1="0" y2="0" stroke="currentColor" strokeWidth="1.5" className="flow-line" style={{ transform: 'translateX(-22px)' }} />
                    </svg>
                  )}
                  <span className="relative z-10 flex h-10 w-10 items-center justify-center rounded-full border border-border bg-card text-foreground shadow-xs">
                    <Icon name={s.icon} className="h-[18px] w-[18px]" />
                  </span>
                  <span className="mt-2 px-1 text-xs text-muted-foreground">{s.label}</span>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-sm text-muted-foreground">
              Reads {app.entities.length} business entities live from your systems, links them in the knowledge graph, and lets the agents act within policy.
            </p>
          </section>

          <section>
            <h2 className="border-b border-border pb-1 text-md font-medium text-foreground">About</h2>
            <KeyValues
              items={[
                { label: 'Use case', value: app.useCase, mono: true },
                { label: 'Business entities', value: app.entities.length },
                { label: 'KPIs tracked', value: app.kpis.length },
              ]}
            />
            <div className="mt-3 flex flex-wrap gap-1.5">
              {app.entities.map(e => (
                <span key={e} className="rounded-md border border-border bg-surface-2/70 px-2 py-0.5 text-xs text-muted-foreground">{e.replace(/_/g, ' ')}</span>
              ))}
            </div>
          </section>
        </aside>
      </div>

      {/* Go to */}
      <section>
        <h2 className="mb-3 text-md font-medium text-foreground">Explore</h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {shortcuts.map(item => (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className="group flex flex-col rounded-xl border border-border bg-card p-5 text-left shadow-xs transition-all duration-300 ease-brand-out hover:-translate-y-0.5 hover:border-brand/50 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span className="flex items-center justify-between">
                <Icon name={item.icon} className="h-5 w-5 text-muted-foreground transition-colors group-hover:text-primary dark:group-hover:text-brand-hi" />
                <Icon name="arrow-up-right" className="h-3.5 w-3.5 text-subtle-foreground transition-transform duration-300 ease-brand-out group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground" />
              </span>
              <span className="mt-4 text-sm font-medium text-foreground">{item.label}</span>
              <span className="mt-1 text-xs text-muted-foreground">{item.desc}</span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
