/**
 * Journey builder: draw a journey as a graph of steps.
 *
 * Editor layout: a sticky header (name, state, Suggest / Validate / Test run,
 * Save), the steps to add on the left (searchable, grouped), the flow on a
 * dotted canvas in the middle, and an inspector on the right with the selected
 * step's properties, the journey settings and the last test run. Below lg the
 * step list opens in a sheet; below xl the inspector does.
 */
import { confirmDialog } from '@/components/ds/confirm';
import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Switch } from './ui/switch';
import { Skeleton } from './ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { CodeBlock, DetailSheet, Field, InlineError, KeyValues, SearchInput, StatusPill, SubHeading } from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { useIsWide } from '@/components/journeys/studio/StepPipeline';
import { sentenceCase, systemsIn } from '@/components/journeys/studio/format';
import { apiClient } from '@/services/apiClient';
import {
  reactToolsDiagnosticsService, type RegistryToolRow,
} from '@/services/reactToolsDiagnosticsService';
import { cn } from '@/lib/utils';
import { toast } from '@/hooks/use-toast';
import {
  JourneyGraphCanvas,
  type JourneyGraphCanvasHandle, type PendingConnection,
} from './journey-builder/JourneyGraphCanvas';
import { PendingStepCard } from './journey-builder/PendingStepCard';
import { RunResultsPanel } from './journey-builder/RunResultsPanel';
import { RunQueueInspector } from './journey-builder/RunQueueInspector';
import { ReadsFromDropdown } from './journey-builder/ReadsFromDropdown';
import { StageTabs } from './journey-builder/StageTabs';
import {
  toBuilderRequestMultiStage, applyValidationToNodes, topoOrderClient,
  defaultStage, newStage,
  type BuilderStageState,
  type BuilderTool, type BuilderValidationReport, type ToolOutputHints,
  type ToolRelationships, type BuilderNode, type ValidationIssue,
} from './journey-builder/builderState';

/** ``Untitled journey YYYY-MM-DD`` for first-render Save/Run-enabled state. */
function _defaultJourneyName(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `Untitled journey ${yyyy}-${mm}-${dd}`;
}

// ---------------------------------------------------------------------------
// Group labels (carried over from the legacy palette)
// ---------------------------------------------------------------------------

const GROUP_LABEL: Record<string, string> = {
  fdw: 'FDW', rag: 'RAG', virtual_query: 'Virtual Query',
  o2c: 'O2C', supply_chain: 'Supply Chain', supply_chain_risk: 'Supply Chain Risk',
  customer_360: 'Customer 360', c360: 'Customer 360',
  inventory: 'Inventory',
  demand_forecast: 'Demand Forecast', forecast: 'Demand Forecast',
  procurement: 'Procurement', production_quality: 'Production Quality', pq: 'Production Quality',
  scr: 'Supply Chain Risk', esg: 'ESG', notify: 'Notify',
  credit: 'Credit', policy: 'Policy', misc: 'Misc', dynamic: 'User-Authored',
};

function labelFor(group: string): string {
  if (GROUP_LABEL[group]) return GROUP_LABEL[group];
  return group.split('_').map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w)).join(' ');
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface RunEnvelope {
  run_id?: string | null;
  status?: string;
  step_results?: Record<string, any>;
  completed_steps?: string[];
  pending_step?: { step_id: string; tool?: string; stage_id?: string; params_preview?: Record<string, unknown> } | null;
  error?: string | null;
  validation_report?: BuilderValidationReport['report'];
}

