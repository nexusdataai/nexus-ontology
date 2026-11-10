import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { EditorHeader, NameInput, SaveState } from '@/components/analytics/EditorHeader';
import type { DashboardModel, PanelModel } from '@/lib/dashboard/model';
import { createDefaultDashboard, createDefaultPanel, getNextPanelId } from '@/lib/dashboard/model';
import type { TimeRange } from '@/lib/dashboard/types';
import { DashboardGrid } from '@/lib/dashboard/components/DashboardGrid';
import { AddPanelDialog } from '@/lib/dashboard/components/AddPanelWidget';
import { TimeRangePicker } from '@/lib/dashboard/components/TimeRangePicker';
import { PanelEditor } from '@/lib/dashboard/panel-editor/PanelEditor';
import { RefreshPicker } from '@/lib/dashboard/components/RefreshPicker';
import { VariableControls } from '@/lib/dashboard/components/VariableControls';
import { dashboardService } from '@/services/dashboardService';

const LIBRARY = '/ai-analytics?tab=dashboards';

/** What "saved" means for the unsaved-changes indicator: the dashboard and its time range. */
const snapshot = (d: DashboardModel, t: TimeRange) => JSON.stringify({ d, t });

export default function DashboardBuilderPage() {
  const { uid } = useParams<{ uid: string }>();
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState<DashboardModel>(() => createDefaultDashboard({ title: 'New dashboard' }));
  const [loading, setLoading] = useState(!!uid);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingPanelId, setEditingPanelId] = useState<number | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [timeRange, setTimeRange] = useState<TimeRange>({ from: 'now-6h', to: 'now' });
  const [refreshInterval, setRefreshInterval] = useState('');
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});

  // Unsaved-changes tracking. Until the person first touches the editor, the
  // baseline follows the state, so the grid tidying its layout on first paint
  // does not show up as an edit.
  const [baseline, setBaseline] = useState(() => snapshot(dashboard, timeRange));
  const touched = useRef(false);
  const current = snapshot(dashboard, timeRange);
  useEffect(() => {
    if (!touched.current) setBaseline(current);
  }, [current]);
  const markTouched = () => { touched.current = true; };

  const load = useCallback(() => {
    if (uid && !dashboard.uid) {
      setLoading(true);
      setLoadFailed(false);
      dashboardService.get(uid).then((d) => {
        touched.current = false;
        setDashboard(d);
        if (d.time) setTimeRange(d.time);
      }).catch(() => {
        setLoadFailed(true);
        toast.error('Failed to load dashboard');
      }).finally(() => setLoading(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uid, dashboard.uid]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uid]);

  const handleAddPanel = useCallback((panelType: string) => {
    const newPanel = { ...createDefaultPanel(panelType, dashboard.panels), title: 'New panel' };
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
        touched.current = false;
        setDashboard(updated);
        setBaseline(snapshot(updated, timeRange));
        toast.success('Dashboard saved');
      } else {
        const created = await dashboardService.create(payload);
        touched.current = false;
        setDashboard(created);
        setBaseline(snapshot(created, timeRange));
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
  const panels = dashboard.panels ?? [];
  const variables = dashboard.variables ?? [];
  const isNew = !dashboard.uid;
  const dirty = current !== baseline;
  const empty = panels.length === 0;

  if (loading || loadFailed) {
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

  return (
    <Layout>
      <div className="flex flex-col" onPointerDownCapture={markTouched} onKeyDownCapture={markTouched}>
        <EditorHeader
          backLabel="AI Analytics"
          onBack={() => navigate(LIBRARY)}
          title={
            <NameInput
              value={dashboard.title}
              onChange={(e) => setDashboard((prev) => ({ ...prev, title: e.target.value }))}
              placeholder="Dashboard name"
              aria-label="Dashboard name"
            />
          }
          meta={
            <SaveState
              state={saving ? 'saving' : isNew ? 'new' : dirty ? 'dirty' : 'saved'}
              detail={dashboard.version > 0 ? `version ${dashboard.version}` : undefined}
            />
          }
          actions={
            <>
              <TimeRangePicker value={timeRange} onChange={setTimeRange} />
              <RefreshPicker value={refreshInterval} onChange={setRefreshInterval} />
              <Button variant="outline" size="sm" onClick={() => setAddOpen(true)}>
                <Icon name="plus" className="h-3.5 w-3.5" /> Add panel
              </Button>
              <Button size="sm" variant={empty ? 'outline' : 'default'} onClick={handleSave} disabled={saving}>
                {saving && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
                {saving ? 'Saving' : 'Save dashboard'}
              </Button>
            </>
          }
        >
          {variables.length > 0 && (
            <div className="mt-3">
              <VariableControls variables={variables} values={variableValues} onChange={setVariableValues} />
            </div>
          )}
        </EditorHeader>

        <p className="border-b border-border bg-surface-2/60 px-4 py-2 text-xs text-muted-foreground sm:hidden">
          Panels are stacked on a phone. Moving and resizing them works best on a larger screen.
        </p>

        <div className="p-3 sm:p-4">
          {empty ? (
            <EmptyState
              icon="dashboard"
              title="Start with a panel"
              description="A panel is one chart, number or table. It reads an entity from the virtual data layer: you choose the fields, filters and how many rows. Add as many as you need, then drag and resize them."
              action={
                <Button onClick={() => setAddOpen(true)}>
                  <Icon name="plus" className="h-3.5 w-3.5" /> Add the first panel
                </Button>
              }
              className="mx-auto mt-6 max-w-2xl py-16"
            />
          ) : (
            <DashboardGrid
              panels={panels}
              timeRange={timeRange}
              isEditing={true}
              onLayoutChange={handleLayoutChange}
              onEditPanel={handleEditPanel}
              onDuplicatePanel={handleDuplicatePanel}
              onRemovePanel={handleRemovePanel}
            />
          )}
        </div>

        <AddPanelDialog open={addOpen} onOpenChange={setAddOpen} onSelect={handleAddPanel} />

        <PanelEditor
          panel={editingPanel}
          open={editingPanelId !== null && !!editingPanel}
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
          onSave={handlePanelSave}
          onCancel={() => setEditingPanelId(null)}
        />
      </div>
    </Layout>
  );
}
