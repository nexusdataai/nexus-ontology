/**
 * AI Analytics: dashboards (with panels that query the virtual data layer),
 * views (tabbed dashboards) and solutions (collections of views).
 */
import { type SampleRoute, PEOPLE, ago, asObj, emailOf, entityByName, HOUR, DAY } from '../fixtures';
import { runQuery, isKnownResultEntity } from '../rows';
import { APP_SOLUTION } from './solutions';

// ---------------------------------------------------------------------------
// Dashboards
// ---------------------------------------------------------------------------

const DS = { type: 'vdl', uid: 'vdl-default' };

interface PanelSeed {
  type: string; title: string; description?: string;
  /** [x, y, w, h] on a 24-column grid. */
  grid: [number, number, number, number];
  entity?: string; fields?: string[];
  aggregation?: { function: string; field?: string }; groupBy?: string[]; orderBy?: string; limit?: number;
  options?: Record<string, unknown>;
}

const panel = (p: PanelSeed, i: number) => ({
  id: i + 1,
  type: p.type,
  title: p.title,
  description: p.description || '',
  gridPos: { x: p.grid[0], y: p.grid[1], w: p.grid[2], h: p.grid[3] },
  datasource: DS,
  targets: p.entity
    ? [{ refId: 'A', entity: p.entity, fields: p.fields, aggregation: p.aggregation, groupBy: p.groupBy, orderBy: p.orderBy, limit: p.limit ?? 100 }]
    : [],
  options: p.options || {},
});

const kpi = (title: string, x: number, entity: string, field: string, options: Record<string, unknown>): PanelSeed =>
  ({ type: 'kpi-card', title, grid: [x, 0, 6, 4], entity, fields: [field], limit: 1, options: { valueField: field, ...options } });

const CATEGORY_COLORS = { Carbonated: '#ef4444', Juice: '#f59e0b', Water: '#3b82f6', Energy: '#22c55e', Sports: '#8b5cf6', Tea: '#06b6d4', Snacks: '#ec4899' };

