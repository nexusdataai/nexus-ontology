import { apiClient } from './apiClient';

export type CheckLevel = 'pass' | 'warn' | 'fail';
export type OverallLevel = 'healthy' | 'degraded' | 'unhealthy';
export type PanelCheckCode =
  | 'ok'
  | 'no_mapping_rule'
  | 'inactive_rule'
  | 'backend_unreachable'
  | 'query_error'
  | 'no_rows'
  | 'missing_columns'
  | 'null_group_keys'
  | 'slow_query';

export interface PanelDiagnostic {
  panelId: number;
  panelTitle: string;
  panelType: string;
  targetRefId: string;
  entity: string;
  sourceType?: string | null;
  ruleId?: string | null;

  status: CheckLevel;
  code: PanelCheckCode;

  latencyMs?: number | null;
  rowCount?: number | null;
  expectedFields: string[];
  returnedFields: string[];
  missingFields: string[];
  nullGroupColumns: string[];

  errorMessage?: string | null;
  suggestion?: string | null;
  queryPayload: Record<string, unknown>;
}

export interface DashboardDiagnostic {
  uid: string;
  title: string;
  description?: string | null;
  tags: string[];
  status: OverallLevel;
  panelCount: number;
  healthyCount: number;
  degradedCount: number;
  unhealthyCount: number;
  panels: PanelDiagnostic[];
  durationMs?: number | null;
  scannedAt: string;
}

export interface DashboardIndexEntry {
  uid: string;
  title: string;
  description?: string | null;
  tags: string[];
  panelCount: number;
  updatedAt?: string | null;
}

export interface ScanResult {
  total: number;
  healthy: number;
  degraded: number;
  unhealthy: number;
  dashboards: DashboardDiagnostic[];
  durationMs: number;
  scannedAt: string;
}

export interface BackendDiagnostic {
  name: string;
  kind: string;
  status: CheckLevel;
  detail?: string | null;
  latencyMs?: number | null;
  metadata?: Record<string, unknown>;
}

export interface BackendsDiagnostic {
  overall: OverallLevel;
  backends: BackendDiagnostic[];
  scannedAt: string;
}

export interface EntityDiagnostic {
  entity: string;
  status: CheckLevel;
  code: PanelCheckCode;
  ruleId?: string | null;
  sourceType?: string | null;
  sourceTable?: string | null;
  rowCount?: number | null;
  sampleRows: Record<string, unknown>[];
  errorMessage?: string | null;
  latencyMs?: number | null;
  scannedAt: string;
}

export interface RunOneRequest {
  limitPerPanel?: number;
}

export interface RunAllRequest {
  dashboardUids?: string[];
  limitPerPanel?: number;
  concurrency?: number;
}

export type StreamEvent =
  | { type: 'dashboard'; data: DashboardDiagnostic }
  | { type: 'summary'; data: { total: number; healthy: number; degraded: number; unhealthy: number } }
  | { type: 'error'; data: { message: string } };

export const dashboardDiagnosticsService = {
  listIndex: () =>
    apiClient.get<DashboardIndexEntry[]>('/api/v1/diagnostics/dashboards'),

  runOne: (uid: string, body: RunOneRequest = {}) =>
    apiClient.post<DashboardDiagnostic>(
      `/api/v1/diagnostics/dashboards/${encodeURIComponent(uid)}/run`,
      body,
    ),

  runAll: (body: RunAllRequest = {}) =>
    apiClient.post<ScanResult>('/api/v1/diagnostics/dashboards/run-all', body),

  entityCheck: (entity: string, limit = 5) =>
    apiClient.get<EntityDiagnostic>(
      `/api/v1/diagnostics/entities/${encodeURIComponent(entity)}?limit=${limit}`,
    ),

  backendsCheck: () =>
    apiClient.get<BackendsDiagnostic>('/api/v1/diagnostics/backends'),

  /**
   * Stream the run-all output via fetch + ReadableStream so we incrementally
   * paint progress instead of waiting for the full ScanResult. Falls back to
   * a single POST if the SSE pump errors out.
   */
  streamRunAll: async (
    body: RunAllRequest,
    onEvent: (e: StreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> => {
    const apiKey = (window as { __NEXUS_API_KEY__?: string }).__NEXUS_API_KEY__ || '';
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    };
    if (apiKey) headers['x-api-key'] = apiKey;

    const resp = await fetch('/api/v1/diagnostics/dashboards/run-all', {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      credentials: 'include',
      signal,
    });
    if (!resp.ok || !resp.body) {
      const fallback = await dashboardDiagnosticsService.runAll(body);
      for (const d of fallback.dashboards) {
        onEvent({ type: 'dashboard', data: d });
      }
      onEvent({
        type: 'summary',
        data: {
          total: fallback.total,
          healthy: fallback.healthy,
          degraded: fallback.degraded,
          unhealthy: fallback.unhealthy,
        },
      });
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx: number;
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const chunk = buffer.slice(0, idx).trim();
        buffer = buffer.slice(idx + 2);
        if (!chunk.startsWith('data:')) continue;
        const payload = chunk.replace(/^data:\s*/, '');
        if (!payload) continue;
        try {
          const evt = JSON.parse(payload) as StreamEvent;
          onEvent(evt);
        } catch (err) {
          // ignore malformed events
        }
      }
    }
  },
};
