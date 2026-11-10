/**
 * AI Ops: diagnostics (solutions, simulators, virtual data, dashboards,
 * automation) and platform health (AI health, test reports, diagnostics audit).
 * Diagnostics are POST "run" calls; each returns a finished report with a mix
 * of pass, warning and fail so every status style shows.
 * (ReAct tool diagnostics live in reasoning.ts.)
 */
import {
  type SampleRoute, type EntityDef,
  ENTITIES, TOOLS, CONNECTOR_APIS, COPILOT_JOURNEYS, MAPPING_RULES, PEOPLE,
  ago, asObj, between, pad, round, sse, emailOf, entityByName, entityRows, systemOf, ruleForEntity, DAY,
} from '../fixtures';
import { KPIS, alertsFor, runQuery } from '../rows';
import { DASHBOARDS } from './analytics';
import { AUTOMATION_REGISTRY } from './automation';

const worst = (statuses: string[]) =>
  statuses.some(s => ['fail', 'no_data', 'missing', 'error'].includes(s)) ? 'fail' : statuses.some(s => ['warn', 'inactive'].includes(s)) ? 'warn' : 'pass';

// ---------------------------------------------------------------------------
// Solution diagnostics (O2C, DF, IO, PA, PQ, SCR, C360, ESG)
// ---------------------------------------------------------------------------

interface SolutionDiag { prefix: string; entities: string[]; result: { name: string; rows: number; summary: Record<string, unknown>; breakdown?: Record<string, unknown>[] } }

const SOLUTION_DIAG: Record<string, SolutionDiag> = {
  o2c: { prefix: 'O2C', entities: ['Opportunity', 'Account', 'Delivery_Document', 'AR_Invoice', 'AR_Payment', 'AR_Customer'], result: { name: 'O2C_Order_Result', rows: 5310, summary: { matched: 4970, mismatched: 340, match_rate_pct: 93.6, total_value: 48620000, high_risk: 64 } } },
  df: { prefix: 'DF', entities: ['Material_Master', 'Opportunity', 'Inventory_Position', 'Campaign', 'Market_Signal', 'Account'], result: { name: 'DF_Forecast_Result', rows: 4160, summary: { total_rows: 4160, categories: 7, regions: 5, total_forecast_qty: 1284000, top_category: 'Energy' }, breakdown: [{ region: 'North', total_qty: 318000 }, { region: 'South', total_qty: 241000 }, { region: 'East', total_qty: 262000 }, { region: 'West', total_qty: 297000 }, { region: 'Central', total_qty: 166000 }] } },
  io: { prefix: 'IO', entities: ['Inventory_Position', 'Material_Master', 'Plant_Master', 'Production_Order'], result: { name: 'IO_Position_Result', rows: 6388, summary: { positions: 6388, below_reorder_point: 7, overstock: 41, expiring_soon: 12, plants: 5 }, breakdown: [{ plant: 'PL01 Rotterdam', total_qty: 412000 }, { plant: 'PL02 Leeds', total_qty: 188000 }, { plant: 'PL03 Austin', total_qty: 301000 }, { plant: 'PL04 Monterrey', total_qty: 142000 }, { plant: 'PL05 Penang', total_qty: 217000 }] } },
  pa: { prefix: 'PA', entities: ['Purchase_Order', 'Goods_Receipt', 'AP_Invoice', 'Vendor_Master', 'Contract_Document', 'Invoice_Upload'], result: { name: 'PA_Spend_Result', rows: 7615, summary: { orders: 7615, maverick_orders: 488, price_variance_orders: 212, vendors: 412, categories: 6 }, breakdown: [{ category: 'Raw_Materials', total_spend: 7420000 }, { category: 'Packaging', total_spend: 5310000 }, { category: 'Logistics', total_spend: 3180000 }, { category: 'Services', total_spend: 1240000 }, { category: 'Utilities', total_spend: 960000 }, { category: 'Equipment', total_spend: 530000 }] } },
  pq: { prefix: 'PQ', entities: ['Production_Order', 'Plant_Master', 'Material_Master', 'Lab_Report_Upload'], result: { name: 'PQ_Production_Result', rows: 3902, summary: { orders: 3902, completed: 3611, delayed: 148, below_yield_target: 207, lines: 22 }, breakdown: [{ line_id: 'LINE-01', avg_oee: 88.4 }, { line_id: 'LINE-02', avg_oee: 84.1 }, { line_id: 'LINE-03', avg_oee: 76.3 }, { line_id: 'LINE-04', avg_oee: 82.7 }, { line_id: 'LINE-05', avg_oee: 71.9 }] } },
  scr: { prefix: 'SCR', entities: ['Vendor_Master', 'Purchase_Order', 'Market_Signal', 'Contract_Document', 'Goods_Receipt', 'Commodity_Price'], result: { name: 'SCR_Vendor_Result', rows: 412, summary: { vendors: 412, high_risk: 14, medium_risk: 96, single_source: 3, signals_used: 264 }, breakdown: [{ region: 'North', avg_risk: 28.4 }, { region: 'South', avg_risk: 41.2 }, { region: 'East', avg_risk: 36.9 }, { region: 'West', avg_risk: 30.1 }, { region: 'Central', avg_risk: 33.8 }] } },
  c360: { prefix: 'C360', entities: ['Account', 'Opportunity', 'AR_Customer', 'AR_Invoice', 'Brand_Sentiment'], result: { name: 'C360_Customer_Result', rows: 1284, summary: { customers: 1284, at_risk: 112, high_value: 186, cross_sell_openings: 338, segments: 5 }, breakdown: [{ segment: 'Strategic', avg_clv: 1240000 }, { segment: 'Enterprise', avg_clv: 780000 }, { segment: 'Mid-Market', avg_clv: 362000 }, { segment: 'SMB', avg_clv: 118000 }, { segment: 'Emerging', avg_clv: 64000 }] } },
  esg: { prefix: 'ESG', entities: ['Sustainability_Report', 'Material_Master', 'Plant_Master', 'Brand_Sentiment'], result: { name: 'ESG_Plant_Result', rows: 5, summary: { plants: 5, above_carbon_target: 2, above_water_target: 2, reports_used: 14 }, breakdown: [{ plant: 'PL01 Rotterdam', carbon_emissions: 3120 }, { plant: 'PL02 Leeds', carbon_emissions: 2480 }, { plant: 'PL03 Austin', carbon_emissions: 2810 }, { plant: 'PL04 Monterrey', carbon_emissions: 2260 }, { plant: 'PL05 Penang', carbon_emissions: 2040 }] } },
};

