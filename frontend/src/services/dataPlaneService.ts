import apiClient from './apiClient';

export interface DataPlane {
  id: string;
  name: string;
  type: 'FDW' | 'CDC' | 'ETL';
  status: 'connected' | 'disconnected' | 'error' | 'pending';
  connectionConfig: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDataPlaneRequest {
  name: string;
  type: 'FDW' | 'CDC' | 'ETL';
  connectionConfig: Record<string, any>;
}

export interface UpdateDataPlaneRequest {
  name?: string;
  status?: string;
  connectionConfig?: Record<string, any>;
}

export const dataPlaneService = {
  list: (): Promise<DataPlane[]> =>
    apiClient.get('/api/data-planes'),

  get: (id: string): Promise<DataPlane> =>
    apiClient.get(`/api/data-planes/${id}`),

  create: (data: CreateDataPlaneRequest): Promise<DataPlane> =>
    apiClient.post('/api/data-planes', data),

  update: (id: string, data: UpdateDataPlaneRequest): Promise<DataPlane> =>
    apiClient.put(`/api/data-planes/${id}`, data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/api/data-planes/${id}`),

  explore: (id: string): Promise<any> =>
    apiClient.get(`/api/data-planes/${id}/explore`),
};