export function JourneyBuilder() {
  // ---- catalogue + hints (loaded once) ----
  const [tools, setTools] = useState<BuilderTool[]>([]);
  const [hints, setHints] = useState<ToolOutputHints>({});
  // Phase 1 -- per-tool declared output relationships from
  // GET /journey-builder/tool-relationships. Used to translate canvas
  // edges into ConnectionDocs accurately when the source handle
  // decodes to a real relationship name.
  const [toolRelationships, setToolRelationships] = useState<ToolRelationships>({});
  const [toolSearch, setToolSearch] = useState('');
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set());

  // ---- journey-level inputs ----
  // Pre-fill so Save/Run are clickable on first open. The user can
  // overwrite with their own name; auto-select-on-focus (rendered
  // below) makes a single keystroke replace it.
  const [journeyName, setJourneyName] = useState<string>(_defaultJourneyName);
  const [journeyDesc, setJourneyDesc] = useState('');
  const [trigger, setTrigger] = useState('manual');
  // Execution-mode pill state. Defaults to 'dataflow' so the existing
  // canvas affordances (port handles, connections) stay on. Toggling
  // to 'sequential' hides the handles, disables connection drawing,
  // and auto-arranges nodes in a vertical chain.
  const [executionMode, setExecutionMode] = useState<'sequential' | 'dataflow'>('dataflow');

  // ---- selection (canvas <-> right pane) ----
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  // Bumped whenever the canvas mutates so the right pane re-reads state.
  const [canvasVersion, setCanvasVersion] = useState(0);

  // ---- backend feedback ----
  const [validation, setValidation] = useState<BuilderValidationReport | null>(null);
  const [savedYaml, setSavedYaml] = useState<string | null>(null);
  const [savedJourneyId, setSavedJourneyId] = useState<string | null>(null);
  const [run, setRun] = useState<RunEnvelope | null>(null);
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [suggesting, setSuggesting] = useState(false);

  const canvasRef = useRef<JourneyGraphCanvasHandle>(null);
  // Mirrors the canvas's click-to-connect cursor so we can render a
  // banner above the canvas with the source node + cancel affordance.
  const [pendingConnection, setPendingConnection] = useState<PendingConnection | null>(null);

  // ---- multi-stage canvas state ----
  // Each stage holds its own nodes / edges. The canvas component
  // displays the ACTIVE stage only; switching tabs snapshots the
  // current stage's canvas state back into the stages list and
  // remounts the canvas (via a keyed prop) with the next stage's
  // slot. Persistence: every stage round-trips through
  // BuilderRequest.stages.
  const [stages, setStages] = useState<BuilderStageState[]>(() => [defaultStage()]);
  const [activeStageId, setActiveStageId] = useState<string>('main');

  // Snapshot the live canvas state into the active stage's slot.
  // Called before switching tabs / saving / running so the per-stage
  // store is always up to date with the React-Flow internal state.
  const snapshotActiveStage = useCallback(() => {
    const snap = canvasRef.current?.getState();
    if (!snap) return;
    setStages((curr) => curr.map((s) =>
      s.stageId === activeStageId
        ? { ...s, nodes: snap.nodes, edges: snap.edges }
        : s,
    ));
  }, [activeStageId]);

  // ---- load tools + output hints once ----

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await reactToolsDiagnosticsService.registry();
        if (cancelled) return;
        setTools((r.tools || []).map((row: RegistryToolRow) => ({
          name: row.tool_id,
          description: row.description || '',
          risk_level: row.risk_level,
          parameters: row.parameters || {},
          group: row.group || 'misc',
          tags: row.tags || [],
          connector_api: row.connector_api,
        })));
      } catch {
        try {
          const d = await apiClient.get<{ tools: any[] }>('/api/v1/control-plane/tools');
          if (cancelled) return;
          setTools((d.tools || []).map((t: any) => ({
            name: t.name, description: t.description || '',
            risk_level: t.risk_level, parameters: t.parameters || {},
            group: t.group || 'misc', tags: t.tags || [],
            connector_api: t.connector_api ?? null,
          })));
        } catch { /* swallow */ }
      }
      try {
        const h = await apiClient.get<{ hints: ToolOutputHints }>(
          '/api/v1/control-plane/journey-builder/tool-outputs',
        );
        if (!cancelled) setHints(h.hints || {});
      } catch { /* swallow -- canvas falls back to no hints */ }
      try {
        const r = await apiClient.get<{ relationships: ToolRelationships }>(
          '/api/v1/control-plane/journey-builder/tool-relationships',
        );
        if (!cancelled) setToolRelationships(r.relationships || {});
      } catch { /* swallow -- legacy edges path still works */ }
    })();
    return () => { cancelled = true; };
  }, []);

  // ---- palette search + group buckets ----

  const filteredTools = useMemo(() => {
    const q = toolSearch.trim().toLowerCase();
    if (!q) return tools;
    return tools.filter((t) =>
      t.name.toLowerCase().includes(q)
      || (t.description || '').toLowerCase().includes(q)
      || (t.group || '').toLowerCase().includes(q)
      || (t.connector_api || '').toLowerCase().includes(q)
      || (t.tags || []).some((tag) => tag.toLowerCase().includes(q)),
    );
  }, [tools, toolSearch]);

  const groupedTools = useMemo(() => {
    const map = new Map<string, BuilderTool[]>();
    for (const t of filteredTools) {
      const g = t.group || 'misc';
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(t);
    }
    for (const arr of map.values()) arr.sort((a, b) => a.name.localeCompare(b.name));
    return Array.from(map.entries()).sort(([a], [b]) => labelFor(a).localeCompare(labelFor(b)));
  }, [filteredTools]);

  useEffect(() => {
    if (expandedCats.size > 0) return;
    if (groupedTools.length === 0) return;
    setExpandedCats(new Set([groupedTools[0][0]]));
  }, [groupedTools, expandedCats.size]);

  // ---- selection: keep a sync'd snapshot of the selected node ----

  const selectedNode: BuilderNode | null = useMemo(() => {
    if (!selectedNodeId) return null;
    // canvasVersion read so React re-evaluates after every patch.
    void canvasVersion;
    const state = canvasRef.current?.getState();
    return state?.nodes.find((n) => n.id === selectedNodeId) || null;
  }, [selectedNodeId, canvasVersion]);

  const canvasSnapshot = useMemo(() => {
    void canvasVersion;
    return canvasRef.current?.getState() || { nodes: [], edges: [] };
  }, [canvasVersion]);

  const allNodes: BuilderNode[] = canvasSnapshot.nodes;
  const allEdges = canvasSnapshot.edges;

  const orderByNode = useMemo(
    () => topoOrderClient(allNodes, allEdges),
    [allNodes, allEdges],
  );

  const hasCycleOnCanvas = useMemo(() => {
    for (const v of orderByNode.values()) if (v === -1) return true;
    return false;
  }, [orderByNode]);

  /**
   * Ready-state for the toolbar pill -- collapses the multiple
   * preconditions Save / Run check into a single human-readable
   * status so the user can read it at a glance.
   */
  const readyState: { tone: 'ready' | 'warn' | 'block'; label: string } = useMemo(() => {
    if (!journeyName.trim()) return { tone: 'warn', label: 'name required' };
    if (allNodes.length === 0) return { tone: 'warn', label: 'drop at least one tool' };
    if (hasCycleOnCanvas) return { tone: 'block', label: 'cycle detected -- resolve before running' };
    if (validation && !validation.valid) return { tone: 'warn', label: `${validation.errors.length} validation error(s)` };
    return { tone: 'ready', label: 'ready' };
  }, [journeyName, allNodes.length, hasCycleOnCanvas, validation]);

  const resolveTool = useCallback(
    (name: string) => tools.find((t) => t.name === name) || null,
    [tools],
  );

  // ---- node patch helper (right pane edits) ----

  const patchSelected = useCallback((patch: Parameters<JourneyGraphCanvasHandle['patchNode']>[1]) => {
    if (!selectedNodeId) return;
    canvasRef.current?.patchNode(selectedNodeId, patch);
    setCanvasVersion((v) => v + 1);
  }, [selectedNodeId]);

  // ---- toolbar actions ----

  const buildRequestBody = useCallback(() => {
    const snap = canvasRef.current?.getState() || { nodes: [], edges: [] };
    // Mutate the active stage's slot with the live canvas state so
    // the wire body always reflects every drag / drop / wire the
    // user made since the last tab switch.
    const liveStages = stages.map((s) =>
      s.stageId === activeStageId
        ? { ...s, nodes: snap.nodes, edges: snap.edges }
        : s,
    );
    return toBuilderRequestMultiStage({
      stages: liveStages,
      name: journeyName,
      displayName: journeyName,
      description: journeyDesc,
      trigger,
      toolRelationships,
      executionMode,
    });
  }, [journeyName, journeyDesc, trigger, toolRelationships, executionMode, stages, activeStageId]);

  const handleValidate = useCallback(async () => {
    try {
      const data = await apiClient.post<BuilderValidationReport>(
        '/api/v1/control-plane/journey-builder/validate',
        buildRequestBody(),
      );
      setValidation(data);
    } catch (e: any) {
      setValidation({
        valid: false,
        errors: [e?.message || 'Validation request failed'],
        warnings: [],
      });
    }
  }, [buildRequestBody]);

  const handleSave = useCallback(async () => {
    if (!journeyName.trim()) return;
    setSaving(true);
    setSavedJourneyId(null);
    try {
      const data = await apiClient.post<{
        success: boolean; journey_id?: string | null; yaml?: string;
        url?: string; validation_report?: BuilderValidationReport['report'];
      }>(
        '/api/v1/control-plane/journey-builder/save',
        buildRequestBody(),
      );
      setSavedYaml(data.yaml || null);
      setSavedJourneyId(data.journey_id || null);
      if (data.validation_report) {
        setValidation({ valid: true, errors: [], warnings: [], report: data.validation_report });
      }
      toast({
        title: 'Saved to Journeys',
        description: data.journey_id ? `Journey id: ${data.journey_id}` : 'Saved successfully',
      });
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.detail;
      if (detail?.code === 'builder_validation_failed') {
        setValidation({
          valid: false,
          errors: (detail.errors || []).map((iss: ValidationIssue) => iss.message),
          warnings: (detail.warnings || []).map((iss: ValidationIssue) => iss.message),
          report: { errors: detail.errors || [], warnings: detail.warnings || [] },
        });
        toast({
          title: 'Save rejected by validation',
          description: `${(detail.errors || []).length} error(s); see banner above the canvas`,
          variant: 'destructive',
        });
      } else {
        const msg = detail?.message || e?.message || 'Save failed';
        setValidation({ valid: false, errors: [msg], warnings: [] });
        toast({ title: 'Save failed', description: msg, variant: 'destructive' });
      }
    } finally {
      setSaving(false);
    }
  }, [journeyName, buildRequestBody]);

  const handleRun = useCallback(async () => {
    if (!journeyName.trim()) return;
    setRunning(true);
    setRun(null);
    try {
      const env = await apiClient.post<RunEnvelope>(
        '/api/v1/control-plane/journey-builder/run',
        buildRequestBody(),
        { timeout: 300000 },
      );
      setRun(env);
      // Only toast on terminal states; awaiting_step_approval gets its
      // own PendingStepCard above the canvas.
      if (env.status === 'completed') {
        toast({
          title: 'Run completed',
          description: `${(env.completed_steps || []).length} step(s) finished`,
        });
      } else if (env.status === 'failed') {
        toast({
          title: 'Run failed',
          description: env.error || 'See results panel for details',
          variant: 'destructive',
        });
      }
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.detail;
      const msg = detail?.message || e?.message || 'Run failed';
      setRun({
        status: 'failed',
        error: msg,
        run_id: null,
        step_results: {},
        completed_steps: [],
      });
      toast({ title: 'Run failed', description: msg, variant: 'destructive' });
    } finally {
      setRunning(false);
    }
  }, [journeyName, buildRequestBody]);

  const handleApproveStep = useCallback(async (stepId: string) => {
    if (!run?.run_id) return;
    const env = await apiClient.post<RunEnvelope>(
      `/api/v1/control-plane/journey-builder/run/${encodeURIComponent(run.run_id)}/approve-step`,
      { step_id: stepId, approved: true },
    );
    setRun(env);
    if (env.status === 'completed') {
      toast({ title: 'Run completed', description: `Step '${stepId}' approved` });
    } else if (env.status === 'failed') {
      toast({ title: 'Run failed', description: env.error || `After approving '${stepId}'`, variant: 'destructive' });
    }
  }, [run]);

  const handleRejectStep = useCallback(async (stepId: string) => {
    if (!run?.run_id) return;
    const env = await apiClient.post<RunEnvelope>(
      `/api/v1/control-plane/journey-builder/run/${encodeURIComponent(run.run_id)}/approve-step`,
      { step_id: stepId, approved: false },
    );
    setRun(env);
    toast({ title: 'Step rejected', description: `Step '${stepId}' rejected; run aborted`, variant: 'destructive' });
  }, [run]);

  const handleSuggest = useCallback(async () => {
    setSuggesting(true);
    try {
      // Legacy AI Suggest still appends to the canvas via direct
      // patchNode calls -- minimal touch since the focus of this PR
      // is Save / Run / Validate / chaining.
      await apiClient.post('/api/v1/control-plane/journey-builder/suggest', {
        current_steps: (canvasRef.current?.getState().nodes || []).map((n) => ({
          id: n.id, tool: n.data.tool, name: n.data.name, params: n.data.params,
        })),
        goal: journeyDesc || journeyName, use_case: '',
      });
    } catch { /* swallow */ }
    finally { setSuggesting(false); }
  }, [journeyName, journeyDesc]);

  // ---- per-node issue map for the validate panel summary ----

  const issuesByNode = useMemo(
    () => applyValidationToNodes(validation, allNodes),
    [validation, allNodes],
  );

  // ---- palette drag handler ----

  const onPaletteDragStart = useCallback((e: DragEvent<HTMLButtonElement>, toolName: string) => {
    e.dataTransfer.setData('application/x-tool-name', toolName);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  // ---- render ----
  // Presentation only below this line.

  const [paletteOpen, setPaletteOpen] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<'step' | 'journey' | 'run'>('journey');
  const isXl = useIsWide('(min-width: 1280px)');

  // The inspector follows the canvas: a selected step shows its properties,
  // a test run shows its results.
  useEffect(() => {
    if (selectedNodeId) { setInspectorTab('step'); setInspectorOpen(true); }
    else setInspectorTab((t) => (t === 'step' ? 'journey' : t));
  }, [selectedNodeId]);
  useEffect(() => {
    if (run || running) { setInspectorTab('run'); setInspectorOpen(true); }
  }, [run, running]);

  const addTool = (toolName: string) => {
    canvasRef.current?.addTool(toolName);
    setCanvasVersion((v) => v + 1);
    setPaletteOpen(false);
  };

  const readyText =
    readyState.label === 'ready' ? 'Ready to run'
    : readyState.label === 'name required' ? 'Add a name to save or run'
    : readyState.label === 'drop at least one tool' ? 'Add a step to get started'
    : readyState.tone === 'block' ? 'Steps form a loop: remove one connection'
    : validation && !validation.valid ? `${validation.errors.length} validation ${validation.errors.length === 1 ? 'error' : 'errors'}`
    : readyState.label;
  const saveState = saving ? 'Saving' : savedJourneyId ? 'Saved to journeys' : 'Not saved yet';

  const palette = (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 px-3 pb-2 pt-3">
        <SearchInput value={toolSearch} onChange={setToolSearch} placeholder="Search steps" className="sm:w-full" />
      </div>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto pb-3">
        {groupedTools.length === 0 && tools.length === 0 && (
          <div className="space-y-2 px-3 pt-1" aria-label="Loading steps">
            {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-9 w-full" />)}
          </div>
        )}
        {groupedTools.length === 0 && tools.length > 0 && (
          <p className="px-4 py-6 text-center text-sm text-muted-foreground">No steps match "{toolSearch}".</p>
        )}
        {groupedTools.map(([groupKey, catTools]) => {
          const isOpen = expandedCats.has(groupKey) || !!toolSearch.trim();
          return (
            <div key={groupKey}>
              <button
                type="button"
                aria-expanded={isOpen}
                className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                onClick={() => setExpandedCats((prev) => {
                  const n = new Set(prev);
                  n.has(groupKey) ? n.delete(groupKey) : n.add(groupKey);
                  return n;
                })}
              >
                <Icon name={isOpen ? 'chevron-down' : 'chevron-right'} className="h-3 w-3 shrink-0" />
                <span className="min-w-0 flex-1 truncate">{sentenceCase(labelFor(groupKey))}</span>
                <span className="num text-subtle-foreground">{catTools.length}</span>
              </button>
              {isOpen && catTools.map((tool) => {
                const system = systemsIn(`${tool.connector_api || ''} ${tool.name}`)[0];
                return (
                  <button
                    key={tool.name}
                    type="button"
                    draggable
                    onDragStart={(e) => onPaletteDragStart(e, tool.name)}
                    onClick={() => addTool(tool.name)}
                    title={tool.connector_api ? `Drag onto the canvas, or select to add. Calls ${tool.connector_api}` : 'Drag onto the canvas, or select to add'}
                    className="group flex w-full cursor-grab items-start gap-2.5 px-3 py-2 text-left transition-colors hover:bg-accent/70 focus-visible:bg-accent/70 focus-visible:outline-none active:cursor-grabbing"
                  >
                    {system
                      ? <SystemLogo system={system} size="xs" className="mt-0.5" />
                      : <Icon name="cube" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-subtle-foreground" />}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-mono text-xs text-foreground">{tool.name}</span>
                      {tool.description && <span className="mt-0.5 line-clamp-2 block text-xs text-muted-foreground">{tool.description}</span>}
                    </span>
                    <Icon name="plus" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-subtle-foreground opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100" />
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );

  const journeySettings = (
    <div className="space-y-5">
      <Field label="Description" htmlFor="jb-desc" hint="Also used as the goal when you ask for a suggestion.">
        <Textarea id="jb-desc" value={journeyDesc} onChange={(e) => setJourneyDesc(e.target.value)} placeholder="What this journey does" rows={3} />
      </Field>
      <Field label="Starts" htmlFor="jb-trigger">
        <Select value={trigger} onValueChange={setTrigger}>
          <SelectTrigger id="jb-trigger"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="manual">Manually</SelectItem>
            <SelectItem value="schedule">On a schedule</SelectItem>
            <SelectItem value="webhook">From a webhook</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field
        label="How steps run"
        hint={executionMode === 'sequential'
          ? 'Steps run in order and do not pass data to each other.'
          : 'Steps can read the outputs of earlier steps through connections.'}
      >
        {/* Switching to "In order" while connections exist asks first,
            because the wiring will be dropped. */}
        <div className="inline-flex rounded-md border border-border bg-surface-2 p-0.5" role="tablist" aria-label="How steps run">
          <button
            type="button"
            role="tab"
            aria-selected={executionMode === 'sequential'}
            className={cn(
              'h-8 rounded-[5px] px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              executionMode === 'sequential' ? 'bg-card font-medium text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground',
            )}
            onClick={async () => {
              if (executionMode === 'sequential') return;
              const snap = canvasRef.current?.getState();
              const edgeCount = snap?.edges?.length || 0;
              if (edgeCount > 0) {
                const ok = await confirmDialog({
                  title: 'Run the steps in order?',
                  description: `This removes ${edgeCount} connection${edgeCount === 1 ? '' : 's'} from the canvas.`,
                  confirmLabel: 'Switch',
                });
                if (!ok) return;
              }
              setExecutionMode('sequential');
              setCanvasVersion((v) => v + 1);
            }}
          >
            In order
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={executionMode === 'dataflow'}
            className={cn(
              'h-8 rounded-[5px] px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              executionMode === 'dataflow' ? 'bg-card font-medium text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground',
            )}
            onClick={() => setExecutionMode('dataflow')}
          >
            Data flow
          </button>
        </div>
      </Field>

      <div className="border-t border-border pt-4">
        <SubHeading>On the canvas</SubHeading>
        <KeyValues
          items={[
            { label: 'Steps', value: <span className="num">{allNodes.length}</span> },
            { label: 'Connections', value: <span className="num">{allEdges.length}</span> },
            { label: 'Stages', value: <span className="num">{stages.length}</span> },
            { label: 'Saved', value: savedJourneyId ? <span className="mono-id text-foreground">{savedJourneyId}</span> : 'Not yet' },
          ]}
        />
      </div>

      {savedYaml && (
        <div>
          <SubHeading>Definition</SubHeading>
          <CodeBlock maxHeight={280}>{savedYaml}</CodeBlock>
        </div>
      )}
    </div>
  );

  const runPanel = (
    <div className="space-y-4">
      {running && (
        <p className="flex items-center gap-2.5 text-sm text-muted-foreground" aria-live="polite">
          <span className="dot-live text-primary dark:text-brand-hi" aria-hidden="true" /> Running the steps on the canvas
        </p>
      )}
      {!run && !running && (
        <EmptyState icon="play" title="No test run yet" description="Run the journey to see what each step returned." className="py-10" />
      )}
      {run && <RunResultsPanel envelope={run} />}
      {/* Data queues: data flow journeys only. Polls every 2 s while the run is in flight. */}
      {run?.run_id && executionMode === 'dataflow' && (
        <RunQueueInspector
          runId={run.run_id}
          pollIntervalMs={run.status === 'awaiting_step_approval' || run.status === 'running' ? 2000 : 0}
        />
      )}
    </div>
  );

  const inspector = (
    <Tabs value={inspectorTab} onValueChange={(v) => setInspectorTab(v as typeof inspectorTab)} className="flex min-h-0 flex-1 flex-col">
      <TabsList variant="line" className="shrink-0 px-4">
        <TabsTrigger value="step">Step</TabsTrigger>
        <TabsTrigger value="journey">Journey</TabsTrigger>
        <TabsTrigger value="run">Test run</TabsTrigger>
      </TabsList>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <TabsContent value="step" className="mt-0">
          {selectedNode ? (
            <StepEditor
              node={selectedNode}
              allNodes={allNodes}
              hints={hints}
              tools={tools}
              issues={issuesByNode.get(selectedNode.id) || []}
              onPatch={patchSelected}
              onWireFromParam={(param, src) => {
                canvasRef.current?.setEdge({
                  fromNode: src.fromNode,
                  fromKey: src.fromKey,
                  toNode: selectedNode.id,
                  toParam: param,
                });
                setCanvasVersion((v) => v + 1);
              }}
              onClearWireForParam={(param) => {
                canvasRef.current?.removeEdgeForTarget(selectedNode.id, param);
                setCanvasVersion((v) => v + 1);
              }}
            />
          ) : (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {allNodes.length === 0 ? 'Add a step from the list, then select it to set its inputs.' : 'Select a step on the canvas to set its inputs.'}
            </p>
          )}
        </TabsContent>
        <TabsContent value="journey" className="mt-0">{journeySettings}</TabsContent>
        <TabsContent value="run" className="mt-0">{runPanel}</TabsContent>
      </div>
    </Tabs>
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Sticky editor header: name, state, secondary actions, Save */}
      <header className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-2 border-b border-border bg-background px-3 py-2 sm:px-5">
        <Input
          value={journeyName}
          onChange={(e) => setJourneyName(e.target.value)}
          onFocus={(e) => e.target.select()}
          placeholder="Journey name"
          aria-label="Journey name"
          className="h-9 w-full border-transparent bg-transparent px-2 text-md font-medium shadow-none hover:border-border focus-visible:border-border-strong sm:w-72"
        />
        <div className="flex min-w-0 items-center gap-3 text-xs text-muted-foreground">
          <StatusPill tone={readyState.tone === 'ready' ? 'success' : readyState.tone === 'warn' ? 'warning' : 'danger'} className="font-normal">{readyText}</StatusPill>
          <span className="hidden truncate md:inline">{saveState}</span>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-1.5">
          <Button size="sm" variant="ghost" className="lg:hidden" onClick={() => setPaletteOpen(true)}>
            <Icon name="plus" /> Add step
          </Button>
          <Button size="sm" variant="ghost" className="xl:hidden" onClick={() => setInspectorOpen(true)}>
            <Icon name="sliders" /> Properties
          </Button>
          <Button size="sm" variant="ghost" onClick={handleSuggest} disabled={suggesting} title="Ask the Copilot to suggest the next steps">
            <Icon name={suggesting ? 'spinner' : 'sparkles'} className={suggesting ? 'animate-spin' : undefined} /> Suggest
          </Button>
          <Button size="sm" variant="ghost" onClick={handleValidate} title="Check every step against the tools registry">
            <Icon name="shield-check" /> Validate
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleRun}
            disabled={running || !journeyName.trim() || allNodes.length === 0 || hasCycleOnCanvas}
            title={
              !journeyName.trim() ? 'Enter a journey name to run'
              : allNodes.length === 0 ? 'Add at least one step to run'
              : hasCycleOnCanvas ? 'Remove the loop in the graph before running'
              : 'Run the journey as drawn, without saving'
            }
          >
            <Icon name={running ? 'spinner' : 'play'} className={running ? 'animate-spin' : undefined} /> Test run
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving || !journeyName.trim() || hasCycleOnCanvas}
            title={
              !journeyName.trim() ? 'Enter a journey name to save'
              : hasCycleOnCanvas ? 'Remove the loop in the graph before saving'
              : 'Save this journey to the Journeys tab'
            }
          >
            {saving && <Icon name="spinner" className="animate-spin" />} Save
          </Button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[256px_minmax(0,1fr)] xl:grid-cols-[256px_minmax(0,1fr)_340px]">
        {/* Left: steps to add */}
        <aside className="hidden min-h-0 flex-col border-r border-border bg-sidebar/40 lg:flex" aria-label="Steps">
          {palette}
        </aside>

        {/* Centre: the flow */}
        <div className="flex min-h-0 min-w-0 flex-col">
          {(validation || savedJourneyId || (run?.status === 'awaiting_step_approval' && run.pending_step && run.run_id)) && (
            <div className="shrink-0 space-y-2 border-b border-border px-3 py-2 sm:px-4">
              {validation && (
                validation.valid ? (
                  <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-foreground">
                    <StatusPill tone={validation.warnings.length ? 'warning' : 'success'}>{validation.warnings.length ? 'Valid, with notes' : 'Valid'}</StatusPill>
                    {validation.warnings.length > 0 && <span className="text-muted-foreground">{validation.warnings.join('; ')}</span>}
                  </p>
                ) : (
                  <InlineError>
                    {validation.errors.join('; ')}
                    {validation.warnings.length > 0 && <span className="mt-1 block text-warning">{validation.warnings.join('; ')}</span>}
                  </InlineError>
                )
              )}
              {run?.status === 'awaiting_step_approval' && run.pending_step && run.run_id && (
                <PendingStepCard
                  runId={run.run_id}
                  pending={run.pending_step}
                  onApprove={handleApproveStep}
                  onReject={handleRejectStep}
                />
              )}
              {savedJourneyId && (
                <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-foreground">
                  <StatusPill tone="success">Saved</StatusPill>
                  <span className="mono-id">{savedJourneyId}</span>
                  <a
                    className="ml-auto inline-flex items-center gap-1 text-sm font-medium text-primary underline-offset-4 hover:underline dark:text-brand-hi"
                    href={`/workspace/automation?tab=journeys&id=${encodeURIComponent(savedJourneyId)}`}
                  >
                    Open in journeys <Icon name="arrow-right" className="h-3.5 w-3.5" />
                  </a>
                </p>
              )}
            </div>
          )}

          <div className="relative min-h-[320px] flex-1 overflow-hidden">
            <JourneyGraphCanvas
              key={activeStageId}
              ref={canvasRef}
              outputHints={hints}
              validation={validation}
              resolveTool={resolveTool}
              executionMode={executionMode}
              onSelectionChange={(id) => {
                setSelectedNodeId(id);
                setCanvasVersion((v) => v + 1);
              }}
              onPendingConnectionChange={setPendingConnection}
            />

            {/* Floating bar: stages of the journey */}
            <div className="absolute left-3 top-3 z-10 max-w-[calc(100%-1.5rem)] rounded-lg border border-border bg-popover px-2 pt-2 shadow-sm">
              <StageTabs
                stages={stages}
                activeStageId={activeStageId}
                onActiveChange={(nextId) => {
                  // Snapshot the live canvas back to the current slot
                  // before switching tabs so unsaved drag / drop work is
                  // preserved across the canvas remount.
                  snapshotActiveStage();
                  setActiveStageId(nextId);
                }}
                onAdd={() => {
                  snapshotActiveStage();
                  const next = newStage(stages);
                  setStages((curr) => [...curr, next]);
                  setActiveStageId(next.stageId);
                }}
                onRename={(stageId, name) => {
                  setStages((curr) => curr.map((s) =>
                    s.stageId === stageId ? { ...s, name } : s,
                  ));
                }}
                onDelete={(stageId) => {
                  setStages((curr) => {
                    const remaining = curr.filter((s) => s.stageId !== stageId);
                    return remaining.length ? remaining : [defaultStage()];
                  });
                  if (activeStageId === stageId) {
                    const rest = stages.filter((s) => s.stageId !== stageId);
                    setActiveStageId((rest[0] || defaultStage()).stageId);
                  }
                }}
              />
            </div>

            {/* Connecting: which output is being wired, and how to cancel */}
            {pendingConnection && (
              <div className="animate-fade-up absolute left-1/2 top-3 z-10 flex max-w-[calc(100%-1.5rem)] -translate-x-1/2 items-center gap-2 rounded-lg border border-brand/40 bg-popover px-3 py-1.5 text-xs text-foreground shadow-md">
                <span className="dot-live shrink-0 text-primary dark:text-brand-hi" aria-hidden="true" />
                <span className="min-w-0 truncate">
                  Connecting <span className="font-mono">{pendingConnection.toolName}.{pendingConnection.key}</span>. Select an input to finish.
                </span>
                <button
                  type="button"
                  onClick={() => canvasRef.current?.cancelConnection()}
                  className="shrink-0 font-medium text-primary underline-offset-4 hover:underline dark:text-brand-hi"
                  title="Cancel (Esc)"
                >
                  Cancel
                </button>
              </div>
            )}

            {allNodes.length === 0 && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6">
                <div className="max-w-xs text-center">
                  <p className="text-md font-medium text-foreground">Start with a step</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    <span className="hidden lg:inline">Drag a step from the list onto the canvas, or select one to add it.</span>
                    <span className="lg:hidden">Use "Add step" to choose the first step.</span>
                    {' '}Connect an output to an input to pass data along.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: properties of the selected step, journey settings, test run */}
        {isXl && (
          <aside className="flex min-h-0 flex-col border-l border-border bg-card" aria-label="Properties">
            {inspector}
          </aside>
        )}
      </div>

      {/* Below lg the step list opens in a sheet; below xl the properties do. */}
      <DetailSheet open={paletteOpen} onOpenChange={setPaletteOpen} title="Add a step" description="Select a step to add it to the canvas.">
        <div className="-mx-5 -my-5 flex min-h-[60vh] flex-col">{paletteOpen ? palette : null}</div>
      </DetailSheet>
      <DetailSheet
        open={!isXl && inspectorOpen}
        onOpenChange={setInspectorOpen}
        title={inspectorTab === 'step' && selectedNode ? selectedNode.data.name || 'Step' : 'Properties'}
        description="Step inputs, journey settings and the last test run."
      >
        <div className="-mx-5 -my-5 flex min-h-[60vh] flex-col">{!isXl && inspectorOpen ? inspector : null}</div>
      </DetailSheet>
    </div>
  );
}

// ---------------------------------------------------------------------------
// StepEditor (inspector content for the selected step)
// ---------------------------------------------------------------------------

interface StepEditorProps {
  node: BuilderNode;
  allNodes: BuilderNode[];
  hints: ToolOutputHints;
  tools: BuilderTool[];
  issues: ValidationIssue[];
  onPatch: (patch: Parameters<JourneyGraphCanvasHandle['patchNode']>[1]) => void;
  /** Wire a producer step's output key into this node's ``param``. */
  onWireFromParam: (param: string, src: { fromNode: string; fromKey: string }) => void;
  /** Clear any incoming wire for this node's ``param`` (restore literal). */
  onClearWireForParam: (param: string) => void;
}

function StepEditor({
  node, allNodes, hints, tools, issues, onPatch,
  onWireFromParam, onClearWireForParam,
}: StepEditorProps) {
  const params = node.data.params || {};
  const tool = node.data.toolDef;
  const paramKeys: string[] = tool?.parameters?.properties ? Object.keys(tool.parameters.properties) : Object.keys(params);
  const requiredSet = new Set<string>(tool?.parameters?.required || []);

  const setParam = (k: string, raw: string) => {
    // Try JSON; fall back to literal string so users can type plain
    // strings without quotes.
    let value: any = raw;
    if (raw.trim().startsWith('{') || raw.trim().startsWith('[') || raw.trim().startsWith('"')) {
      try { value = JSON.parse(raw); } catch { /* keep string */ }
    } else if (/^-?\d+(\.\d+)?$/.test(raw.trim())) {
      value = Number(raw);
    } else if (raw === 'true') value = true;
    else if (raw === 'false') value = false;
    onPatch({ params: { ...params, [k]: value } });
  };

  const system = systemsIn(`${tool?.connector_api || ''} ${node.data.tool || ''}`)[0];

  return (
    <div className="space-y-5">
      {issues.length > 0 && (
        <div role="alert" className="space-y-2 rounded-lg border border-destructive/25 bg-destructive/5 p-3">
          {issues.map((iss, i) => (
            <div key={i} className="text-sm">
              <StatusPill tone={iss.severity === 'error' ? 'danger' : 'warning'}>{String(iss.code || '').replace(/[_-]+/g, ' ')}</StatusPill>
              <p className="mt-0.5 text-muted-foreground">{iss.message}</p>
            </div>
          ))}
        </div>
      )}

      <Field label="Step name" htmlFor={`name-${node.id}`}>
        <Input id={`name-${node.id}`} value={node.data.name} onChange={(e) => onPatch({ name: e.target.value })} />
      </Field>

      <Field
        label="Tool"
        htmlFor={`tool-${node.id}`}
        hint={tool?.description ? tool.description : undefined}
      >
        <Select
          value={node.data.tool || ''}
          onValueChange={(value) => {
            const t = tools.find((x) => x.name === value);
            onPatch({ tool: value, toolDef: t || undefined, params: {} });
          }}
        >
          <SelectTrigger id={`tool-${node.id}`} className="font-mono text-xs"><SelectValue placeholder="Choose a tool" /></SelectTrigger>
          <SelectContent className="max-h-72">
            {tools.map((t) => <SelectItem key={t.name} value={t.name} className="font-mono text-xs">{t.name}</SelectItem>)}
          </SelectContent>
        </Select>
        {(system || tool?.risk_level) && (
          <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {system && <span className="inline-flex items-center gap-1.5 text-foreground"><SystemLogo system={system} size="xs" /> {systemName(system)}</span>}
            {tool?.risk_level && <StatusPill status={tool.risk_level} className="font-normal" />}
          </p>
        )}
      </Field>

      <div>
        <SubHeading action={<span className="num text-xs text-muted-foreground">{paramKeys.length} {paramKeys.length === 1 ? 'input' : 'inputs'}</span>}>Inputs</SubHeading>
        {paramKeys.length === 0 && <p className="text-sm text-muted-foreground">This tool takes no inputs.</p>}
        <div className="space-y-3.5">
          {paramKeys.map((k) => {
            const v = (params as any)[k];
            const shown = typeof v === 'string' ? v : (v === undefined ? '' : JSON.stringify(v));
            const isRequired = requiredSet.has(k);
            return (
              <div key={k}>
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <label htmlFor={`param-${node.id}-${k}`} className="min-w-0 truncate font-mono text-xs text-foreground">
                    {k}{isRequired ? <span className="font-sans text-muted-foreground"> (required)</span> : ''}
                  </label>
                  <ReadsFromDropdown
                    consumerNodeId={node.id}
                    consumerParam={k}
                    allNodes={allNodes}
                    outputHints={hints}
                    currentValue={v}
                    onPick={(src) => onWireFromParam(k, src)}
                    onClearChain={() => onClearWireForParam(k)}
                    className="max-w-[150px]"
                  />
                </div>
                <Input
                  id={`param-${node.id}-${k}`}
                  value={shown}
                  onChange={(e) => setParam(k, e.target.value)}
                  placeholder={isRequired ? 'Required' : 'Optional'}
                  className="font-mono text-xs"
                />
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-subtle-foreground">
          Type a value, or read it from an earlier step: drag that step's output onto the input on the canvas, or pick it from the menu beside the field.
        </p>
      </div>

      <Field label="Repeat for each item" htmlFor={`foreach-${node.id}`} hint="Optional. A list from an earlier step; the tool runs once per item.">
        <Input
          id={`foreach-${node.id}`}
          value={node.data.foreach || ''}
          onChange={(e) => onPatch({ foreach: e.target.value || undefined })}
          placeholder="${steps.s1.results}"
          className="font-mono text-xs"
        />
      </Field>

      <div className="flex items-center justify-between gap-4 border-t border-border pt-4">
        <label htmlFor={`approval-${node.id}`} className="min-w-0 cursor-pointer">
          <span className="block text-sm font-medium text-foreground">Pause for approval</span>
          <span className="block text-xs text-muted-foreground">The run waits for a person before this step.</span>
        </label>
        <Switch
          id={`approval-${node.id}`}
          checked={!!node.data.requires_approval}
          onCheckedChange={(checked) => onPatch({ requires_approval: !!checked })}
        />
      </div>
    </div>
  );
}

export default JourneyBuilder;
