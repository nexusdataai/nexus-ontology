import apiClient from './apiClient';
import type { View, ViewSummary, ViewTab, SimulatorRef } from '@/lib/foundry/model';

export interface ViewTabPayload {
  tabId?: string;
  label?: string;
  icon?: string;
  dashboardId: string;
  simulatorRefs?: SimulatorRef[];
  timeOverride?: { from?: string; to?: string } | null;
  position?: number;
}

export const viewService = {
  list: (search?: string, tags?: string): Promise<ViewSummary[]> => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (tags) params.set('tags', tags);
    const qs = params.toString();
    return apiClient.get<ViewSummary[]>(`/api/v1/views${qs ? '?' + qs : ''}`);
  },

  get: (viewId: string): Promise<View> => apiClient.get<View>(`/api/v1/views/${viewId}`),

  create: (payload: Partial<View>): Promise<View> => apiClient.post<View>('/api/v1/views', payload),

  update: (viewId: string, payload: Partial<View>): Promise<View> =>
    apiClient.put<View>(`/api/v1/views/${viewId}`, payload),

  delete: (viewId: string): Promise<{ status: string; viewId: string }> =>
    apiClient.delete(`/api/v1/views/${viewId}`),

  addTab: (viewId: string, tab: ViewTabPayload): Promise<View> =>
    apiClient.post<View>(`/api/v1/views/${viewId}/tabs`, tab),

  updateTab: (viewId: string, tabId: string, tab: Partial<ViewTab>): Promise<View> =>
    apiClient.put<View>(`/api/v1/views/${viewId}/tabs/${tabId}`, tab),

  removeTab: (viewId: string, tabId: string): Promise<View> =>
    apiClient.delete<View>(`/api/v1/views/${viewId}/tabs/${tabId}`),

  reorderTabs: (viewId: string, tabIds: string[]): Promise<View> =>
    apiClient.post<View>(`/api/v1/views/${viewId}/tabs/reorder`, { tabIds }),
};
