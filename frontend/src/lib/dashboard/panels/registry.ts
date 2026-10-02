import {
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  Table2,
  AlertTriangle,
  Gauge,
  Type,
  Activity,
  BarChartHorizontal,
  TrendingUp,
  BarChart2,
  Grid3x3,
  GanttChart,
  Crosshair,
  CalendarCheck,
  GitBranch,
  CandlestickChart,
  List,
  ArrowUpRight,
  MapPin,
} from 'lucide-react';
import type { PanelPlugin } from './types';
import { KPICardPanel } from './kpi-card/KPICardPanel';
import { BarChartPanel } from './bar-chart/BarChartPanel';
import { LineChartPanel } from './line-chart/LineChartPanel';
import { PieChartPanel } from './pie-chart/PieChartPanel';
import { TablePanel } from './table/TablePanel';
import { AlertListPanel } from './alert-list/AlertListPanel';
import { GaugePanel } from './gauge/GaugePanel';
import { TextMarkdownPanel } from './text-markdown/TextMarkdownPanel';
import { BarGaugePanel } from './bar-gauge/BarGaugePanel';
import { TimeSeriesPanel } from './time-series/TimeSeriesPanel';
import { HistogramPanel } from './histogram/HistogramPanel';
import { HeatmapPanel } from './heatmap/HeatmapPanel';
import { StateTimelinePanel } from './state-timeline/StateTimelinePanel';
import { XYChartPanel } from './xy-chart/XYChartPanel';
import { StatusHistoryPanel } from './status-history/StatusHistoryPanel';
import { TrendPanel } from './trend/TrendPanel';
import { NodeGraphPanel } from './node-graph/NodeGraphPanel';
import { CandlestickPanel } from './candlestick/CandlestickPanel';
import { AnnotationsListPanel } from './annotations-list/AnnotationsListPanel';
import { GeomapPanel } from './geomap/GeomapPanel';
import {
  ChartOptionsEditor,
  KPIOptionsEditor,
  PieChartOptionsEditor,
  TableOptionsEditor,
  GaugeOptionsEditor,
  TextOptionsEditor,
  BarGaugeOptionsEditor,
  TimeSeriesOptionsEditor,
  HistogramOptionsEditor,
  HeatmapOptionsEditor,
  StateTimelineOptionsEditor,
  XYChartOptionsEditor,
  StatusHistoryOptionsEditor,
  TrendOptionsEditor,
  NodeGraphOptionsEditor,
  CandlestickOptionsEditor,
  AnnotationsListOptionsEditor,
  GeomapOptionsEditor,
  EmptyOptionsEditor,
} from './common-options-editor';

const panelPlugins: Map<string, PanelPlugin> = new Map();

function register(plugin: PanelPlugin) {
  panelPlugins.set(plugin.meta.id, plugin);
}

register({
  meta: {
    id: 'kpi-card',
    name: 'KPI Card',
    description: 'Single stat / KPI value with optional trend indicator',
    icon: Activity,
    category: 'stat',
    defaultOptions: {},
    optionsEditor: KPIOptionsEditor,
  },
  component: KPICardPanel,
});

register({
  meta: {
    id: 'bar-chart',
    name: 'Bar Chart',
    description: 'Vertical bar chart for comparing categories',
    icon: BarChart3,
    category: 'chart',
    defaultOptions: { color: '#3b82f6' },
    optionsEditor: ChartOptionsEditor,
  },
  component: BarChartPanel,
});

register({
  meta: {
    id: 'line-chart',
    name: 'Line Chart',
    description: 'Line chart for time series or trends',
    icon: LineChartIcon,
    category: 'chart',
    defaultOptions: { color: '#3b82f6' },
    optionsEditor: ChartOptionsEditor,
  },
  component: LineChartPanel,
});

register({
  meta: {
    id: 'pie-chart',
    name: 'Pie Chart',
    description: 'Pie / donut chart for distribution',
    icon: PieChartIcon,
    category: 'chart',
    defaultOptions: {},
    optionsEditor: PieChartOptionsEditor,
  },
  component: PieChartPanel,
});

register({
  meta: {
    id: 'table',
    name: 'Table',
    description: 'Data table with scrollable rows',
    icon: Table2,
    category: 'table',
    defaultOptions: {},
    optionsEditor: TableOptionsEditor,
  },
  component: TablePanel,
});

register({
  meta: {
    id: 'alert-list',
    name: 'Alert List',
    description: 'List of alerts with severity indicators',
    icon: AlertTriangle,
    category: 'misc',
    defaultOptions: {},
    optionsEditor: EmptyOptionsEditor,
  },
  component: AlertListPanel,
});

register({
  meta: {
    id: 'gauge',
    name: 'Gauge',
    description: 'Gauge meter for showing progress toward a goal',
    icon: Gauge,
    category: 'stat',
    defaultOptions: { min: 0, max: 100 },
    optionsEditor: GaugeOptionsEditor,
  },
  component: GaugePanel,
});

