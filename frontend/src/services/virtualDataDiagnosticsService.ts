import { apiClient } from './apiClient';

export type CheckLevel = 'pass' | 'warn' | 'fail';
export type OverallLevel = 'healthy' | 'degraded' | 'unhealthy';

export interface VirtualEntityCheck {
  code: string;
  status: CheckLevel;
  message: string;
  suggestion?: string | null;
  detail?: Record<string, unknown>;
}

export interface VirtualEntityDiagnostic {
  virtualEntity: string;
  overall: OverallLevel;

  sourceType?: string | null;
  sourceSystem?: string | null;
  sourceSchema?: string | null;
  sourceTable?: string | null;
  ruleId?: string | null;

  activeRuleCount: number;
  totalRuleCount: number;

  rowCount?: number | null;
  latencyMs?: number | null;

  checks: VirtualEntityCheck[];
  sampleRow?: Record<string, unknown> | null;

  durationMs?: number | null;
  scannedAt: string;
}

export interface VirtualEntityIndexEntry {
  virtualEntity: string;
  totalRuleCount: number;
  activeRuleCount: number;
  sourceSystems: string[];
  sourceSchemas: string[];
}

export interface ScanResult {
  overall: OverallLevel;
  total: number;
  healthy: number;
  degraded: number;
  unhealthy: number;
  entities: VirtualEntityDiagnostic[];
  durationMs: number;
  scannedAt: string;
}

export interface RunOneRequest {
  limit?: number;
}

export interface RunAllRequest {
  entities?: string[];
  limit?: number;
  concurrency?: number;
}

export type StreamEvent =
  | { type: 'entity'; data: VirtualEntityDiagnostic }
  | {
      type: 'summary';
      data: {
        total: number;
        healthy: number;
        degraded: number;
        unhealthy: number;
      };
    }
  | { type: 'error'; data: { message: string } };

const BASE = '/api/v1/diagnostics/virtual-entities';

export const virtualDataDiagnosticsService = {
  listIndex: () =>
    apiClient.get<VirtualEntityIndexEntry[]>(BASE),

  runOne: (entity: string, body: RunOneRequest = {}) =>
    apiClient.post<VirtualEntityDiagnostic>(
      `${BASE}/${encodeURIComponent(entity)}/run`,
      body,
    ),

  runAll: (body: RunAllRequest = {}) =>
    apiClient.post<ScanResult>(`${BASE}/run-all`, body),

  /**
   * Stream the run-all output via fetch + ReadableStream so the panel
   * paints rows incrementally instead of blocking on the full scan.
   * Falls back to a single POST when the SSE pump errors out.
   */
  streamRunAll: async (
    body: RunAllRequest,
    onEvent: (e: StreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> => {
    const apiKey =
      (window as { __NEXUS_API_KEY__?: string }).__NEXUS_API_KEY__ || '';
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    };
    if (apiKey) headers['x-api-key'] = apiKey;

    const resp = await fetch(`${BASE}/run-all`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      credentials: 'include',
      signal,
    });
    if (!resp.ok || !resp.body) {
      const fallback = await virtualDataDiagnosticsService.runAll(body);
      for (const d of fallback.entities) {
        onEvent({ type: 'entity', data: d });
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
        } catch {
          // ignore malformed events
        }
      }
    }
  },
};
