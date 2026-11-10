import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  DndContext,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import { cn } from '@/lib/utils';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { EditorHeader, NameInput, SaveState } from '@/components/analytics/EditorHeader';
import { toast } from 'sonner';
import { viewService } from '@/services/viewService';
import type { View, ViewTab } from '@/lib/foundry/model';
import type { DashboardListItem } from '@/services/dashboardService';
import { DashboardPalette } from '@/components/views/DashboardPalette';
import { TabStrip } from '@/components/views/TabStrip';
import { TabInspector } from '@/components/views/TabInspector';
import { type DraftTab, tabsFromServer } from '@/components/views/ViewBuilderTypes';
import { DashboardSkeleton, ViewRuntime, ViewTabPanel } from '@/components/views/ViewRuntime';
import { ViewSolutionsPicker } from '@/components/views/ViewSolutionsPicker';

const LIBRARY = '/ai-analytics?tab=views';

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

  const [name, setName] = useState('New view');
  const [description, setDescription] = useState('');
  const [view, setView] = useState<View | null>(null);
  const [tabs, setTabs] = useState<DraftTab[]>([]);
  const [removedServerTabIds, setRemovedServerTabIds] = useState<string[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | undefined>();
  const [loading, setLoading] = useState(!!viewId);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);

  const load = useCallback(() => {
    if (!viewId) return;
    setLoading(true);
    setLoadFailed(false);
    viewService
      .get(viewId)
      .then((v) => {
        setView(v);
        setName(v.name);
        setDescription(v.description || '');
        setTabs(tabsFromServer(v.tabs));
        setActiveTabId(v.defaultTabId || v.tabs[0]?.tabId);
      })
      .catch(() => {
        setLoadFailed(true);
        toast.error('Failed to load view');
      })
      .finally(() => setLoading(false));
  }, [viewId]);

  useEffect(() => {
    load();
  }, [load]);

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
    const blank = newDraftTab('New tab', '');
    setTabs((prev) => [...prev, blank]);
    setActiveTabId(blank.tabId);
  };

  /** Same result as dropping a dashboard on "Add tab", without dragging. */
  const handleAddFromPalette = (dashboard: DashboardListItem) => {
    const newTab = newDraftTab(dashboard.title, dashboard.uid);
    setTabs((prev) => [...prev, newTab]);
    setActiveTabId(newTab.tabId);
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

  const handleRenameTab = (tabId: string, label: string) => {
    setTabs((prev) => prev.map((t) => (t.tabId === tabId ? { ...t, label, isDirty: true } : t)));
  };

  const activeIndex = tabs.findIndex((t) => t.tabId === activeTabId);
  const handleMoveActive = (direction: -1 | 1) => {
    const target = activeIndex + direction;
    if (activeIndex < 0 || target < 0 || target >= tabs.length) return;
    const ids = tabs.map((t) => t.tabId);
    [ids[activeIndex], ids[target]] = [ids[target], ids[activeIndex]];
    handleReorder(ids);
  };

  // Live preview of the selected tab. A new tab or dashboard shows at once;
  // typing a time range waits until the typing stops. The label is left out
  // on purpose, so renaming a tab does not reload its dashboard.
  const [previewTab, setPreviewTab] = useState<ViewTab | null>(null);
  const previewKey = useRef('');
  const activeFrom = activeTab?.timeOverride?.from;
  const activeTo = activeTab?.timeOverride?.to;
  useEffect(() => {
    if (!activeTab?.dashboardId) {
      previewKey.current = '';
      setPreviewTab(null);
      return;
    }
    const key = `${activeTab.tabId}|${activeTab.dashboardId}`;
    const next: ViewTab = {
      tabId: activeTab.tabId,
      order: 0,
      label: activeTab.label,
      dashboardId: activeTab.dashboardId,
      simulatorRefs: activeTab.simulatorRefs,
      timeOverride: activeTab.timeOverride,
    };
    const delay = previewKey.current === key ? 600 : 0;
    const handle = window.setTimeout(() => {
      previewKey.current = key;
      setPreviewTab(next);
    }, delay);
    return () => window.clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab?.tabId, activeTab?.dashboardId, activeFrom, activeTo]);

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

  // Whole-view preview: rebuilt only when what it shows changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const previewView = useMemo(() => (previewing ? buildPreviewView() : null), [previewing, view, name, description, tabs]);

  const serverOrder = view ? [...view.tabs].sort((a, b) => a.order - b.order).map((t) => t.tabId) : [];
  const dirty =
    !view ||
    name !== view.name ||
    description !== (view.description || '') ||
    removedServerTabIds.length > 0 ||
    tabs.some((t) => t.isNew || t.isDirty) ||
    tabs.map((t) => t.tabId).join('|') !== serverOrder.join('|');
  const missingDashboard = tabs.filter((t) => !t.dashboardId).length;

  if (loading || loadFailed) {
    return (
      <Layout>
        <div className="flex flex-col">
          <EditorHeader
            backLabel="AI Analytics"
            onBack={() => navigate(LIBRARY)}
            title={loading ? <Skeleton className="h-7 w-56" /> : <h1 className="text-lg font-medium tracking-tight text-foreground">View</h1>}
          />
          <div className="p-4 sm:p-6">
            {loading ? (
              <div aria-busy="true" aria-label="Loading view">
                <div className="flex gap-5 border-b border-border pb-3">
                  <Skeleton className="h-4 w-28" />
                  <Skeleton className="h-4 w-24" />
                </div>
                <DashboardSkeleton className="mt-4" />
              </div>
            ) : (
              <InlineError onRetry={load}>
                This view could not be loaded. It may have been deleted, or the server did not answer.
              </InlineError>
            )}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex flex-col">
        <EditorHeader
          backLabel="AI Analytics"
          onBack={() => navigate(LIBRARY)}
          title={
            <NameInput
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="View name"
              aria-label="View name"
            />
          }
          meta={
            <SaveState
              state={saving ? 'saving' : !view ? 'new' : dirty ? 'dirty' : 'saved'}
              detail={
                missingDashboard > 0
                  ? `${missingDashboard} ${missingDashboard === 1 ? 'tab needs' : 'tabs need'} a dashboard`
                  : `${tabs.length} ${tabs.length === 1 ? 'tab' : 'tabs'}`
              }
            />
          }
          actions={
            <>
              <ViewSolutionsPicker viewId={view?.viewId} />
              <Button variant="outline" size="sm" onClick={() => setPreviewing((p) => !p)}>
                <Icon name={previewing ? 'edit' : 'eye'} className="h-3.5 w-3.5" />
                {previewing ? 'Back to editing' : 'Preview view'}
              </Button>
              <Button size="sm" variant={tabs.length === 0 ? 'outline' : 'default'} onClick={handleSave} disabled={saving}>
                {saving && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
                {saving ? 'Saving' : 'Save view'}
              </Button>
            </>
          }
        >
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Add a short description (optional)"
            aria-label="Description"
            className="-ml-2 mt-1 h-8 max-w-2xl border-transparent bg-transparent px-2 text-sm text-muted-foreground shadow-none hover:border-border focus:border-border-strong focus:bg-card focus:text-foreground"
          />
        </EditorHeader>

        {previewing && previewView ? (
          <div className="min-h-0 flex-1">
            <ViewRuntime view={previewView} />
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            onDragEnd={handlePaletteDrop}
            accessibility={{
              screenReaderInstructions: { draggable: 'Use the add button next to a dashboard to add it as a tab without dragging.' },
              announcements: {
                onDragStart: () => 'Picked up a dashboard.',
                onDragOver: ({ over }) => (over ? 'Over a place where the dashboard can be dropped.' : 'Not over a drop place.'),
                onDragEnd: ({ over }) => (over ? 'Dashboard dropped.' : 'Dashboard put back.'),
                onDragCancel: () => 'Cancelled.',
              },
            }}
          >
            <p className="border-b border-border bg-surface-2/60 px-4 py-2 text-xs text-muted-foreground lg:hidden">
              Building a view works best on a larger screen. Here you can still add tabs and choose a dashboard for each one in the tab settings.
            </p>
            <div className="lg:grid lg:h-pane lg:grid-cols-[272px_minmax(0,1fr)] lg:overflow-hidden">
              <DashboardPalette
                className="hidden lg:flex"
                onAdd={handleAddFromPalette}
                usedIds={tabs.map((t) => t.dashboardId).filter(Boolean)}
              />
              <div className="scroll-thin flex min-w-0 flex-col lg:min-h-0 lg:overflow-y-auto">
                <TabStrip
                  tabs={tabs}
                  activeTabId={activeTabId}
                  onSelect={setActiveTabId}
                  onRemove={handleRemoveTab}
                  onReorder={handleReorder}
                  onAddBlankTab={handleAddBlankTab}
                  onRename={handleRenameTab}
                />
                {activeTab ? (
                  <>
                    <TabInspector
                      tab={activeTab}
                      onChange={handleTabChange}
                      onRemove={() => handleRemoveTab(activeTab.tabId)}
                      onMove={handleMoveActive}
                      canMoveLeft={activeIndex > 0}
                      canMoveRight={activeIndex >= 0 && activeIndex < tabs.length - 1}
                    />
                    <ActiveTabDropZone>
                      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                        <h2 className="text-sm font-medium text-foreground">Preview</h2>
                        <p className="text-xs text-muted-foreground">
                          How this tab looks to people, read only.
                          <span className="hidden lg:inline"> Drop a dashboard here to use it for this tab.</span>
                        </p>
                      </div>
                      {activeTab.dashboardId ? (
                        previewTab && previewTab.tabId === activeTab.tabId && previewTab.dashboardId === activeTab.dashboardId ? (
                          <ViewTabPanel key={`${previewTab.tabId}|${previewTab.dashboardId}`} tab={previewTab} />
                        ) : (
                          <DashboardSkeleton />
                        )
                      ) : (
                        <EmptyState
                          icon="dashboard"
                          title="Choose a dashboard for this tab"
                          description="Pick one under Dashboard in the tab settings. On a larger screen you can also drag one in from the list."
                        />
                      )}
                    </ActiveTabDropZone>
                  </>
                ) : (
                  <EmptyDropZone onAdd={handleAddBlankTab} hasTabs={tabs.length > 0} />
                )}
              </div>
            </div>
          </DndContext>
        )}
      </div>
    </Layout>
  );
}

function EmptyDropZone({ onAdd, hasTabs }: { onAdd: () => void; hasTabs: boolean }) {
  const { setNodeRef, isOver } = useDroppable({ id: 'view-builder-empty-area' });
  return (
    <div ref={setNodeRef} className="p-4 sm:p-6">
      <EmptyState
        icon="layers"
        title={isOver ? 'Drop to add it as a tab' : hasTabs ? 'Select a tab to edit it' : 'Add the first tab'}
        description="A view is a set of tabs, and each tab shows one dashboard. Attach the view to a solution and it appears in that solution's side menu (Monitor, Diagnose, Predict, Outcomes)."
        action={
          <Button onClick={onAdd}>
            <Icon name="plus" className="h-3.5 w-3.5" /> Add a tab
          </Button>
        }
        className={cn('mx-auto mt-4 max-w-2xl py-16 transition-colors', isOver && 'border-brand/60 bg-brand/5')}
      />
    </div>
  );
}

function ActiveTabDropZone({ children }: { children: React.ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id: 'view-builder-active-tab-area' });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        'flex-1 p-3 transition-colors sm:p-4',
        isOver && 'bg-brand/5 ring-1 ring-inset ring-brand/50',
      )}
    >
      {children}
    </div>
  );
}