register({
  meta: {
    id: 'text-markdown',
    name: 'Text / Markdown',
    description: 'Static text or markdown content',
    icon: Type,
    category: 'misc',
    defaultOptions: { content: '', mode: 'markdown' },
    optionsEditor: TextOptionsEditor,
  },
  component: TextMarkdownPanel,
});

register({
  meta: {
    id: 'bar-gauge',
    name: 'Bar Gauge',
    description: 'Horizontal and vertical gauges for comparing values',
    icon: BarChartHorizontal,
    category: 'stat',
    defaultOptions: { min: 0, max: 100, orientation: 'horizontal', displayMode: 'gradient' },
    optionsEditor: BarGaugeOptionsEditor,
  },
  component: BarGaugePanel,
});

register({
  meta: {
    id: 'time-series',
    name: 'Time Series',
    description: 'Multi-series line, area, and bar charts over time',
    icon: TrendingUp,
    category: 'chart',
    defaultOptions: { drawStyle: 'line', fillOpacity: 0, stacking: 'none', showLegend: true },
    optionsEditor: TimeSeriesOptionsEditor,
  },
  component: TimeSeriesPanel,
});

register({
  meta: {
    id: 'histogram',
    name: 'Histogram',
    description: 'Distribution of values as bucketed bars',
    icon: BarChart2,
    category: 'chart',
    defaultOptions: { bucketCount: 0, color: '#3b82f6' },
    optionsEditor: HistogramOptionsEditor,
  },
  component: HistogramPanel,
});

register({
  meta: {
    id: 'heatmap',
    name: 'Heatmap',
    description: 'Color-coded grid for patterns across two dimensions',
    icon: Grid3x3,
    category: 'chart',
    defaultOptions: { colorScheme: 'blues', cellGap: 1, showTooltip: true },
    optionsEditor: HeatmapOptionsEditor,
  },
  component: HeatmapPanel,
});

register({
  meta: {
    id: 'state-timeline',
    name: 'State Timeline',
    description: 'State changes and durations over time',
    icon: GanttChart,
    category: 'timeline',
    defaultOptions: { showValue: 'auto', rowHeight: 28 },
    optionsEditor: StateTimelineOptionsEditor,
  },
  component: StateTimelinePanel,
});

register({
  meta: {
    id: 'xy-chart',
    name: 'XY Chart',
    description: 'Scatter and bubble plots for variable relationships',
    icon: Crosshair,
    category: 'chart',
    defaultOptions: { pointSize: 8 },
    optionsEditor: XYChartOptionsEditor,
  },
  component: XYChartPanel,
});

register({
  meta: {
    id: 'status-history',
    name: 'Status History',
    description: 'Periodic status grid for multiple entities over time',
    icon: CalendarCheck,
    category: 'timeline',
    defaultOptions: { showValue: false },
    optionsEditor: StatusHistoryOptionsEditor,
  },
  component: StatusHistoryPanel,
});

register({
  meta: {
    id: 'trend',
    name: 'Trend',
    description: 'Like time series but X-axis is ordinal or numeric',
    icon: ArrowUpRight,
    category: 'chart',
    defaultOptions: { drawStyle: 'line', showPoints: true, showLegend: true },
    optionsEditor: TrendOptionsEditor,
  },
  component: TrendPanel,
});

register({
  meta: {
    id: 'node-graph',
    name: 'Node Graph',
    description: 'Force-directed network and dependency visualization',
    icon: GitBranch,
    category: 'graph',
    defaultOptions: { nodeSize: 16 },
    optionsEditor: NodeGraphOptionsEditor,
  },
  component: NodeGraphPanel,
});

register({
  meta: {
    id: 'candlestick',
    name: 'Candlestick',
    description: 'OHLC chart for price and financial data',
    icon: CandlestickChart,
    category: 'chart',
    defaultOptions: { colorUp: '#22c55e', colorDown: '#ef4444' },
    optionsEditor: CandlestickOptionsEditor,
  },
  component: CandlestickPanel,
});

register({
  meta: {
    id: 'annotations-list',
    name: 'Annotations List',
    description: 'Chronological list of events and annotations',
    icon: List,
    category: 'misc',
    defaultOptions: { showTags: true, showUser: true, limit: 50 },
    optionsEditor: AnnotationsListOptionsEditor,
  },
  component: AnnotationsListPanel,
});

register({
  meta: {
    id: 'geomap',
    name: 'Geomap',
    description: 'Geographic visualization with coordinate markers',
    icon: MapPin,
    category: 'misc',
    defaultOptions: { pointSize: 6 },
    optionsEditor: GeomapOptionsEditor,
  },
  component: GeomapPanel,
});

export function getPanelPlugin(id: string): PanelPlugin | undefined {
  return panelPlugins.get(id);
}

export function getAllPanelPlugins(): PanelPlugin[] {
  return Array.from(panelPlugins.values());
}

export function getPanelPluginsByCategory(category: string): PanelPlugin[] {
  return getAllPanelPlugins().filter((p) => p.meta.category === category);
}
