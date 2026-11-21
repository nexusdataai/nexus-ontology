import { apiClient } from '@/services/apiClient';
import type { FieldMap } from '@/services/mappingRuleService';

export type CompositionStatus = 'draft' | 'active' | 'inactive';

export interface CompositionSourceRef {
  alias: string;
  sourceSystem: string;
  schema: string;
  table: string;
}

export interface CompositionJoin {
  left: string;
  right: string;
  type: string;
  on: string;
}

export interface CompositionProjection {
  targetField: string;
  expr: string;
}

export interface VdlComposition {
  virtualEntity: string;
  name?: string;
  status: CompositionStatus;
  strategy: 'runtime_sql' | 'materialized_table' | 'promql' | 'athena_select';
  from: CompositionSourceRef[];
  joins: CompositionJoin[];
  select: CompositionProjection[];
  fieldMaps: FieldMap[];
  filterExpression?: string;
  businessLogic?: string;
  createdAt: string;
  updatedAt: string;
}

export interface VdlCompositionUpsert {
  virtualEntity: string;
  name?: string;
  status: CompositionStatus;
  strategy?: VdlComposition['strategy'];
  from: CompositionSourceRef[];
  joins?: CompositionJoin[];
  select?: CompositionProjection[];
  fieldMaps?: FieldMap[];
  filterExpression?: string;
  businessLogic?: string;
}

export const vdlCompositionService = {
  async list(): Promise<VdlComposition[]> {
    const data = await apiClient.get<VdlComposition[]>('/api/v1/vdl-compositions');
    return Array.isArray(data) ? data : [];
  },

  async get(virtualEntity: string): Promise<VdlComposition> {
    return apiClient.get<VdlComposition>(`/api/v1/vdl-compositions/${encodeURIComponent(virtualEntity)}`);
  },

  async upsert(virtualEntity: string, body: VdlCompositionUpsert): Promise<VdlComposition> {
    return apiClient.put<VdlComposition>(
      `/api/v1/vdl-compositions/${encodeURIComponent(virtualEntity)}`,
      body,
    );
  },

  async validate(virtualEntity: string): Promise<{ valid: boolean; errors: string[]; sqlPreview?: string }> {
    return apiClient.post(`/api/v1/vdl-compositions/${encodeURIComponent(virtualEntity)}/validate`);
  },
};