import apiClient from './apiClient';
import type { ETLSourceType } from './etlPipelineService';

export interface DataFlowViewport {
  x: number;
  y: number;
  zoom: number;
}

export interface DataFlowNode {
  id: string;
  type: string;
  params?: Record<string, unknown>;
  ui?: { position: { x: number; y: number }; label?: string; proposed?: boolean };
  autoInserted?: boolean;
}

export interface DataFlowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  relationship?: string;
}

export interface DataFlowGraph {
  version?: number;
  draftVersion?: number;
  nodes: DataFlowNode[];
  edges: DataFlowEdge[];
  viewport?: DataFlowViewport;
}

export interface CatalogNodeType {
  type: string;
  category: string;
  label: string;
  description: string;
  icon: string;
  defaultParams?: Record<string, unknown>;
  mapsToRuntimeStep?: string | null;
  requiresSourceTypes?: string[];
  runtime?: 'live' | 'stub';
  properties?: { name: string; displayName?: string }[];
  relationships?: { name: string }[];
  nifiClass?: string;
  bundle?: string;
}

export interface ProposedPatch {
  op: 'add_node' | 'remove_node' | 'update_node' | 'add_edge' | 'remove_edge' | 'update_params';
  node?: DataFlowNode;
  edge?: DataFlowEdge;
  nodeId?: string;
  params?: Record<string, unknown>;
  summary?: string;
}

export const dataFlowService = {
  getCatalog: () => apiClient.get('/api/v1/data-flow/catalog') as Promise<{
    nodeTypes: CatalogNodeType[];
    runtimeStepsBySource: Record<string, { id: string; name: string; description: string }[]>;
    runtimeStepOrder: string[];
  }>,

  validate: (graph: DataFlowGraph) =>
    apiClient.post('/api/v1/data-flow/validate', graph),

  compile: (graph: DataFlowGraph) =>
    apiClient.post('/api/v1/data-flow/compile', graph),

  plan: (graph: DataFlowGraph, prompt: string, journeyId?: string) =>
    apiClient.post('/api/v1/data-flow/plan', { graph, prompt, journeyId }),

  applyPatches: (graph: DataFlowGraph, patches: ProposedPatch[]) =>
    apiClient.post('/api/v1/data-flow/apply-patches', { graph, patches }) as Promise<DataFlowGraph>,

  previewNifiRun: (graph: DataFlowGraph) =>
    apiClient.post('/api/v1/data-flow/nifi/preview-run', graph) as Promise<Record<string, unknown>>,

  getJourneyGraph: (journeyId: string) =>
    apiClient.get(`/api/v1/data-flow/journeys/${journeyId}`) as Promise<{
      journeyId: string;
      graph: DataFlowGraph | null;
      config?: Record<string, unknown>;
      productionGraphSnapshot?: DataFlowGraph;
      draftVersion?: number;
    }>,

  saveJourneyGraph: (journeyId: string, graph: DataFlowGraph, deploy = false, name?: string) =>
    apiClient.put(`/api/v1/data-flow/journeys/${journeyId}`, { graph, deploy, name }),

  createPipeline: (name: string, graph: DataFlowGraph, deploy = false) =>
    apiClient.post('/api/v1/data-flow/pipelines', { name, graph, deploy }) as Promise<{
      success: boolean;
      journeyId: string;
      deployed: boolean;
    }>,
};