/**
 * Pure builderState helpers shared by the graph canvas and the
 * Save / Run / Validate handlers in JourneyBuilder.tsx.
 *
 * All functions are side-effect free so they can be unit tested in
 * isolation; the React-Flow component imports them but does not
 * mutate anything they own.
 */

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/** Minimal tool descriptor the builder needs from the registry response. */
export interface BuilderTool {
  name: string;
  description: string;
  risk_level: string;
  parameters: Record<string, any>;
  group: string;
  tags: string[];
  connector_api: string | null;
  /** Phase 1 -- registry namespace this tool lives in (e.g. ``customer-360``). */
  bucket?: string;
  /** Phase 1 -- declared output channels; one handle per relationship. */
  output_relationships?: BuilderToolRelationship[];
}

/** One named output channel a tool may emit on. */
export interface BuilderToolRelationship {
  name: string;
  description?: string;
  auto_terminate_default?: boolean;
}

/** Per-tool relationship catalogue from GET /journey-builder/tool-relationships. */
export type ToolRelationships = Record<string, BuilderToolRelationship[]>;

/** One node on the canvas. ``data`` carries the per-step authoring state. */
export interface BuilderNode {
  id: string;
  type: 'tool';
  position: { x: number; y: number };
  data: BuilderNodeData;
}

export interface BuilderNodeData {
  /** The tool this node dispatches. */
  tool: string;
  /** Author-facing display name (defaults to ``tool``). */
  name: string;
  /** Raw params dict. May contain ``${steps.X.y}`` placeholders. */
  params: Record<string, any>;
  /** Optional foreach expression -- preserved on save. */
  foreach?: string;
  /** Mirrors ``StepDoc.requires_approval``. */
  requires_approval?: boolean;
  /** Tool descriptor cached at drop time for handle / hint rendering. */
  toolDef?: BuilderTool;
}

/** One edge between two tool nodes' output and input ports. */
export interface BuilderGraphEdge {
  id: string;
  source: string;        // source node id
  target: string;        // target node id
  /** Source handle id -- formatted as ``out:<dotted-key>``. */
  sourceHandle: string;
  /** Target handle id -- formatted as ``in:<param-name>``. */
  targetHandle: string;
}

/** One stage's slice of builder state when serialised to the wire. */
export interface BuilderStageWire {
  stage_id: string;
  name?: string;
  order: number;
  steps: Array<{
    id: string;
    name: string;
    tool: string;
    params: Record<string, any>;
    foreach?: string;
    requires_approval?: boolean;
  }>;
  edges: Array<{
    from_node: string;
    from_key: string;
    to_node: string;
    to_param: string;
  }>;
  connections: Array<{
    from_step: string;
    from_relationship: string;
    to_step: string;
    to_param: string;
    from_path?: string;
  }>;
}

/** Wire body for POST /journey-builder/{save,run,validate}. */
export interface BuilderRequest {
  name: string;
  display_name: string;
  description: string;
  trigger: string;
  steps: Array<{
    id: string;
    name: string;
    tool: string;
    params: Record<string, any>;
    foreach?: string;
    requires_approval?: boolean;
  }>;
  /**
   * Multi-stage payload. When present, the backend ignores the flat
   * ``steps`` / ``edges`` / ``connections`` lists above. When empty,
   * the legacy single-stage path produces a ``main`` stage from the
   * flat fields.
   */
  stages?: BuilderStageWire[];
  /**
   * Legacy wire format -- ``from_key`` is the dotted output path
   * (``results.0.customer_id``). The backend translates these into
   * ``${steps.X.y}`` placeholders.
   */
  edges: Array<{
    from_node: string;
    from_key: string;
    to_node: string;
    to_param: string;
  }>;
  /**
   * Phase 1 wire format -- explicit relationship-routed dataflow edges.
   * ``from_relationship`` is one of the producer tool's declared output
   * relationships; ``from_path`` is the optional dotted accessor into
   * that relationship's payload.
   *
   * The backend prefers ``connections`` over ``edges`` when present;
   * leaving this empty keeps older UI builds working unchanged.
   */
  connections?: Array<{
    from_step: string;
    from_relationship: string;
    to_step: string;
    to_param: string;
    from_path?: string;
  }>;
  /** Phase 1 -- registry bucket this journey belongs to. */
  bucket?: string;
  /** Execution-mode discriminator (sequential | dataflow). */
  execution_mode?: 'sequential' | 'dataflow';
  solution_id?: string;
  inputs?: Record<string, any>;
}

