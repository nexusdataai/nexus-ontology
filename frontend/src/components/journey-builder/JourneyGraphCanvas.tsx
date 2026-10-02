import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useState, type DragEvent } from 'react';
import {
  ReactFlow, ReactFlowProvider, Background, Controls,
  addEdge, applyEdgeChanges, applyNodeChanges,
  type Connection, type Edge, type EdgeChange, type EdgeTypes, type Node, type NodeChange, type NodeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import ToolNode from './ToolNode';
import DeletableEdge from './DeletableEdge';
import {
  applyValidationToNodes, makeEdgeId, decodeInputHandle, decodeOutputHandle,
  encodeInputHandle, encodeOutputHandle, topoOrderClient, verticalChainLayout,
  type BuilderGraphEdge, type BuilderNode, type BuilderNodeData, type BuilderTool,
  type BuilderValidationReport, type ToolOutputHints, type ValidationIssue,
} from './builderState';

// React-Flow v12 typings: Node.data is ``Record<string, unknown>`` by
// default; widen our generic so the canvas can read structured fields
// without ``as unknown as`` casts everywhere.
type CanvasNode = Node<BuilderNodeData & Record<string, unknown>, 'tool'>;

// ---------------------------------------------------------------------------
// Public ref API consumed by JourneyBuilder.tsx
// ---------------------------------------------------------------------------

export interface CanvasState {
  nodes: BuilderNode[];
  edges: BuilderGraphEdge[];
}

export interface JourneyGraphCanvasHandle {
  getState: () => CanvasState;
  setSelectedNode: (id: string | null) => void;
  /** Apply a partial patch to a node's ``data`` (params / name / foreach...). */
  patchNode: (id: string, patch: Partial<BuilderNodeData>) => void;
  /**
   * Idempotently upsert an edge from one node's output key to another
   * node's input param. Mirrors the on-canvas drag path: replaces any
   * existing edge into ``(toNode, toParam)`` so each input port has
   * at most one producer; writes ``${steps.<fromNode>.<fromKey>}``
   * into the consumer's params dict.
   */
  setEdge: (input: { fromNode: string; fromKey: string; toNode: string; toParam: string }) => void;
  /** Remove the edge feeding ``(toNode, toParam)`` and clear the corresponding param placeholder. */
  removeEdgeForTarget: (toNode: string, toParam: string) => void;
  /** Cancel an in-progress click-to-connect. Safe to call when none is pending. */
  cancelConnection: () => void;
}

/** State of an in-progress click-to-connect session. */
export interface PendingConnection {
  nodeId: string;
  key: string;
  /** Resolved tool name for the banner ("find_churning_customers" etc.). */
  toolName: string;
}

interface Props {
  /** Output-hints map keyed by tool name; injected via /tool-outputs endpoint. */
  outputHints: ToolOutputHints;
  /** Validation report from the last Validate / Save round-trip. */
  validation: BuilderValidationReport | null;
  /** Called when the user clicks a node so the right pane can edit it. */
  onSelectionChange: (nodeId: string | null) => void;
  /** External lookup so the canvas can resolve a tool by name on drop. */
  resolveTool: (name: string) => BuilderTool | null;
  /** Fires when click-to-connect mode begins or ends so the parent can render a banner. */
  onPendingConnectionChange?: (pending: PendingConnection | null) => void;
  /** Execution-mode discriminator. ``sequential`` hides port handles,
   * disables connection drawing, and auto-arranges nodes in a vertical
   * chain. ``dataflow`` (default) is the existing graph-editor canvas.
   */
  executionMode?: 'sequential' | 'dataflow';
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

let _idCounter = 0;
function nextNodeId(): string {
  _idCounter += 1;
  return `s${Date.now().toString(36)}${_idCounter}`;
}

const NODE_TYPES: NodeTypes = { tool: ToolNode } as NodeTypes;

// Custom edge with a midpoint "x" delete button (discoverability fix:
// users can now remove a mis-wired chain without opening the Step
// Editor). Applied as the default edge type.
const EDGE_TYPES: EdgeTypes = { deletable: DeletableEdge };

const FIT_VIEW_OPTIONS = { padding: 0.2 } as const;

// Keyboard delete: Backspace or Delete with an edge / node selected
// removes it. React-Flow re-emits the change through onEdgesChange /
// onNodesChange so our onEdgesDelete handler still fires.
const DELETE_KEY_CODES = ['Backspace', 'Delete'];

// ---------------------------------------------------------------------------

const JourneyGraphCanvasInner = forwardRef<JourneyGraphCanvasHandle, Props>(function JourneyGraphCanvasInner(
  props,
  ref,
) {
  const {
    outputHints, validation, onSelectionChange, resolveTool,
    onPendingConnectionChange, executionMode,
  } = props;
  const isSequential = executionMode === 'sequential';

  const [nodes, setNodes] = useState<CanvasNode[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  /**
   * Click-to-connect cursor. When non-null, the next click on an input
   * port completes the wire; pane click or Escape cancels.
   */
  const [connectingFrom, setConnectingFrom] = useState<PendingConnection | null>(null);

  // ---- imperative handle: parent component reads canvas state via ref ----

  useImperativeHandle(
    ref,
    () => ({
      getState: () => ({
        nodes: nodes.map(_toBuilderNode),
        edges: edges.map(_toBuilderEdge),
      }),
      setSelectedNode: (id) => setSelectedId(id),
      patchNode: (id, patch) => {
        setNodes((curr) => curr.map((n) =>
          n.id === id
            ? { ...n, data: { ...n.data, ...patch } as BuilderNodeData & Record<string, unknown> }
            : n,
        ));
      },
      setEdge: ({ fromNode, fromKey, toNode, toParam }) => {
        const sourceHandle = encodeOutputHandle(fromKey);
        const targetHandle = encodeInputHandle(toParam);
        const id = makeEdgeId({ source: fromNode, target: toNode, sourceHandle, targetHandle });
        setEdges((curr) => {
          // Drop any edge that previously fed the same target param.
          const without = curr.filter((e) =>
            !(e.target === toNode && e.targetHandle === targetHandle));
          return addEdge(
            { id, source: fromNode, target: toNode, sourceHandle, targetHandle, type: 'deletable', animated: true },
            without,
          );
        });
        // Mirror the wire into the consumer node's params so the JSON
        // editor + on-canvas badge agree without needing a save.
        setNodes((curr) =>
          curr.map((n) =>
            n.id === toNode
              ? {
                  ...n,
                  data: {
                    ...n.data,
                    params: {
                      ...(n.data.params || {}),
                      [toParam]: `\${steps.${fromNode}.${fromKey}}`,
                    },
                  } as BuilderNodeData & Record<string, unknown>,
                }
              : n,
          ),
        );
      },
      removeEdgeForTarget: (toNode, toParam) => {
        const targetHandle = encodeInputHandle(toParam);
        setEdges((curr) =>
          curr.filter((e) => !(e.target === toNode && e.targetHandle === targetHandle)),
        );
        // Strip the ${steps.X.y} placeholder if it's the current value
        // for that param (don't disturb literal user input that
        // happens to share the key name).
        setNodes((curr) =>
          curr.map((n) => {
            if (n.id !== toNode) return n;
            const params = { ...(n.data.params || {}) };
            const v = params[toParam];
            if (typeof v === 'string' && /^\$\{\s*steps\./.test(v.trim())) {
              delete params[toParam];
            }
            return {
              ...n,
              data: { ...n.data, params } as BuilderNodeData & Record<string, unknown>,
            };
          }),
        );
      },
      cancelConnection: () => {
        setConnectingFrom(null);
        onPendingConnectionChange?.(null);
      },
    }),
    [nodes, edges, onPendingConnectionChange],
  );

  // ---- click-to-connect helpers ----

  /** Click handler for output ports inside ToolNode. */
  const beginConnection = useCallback(
    (input: { nodeId: string; key: string; toolName: string }) => {
      const pending: PendingConnection = input;
      setConnectingFrom(pending);
      onPendingConnectionChange?.(pending);
    },
    [onPendingConnectionChange],
  );

  /**
   * Click handler for input ports inside ToolNode. Only completes the
   * wire when ``connectingFrom`` is non-null. Returns true if the wire
   * was completed so the caller can stop the click from bubbling.
   */
  const completeConnection = useCallback(
    (input: { nodeId: string; param: string }) => {
      if (!connectingFrom) return false;
      // Skip self-connections; React Flow allows them but the runner
      // would topo-fail anyway.
      if (connectingFrom.nodeId === input.nodeId) {
        setConnectingFrom(null);
        onPendingConnectionChange?.(null);
        return false;
      }
      const sourceHandle = encodeOutputHandle(connectingFrom.key);
      const targetHandle = encodeInputHandle(input.param);
      const id = makeEdgeId({
        source: connectingFrom.nodeId, target: input.nodeId,
        sourceHandle, targetHandle,
      });
      setEdges((curr) => {
        const without = curr.filter((e) =>
          !(e.target === input.nodeId && e.targetHandle === targetHandle));
        return addEdge(
          {
            id, source: connectingFrom.nodeId, target: input.nodeId,
            sourceHandle, targetHandle, type: 'deletable', animated: true,
          },
          without,
        );
      });
      setNodes((curr) =>
        curr.map((n) =>
          n.id === input.nodeId
            ? {
                ...n,
                data: {
                  ...n.data,
                  params: {
                    ...(n.data.params || {}),
                    [input.param]: `\${steps.${connectingFrom.nodeId}.${connectingFrom.key}}`,
                  },
                } as BuilderNodeData & Record<string, unknown>,
              }
            : n,
        ),
      );
      setConnectingFrom(null);
      onPendingConnectionChange?.(null);
      return true;
    },
    [connectingFrom, onPendingConnectionChange],
  );

  const cancelConnection = useCallback(() => {
    setConnectingFrom(null);
    onPendingConnectionChange?.(null);
  }, [onPendingConnectionChange]);

  // Bind Escape so the user can always back out.
  useEffect(() => {
    if (!connectingFrom) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') cancelConnection();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [connectingFrom, cancelConnection]);

  // ---- per-node issue map computed once per validation report ----

  const issuesByNode: Map<string, ValidationIssue[]> = useMemo(
    () => applyValidationToNodes(validation, nodes.map(_toBuilderNode)),
    [validation, nodes],
  );

  // ---- topological position per node (drives the "1 / 2 / 3" badge) ----

  const orderByNode: Map<string, number> = useMemo(
    () => topoOrderClient(nodes.map(_toBuilderNode), edges.map(_toBuilderEdge)),
    [nodes, edges],
  );

  // ---- enrich every node's data with edges / issues / hints / order / delete --
  //
  // Selection is handled at the canvas level via ``onNodeClick`` below
  // (the wrapper-onClick path clashed with React-Flow's pan/drag).

  // Sequential mode pins nodes to a vertical 1-column chain so they
  // render as a list (no x scatter). Recomputed whenever node IDs or
  // topo order change.
  const sequentialPositions = useMemo(
    () => isSequential ? verticalChainLayout(nodes.map(_toBuilderNode), orderByNode) : null,
    [isSequential, nodes, orderByNode],
  );

  // Sequential mode also renders non-editable visual edges between
  // consecutive nodes so the execution order is immediately clear.
  // These edges are NEVER persisted to JourneyDoc.connections (that's
  // a dataflow-only field) -- they exist purely for the canvas.
  const sequentialDisplayEdges: Edge[] = useMemo(() => {
    if (!isSequential) return [];
    const ordered = nodes
      .map((n) => ({ id: n.id, pos: orderByNode.get(n.id) ?? Number.MAX_SAFE_INTEGER }))
      .filter((r) => r.pos > 0) // skip cycle members (pos = -1)
      .sort((a, b) => a.pos - b.pos);
    const out: Edge[] = [];
    for (let i = 0; i < ordered.length - 1; i += 1) {
      out.push({
        id: `seq:${ordered[i].id}->${ordered[i + 1].id}`,
        source: ordered[i].id,
        target: ordered[i + 1].id,
        type: 'smoothstep',
        animated: false,
        // Muted style to distinguish from dataflow connections.
        style: { strokeWidth: 1.5, strokeDasharray: '4 4', opacity: 0.7 },
        // No handle ids -- React-Flow falls back to node centroid.
        selectable: false,
        focusable: false,
        deletable: false,
      });
    }
    return out;
  }, [isSequential, nodes, orderByNode]);

  const decoratedNodes: CanvasNode[] = useMemo(
    () =>
      nodes.map((n) => {
        const td = n.data.toolDef;
        const seqPos = sequentialPositions?.get(n.id);
        return {
          ...n,
          ...(seqPos ? { position: seqPos } : {}),
          selected: n.id === selectedId,
          data: {
            ...n.data,
            __edges: edges.map(_toBuilderEdge),
            __issues: issuesByNode.get(n.id) || [],
            __outputHints: td ? outputHints[td.name] || outputHints[n.data.tool] || [] : [],
            __order: orderByNode.get(n.id),
            __pendingConnection: connectingFrom,
            __beginConnection: (key: string) =>
              beginConnection({ nodeId: n.id, key, toolName: n.data.tool }),
            __completeConnection: (param: string) =>
              completeConnection({ nodeId: n.id, param }),
            __hideHandles: isSequential,
            __onDelete: (id: string) => {
              setNodes((curr) => curr.filter((x) => x.id !== id));
              setEdges((curr) => curr.filter((e) => e.source !== id && e.target !== id));
              if (selectedId === id) {
                setSelectedId(null);
                onSelectionChange(null);
              }
            },
          } as BuilderNodeData & Record<string, unknown>,
        };
      }),
    [nodes, edges, issuesByNode, outputHints, orderByNode, selectedId, onSelectionChange,
     connectingFrom, beginConnection, completeConnection, isSequential, sequentialPositions],
  );

  // ---- React-Flow handlers ----

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds) as CanvasNode[]),
    [],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [],
  );

  /**
   * Fires when React-Flow removes one or more edges (delete button on
   * the custom edge, or keyboard Delete / Backspace). Mirrors the
   * inverse of ``onConnect``: strip the ``${steps.X.y}`` placeholder
   * from the consumer node so the param falls back to whatever
   * literal value the user had (or empty).
   */
  const onEdgesDelete = useCallback(
    (deleted: Edge[]) => {
      if (!deleted.length) return;
      setNodes((curr) =>
        curr.map((n) => {
          // Collect all params on this node whose incoming wire just got removed.
          const affected = deleted
            .filter((edge) => edge.target === n.id)
            .map((edge) => decodeInputHandle(edge.targetHandle))
            .filter((p): p is string => !!p);
          if (affected.length === 0) return n;
          const params = { ...(n.data.params || {}) };
          for (const p of affected) {
            const v = params[p];
            if (typeof v === 'string' && /^\$\{\s*steps\./.test(v.trim())) {
              delete params[p];
            }
          }
          return {
            ...n,
            data: { ...n.data, params } as BuilderNodeData & Record<string, unknown>,
          };
        }),
      );
    },
    [],
  );

  const onConnect = useCallback(
    (conn: Connection) => {
      const fromKey = decodeOutputHandle(conn.sourceHandle);
      const toParam = decodeInputHandle(conn.targetHandle);
      if (!fromKey || !toParam || !conn.source || !conn.target) return;
      const id = makeEdgeId({
        source: conn.source!, target: conn.target!,
        sourceHandle: conn.sourceHandle!, targetHandle: conn.targetHandle!,
      });
      setEdges((curr) => {
        // Replace any existing edge into the same (target, to_param) so
        // each input port has at most one producer.
        const without = curr.filter((e) =>
          !(e.target === conn.target && e.targetHandle === conn.targetHandle));
        return addEdge(
          { ...conn, id, type: 'deletable', animated: true },
          without,
        );
      });
      // Mirror the wire into the consumer's params so the per-node JSON
      // editor reflects the chain even before Save.
      setNodes((curr) =>
        curr.map((n) =>
          n.id === conn.target
            ? {
                ...n,
                data: {
                  ...n.data,
                  params: {
                    ...(n.data.params || {}),
                    [toParam]: `\${steps.${conn.source}.${fromKey}}`,
                  },
                } as BuilderNodeData & Record<string, unknown>,
              }
            : n,
        ),
      );
    },
    [],
  );

  // ---- drop target for palette drags ----

  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      const toolName = e.dataTransfer.getData('application/x-tool-name');
      if (!toolName) return;
      const tool = resolveTool(toolName);
      if (!tool) return;
      const rect = (e.target as HTMLElement).getBoundingClientRect();
      const position = {
        x: Math.max(0, e.clientX - rect.left - 140),
        y: Math.max(0, e.clientY - rect.top - 40),
      };
      const id = nextNodeId();
      const data: BuilderNodeData = {
        tool: tool.name,
        name: tool.name,
        params: {},
        requires_approval: false,
        toolDef: tool,
      };
      const newNode: CanvasNode = {
        id, type: 'tool', position,
        data: data as BuilderNodeData & Record<string, unknown>,
      };
      setNodes((curr) => [...curr, newNode]);
      setSelectedId(id);
      onSelectionChange(id);
    },
    [resolveTool, onSelectionChange],
  );

  // ---- propagate selection clears (background click) ----

  const onPaneClick = useCallback(() => {
    setSelectedId(null);
    onSelectionChange(null);
    // A click on empty canvas also cancels click-to-connect so the
    // user can back out without hunting for the source port.
    if (connectingFrom) {
      setConnectingFrom(null);
      onPendingConnectionChange?.(null);
    }
  }, [onSelectionChange, connectingFrom, onPendingConnectionChange]);

  // ---- canvas-level node click: drives selection without colliding
  // with React-Flow's pan / drag handlers ----

  const onNodeClick = useCallback(
    (_e: unknown, node: { id: string }) => {
      setSelectedId(node.id);
      onSelectionChange(node.id);
    },
    [onSelectionChange],
  );

  // ---- effect: keep selection valid if a node disappears ----

  useEffect(() => {
    if (selectedId && !nodes.some((n) => n.id === selectedId)) {
      setSelectedId(null);
      onSelectionChange(null);
    }
  }, [nodes, selectedId, onSelectionChange]);

  return (
    <div className="w-full h-full" onDrop={onDrop} onDragOver={onDragOver}>
      <ReactFlow
        nodes={decoratedNodes}
        edges={isSequential ? sequentialDisplayEdges : edges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        nodesConnectable={!isSequential}
        edgesFocusable={!isSequential}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onEdgesDelete={onEdgesDelete}
        onConnect={isSequential ? undefined : onConnect}
        onPaneClick={onPaneClick}
        onNodeClick={onNodeClick}
        deleteKeyCode={DELETE_KEY_CODES}
        fitView
        fitViewOptions={FIT_VIEW_OPTIONS}
        defaultEdgeOptions={{ type: 'deletable', animated: true, style: { strokeWidth: 1.75 } }}
      >
        <Background gap={20} size={1} />
        <Controls position="bottom-left" showInteractive={false} />
      </ReactFlow>
    </div>
  );
});

// ---------------------------------------------------------------------------
// Wrap in a Provider so multiple canvases on a page (none today, but
// keeps the API stable) each have their own internal state.
// ---------------------------------------------------------------------------

export const JourneyGraphCanvas = forwardRef<JourneyGraphCanvasHandle, Props>(function JourneyGraphCanvas(
  props,
  ref,
) {
  return (
    <ReactFlowProvider>
      <JourneyGraphCanvasInner {...props} ref={ref} />
    </ReactFlowProvider>
  );
});

export default JourneyGraphCanvas;

// ---------------------------------------------------------------------------
// Conversion helpers (kept private to the canvas)
// ---------------------------------------------------------------------------

function _toBuilderNode(n: CanvasNode): BuilderNode {
  const d = n.data;
  return {
    id: n.id,
    type: 'tool',
    position: n.position,
    data: {
      tool: d.tool,
      name: d.name,
      params: d.params || {},
      foreach: d.foreach,
      requires_approval: d.requires_approval,
      toolDef: d.toolDef,
    },
  };
}

function _toBuilderEdge(e: Edge): BuilderGraphEdge {
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle || '',
    targetHandle: e.targetHandle || '',
  };
}
