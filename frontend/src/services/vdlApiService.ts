/**
 * Virtual Data API Registry service (Data Plane, Phase 2).
 *
 * Wraps the `/api/v1/vdl-apis` endpoints. Distinct from the Connector API
 * registry: VDL APIs operate on virtual entities and dispatch to one or
 * more Connector API implementations.
 */

import { apiClient } from './apiClient';

export type VdlVerb = 'read' | 'write' | 'upsert' | 'delete' | 'aggregate';

export interface ImplBinding {
  connector_api_id: string;
  arg_mapping?: Record<string, string>;
  when?: Record<string, unknown>;
}

export interface DirectSqlBinding {
  virtual_entity: string;
  filters?: Record<string, unknown>;
  projection?: string[];
  limit?: number;
}

export interface VdlApiSpec {
  api_id: string;
  verb: VdlVerb;
  virtual_entity: string;
  parameters_schema?: Record<string, unknown>;
  impl: ImplBinding[];
  direct_sql?: DirectSqlBinding | null;
  risk_level: string;
  description: string;
  tags: string[];
}

export interface VdlApiListResponse {
  total: number;
  items: VdlApiSpec[];
}

export interface InvokeResult {
  api_id: string;
  ok: boolean;
  plan: {
    api_id: string;
    verb: string;
    virtual_entity: string;
    steps: Array<{ connector_api_id: string; args: Record<string, unknown> }>;
    direct_sql?: DirectSqlBinding | null;
  };
  step_results: Array<Record<string, unknown>>;
  duration_ms: number;
  error?: string | null;
}

export const vdlApiService = {
  list: (params?: { virtual_entity?: string; verb?: string }) => {
    const q = new URLSearchParams();
    if (params?.virtual_entity) q.set('virtual_entity', params.virtual_entity);
    if (params?.verb) q.set('verb', params.verb);
    const suffix = q.toString();
    return apiClient.get<VdlApiListResponse>(`/api/v1/vdl-apis${suffix ? '?' + suffix : ''}`);
  },
  get: (apiId: string) =>
    apiClient.get<VdlApiSpec>(`/api/v1/vdl-apis/${encodeURIComponent(apiId)}`),
  upsert: (spec: VdlApiSpec) =>
    apiClient.post<VdlApiSpec>('/api/v1/vdl-apis', spec),
  update: (apiId: string, spec: VdlApiSpec) =>
    apiClient.put<VdlApiSpec>(`/api/v1/vdl-apis/${encodeURIComponent(apiId)}`, spec),
  remove: (apiId: string) =>
    apiClient.delete<void>(`/api/v1/vdl-apis/${encodeURIComponent(apiId)}`),
  invoke: (apiId: string, args: Record<string, unknown>) =>
    apiClient.post<InvokeResult>(
      `/api/v1/vdl-apis/${encodeURIComponent(apiId)}/invoke`,
      { args },
    ),
};
