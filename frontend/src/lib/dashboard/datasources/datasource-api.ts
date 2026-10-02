import type {
  DashboardQueryRequest,
  DashboardQueryResponse,
  FieldDescriptor,
  VirtualEntitySummary,
} from '../types';

export interface DataSourceApi {
  uid: string;
  type: string;
  name: string;

  query(request: DashboardQueryRequest): Promise<DashboardQueryResponse>;

  testConnection(): Promise<{ status: 'success' | 'error'; message: string }>;

  getEntities(): Promise<VirtualEntitySummary[]>;

  getEntityFields(entity: string): Promise<FieldDescriptor[]>;
}