const dataStatus = (e: EntityDef) => (e.fdwMappingStatus === 'unmapped' ? 'missing' : e.totalRows === 0 ? 'no_data' : 'pass');
const ruleStatus = (e: EntityDef) => {
  const rule = ruleForEntity(e.name);
  return !rule ? 'missing' : rule.status === 'active' ? 'pass' : rule.status === 'inactive' ? 'inactive' : 'warn';
};

function adequacyRows(names: string[]) {
  return names.map(name => {
    const e = entityByName(name)!;
    const status = dataStatus(e);
    return {
      name, system: systemOf(e).label, rows: status === 'missing' ? -1 : e.totalRows, fields: e.cols.length, status,
      ...(status === 'missing' ? { error: 'No mapping rule, so the entity cannot be queried' } : status === 'no_data' ? { error: 'Source table exists but returned no rows' } : {}),
    };
  });
}

function mappingRows(names: string[]) {
  return names.map(name => {
    const e = entityByName(name)!;
    const rule = ruleForEntity(name);
    const status = ruleStatus(e);
    const unmapped = status === 'pass' ? (name === 'AR_Invoice' ? 2 : name === 'Inventory_Position' ? 1 : 0) : 0;
    return {
      entity: name, rule_name: rule?.name, source_table: rule?.sourceTable, source_schema: rule?.sourceSchema, source_type: rule?.sourceType,
      mapped_fields: rule ? e.cols.length : 0, unmapped_fields: rule ? unmapped : e.cols.length, status,
      ...(status === 'missing' ? { issue: 'No mapping rule found' } : status === 'inactive' ? { issue: 'Rule exists but is inactive' } : status === 'warn' ? { issue: 'Rule is a draft and is not used by queries' } : unmapped ? { issue: `${unmapped} schema field(s) have no source column` } : {}),
    };
  });
}

function qualityChecks(names: string[]) {
  return names.flatMap(name => {
    const e = entityByName(name)!;
    if (dataStatus(e) !== 'pass') return [];
    return e.cols.slice(0, 3).map((col, i) => {
      // A few known weak spots, the rest clean.
      const pct = name === 'Delivery_Document' && i === 2 ? 0 : name === 'AR_Invoice' && i === 2 ? 3.4 : name === 'Vendor_Master' && i === 2 ? 12.6 : name === 'Brand_Sentiment' && i === 1 ? 6.1 : round(between(`dq-${name}-${col.name}`, 0, 0.9, 1), 1);
      const total = Math.max(e.totalRows, 1);
      return { entity: name, field: col.name, type: col.dataType, null_count: Math.round((total * pct) / 100), total_rows: total, null_pct: pct, field_present: true, status: pct > 10 ? 'fail' : pct > 2 ? 'warn' : 'pass' };
    });
  });
}

function solutionReport(key: string) {
  const cfg = SOLUTION_DIAG[key];
  const adequacy = adequacyRows(cfg.entities);
  const mapping = mappingRows(cfg.entities);
  const checks = qualityChecks(cfg.entities);
  const queries = cfg.entities.map(name => {
    const e = entityByName(name)!;
    const ok = dataStatus(e) === 'pass' && ruleStatus(e) === 'pass';
    const sample = ok ? entityRows(e, 1)[0] : {};
    return {
      entity: name, rows_returned: ok ? Math.min(e.totalRows, 100) : 0, status: ok ? 'pass' : ruleStatus(e) === 'inactive' ? 'inactive' : dataStatus(e) === 'missing' ? 'missing' : 'no_data',
      field_keys: ok ? Object.keys(sample).slice(0, 6) : [],
      sample_row: ok ? Object.fromEntries(Object.entries(sample).slice(0, 4)) : {},
      ...(ok ? {} : { error: ruleStatus(e) === 'inactive' ? 'Mapping rule is inactive' : dataStatus(e) === 'missing' ? 'No mapping rule for this entity' : 'Query returned no rows' }),
    };
  });
  const results = [
    { name: `${cfg.prefix}_KPI_Snapshot`, rows: 1, status: 'pass', kpis: KPIS[cfg.prefix] },
    { name: cfg.result.name, rows: cfg.result.rows, status: 'pass', summary: cfg.result.summary, ...(cfg.result.breakdown ? { breakdown: cfg.result.breakdown } : {}) },
    { name: `${cfg.prefix}_Alert`, rows: alertsFor(cfg.prefix).length, status: 'pass', alert_count: alertsFor(cfg.prefix).length },
    ...(key === 'o2c' ? [{ name: 'O2C_Action_Log', rows: 0, status: 'warn', error: 'No actions recorded by the last job (workflow step was skipped)' }] : []),
  ];
  const sections = {
    data_adequacy: { status: worst(adequacy.map(r => r.status)), summary: { with_data: adequacy.filter(r => r.status === 'pass').length, total_entities: adequacy.length }, entities: adequacy },
    mapping_correctness: { status: worst(mapping.map(r => (r.unmapped_fields && r.status === 'pass' ? 'warn' : r.status))), summary: { active: mapping.filter(r => r.status === 'pass').length, total_rules: mapping.filter(r => r.status !== 'missing').length, issues: mapping.filter(r => 'issue' in r).length }, rules: mapping },
    data_after_mapping: { status: worst(queries.map(q => q.status)), queries },
    data_quality: { status: worst(checks.map(ch => ch.status)), summary: { passed: checks.filter(ch => ch.status === 'pass').length, warnings: checks.filter(ch => ch.status === 'warn').length, failures: checks.filter(ch => ch.status === 'fail').length, total_checks: checks.length }, checks },
    results_analysis: { status: worst(results.map(r => r.status)), entities: results },
  };
  return { timestamp: ago(0), overall_status: worst(Object.values(sections).map(s => s.status)), sections };
}

// ---------------------------------------------------------------------------
// CPQ diagnostics
// ---------------------------------------------------------------------------

