import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Save, ArrowLeft, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import type { DashboardModel, PanelModel } from '@/lib/dashboard/model';
import { createDefaultDashboard, createDefaultPanel, getNextPanelId } from '@/lib/dashboard/model';
import type { TimeRange } from '@/lib/dashboard/types';
import { DashboardGrid } from '@/lib/dashboard/components/DashboardGrid';
import { AddPanelWidget } from '@/lib/dashboard/components/AddPanelWidget';
import { TimeRangePicker } from '@/lib/dashboard/components/TimeRangePicker';
import { PanelEditor } from '@/lib/dashboard/panel-editor/PanelEditor';
import { RefreshPicker } from '@/lib/dashboard/components/RefreshPicker';
import { VariableControls } from '@/lib/dashboard/components/VariableControls';
import { dashboardService } from '@/services/dashboardService';

export default function DashboardBuilderPage() {
  const { uid } = useParams<{ uid: string }>();
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState<DashboardModel>(createDefaultDashboard());
  const [saving, setSaving] = useState(false);
  const [editingPanelId, setEditingPanelId] = useState<number | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>({ from: 'now-6h', to: 'now' });
  const [refreshInterval, setRefreshInterval] = useState('');
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});

  useEffect(() => {
    if (uid && !dashboard.uid) {
      dashboardService.get(uid).then((d) => {
        setDashboard(d);
        if (d.time) setTimeRange(d.time);
      }).catch(() => {
        toast.error('Failed to load dashboard');
      });
    }
  }, [uid]);

  const handleAddPanel = useCallback((panelType: string) => {
    const newPanel = createDefaultPanel(panelType, dashboard.panels);
    const updated = { ...dashboard, panels: [...dashboard.panels, newPanel] };
    setDashboard(updated);
    setEditingPanelId(newPanel.id);
  }, [dashboard]);

  const handleLayoutChange = useCallback((panels: PanelModel[]) => {
    setDashboard((prev) => ({ ...prev, panels }));
  }, []);

  const handleEditPanel = useCallback((panelId: number) => {
    setEditingPanelId(panelId);
  }, []);

  const handleDuplicatePanel = useCallback((panelId: number) => {
    const source = dashboard.panels.find((p) => p.id === panelId);
    if (!source) return;
    const newId = getNextPanelId(dashboard.panels);
    const maxY = dashboard.panels.reduce((max, p) => Math.max(max, p.gridPos.y + p.gridPos.h), 0);
    const dup: PanelModel = {
      ...JSON.parse(JSON.stringify(source)),
      id: newId,
      title: `${source.title} (copy)`,
      gridPos: { ...source.gridPos, y: maxY },
    };
    setDashboard((prev) => ({ ...prev, panels: [...prev.panels, dup] }));
  }, [dashboard]);

  const handleRemovePanel = useCallback((panelId: number) => {
    setDashboard((prev) => ({
      ...prev,
      panels: prev.panels.filter((p) => p.id !== panelId),
    }));
    if (editingPanelId === panelId) setEditingPanelId(null);
  }, [editingPanelId]);

  const handlePanelSave = useCallback((panel: PanelModel) => {
    setDashboard((prev) => ({
      ...prev,
      panels: prev.panels.map((p) => (p.id === panel.id ? panel : p)),
    }));
    setEditingPanelId(null);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = { ...dashboard, time: timeRange };
      if (dashboard.uid) {
        const updated = await dashboardService.update(dashboard.uid, payload);
        setDashboard(updated);
        toast.success('Dashboard saved');
      } else {
        const created = await dashboardService.create(payload);
        setDashboard(created);
        navigate(`/dashboard/builder/${created.uid}`, { replace: true });
        toast.success('Dashboard created');
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const editingPanel = dashboard.panels.find((p) => p.id === editingPanelId) || null;
  const isEditing = editingPanelId !== null;

  if (isEditing && editingPanel) {
    return (
      <Layout>
        <div className="flex flex-col h-full">
          {/* Toolbar for edit mode */}
          <div className="flex items-center justify-between gap-3 px-4 py-2 border-b bg-background/95 backdrop-blur-sm sticky top-0 z-20 flex-shrink-0">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="h-7" onClick={() => setEditingPanelId(null)}>
                <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Back to dashboard
              </Button>
              <span className="text-xs text-muted-foreground">/ Editing: {editingPanel.title}</span>
            </div>
            <div className="flex items-center gap-2">
              <TimeRangePicker value={timeRange} onChange={setTimeRange} />
            </div>
          </div>

          {/* Full-screen panel editor: preview top + options bottom */}
          <PanelEditor
            panel={editingPanel}
            open={true}
            timeRange={timeRange}
            onSave={handlePanelSave}
            onCancel={() => setEditingPanelId(null)}
          />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex flex-col h-full">
        {/* Top toolbar */}
        <div className="flex items-center justify-between gap-3 p-3 border-b bg-background/95 backdrop-blur-sm sticky top-0 z-20">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <Button variant="ghost" size="sm" className="h-8" onClick={() => navigate('/dashboards')}>
              <ArrowLeft className="h-3.5 w-3.5" />
            </Button>
            <Input
              className="h-8 text-sm font-medium max-w-xs border-transparent hover:border-border focus:border-border transition-colors"
              value={dashboard.title}
              onChange={(e) => setDashboard((prev) => ({ ...prev, title: e.target.value }))}
              placeholder="Dashboard title"
            />
            {dashboard.version > 0 && (
              <Badge variant="outline" className="text-xs">v{dashboard.version}</Badge>
            )}
          </div>

          <div className="flex items-center gap-2">
            <TimeRangePicker value={timeRange} onChange={setTimeRange} />
            <RefreshPicker value={refreshInterval} onChange={setRefreshInterval} />
            <AddPanelWidget onSelect={handleAddPanel} />
            <Button size="sm" className="h-8" onClick={handleSave} disabled={saving}>
              {saving ? <RefreshCw className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}
              Save
            </Button>
          </div>
        </div>

        {/* Variable controls */}
        {dashboard.variables.length > 0 && (
          <div className="px-4 pt-2 border-b">
            <VariableControls variables={dashboard.variables} values={variableValues} onChange={setVariableValues} />
          </div>
        )}

        {/* Grid canvas */}
        <div className="flex-1 overflow-auto p-4">
          <DashboardGrid
            panels={dashboard.panels}
            timeRange={timeRange}
            isEditing={true}
            onLayoutChange={handleLayoutChange}
            onEditPanel={handleEditPanel}
            onDuplicatePanel={handleDuplicatePanel}
            onRemovePanel={handleRemovePanel}
          />
        </div>
      </div>
    </Layout>
  );
}