/** Shape returned by POST /journey-builder/validate. */
export interface BuilderValidationReport {
  valid: boolean;
  errors: string[];
  warnings: string[];
  report?: {
    errors: ValidationIssue[];
    warnings: ValidationIssue[];
  };
}

export interface ValidationIssue {
  severity: 'error' | 'warning';
  path: string;
  code: string;
  message: string;
}

/** Per-tool output port catalogue returned by GET /journey-builder/tool-outputs. */
export interface OutputHint {
  key: string;
  kind: string;
  desc: string;
}

export type ToolOutputHints = Record<string, OutputHint[]>;

// ---------------------------------------------------------------------------
// Handle id encoding
// ---------------------------------------------------------------------------
//
// React-Flow needs unique handle ids per node. We encode the
// producer-side as ``out:<dotted-key>`` and consumer-side as
// ``in:<param-name>`` so the canvas can decode them when serialising
// edges back to the wire format.

export const OUT_HANDLE_PREFIX = 'out:';
export const IN_HANDLE_PREFIX = 'in:';

export function encodeOutputHandle(key: string): string {
  return `${OUT_HANDLE_PREFIX}${key}`;
}

export function decodeOutputHandle(handleId: string | null | undefined): string | null {
  if (!handleId || !handleId.startsWith(OUT_HANDLE_PREFIX)) return null;
  return handleId.slice(OUT_HANDLE_PREFIX.length);
}

export function encodeInputHandle(param: string): string {
  return `${IN_HANDLE_PREFIX}${param}`;
}

export function decodeInputHandle(handleId: string | null | undefined): string | null {
  if (!handleId || !handleId.startsWith(IN_HANDLE_PREFIX)) return null;
  return handleId.slice(IN_HANDLE_PREFIX.length);
}

// ---------------------------------------------------------------------------
// BuilderState -> BuilderRequest
// ---------------------------------------------------------------------------

/**
 * Serialise the canvas state into the wire shape the backend expects.
 *
 * The graph layout (x/y positions) is intentionally NOT round-tripped
 * to the backend -- positions are pure UI affordance. We do drop nodes
 * whose ``data.tool`` is empty to keep the JourneyDoc clean.
 */
