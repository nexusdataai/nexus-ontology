/**
 * Solutions catalog service (Workspace, Phase 5).
 *
 * Reads AI Solutions from `/api/v1/solutions/catalog` (DDB-backed) and
 * runs NLP search via `/api/v1/solutions/search`. Replaces the
 * hardcoded APPS array in `AppCatalogue.tsx`.
 */

import { apiClient } from './apiClient';

export interface SolutionCatalogEntry {
  solutionId: string;
  title: string;
  description: string;
  priority?: string;
  category?: string;
  timeToValue?: string;
  verticals?: string[];
  personas?: string[];
  entities?: string[];
  kpis?: string[];
  automations?: string[];
  analytics?: string[];
  nlq_examples?: string[];
  color?: string;
  icon?: string;
  journeyId?: string;
  status?: 'available' | 'coming_soon';
}

export interface SolutionSearchHit {
  content_type: string;
  source_id: string;
  content: string;
  similarity: number;
  metadata?: Record<string, unknown>;
}

// The `/api/v1/solution-catalog` prefix (not `/api/v1/solutions/...`) is
// deliberate: the older `solution_api` router owns `/api/v1/solutions/*`
// with a wildcard `GET /{solution_id}` that shadows any nested paths.
export const solutionsCatalogService = {
  list: () =>
    apiClient.get<{ total: number; items: SolutionCatalogEntry[] }>(
      `/api/v1/solution-catalog`,
    ),
  get: (solutionId: string) =>
    apiClient.get<SolutionCatalogEntry>(
      `/api/v1/solution-catalog/${encodeURIComponent(solutionId)}`,
    ),
  upsert: (entry: SolutionCatalogEntry) =>
    apiClient.post<SolutionCatalogEntry>(`/api/v1/solution-catalog`, entry),
  remove: (solutionId: string) =>
    apiClient.delete<void>(
      `/api/v1/solution-catalog/${encodeURIComponent(solutionId)}`,
    ),
  search: (query: string, limit: number = 5) =>
    apiClient.post<{ query: string; total: number; items: SolutionSearchHit[] }>(
      `/api/v1/solution-catalog/search`,
      { query, limit },
    ),
};