function cpqReport() {
  const ent = (name: string, system: string, rows: number, fields: number) => ({ name, system, rows, fields, status: rows > 0 ? 'ok' : 'no_data', ...(rows > 0 ? {} : { error: 'Simulator table is empty' }) });
  const sell = [ent('Product_Offering', 'tpm_sim', 48, 12), ent('Quote_Header', 'tpm_sim', 421, 18), ent('Quote_Line', 'tpm_sim', 2960, 14), ent('Price_Tier', 'tpm_sim', 36, 8), ent('Trade_Proposal', 'tpm_sim', 0, 11)];
  const buy = [ent('RFx_Event', 'sourcing_sim', 31, 13), ent('Vendor_Quote', 'sourcing_sim', 204, 10), ent('Vendor_Quote_Line', 'sourcing_sim', 1410, 12), ent('Sourcing_Scenario', 'sourcing_sim', 58, 9), ent('Should_Cost_Model', 'sourcing_sim', 44, 8), ent('Sourcing_Award', 'sourcing_sim', 18, 9)];
  const all = [...sell, ...buy];
  const rules = all.map(e => ({ entity: e.name, source_schema: e.system, source_table: e.name.toLowerCase(), mapped_fields: e.name === 'Trade_Proposal' ? 0 : e.fields, status: e.name === 'Trade_Proposal' ? 'missing' : e.name === 'Price_Tier' ? 'inactive' : 'ok' }));
  const checks = [
    { entity: 'Quote_Header', field: 'Margin_Pct', null_count: 0, total_rows: 421, null_pct: 0, status: 'pass' },
    { entity: 'Quote_Header', field: 'Validity_Date', null_count: 17, total_rows: 421, null_pct: 4.0, status: 'warn' },
    { entity: 'Quote_Line', field: 'Unit_Price', null_count: 0, total_rows: 2960, null_pct: 0, status: 'pass' },
    { entity: 'Vendor_Quote_Line', field: 'Lead_Time_Days', null_count: 212, total_rows: 1410, null_pct: 15.0, status: 'fail' },
    { entity: 'Sourcing_Scenario', field: 'Modeled_Savings', null_count: 0, total_rows: 58, null_pct: 0, status: 'pass' },
    { entity: 'RFx_Event', field: 'Category', null_count: 1, total_rows: 31, null_pct: 3.2, status: 'warn' },
  ];
  const tool = (name: string, risk: string, bucket: string, api: string | null, ok = true, approval = false) => ({ name, risk, bucket, requires_approval: approval, connector_api: api, status: ok ? 'ok' : 'missing' });
  const sellTools = [tool('cpq_configure_offering', 'read_only', 'trade-cpq', null), tool('cpq_price_quote', 'read_only', 'trade-cpq', null), tool('cpq_check_margin_floor', 'read_only', 'trade-cpq', null), tool('cpq_submit_for_approval', 'low_risk_write', 'trade-cpq', 'sfdc.quote.submit'), tool('cpq_convert_to_order', 'high_risk_write', 'trade-cpq', 'sap.sales_order.create', true, true), tool('cpq_generate_proposal', 'low_risk_write', 'trade-cpq', null, false)];
  const buyTools = [tool('rfx_create_event', 'low_risk_write', 'sourcing-cpq', 'sap.rfx.create'), tool('rfx_compare_bids', 'read_only', 'sourcing-cpq', null), tool('rfx_should_cost', 'read_only', 'sourcing-cpq', null), tool('rfx_model_scenarios', 'read_only', 'sourcing-cpq', null), tool('rfx_award', 'high_risk_write', 'sourcing-cpq', 'sap.purchase_order.create', true, true)];
  const wf = (id: string, name: string, ok = true) => ({ id, name, file: `enterprise-knowledge/workflows/${id.toLowerCase()}.yaml`, status: ok ? 'ok' : 'missing' });
  const sellWf = [wf('WF_QUOTE_APPROVAL_V1', 'Trade Quote Approval'), wf('WF_QUOTE_TO_ORDER_V1', 'Quote to Order'), wf('WF_PROMO_PLANNING_V1', 'Promotion Planning')];
  const buyWf = [wf('WF_RFX_AWARD_V1', 'RFx Award'), wf('WF_CONTRACT_RENEWAL_V1', 'Contract Renewal'), wf('WF_SUPPLIER_QUALIFICATION_V1', 'Supplier Qualification', false)];
  const policies = [
    { id: 'POL-PRICE-001', file: 'policies/pricing-policy.md', size_bytes: 1184, status: 'ok' },
    { id: 'POL-PROC-001', file: 'policies/procurement-policy.md', size_bytes: 962, status: 'ok' },
    { id: 'POL-CPQ-APPROVAL-001', file: 'policies/cpq-approval-policy.md', size_bytes: 0, status: 'missing' },
  ];
  const sections = {
    simulator_status: { status: 'warn', checks: [
      { key: 'tpm', name: 'Trade promotion simulator', message: '4 of 5 tables have data', details: { schema: 'tpm_sim', tables: 5, tables_with_data: 4, total_rows: 3465 }, status: 'warn' },
      { key: 'sourcing', name: 'Sourcing simulator', message: 'All 6 tables have data', details: { schema: 'sourcing_sim', tables: 6, tables_with_data: 6, total_rows: 1765 }, status: 'pass' },
    ] },
    data_adequacy_sell: { status: 'warn', summary: { with_data: sell.filter(e => e.rows > 0).length, total: sell.length }, entities: sell },
    data_adequacy_buy: { status: 'pass', summary: { with_data: buy.length, total: buy.length }, entities: buy },
    mapping_correctness: { status: 'warn', summary: { active: rules.filter(r => r.status === 'ok').length, total: rules.length, issues: rules.filter(r => r.status !== 'ok').length }, rules },
    data_quality: { status: 'fail', summary: { passed: 3, warnings: 2, failures: 1, total_checks: checks.length }, checks },
    tool_registry: { status: 'warn', summary: { registered: 10, expected: 11 }, sell_tools: sellTools, buy_tools: buyTools },
    workflows: { status: 'warn', summary: { present: 5, expected: 6 }, sell_workflows: sellWf, buy_workflows: buyWf },
    policies: { status: 'fail', policies },
  };
  return { timestamp: ago(0), overall_status: 'fail', sections };
}

// ---------------------------------------------------------------------------
// Simulator diagnostics
// ---------------------------------------------------------------------------