const DASHBOARD_SEEDS: { uid: string; title: string; description: string; tags: string[]; by: string; createdMin: number; updatedMin: number; refresh: string; from: string; panels: PanelSeed[] }[] = [
  {
    uid: 'dash-o2c-overview', title: 'Order-to-Cash overview', description: 'Receivables, order matching and collection actions.', tags: ['finance', 'o2c'], by: PEOPLE[1], createdMin: DAY * 26, updatedMin: HOUR * 5, refresh: '5m', from: 'now-30d',
    panels: [
      kpi('Days sales outstanding', 0, 'O2C_KPI_Snapshot', 'dso', { unit: ' days', target: 35, direction: 'lower' }),
      kpi('Open receivables', 6, 'O2C_KPI_Snapshot', 'total_open_ar', { format: 'currency' }),
      kpi('Match rate', 12, 'O2C_KPI_Snapshot', 'match_rate', { unit: '%', target: 95, direction: 'higher' }),
      kpi('Revenue leakage', 18, 'O2C_KPI_Snapshot', 'leakage_rate', { unit: '%', target: 0.5, direction: 'lower' }),
      { type: 'time-series', title: 'DSO, last 30 days', grid: [0, 4, 14, 8], entity: 'O2C_Daily_Trend', fields: ['date', 'dso'], limit: 30, options: { xKey: 'date', yFields: ['dso'], drawStyle: 'line', fillOpacity: 0.15, showLegend: false } },
      { type: 'pie-chart', title: 'Order match status', grid: [14, 4, 10, 8], entity: 'O2C_Order_Result', fields: ['match_status'], aggregation: { function: 'count' }, groupBy: ['match_status'], limit: 20, options: { nameKey: 'match_status', valueKey: 'value', colors: { matched: '#22c55e', quantity_mismatch: '#f59e0b', price_mismatch: '#ef4444', missing_delivery: '#8b5cf6', missing_invoice: '#64748b' } } },
      { type: 'table', title: 'Highest risk orders', grid: [0, 12, 14, 9], entity: 'O2C_Order_Result', fields: ['opportunity_id', 'account_name', 'order_amount', 'match_status', 'anomaly_score'], orderBy: 'anomaly_score DESC', limit: 12 },
      { type: 'alert-list', title: 'Active alerts', grid: [14, 12, 10, 9], entity: 'O2C_Alert', limit: 20 },
    ],
  },
  {
    uid: 'dash-inventory-health', title: 'Inventory health', description: 'Stock cover, fill rate and expiry exposure by plant.', tags: ['operations', 'inventory'], by: PEOPLE[2], createdMin: DAY * 19, updatedMin: HOUR * 27, refresh: '15m', from: 'now-7d',
    panels: [
      kpi('Inventory turns', 0, 'IO_KPI_Snapshot', 'turns', { unit: 'x', target: 12, direction: 'higher' }),
      kpi('Days of supply', 6, 'IO_KPI_Snapshot', 'days_of_supply', { unit: ' days', target: 30, direction: 'lower' }),
      kpi('Expiry write-off', 12, 'IO_KPI_Snapshot', 'expired_write_off_pct', { unit: '%', target: 1, direction: 'lower' }),
      { type: 'gauge', title: 'Fill rate', grid: [18, 0, 6, 4], entity: 'IO_KPI_Snapshot', fields: ['fill_rate_pct'], limit: 1, options: { valueField: 'fill_rate_pct', min: 80, max: 100, unit: '%', thresholds: [{ value: 80, color: '#ef4444' }, { value: 92, color: '#f59e0b' }, { value: 97, color: '#22c55e' }] } },
      { type: 'bar-chart', title: 'Stock by plant (cases)', grid: [0, 4, 12, 8], entity: 'IO_Plant_Summary', fields: ['plant', 'total_qty'], orderBy: 'total_qty DESC', limit: 10, options: { xKey: 'plant', yKey: 'total_qty', color: '#22c55e' } },
      { type: 'pie-chart', title: 'Stock by category', grid: [12, 4, 6, 8], entity: 'IO_Category_Summary', fields: ['category', 'total_qty'], limit: 10, options: { nameKey: 'category', valueKey: 'total_qty', colors: CATEGORY_COLORS } },
      { type: 'bar-gauge', title: 'Fill rate by plant', grid: [18, 4, 6, 8], entity: 'IO_Plant_Summary', fields: ['plant', 'fill_rate_pct'], limit: 10, options: { nameKey: 'plant', valueKey: 'fill_rate_pct', min: 80, max: 100, thresholds: [{ value: 80, color: '#ef4444' }, { value: 92, color: '#f59e0b' }, { value: 97, color: '#22c55e' }] } },
      { type: 'table', title: 'Positions with least cover', grid: [0, 12, 24, 9], entity: 'IO_Position_Result', fields: ['sku', 'plant', 'category', 'current_qty', 'days_of_supply', 'abc_class', 'expiry_risk'], orderBy: 'days_of_supply ASC', limit: 15 },
    ],
  },
  {
    uid: 'dash-procurement-spend', title: 'Procurement spend', description: 'Spend by supplier and category, with price variance against contracts.', tags: ['finance', 'procurement'], by: PEOPLE[4], createdMin: DAY * 15, updatedMin: DAY * 2, refresh: '', from: 'now-90d',
    panels: [
      kpi('Total spend', 0, 'PA_KPI_Snapshot', 'total_spend', { format: 'currency' }),
      kpi('Maverick spend', 6, 'PA_KPI_Snapshot', 'maverick_spend_pct', { unit: '%', target: 5, direction: 'lower' }),
      kpi('Straight-through rate', 12, 'PA_KPI_Snapshot', 'stp_rate_pct', { unit: '%', target: 80, direction: 'higher' }),
      kpi('Price variance', 18, 'PA_KPI_Snapshot', 'price_variance_pct', { unit: '%', target: 5, direction: 'lower' }),
      { type: 'line-chart', title: 'Spend by month', grid: [0, 4, 14, 8], entity: 'PA_Spend_History', fields: ['month', 'total_spend'], limit: 12, options: { xKey: 'month', yKey: 'total_spend', color: '#f59e0b' } },
      { type: 'pie-chart', title: 'Spend by category', grid: [14, 4, 10, 8], entity: 'PA_Category_Summary', fields: ['category', 'total_spend'], limit: 10, options: { nameKey: 'category', valueKey: 'total_spend' } },
      { type: 'bar-chart', title: 'Top suppliers by spend', grid: [0, 12, 12, 9], entity: 'PA_Vendor_Summary', fields: ['vendor_name', 'total_spend'], orderBy: 'total_spend DESC', limit: 8, options: { xKey: 'vendor_name', yKey: 'total_spend', color: '#3b82f6' } },
      { type: 'table', title: 'Orders above contract price', grid: [12, 12, 12, 9], entity: 'PA_Spend_Result', fields: ['po_id', 'vendor', 'category', 'amount', 'price_variance'], orderBy: 'price_variance DESC', limit: 10 },
    ],
  },
  {
    uid: 'dash-supplier-risk', title: 'Supplier risk radar', description: 'Risk scores, delivery performance and external signals.', tags: ['risk', 'procurement'], by: PEOPLE[0], createdMin: DAY * 9, updatedMin: HOUR * 2, refresh: '1h', from: 'now-30d',
    panels: [
      kpi('Average risk score', 0, 'SCR_KPI_Snapshot', 'avg_risk_score', { unit: ' / 100', target: 30, direction: 'lower' }),
      kpi('On-time delivery', 6, 'SCR_KPI_Snapshot', 'otd_pct', { unit: '%', target: 95, direction: 'higher' }),
      kpi('Single-source materials', 12, 'SCR_KPI_Snapshot', 'single_source_count', { target: 0, direction: 'lower' }),
      { type: 'text-markdown', title: 'This week', grid: [18, 0, 6, 4], options: { mode: 'markdown', content: '**NutraChem Ingredients** moved to high risk after a plant fire.\n\nSecond source for taurine premix is in qualification.' } },
      { type: 'bar-chart', title: 'Average risk by region', grid: [0, 4, 10, 8], entity: 'SCR_Region_Summary', fields: ['region', 'avg_risk'], orderBy: 'avg_risk DESC', limit: 10, options: { xKey: 'region', yKey: 'avg_risk', color: '#ef4444' } },
      { type: 'table', title: 'Suppliers by risk', grid: [10, 4, 14, 8], entity: 'SCR_Vendor_Result', fields: ['vendor_name', 'region', 'risk_score', 'otd_pct', 'quality_score', 'financial_risk'], orderBy: 'risk_score DESC', limit: 10 },
      { type: 'table', title: 'Market signals', grid: [0, 12, 14, 9], entity: 'Market_Signal', fields: ['Signal_ID', 'Event_Type', 'Location', 'Affected_Commodity', 'Severity', 'Timestamp'], limit: 10 },
      { type: 'alert-list', title: 'Risk alerts', grid: [14, 12, 10, 9], entity: 'SCR_Alert', limit: 20 },
    ],
  },
  {
    uid: 'dash-demand-forecast', title: 'Demand forecast accuracy', description: 'Forecast volume and error by region and category.', tags: ['planning'], by: PEOPLE[2], createdMin: DAY * 6, updatedMin: DAY * 4, refresh: '', from: 'now-90d',
    panels: [
      kpi('Forecast error (MAPE)', 0, 'DF_KPI_Snapshot', 'mape', { unit: '%', target: 15, direction: 'lower' }),
      kpi('Forecast bias', 6, 'DF_KPI_Snapshot', 'bias', { unit: '%', target: 3, direction: 'lower' }),
      kpi('Stockout rate', 12, 'DF_KPI_Snapshot', 'stockout_rate_pct', { unit: '%', target: 2, direction: 'lower' }),
      kpi('Forecast volume', 18, 'DF_KPI_Snapshot', 'total_forecast_qty', { unit: ' cases' }),
      { type: 'time-series', title: 'Forecast against actual', grid: [0, 4, 16, 8], entity: 'DF_Weekly_Trend', fields: ['week', 'forecast_qty', 'actual_qty'], limit: 12, options: { xKey: 'week', yFields: ['forecast_qty', 'actual_qty'], drawStyle: 'line', showPoints: true } },
      { type: 'bar-chart', title: 'Forecast by region', grid: [16, 4, 8, 8], entity: 'DF_Region_Summary', fields: ['region', 'total_qty'], orderBy: 'total_qty DESC', limit: 10, options: { xKey: 'region', yKey: 'total_qty', color: '#8b5cf6' } },
      { type: 'table', title: 'Largest forecasts', grid: [0, 12, 24, 9], entity: 'DF_Forecast_Result', fields: ['sku', 'region', 'category', 'period', 'forecast_qty', 'base_forecast', 'promo_lift', 'override_applied'], orderBy: 'forecast_qty DESC', limit: 12 },
    ],
  },
  {
    uid: 'dash-customer-accounts', title: 'Customer accounts', description: 'Accounts, open invoices and payments straight from the source systems.', tags: ['finance', 'customers'], by: PEOPLE[3], createdMin: DAY * 3, updatedMin: HOUR * 20, refresh: '', from: 'now-30d',
    panels: [
      { type: 'pie-chart', title: 'Invoices by status', grid: [0, 0, 8, 8], entity: 'AR_Invoice', fields: ['status'], aggregation: { function: 'count' }, groupBy: ['status'], limit: 20, options: { nameKey: 'status', valueKey: 'value' } },
      { type: 'bar-chart', title: 'Credit limit by region', grid: [8, 0, 8, 8], entity: 'Account', fields: ['Region__c', 'Credit_Limit__c'], aggregation: { function: 'sum', field: 'Credit_Limit__c' }, groupBy: ['Region__c'], limit: 10, options: { xKey: 'Region__c', yKey: 'value', color: '#3b82f6' } },
      { type: 'bar-chart', title: 'Payments by method', grid: [16, 0, 8, 8], entity: 'AR_Payment', fields: ['method', 'amount'], aggregation: { function: 'sum', field: 'amount' }, groupBy: ['method'], limit: 10, options: { xKey: 'method', yKey: 'value', color: '#22c55e' } },
      { type: 'table', title: 'Open and overdue invoices', grid: [0, 8, 24, 10], entity: 'AR_Invoice', fields: ['invoice_id', 'customer_name', 'invoice_date', 'due_date', 'amount', 'amount_due', 'status'], limit: 15 },
    ],
  },
];

