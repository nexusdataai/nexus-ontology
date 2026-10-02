import apiClient from './apiClient';
import type { DashboardModel } from '@/lib/dashboard/model';

export interface DashboardListItem {
  uid: string;
  title: string;
  description?: string;
  tags: string[];
  panelCount: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
}

export const dashboardService = {
  list: async (search?: string, tags?: string): Promise<DashboardListItem[]> => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (tags) params.set('tags', tags);
    const qs = params.toString();
    const items = await apiClient.get<DashboardListItem[]>(
      `/api/v1/dashboards${qs ? '?' + qs : ''}`
    );
    return items.sort((a, b) => (b.updatedAt || '').localeCompare(a.updatedAt || ''));
  },

  get: (uid: string): Promise<DashboardModel> =>
    apiClient.get<DashboardModel>(`/api/v1/dashboards/${uid}`),

  create: (dashboard: Partial<DashboardModel>): Promise<DashboardModel> =>
    apiClient.post<DashboardModel>('/api/v1/dashboards', dashboard),

  update: (uid: string, dashboard: Partial<DashboardModel>): Promise<DashboardModel> =>
    apiClient.put<DashboardModel>(`/api/v1/dashboards/${uid}`, dashboard),

  delete: (uid: string): Promise<{ status: string; uid: string }> =>
    apiClient.delete<{ status: string; uid: string }>(`/api/v1/dashboards/${uid}`),

  clone: (uid: string): Promise<DashboardModel> =>
    apiClient.post<DashboardModel>(`/api/v1/dashboards/${uid}/clone`),
};
