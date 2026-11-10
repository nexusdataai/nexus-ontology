import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  DndContext,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import { ArrowLeft, Loader2, Save, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { viewService } from '@/services/viewService';
import type { View } from '@/lib/foundry/model';
import type { DashboardListItem } from '@/services/dashboardService';
import { DashboardPalette } from '@/components/views/DashboardPalette';
import { TabStrip } from '@/components/views/TabStrip';
import { TabInspector } from '@/components/views/TabInspector';
import { type DraftTab, tabsFromServer } from '@/components/views/ViewBuilderTypes';
import { ViewRuntime } from '@/components/views/ViewRuntime';
import { ViewSolutionsPicker } from '@/components/views/ViewSolutionsPicker';

function newDraftTab(label: string, dashboardId: string): DraftTab {
  return {
    tabId: `new-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
    label,
    dashboardId,
    simulatorRefs: [],
    timeOverride: null,
    isNew: true,
    isDirty: true,
  };
}

export default function ViewBuilderPage() {
  const { viewId } = useParams<{ viewId: string }>();
  const navigate = useNavigate();

  const [name, setName] = useState('New View');
  const [description, setDescription] = useState('');
  const [view, setView] = useState<View | null>(null);
  const [tabs, setTabs] = useState<DraftTab[]>([]);
  const [removedServerTabIds, setRemovedServerTabIds] = useState<string[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);

  useEffect(() => {
    if (!viewId) return;
    setLoading(true);
    viewService
      .get(viewId)
      .then((v) => {
        setView(v);
        setName(v.name);
        setDescription(v.description || '');
        setTabs(tabsFromServer(v.tabs));
        setActiveTabId(v.defaultTabId || v.tabs[0]?.tabId);
      })
      .catch(() => toast.error('Failed to load view'))
      .finally(() => setLoading(false));
  }, [viewId]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const activeTab = useMemo(
    () => tabs.find((t) => t.tabId === activeTabId) || null,
    [tabs, activeTabId]
  );

  const handlePaletteDrop = (event: DragEndEvent) => {
    const overId = event.over?.id;
    if (!overId) return;
    const dragData = event.active.data.current as
      | { dashboard?: DashboardListItem }
      | undefined;
    if (!dragData?.dashboard) return;
    const dashboard = dragData.dashboard;

    // Drop on "+ Add tab" button or the empty central area: always create a new tab.
    if (overId === 'tabstrip-new-tab' || overId === 'view-builder-empty-area') {
      const newTab = newDraftTab(dashboard.title, dashboard.uid);
      setTabs((prev) => [...prev, newTab]);
      setActiveTabId(newTab.tabId);
      return;
    }

    // Drop on the active-tab card: rebind the active tab to this dashboard.
    if (overId === 'view-builder-active-tab-area' && activeTabId) {
      setTabs((prev) =>
        prev.map((t) =>
          t.tabId === activeTabId
            ? {
                ...t,
                dashboardId: dashboard.uid,
                label: t.label || dashboard.title,
                isDirty: true,
              }
            : t,
        ),
      );
      return;
    }

    if (typeof overId === 'string' && overId.startsWith('tab:')) {
      const targetId = overId.slice('tab:'.length);
      setTabs((prev) =>
        prev.map((t) =>
          t.tabId === targetId
            ? { ...t, dashboardId: dashboard.uid, label: t.label || dashboard.title, isDirty: true }
            : t
        )
      );
      setActiveTabId(targetId);
    }
  };

  const handleAddBlankTab = () => {
    const blank = newDraftTab('New Tab', '');
    setTabs((prev) => [...prev, blank]);
    setActiveTabId(blank.tabId);
  };

  const handleRemoveTab = (tabId: string) => {
    const removing = tabs.find((t) => t.tabId === tabId);
    if (removing && !removing.isNew) {
      setRemovedServerTabIds((prev) => [...prev, tabId]);
    }
    setTabs((prev) => prev.filter((t) => t.tabId !== tabId));
    if (activeTabId === tabId) {
      const remaining = tabs.filter((t) => t.tabId !== tabId);
      setActiveTabId(remaining[0]?.tabId);
    }
  };

  const handleReorder = (orderedIds: string[]) => {
    setTabs((prev) => orderedIds.map((id) => prev.find((t) => t.tabId === id)!).filter(Boolean));
  };

  const handleTabChange = (next: DraftTab) => {
    setTabs((prev) => prev.map((t) => (t.tabId === next.tabId ? next : t)));
  };

  const buildPreviewView = (): View => {
    return {
      viewId: view?.viewId || 'preview',
      name,
      description,
      tags: view?.tags || [],
      defaultTabId: tabs[0]?.tabId,
      version: view?.version || 0,
      createdAt: view?.createdAt || '',
      updatedAt: new Date().toISOString(),
      createdBy: view?.createdBy || '',
      tabs: tabs.map((t, i) => ({
        tabId: t.tabId,
        order: i,
        label: t.label,
        icon: t.icon,
        dashboardId: t.dashboardId,
        simulatorRefs: t.simulatorRefs,
        timeOverride: t.timeOverride,
      })),
    };
  };

  const handleSave = async () => {
    if (!name.trim()) {
      toast.error('Please give the view a name');
      return;
    }
    if (tabs.some((t) => !t.dashboardId)) {
      toast.error('Every tab must reference a dashboard');
      return;
    }
    setSaving(true);
    try {
      let current = view;
      if (!current) {
        current = await viewService.create({ name, description });
      } else {
        current = await viewService.update(current.viewId, {
          name,
          description,
          version: current.version,
        });
      }

      for (const removedId of removedServerTabIds) {
        try {
          current = await viewService.removeTab(current.viewId, removedId);
        } catch (e) {
          console.warn('Failed to remove tab', removedId, e);
        }
      }

      for (const tab of tabs) {
        if (tab.isNew) {
          if (!tab.dashboardId) continue;
          current = await viewService.addTab(current.viewId, {
            label: tab.label,
            dashboardId: tab.dashboardId,
            simulatorRefs: tab.simulatorRefs,
            timeOverride: tab.timeOverride,
          });
        } else if (tab.isDirty) {
          current = await viewService.updateTab(current.viewId, tab.tabId, {
            label: tab.label,
            dashboardId: tab.dashboardId,
            simulatorRefs: tab.simulatorRefs,
            timeOverride: tab.timeOverride,
          });
        }
      }

      const finalIds = current.tabs
        .sort((a, b) => a.order - b.order)
        .map((t) => t.tabId);
      const labelToServerId = new Map<string, string>();
      current.tabs.forEach((t) => labelToServerId.set(`${t.label}::${t.dashboardId}`, t.tabId));
      const desiredIds = tabs
        .map((t) => {
          if (!t.isNew) return t.tabId;
          return labelToServerId.get(`${t.label}::${t.dashboardId}`);
        })
        .filter(Boolean) as string[];

      if (
        desiredIds.length === finalIds.length &&
        desiredIds.some((id, i) => id !== finalIds[i])
      ) {
        current = await viewService.reorderTabs(current.viewId, desiredIds);
      }

      setView(current);
      setName(current.name);
      setDescription(current.description || '');
      setTabs(tabsFromServer(current.tabs));
      setRemovedServerTabIds([]);
      setActiveTabId((prev) => current!.tabs.find((t) => t.tabId === prev)?.tabId || current!.tabs[0]?.tabId);
      toast.success('View saved');
      if (!viewId && current.viewId) {
        navigate(`/views/builder/${current.viewId}`, { replace: true });
      }
    } catch (e: any) {
      toast.error(e?.message || 'Save failed');
    } finally {
      setSaving(false);
    }
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

  return (
    <Layout>
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between gap-3 p-3 border-b bg-background/95 backdrop-blur-sm sticky top-0 z-20">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <Button variant="ghost" size="sm" className="h-8" onClick={() => navigate('/views')}>
              <ArrowLeft className="h-3.5 w-3.5" />
            </Button>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="View name"
              className="h-8 text-sm font-medium max-w-xs"
            />
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optional)"
              className="h-8 min-h-8 text-xs flex-1 max-w-md py-1.5 resize-none"
            />
          </div>

          <div className="flex items-center gap-2">
            <ViewSolutionsPicker viewId={view?.viewId} />
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => setPreviewing((p) => !p)}
            >
              <Eye className="h-3.5 w-3.5 mr-1" />
              {previewing ? 'Edit' : 'Preview'}
            </Button>
            <Button size="sm" className="h-8" onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}
              Save
            </Button>
          </div>
        </div>

        {previewing ? (
          <div className="flex-1 min-h-0">
            <ViewRuntime view={buildPreviewView()} />
          </div>
        ) : (
          <DndContext sensors={sensors} onDragEnd={handlePaletteDrop}>
            <div className="flex-1 grid grid-cols-[260px_minmax(0,1fr)_320px] min-h-0">
              <DashboardPalette />
              <div className="flex flex-col min-w-0">
                <TabStrip
                  tabs={tabs}
                  activeTabId={activeTabId}
                  onSelect={setActiveTabId}
                  onRemove={handleRemoveTab}
                  onReorder={handleReorder}
                  onAddBlankTab={handleAddBlankTab}
                />
                <div className="flex-1 overflow-auto p-4">
                  {activeTab ? (
                    <ActiveTabDropZone>
                      <div className="text-xs text-muted-foreground mb-2">
                        Editing <span className="font-medium text-foreground">{activeTab.label}</span>
                        {activeTab.dashboardId ? (
                          <>
                            {' '}— bound to dashboard{' '}
                            <span className="font-mono text-xs">{activeTab.dashboardId}</span>
                          </>
                        ) : (
                          ' — drop a dashboard from the palette to bind one'
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Use the inspector on the right to configure this tab. Drop a dashboard here
                        to rebind, or switch to Preview to render the bound dashboard.
                      </p>
                    </ActiveTabDropZone>
                  ) : (
                    <EmptyDropZone />
                  )}
                </div>
              </div>
              <TabInspector
                tab={activeTab}
                onChange={handleTabChange}
                onRemove={() => activeTab && handleRemoveTab(activeTab.tabId)}
              />
            </div>
          </DndContext>
        )}
      </div>
    </Layout>
  );
}

function EmptyDropZone() {
  const { setNodeRef, isOver } = useDroppable({ id: 'view-builder-empty-area' });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        'border-2 border-dashed rounded-lg p-12 text-center text-sm transition-colors',
        isOver
          ? 'border-primary bg-primary/5 text-primary'
          : 'border-border text-muted-foreground',
      )}
    >
      No tabs yet. Drag a dashboard from the left into this area or the tab strip,
      or click "Add tab" to start.
    </div>
  );
}

function ActiveTabDropZone({ children }: { children: React.ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id: 'view-builder-active-tab-area' });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        'border rounded-lg p-4 bg-card transition-colors',
        isOver && 'ring-1 ring-primary border-primary',
      )}
    >
      {children}
    </div>
  );
}