export function toBuilderRequest(args: {
  nodes: BuilderNode[];
  edges: BuilderGraphEdge[];
  name: string;
  displayName?: string;
  description?: string;
  trigger?: string;
  inputs?: Record<string, any>;
  solutionId?: string;
  /** Phase 1 -- registry bucket. */
  bucket?: string;
  /** Execution-mode discriminator. ``sequential`` forces an empty
   * connections list on the wire (the backend would also reject
   * connections in sequential mode but emitting [] is cleaner). */
  executionMode?: 'sequential' | 'dataflow';
  /** Phase 1 -- ``tool_name -> declared relationships``. When supplied,
   * edges whose source-handle decodes to a declared relationship are
   * emitted as ConnectionDocs (in addition to the legacy ``edges``
   * wire format which the backend still honors as a fallback). */
  toolRelationships?: ToolRelationships;
}): BuilderRequest {
  const validNodes = args.nodes.filter((n) => !!n.data?.tool);
  const validIds = new Set(validNodes.map((n) => n.id));
  const nodeToTool = new Map<string, string>();
  for (const n of validNodes) nodeToTool.set(n.id, n.data.tool);

  const rels = args.toolRelationships || {};
  const executionMode: 'sequential' | 'dataflow' = args.executionMode === 'sequential' ? 'sequential' : 'dataflow';
  const isSequential = executionMode === 'sequential';

  return {
    name: args.name || 'Untitled',
    display_name: args.displayName || args.name || 'Untitled',
    description: args.description || '',
    trigger: args.trigger || 'manual',
    solution_id: args.solutionId || 'builder',
    bucket: args.bucket || 'default',
    execution_mode: executionMode,
    inputs: args.inputs,
    steps: validNodes.map((n) => ({
      id: n.id,
      name: n.data.name || n.data.tool,
      tool: n.data.tool,
      params: n.data.params || {},
      foreach: n.data.foreach,
      requires_approval: !!n.data.requires_approval,
    })),
    edges: isSequential
      ? []
      : args.edges
          .filter((e) => validIds.has(e.source) && validIds.has(e.target))
          .map((e) => {
            const fromKey = decodeOutputHandle(e.sourceHandle);
            const toParam = decodeInputHandle(e.targetHandle);
            if (!fromKey || !toParam) return null;
            return {
              from_node: e.source,
              from_key: fromKey,
              to_node: e.target,
              to_param: toParam,
            };
          })
          .filter((e): e is NonNullable<typeof e> => e !== null),
    // Phase 1: every wire becomes a ConnectionDoc carrying the decoded
    // source-handle name as ``from_relationship``. Sequential journeys
    // forcibly emit ``[]`` -- the backend validator rejects connections
    // in sequential mode and the runner's ``_apply_connections`` is
    // bypassed anyway, so emitting an empty list keeps the wire clean.
    connections: isSequential
      ? []
      : args.edges
          .filter((e) => validIds.has(e.source) && validIds.has(e.target))
          .map((e) => {
            const handleName = decodeOutputHandle(e.sourceHandle);
            const toParam = decodeInputHandle(e.targetHandle);
            if (!handleName || !toParam) return null;
            const sourceToolName = nodeToTool.get(e.source);
            const declared = (sourceToolName && rels[sourceToolName]) || [];
            const isDeclared = declared.some((r) => r.name === handleName);
            // Backend ``ConnectionDoc.from_relationship`` is a slug-
            // validated Pydantic field (a-z0-9_- only). Legacy hint-
            // keyed handles (e.g. ``results.0.customer_id``) carry
            // dots / digits-first segments that would 422 the wire
            // out -- coerce them into the default ``success``
            // relationship and stash the dotted path in ``from_path``
            // so the runner can still resolve the value via the
            // substitution fallback.
            const fromRelationship = isDeclared ? handleName : 'success';
            return {
              from_step: e.source,
              from_relationship: fromRelationship,
              to_step: e.target,
              to_param: toParam,
              from_path: isDeclared ? undefined : handleName,
            };
          })
          .filter((c): c is NonNullable<typeof c> => c !== null),
  };
}


// ---------------------------------------------------------------------------
// Multi-stage canvas state (UI-only)
// ---------------------------------------------------------------------------

/**
 * One stage's UI state held by JourneyBuilder. Each stage has its
 * own canvas slot (nodes + edges); switching the active stage swaps
 * the canvas's rendered content. Identity is the stage_id slug.
 */
export interface BuilderStageState {
  /** Stable slug -- becomes ``StageDoc.stage_id``. */
  stageId: string;
  /** Human-readable name (defaults to the slug). */
  name: string;
  /** 1-based execution position; renormalised on save. */
  order: number;
  /** Canvas state for this stage. */
  nodes: BuilderNode[];
  edges: BuilderGraphEdge[];
}

/** Default starting stage when a new builder session opens. */
export function defaultStage(): BuilderStageState {
  return { stageId: 'main', name: 'Main', order: 1, nodes: [], edges: [] };
}

/** Allocate a new stage with a unique slug given the existing list. */
export function newStage(existing: BuilderStageState[], prefix = 'stage'): BuilderStageState {
  const slugs = new Set(existing.map((s) => s.stageId));
  let i = existing.length + 1;
  let slug = `${prefix}_${i}`;
  while (slugs.has(slug)) { i += 1; slug = `${prefix}_${i}`; }
  return {
    stageId: slug,
    name: `Stage ${i}`,
    order: (existing.reduce((m, s) => Math.max(m, s.order), 0) || 0) + 1,
    nodes: [],
    edges: [],
  };
}

