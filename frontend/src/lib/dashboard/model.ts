import type { PanelQuery, TimeRange } from './types';

export interface GridPos {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface DataSourceRef {
  type: string;
  uid: string;
}

export interface TransformConfig {
  id: string;
  options: Record<string, unknown>;
}

export interface FieldConfigModel {
  defaults?: Record<string, unknown>;
  overrides?: Array<{
    matcher: { id: string; options: unknown };
    properties: Array<{ id: string; value: unknown }>;
  }>;
}

export interface PanelModel {
  id: number;
  type: string;
  title: string;
  description?: string;
  gridPos: GridPos;
  datasource: DataSourceRef;
  targets: PanelQuery[];
  options: Record<string, unknown>;
  fieldConfig?: FieldConfigModel;
  transformations?: TransformConfig[];
  transparent?: boolean;
}

export interface VariableModel {
  name: string;
  label?: string;
  type: 'query' | 'custom' | 'constant' | 'textbox';
  query?: string;
  options?: Array<{ text: string; value: string }>;
  current?: { text: string; value: string };
  multi?: boolean;
  includeAll?: boolean;
}

export interface DashboardModel {
  uid: string;
  title: string;
  description?: string;
  tags: string[];
  panels: PanelModel[];
  time: TimeRange;
  refresh?: string;
  variables: VariableModel[];
  version: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
}

const DEFAULT_DATASOURCE: DataSourceRef = { type: 'vdl', uid: 'vdl-default' };

export function createDefaultDashboard(partial?: Partial<DashboardModel>): DashboardModel {
  return {
    uid: '',
    title: 'New Dashboard',
    description: '',
    tags: [],
    panels: [],
    time: { from: 'now-6h', to: 'now' },
    refresh: '',
    variables: [],
    version: 0,
    createdAt: '',
    updatedAt: '',
    createdBy: '',
    ...partial,
  };
}

let _nextPanelId = 1;

export function getNextPanelId(panels: PanelModel[]): number {
  const maxId = panels.reduce((max, p) => Math.max(max, p.id), 0);
  _nextPanelId = maxId + 1;
  return _nextPanelId;
}

export function createDefaultPanel(
  type: string,
  panels: PanelModel[],
  gridPos?: Partial<GridPos>,
): PanelModel {
  const id = getNextPanelId(panels);
  const defaultY = panels.reduce((maxY, p) => Math.max(maxY, p.gridPos.y + p.gridPos.h), 0);
  return {
    id,
    type,
    title: 'Panel Title',
    gridPos: { x: 0, y: defaultY, w: 12, h: 8, ...gridPos },
    datasource: DEFAULT_DATASOURCE,
    targets: [{ refId: 'A', entity: '' }],
    options: {},
  };
}
