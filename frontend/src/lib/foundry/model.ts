/**
 * Foundry Workspace TypeScript model
 *
 * Mirrors the backend Pydantic models (solution_models.py, view_models.py)
 * for Solutions, Views, and View tabs.
 */

export interface SimulatorRef {
  service: string;
  scenario?: string;
  s3Key?: string;
}

export interface ViewTab {
  tabId: string;
  order: number;
  label: string;
  icon?: string;
  dashboardId: string;
  simulatorRefs?: SimulatorRef[];
  timeOverride?: { from?: string; to?: string } | null;
}

export interface View {
  viewId: string;
  name: string;
  description?: string;
  tags: string[];
  defaultTabId?: string;
  version: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  tabs: ViewTab[];
}

export interface ViewSummary {
  viewId: string;
  name: string;
  description?: string;
  tags: string[];
  tabCount: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
}

export interface SolutionViewLink {
  viewId: string;
  order: number;
  name?: string | null;
  displayName?: string | null;
}

export interface Solution {
  solutionId: string;
  name: string;
  description?: string;
  appId?: string;
  icon?: string;
  version: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  views: SolutionViewLink[];
}

export interface SolutionSummary {
  solutionId: string;
  name: string;
  description?: string;
  appId?: string;
  icon?: string;
  viewCount: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
}
