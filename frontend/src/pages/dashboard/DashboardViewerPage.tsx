import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Pencil, ArrowLeft, RefreshCw, Loader2, Download } from 'lucide-react';
import { toast } from 'sonner';
import type { DashboardModel } from '@/lib/dashboard/model';
import type { TimeRange } from '@/lib/dashboard/types';
import { DashboardGrid } from '@/lib/dashboard/components/DashboardGrid';
import { TimeRangePicker } from '@/lib/dashboard/components/TimeRangePicker';
import { RefreshPicker } from '@/lib/dashboard/components/RefreshPicker';
import { VariableControls } from '@/lib/dashboard/components/VariableControls';
import { dashboardService } from '@/services/dashboardService';

export default function DashboardViewerPage() {
  const { uid } = useParams<{ uid: string }>();
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState<DashboardModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<TimeRange>({ from: 'now-6h', to: 'now' });
  const [refreshInterval, setRefreshInterval] = useState('');
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});

  useEffect(() => {
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

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      </Layout>
    );
  }

  if (!dashboard) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center h-64">
          <p className="text-sm text-muted-foreground mb-3">Dashboard not found</p>
          <Button variant="outline" size="sm" onClick={() => navigate('/dashboards')}>
            <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Back to dashboards
          </Button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex flex-col h-full">
        <div className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b border-border bg-background/95 px-3 py-2.5 backdrop-blur-sm sm:px-5">
          <div className="flex items-center gap-2 min-w-0">
            <Button variant="ghost" size="sm" className="h-8" onClick={() => navigate('/dashboards')}>
              <ArrowLeft className="h-3.5 w-3.5" />
            </Button>
            <h1 className="text-sm font-medium truncate">{dashboard.title}</h1>
            {dashboard.version > 0 && (
              <Badge variant="outline" className="text-xs">v{dashboard.version}</Badge>
            )}
          </div>

          <div className="scrollbar-hide flex max-w-full items-center gap-2 overflow-x-auto">
            <TimeRangePicker value={timeRange} onChange={setTimeRange} />
            <RefreshPicker value={refreshInterval} onChange={setRefreshInterval} />
            <Button variant="outline" size="sm" className="h-8" onClick={handleExport}>
              <Download className="h-3.5 w-3.5 mr-1" /> Export
            </Button>
            <Button variant="outline" size="sm" className="h-8" onClick={() => navigate(`/dashboard/builder/${uid}`)}>
              <Pencil className="h-3.5 w-3.5 mr-1" /> Edit
            </Button>
          </div>
        </div>

        {(dashboard.variables ?? []).length > 0 && (
          <div className="px-4 pt-2 border-b">
            <VariableControls variables={dashboard.variables ?? []} values={variableValues} onChange={setVariableValues} />
          </div>
        )}

        <div className="flex-1 overflow-auto p-4">
          <DashboardGrid
            panels={dashboard.panels ?? []}
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
