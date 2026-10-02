/**
 * Knowledge Pipelines registry service (Control plane, Phase 3.4).
 *
 * Reads `/api/v1/knowledge-pipelines` backed by KP# rows in the
 * foundry-workspace DDB. Populated by the Knowledge Processor stage
 * (semantic_rag) after each successful run.
 */

import { apiClient } from './apiClient';

export interface KnowledgePipeline {
  pipelineId: string;
  name: string;
  description: string;
  stageIds: string[];
  outputs: string[];
  updatedAt?: string;
}

export interface KnowledgePipelineRun {
  pipelineId: string;
  journeyId?: string;
  jobId?: string;
  counts?: Record<string, number>;
  success?: boolean;
  recordedAt?: string;
  SK?: string;
}

export const knowledgePipelinesService = {
  list: () =>
    apiClient.get<{ total: number; items: KnowledgePipeline[] }>(`/api/v1/knowledge-pipelines`),
  get: (pipelineId: string) =>
    apiClient.get<KnowledgePipeline>(`/api/v1/knowledge-pipelines/${encodeURIComponent(pipelineId)}`),
  listRuns: (pipelineId: string, limit: number = 20) =>
    apiClient.get<{ pipelineId: string; total: number; items: KnowledgePipelineRun[] }>(
      `/api/v1/knowledge-pipelines/${encodeURIComponent(pipelineId)}/runs?limit=${limit}`,
    ),
};
