import apiClient from './apiClient';

export interface VirtualFilter {
  field: string;
  operator: string;
  value: string | number | boolean;
}

export interface VirtualQueryRequest {
  virtualEntity: string;
  fields?: string[];
  filters?: VirtualFilter[];
  limit?: number;
  offset?: number;
}

export interface VirtualQueryResponse {
  rows: Record<string, any>[];
  metadata: {
    sourceTable?: string;
    durationMs?: number;
    rowCount?: number;
    mappingRuleId?: string;
    sourceType?: string;
    [key: string]: any;
  };
  virtualEntity: string;
}

export interface VirtualEntitySummary {
  virtual_entity: string;
  source_count: number;
  active_rules: number;
  sources: {
    source_system: string;
    source_table: string;
    source_type: string;
    status: string;
  }[];
  target_type?: string;
  query_language?: string;
  physical_table_fqn?: string;
  binding?: string;
}

export type VqsTargetType = 'FDW' | 'Athena' | 'Mimir' | 'None';

export interface EntityHydration {
  virtualEntity: string;
  resolvedFrom?: string | null;
  binding: 'none' | 'mapping_rule' | 'composition';
  /** Where VQS runs the query (simulator tables count as FDW). */
  targetType: VqsTargetType;
  queryLanguage?: 'SQL' | 'PromQL' | null;
  queryPreview?: string | null;
  physicalTargets?: string[];
  hydrationStore?: string;
  sourceType?: string | null;
  strategy?: string;
  physicalSchema?: string | null;
  physicalTable?: string | null;
  physicalTableFqn?: string | null;
  sourceTables?: string[];
  ruleId?: string;
  sourceSystem?: string;
}

export const virtualQueryService = {
  queryEntity: (request: VirtualQueryRequest): Promise<VirtualQueryResponse> =>
    apiClient.post('/api/v1/control-plane/virtual/query', request),

  listEntities: (): Promise<VirtualEntitySummary[]> =>
    apiClient.get('/api/v1/control-plane/virtual/entities'),

  previewEntity: (entityId: string, limit: number = 10): Promise<VirtualQueryResponse> =>
    apiClient.get(`/api/v1/control-plane/virtual/entities/${encodeURIComponent(entityId)}/preview?limit=${limit}`),

  getEntityHydration: (entityId: string): Promise<EntityHydration> =>
    apiClient.get(`/api/v1/control-plane/virtual/entities/${encodeURIComponent(entityId)}/hydration`, {
      requireAuth: false,
    }),
};
