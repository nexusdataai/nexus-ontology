import { useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { View, ViewTab } from '@/lib/foundry/model';
import type { DashboardModel } from '@/lib/dashboard/model';
import type { TimeRange } from '@/lib/dashboard/types';
import { DashboardGrid } from '@/lib/dashboard/components/DashboardGrid';
import { dashboardService } from '@/services/dashboardService';
import { viewService } from '@/services/viewService';
import { toast } from 'sonner';

interface ViewRuntimeProps {
  viewId?: string;
  view?: View;
  className?: string;
}

export function ViewRuntime({ viewId, view: viewProp, className }: ViewRuntimeProps) {
  const [view, setView] = useState<View | null>(viewProp || null);
  const [loading, setLoading] = useState(!viewProp);
  const [active, setActive] = useState<string | undefined>(undefined);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!view) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted-foreground">
        View not found
      </div>
    );
  }

  if (view.tabs.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 border-2 border-dashed border-border rounded-lg m-4 text-sm text-muted-foreground">
        This view has no dashboards yet. Open the View Builder to add tabs.
      </div>
    );
  }

  return (
    <div className={className || 'flex flex-col h-full'}>
      <Tabs value={active} onValueChange={setActive} className="flex flex-col flex-1 min-h-0">
        <div className="px-3 pt-2 border-b">
          <TabsList className="bg-transparent p-0 h-auto gap-1">
            {view.tabs.map((tab) => (
              <TabsTrigger
                key={tab.tabId}
                value={tab.tabId}
                className="data-[state=active]:bg-muted text-xs px-3 py-1.5 rounded-md"
              >
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        <div className="flex-1 overflow-auto">
          {view.tabs.map((tab) => (
            <TabsContent key={tab.tabId} value={tab.tabId} className="mt-0 p-4">
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

function ViewTabPanel({ tab }: ViewTabPanelProps) {
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
      <div className="flex items-center justify-center h-32">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
        Dashboard {tab.dashboardId} not available
      </div>
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
