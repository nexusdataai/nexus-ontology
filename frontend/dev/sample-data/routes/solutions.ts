/**
 * Solutions: the catalogue and the per-solution app pages
 * (dashboard KPIs, alerts, widget queries, live entity counts).
 * Solution ids match src/config/appRegistry.ts.
 */
import { type SampleRoute, ago, asObj, between, entityByName, entityRows, HOUR } from '../fixtures';
import { APP_PREFIX, KPIS, alertsFor, runQuery } from '../rows';

const CATALOGUE = [
  { solutionId: 'order-to-cash', title: 'Order-to-Cash Monitor', category: 'Finance', priority: 'P1', timeToValue: '4 weeks', icon: 'ShoppingCart', color: 'from-primary to-primary', journey: 'jr-o2c-01',
    description: 'End-to-end visibility and anomaly detection across the order-to-cash lifecycle.',
    entities: ['Opportunity', 'Account', 'Delivery_Document', 'AR_Invoice', 'AR_Payment', 'AR_Customer'],
    kpis: ['DSO under 35 days', 'Match rate over 95%', 'Leakage under 0.5%'],
    nlq: ['Which invoices are more than 30 days overdue?', 'Show orders delivered but not invoiced'] },
  { solutionId: 'demand-forecasting', title: 'Demand Forecasting Engine', category: 'Planning', priority: 'P1', timeToValue: '6 weeks', icon: 'TrendingUp', color: 'from-primary to-success', journey: 'jr-dfc-01',
    description: 'Forecasts by SKU and region from sales history, promotions and market signals.',
    entities: ['Material_Master', 'Opportunity', 'Inventory_Position', 'Campaign', 'Market_Signal', 'Account'],
    kpis: ['MAPE under 15%', 'Bias under 3%', 'Stockouts under 2%'],
    nlq: ['What is the forecast for Zero Sugar in the West next month?'] },
  { solutionId: 'inventory-optimization', title: 'Inventory Optimization', category: 'Operations', priority: 'P1', timeToValue: '4 weeks', icon: 'Package', color: 'from-success to-primary', journey: 'jr-inv-01',
    description: 'Reorder points, expiry risk and transfers between plants.',
    entities: ['Inventory_Position', 'Material_Master', 'Plant_Master', 'Production_Order'],
    kpis: ['Turns over 12', 'Fill rate over 97%', 'Write-off under 1%'],
    nlq: ['Which SKUs are below their reorder point?'] },
  { solutionId: 'procurement-analytics', title: 'Procurement & Spend Analytics', category: 'Finance', priority: 'P2', timeToValue: '5 weeks', icon: 'Receipt', color: 'from-warning to-primary', journey: 'jr-prc-01',
    description: 'Spend visibility, maverick detection and price checks against contracts.',
    entities: ['Purchase_Order', 'Goods_Receipt', 'AP_Invoice', 'Vendor_Master', 'Contract_Document', 'Invoice_Upload'],
    kpis: ['Maverick spend under 5%', 'Straight-through over 80%'],
    nlq: ['Which purchase orders are above the contract price?'] },
  { solutionId: 'production-quality', title: 'Production & Quality Copilot', category: 'Operations', priority: 'P2', timeToValue: '8 weeks', icon: 'Factory', color: 'from-primary to-warning', journey: null,
    description: 'Line efficiency, yield and quality release, with batch-level lab results.',
    entities: ['Production_Order', 'Plant_Master', 'Material_Master', 'Lab_Report_Upload'],
    kpis: ['OEE over 85%', 'Yield over 98%', 'First pass over 95%'],
    nlq: ['Which lines ran below 80% OEE this week?'] },
  { solutionId: 'supply-chain-risk', title: 'Supply Chain Risk Radar', category: 'Risk', priority: 'P1', timeToValue: '3 weeks', icon: 'Shield', color: 'from-destructive to-warning', journey: 'jr-risk-01',
    description: 'Supplier risk scores and early warning from external market signals.',
    entities: ['Vendor_Master', 'Purchase_Order', 'Market_Signal', 'Contract_Document', 'Goods_Receipt', 'Commodity_Price'],
    kpis: ['On-time delivery over 95%', 'No single-source materials'],
    nlq: ['Which suppliers moved into the high-risk band this week?'] },
  { solutionId: 'customer-360', title: 'Customer 360 & Revenue Growth', category: 'Revenue', priority: 'P2', timeToValue: '6 weeks', icon: 'Users', color: 'from-primary to-destructive', journey: null,
    description: 'One profile per customer with lifetime value, churn risk and cross-sell openings.',
    entities: ['Account', 'Opportunity', 'AR_Customer', 'AR_Invoice', 'Brand_Sentiment'],
    kpis: ['Churn risk under 10%', 'Cross-sell over 25%'],
    nlq: ['Which accounts are at risk of churn?'] },
  { solutionId: 'esg-sustainability', title: 'ESG & Sustainability Tracker', category: 'ESG', priority: 'P3', timeToValue: '6 weeks', icon: 'Leaf', color: 'from-success to-success', journey: null,
    description: 'Carbon, water and packaging metrics per plant against targets.',
    entities: ['Sustainability_Report', 'Material_Master', 'Plant_Master', 'Brand_Sentiment'],
    kpis: ['Recycled content over 50%', 'Water under 2.0 L per case'],
    nlq: ['Which plant is furthest from its carbon target?'] },
  { solutionId: 'trade-cpq', title: 'Trade CPQ', category: 'CPQ', priority: 'P2', timeToValue: '8 weeks', icon: 'ClipboardList', color: 'from-primary to-primary', journey: null,
    description: 'Configure, price and quote trade offerings with margin guardrails and approvals.',
    entities: ['Account', 'Opportunity', 'Campaign', 'Material_Master'],
    kpis: ['Margin over 15%', 'Quote cycle under 3 days'],
    nlq: ['Which open quotes are below the margin floor?'] },
  { solutionId: 'sourcing-cpq', title: 'Sourcing CPQ', category: 'CPQ', priority: 'P3', timeToValue: '8 weeks', icon: 'Truck', color: 'from-warning to-success', journey: null,
    description: 'Run RFx events, compare supplier bids and model award scenarios.',
    entities: ['Vendor_Master', 'Purchase_Order', 'Contract_Document', 'Commodity_Price'],
    kpis: ['Savings over 5%', 'Concentration under 60%'],
    nlq: ['Compare the bids for the 2027 aluminium can tender'] },
  { solutionId: 'logistics-control-tower', title: 'Logistics Control Tower', category: 'Operations', priority: 'P3', timeToValue: '10 weeks', icon: 'Truck', color: '', journey: null, status: 'coming_soon',
    description: 'Shipment tracking, carrier performance and delay prediction across lanes.',
    entities: ['Delivery_Document', 'Plant_Master', 'Market_Signal'],
    kpis: ['On-time in-full over 96%'],
    nlq: [] },
  { solutionId: 'trade-promotion-optimizer', title: 'Trade Promotion Optimizer', category: 'Revenue', priority: 'P3', timeToValue: '12 weeks', icon: 'BarChart3', color: '', journey: null, status: 'coming_soon',
    description: 'Measures promotion return and recommends the next promotion calendar.',
    entities: ['Campaign', 'Opportunity', 'Account', 'Brand_Sentiment'],
    kpis: ['Promotion ROI over 1.4'],
    nlq: [] },
].map(s => ({
  solutionId: s.solutionId,
  title: s.title,
  description: s.description,
  priority: s.priority,
  category: s.category,
  timeToValue: s.timeToValue,
  verticals: ['supply_chain', ...(s.category === 'Revenue' || s.category === 'Finance' ? ['crm'] : [])],
  personas: s.category === 'Finance' ? ['Finance Controller', 'Credit Manager'] : s.category === 'Risk' ? ['Procurement Lead', 'Supply Chain Director'] : ['Planner', 'Operations Manager'],
  entities: s.entities,
  kpis: s.kpis,
  automations: [],
  analytics: [],
  nlq_examples: s.nlq,
  ...(s.color ? { color: s.color } : {}),
  icon: s.icon,
  ...(s.journey ? { journeyId: s.journey } : {}),
  status: ((s as { status?: string }).status || 'available') as 'available' | 'coming_soon',
}));