const DASHBOARDS = DASHBOARD_SEEDS.map((d, i) => ({
  uid: d.uid,
  title: d.title,
  description: d.description,
  tags: d.tags,
  panels: d.panels.map(panel),
  time: { from: d.from, to: 'now' },
  refresh: d.refresh,
  variables: i === 0 ? [{ name: 'region', label: 'Region', type: 'custom' as const, options: ['All', 'North', 'South', 'East', 'West', 'Central'].map(r => ({ text: r, value: r })), current: { text: 'All', value: 'All' } }] : [],
  version: 3 + i,
  createdAt: ago(d.createdMin),
  updatedAt: ago(d.updatedMin),
  createdBy: emailOf(d.by),
}));
const dashboardById = (uid: string) => DASHBOARDS.find(d => d.uid === uid);
const listItem = (d: (typeof DASHBOARDS)[number]) => ({ uid: d.uid, title: d.title, description: d.description, tags: d.tags, panelCount: d.panels.length, createdAt: d.createdAt, updatedAt: d.updatedAt, createdBy: d.createdBy });

function dashboardQuery(body: Record<string, any>) {
  const results: Record<string, unknown> = {};
  for (const q of Array.isArray(body.queries) ? body.queries : []) {
    const refId = String(q.ref_id || q.refId || 'A');
    const entity = String(q.entity || '');
    if (!entityByName(entity) && !isKnownResultEntity(entity)) {
      results[refId] = { ref_id: refId, rows: [], total: 0, error: `No active mapping rule for virtual entity '${entity}'` };
      continue;
    }
    const e = entityByName(entity);
    if (e && e.fdwMappingStatus !== 'mapped') {
      results[refId] = { ref_id: refId, rows: [], total: 0, source: 'vdl' };
      continue;
    }
    const { rows, total } = runQuery({ entity, fields: q.fields, filters: q.filters, aggregation: q.aggregation, groupBy: q.group_by || q.groupBy, orderBy: q.order_by || q.orderBy, limit: q.limit });
    results[refId] = { ref_id: refId, rows, total, source: e ? 'vdl' : 's3' };
  }
  return { results };
}