/**
 * Serialise the multi-stage canvas into the wire shape.
 *
 * Internally calls ``toBuilderRequest`` (the legacy single-stage
 * serialiser) once per stage to reuse its connection / edge / bucket
 * / executionMode handling, then aggregates the per-stage results.
 *
 * Sequential mode forces ``connections: []`` AND ``edges: []`` on
 * every stage. Dataflow mode emits per-stage ConnectionDocs.
 */
export function toBuilderRequestMultiStage(args: {
  stages: BuilderStageState[];
  name: string;
  displayName?: string;
  description?: string;
  trigger?: string;
  inputs?: Record<string, any>;
  solutionId?: string;
  bucket?: string;
  executionMode?: 'sequential' | 'dataflow';
  toolRelationships?: ToolRelationships;
}): BuilderRequest {
  // Flat top-level fields come from the FIRST stage (back-compat with
  // single-stage consumers that read only the flat ``steps`` list).
  const first = args.stages[0] || defaultStage();
  const base = toBuilderRequest({
    nodes: first.nodes,
    edges: first.edges,
    name: args.name,
    displayName: args.displayName,
    description: args.description,
    trigger: args.trigger,
    inputs: args.inputs,
    solutionId: args.solutionId,
    bucket: args.bucket,
    executionMode: args.executionMode,
    toolRelationships: args.toolRelationships,
  });

  // Per-stage wire slices. Normalise order to 1..N so the runner sees
  // a deterministic sequence.
  const sorted = [...args.stages].sort((a, b) => a.order - b.order);
  base.stages = sorted.map((s, idx) => {
    const slice = toBuilderRequest({
      nodes: s.nodes,
      edges: s.edges,
      name: args.name,
      displayName: args.displayName,
      description: args.description,
      trigger: args.trigger,
      solutionId: args.solutionId,
      bucket: args.bucket,
      executionMode: args.executionMode,
      toolRelationships: args.toolRelationships,
    });
    return {
      stage_id: s.stageId,
      name: s.name,
      order: idx + 1,
      steps: slice.steps,
      edges: slice.edges,
      connections: slice.connections || [],
    };
  });
  return base;
}

// ---------------------------------------------------------------------------
// Sequential-mode vertical chain layout
// ---------------------------------------------------------------------------

/**
 * Compute a vertical 1-column position map for sequential-mode nodes.
 * Nodes are ordered by their topological position from ``topoOrderClient``;
 * cycle / isolated nodes fall back to their order-1 default position so the
 * layout is always deterministic and stable.
 *
 * Constants picked to roughly match the existing canvas spacing.
 */
export function verticalChainLayout(
  nodes: BuilderNode[],
  topoOrder: Map<string, number>,
): Map<string, { x: number; y: number }> {
  const X_COL = 240;
  const Y_GAP = 160;
  const Y_TOP = 40;
  const out = new Map<string, { x: number; y: number }>();

  // Sort nodes by topo position (1, 2, 3, ...) with stable insertion-order
  // tie-break for nodes that lack a position (e.g. when the canvas just
  // initialised and orderByNode hasn't computed yet).
  const positioned = nodes
    .map((n, idx) => ({ n, pos: topoOrder.get(n.id) ?? idx + 1 }))
    .sort((a, b) => a.pos - b.pos);

  positioned.forEach(({ n }, idx) => {
    out.set(n.id, { x: X_COL, y: Y_TOP + idx * Y_GAP });
  });
  return out;
}

// ---------------------------------------------------------------------------
// Apply validation report -> per-node issue map
// ---------------------------------------------------------------------------

/**
 * Walk ``report.errors + report.warnings`` and bucket issues by the
 * step id mentioned in their ``path``. Paths look like
 * ``stages[0].steps[2].bindings[0]`` so we read ``steps[K]`` and map
 * back to the original node id by canvas order.
 */
