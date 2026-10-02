/**
 * Connector API Workbench service.
 *
 * Wraps the four backend routes under /api/v1/connector-apis/*. Powers
 * the Connector APIs tab in the Diagnostics page (and the per-row Test
 * drawer surfaced from the ReAct Tools panel + ConnectorDetailView).
 */

import { apiClient } from './apiClient';
import type { ConnectorAPISpec, RiskLevel, TargetSystem } from './connectorApiService';

export type Verdict = 'verified' | 'no_change' | 'audit_missing' | 'http_error';

export interface AuditEvent {
  event_id: string;
  actor: string;
  verb: string;
  target: string;
  payload: Record<string, unknown> | null;
  api_id: string | null;
  event_ts: string;
}

export interface ConnectorAPIRowEnriched extends ConnectorAPISpec {
  tool_callers: string[];
  tool_caller_count: number;
  audit_count: number;
  last_invocation_ts: string | null;
  verified: boolean;
  has_verification_hint: boolean;
}

export interface ConnectorAPIListTotals {
  checked: number;
  orphans: number;
  verified: number;
  never_invoked: number;
  by_target_system: Record<string, number>;
  by_risk_level: Record<string, number>;
}

export interface ConnectorAPIListResponse {
  items: ConnectorAPIRowEnriched[];
  totals: ConnectorAPIListTotals;
}

export interface ConnectorAPIDetail extends ConnectorAPIRowEnriched {
  recent_events: AuditEvent[];
}

export interface CanaryPayloadResponse {
  api_id: string;
  payload: Record<string, unknown>;
}

export interface VerificationBlock {
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  row_diff: string[];
  row_count_before: number;
  row_count_after: number;
  audit_event: AuditEvent | null;
  audit_appeared: boolean;
  table: string | null;
  schema: string | null;
  mode: 'patch' | 'post' | 'post_prefix' | null;
}

export interface InvokeRequestBlock {
  method: string;
  path: string;
  body: Record<string, unknown>;
  full_payload: Record<string, unknown>;
}

export interface InvokeResponse {
  api_id: string;
  operation: string;
  request: InvokeRequestBlock;
  http_status: number;
  response: unknown;
  http_error: string | null;
  verification: VerificationBlock;
  duration_ms: number;
  verdict: Verdict;
  marker: string;
}

// ---------------------------------------------------------------------------
// Diagnostic surface
// ---------------------------------------------------------------------------

export type Severity = 'error' | 'warning';
export type Smell = 'ok' | 'never_called' | 'audit_missing';
export type BindingStatus = 'ok' | 'dangling' | 'orphan' | 'read_only';
export type Overall = 'healthy' | 'degraded' | 'unhealthy';

export interface DiagSummary {
  checked: number;
  verified: number;
  never_invoked: number;
  orphans: number;
  with_hint: number;
  without_hint: number;
  audit_events_24h: number;
  by_target_system: Record<string, number>;
  by_risk_level: Record<string, number>;
  overall: Overall;
}

export interface CatalogueIssue {
  severity: Severity;
  code: string;
  message: string;
}

export interface CatalogueHealthReport {
  totals: { checked: number; errors: number; warnings: number; specs_with_issues: number };
  issues_by_api: Record<string, CatalogueIssue[]>;
  overall: Overall;
}

export interface ToolMappingRow {
  tool_id: string;
  risk_level: string;
  connector_api: string | null;
  binding_status: BindingStatus;
}

export interface ToolMappingReport {
  totals: {
    tools: number;
    tools_with_binding: number;
    orphan_tools: number;
    dangling_tools: number;
    orphan_apis: number;
  };
  by_api: Record<string, string[]>;
  by_tool: ToolMappingRow[];
  orphan_apis: string[];
  orphan_tools: { tool_id: string; risk_level: string }[];
  dangling_tools: string[];
  overall: Overall;
}

export interface HintRow {
  api_id: string;
  has_hint: boolean;
  mode: string | null;
  schema: string | null;
  table: string | null;
  pk_col: string | null;
  pk_arg: string | null;
  has_companion: boolean;
}

export interface VerificationHintsReport {
  totals: { checked: number; with_hint: number; without_hint: number };
  rows: HintRow[];
  non_verifiable_api_ids: string[];
  overall: Overall;
}

export interface AuditRollupRow {
  api_id: string;
  target_system: string;
  risk_level: string;
  simulator_writeback: boolean;
  total_events: number;
  events_24h: number;
  last_event_ts: string | null;
  smell: Smell;
}

export interface AuditDisciplineReport {
  totals: { checked: number; ok: number; never_called: number; audit_missing: number };
  rows: AuditRollupRow[];
  overall: Overall;
}

export interface CoverageRow {
  sim_key: string;
  schema: string;
  table: string;
  row_count: number;
  used_by_apis: string[];
  blocking: boolean;
}

export interface SimulatorCoverageReport {
  totals: { tables: number; blocking: number };
  rows: CoverageRow[];
  overall: Overall;
}

export interface DiagnosticReport {
  summary: DiagSummary;
  catalogue_health: CatalogueHealthReport;
  tool_mapping: ToolMappingReport;
  verification_hints: VerificationHintsReport;
  audit_discipline: AuditDisciplineReport;
  simulator_coverage: SimulatorCoverageReport;
}

// ---------------------------------------------------------------------------
// Smoke test surface
// ---------------------------------------------------------------------------

export interface SmokeRow {
  api_id: string;
  verdict: Verdict;
  http_status?: number;
  http_error?: string | null;
  duration_ms?: number;
  verification?: VerificationBlock;
  request?: InvokeRequestBlock;
  response?: unknown;
}

export interface SmokeReport {
  totals: {
    checked: number;
    verified: number;
    no_change: number;
    audit_missing: number;
    http_error: number;
    duration_ms: number;
  };
  results: SmokeRow[];
  overall: Overall;
}

// ---------------------------------------------------------------------------

export const connectorApiWorkbenchService = {
  list: (targetSystem?: TargetSystem) =>
    apiClient.get<ConnectorAPIListResponse>(
      targetSystem
        ? `/api/v1/connector-apis?target_system=${encodeURIComponent(targetSystem)}`
        : '/api/v1/connector-apis',
    ),

  get: (apiId: string) =>
    apiClient.get<ConnectorAPIDetail>(
      `/api/v1/connector-apis/${encodeURIComponent(apiId)}`,
    ),

  events: (apiId: string, limit = 20) =>
    apiClient.get<{ events: AuditEvent[] }>(
      `/api/v1/connector-apis/${encodeURIComponent(apiId)}/events?limit=${limit}`,
    ),

  canaryPayload: (apiId: string) =>
    apiClient.get<CanaryPayloadResponse>(
      `/api/v1/connector-apis/${encodeURIComponent(apiId)}/canary-payload`,
    ),

  invoke: (apiId: string, payload: Record<string, unknown>) =>
    apiClient.post<InvokeResponse>(
      `/api/v1/connector-apis/${encodeURIComponent(apiId)}/invoke`,
      { payload },
      { timeout: 60000 },
    ),

  diagnostic: () =>
    apiClient.get<DiagnosticReport>('/api/v1/connector-apis/diagnostic'),

  smokeTest: (opts?: { only_systems?: string[]; skip_high_risk?: boolean }) =>
    apiClient.post<SmokeReport>(
      '/api/v1/connector-apis/smoke-test',
      opts || {},
      { timeout: 180000 },
    ),
};

export type { RiskLevel, TargetSystem };
