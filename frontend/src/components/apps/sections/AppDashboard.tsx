import { useState, useEffect } from 'react';
import { apiClient } from '@/services/apiClient';
import type { AppConfig } from '@/config/appRegistry';
import { getWidgetsForApp } from '@/config/dashboardWidgets';
import { DashboardRenderer } from '../DashboardRenderer';
import { Skeleton } from '@/components/ui/skeleton';
import { AnimatedNumber } from '@/components/ds/AnimatedNumber';
import { StatusPill, SubHeading } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';

interface Props {
  app: AppConfig;
}

const pretty = (s: string) => s.replace(/_/g, ' ').replace(/\bAR\b/, 'AR').toLowerCase().replace(/^\w/, c => c.toUpperCase()).replace(/\bar\b/g, 'AR');

/** Process Analytics: KPIs against target, charts, and the live source records behind them. */
export function AppDashboard({ app }: Props) {
  const [liveData, setLiveData] = useState<Record<string, any>>({});
  const [liveLoading, setLiveLoading] = useState(true);

  const widgets = getWidgetsForApp(app.id);
  const hasRealWidgets = widgets.some(w => w.query.entity && !(w.config as any).placeholder);

  useEffect(() => {
    setLiveLoading(true);
    Promise.all(
      app.entities.slice(0, 4).map(e =>
        apiClient.get(`/api/v1/apps/${app.id}/live/${e}?limit=5`)
          .then(d => ({ entity: e, data: d }))
          .catch(() => ({ entity: e, data: null }))
      )
    ).then(results => {
      const map: Record<string, any> = {};
      for (const r of results) if (r.data) map[r.entity] = r.data;
      setLiveData(map);
    }).finally(() => setLiveLoading(false));
  }, [app.id]);

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-8 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-lg font-medium tracking-tight text-foreground">Process analytics</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">How {app.name.toLowerCase()} is performing against its targets, from the latest automation run.</p>
        </div>
        <StatusPill status="running" tone="success" live>Live data</StatusPill>
      </header>

      {hasRealWidgets ? (
        <DashboardRenderer appId={app.id} widgets={widgets} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-border bg-border shadow-xs sm:grid-cols-2 xl:grid-cols-4">
            {app.kpis.map(kpi => (
              <div key={kpi.label} className="bg-card p-5">
                <p className="text-sm text-muted-foreground">{kpi.label}</p>
                <p className="num mt-2 text-3xl font-medium tracking-tight text-subtle-foreground">—</p>
                <p className="mt-4 text-xs text-muted-foreground">Target <span className="num text-foreground">{kpi.target}</span></p>
              </div>
            ))}
          </div>
          <EmptyState
            icon="chart-bar"
            title="Charts appear after the first run"
            description="This solution has not produced results yet. Run its automation journey and the charts will fill in here."
          />
        </>
      )}

      <section>
        <SubHeading>Source records behind this view</SubHeading>
        <ul className="mt-3 grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 xl:grid-cols-4">
          {app.entities.slice(0, 4).map(entity => {
            const live = liveData[entity];
            const count = live?.total || live?.rows?.length || 0;
            return (
              <li key={entity} className="flex items-center justify-between gap-3 bg-card px-5 py-4">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">{pretty(entity)}</p>
                  <p className="text-xs text-muted-foreground">Read live from the virtual data layer</p>
                </div>
                {liveLoading ? <Skeleton className="h-6 w-12" /> : <AnimatedNumber value={count} className="num text-lg font-medium text-foreground" />}
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