function entityFields(entity: string) {
  const e = entityByName(entity);
  if (e) {
    const sample = runQuery({ entity, limit: 3 }).rows;
    return e.cols.map(col => ({
      name: col.name,
      type: /int|num|dec|number/.test(col.dataType) ? 'number' : /date|time/.test(col.dataType) ? 'time' : /bool/.test(col.dataType) ? 'boolean' : 'string',
      sampleValues: sample.map(r => r[col.name]).filter(v => v != null),
    }));
  }
  const rows = runQuery({ entity, limit: 3 }).rows;
  if (!rows.length) return [];
  return Object.keys(rows[0]).map(name => {
    const v = rows[0][name];
    return { name, type: typeof v === 'number' ? 'number' : typeof v === 'boolean' ? 'boolean' : /^\d{4}-\d{2}-\d{2}/.test(String(v)) ? 'time' : 'string', sampleValues: rows.map(r => r[name]) };
  });
}

function nlQuery(body: Record<string, any>) {
  const q = String(body.query || '').toLowerCase();
  if (/supplier|vendor|risk/.test(q)) return { panel_query: { entity: 'Vendor_Master', fields: ['Vendor_Name', 'Risk_Score'], orderBy: 'Risk_Score DESC', limit: 10 }, suggested_panel_type: 'bar-chart', suggested_title: 'Suppliers by risk score', explanation: 'Read supplier names and risk scores from Vendor_Master, highest first.' };
  if (/stock|inventory|supply/.test(q)) return { panel_query: { entity: 'Inventory_Position', fields: ['Plant', 'Unrestricted_Qty'], aggregation: { function: 'sum', field: 'Unrestricted_Qty' }, groupBy: ['Plant'], limit: 10 }, suggested_panel_type: 'bar-chart', suggested_title: 'Available stock by plant', explanation: 'Sum unrestricted stock from Inventory_Position, grouped by plant.' };
  if (/order|opportunit|pipeline|sales/.test(q)) return { panel_query: { entity: 'Opportunity', fields: ['StageName'], aggregation: { function: 'count' }, groupBy: ['StageName'], limit: 10 }, suggested_panel_type: 'pie-chart', suggested_title: 'Orders by stage', explanation: 'Count opportunities grouped by stage.' };
  return { panel_query: { entity: 'AR_Invoice', fields: ['status'], aggregation: { function: 'count' }, groupBy: ['status'], limit: 10 }, suggested_panel_type: 'pie-chart', suggested_title: 'Invoices by status', explanation: 'Count invoices in AR_Invoice grouped by status.' };
}

