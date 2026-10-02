import { apiClient } from './apiClient';

export type TargetSystem = 'oracle' | 'sap' | 'sfdc' | 'external';
export type RiskLevel = 'read_only' | 'low_risk_write' | 'high_risk_write';

export interface ConnectorAPISpec {
  api_id: string;
  target_system: TargetSystem;
  operation: string;
  description: string;
  request_schema: Record<string, unknown>;
  response_schema: Record<string, unknown>;
  simulator_writeback: boolean;
  risk_level: RiskLevel;
  tags: string[];
}

interface ListResponse {
  items: ConnectorAPISpec[];
}

export const connectorApiService = {
  list: (targetSystem?: TargetSystem) => {
    const path = targetSystem
      ? `/api/v1/automation/connector-apis?target_system=${encodeURIComponent(targetSystem)}`
      : '/api/v1/automation/connector-apis';
    return apiClient.get<ListResponse>(path);
  },
};
