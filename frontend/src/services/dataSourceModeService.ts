/**
 * Data Source Mode service.
 *
 * Wraps the per-source `simulator | real` switch:
 *   GET /api/v1/data-source-mode
 *   PUT /api/v1/data-source-mode/{source}
 *
 * Used by:
 *   - SystemSettings.tsx (write surface)
 *   - DataPlanePage.tsx (read-only badges)
 *   - AutomationDiagnosticsPanel.tsx (Copilot Runtime mini-card)
 */

import { apiClient } from './apiClient';

export type Mode = 'simulator' | 'real';
export type Source = 'sfdc' | 'oracle' | 'sap' | 'external';

export interface DataSourceModeReport {
  modes: Record<string, Mode>;
  default: Mode;
  available_sources: string[];
  summary: { simulator: number; real: number };
}

export interface SetModeResponse {
  source: string;
  mode: Mode;
  previous_mode: Mode;
}

export const dataSourceModeService = {
  list: () =>
    apiClient.get<DataSourceModeReport>('/api/v1/data-source-mode'),

  setMode: (source: string, mode: Mode) =>
    apiClient.put<SetModeResponse>(
      `/api/v1/data-source-mode/${encodeURIComponent(source)}`,
      { mode },
    ),
};
