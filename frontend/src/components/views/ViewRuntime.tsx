import { useEffect, useMemo, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { View, ViewTab } from '@/lib/foundry/model';
import type { DashboardModel } from '@/lib/dashboard/model';
import type { TimeRange } from '@/lib/dashboard/types';
import { DashboardGrid } from '@/lib/dashboard/components/DashboardGrid';
import { dashboardService } from '@/services/dashboardService';
import { viewService } from '@/services/viewService';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ds/primitives';

interface ViewRuntimeProps {
  viewId?: string;
  view?: View;
  className?: string;
}

export function ViewRuntime({ viewId, view: viewProp, className }: ViewRuntimeProps) {
  const [view, setView] = useState<View | null>(viewProp || null);
  const [loading, setLoading] = useState(!viewProp);
  const [active, setActive] = useState<string | undefined>(undefined);
  // Seeded views name their tabs "Tab 1", "Tab 2". Show the dashboard's own
  // title for those, so the tab says what is in it.
  const [tabTitles, setTabTitles] = useState<Record<string, string>>({});

  useEffect(() => {
    if (viewProp) {
      setView(viewProp);
      setLoading(false);
      return;
    }
    if (!viewId) return;
    setLoading(true);
    viewService
      .get(viewId)
      .then((v) => setView(v))
      .catch(() => toast.error('Failed to load view'))
      .finally(() => setLoading(false));
  }, [viewId, viewProp]);

  useEffect(() => {
    if (!view) return;
    if (active && view.tabs.some((t) => t.tabId === active)) return;
    const fallback = view.defaultTabId || view.tabs[0]?.tabId;
    if (fallback) setActive(fallback);
  }, [view, active]);

  useEffect(() => {
    if (!view) return;
    let cancelled = false;
    const generic = view.tabs.filter((t) => !t.label || /^tab\s*\d+$/i.test(t.label.trim()));
    Promise.all(generic.map((t) => dashboardService.get(t.dashboardId).then((d) => [t.tabId, d?.title || ''] as const).catch(() => [t.tabId, ''] as const)))
      .then((pairs) => { if (!cancelled) setTabTitles(Object.fromEntries(pairs.filter(([, title]) => title))); });
    return () => { cancelled = true; };
  }, [view]);

  if (loading) {
    return (
      <div className="p-4 sm:px-6" aria-busy="true" aria-label="Loading view">
        <div className="flex gap-5 border-b border-border pb-3">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
        </div>
        <DashboardSkeleton className="mt-4" />
      </div>
    );
  }

  if (!view) {
    return (
      <div className="p-4 sm:p-6">
        <EmptyState
          icon="layers"
          title="This view is not available"
          description="It may have been deleted, or the server did not answer. Go back and try again."
        />
      </div>
    );
  }

  if (view.tabs.length === 0) {
    return (
      <div className="p-4 sm:p-6">
        <EmptyState
          icon="layers"
          title="No dashboards in this view yet"
          description="A view shows one dashboard per tab. Edit the view to add the first tab."
        />
      </div>
    );
  }

  return (
    <div className={className || 'flex flex-col h-full'}>
      <Tabs value={active} onValueChange={setActive} className="flex flex-col flex-1 min-h-0">
        <div className="px-4 sm:px-6">
          <TabsList variant="line">
            {view.tabs.map((tab) => (
              <TabsTrigger key={tab.tabId} value={tab.tabId}>
                {tabTitles[tab.tabId] || tab.label || 'Untitled'}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        <div className="flex-1 overflow-auto">
          {view.tabs.map((tab) => (
            <TabsContent key={tab.tabId} value={tab.tabId} className="mt-0 p-3 sm:p-4">
              <ViewTabPanel tab={tab} />
            </TabsContent>
          ))}
        </div>
      </Tabs>
    </div>
  );
}

interface ViewTabPanelProps {
  tab: ViewTab;
}

/** Placeholder with the rough shape of a dashboard while it loads. */
export function DashboardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('grid gap-2 md:grid-cols-2', className)} aria-busy="true" aria-label="Loading dashboard">
      {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-48 rounded-xl" />)}
    </div>
  );
}

/** One tab of a view: its dashboard, read only, with the tab's time range. */
export function ViewTabPanel({ tab }: ViewTabPanelProps) {
  const [dashboard, setDashboard] = useState<DashboardModel | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    dashboardService
      .get(tab.dashboardId)
      .then(setDashboard)
      .catch(() => toast.error(`Failed to load dashboard for tab ${tab.label}`))
      .finally(() => setLoading(false));
  }, [tab.dashboardId, tab.label]);

  const timeRange = useMemo<TimeRange>(() => {
    if (tab.timeOverride && tab.timeOverride.from && tab.timeOverride.to) {
      return { from: tab.timeOverride.from, to: tab.timeOverride.to };
    }
    if (dashboard?.time) return dashboard.time;
    return { from: 'now-6h', to: 'now' };
  }, [tab.timeOverride, dashboard]);

  if (loading) {
    return (
      <DashboardSkeleton />
    );
  }

  if (!dashboard) {
    return (
      <EmptyState
        icon="dashboard"
        title="This dashboard is not available"
        description="The dashboard behind this tab could not be loaded. It may have been deleted. Edit the view to choose another one."
      />
    );
  }

  return (
    <DashboardGrid
      panels={dashboard.panels}
      timeRange={timeRange}
      isEditing={false}
      onLayoutChange={() => {}}
      onEditPanel={() => {}}
      onDuplicatePanel={() => {}}
      onRemovePanel={() => {}}
    />
  );
}

export default ViewRuntime;