function simulatorReport() {
  const sims = [{ key: 'sfdc', label: 'Salesforce', tables: 22, rows: 48210, empty: [] as string[] }, { key: 'oracle', label: 'Oracle ERP', tables: 18, rows: 131540, empty: ['GL_Period', 'Tax_Code'] }, { key: 'sap', label: 'SAP S/4HANA', tables: 31, rows: 96875, empty: ['Goods_Receipt', 'Capacity_Plan', 'Maintenance_Order'] }, { key: 'external', label: 'External sources', tables: 9, rows: 3092, empty: ['Lab_Report_Upload'] }];
  const sections = {
    s3_source_data: { status: 'pass', checks: sims.map(s => ({ name: `${s.label} seed files`, status: 'pass', message: `${s.tables} files under s3://kinetiq-nexus-simulators/${s.key}/, last written ${s.key === 'external' ? 6 : 26} hours ago`, details: { bucket: 'kinetiq-nexus-simulators', prefix: `${s.key}/`, files: s.tables } })) },
    redis_cache_health: { status: 'warn', checks: [{ name: 'Redis', status: 'warn', message: 'Memory use is above 60% of the limit', details: { dbsize: 80, used_memory_mb: 332, used_memory_peak_mb: 418, maxmemory_mb: 512, memory_usage_pct: 64.8, maxmemory_policy: 'allkeys-lru', default_ttl_seconds: 86400, fallback_active: false, fallback_keys: 0, keys_per_simulator: { sfdc: 22, oracle: 18, sap: 31, external: 9 } } }] },
    data_loading: { status: 'warn', checks: sims.map(s => ({ name: `${s.label} loaded`, status: s.empty.length > 2 ? 'warn' : 'pass', message: `${s.tables - s.empty.length} of ${s.tables} tables loaded with data`, details: { tables: s.tables, loaded: s.tables - s.empty.length } })) },
    ttl_and_refresh: { status: 'pass', checks: [
      { name: 'Key expiry', status: 'pass', message: 'Shortest remaining TTL is 9h 12m', details: { min_ttl_seconds: 33120 } },
      { name: 'Scheduled refresh', status: 'pass', message: 'Last refresh finished 14h 48m ago, next in 9h 12m', details: { last_refresh_at: ago(888) } },
    ] },
    data_access: { status: 'fail', checks: [
      { name: 'Salesforce simulator API', status: 'pass', message: 'GET /sobjects/Account returned 200 in 84 ms', details: { latency_ms: 84 } },
      { name: 'SAP simulator API', status: 'pass', message: 'GET /A_PurchaseOrder returned 200 in 112 ms', details: { latency_ms: 112 } },
      { name: 'Oracle simulator API', status: 'fail', message: 'GET /payablesInvoices timed out after 30 s', details: { latency_ms: 30000, error: 'Gateway timeout' } },
      { name: 'External sources API', status: 'pass', message: 'GET /drive/contracts returned 200 in 201 ms', details: { latency_ms: 201 } },
    ] },
    data_volume: { status: 'warn', checks: sims.map(s => ({ name: s.label, status: s.empty.length ? 'warn' : 'pass', message: `${s.tables} tables, ${s.rows.toLocaleString('en-US')} rows`, details: { tables: s.tables, total_rows: s.rows, zero_row_count: s.empty.length, zero_row_tables: s.empty } })) },
  };
  return { timestamp: ago(0), overall_status: 'fail', sections };
}

// ---------------------------------------------------------------------------
// Virtual data diagnostics
// ---------------------------------------------------------------------------

function virtualEntityDiag(name: string) {
  const e = entityByName(name);
  const rule = e && ruleForEntity(e.name);
  const sys = e && systemOf(e);
  const checks: { code: string; status: 'pass' | 'warn' | 'fail'; message: string; suggestion?: string | null; detail?: Record<string, unknown> }[] = [];
  if (!e || !rule) {
    checks.push({ code: 'no_mapping_rule', status: 'fail', message: 'No mapping rule exists for this entity.', suggestion: 'Run Auto-map in Data Plane > Mapping rules, or create a rule by hand.' });
  } else {
    checks.push({ code: 'rule_found', status: 'pass', message: `Rule ${rule.id} maps ${rule.sourceSchema}.${rule.sourceTable}.` });
    if (rule.status !== 'active') checks.push({ code: 'inactive_rule', status: rule.status === 'draft' ? 'fail' : 'warn', message: `The rule is ${rule.status}.`, suggestion: 'Activate the rule so queries can use it.' });
    else {
      checks.push({ code: 'source_reachable', status: 'pass', message: `${sys!.label} answered in ${between(`vd-lat-${name}`, 28, 190)} ms.` });
      if (e.totalRows === 0) checks.push({ code: 'no_rows', status: 'warn', message: 'The query ran but returned no rows.', suggestion: 'Check the filter expression and the source data.' });
      else checks.push({ code: 'rows_returned', status: 'pass', message: `${e.totalRows.toLocaleString('en-US')} rows available.` });
      if (name === 'AR_Invoice') checks.push({ code: 'missing_columns', status: 'warn', message: '2 schema fields have no source column: dispute_reason, dunning_level.', suggestion: 'Add field mappings or mark the fields optional.', detail: { missing: ['dispute_reason', 'dunning_level'] } });
      if (name === 'Vendor_Master') checks.push({ code: 'null_rate', status: 'warn', message: 'Country is empty in 12.6% of rows.', suggestion: 'Set a default value in the mapping rule.' });
    }
  }
  const levels = checks.map(ch => ch.status);
  const overall = levels.includes('fail') ? 'unhealthy' : levels.includes('warn') ? 'degraded' : 'healthy';
  return {
    virtualEntity: name,
    overall,
    sourceType: rule?.sourceType || null, sourceSystem: rule?.sourceSystem || null, sourceSchema: rule?.sourceSchema || null, sourceTable: rule?.sourceTable || null,
    ruleId: rule?.id || null,
    activeRuleCount: rule?.status === 'active' ? 1 : 0, totalRuleCount: rule ? 1 : 0,
    rowCount: rule?.status === 'active' ? e!.totalRows : null,
    latencyMs: rule?.status === 'active' ? between(`vd-lat-${name}`, 28, 190) : null,
    checks,
    sampleRow: rule?.status === 'active' && e!.totalRows > 0 ? entityRows(e!, 1)[0] : null,
    durationMs: between(`vd-dur-${name}`, 60, 420),
    scannedAt: ago(0),
  };
}

