import apiClient from './apiClient';
import type {
  ForeignServerInfo,
  ForeignTableInfo,
  ColumnInfo,
  QueryRequest,
  QueryResponse,
  FdwHealthResponse,
} from '@/types/fdwTypes';

function _qs(params: Record<string, string | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v != null) as [string, string][];
  if (entries.length === 0) return '';
  return '?' + entries.map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
}

export const fdwService = {
  getHealth: (): Promise<FdwHealthResponse> =>
    apiClient.get('/api/v1/health/fdw'),

  listServers: (source?: string): Promise<ForeignServerInfo[]> =>
    apiClient.get(`/api/fdw/servers${_qs({ source })}`),

  listTables: (server?: string, source?: string): Promise<ForeignTableInfo[]> =>
    apiClient.get(`/api/fdw/tables${_qs({ server, source })}`),

  getColumns: (schema: string, table: string, source?: string): Promise<ColumnInfo[]> =>
    apiClient.get(
      `/api/fdw/tables/${encodeURIComponent(schema)}/${encodeURIComponent(table)}/columns${_qs({ source })}`
    ),

  executeQuery: (request: QueryRequest, source?: string): Promise<QueryResponse> =>
    apiClient.post(`/api/fdw/query${_qs({ source })}`, request),
};
