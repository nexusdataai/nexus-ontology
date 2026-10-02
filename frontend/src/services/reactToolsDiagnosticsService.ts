/**
 * ReAct Tools Diagnostics service.
 *
 * Wraps the five backend endpoints under
 * /api/v1/diagnostics/react-tools/*. Powers the ReAct Tools tab in the
 * Diagnostics page (registry health, contract verification, connector
 * APIs, execution canaries, interactive Try-it).
 */

import { apiClient } from './apiClient';

export type Severity = 'error' | 'warning';
export type Overall = 'healthy' | 'degraded' | 'unhealthy';
export type CanaryStatus = 'pass' | 'fail' | 'skip';

// ---------------------------------------------------------------------------
// /registry
// ---------------------------------------------------------------------------

export interface RegistryToolRow {
  tool_id: string;
  display_name: string;
  group: string;
  description: string;
  risk_level: string;
  requires_approval: boolean;
  cacheable: boolean;
  connector_api: string | null;
  tags: string[];
  parameters: any;
  yaml_present: boolean;
  use_case_refs: number;
  has_canary: boolean;
}

export interface RegistryReport {
  totals: {
    registered_tools: number;
    yaml_tools: number;
    yaml_only_orphans: number;
    registry_only_orphans: number;
    by_group: Record<string, number>;
    by_risk_level: Record<string, number>;
  };
  tools: RegistryToolRow[];
  yaml_only_orphans: string[];
  registry_only_orphans: string[];
  overall: Overall;
}

// ---------------------------------------------------------------------------
// /contracts
// ---------------------------------------------------------------------------

export interface ContractIssue {
  severity: Severity;
  code: string;
  message: string;
}

export interface ContractsReport {
  totals: {
    checked: number;
    errors: number;
    warnings: number;
    tools_with_issues: number;
  };
  issues_by_tool: Record<string, ContractIssue[]>;
  overall: Overall;
}

// ---------------------------------------------------------------------------
// /connector-apis
// ---------------------------------------------------------------------------

export interface ConnectorAPIRow {
  api_id: string;
  target_system: string;
  operation: string;
  risk_level: string;
  description: string;
  tags: string[];
  has_request_schema: boolean;
  has_response_schema: boolean;
  tool_callers: string[];
  tool_caller_count: number;
  simulator_writeback: boolean;
  audit_count?: number;
  last_invocation_ts?: string | null;
  verified?: boolean;
}

export interface ConnectorAPIReport {
  totals: {
    checked: number;
    errors: number;
    warnings: number;
    orphans: number;
    verified?: number;
    never_invoked?: number;
    by_target_system: Record<string, number>;
    by_risk_level: Record<string, number>;
  };
  apis: ConnectorAPIRow[];
  issues_by_api: Record<string, ContractIssue[]>;
  orphan_api_ids: string[];
  overall: Overall;
}

// ---------------------------------------------------------------------------
// /run + /{tool}/execute
// ---------------------------------------------------------------------------

export interface CanaryResult {
  tool_id: string;
  group?: string;
  risk_level: string;
  requires_approval?: boolean;
  connector_api?: string | null;
  status: CanaryStatus;
  duration_ms: number;
  result_preview?: string;
  marker?: string | null;
  params?: Record<string, any>;
  reason?: string;
  missing_required?: string[];
  error?: string;
}

export interface CanaryReport {
  totals: {
    checked: number;
    pass: number;
    fail: number;
    skip: number;
    read_only_failures: number;
    duration_ms: number;
  };
  results: CanaryResult[];
  overall: Overall;
  error?: string;
}

export interface ExecuteResult extends CanaryResult {
  result?: any;
}

// ---------------------------------------------------------------------------

export const reactToolsDiagnosticsService = {
  registry: () =>
    apiClient.get<RegistryReport>('/api/v1/diagnostics/react-tools/registry'),

  contracts: () =>
    apiClient.get<ContractsReport>('/api/v1/diagnostics/react-tools/contracts'),

  connectorAPIs: () =>
    apiClient.get<ConnectorAPIReport>('/api/v1/diagnostics/react-tools/connector-apis'),

  runAll: (opts?: { only_read_only?: boolean; tool_ids?: string[] }) =>
    apiClient.post<CanaryReport>(
      '/api/v1/diagnostics/react-tools/run',
      opts || {},
      { timeout: 300000 },
    ),

  executeOne: (tool: string, params: Record<string, any>) =>
    apiClient.post<ExecuteResult>(
      `/api/v1/diagnostics/react-tools/${encodeURIComponent(tool)}/execute`,
      { params },
      { timeout: 60000 },
    ),
};
