import apiClient from './apiClient';

export interface FieldMap {
  sourceField: string;
  targetField: string;
  transform?: string;
  defaultValue?: string;
}

export interface MappingRule {
  id: string;
  name: string;
  virtualEntity: string;
  sourceType: 'FDW' | 'ETL' | 'CDC';
  sourceSystem: string;
  sourceTable: string;
  sourceSchema: string;
  fieldMaps: FieldMap[];
  businessLogic?: string;
  filterExpression?: string;
  status: 'draft' | 'active' | 'inactive';
  createdAt: string;
  updatedAt: string;
}

export interface CreateMappingRuleRequest {
  name: string;
  virtualEntity: string;
  sourceType: 'FDW' | 'ETL' | 'CDC';
  sourceSystem: string;
  sourceTable: string;
  sourceSchema: string;
  fieldMaps: FieldMap[];
  businessLogic?: string;
  filterExpression?: string;
}

export interface UpdateMappingRuleRequest {
  name?: string;
  fieldMaps?: FieldMap[];
  businessLogic?: string;
  filterExpression?: string;
  status?: 'draft' | 'active' | 'inactive';
}

export interface MappingSuggestion {
  sourceField: string;
  targetField: string;
  confidence: string;
}

export interface AutoMapDetail {
  entity: string;
  status: 'created' | 'skipped' | 'error';
  reason?: string;
}

export interface AutoMapResponse {
  created: number;
  skipped: number;
  errors: number;
  details: AutoMapDetail[];
}

export const mappingRuleService = {
  list: (virtualEntity?: string, sourceType?: string): Promise<MappingRule[]> => {
    const params = new URLSearchParams();
    if (virtualEntity) params.set('virtual_entity', virtualEntity);
    if (sourceType) params.set('source_type', sourceType);
    const qs = params.toString();
    return apiClient.get(`/api/v1/mapping-rules${qs ? `?${qs}` : ''}`);
  },

  get: (id: string): Promise<MappingRule> =>
    apiClient.get(`/api/v1/mapping-rules/${id}`),

  create: (data: CreateMappingRuleRequest): Promise<MappingRule> =>
    apiClient.post('/api/v1/mapping-rules', data),

  update: (id: string, data: UpdateMappingRuleRequest): Promise<MappingRule> =>
    apiClient.put(`/api/v1/mapping-rules/${id}`, data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/api/v1/mapping-rules/${id}`),

  validate: (id: string): Promise<{ valid: boolean; errors: string[] }> =>
    apiClient.post(`/api/v1/mapping-rules/${id}/validate`, {}),

  suggest: (virtualEntity: string, sourceSchema: string, sourceTable: string): Promise<{ suggestions: MappingSuggestion[] }> =>
    apiClient.post('/api/v1/mapping-rules/suggest', { virtualEntity, sourceSchema, sourceTable }),

  autoMap: (force: boolean = true): Promise<AutoMapResponse> =>
    apiClient.post(`/api/v1/mapping-rules/auto-map?force=${force}`, {}),

  audit: (): Promise<AuditResponse> =>
    apiClient.get('/api/v1/mapping-rules/audit'),
};

export interface AuditEntityDetail {
  entity: string;
  system: string;
  domain: string;
  schemaFields: number;
  mappingStatus: 'mapped' | 'unmapped' | 'error';
  ruleName?: string;
  ruleId?: string;
  sourceSchema?: string;
  sourceTable?: string;
  sourceType?: string;
  mappedFields: number;
  unmappedFields: number;
  rowCount: number;
  dataStatus: 'has_data' | 'no_data' | 'no_source';
  issues: string[];
}

export interface AuditResponse {
  totalEntities: number;
  mapped: number;
  unmapped: number;
  withData: number;
  withoutData: number;
  entities: AuditEntityDetail[];
  summaryBySystem: Record<string, { mapped: number; unmapped: number; rows: number }>;
}