export function applyValidationToNodes(
  report: BuilderValidationReport | null,
  nodes: BuilderNode[],
): Map<string, ValidationIssue[]> {
  const out = new Map<string, ValidationIssue[]>();
  if (!report?.report) return out;
  const ids = nodes.map((n) => n.id);
  const rx = /steps\[(\d+)\]/;
  const ingest = (iss: ValidationIssue) => {
    const m = rx.exec(iss.path || '');
    if (!m) return;
    const idx = parseInt(m[1], 10);
    if (!Number.isFinite(idx) || idx < 0 || idx >= ids.length) return;
    const nodeId = ids[idx];
    const arr = out.get(nodeId) || [];
    arr.push(iss);
    out.set(nodeId, arr);
  };
  for (const iss of report.report.errors || []) ingest(iss);
  for (const iss of report.report.warnings || []) ingest(iss);
  return out;
}

// ---------------------------------------------------------------------------
// Edge utility -- which target params already have an incoming edge?
// ---------------------------------------------------------------------------

/** Returns the set of ``param-name`` already wired into ``nodeId``. */
export function consumedParamsOf(nodeId: string, edges: BuilderGraphEdge[]): Set<string> {
  const out = new Set<string>();
  for (const e of edges) {
    if (e.target !== nodeId) continue;
    const p = decodeInputHandle(e.targetHandle);
    if (p) out.add(p);
  }
  return out;
}

/** Returns a stable id for a new edge. */
export function makeEdgeId(e: { source: string; target: string; sourceHandle: string; targetHandle: string }): string {
  return `${e.source}|${e.sourceHandle}__${e.target}|${e.targetHandle}`;
}

// ---------------------------------------------------------------------------
// Client-side topological order
// ---------------------------------------------------------------------------

/**
 * Compute the 1-based execution position of every node by walking the
 * same Kahn's algorithm as the backend ``_topo_sort``. Unconnected
 * nodes fall back to their insertion-order position so the canvas
 * still shows a stable ``1 / 2 / 3`` even before edges are drawn.
 *
 * Cycle handling: every node that participates in a cycle is assigned
 * ``-1`` so the UI can flag it with ``!`` instead of a real ordinal.
 * The badge mapping is documentation only; the canonical order is
 * computed server-side on save / run.
 */
export function topoOrderClient(
  nodes: BuilderNode[], edges: BuilderGraphEdge[],
): Map<string, number> {
  const out = new Map<string, number>();
  if (!nodes.length) return out;

  const ids = nodes.map((n) => n.id);
  const inDeg = new Map<string, number>();
  const adj = new Map<string, string[]>();
  for (const id of ids) {
    inDeg.set(id, 0);
    adj.set(id, []);
  }
  for (const e of edges) {
    if (!inDeg.has(e.source) || !inDeg.has(e.target)) continue;
    if (e.source === e.target) continue;          // self-edge -- ignore for ordering
    adj.get(e.source)!.push(e.target);
    inDeg.set(e.target, (inDeg.get(e.target) || 0) + 1);
  }

  // Kahn's algorithm with stable tie-break: leftmost ready node in
  // original insertion order wins.
  const indexOf = new Map<string, number>();
  ids.forEach((id, i) => indexOf.set(id, i));
  const ready: string[] = ids.filter((id) => (inDeg.get(id) || 0) === 0);

  let position = 1;
  const emitted = new Set<string>();
  while (ready.length) {
    ready.sort((a, b) => (indexOf.get(a)! - indexOf.get(b)!));
    const id = ready.shift()!;
    if (emitted.has(id)) continue;
    emitted.add(id);
    out.set(id, position);
    position += 1;
    for (const child of adj.get(id) || []) {
      inDeg.set(child, (inDeg.get(child) || 0) - 1);
      if ((inDeg.get(child) || 0) === 0) {
        ready.push(child);
      }
    }
  }

  // Anything not yet emitted is in a cycle.
  for (const id of ids) {
    if (!emitted.has(id)) out.set(id, -1);
  }
  return out;
}

/** Convenience: ``true`` if any node in the graph is in a cycle. */
export function hasCycle(order: Map<string, number>): boolean {
  for (const v of order.values()) if (v === -1) return true;
  return false;
}
