/**
 * Diagnostics history service (AI-OPs plane, Phase 1).
 *
 * Reads persisted diagnostic runs from `/api/v1/diagnostics/history`. Each
 * run is a snapshot of a diagnostic endpoint's response, captured by the
 * backend recorder middleware.
 */

import { apiClient } from './apiClient';

export interface DiagnosticRun {
  scope: string;
  run_id: string;
  recordedAt: string;
  succeeded?: boolean;
  summary?: Record<string, unknown>;
  result?: unknown;
}

export const diagnosticsHistoryService = {
  listScopes: () =>
    apiClient.get<{ scopes: string[] }>(`/api/v1/diagnostics/history/scopes`),
  list: (scope: string, limit: number = 50) =>
    apiClient.get<{ scope: string; total: number; items: DiagnosticRun[] }>(
      `/api/v1/diagnostics/history?scope=${encodeURIComponent(scope)}&limit=${limit}`,
    ),
  get: (scope: string, runId: string) =>
    apiClient.get<DiagnosticRun>(
      `/api/v1/diagnostics/history/${encodeURIComponent(scope)}/${encodeURIComponent(runId)}`,
    ),
};
