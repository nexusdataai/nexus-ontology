import { forwardRef, useCallback, useImperativeHandle, useMemo } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Controls,
  Background,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type Node,
  type NodeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import PipelineNode from './PipelineNode';
import type { DataFlowEdge, DataFlowGraph, DataFlowNode } from '@/services/dataFlowService';
import type { CatalogNodeType } from '@/services/dataFlowService';
import { nodeLabel } from './pipelineStudioState';

const nodeTypes: NodeTypes = { pipeline: PipelineNode };

export interface PipelineCanvasHandle {
  getGraph: () => DataFlowGraph;
}

function toFlowNodes(nodes: DataFlowNode[], catalog: CatalogNodeType[]): Node[] {
  return nodes.map(n => {
    const cat = catalog.find(c => c.type === n.type);
    return {
      id: n.id,
      type: 'pipeline',
      position: n.ui?.position ?? { x: 0, y: 0 },
      data: {
        label: n.ui?.label || nodeLabel(n.type, catalog),
        nodeType: n.type,
        icon: cat?.icon,
        proposed: n.ui?.proposed,
        autoInserted: n.autoInserted,
        params: n.params,
      },
    };
  });
}

function fromFlowNodes(flowNodes: Node[]): DataFlowNode[] {
  return flowNodes.map(n => ({
    id: n.id,
    type: String((n.data as { nodeType?: string }).nodeType ?? 'transform.filter'),
    params: (n.data as { params?: Record<string, unknown> }).params ?? {},
    ui: {
      position: n.position,
      label: String((n.data as { label?: string }).label ?? ''),
      proposed: Boolean((n.data as { proposed?: boolean }).proposed),
    },
    autoInserted: Boolean((n.data as { autoInserted?: boolean }).autoInserted),
  }));
}

interface InnerProps {
  graph: DataFlowGraph;
  catalog: CatalogNodeType[];
  onGraphChange: (g: DataFlowGraph) => void;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
}

const Inner = forwardRef<PipelineCanvasHandle, InnerProps>(function Inner(
  { graph, catalog, onGraphChange, selectedNodeId, onSelectNode },
  ref,
) {
  const flowNodes = useMemo(() => toFlowNodes(graph.nodes, catalog), [graph.nodes, catalog]);
  const flowEdges: Edge[] = useMemo(
    () =>
      graph.edges.map(e => ({
        ...e,
        type: 'smoothstep',
        label: e.relationship || 'success',
        data: { relationship: e.relationship || 'success' },
      })),
    [graph.edges],
  );

  const emit = useCallback(
    (nodes: Node[], edges: Edge[]) => {
      onGraphChange({
        ...graph,
        nodes: fromFlowNodes(nodes),
        edges: edges.map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle ?? undefined,
          targetHandle: e.targetHandle ?? undefined,
          relationship: (e.data as { relationship?: string })?.relationship ?? 'success',
        })),
      });
    },
    [graph, onGraphChange],
  );

  useImperativeHandle(ref, () => ({
    getGraph: () => graph,
  }));

  const onNodesChange = useCallback(
    (changes: Parameters<typeof applyNodeChanges>[0]) => {
      const next = applyNodeChanges(changes, flowNodes);
      emit(next, flowEdges);
    },
    [emit, flowEdges, flowNodes],
  );

  const onEdgesChange = useCallback(
    (changes: Parameters<typeof applyEdgeChanges>[0]) => {
      const next = applyEdgeChanges(changes, flowEdges);
      emit(flowNodes, next);
    },
    [emit, flowEdges, flowNodes],
  );

  const onConnect = useCallback(
    (conn: Connection) => {
      const next = addEdge({ ...conn, id: `e-${conn.source}-${conn.target}` }, flowEdges);
      emit(flowNodes, next);
    },
    [emit, flowEdges, flowNodes],
  );

  return (
    <ReactFlow
      nodes={flowNodes.map(n => ({ ...n, selected: n.id === selectedNodeId }))}
      edges={flowEdges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={(_, n) => onSelectNode(n.id)}
      onPaneClick={() => onSelectNode(null)}
      fitView
      proOptions={{ hideAttribution: true }}
    >
      <Controls showInteractive={false} />
      <Background gap={16} />
    </ReactFlow>
  );
});

export default function PipelineGraphCanvas(props: InnerProps & { canvasRef?: React.Ref<PipelineCanvasHandle> }) {
  const { canvasRef, ...rest } = props;
  return (
    <ReactFlowProvider>
      <motion className="h-full w-full min-h-[420px]">
        <Inner ref={canvasRef} {...rest} />
      </motion>
    </ReactFlowProvider>
  );
}

function motion({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={className}>{children}</div>;
}

export function addPaletteNode(
  graph: DataFlowGraph,
  nodeType: string,
  catalog: CatalogNodeType[],
  extraParams?: Record<string, unknown>,
  labelOverride?: string,
): DataFlowGraph {
  const cat = catalog.find(c => c.type === nodeType);
  const id = `n-${nodeType}-${crypto.randomUUID().slice(0, 8)}`;
  const y = graph.nodes.reduce((m, n) => Math.max(m, n.ui?.position?.y ?? 0), 0) + 120;
  const node: DataFlowNode = {
    id,
    type: nodeType,
    params: { ...(cat?.defaultParams ?? {}), ...(extraParams ?? {}) },
    ui: { position: { x: 120, y }, label: labelOverride || nodeLabel(nodeType, catalog) },
  };
  const edges = [...graph.edges];
  const last = graph.nodes[graph.nodes.length - 1];
  if (last) {
    edges.push({ id: `e-${last.id}-${id}`, source: last.id, target: id });
  }
  return { ...graph, nodes: [...graph.nodes, node], edges };
}