/** Solutions (view collections) attached to an app. Shared with analytics.ts. */
export const APP_SOLUTION: Record<string, string> = {
  'order-to-cash': 'sol-finance-ops',
  'inventory-optimization': 'sol-supply-planning',
  'supply-chain-risk': 'sol-supplier-risk',
};

function searchCatalogue(query: string, limit: number) {
  const words = query.toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 2);
  const scored = CATALOGUE.map(s => {
    const hay = `${s.title} ${s.description} ${s.entities.join(' ')} ${s.kpis.join(' ')} ${s.nlq_examples.join(' ')}`.toLowerCase();
    return { s, hits: words.filter(w => hay.includes(w)).length };
  }).sort((a, b) => b.hits - a.hits).slice(0, limit);
  return scored.map((x, i) => ({
    content_type: 'solution',
    source_id: x.s.solutionId,
    content: `${x.s.title}: ${x.s.description}`,
    similarity: Math.max(0.38, Math.round((0.9 - i * 0.11) * (x.hits ? 1 : 0.6) * 100) / 100),
    metadata: { category: x.s.category, priority: x.s.priority },
  }));
}

const prefixFor = (appId: string) => APP_PREFIX[appId] || 'O2C';

export const solutionsRoutes: SampleRoute[] = [
  // Catalogue
  { method: 'GET', path: '/api/v1/solution-catalog', handle: () => ({ total: CATALOGUE.length, items: CATALOGUE }) },
  {
    method: 'POST', path: '/api/v1/solution-catalog/search',
    handle: ({ body }) => {
      const b = asObj(body);
      const items = searchCatalogue(String(b.query || ''), Number(b.limit) || 5);
      return { query: b.query, total: items.length, items };
    },
  },
  { method: 'POST', path: '/api/v1/solution-catalog', handle: ({ body }) => ({ status: 'available', ...asObj(body) }) },
  { method: 'GET', path: /^\/api\/v1\/solution-catalog\/([^/]+)$/, handle: ({ match }) => CATALOGUE.find(s => s.solutionId === decodeURIComponent(match[1])) || CATALOGUE[0] },

  // App pages
  {
    method: 'GET', path: /^\/api\/v1\/apps\/([^/]+)\/dashboard$/,
    handle: ({ match }) => {
      const prefix = prefixFor(match[1]);
      // CPQ cards are computed by widget queries, so no snapshot is returned for them.
      const snapshot = prefix === 'TCPQ' || prefix === 'SCPQ' ? {} : KPIS[prefix];
      return { app_id: match[1], kpis: snapshot, job_id: 'JOB-0064', generated_at: ago(42), source: 's3' };
    },
  },
  {
    method: 'GET', path: /^\/api\/v1\/apps\/([^/]+)\/alerts$/,
    handle: ({ match }) => {
      const alerts = alertsFor(prefixFor(match[1]));
      return { app_id: match[1], alerts, total: alerts.length, generated_at: ago(42) };
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/apps\/([^/]+)\/query$/,
    handle: ({ body }) => {
      const b = asObj(body);
      const { rows, total } = runQuery({ entity: String(b.entity || ''), fields: b.columns, aggregation: b.aggregation, groupBy: b.groupBy, orderBy: b.orderBy, filters: b.filters, limit: b.limit });
      return { rows, total, source: 'vdl', entity: b.entity, duration_ms: between(`appq-${b.entity}`, 30, 240) };
    },
  },
  {
    method: 'GET', path: /^\/api\/v1\/apps\/([^/]+)\/live\/([^/]+)$/,
    handle: ({ match, query }) => {
      const name = decodeURIComponent(match[2]);
      const e = entityByName(name);
      const limit = Number(query.get('limit')) || 5;
      return e
        ? { entity: name, rows: entityRows(e, Math.min(limit, 20)), total: e.totalRows || 18, source: 'vdl', as_of: ago(HOUR) }
        : { entity: name, rows: [], total: between(`live-${name}`, 120, 9400), source: 'vdl', as_of: ago(HOUR) };
    },
  },
];
