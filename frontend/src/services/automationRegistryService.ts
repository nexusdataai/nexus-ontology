/**
 * Automation Registry service (Workspace, Phase 5.3).
 *
 * Wraps the DDB-backed AUTOMATION# rows exposed at
 * `/api/v1/automation/registry`. Distinct from the older
 * `/api/v1/automation/use-cases` endpoint which returns pgvector-derived
 * summaries.
 */

import { apiClient } from './apiClient';

export interface AutomationRow {
  useCaseId: string;
  solution: string;
  sourceFile: string;
  yamlText?: string;
  sizeBytes?: number;
  updatedAt?: string;
}

export const automationRegistryService = {
  list: (solution?: string) => {
    const q = solution ? `?solution=${encodeURIComponent(solution)}` : '';
    return apiClient.get<{ total: number; items: AutomationRow[] }>(`/api/v1/automation/registry${q}`);
  },
  get: (useCaseId: string) =>
    apiClient.get<AutomationRow>(`/api/v1/automation/registry/${encodeURIComponent(useCaseId)}`),
  upsert: (row: {
    use_case_id: string;
    solution: string;
    yaml_text: string;
    source_file?: string;
  }) => apiClient.post<AutomationRow>('/api/v1/automation/registry', row),
  remove: (useCaseId: string) =>
    apiClient.delete<void>(`/api/v1/automation/registry/${encodeURIComponent(useCaseId)}`),
};
