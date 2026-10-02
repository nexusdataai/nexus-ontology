import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ScrollArea } from './ui/scroll-area';
import {
  CheckCircle2, ChevronDown, ChevronRight, Database, Loader2, Play,
  Save, Search, Settings, Sparkles, AlertTriangle, GripVertical,
} from 'lucide-react';
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

  return (
    <div className="h-full flex gap-3 p-4">
      {/* Left: Tool Palette */}
      <Card className="w-64 flex flex-col shrink-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Tool Palette</CardTitle>
          <div className="relative mt-1">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
            <Input
              value={toolSearch}
              onChange={(e) => setToolSearch(e.target.value)}
              placeholder="Search tools..."
              className="pl-7 h-7 text-xs"
            />
          </div>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 p-0">
          <ScrollArea className="h-full">
            {groupedTools.length === 0 && (
              <div className="px-3 py-6 text-[11px] text-muted-foreground text-center">
                {tools.length === 0 ? 'Loading tools...' : 'No tools match your search.'}
              </div>
            )}
            {groupedTools.map(([groupKey, catTools]) => {
              const isOpen = expandedCats.has(groupKey);
              return (
                <div key={groupKey}>
                  <button
                    className="w-full flex items-center gap-1 px-3 py-1.5 text-[10px] font-semibold text-muted-foreground hover:bg-muted/30 uppercase tracking-wider"
                    onClick={() => setExpandedCats((prev) => {
                      const n = new Set(prev);
                      n.has(groupKey) ? n.delete(groupKey) : n.add(groupKey);
                      return n;
                    })}
                  >
                    {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                    {labelFor(groupKey)} ({catTools.length})
                  </button>
                  {isOpen && catTools.map((tool) => (
                    <button
                      key={tool.name}
                      draggable
                      onDragStart={(e) => onPaletteDragStart(e, tool.name)}
                      title={tool.connector_api ? `Drag onto canvas. Calls ${tool.connector_api}` : 'Drag onto canvas'}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted/30 border-b border-border/30 cursor-grab active:cursor-grabbing flex items-start gap-1"
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground/60 mt-0.5 shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="font-medium truncate">{tool.name}</div>
                        <div className="text-[9px] text-muted-foreground truncate">
                          {tool.description?.substring(0, 50)}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              );
            })}
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Center: Graph Canvas + toolbar + run feedback */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center gap-2 mb-2">
          <Input
            value={journeyName}
            onChange={(e) => setJourneyName(e.target.value)}
            onFocus={(e) => e.target.select()}
            placeholder="Journey name..."
            className="text-sm h-8 max-w-xs"
          />
          {/* Execution-mode pill: two segments. Switching to sequential
              while edges exist on the canvas pops a confirm so the user
              knows their wiring will be dropped. */}
          <div className="inline-flex rounded-md border bg-card overflow-hidden text-xs h-8" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={executionMode === 'sequential'}
              title="Sequential: steps run in order with no inter-step data exchange (knowledge-indexing / ETL)"
              className={cn(
                'px-3 transition-colors',
                executionMode === 'sequential'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted/30',
              )}
              onClick={() => {
                if (executionMode === 'sequential') return;
                const snap = canvasRef.current?.getState();
                const edgeCount = snap?.edges?.length || 0;
                if (edgeCount > 0) {
                  const ok = window.confirm(
                    `Switching to Sequential mode will remove ${edgeCount} connection${edgeCount === 1 ? '' : 's'} from the canvas. Continue?`,
                  );
                  if (!ok) return;
                }
                setExecutionMode('sequential');
                setCanvasVersion((v) => v + 1);
              }}
            >
              Sequential
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={executionMode === 'dataflow'}
              title="Dataflow: steps may consume one another's outputs via ConnectionDocs"
              className={cn(
                'px-3 transition-colors border-l',
                executionMode === 'dataflow'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted/30',
              )}
              onClick={() => setExecutionMode('dataflow')}
            >
              Dataflow
            </button>
          </div>
          <Input
            value={journeyDesc}
            onChange={(e) => setJourneyDesc(e.target.value)}
            placeholder="Description..."
            className="text-sm h-8 flex-1"
          />
          <select
            value={trigger}
            onChange={(e) => setTrigger(e.target.value)}
            className="h-8 px-2 rounded border text-xs bg-background"
          >
            <option value="manual">Manual</option>
            <option value="schedule">Schedule</option>
            <option value="webhook">Webhook</option>
          </select>
          <Button size="sm" variant="outline" onClick={handleSuggest} disabled={suggesting}
            title="Ask the AI Copilot to suggest next steps"
          >
            {suggesting ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Sparkles className="h-3.5 w-3.5 mr-1" />}
            AI Suggest
          </Button>
          <Button size="sm" variant="outline" onClick={handleValidate}
            title="Run JourneyDoc.validate_strict against the live ToolRegistry"
          >
            <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Validate
          </Button>
          <Button
            size="sm" variant="outline" onClick={handleSave}
            disabled={saving || !journeyName.trim() || hasCycleOnCanvas}
            title={
              !journeyName.trim() ? 'Enter a journey name above to enable Save'
              : hasCycleOnCanvas ? 'Resolve the cycle in the graph before saving'
              : 'Persist this journey to the Journeys tab (Foundry DDB)'
            }
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}
            Save
          </Button>
          <Button
            size="sm"
            onClick={handleRun}
            disabled={running || !journeyName.trim() || allNodes.length === 0 || hasCycleOnCanvas}
            title={
              !journeyName.trim() ? 'Enter a journey name above to enable Run'
              : allNodes.length === 0 ? 'Drop at least one tool onto the canvas to enable Run'
              : hasCycleOnCanvas ? 'Resolve the cycle in the graph before running'
              : 'Dispatch this journey through the YAML Journey Runner'
            }
          >
            {running ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-1" />}
            Run
          </Button>
        </div>

        {/* Ready-state pill: communicates exactly why Save/Run are
            disabled (or that everything is ready) so the user never
            has to guess. */}
        <div className={cn(
          'mb-2 inline-flex items-center gap-2 self-start px-2 py-1 rounded text-[11px] border',
          readyState.tone === 'ready'
            ? 'bg-green-500/10 text-green-300 border-green-500/30'
            : readyState.tone === 'warn'
              ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
              : 'bg-red-500/10 text-red-300 border-red-500/30',
        )}>
          <span className="font-mono">{allNodes.length} nodes</span>
          <span className="opacity-70">{allEdges.length} edges</span>
          <span className="opacity-70">- "{journeyName || 'unnamed'}"</span>
          <span className="font-medium">- {readyState.label}</span>
        </div>

        {validation && (
          <div className={cn(
            'mb-2 px-3 py-2 rounded text-xs',
            validation.valid ? 'bg-green-500/10 text-green-300' : 'bg-red-500/10 text-red-300',
          )}>
            {validation.valid ? 'Journey is valid' : validation.errors.join('; ')}
            {validation.warnings.length > 0 && (
              <span className="text-amber-300 ml-2">{validation.warnings.join('; ')}</span>
            )}
          </div>
        )}

        {run?.status === 'awaiting_step_approval' && run.pending_step && run.run_id && (
          <PendingStepCard
            runId={run.run_id}
            pending={run.pending_step}
            onApprove={handleApproveStep}
            onReject={handleRejectStep}
            className="mb-2"
          />
        )}

        {pendingConnection && (
          <div className="mb-2 inline-flex items-center gap-2 self-start px-2 py-1 rounded text-[11px] border bg-primary/15 text-primary border-primary/40">
            <span className="font-mono">{pendingConnection.toolName}.{pendingConnection.key}</span>
            <span className="opacity-80">- click an input port to wire</span>
            <button
              type="button"
              onClick={() => canvasRef.current?.cancelConnection()}
              className="ml-2 underline hover:opacity-80"
              title="Cancel (Esc)"
            >
              cancel
            </button>
          </div>
        )}

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

        <div className="flex-1 min-h-[300px] border rounded-md overflow-hidden bg-card/30">
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
        </div>

        {savedJourneyId && (
          <div className="mt-2 px-3 py-2 rounded text-xs bg-green-500/10 text-green-300 flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Saved as <span className="font-mono">{savedJourneyId}</span>
            <a
              className="underline hover:text-green-200 ml-auto"
              href={`/workspace/automation?tab=journeys&id=${encodeURIComponent(savedJourneyId)}`}
            >
              Open in Journeys
            </a>
          </div>
        )}

        {run && (
          <RunResultsPanel envelope={run} className="mt-2 max-h-72 overflow-auto" />
        )}

        {/* Data Queues inspector -- dataflow journeys only, since
            sequential mode does not exchange data between steps and
            thus has no queues to inspect. Polls every 2 s while the
            run is in flight (paused / running). */}
        {run?.run_id && executionMode === 'dataflow' && (
          <RunQueueInspector
            runId={run.run_id}
            className="mt-2"
            pollIntervalMs={
              run.status === 'awaiting_step_approval' || run.status === 'running' ? 2000 : 0
            }
          />
        )}

        {savedYaml && (
          <details className="mt-2 text-xs">
            <summary className="cursor-pointer text-muted-foreground">Show saved YAML</summary>
            <pre className="text-[9px] bg-muted/30 rounded p-2 mt-1 overflow-x-auto font-mono whitespace-pre">{savedYaml}</pre>
          </details>
        )}
      </div>

      {/* Right: Step Editor */}
      <Card className="w-80 flex flex-col shrink-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-1">
            <Settings className="h-3.5 w-3.5" /> Step Editor
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 p-3">
          {selectedNode ? (
            <ScrollArea className="h-full">
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
            </ScrollArea>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">
              Drop a tool onto the canvas, then click a node to edit it.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// StepEditor (right-pane content)
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

  return (
    <div className="space-y-3 text-xs">
      <div>
        <label className="text-[10px] text-muted-foreground uppercase">Step Name</label>
        <Input
          value={node.data.name}
          onChange={(e) => onPatch({ name: e.target.value })}
          className="h-7 text-xs mt-0.5"
        />
      </div>

      <div>
        <label className="text-[10px] text-muted-foreground uppercase">Tool</label>
        <select
          value={node.data.tool || ''}
          onChange={(e) => {
            const t = tools.find((x) => x.name === e.target.value);
            onPatch({ tool: e.target.value, toolDef: t || undefined, params: {} });
          }}
          className="w-full h-7 px-2 rounded border text-xs bg-background mt-0.5"
        >
          {tools.map((t) => <option key={t.name} value={t.name}>{t.name}</option>)}
        </select>
      </div>

      <div>
        <div className="flex items-center justify-between">
          <label className="text-[10px] text-muted-foreground uppercase">Parameters</label>
          <span className="text-[9px] text-muted-foreground">{paramKeys.length} fields</span>
        </div>
        <div className="space-y-1.5 mt-1">
          {paramKeys.length === 0 && (
            <div className="text-[10px] text-muted-foreground italic">no parameters declared</div>
          )}
          {paramKeys.map((k) => {
            const v = (params as any)[k];
            const shown = typeof v === 'string' ? v : (v === undefined ? '' : JSON.stringify(v));
            const isRequired = requiredSet.has(k);
            return (
              <div key={k} className="space-y-0.5">
                <div className="flex items-center justify-between gap-1">
                  <label className="text-[10px] font-mono">
                    {k}{isRequired ? <span className="text-amber-300">*</span> : ''}
                  </label>
                  <ReadsFromDropdown
                    consumerNodeId={node.id}
                    consumerParam={k}
                    allNodes={allNodes}
                    outputHints={hints}
                    currentValue={v}
                    onPick={(src) => onWireFromParam(k, src)}
                    onClearChain={() => onClearWireForParam(k)}
                    className="max-w-[140px]"
                  />
                </div>
                <Input
                  value={shown}
                  onChange={(e) => setParam(k, e.target.value)}
                  placeholder={isRequired ? 'required' : 'optional'}
                  className="h-7 text-[11px] font-mono"
                />
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <label className="text-[10px] text-muted-foreground uppercase">Foreach (optional)</label>
        <Input
          value={node.data.foreach || ''}
          onChange={(e) => onPatch({ foreach: e.target.value || undefined })}
          placeholder="${steps.s1.results}"
          className="h-7 text-[11px] font-mono mt-0.5"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id={`approval-${node.id}`}
          checked={!!node.data.requires_approval}
          onChange={(e) => onPatch({ requires_approval: e.target.checked })}
          className="h-3 w-3"
        />
        <label htmlFor={`approval-${node.id}`} className="text-[11px] cursor-pointer">
          Requires approval
        </label>
      </div>

      {issues.length > 0 && (
        <div className="pt-2 border-t space-y-1">
          <div className="text-[10px] uppercase tracking-wide text-red-300 flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" /> Validation
          </div>
          {issues.map((iss, i) => (
            <div key={i} className="text-[10px]">
              <Badge variant="outline" className={cn(
                'text-[9px] mr-1',
                iss.severity === 'error'
                  ? 'bg-red-500/15 text-red-300 border-red-500/30'
                  : 'bg-amber-500/15 text-amber-300 border-amber-500/30',
              )}>
                {iss.code}
              </Badge>
              {iss.message}
            </div>
          ))}
        </div>
      )}

      <div className="text-[9px] text-muted-foreground pt-2 border-t flex items-start gap-1">
        <Database className="h-3 w-3 mt-0.5 shrink-0" />
        <span>
          Drag a producer node's output port onto an input port to chain.
          The reference dropdown next to each param is the keyboard fallback.
        </span>
      </div>
    </div>
  );
}

export default JourneyBuilder;
