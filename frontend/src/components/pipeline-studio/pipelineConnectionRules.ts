import type { CatalogNodeType, DataFlowEdge, DataFlowGraph, DataFlowNode } from '@/services/dataFlowService';

/** Categories that may not have incoming data-flow edges (ETL sources). */
const NO_INCOMING = new Set(['sources']);

/** Allowed target categories for each source category (ETL golden path + flow processors). */
const ALLOWED_TARGET: Record<string, Set<string>> = {
  sources: new Set(['transform', 'ai', 'sinks', 'control', 'route', 'nexus']),
  transform: new Set(['transform', 'ai', 'sinks', 'control', 'route', 'nexus']),
  ai: new Set(['transform', 'sinks', 'control', 'route', 'nexus']),
  route: new Set(['transform', 'ai', 'sinks', 'control', 'nexus']),
  nexus: new Set(['transform', 'ai', 'sinks', 'control', 'route', 'nexus']),
  sinks: new Set(['sinks']),
  control: new Set(['transform', 'sinks', 'route', 'nexus']),
};

const LIVE_SOURCE_PREFIXES = [
  'source.social_listening',
  'source.file_uploads',
  'source.google_drive',
  'source.external_full',
  'source.fdw',
  'source.external_feed',
];

export function categoryForType(nodeType: string, catalog: CatalogNodeType[]): string {
  const hit = catalog.find(c => c.type === nodeType);
  if (hit?.category) return hit.category;
  if (nodeType.startsWith('source.')) return 'sources';
  if (nodeType.startsWith('nexus.') || nodeType.startsWith('nifi.')) return 'nexus';
  if (nodeType.startsWith('sink.')) return 'sinks';
  if (nodeType.startsWith('transform.')) return 'transform';
  if (nodeType.startsWith('ai.')) return 'ai';
  if (nodeType.startsWith('route.')) return 'route';
  return 'transform';
}

export function isLiveEtlSource(nodeType: string): boolean {
  return LIVE_SOURCE_PREFIXES.some(p => nodeType === p || nodeType.startsWith(p));
}

export interface ConnectionCheck {
  allowed: boolean;
  reason?: string;
}

export function canConnectNodes(
  source: DataFlowNode,
  target: DataFlowNode,
  catalog: CatalogNodeType[],
): ConnectionCheck {
  if (source.id === target.id) {
    return { allowed: false, reason: 'Cannot connect a step to itself' };
  }
  const srcCat = categoryForType(source.type, catalog);
  const tgtCat = categoryForType(target.type, catalog);

  if (NO_INCOMING.has(tgtCat) && tgtCat === 'sources') {
    return { allowed: false, reason: 'Sources cannot receive incoming connections' };
  }
  const allowed = ALLOWED_TARGET[srcCat];
  if (!allowed || !allowed.has(tgtCat)) {
    return {
      allowed: false,
      reason: `Invalid link: ${srcCat} cannot connect to ${tgtCat}`,
    };
  }
  if (srcCat === 'sources' && categoryForType(target.type, catalog) === 'sources') {
    return { allowed: false, reason: 'Connect transforms or sinks after a source, not another source' };
  }
  return { allowed: true };
}

export function isValidGraphConnection(
  sourceId: string,
  targetId: string,
  graph: DataFlowGraph,
  catalog: CatalogNodeType[],
): ConnectionCheck {
  const source = graph.nodes.find(n => n.id === sourceId);
  const target = graph.nodes.find(n => n.id === targetId);
  if (!source || !target) {
    return { allowed: false, reason: 'Unknown node' };
  }
  const dup = graph.edges.some(e => e.source === sourceId && e.target === targetId);
  if (dup) {
    return { allowed: false, reason: 'Connection already exists' };
  }
  return canConnectNodes(source, target, catalog);
}

/** Prefer selected node, else last node that can legally connect to the new type. */
export function resolveChainedSourceNodeId(
  graph: DataFlowGraph,
  newNodeType: string,
  catalog: CatalogNodeType[],
  selectedNodeId: string | null,
): string | null {
  const newCat = categoryForType(newNodeType, catalog);
  if (NO_INCOMING.has(newCat)) {
    return null;
  }

  if (selectedNodeId) {
    const selected = graph.nodes.find(n => n.id === selectedNodeId);
    const draft: DataFlowNode = {
      id: '__draft__',
      type: newNodeType,
      params: {},
    };
    if (selected && canConnectNodes(selected, draft, catalog).allowed) {
      return selected.id;
    }
  }

  for (let i = graph.nodes.length - 1; i >= 0; i -= 1) {
    const candidate = graph.nodes[i];
    const draft: DataFlowNode = { id: '__draft__', type: newNodeType, params: {} };
    if (canConnectNodes(candidate, draft, catalog).allowed) {
      return candidate.id;
    }
  }
  return null;
}

export function addPaletteNodeWithRules(
  graph: DataFlowGraph,
  nodeType: string,
  catalog: CatalogNodeType[],
  selectedNodeId: string | null,
  extraParams?: Record<string, unknown>,
  labelOverride?: string,
): DataFlowGraph {
  const cat = catalog.find(c => c.type === nodeType);
  const id = `n-${nodeType.replace(/\./g, '_')}-${crypto.randomUUID().slice(0, 8)}`;
  const y = graph.nodes.reduce((m, n) => Math.max(m, n.ui?.position?.y ?? 0), 0) + 120;
  const node: DataFlowNode = {
    id,
    type: nodeType,
    params: { ...(cat?.defaultParams ?? {}), ...(extraParams ?? {}) },
    ui: { position: { x: 120, y }, label: labelOverride || cat?.label || nodeType },
  };
  const edges = [...graph.edges];
  const fromId = resolveChainedSourceNodeId(graph, nodeType, catalog, selectedNodeId);
  if (fromId) {
    const check = isValidGraphConnection(fromId, id, { ...graph, nodes: [...graph.nodes, node] }, catalog);
    if (check.allowed) {
      edges.push({ id: `e-${fromId}-${id}`, source: fromId, target: id, relationship: 'success' });
    }
  }
  return { ...graph, nodes: [...graph.nodes, node], edges };
}