function scanSummary<T extends { overall?: string; status?: string }>(items: T[]) {
  const level = (i: T) => i.overall || i.status;
  return { total: items.length, healthy: items.filter(i => level(i) === 'healthy').length, degraded: items.filter(i => level(i) === 'degraded').length, unhealthy: items.filter(i => level(i) === 'unhealthy').length };
}

// ---------------------------------------------------------------------------
// Dashboard diagnostics
// ---------------------------------------------------------------------------

function dashboardDiag(uid: string) {
  const d = DASHBOARDS.find(x => x.uid === uid) || DASHBOARDS[0];
  const panels = d.panels.filter(p => p.targets.length).map(p => {
    const t = p.targets[0];
    const payload = { entity: t.entity, fields: t.fields, aggregation: t.aggregation, group_by: t.groupBy, order_by: t.orderBy, limit: t.limit };
    const { rows } = runQuery({ entity: t.entity, fields: t.fields, aggregation: t.aggregation, groupBy: t.groupBy, orderBy: t.orderBy, limit: t.limit });
    const e = entityByName(t.entity);
    const rule = e && ruleForEntity(e.name);
    const returned = rows.length ? Object.keys(rows[0]) : [];
    const expected = t.aggregation ? [...(t.groupBy || []), 'value'] : t.fields || returned;
    // Two deliberate problems so the panel shows more than green rows.
    const slow = d.uid === 'dash-procurement-spend' && p.type === 'table';
    const missing = d.uid === 'dash-supplier-risk' && t.entity === 'Market_Signal' ? ['Summary'] : [];
    const status = missing.length ? 'fail' : slow ? 'warn' : 'pass';
    return {
      panelId: p.id, panelTitle: p.title, panelType: p.type, targetRefId: t.refId, entity: t.entity,
      sourceType: rule?.sourceType || 'S3', ruleId: rule?.id || null,
      status, code: missing.length ? 'missing_columns' : slow ? 'slow_query' : 'ok',
      latencyMs: slow ? 4180 : between(`dd-${d.uid}-${p.id}`, 24, 380), rowCount: rows.length,
      expectedFields: [...expected, ...missing], returnedFields: returned, missingFields: missing, nullGroupColumns: [],
      errorMessage: missing.length ? "Column 'Summary' is not returned by the mapping rule." : null,
      suggestion: missing.length ? 'Add the column to the mapping rule or remove it from the panel.' : slow ? 'Add a limit or a filter. The query scans every purchase order.' : null,
      queryPayload: payload,
    };
  });
  const healthy = panels.filter(p => p.status === 'pass').length;
  const degraded = panels.filter(p => p.status === 'warn').length;
  const unhealthy = panels.filter(p => p.status === 'fail').length;
  return {
    uid: d.uid, title: d.title, description: d.description, tags: d.tags,
    status: unhealthy ? 'unhealthy' : degraded ? 'degraded' : 'healthy',
    panelCount: panels.length, healthyCount: healthy, degradedCount: degraded, unhealthyCount: unhealthy,
    panels, durationMs: panels.reduce((n, p) => n + (p.latencyMs || 0), 0), scannedAt: ago(0),
  };
}

const backends = () => ({
  overall: 'degraded',
  backends: [
    { name: 'Virtual data layer', kind: 'postgres', status: 'pass', detail: `${MAPPING_RULES.filter(r => r.status === 'active').length} active mapping rules`, latencyMs: 18, metadata: { version: '16.4' } },
    { name: 'Salesforce FDW', kind: 'fdw', status: 'pass', detail: 'sfdc_server reachable', latencyMs: 96, metadata: { tables: 22 } },
    { name: 'SAP FDW', kind: 'fdw', status: 'pass', detail: 'sap_s4_server reachable', latencyMs: 131, metadata: { tables: 31 } },
    { name: 'Oracle FDW', kind: 'fdw', status: 'warn', detail: 'oracle_erp_server slow: 2.4 s on the last probe', latencyMs: 2410, metadata: { tables: 18 } },
    { name: 'Results store', kind: 's3', status: 'pass', detail: 's3://kinetiq-nexus-results reachable', latencyMs: 54, metadata: {} },
    { name: 'Redis cache', kind: 'redis', status: 'pass', detail: '80 keys, 65% of memory limit', latencyMs: 3, metadata: {} },
  ],
  scannedAt: ago(0),
});

// ---------------------------------------------------------------------------
// Automation diagnostics
// ---------------------------------------------------------------------------

const knownTools = new Set(TOOLS.map(t => t.name));

function automationDryRun() {
  const useCases = AUTOMATION_REGISTRY.map((r, i) => {
    const toolRefs = [...r.yamlText.matchAll(/tool: (\S+)/g)].map(m => m[1]);
    // One use case refers to a tool that does not exist, one to a connector API that does not.
    const missingTools = r.useCaseId === 'o2c-dispute-case' ? ['open_dispute_case'] : [];
    const missingApis = r.useCaseId === 'io-expiry-discount' ? ['sfdc.promotion.create'] : [];
    const apis = toolRefs.map(t => TOOLS.find(x => x.name === t)?.connectorApi).filter((x): x is string => !!x);
    const highRisk = toolRefs.filter(t => TOOLS.find(x => x.name === t)?.risk === 'high_risk_write').length;
    return {
      use_case_id: r.useCaseId, title: r.yamlText.split('\n')[1].replace('title: ', ''), solution_id: r.solution,
      status: missingTools.length ? 'fail' : missingApis.length ? 'warn' : 'pass',
      yaml_file: r.sourceFile, stage_count: 1, step_count: toolRefs.length + missingTools.length, binding_count: apis.length,
      tool_refs: [...toolRefs, ...missingTools], connector_api_refs: [...apis, ...missingApis],
      missing_tools: missingTools, missing_connector_apis: missingApis, high_risk_steps: highRisk,
      tags: [r.solution.split('-')[0], i % 2 ? 'scheduled' : 'on-demand'], kpi_impact: i % 3 === 0 ? ['dso', 'leakage_rate'] : i % 3 === 1 ? ['fill_rate_pct'] : ['price_variance_pct'],
    };
  });
  const sum = (key: 'stage_count' | 'step_count' | 'binding_count' | 'high_risk_steps') => useCases.reduce((n, u) => n + u[key], 0);
  return {
    yaml_root: 'enterprise-knowledge/automations', files_seen: useCases.length + 1, validated: useCases.length, validation_errors: 1,
    use_cases: useCases,
    errors: [{ file: 'enterprise-knowledge/automations/order-to-cash/o2c-legacy-holds.yaml', error: "stages[0].steps[2]: field 'tool' is required" }],
    totals: { use_cases: useCases.length, stages: sum('stage_count'), steps: sum('step_count'), tool_bindings: sum('binding_count'), connector_apis: new Set(useCases.flatMap(u => u.connector_api_refs)).size, high_risk_steps: sum('high_risk_steps'), missing_tools: 1, missing_connector_apis: 1 },
    overall: 'degraded',
    registry: { known_tools: [...knownTools], known_connector_apis: CONNECTOR_APIS.map(a => a.api_id) },
  };
}