// ---------------------------------------------------------------------------
// Views (tabbed dashboards)
// ---------------------------------------------------------------------------

const VIEWS = [
  { viewId: 'view-finance-cockpit', name: 'Finance cockpit', description: 'Receivables, spend and customer accounts in one place.', tags: ['finance'], by: PEOPLE[1], createdMin: DAY * 14, updatedMin: HOUR * 6,
    tabs: [['Order to cash', 'dash-o2c-overview', 'ShoppingCart'], ['Procurement', 'dash-procurement-spend', 'Receipt'], ['Customers', 'dash-customer-accounts', 'Users']] },
  { viewId: 'view-supply-planning', name: 'Supply planning', description: 'Demand, stock cover and supplier risk for the weekly planning meeting.', tags: ['planning', 'operations'], by: PEOPLE[2], createdMin: DAY * 10, updatedMin: DAY * 1,
    tabs: [['Demand', 'dash-demand-forecast', 'TrendingUp'], ['Inventory', 'dash-inventory-health', 'Package'], ['Suppliers', 'dash-supplier-risk', 'Shield']] },
  { viewId: 'view-supplier-review', name: 'Supplier review', description: 'Pack for the monthly supplier review.', tags: ['risk', 'procurement'], by: PEOPLE[0], createdMin: DAY * 7, updatedMin: HOUR * 30,
    tabs: [['Risk', 'dash-supplier-risk', 'Shield'], ['Spend', 'dash-procurement-spend', 'Receipt']] },
  { viewId: 'view-executive-summary', name: 'Executive summary', description: 'Headline numbers for the leadership update.', tags: ['executive'], by: PEOPLE[0], createdMin: DAY * 2, updatedMin: HOUR * 3,
    tabs: [['Cash', 'dash-o2c-overview', 'BarChart3']] },
].map(v => ({
  viewId: v.viewId,
  name: v.name,
  description: v.description,
  tags: v.tags,
  defaultTabId: `${v.viewId}-tab-1`,
  version: 2,
  createdAt: ago(v.createdMin),
  updatedAt: ago(v.updatedMin),
  createdBy: emailOf(v.by),
  tabs: v.tabs.map(([label, dashboardId, icon], i) => ({
    tabId: `${v.viewId}-tab-${i + 1}`, order: i, label, icon, dashboardId,
    simulatorRefs: i === 0 ? [{ service: 'oracle', scenario: 'month-end' }] : [],
    timeOverride: i === 1 ? { from: 'now-90d', to: 'now' } : null,
  })),
}));
type View = (typeof VIEWS)[number];
const viewById = (id: string): View => VIEWS.find(v => v.viewId === id) || { ...VIEWS[0], viewId: id, name: 'New view', description: '', tags: [], tabs: [] };
const viewSummary = (v: View) => ({ viewId: v.viewId, name: v.name, description: v.description, tags: v.tags, tabCount: v.tabs.length, createdAt: v.createdAt, updatedAt: v.updatedAt, createdBy: v.createdBy });

