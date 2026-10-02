/**
 * Tool Builder service.
 *
 * Wraps the /api/v1/tools/* REST endpoints. Powers the Tool Builder
 * page (Monaco editor + parameters + test runner + version history).
 */

import { apiClient } from './apiClient';

export type RiskLevel = 'read_only' | 'low_risk_write' | 'high_risk_write';
export type ToolStatus = 'active' | 'deleted';

export interface ToolSummary {
  tool_id: string;
  name: string;
  description: string;
  risk_level: RiskLevel;
  requires_approval: boolean;
  cacheable: boolean;
  connector_api: string | null;
  tags: string[];
  current_version: number;
  status: ToolStatus;
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface ToolDoc extends ToolSummary {
  parameters: Record<string, unknown>;
  source_code: string;
  source_sha256?: string | null;
  changelog?: string | null;
}

export interface ToolVersion {
  tool_id: string;
  version: number;
  source_code: string;
  parameters: Record<string, unknown>;
  source_sha256?: string | null;
  changelog?: string | null;
  createdBy?: string | null;
  createdAt?: string | null;
}

export interface ToolCreate {
  name: string;
  description?: string;
  parameters?: Record<string, unknown>;
  risk_level: RiskLevel;
  requires_approval?: boolean;
  cacheable?: boolean;
  connector_api?: string | null;
  tags?: string[];
  source_code: string;
}

export interface ToolUpdate {
  description?: string;
  parameters?: Record<string, unknown>;
  risk_level?: RiskLevel;
  requires_approval?: boolean;
  cacheable?: boolean;
  connector_api?: string | null;
  tags?: string[];
  source_code?: string;
  changelog?: string;
  if_unchanged_updated_at?: string | null;
}

export interface ToolTestResponse {
  status: 'pass' | 'fail';
  duration_ms: number;
  result?: unknown;
  error?: string | null;
  logs: { ts: string; level: string; msg: string; kw?: Record<string, unknown> }[];
}

export interface ToolImportBundle {
  tools: ToolCreate[];
  mode?: 'merge' | 'replace' | 'skip_existing';
}

export interface ToolImportResult {
  imported: number;
  updated: number;
  skipped: number;
  errors: { name: string; error: string }[];
}

const BASE = '/api/v1/tools';
const enc = (s: string) => encodeURIComponent(s);

export const toolBuilderService = {
  list: (opts?: { search?: string; tag?: string; risk_level?: RiskLevel }) => {
    const qs = new URLSearchParams();
    if (opts?.search) qs.set('search', opts.search);
    if (opts?.tag) qs.set('tag', opts.tag);
    if (opts?.risk_level) qs.set('risk_level', opts.risk_level);
    const q = qs.toString();
    return apiClient.get<ToolSummary[]>(q ? `${BASE}?${q}` : BASE);
  },

  get: (toolId: string) =>
    apiClient.get<ToolDoc>(`${BASE}/${enc(toolId)}`),

  create: (body: ToolCreate) =>
    apiClient.post<ToolDoc>(BASE, body),

  update: (toolId: string, body: ToolUpdate) =>
    apiClient.put<ToolDoc>(`${BASE}/${enc(toolId)}`, body),

  remove: (toolId: string) =>
    apiClient.delete<{ deleted: boolean; tool_id: string }>(`${BASE}/${enc(toolId)}`),

  listVersions: (toolId: string) =>
    apiClient.get<ToolVersion[]>(`${BASE}/${enc(toolId)}/versions`),

  getVersion: (toolId: string, version: number) =>
    apiClient.get<ToolDoc>(`${BASE}/${enc(toolId)}/versions/${version}`),

  restoreVersion: (toolId: string, version: number) =>
    apiClient.post<ToolDoc>(`${BASE}/${enc(toolId)}/restore/${version}`, {}),

  test: (toolId: string, params: Record<string, unknown>) =>
    apiClient.post<ToolTestResponse>(
      `${BASE}/${enc(toolId)}/test`,
      { params },
      { timeout: 90000 },
    ),

  exportBundle: (ids?: string[]) => {
    const q = ids?.length ? `?ids=${enc(ids.join(','))}` : '';
    return apiClient.get<{ exported_at: string; tools: ToolCreate[] }>(`${BASE}/export${q}`);
  },

  importBundle: (bundle: ToolImportBundle) =>
    apiClient.post<ToolImportResult>(`${BASE}/import`, bundle),
};
