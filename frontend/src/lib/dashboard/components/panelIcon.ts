import type { IconName } from '@/components/ds/Icon';
import type { PanelPluginMeta } from '../panels/types';

/** Product icon for a visualisation type (the picker and the panel editor). */
const BY_ID: Record<string, IconName> = {
  'kpi-card': 'trend-up',
  'bar-chart': 'chart-bar',
  'line-chart': 'activity',
  'time-series': 'activity',
  trend: 'trend-up',
  table: 'table',
  'alert-list': 'alert-triangle',
  'annotations-list': 'list',
  'text-markdown': 'document',
  'node-graph': 'network',
  geomap: 'globe',
  heatmap: 'grid',
  'state-timeline': 'history',
  'status-history': 'history',
};

const BY_CATEGORY: Record<PanelPluginMeta['category'], IconName> = {
  stat: 'target',
  chart: 'chart-bar',
  table: 'table',
  timeline: 'history',
  graph: 'graph',
  misc: 'cube',
};

export function panelIconName(meta: Pick<PanelPluginMeta, 'id' | 'category'>): IconName {
  return BY_ID[meta.id] || BY_CATEGORY[meta.category] || 'chart-bar';
}

/** "KPI Card" -> "KPI card": plugin names in sentence case, acronyms kept. */
export function panelTypeLabel(name: string): string {
  return name
    .split(' ')
    .map((w, i) => (i === 0 || w === w.toUpperCase() ? w : w.toLowerCase()))
    .join(' ');
}

export const PANEL_CATEGORIES: Array<{ id: 'all' | PanelPluginMeta['category']; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'stat', label: 'Numbers' },
  { id: 'chart', label: 'Charts' },
  { id: 'table', label: 'Tables' },
  { id: 'timeline', label: 'Timelines' },
  { id: 'graph', label: 'Graphs' },
  { id: 'misc', label: 'Other' },
];
