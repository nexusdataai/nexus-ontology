/**
 * Onto Data API Client — manages knowledge files (policies, workflows, integrations) in S3.
 */

import { apiClient } from './apiClient';

export interface OntoFile {
  key: string;
  filename: string;
  category: string;
  size: number;
  last_modified: string;
}

export const ontoDataApi = {
  async listFiles(category?: string): Promise<{ files: OntoFile[]; total: number }> {
    const params = category ? `?category=${category}` : '';
    return apiClient.get(`/api/v1/control-plane/onto-data/files${params}`);
  },

  async uploadFile(category: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);

    const config = await (async () => {
      try {
        const res = await fetch('/config.json');
        const c = await res.json();
        return c?.api?.baseUrl || '';
      } catch { return ''; }
    })();

    const url = `${config}/api/v1/control-plane/onto-data/files`;
    const response = await fetch(url, { method: 'POST', body: formData, credentials: 'include' });
    if (!response.ok) throw new Error(`Upload failed: ${response.status}`);
    return response.json();
  },

  async deleteFile(key: string): Promise<any> {
    return apiClient.delete(`/api/v1/control-plane/onto-data/files/${key}`);
  },

  async seedDefaults(): Promise<{ success: boolean; counts: Record<string, number> }> {
    return apiClient.post('/api/v1/control-plane/onto-data/seed', {});
  },

  async getInfo(): Promise<any> {
    return apiClient.get('/api/v1/control-plane/onto-data/info');
  },
};
