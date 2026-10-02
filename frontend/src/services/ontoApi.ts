/**
 * Onto API Client — interfaces with the Semantic RAG backend endpoints.
 */

import { apiClient } from './apiClient';

export interface HybridSearchRequest {
  query: string;
  content_type?: string;
  limit?: number;
  graph_hops?: number;
}

export interface SearchResult {
  source_id: string;
  content_type: string;
  content: string;
  similarity: number;
  metadata: Record<string, any>;
  graph_expanded: boolean;
}

export interface HybridSearchResponse {
  total: number;
  vector_hits: number;
  graph_hits: number;
  by_category: Record<string, SearchResult[]>;
  results: SearchResult[];
}

export interface OntoStats {
  total_embeddings: number;
  onto_documents: number;
  by_content_type: Record<string, number>;
  legacy_embeddings: number;
  last_indexed_at?: string;
}

export interface OntoDocument {
  source_id: string;
  content_type: string;
  content: string;
  metadata: Record<string, any>;
  updated_at?: string;
}

export interface DocumentListResponse {
  documents: OntoDocument[];
  total: number;
  offset: number;
  limit: number;
}

export interface GraphNeighborhood {
  center: string;
  hops: number;
  nodes: { id: string }[];
  edges: { source: string; target: string; type: string; description: string }[];
  neighbor_count: number;
}

export interface PipelineStatus {
  journeyId: string;
  jobId: string;
  status: string;
  progress: number;
  currentStep: string;
  logs: string[];
}

export const ontoApi = {
  async hybridSearch(request: HybridSearchRequest): Promise<HybridSearchResponse> {
    return apiClient.post('/api/v1/control-plane/onto/search', request);
  },

  async getStats(): Promise<OntoStats> {
    return apiClient.get('/api/v1/control-plane/onto/stats');
  },

  async getGraphNeighborhood(ontoId: string, hops: number = 2): Promise<GraphNeighborhood> {
    return apiClient.get(`/api/v1/control-plane/onto/graph/${encodeURIComponent(ontoId)}?hops=${hops}`);
  },

  async listDocuments(params: {
    content_type?: string;
    offset?: number;
    limit?: number;
    q?: string;
  } = {}): Promise<DocumentListResponse> {
    const qs = new URLSearchParams();
    if (params.content_type) qs.set('content_type', params.content_type);
    if (params.offset !== undefined) qs.set('offset', String(params.offset));
    if (params.limit !== undefined) qs.set('limit', String(params.limit));
    if (params.q) qs.set('q', params.q);
    const query = qs.toString();
    return apiClient.get(`/api/v1/control-plane/onto/documents${query ? `?${query}` : ''}`);
  },

  async getDocument(sourceId: string): Promise<OntoDocument> {
    return apiClient.get(`/api/v1/control-plane/onto/documents/${encodeURIComponent(sourceId)}`);
  },

  async listBundles(): Promise<{ bundles: any[]; bucket?: string }> {
    return apiClient.get('/api/v1/control-plane/onto/bundles');
  },

  async createAndRunPipeline(): Promise<{ journey_id: string; job_id: string }> {
    const ts = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '');

    // Step 1: Create journey (requires at least one stage in payload for validation)
    const journey: any = await apiClient.post('/api/v1/journeys/', {
      name: `Semantic RAG Builder ${ts}`,
      description: 'Build enterprise knowledge graph from FDW, policies, workflows',
      odaComponentType: 'resource-management',
      stages: [{ stageId: 'semantic_rag', name: 'Knowledge Processor', order: 0, steps: [] }],
    });
    const journeyId = journey.journey_id || journey.journeyId || journey.id;

    // Step 2: Register the actual stage (creation payload stages are metadata only)
    await apiClient.post(
      `/api/v1/journeys/${journeyId}/stages?stage_id=semantic_rag`,
      { name: 'Knowledge Processor', order: 0 }
    );

    // Step 3: Run the pipeline
    const job: any = await apiClient.post(
      `/api/v1/journeys/${journeyId}/jobs?stage_id=semantic_rag`,
      { triggered_by: 'rag-playground', reason: 'Build knowledge index' }
    );
    const jobId = job.job_id || job.jobId || job.id;

    return { journey_id: journeyId, job_id: jobId };
  },

  async getJobStatus(journeyId: string, jobId: string): Promise<any> {
    return apiClient.get(`/api/v1/journeys/${journeyId}/jobs/${jobId}/status`);
  },

  async getJobLogs(journeyId: string, jobId: string): Promise<any> {
    return apiClient.get(`/api/v1/journeys/${journeyId}/jobs/${jobId}/logs`);
  },
};
