/**
 * Tools Registry service (Reasoning plane, Phase 4.2).
 *
 * Reads DDB-backed TOOLREG# rows via `/api/v1/tools-registry`. This is
 * the spec-aligned view of the ReAct tools catalog. The in-memory
 * `/api/v1/control-plane/tools` endpoint stays for runtime execution
 * (built-in Python + user tool source); the DDB view is the durable +
 * externally-consumable projection used for backup, cross-tool audits,
 * and the tools registry browser.
 */

import { apiClient } from './apiClient';

export interface ToolRegistryEntry {
  toolId: string;
  description: string;
  parameters?: Record<string, unknown>;
  riskLevel: string;
  requiresApproval?: boolean;
  cacheable?: boolean;
  connectorApi?: string | null;
  tags?: string[];
  toolKind?: string | null;
  bucket?: string;
  group?: string;
  streaming?: boolean;
  codeRef?: string;
  source?: string;
  updatedAt?: string;
}

export const toolsRegistryService = {
  list: (group?: string) => {
    const q = group ? `?group=${encodeURIComponent(group)}` : '';
    return apiClient.get<{ total: number; items: ToolRegistryEntry[] }>(`/api/v1/tools-registry${q}`);
  },
  get: (toolId: string) =>
    apiClient.get<ToolRegistryEntry>(`/api/v1/tools-registry/${encodeURIComponent(toolId)}`),
  resync: () =>
    apiClient.post<{ synced: number }>(`/api/v1/tools-registry/resync`, {}),
};
