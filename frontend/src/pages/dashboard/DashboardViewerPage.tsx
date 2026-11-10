import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
import { EditorHeader } from '@/components/analytics/EditorHeader';
import type { DashboardModel } from '@/lib/dashboard/model';
import type { TimeRange } from '@/lib/dashboard/types';
import { DashboardGrid } from '@/lib/dashboard/components/DashboardGrid';
import { TimeRangePicker } from '@/lib/dashboard/components/TimeRangePicker';
import { RefreshPicker } from '@/lib/dashboard/components/RefreshPicker';
import { VariableControls } from '@/lib/dashboard/components/VariableControls';
import { dashboardService } from '@/services/dashboardService';

const LIBRARY = '/ai-analytics?tab=dashboards';

export default function DashboardViewerPage() {
  const { uid } = useParams<{ uid: string }>();
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState<DashboardModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<TimeRange>({ from: 'now-6h', to: 'now' });
  const [refreshInterval, setRefreshInterval] = useState('');
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    if (!uid) return;
    setLoading(true);
    dashboardService
      .get(uid)
      .then((d) => {
        setDashboard(d);
        if (d.time) setTimeRange(d.time);
      })
      .catch(() => toast.error('Failed to load dashboard'))
      .finally(() => setLoading(false));
  }, [uid]);

  useEffect(() => {
    load();
  }, [load]);

  const handleExport = () => {
    if (!dashboard) return;
    const blob = new Blob([JSON.stringify(dashboard, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${dashboard.title.replace(/\s+/g, '-').toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Dashboard exported');
  };

  if (loading || !dashboard) {
    return (
      <Layout>
        <div className="flex flex-col">
          <EditorHeader
            backLabel="AI Analytics"
            onBack={() => navigate(LIBRARY)}
            title={loading ? <Skeleton className="h-7 w-56" /> : <h1 className="text-lg font-medium tracking-tight text-foreground">Dashboard</h1>}
          />
          <div className="p-4 sm:p-6">
            {loading ? (
              <div className="grid gap-2 md:grid-cols-2" aria-busy="true" aria-label="Loading dashboard">
                {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-56 rounded-xl" />)}
              </div>
            ) : (
              <InlineError onRetry={load}>
                This dashboard could not be loaded. It may have been deleted, or the server did not answer.
              </InlineError>
            )}
          </div>
        </div>
      </Layout>
    );
  }

  const panels = dashboard.panels ?? [];
  const variables = dashboard.variables ?? [];

  return (
    <Layout>
      <div className="flex flex-col">
        <EditorHeader
          backLabel="AI Analytics"
          onBack={() => navigate(LIBRARY)}
          title={<h1 className="min-w-0 truncate text-lg font-medium tracking-tight text-foreground">{dashboard.title}</h1>}
          meta={
            <span className="num shrink-0 whitespace-nowrap text-xs text-muted-foreground">
              {panels.length} {panels.length === 1 ? 'panel' : 'panels'}
              {dashboard.version > 0 && ` · version ${dashboard.version}`}
            </span>
          }
          actions={
            <>
              <TimeRangePicker value={timeRange} onChange={setTimeRange} />
              <RefreshPicker value={refreshInterval} onChange={setRefreshInterval} />
              <Button variant="outline" size="sm" onClick={handleExport}>
                <Icon name="download" className="h-3.5 w-3.5" /> Export
              </Button>
              <Button size="sm" onClick={() => navigate(`/dashboard/builder/${uid}`)}>
                <Icon name="edit" className="h-3.5 w-3.5" /> Edit dashboard
              </Button>
            </>
          }
        >
          {dashboard.description && <p className="mt-1.5 max-w-3xl text-sm text-muted-foreground">{dashboard.description}</p>}
          {variables.length > 0 && (
            <div className="mt-3">
              <VariableControls variables={variables} values={variableValues} onChange={setVariableValues} />
            </div>
          )}
        </EditorHeader>

        <div className="p-3 sm:p-4">
          <DashboardGrid
            panels={panels}
            timeRange={timeRange}
            isEditing={false}
            onLayoutChange={() => {}}
            onEditPanel={() => {}}
            onDuplicatePanel={() => {}}
            onRemovePanel={() => {}}
          />
        </div>
      </div>
    </Layout>
  );
}
