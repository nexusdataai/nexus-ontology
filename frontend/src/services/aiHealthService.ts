/**
 * AI Health Central service (AI-OPs plane, Phase 1).
 *
 * Wraps the read-only endpoints under `/api/v1/ai-health/*` exposed by the
 * backend `AIHealthService`. Snapshots are computed every 15 minutes on the
 * backend and stored in the `{cap}-{env}-health` DynamoDB table.
 */

import { apiClient } from './apiClient';

export type HealthVerdict = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';

export type PlaneKey = 'ai_ops' | 'data' | 'control' | 'reasoning' | 'workspace';

export interface PlaneSnapshot {
  plane: PlaneKey;
  status: HealthVerdict;
  counts: Record<string, number | string>;
  details: Record<string, unknown>;
  errors: string[];
}

export interface HealthSnapshot {
  scope: string;
  iso_ts: string;
  verdict: HealthVerdict;
  elapsed_ms: number;
  planes: Record<string, PlaneSnapshot>;
  empty?: boolean;
}

export const aiHealthService = {
  latest: (scope: string = 'all') =>
    apiClient.get<HealthSnapshot>(`/api/v1/ai-health/latest?scope=${encodeURIComponent(scope)}`),
  timeseries: (scope: string = 'all', limit: number = 96) =>
    apiClient.get<{ scope: string; total: number; items: HealthSnapshot[] }>(
      `/api/v1/ai-health/timeseries?scope=${encodeURIComponent(scope)}&limit=${limit}`,
    ),
  runNow: (scope: string = 'all') =>
    apiClient.post<HealthSnapshot>(
      `/api/v1/ai-health/run?scope=${encodeURIComponent(scope)}`,
      {},
    ),
};