const toolCatalogue = () => {
  const tools = TOOLS.map((t, i) => ({
    tool_id: t.name, display_name: t.name.replace(/_/g, ' ').replace(/^./, ch => ch.toUpperCase()), group: t.group, risk_level: t.risk, requires_approval: !!t.approval,
    connector_api: t.connectorApi || null, consumes_count: t.risk === 'read_only' ? 1 : 2, produces_count: i % 4 === 0 ? 0 : 1, tags: t.tags,
    registered: true, yaml_present: t.name !== 'summarise_findings', example_invocation: i % 5 !== 3,
  }));
  const groups = tools.reduce<Record<string, number>>((acc, t) => { acc[t.group] = (acc[t.group] || 0) + 1; return acc; }, {});
  return {
    totals: { yaml_tools: tools.length, registered_tools: tools.length, yaml_only_orphans: 1, registry_only_orphans: 1, groups },
    metadata_quality: { with_consumes_entities: tools.length, with_produces_entities: tools.filter(t => t.produces_count).length, with_connector_api: tools.filter(t => t.connector_api).length, with_example_invocation: tools.filter(t => t.example_invocation).length, with_tags: tools.length },
    risk_distribution: { read_only: tools.filter(t => t.risk_level === 'read_only').length, low_risk_write: tools.filter(t => t.risk_level === 'low_risk_write').length, high_risk_write: tools.filter(t => t.risk_level === 'high_risk_write').length },
    yaml_only_orphans: ['reconcile_bank_statement'], registry_only_orphans: ['summarise_findings'],
    tools,
    errors: [{ file: 'enterprise-knowledge/tools/misc/reconcile_bank_statement.yaml', phase: 'registry', error: 'YAML present but no implementation is registered' }],
    tools_yaml_root: 'enterprise-knowledge/tools',
    overall: 'degraded',
  };
};

const savedJourneysReport = () => ({
  total: COPILOT_JOURNEYS.length,
  by_kind: COPILOT_JOURNEYS.reduce<Record<string, number>>((acc, j) => { acc[j.kind] = (acc[j.kind] || 0) + 1; return acc; }, {}),
  by_solution: COPILOT_JOURNEYS.reduce<Record<string, number>>((acc, j) => { acc[j.solution_id] = (acc[j.solution_id] || 0) + 1; return acc; }, {}),
  broken_journeys: [{ journey_id: 'cj-returns-credit-note', title: 'Returns credit note', kind: 'copilot', solution_id: 'order-to-cash', missing_tools: ['create_credit_note'], missing_connector_apis: ['oracle.ar_credit_note.create'] }],
  recent: COPILOT_JOURNEYS.map(j => ({ journey_id: j.journey_id, title: j.title, kind: j.kind, solution_id: j.solution_id, createdBy: j.createdBy, createdAt: j.createdAt, updatedAt: j.updatedAt, step_count: j.step_count, validation_ok: true })),
  overall: 'degraded',
  source: 'foundry-workspace',
});

const copilotRuntime = () => ({
  session_store: { mode: 'pg', recent_count: 47, by_status: { completed: 38, awaiting_step_approval: 4, failed: 3, planned: 2 }, stuck_awaiting_approval_24h: 1 },
  vector_index: { onto_schema: 86, onto_policy: 14, onto_workflow: 23, onto_integration: 9, automation_use_case: AUTOMATION_REGISTRY.length, nlq_exemplar: 344 },
  knowledge_graph: { age_available: false, uses_metadata_fallback: true },
  tool_registry_size: TOOLS.length,
  connector_api_registry_size: CONNECTOR_APIS.length,
  overall: 'degraded',
});

const graphIntegrity = () => ({
  use_cases_checked: AUTOMATION_REGISTRY.length,
  missing_tools: 1,
  missing_connector_apis: 1,
  broken_edges: [
    { use_case_id: 'o2c-dispute-case', type: 'uses_tool', missing_target: 'open_dispute_case' },
    { use_case_id: 'io-expiry-discount', type: 'calls_api', missing_target: 'sfdc.promotion.create' },
  ],
  orphan_registry_tools: ['forecast_demand', 'query_market_signals'],
  overall: 'degraded',
  source: 'metadata-fallback',
});

const smokeTest = (goal?: string) => ({
  overall: 'degraded',
  goal: goal || 'Find invoices more than 30 days overdue and send a second notice',
  stages: [
    { name: 'plan', status: 'pass', duration_ms: 2140, detail: { steps: 4, playbook: 'o2c-dunning-run', rag_sources: 3 } },
    { name: 'validate', status: 'pass', duration_ms: 86, detail: { errors: 0, warnings: 0 } },
    { name: 'execute', status: 'pass', duration_ms: 6420, detail: { completed_steps: 4, invoices_found: 18, notices_sent: 18 } },
    { name: 'save', status: 'pass', duration_ms: 310, detail: { persisted: true } },
    { name: 'rerun_saved', status: 'fail', duration_ms: 30012, detail: { error: 'Step send_notice timed out calling oracle.ar_invoice.add_dunning' } },
    { name: 'cleanup', status: 'skip', duration_ms: 0, detail: { reason: 'Kept for inspection because a stage failed' } },
  ],
  session_id: `cps-0-${Date.now().toString(36)}`,
  journey_id: 'cj-smoke-test-dunning',
});