// ---------------------------------------------------------------------------
// Solutions (collections of views, optionally attached to an app)
// ---------------------------------------------------------------------------

const SOLUTIONS = [
  { solutionId: 'sol-finance-ops', name: 'Finance operations', description: 'Views used by the finance team.', appId: 'order-to-cash', icon: 'ShoppingCart', views: ['view-finance-cockpit', 'view-executive-summary'], by: PEOPLE[1], createdMin: DAY * 13, updatedMin: HOUR * 6 },
  { solutionId: 'sol-supply-planning', name: 'Supply planning', description: 'Views used in the weekly planning cycle.', appId: 'inventory-optimization', icon: 'Package', views: ['view-supply-planning'], by: PEOPLE[2], createdMin: DAY * 9, updatedMin: DAY * 1 },
  { solutionId: 'sol-supplier-risk', name: 'Supplier risk', description: 'Views for supplier reviews.', appId: 'supply-chain-risk', icon: 'Shield', views: ['view-supplier-review', 'view-supply-planning'], by: PEOPLE[0], createdMin: DAY * 6, updatedMin: HOUR * 30 },
].map(s => ({
  solutionId: s.solutionId,
  name: s.name,
  description: s.description,
  appId: s.appId,
  icon: s.icon,
  version: 1,
  createdAt: ago(s.createdMin),
  updatedAt: ago(s.updatedMin),
  createdBy: emailOf(s.by),
  views: s.views.map((viewId, i) => ({ viewId, order: i, name: viewById(viewId).name, displayName: null as string | null })),
}));
type Solution = (typeof SOLUTIONS)[number];
const solutionById = (id: string): Solution => SOLUTIONS.find(s => s.solutionId === id) || { ...SOLUTIONS[0], solutionId: id, name: 'New solution', description: '', appId: '', views: [] };
const solutionSummary = (s: Solution) => ({ solutionId: s.solutionId, name: s.name, description: s.description, appId: s.appId, icon: s.icon, viewCount: s.views.length, createdAt: s.createdAt, updatedAt: s.updatedAt, createdBy: s.createdBy });

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

