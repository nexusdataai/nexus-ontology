import apiClient from './apiClient';
import type { Solution, SolutionSummary } from '@/lib/foundry/model';

export const solutionService = {
  list: (search?: string): Promise<SolutionSummary[]> => {
    const qs = search ? `?search=${encodeURIComponent(search)}` : '';
    return apiClient.get<SolutionSummary[]>(`/api/v1/solutions${qs}`);
  },

  get: (solutionId: string): Promise<Solution> =>
    apiClient.get<Solution>(`/api/v1/solutions/${solutionId}`),

  getByAppId: (appId: string): Promise<Solution | null> =>
    apiClient
      .get<Solution>(`/api/v1/solutions/by-app/${encodeURIComponent(appId)}`)
      .catch(() => null),

  create: (payload: Partial<Solution>): Promise<Solution> =>
    apiClient.post<Solution>('/api/v1/solutions', payload),

  update: (solutionId: string, payload: Partial<Solution>): Promise<Solution> =>
    apiClient.put<Solution>(`/api/v1/solutions/${solutionId}`, payload),

  delete: (solutionId: string): Promise<{ status: string; solutionId: string }> =>
    apiClient.delete(`/api/v1/solutions/${solutionId}`),

  addView: (
    solutionId: string,
    viewId: string,
    position?: number,
    displayName?: string
  ): Promise<Solution> =>
    apiClient.post<Solution>(`/api/v1/solutions/${solutionId}/views`, {
      viewId,
      position,
      displayName,
    }),

  removeView: (solutionId: string, viewId: string): Promise<Solution> =>
    apiClient.delete<Solution>(`/api/v1/solutions/${solutionId}/views/${viewId}`),

  reorderViews: (solutionId: string, viewIds: string[]): Promise<Solution> =>
    apiClient.post<Solution>(`/api/v1/solutions/${solutionId}/views/reorder`, { viewIds }),
};