// ---------------------------------------------------------------------------
// Diagnostics history
// ---------------------------------------------------------------------------

const HISTORY_SCOPES = ['o2c', 'df', 'io', 'pa', 'pq', 'scr', 'c360', 'esg', 'cpq', 'simulators', 'virtual-entities', 'dashboards', 'automation', 'react-tools', 'connector-apis'];

function historyRuns(scope: string, limit: number) {
  const count = Math.min(limit, 9);
  return Array.from({ length: count }, (_, k) => {
    const recordedAt = ago(35 + k * between(`hist-${scope}-${k}`, 300, 900));
    const succeeded = !(k === 2 || (scope === 'pa' && k === 0));
    const status = !succeeded ? 'fail' : k % 4 === 1 ? 'warn' : 'pass';
    return {
      scope,
      run_id: `${recordedAt.replace(/[-:.TZ]/g, '').slice(0, 14)}-${pad(between(`hist-id-${scope}-${k}`, 0, 9999))}`,
      recordedAt,
      succeeded,
      summary: { overall_status: status, checks: between(`hist-c-${scope}`, 14, 42), failures: status === 'fail' ? between(`hist-f-${scope}-${k}`, 1, 4) : 0, duration_ms: between(`hist-d-${scope}-${k}`, 800, 9400), triggered_by: emailOf(PEOPLE[(k + scope.length) % PEOPLE.length]) },
    };
  });
}

function historyRun(scope: string, runId: string) {
  const run = historyRuns(scope, 50).find(r => r.run_id === runId) || historyRuns(scope, 1)[0];
  const result = SOLUTION_DIAG[scope] ? solutionReport(scope) : scope === 'cpq' ? cpqReport() : scope === 'simulators' ? simulatorReport() : { overall_status: run.summary.overall_status, checks: run.summary.checks, failures: run.summary.failures };
  return { ...run, result };
}

// ---------------------------------------------------------------------------
// AI health
// ---------------------------------------------------------------------------

function healthSnapshot(minutesAgo: number, k = 0) {
  // Mostly healthy, with a degraded spell and one unhealthy reading in the history.
  const verdict = k >= 9 && k <= 12 ? 'degraded' : k === 27 ? 'unhealthy' : k === 0 ? 'degraded' : 'healthy';
  const reasoningDegraded = verdict !== 'healthy';
  return {
    scope: 'all',
    iso_ts: ago(minutesAgo),
    verdict,
    elapsed_ms: between(`health-${k}`, 640, 2100),
    planes: {
      ai_ops: { plane: 'ai_ops', status: 'healthy', counts: { diagnostic_runs_24h: 38, failed_runs_24h: 3, test_suites: 4, alarms_open: 1 }, details: {}, errors: [] },
      data: { plane: 'data', status: verdict === 'unhealthy' ? 'unhealthy' : 'healthy', counts: { sources_connected: 6, fdw_tables: 71, mapping_rules_active: 118, pipelines_running: 1 }, details: {}, errors: verdict === 'unhealthy' ? ['oracle_erp_server did not answer within 30 s'] : [] },
      control: { plane: 'control', status: 'healthy', counts: { documents_indexed: 132, embeddings: 5630, graph_nodes: 412, graph_edges: 1287 }, details: { last_indexed_at: ago(380) }, errors: [] },
      reasoning: { plane: 'reasoning', status: reasoningDegraded ? 'degraded' : 'healthy', counts: { tools_registered: 47, connector_apis: CONNECTOR_APIS.length, agent_sessions_24h: 212, p95_latency_ms: reasoningDegraded ? 8400 : 3100 }, details: {}, errors: reasoningDegraded ? ['Model p95 latency above the 6 s threshold', 'Knowledge graph is using the metadata fallback (AGE extension not installed)'] : [] },
      workspace: { plane: 'workspace', status: 'healthy', counts: { solutions_available: 10, journeys: 6, jobs_24h: 41, failed_jobs_24h: 2, dashboards: DASHBOARDS.length }, details: {}, errors: [] },
    },
  };
}

// ---------------------------------------------------------------------------
// Test reports
// ---------------------------------------------------------------------------

const workflowRun = (k: number, status: string, conclusion: string | null) => ({
  run_id: 9184420117 - k * 31873,
  status,
  conclusion,
  html_url: `https://github.com/kinetiq-beverages/nexus-platform/actions/runs/${9184420117 - k * 31873}`,
  started_at: ago(95 + k * DAY),
  updated_at: ago(77 + k * DAY),
  actor: ['p-raman', 'd-okafor', 'm-chen', 's-lindqvist'][k % 4],
  display_title: ['Nightly test run', 'Test run: unit, integration', 'Nightly test run', 'Test run: bdd', 'Nightly test run', 'Test run: endurance'][k % 6],
});

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

const VIRTUAL = '/api/v1/diagnostics/virtual-entities';