export const analyticsRoutes: SampleRoute[] = [
  // Dashboard data
  { method: 'POST', path: '/api/v1/dashboard/query', handle: ({ body }) => dashboardQuery(asObj(body)) },
  { method: 'POST', path: '/api/v1/dashboard/nl-query', handle: ({ body }) => nlQuery(asObj(body)) },
  {
    method: 'GET', path: /^\/api\/v1\/dashboard\/datasource\/vdl\/entities\/([^/]+)\/fields$/,
    handle: ({ match }) => ({ fields: entityFields(decodeURIComponent(match[1])) }),
  },

  // Dashboards
  {
    method: 'GET', path: '/api/v1/dashboards',
    handle: ({ query }) => {
      const search = (query.get('search') || '').toLowerCase();
      const tags = (query.get('tags') || '').split(',').filter(Boolean);
      return DASHBOARDS
        .filter(d => (!search || `${d.title} ${d.description}`.toLowerCase().includes(search)) && (!tags.length || tags.some(t => d.tags.includes(t))))
        .map(listItem);
    },
  },
  {
    method: 'POST', path: '/api/v1/dashboards',
    handle: ({ body }) => ({ tags: [], panels: [], time: { from: 'now-6h', to: 'now' }, variables: [], title: 'New dashboard', ...asObj(body), uid: `dash-${Date.now().toString(36)}`, version: 1, createdAt: ago(0), updatedAt: ago(0), createdBy: emailOf(PEOPLE[0]) }),
  },
  {
    method: 'POST', path: /^\/api\/v1\/dashboards\/([^/]+)\/clone$/,
    handle: ({ match }) => {
      const d = dashboardById(match[1]) || DASHBOARDS[0];
      return { ...d, uid: `${d.uid}-copy-${Date.now().toString(36)}`, title: `${d.title} (copy)`, version: 1, createdAt: ago(0), updatedAt: ago(0) };
    },
  },
  {
    method: 'GET', path: /^\/api\/v1\/dashboards\/([^/]+)$/,
    handle: ({ match }) => dashboardById(match[1]) || { ...DASHBOARDS[0], uid: match[1], title: 'New dashboard', description: '', panels: [], tags: [] },
  },
  {
    method: 'PUT', path: /^\/api\/v1\/dashboards\/([^/]+)$/,
    handle: ({ match, body }) => {
      const d = dashboardById(match[1]) || DASHBOARDS[0];
      return { ...d, ...asObj(body), uid: match[1], version: d.version + 1, updatedAt: ago(0) };
    },
  },
  { method: 'DELETE', path: /^\/api\/v1\/dashboards\/([^/]+)$/, handle: ({ match }) => ({ status: 'deleted', uid: match[1] }) },

  // Views
  {
    method: 'GET', path: '/api/v1/views',
    handle: ({ query }) => {
      const search = (query.get('search') || '').toLowerCase();
      const tags = (query.get('tags') || '').split(',').filter(Boolean);
      return VIEWS
        .filter(v => (!search || `${v.name} ${v.description}`.toLowerCase().includes(search)) && (!tags.length || tags.some(t => v.tags.includes(t))))
        .map(viewSummary);
    },
  },
  {
    method: 'POST', path: '/api/v1/views',
    handle: ({ body }) => ({ ...viewById(`view-${Date.now().toString(36)}`), ...asObj(body), version: 1, createdAt: ago(0), updatedAt: ago(0), createdBy: emailOf(PEOPLE[0]) }),
  },
  {
    method: 'POST', path: /^\/api\/v1\/views\/([^/]+)\/tabs\/reorder$/,
    handle: ({ match, body }) => {
      const v = viewById(match[1]);
      const ids: string[] = asObj(body).tabIds || [];
      const tabs = [...v.tabs].sort((a, b) => ids.indexOf(a.tabId) - ids.indexOf(b.tabId)).map((t, i) => ({ ...t, order: i }));
      return { ...v, tabs, updatedAt: ago(0) };
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/views\/([^/]+)\/tabs$/,
    handle: ({ match, body }) => {
      const v = viewById(match[1]);
      const b = asObj(body);
      const tab = { tabId: b.tabId || `${v.viewId}-tab-${Date.now().toString(36)}`, order: b.position ?? v.tabs.length, label: b.label || dashboardById(b.dashboardId)?.title || 'New tab', icon: b.icon || 'BarChart3', dashboardId: b.dashboardId, simulatorRefs: b.simulatorRefs || [], timeOverride: b.timeOverride ?? null };
      return { ...v, tabs: [...v.tabs, tab], updatedAt: ago(0) };
    },
  },
  {
    method: 'PUT', path: /^\/api\/v1\/views\/([^/]+)\/tabs\/([^/]+)$/,
    handle: ({ match, body }) => {
      const v = viewById(match[1]);
      return { ...v, tabs: v.tabs.map(t => (t.tabId === match[2] ? { ...t, ...asObj(body) } : t)), updatedAt: ago(0) };
    },
  },
  {
    method: 'DELETE', path: /^\/api\/v1\/views\/([^/]+)\/tabs\/([^/]+)$/,
    handle: ({ match }) => {
      const v = viewById(match[1]);
      return { ...v, tabs: v.tabs.filter(t => t.tabId !== match[2]), updatedAt: ago(0) };
    },
  },
  { method: 'GET', path: /^\/api\/v1\/views\/([^/]+)$/, handle: ({ match }) => viewById(match[1]) },
  { method: 'PUT', path: /^\/api\/v1\/views\/([^/]+)$/, handle: ({ match, body }) => ({ ...viewById(match[1]), ...asObj(body), viewId: match[1], updatedAt: ago(0) }) },
  { method: 'DELETE', path: /^\/api\/v1\/views\/([^/]+)$/, handle: ({ match }) => ({ status: 'deleted', viewId: match[1] }) },

  // Solutions
  {
    method: 'GET', path: /^\/api\/v1\/solutions\/by-app\/([^/]+)$/,
    // JSON null means "this app has no solution yet"; the app page handles it.
    handle: ({ match }) => {
      const id = APP_SOLUTION[decodeURIComponent(match[1])];
      return id ? solutionById(id) : null;
    },
  },
  {
    method: 'GET', path: '/api/v1/solutions',
    handle: ({ query }) => {
      const search = (query.get('search') || '').toLowerCase();
      return SOLUTIONS.filter(s => !search || `${s.name} ${s.description}`.toLowerCase().includes(search)).map(solutionSummary);
    },
  },
  {
    method: 'POST', path: '/api/v1/solutions',
    handle: ({ body }) => ({ ...solutionById(`sol-${Date.now().toString(36)}`), ...asObj(body), views: [], version: 1, createdAt: ago(0), updatedAt: ago(0), createdBy: emailOf(PEOPLE[0]) }),
  },
  {
    method: 'POST', path: /^\/api\/v1\/solutions\/([^/]+)\/views\/reorder$/,
    handle: ({ match, body }) => {
      const s = solutionById(match[1]);
      const ids: string[] = asObj(body).viewIds || [];
      return { ...s, views: [...s.views].sort((a, b) => ids.indexOf(a.viewId) - ids.indexOf(b.viewId)).map((v, i) => ({ ...v, order: i })), updatedAt: ago(0) };
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/solutions\/([^/]+)\/views$/,
    handle: ({ match, body }) => {
      const s = solutionById(match[1]);
      const b = asObj(body);
      return { ...s, views: [...s.views.filter(v => v.viewId !== b.viewId), { viewId: b.viewId, order: b.position ?? s.views.length, name: viewById(b.viewId).name, displayName: b.displayName ?? null }], updatedAt: ago(0) };
    },
  },
  {
    method: 'DELETE', path: /^\/api\/v1\/solutions\/([^/]+)\/views\/([^/]+)$/,
    handle: ({ match }) => {
      const s = solutionById(match[1]);
      return { ...s, views: s.views.filter(v => v.viewId !== match[2]), updatedAt: ago(0) };
    },
  },
  { method: 'GET', path: /^\/api\/v1\/solutions\/([^/]+)$/, handle: ({ match }) => solutionById(match[1]) },
  { method: 'PUT', path: /^\/api\/v1\/solutions\/([^/]+)$/, handle: ({ match, body }) => ({ ...solutionById(match[1]), ...asObj(body), solutionId: match[1], updatedAt: ago(0) }) },
  { method: 'DELETE', path: /^\/api\/v1\/solutions\/([^/]+)$/, handle: ({ match }) => ({ status: 'deleted', solutionId: match[1] }) },
];

export { DASHBOARDS };