export const opsRoutes: SampleRoute[] = [
  // Solution diagnostics
  {
    method: 'POST', path: /^\/api\/v1\/diagnostics\/(o2c|df|io|pa|pq|scr|c360|esg)$/,
    handle: ({ match }) => solutionReport(match[1]),
  },
  { method: 'POST', path: '/api/v1/diagnostics/cpq', handle: () => cpqReport() },
  { method: 'POST', path: '/api/v1/diagnostics/simulators', handle: () => simulatorReport() },

  // Virtual data diagnostics
  {
    method: 'GET', path: VIRTUAL,
    handle: () => ENTITIES.map(e => {
      const rule = ruleForEntity(e.name);
      return { virtualEntity: e.name, totalRuleCount: rule ? 1 : 0, activeRuleCount: rule?.status === 'active' ? 1 : 0, sourceSystems: rule ? [rule.sourceSystem] : [], sourceSchemas: rule ? [rule.sourceSchema] : [] };
    }),
  },
  {
    // Read as an event stream by the panel.
    method: 'POST', path: `${VIRTUAL}/run-all`,
    handle: ({ body }) => {
      const only: string[] | undefined = asObj(body).entities;
      const items = ENTITIES.filter(e => !only?.length || only.includes(e.name)).map(e => virtualEntityDiag(e.name));
      return sse([...items.map(data => ({ type: 'entity', data })), { type: 'summary', data: scanSummary(items) }]);
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/diagnostics\/virtual-entities\/([^/]+)\/run$/,
    handle: ({ match }) => virtualEntityDiag(decodeURIComponent(match[1])),
  },

  // Dashboard diagnostics
  {
    method: 'GET', path: '/api/v1/diagnostics/dashboards',
    handle: () => DASHBOARDS.map(d => ({ uid: d.uid, title: d.title, description: d.description, tags: d.tags, panelCount: d.panels.length, updatedAt: d.updatedAt })),
  },
  {
    // Read as an event stream by the panel.
    method: 'POST', path: '/api/v1/diagnostics/dashboards/run-all',
    handle: ({ body }) => {
      const only: string[] | undefined = asObj(body).dashboardUids;
      const items = DASHBOARDS.filter(d => !only?.length || only.includes(d.uid)).map(d => dashboardDiag(d.uid));
      return sse([...items.map(data => ({ type: 'dashboard', data })), { type: 'summary', data: scanSummary(items) }]);
    },
  },
  { method: 'POST', path: /^\/api\/v1\/diagnostics\/dashboards\/([^/]+)\/run$/, handle: ({ match }) => dashboardDiag(decodeURIComponent(match[1])) },
  { method: 'GET', path: '/api/v1/diagnostics/backends', handle: () => backends() },
  {
    method: 'GET', path: /^\/api\/v1\/diagnostics\/entities\/([^/]+)$/,
    handle: ({ match, query }) => {
      const name = decodeURIComponent(match[1]);
      const d = virtualEntityDiag(name);
      const e = entityByName(name);
      return {
        entity: name, status: d.overall === 'healthy' ? 'pass' : d.overall === 'degraded' ? 'warn' : 'fail',
        code: d.overall === 'unhealthy' ? (d.ruleId ? 'inactive_rule' : 'no_mapping_rule') : d.rowCount === 0 ? 'no_rows' : 'ok',
        ruleId: d.ruleId, sourceType: d.sourceType, sourceTable: d.sourceTable, rowCount: d.rowCount,
        sampleRows: e && d.rowCount ? entityRows(e, Math.min(Number(query.get('limit')) || 5, 10)) : [],
        errorMessage: d.overall === 'unhealthy' ? d.checks.find(ch => ch.status === 'fail')?.message : null,
        latencyMs: d.latencyMs, scannedAt: d.scannedAt,
      };
    },
  },

  // Automation diagnostics
  { method: 'GET', path: '/api/v1/diagnostics/automation', handle: () => automationDryRun() },
  { method: 'POST', path: '/api/v1/diagnostics/automation/dry-run', handle: () => automationDryRun() },
  { method: 'GET', path: '/api/v1/diagnostics/automation/tool-catalogue', handle: () => toolCatalogue() },
  { method: 'GET', path: '/api/v1/diagnostics/automation/saved-journeys', handle: () => savedJourneysReport() },
  { method: 'GET', path: '/api/v1/diagnostics/automation/copilot-runtime', handle: () => copilotRuntime() },
  { method: 'GET', path: '/api/v1/diagnostics/automation/graph-integrity', handle: () => graphIntegrity() },
  { method: 'POST', path: '/api/v1/diagnostics/automation/smoke-test', handle: ({ body }) => smokeTest(asObj(body).goal) },

  // Diagnostics audit (history)
  { method: 'GET', path: '/api/v1/diagnostics/history/scopes', handle: () => ({ scopes: HISTORY_SCOPES }) },
  {
    method: 'GET', path: '/api/v1/diagnostics/history',
    handle: ({ query }) => {
      const scope = query.get('scope') || 'o2c';
      const items = historyRuns(scope, Number(query.get('limit')) || 50);
      return { scope, total: items.length, items };
    },
  },
  {
    method: 'GET', path: /^\/api\/v1\/diagnostics\/history\/([^/]+)\/([^/]+)$/,
    handle: ({ match }) => historyRun(decodeURIComponent(match[1]), decodeURIComponent(match[2])),
  },

  // AI health
  { method: 'GET', path: '/api/v1/ai-health/latest', handle: () => healthSnapshot(6, 0) },
  {
    method: 'GET', path: '/api/v1/ai-health/timeseries',
    handle: ({ query }) => {
      const limit = Math.min(Number(query.get('limit')) || 96, 96);
      // Newest first, one snapshot every 15 minutes.
      const items = Array.from({ length: limit }, (_, k) => healthSnapshot(6 + k * 15, k));
      return { scope: query.get('scope') || 'all', total: items.length, items };
    },
  },
  { method: 'POST', path: '/api/v1/ai-health/run', handle: () => healthSnapshot(0, 0) },

  // Test reports
  {
    method: 'GET', path: '/api/v1/tests/status',
    handle: () => ({
      status: 'completed', conclusion: 'success',
      latest_run: workflowRun(0, 'completed', 'success'),
      recent_runs: [workflowRun(0, 'completed', 'success'), workflowRun(1, 'completed', 'failure'), workflowRun(2, 'completed', 'success'), workflowRun(3, 'completed', 'success'), workflowRun(4, 'completed', 'cancelled'), workflowRun(5, 'completed', 'success')],
    }),
  },
  {
    method: 'GET', path: '/api/v1/tests/results',
    handle: () => ({
      dashboard_url: 'https://reports.kinetiq-beverages.example/tests/index.html',
      categories: {
        unit: { available: true, timestamp: ago(77).slice(0, 16).replace('T', ' '), report_url: 'https://reports.kinetiq-beverages.example/tests/unit/index.html' },
        integration: { available: true, timestamp: ago(77).slice(0, 16).replace('T', ' '), report_url: 'https://reports.kinetiq-beverages.example/tests/integration/index.html' },
        bdd: { available: true, timestamp: ago(77 + DAY * 3).slice(0, 16).replace('T', ' '), report_url: 'https://reports.kinetiq-beverages.example/tests/bdd/index.html' },
        endurance: { available: false },
      },
    }),
  },
  { method: 'POST', path: '/api/v1/tests/run', handle: ({ body }) => ({ status: 'queued', test_types: asObj(body).test_types || [], run_id: 9184452001 }) },
];
