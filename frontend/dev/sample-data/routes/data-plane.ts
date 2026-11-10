/**
 * Data Plane: sources, FDW explorer, virtual entities, mapping rules,
 * connector API registry and workbench, virtual data API registry.
 * (Data pipelines are journeys; see automation.ts.)
 */
import {
  type SampleRoute, type EntityDef, type ConnectorApiDef,
  SYSTEMS, ENTITIES, MAPPING_RULES, CONNECTOR_APIS, TOOLS, PEOPLE,
  ago, asObj, between, pad, pick, emailOf, entityByName, entityRows, schemaEntity, systemOf, ruleForEntity,
  schemaOf, callersOf, HOUR, DAY,
} from '../fixtures';
import { runQuery, previewEntity } from '../rows';

// ---------------------------------------------------------------------------
// Data sources
// ---------------------------------------------------------------------------

/** Sources registered by users, shown above the six built-in ones. */
const DATA_PLANES = [
  { id: 'dp-oracle-ar-cdc', name: 'Oracle AR change feed', type: 'CDC', status: 'error', connectionConfig: { host: 'ora-erp-prod.kinetiq.internal', port: 1521, service: 'ERPPRD', tables: ['AR_Invoice', 'AR_Payment'], lastError: 'LogMiner session expired (ORA-01291)' }, createdAt: ago(DAY * 19), updatedAt: ago(HOUR * 3) },
  { id: 'dp-sap-bw-extract', name: 'SAP BW weekly extract', type: 'ETL', status: 'pending', connectionConfig: { host: 'sap-bw.kinetiq.internal', client: '100', schedule: '0 2 * * 1' }, createdAt: ago(DAY * 2), updatedAt: ago(DAY * 2) },
];
const BUILT_IN_SOURCES: Record<string, { name: string; type: string }> = {
  'sample-crm': { name: 'Salesforce CRM', type: 'FDW' },
  'sample-erp': { name: 'Oracle ERP', type: 'FDW' },
  'sample-sap': { name: 'SAP S/4HANA', type: 'FDW' },
  'sample-drive': { name: 'Google Drive', type: 'FDW' },
  'sample-files': { name: 'File Uploads', type: 'ETL' },
  'sample-social': { name: 'Social Listening', type: 'ETL' },
};
const planeById = (id: string) =>
  DATA_PLANES.find(p => p.id === id)
  || (BUILT_IN_SOURCES[id] && { id, ...BUILT_IN_SOURCES[id], status: 'connected', connectionConfig: {}, createdAt: ago(DAY * 40), updatedAt: ago(HOUR * 6) })
  || { id, name: 'Data source', type: 'FDW', status: 'connected', connectionConfig: {}, createdAt: ago(DAY * 5), updatedAt: ago(HOUR * 2) };

const dataSourceModes = () => {
  const modes = Object.fromEntries(SYSTEMS.map(s => [s.modeKey, s.mode]));
  return {
    modes,
    default: 'simulator',
    available_sources: SYSTEMS.map(s => s.modeKey),
    summary: {
      simulator: SYSTEMS.filter(s => s.mode === 'simulator').length,
      real: SYSTEMS.filter(s => s.mode === 'real').length,
    },
  };
};

// ---------------------------------------------------------------------------
// FDW (foreign tables)
// ---------------------------------------------------------------------------

/** Entities reachable for a `source` value. No source (or `real`) means the whole catalogue. */
const entitiesForSource = (source: string | null): EntityDef[] => {
  if (!source || source === 'real') return ENTITIES;
  return ENTITIES.filter(e => systemOf(e).fdwSource === source);
};
const tableInfo = (e: EntityDef) => ({
  schemaName: systemOf(e).schema,
  tableName: e.name,
  serverName: systemOf(e).server,
  columnCount: e.cols.length,
});
const columnsOf = (e: EntityDef) => e.cols.map((col, i) => ({
  columnName: col.name,
  dataType: col.dataType,
  isNullable: i !== 0,
  ordinalPosition: i + 1,
}));

function fdwQuery(body: Record<string, any>) {
  const e = entityByName(body.table);
  const limit = Math.min(Number(body.limit) || 50, 200);
  const offset = Number(body.offset) || 0;
  if (!e) return { rows: [], metadata: { durationMs: 12, tableQueried: `${body.schemaName || 'public'}.${body.table}`, rowCount: 0 } };
  // Pages of generated rows; the visible total is capped so paging ends.
  const available = Math.min(e.cols.length > 0 ? Math.max(e.totalRows, 18) : 0, 60);
  let rows = entityRows(e, Math.max(0, Math.min(limit, available - offset)), offset);
  const filters: any[] = Array.isArray(body.filters) ? body.filters : [];
  for (const f of filters) {
    rows = rows.filter(r => {
      const v = r[f.column];
      if (v === undefined) return true;
      if (f.operator === 'like') return String(v).toLowerCase().includes(String(f.value).replace(/%/g, '').toLowerCase());
      if (f.operator === 'neq') return String(v) !== String(f.value);
      if (f.operator === 'in') return Array.isArray(f.value) ? f.value.map(String).includes(String(v)) : true;
      const a = Number(v), b = Number(f.value);
      if (f.operator === 'gt') return a > b;
      if (f.operator === 'gte') return a >= b;
      if (f.operator === 'lt') return a < b;
      if (f.operator === 'lte') return a <= b;
      return String(v) === String(f.value);
    });
  }
  const order = Array.isArray(body.orderBy) ? body.orderBy[0] : null;
  if (order?.column) {
    rows = [...rows].sort((x, y) => {
      const a = x[order.column], b = y[order.column];
      const cmp = typeof a === 'number' && typeof b === 'number' ? a - b : String(a ?? '').localeCompare(String(b ?? ''));
      return order.direction === 'desc' ? -cmp : cmp;
    });
  }
  if (Array.isArray(body.columns) && body.columns.length) {
    rows = rows.map(r => Object.fromEntries(body.columns.filter((col: string) => col in r).map((col: string) => [col, r[col]])));
  }
  return {
    rows,
    metadata: { durationMs: between(`fdw-${e.name}`, 18, 140), tableQueried: `${systemOf(e).schema}.${e.name}`, rowCount: rows.length },
  };
}

// ---------------------------------------------------------------------------
// Entity graph
// ---------------------------------------------------------------------------

function entityGraph() {
  const names = new Set(ENTITIES.map(e => e.name));
  const edges = ENTITIES.flatMap(e =>
    e.relationships
      .filter(r => names.has(r.targetEntity)) // only edges between entities, so the layout never meets a missing node
      .map((r, i) => ({
        id: `${e.name}-${r.type}-${r.targetEntity}-${i}`,
        source: e.name,
        target: r.targetEntity,
        type: r.type,
        category: r.targetCategory,
        description: r.description,
        targetExists: true,
      })));
  const degree = (name: string) => edges.filter(ed => ed.source === name || ed.target === name).length;
  const nodes = ENTITIES.map(e => ({
    id: e.name,
    label: e.name,
    system: systemOf(e).system,
    domain: e.domain,
    riskLevel: e.riskLevel,
    fieldCount: e.cols.length,
    isVirtual: e.fdwMappingStatus === 'virtual',
    fdwMappingStatus: e.fdwMappingStatus,
    degree: degree(e.name),
  }));
  return {
    nodes,
    edges,
    stats: {
      nodeCount: nodes.length,
      edgeCount: edges.length,
      systems: [...new Set(nodes.map(n => n.system))],
      relationshipTypes: [...new Set(edges.map(ed => ed.type))],
    },
  };
}

// ---------------------------------------------------------------------------
// Virtual data layer
// ---------------------------------------------------------------------------

const virtualEntitySummaries = () => ENTITIES.map(e => {
  const rule = ruleForEntity(e.name);
  return {
    virtual_entity: e.name,
    source_count: rule ? 1 : 0,
    active_rules: rule && rule.status === 'active' ? 1 : 0,
    sources: rule ? [{ source_system: rule.sourceSystem, source_table: `${rule.sourceSchema}.${rule.sourceTable}`, source_type: rule.sourceType, status: rule.status }] : [],
  };
});

function virtualResponse(entity: string, rows: Record<string, unknown>[]) {
  const e = entityByName(entity);
  const rule = ruleForEntity(entity);
  return {
    rows,
    total: rows.length,
    virtualEntity: entity,
    metadata: {
      sourceTable: e ? `${systemOf(e).schema}.${e.name}` : `results.${entity.toLowerCase()}`,
      durationMs: between(`vq-${entity}`, 22, 180),
      rowCount: rows.length,
      mappingRuleId: rule?.id,
      sourceType: rule?.sourceType || 'S3',
      source_type: rule?.sourceType || 'S3',
    },
  };
}

// ---------------------------------------------------------------------------
// Mapping rules
// ---------------------------------------------------------------------------

function mappingAudit() {
  const entities = ENTITIES.map(e => {
    const rule = ruleForEntity(e.name);
    const mappedOk = !!rule && rule.status === 'active';
    const issues: string[] = [];
    if (!rule) issues.push('No mapping rule. Run Auto-map or create one.');
    else if (rule.status === 'draft') issues.push('Rule is a draft and is not used by queries.');
    else if (rule.status === 'inactive') issues.push('Rule is inactive.');
    if (rule && e.totalRows === 0) issues.push('Source table returned no rows.');
    const unmappedFields = mappedOk ? (e.name === 'AR_Invoice' ? 2 : e.name === 'Inventory_Position' ? 1 : 0) : e.cols.length;
    if (mappedOk && unmappedFields) issues.push(`${unmappedFields} schema field(s) have no source column.`);
    return {
      entity: e.name,
      system: systemOf(e).system,
      domain: e.domain,
      schemaFields: e.cols.length + (mappedOk ? unmappedFields : 0),
      mappingStatus: (rule ? (rule.status === 'active' ? 'mapped' : 'error') : 'unmapped') as 'mapped' | 'unmapped' | 'error',
      ruleName: rule?.name,
      ruleId: rule?.id,
      sourceSchema: rule?.sourceSchema,
      sourceTable: rule?.sourceTable,
      sourceType: rule?.sourceType,
      mappedFields: rule ? e.cols.length : 0,
      unmappedFields,
      rowCount: rule ? e.totalRows : 0,
      dataStatus: (!rule ? 'no_source' : e.totalRows > 0 ? 'has_data' : 'no_data') as 'has_data' | 'no_data' | 'no_source',
      issues,
    };
  });
  const summaryBySystem: Record<string, { mapped: number; unmapped: number; rows: number }> = {};
  for (const row of entities) {
    const s = (summaryBySystem[row.system] ||= { mapped: 0, unmapped: 0, rows: 0 });
    if (row.mappingStatus === 'mapped') s.mapped++; else s.unmapped++;
    s.rows += row.rowCount;
  }
  return {
    totalEntities: entities.length,
    mapped: entities.filter(r => r.mappingStatus === 'mapped').length,
    unmapped: entities.filter(r => r.mappingStatus !== 'mapped').length,
    withData: entities.filter(r => r.dataStatus === 'has_data').length,
    withoutData: entities.filter(r => r.dataStatus !== 'has_data').length,
    entities,
    summaryBySystem,
  };
}

function suggestMappings(body: Record<string, any>) {
  const e = entityByName(body.virtualEntity) || entityByName(body.sourceTable);
  if (!e) return { suggestions: [] };
  const rule = ruleForEntity(e.name);
  return {
    suggestions: e.cols.map((col, i) => ({
      sourceField: col.name,
      targetField: rule?.fieldMaps[i]?.targetField || col.name,
      confidence: pick(['high', 'high', 'high', 'medium', 'high', 'low'], i),
    })),
  };
}

// ---------------------------------------------------------------------------
// Connector APIs
// ---------------------------------------------------------------------------

const specOf = (a: ConnectorApiDef) => ({
  api_id: a.api_id,
  target_system: a.target_system,
  operation: a.operation,
  description: a.description,
  request_schema: schemaOf(a.request),
  response_schema: schemaOf(a.response),
  simulator_writeback: a.simulator_writeback,
  risk_level: a.risk_level,
  tags: a.tags,
});

/** Invocation history per API: a few are never called, one writes without an audit row. */
const auditCount = (a: ConnectorApiDef, i: number) =>
  a.api_id === 'sap.production_order.list' || a.api_id === 'external.gdrive.contract.get' ? 0 : between(`audit-${a.api_id}`, 3, 240) + i;

const enriched = (a: ConnectorApiDef, i: number) => {
  const callers = callersOf(a.api_id);
  const count = auditCount(a, i);
  return {
    ...specOf(a),
    tool_callers: callers,
    tool_caller_count: callers.length,
    audit_count: count,
    last_invocation_ts: count ? ago(14 + i * 53) : null,
    verified: count > 0 && a.api_id !== 'sap.purchase_order.block',
    has_verification_hint: a.simulator_writeback,
  };
};
const enrichedList = (target?: string | null) =>
  CONNECTOR_APIS.map(enriched).filter(a => !target || a.target_system === target);

const countBy = <T,>(items: T[], key: (item: T) => string) =>
  items.reduce<Record<string, number>>((acc, item) => { acc[key(item)] = (acc[key(item)] || 0) + 1; return acc; }, {});

const listTotals = (items: ReturnType<typeof enrichedList>) => ({
  checked: items.length,
  orphans: items.filter(a => a.tool_caller_count === 0).length,
  verified: items.filter(a => a.verified).length,
  never_invoked: items.filter(a => a.audit_count === 0).length,
  by_target_system: countBy(items, a => a.target_system),
  by_risk_level: countBy(items, a => a.risk_level),
});

const auditEvents = (apiId: string, limit = 8) => {
  const a = CONNECTOR_APIS.find(x => x.api_id === apiId);
  const i = CONNECTOR_APIS.findIndex(x => x.api_id === apiId);
  if (!a || auditCount(a, i) === 0) return [];
  return Array.from({ length: Math.min(limit, 8) }, (_, k) => ({
    event_id: `evt-${pad(48210 - i * 37 - k, 6)}`,
    actor: pick([emailOf(PEOPLE[1]), 'journey:jr-o2c-01', emailOf(PEOPLE[4]), 'copilot', 'journey:jr-prc-01'], k + i),
    verb: a.operation.split(' ')[0],
    target: a.operation.split(' ')[1],
    payload: canaryPayload(a),
    api_id: a.api_id,
    event_ts: ago(14 + i * 53 + k * 410),
  }));
};

function canaryPayload(a: ConnectorApiDef): Record<string, unknown> {
  const sample: Record<string, unknown> = {
    account_id: 'ACC-1004', Credit_Limit__c: 750000, stage: 'Negotiation', status: 'Open', customer_id: 40004,
    invoice_id: 'INV-88127', level: 2, credit_hold: true, reason: 'Open balance above credit limit', match_status: 'Price variance',
    plant: 'PL02', material_id: 'FG-1003', vendor_id: 'V-1001', po_number: '4500001214', from_plant: 'PL01', to_plant: 'PL02',
    quantity: 9000, category: 'Packaging', contract_id: 'CTR-2026-041',
  };
  return Object.fromEntries(Object.keys(a.request).map(k => [k, sample[k] ?? 'sample']));
}

function invokeResult(apiId: string, payload: Record<string, unknown>) {
  const a = CONNECTOR_APIS.find(x => x.api_id === apiId) || CONNECTOR_APIS[0];
  const i = CONNECTOR_APIS.indexOf(a);
  const [method, path] = a.operation.split(' ');
  const write = a.risk_level !== 'read_only';
  const auditMissing = a.api_id === 'sap.purchase_order.block';
  const e = entityByName(a.api_id.includes('invoice') ? 'AR_Invoice' : a.api_id.includes('account') ? 'Account' : a.api_id.includes('purchase') ? 'Purchase_Order' : a.api_id.includes('inventory') ? 'Inventory_Position' : 'Vendor_Master')!;
  const before = entityRows(e, 1, 3)[0];
  const after = write ? { ...before, [e.cols[e.cols.length - 1].name]: write ? 'Updated by canary' : before[e.cols[e.cols.length - 1].name] } : before;
  const event = { event_id: `evt-${pad(48300 + i, 6)}`, actor: 'workbench', verb: method, target: path, payload, api_id: a.api_id, event_ts: ago(0) };
  return {
    api_id: a.api_id,
    operation: a.operation,
    request: { method, path, body: payload, full_payload: payload },
    http_status: 200,
    response: write ? { success: true, id: Object.values(before)[0] } : { items: entityRows(e, 3), count: 3 },
    http_error: null,
    verification: {
      before: write ? before : null,
      after: write ? after : null,
      row_diff: write ? [e.cols[e.cols.length - 1].name] : [],
      row_count_before: e.totalRows,
      row_count_after: e.totalRows,
      audit_event: auditMissing ? null : event,
      audit_appeared: !auditMissing,
      table: write ? e.name : null,
      schema: write ? systemOf(e).schema : null,
      mode: write ? (method === 'POST' ? 'post' : 'patch') : null,
    },
    duration_ms: between(`inv-${a.api_id}`, 80, 620),
    verdict: !write ? 'no_change' : auditMissing ? 'audit_missing' : 'verified',
    marker: `canary-${Date.now().toString(36)}`,
  };
}

function connectorDiagnostic() {
  const items = enrichedList();
  const totals = listTotals(items);
  const writes = items.filter(a => a.risk_level !== 'read_only');
  const boundTools = TOOLS.filter(t => t.connectorApi);
  const orphanApis = items.filter(a => a.tool_caller_count === 0).map(a => a.api_id);
  const issues: Record<string, { severity: 'error' | 'warning'; code: string; message: string }[]> = {
    'sap.purchase_order.block': [{ severity: 'error', code: 'audit_missing', message: 'High-risk write does not record an audit event in the simulator.' }],
    'sfdc.opportunity.list': [{ severity: 'warning', code: 'no_tool_caller', message: 'No ReAct tool calls this API.' }],
    'external.gdrive.contract.get': [{ severity: 'warning', code: 'response_schema_thin', message: 'Response schema declares 2 of 11 fields.' }],
  };
  return {
    summary: {
      checked: totals.checked, verified: totals.verified, never_invoked: totals.never_invoked, orphans: totals.orphans,
      with_hint: writes.length, without_hint: items.length - writes.length,
      audit_events_24h: 184, by_target_system: totals.by_target_system, by_risk_level: totals.by_risk_level, overall: 'degraded',
    },
    catalogue_health: {
      totals: { checked: items.length, errors: 1, warnings: 2, specs_with_issues: 3 },
      issues_by_api: issues,
      overall: 'degraded',
    },
    tool_mapping: {
      totals: { tools: TOOLS.length, tools_with_binding: boundTools.length, orphan_tools: 2, dangling_tools: 0, orphan_apis: orphanApis.length },
      by_api: Object.fromEntries(items.map(a => [a.api_id, a.tool_callers])),
      by_tool: TOOLS.map(t => ({
        tool_id: t.name,
        risk_level: t.risk,
        connector_api: t.connectorApi || null,
        binding_status: t.connectorApi ? 'ok' : t.risk === 'read_only' ? 'read_only' : 'orphan',
      })),
      orphan_apis: orphanApis,
      orphan_tools: TOOLS.filter(t => !t.connectorApi && t.risk !== 'read_only').map(t => ({ tool_id: t.name, risk_level: t.risk })),
      dangling_tools: [],
      overall: orphanApis.length ? 'degraded' : 'healthy',
    },
    verification_hints: {
      totals: { checked: items.length, with_hint: writes.length, without_hint: items.length - writes.length },
      rows: items.map(a => {
        const e = a.api_id.includes('account') ? 'Account' : a.api_id.includes('customer') ? 'AR_Customer' : a.api_id.includes('invoice') ? 'AR_Invoice' : a.api_id.includes('purchase') ? 'Purchase_Order' : 'Inventory_Position';
        const ent = entityByName(e)!;
        const hinted = a.risk_level !== 'read_only';
        return {
          api_id: a.api_id,
          has_hint: hinted,
          mode: hinted ? (a.operation.startsWith('POST') ? 'post' : 'patch') : null,
          schema: hinted ? systemOf(ent).schema : null,
          table: hinted ? ent.name : null,
          pk_col: hinted ? ent.cols[0].name : null,
          pk_arg: hinted ? Object.keys(CONNECTOR_APIS.find(x => x.api_id === a.api_id)!.request)[0] : null,
          has_companion: hinted && a.api_id !== 'sap.stock_transfer.create',
        };
      }),
      non_verifiable_api_ids: items.filter(a => a.risk_level === 'read_only').map(a => a.api_id),
      overall: 'healthy',
    },
    audit_discipline: {
      totals: {
        checked: items.length,
        ok: items.filter(a => a.audit_count > 0 && a.api_id !== 'sap.purchase_order.block').length,
        never_called: items.filter(a => a.audit_count === 0).length,
        audit_missing: 1,
      },
      rows: items.map(a => ({
        api_id: a.api_id,
        target_system: a.target_system,
        risk_level: a.risk_level,
        simulator_writeback: a.simulator_writeback,
        total_events: a.audit_count,
        events_24h: Math.round(a.audit_count / 9),
        last_event_ts: a.last_invocation_ts,
        smell: a.audit_count === 0 ? 'never_called' : a.api_id === 'sap.purchase_order.block' ? 'audit_missing' : 'ok',
      })),
      overall: 'degraded',
    },
    simulator_coverage: {
      totals: { tables: 9, blocking: 1 },
      rows: ENTITIES.filter(e => ['sfdc', 'sap', 'oracle'].includes(e.systemKey)).slice(0, 9).map(e => ({
        sim_key: systemOf(e).fdwSource === 'simulator' ? 'sfdc' : systemOf(e).fdwSource,
        schema: systemOf(e).schema,
        table: e.name,
        row_count: e.totalRows,
        used_by_apis: CONNECTOR_APIS.filter(a => a.api_id.toLowerCase().includes(e.name.toLowerCase().replace(/_master$/, '').split('_').pop()!)).map(a => a.api_id),
        blocking: e.totalRows === 0,
      })),
      overall: 'degraded',
    },
  };
}

function smokeReport() {
  const results = CONNECTOR_APIS.map(a => {
    const r = invokeResult(a.api_id, canaryPayload(a));
    const failing = a.api_id === 'oracle.ap_invoice.list';
    return {
      api_id: a.api_id,
      verdict: failing ? 'http_error' : r.verdict,
      http_status: failing ? 504 : 200,
      http_error: failing ? 'Gateway timeout after 30s' : null,
      duration_ms: failing ? 30012 : r.duration_ms,
      verification: r.verification,
      request: r.request,
      response: failing ? null : r.response,
    };
  });
  const n = (v: string) => results.filter(r => r.verdict === v).length;
  return {
    totals: { checked: results.length, verified: n('verified'), no_change: n('no_change'), audit_missing: n('audit_missing'), http_error: n('http_error'), duration_ms: results.reduce((s, r) => s + (r.duration_ms || 0), 0) },
    results,
    overall: 'degraded',
  };
}

// ---------------------------------------------------------------------------
// Virtual data APIs
// ---------------------------------------------------------------------------

const VDL_APIS = [
  { api_id: 'vdl.account.read', verb: 'read', virtual_entity: 'Account', impl: ['sfdc.account.get'], risk_level: 'read_only', description: 'Read customer accounts with credit fields.', tags: ['customer'] },
  { api_id: 'vdl.account.update_credit_limit', verb: 'write', virtual_entity: 'Account', impl: ['sfdc.account.update_credit_limit', 'oracle.ar_customer.set_hold'], risk_level: 'high_risk_write', description: 'Change a credit limit in Salesforce and keep Oracle receivables in step.', tags: ['customer', 'credit'] },
  { api_id: 'vdl.opportunity.read', verb: 'read', virtual_entity: 'Opportunity', impl: ['sfdc.opportunity.list'], risk_level: 'read_only', description: 'Read orders and pipeline deals.', tags: ['sales'] },
  { api_id: 'vdl.ar_invoice.read', verb: 'read', virtual_entity: 'AR_Invoice', impl: ['oracle.ar_invoice.list'], risk_level: 'read_only', description: 'Read customer invoices.', tags: ['finance'] },
  { api_id: 'vdl.ar_invoice.aging', verb: 'aggregate', virtual_entity: 'AR_Invoice', impl: [], risk_level: 'read_only', description: 'Open receivables by ageing bucket.', tags: ['finance', 'analytics'] },
  { api_id: 'vdl.ar_invoice.add_dunning', verb: 'upsert', virtual_entity: 'AR_Invoice', impl: ['oracle.ar_invoice.add_dunning'], risk_level: 'low_risk_write', description: 'Record a collection notice against an invoice.', tags: ['finance', 'collections'] },
  { api_id: 'vdl.inventory_position.read', verb: 'read', virtual_entity: 'Inventory_Position', impl: ['sap.inventory.list'], risk_level: 'read_only', description: 'Read stock by material and plant.', tags: ['inventory'] },
  { api_id: 'vdl.inventory_position.transfer', verb: 'write', virtual_entity: 'Inventory_Position', impl: ['sap.stock_transfer.create'], risk_level: 'low_risk_write', description: 'Create a stock transfer between plants.', tags: ['inventory'] },
  { api_id: 'vdl.purchase_order.read', verb: 'read', virtual_entity: 'Purchase_Order', impl: ['sap.purchase_order.list'], risk_level: 'read_only', description: 'Read purchase orders.', tags: ['procurement'] },
  { api_id: 'vdl.purchase_order.block', verb: 'write', virtual_entity: 'Purchase_Order', impl: ['sap.purchase_order.block'], risk_level: 'high_risk_write', description: 'Block a purchase order pending review.', tags: ['procurement'] },
  { api_id: 'vdl.vendor_master.read', verb: 'read', virtual_entity: 'Vendor_Master', impl: ['sap.vendor.list'], risk_level: 'read_only', description: 'Read suppliers with scores.', tags: ['procurement', 'risk'] },
  { api_id: 'vdl.production_order.read', verb: 'read', virtual_entity: 'Production_Order', impl: ['sap.production_order.list'], risk_level: 'read_only', description: 'Read production orders.', tags: ['manufacturing'] },
  { api_id: 'vdl.contract_document.read', verb: 'read', virtual_entity: 'Contract_Document', impl: ['external.gdrive.contract.get'], risk_level: 'read_only', description: 'Read extracted supplier contracts.', tags: ['contracts'] },
  { api_id: 'vdl.market_signal.read', verb: 'read', virtual_entity: 'Market_Signal', impl: [], risk_level: 'read_only', description: 'Read external disruption signals.', tags: ['risk', 'external'] },
].map(a => {
  const e = entityByName(a.virtual_entity)!;
  return {
    api_id: a.api_id,
    verb: a.verb,
    virtual_entity: a.virtual_entity,
    parameters_schema: {
      type: 'object',
      properties: Object.fromEntries(e.cols.slice(0, a.verb === 'read' || a.verb === 'aggregate' ? 3 : 4).map(col => [col.name, { type: /int|num|dec/.test(col.dataType) ? 'number' : 'string', description: col.semantic }])),
      required: a.verb === 'read' || a.verb === 'aggregate' ? [] : [e.cols[0].name],
    },
    impl: a.impl.map(id => ({ connector_api_id: id, arg_mapping: { [e.cols[0].name]: Object.keys(CONNECTOR_APIS.find(x => x.api_id === id)!.request)[0] } })),
    direct_sql: a.impl.length === 0 ? { virtual_entity: a.virtual_entity, projection: e.cols.slice(0, 5).map(col => col.name), limit: 100 } : null,
    risk_level: a.risk_level,
    description: a.description,
    tags: a.tags,
  };
});

function vdlInvoke(apiId: string, args: Record<string, unknown>) {
  const spec = VDL_APIS.find(a => a.api_id === apiId) || VDL_APIS[0];
  const e = entityByName(spec.virtual_entity)!;
  const steps = spec.impl.map(b => ({ connector_api_id: b.connector_api_id, args }));
  const read = spec.verb === 'read' || spec.verb === 'aggregate';
  return {
    api_id: spec.api_id,
    ok: true,
    plan: { api_id: spec.api_id, verb: spec.verb, virtual_entity: spec.virtual_entity, steps, direct_sql: spec.direct_sql },
    step_results: steps.length
      ? steps.map((s, i) => ({ connector_api_id: s.connector_api_id, http_status: 200, duration_ms: between(`vdl-${apiId}-${i}`, 60, 400), ...(read ? { rows: entityRows(e, 3) } : { success: true, audit_event_id: `evt-${pad(48400 + i, 6)}` }) }))
      : [{ source: 'direct_sql', rows: entityRows(e, 5), row_count: 5 }],
    duration_ms: between(`vdl-${apiId}`, 90, 700),
    error: null,
  };
}

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

export const dataPlaneRoutes: SampleRoute[] = [
  // Sources
  { method: 'GET', path: '/api/data-planes', handle: () => DATA_PLANES },
  {
    method: 'GET', path: /^\/api\/data-planes\/([^/]+)\/explore$/,
    handle: ({ match }) => ({ id: decodeURIComponent(match[1]), tables: ENTITIES.slice(0, 8).map(tableInfo) }),
  },
  { method: 'GET', path: /^\/api\/data-planes\/([^/]+)$/, handle: ({ match }) => planeById(decodeURIComponent(match[1])) },
  {
    method: 'POST', path: '/api/data-planes',
    handle: ({ body }) => ({ id: `dp-${Date.now().toString(36)}`, status: 'pending', connectionConfig: {}, ...asObj(body), createdAt: ago(0), updatedAt: ago(0) }),
  },
  {
    method: 'PUT', path: /^\/api\/data-planes\/([^/]+)$/,
    handle: ({ match, body }) => ({ ...planeById(decodeURIComponent(match[1])), ...asObj(body), updatedAt: ago(0) }),
  },
  { method: 'GET', path: '/api/v1/data-source-mode', handle: () => dataSourceModes() },
  {
    method: 'PUT', path: /^\/api\/v1\/data-source-mode\/([^/]+)$/,
    handle: ({ match, body }) => {
      const source = decodeURIComponent(match[1]);
      const mode = asObj(body).mode || 'simulator';
      const previous = SYSTEMS.find(s => s.modeKey === source)?.mode || 'simulator';
      return { source, mode, previous_mode: previous };
    },
  },

  // FDW explorer
  {
    method: 'GET', path: '/api/v1/health/fdw',
    handle: () => ({ status: 'healthy', latencyMs: 41, foreignServersCount: new Set(SYSTEMS.map(s => s.server)).size, foreignTablesCount: ENTITIES.length }),
  },
  {
    method: 'GET', path: '/api/fdw/servers',
    handle: ({ query }) => {
      const systems = SYSTEMS.filter(s => entitiesForSource(query.get('source')).some(e => e.systemKey === s.key));
      const seen = new Set<string>();
      return systems.filter(s => !seen.has(s.server) && seen.add(s.server)).map(s => ({
        serverName: s.server,
        wrapperType: s.wrapper,
        serverOptions: s.fdwSource === 'external'
          ? { bucket: 's3://kinetiq-nexus-extracted', format: 'parquet' }
          : { host: `${s.key}-gateway.kinetiq.internal`, port: s.key === 'oracle' ? '1521' : s.key === 'sap' ? '30015' : '443', schema: s.schema, fetch_size: '1000' },
      }));
    },
  },
  {
    method: 'GET', path: /^\/api\/fdw\/tables\/([^/]+)\/([^/]+)\/columns$/,
    handle: ({ match }) => {
      const e = entityByName(decodeURIComponent(match[2]));
      return e ? columnsOf(e) : [];
    },
  },
  {
    method: 'GET', path: '/api/fdw/tables',
    handle: ({ query }) => {
      const server = query.get('server');
      return entitiesForSource(query.get('source')).map(tableInfo).filter(t => !server || t.serverName === server);
    },
  },
  { method: 'POST', path: '/api/fdw/query', handle: ({ body }) => fdwQuery(asObj(body)) },

  // Entities and knowledge graph
  { method: 'GET', path: '/api/v1/control-plane/entities/graph', handle: () => entityGraph() },
  { method: 'GET', path: '/api/v1/control-plane/entities', handle: () => ENTITIES.map(schemaEntity) },
  {
    method: 'GET', path: /^\/api\/v1\/control-plane\/entities\/([^/]+)$/,
    handle: ({ match }) => {
      const e = entityByName(decodeURIComponent(match[1]));
      return e ? schemaEntity(e) : { name: decodeURIComponent(match[1]), fields: [], relationships: [] };
    },
  },

  // Virtual data layer
  { method: 'GET', path: '/api/v1/control-plane/virtual/entities', handle: () => virtualEntitySummaries() },
  {
    method: 'GET', path: /^\/api\/v1\/control-plane\/virtual\/entities\/([^/]+)\/preview$/,
    handle: ({ match, query }) => {
      const entity = decodeURIComponent(match[1]);
      return virtualResponse(entity, previewEntity(entity, Number(query.get('limit')) || 10).rows);
    },
  },
  {
    method: 'POST', path: '/api/v1/control-plane/virtual/query',
    handle: ({ body }) => {
      const b = asObj(body);
      const entity = String(b.virtualEntity || b.entity || '');
      const e = entityByName(entity);
      const rule = e && ruleForEntity(e.name);
      // Field names may be the mapped (target) names; translate them back to source columns.
      const fields: string[] | undefined = Array.isArray(b.fields)
        ? b.fields.map((f: string) => rule?.fieldMaps.find(m => m.targetField === f)?.sourceField || f)
        : undefined;
      const { rows } = e && e.fdwMappingStatus !== 'mapped' ? { rows: [] } : runQuery({ entity, fields, filters: b.filters, limit: b.limit });
      return virtualResponse(entity, rows);
    },
  },

  // Mapping rules
  { method: 'GET', path: '/api/v1/mapping-rules/audit', handle: () => mappingAudit() },
  { method: 'POST', path: '/api/v1/mapping-rules/suggest', handle: ({ body }) => suggestMappings(asObj(body)) },
  {
    method: 'POST', path: '/api/v1/mapping-rules/auto-map',
    handle: () => ({
      created: MAPPING_RULES.filter(r => r.status === 'active').length,
      skipped: 2,
      errors: 1,
      details: ENTITIES.map(e => {
        const rule = ruleForEntity(e.name);
        if (!rule) return { entity: e.name, status: 'error' as const, reason: 'No source table with a matching name was found' };
        if (rule.status !== 'active') return { entity: e.name, status: 'skipped' as const, reason: 'A manually edited rule already exists' };
        return { entity: e.name, status: 'created' as const };
      }),
    }),
  },
  {
    method: 'GET', path: '/api/v1/mapping-rules',
    handle: ({ query }) => {
      const ve = query.get('virtual_entity');
      const st = query.get('source_type');
      return MAPPING_RULES.filter(r => (!ve || r.virtualEntity === ve) && (!st || r.sourceType === st));
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/mapping-rules\/([^/]+)\/validate$/,
    handle: ({ match }) => {
      const rule = MAPPING_RULES.find(r => r.id === match[1]);
      const e = rule && entityByName(rule.virtualEntity);
      return e && e.totalRows === 0
        ? { valid: false, errors: [`Source table ${rule!.sourceSchema}.${rule!.sourceTable} returned no rows.`] }
        : { valid: true, errors: [] };
    },
  },
  { method: 'GET', path: /^\/api\/v1\/mapping-rules\/([^/]+)$/, handle: ({ match }) => MAPPING_RULES.find(r => r.id === match[1]) || MAPPING_RULES[0] },
  {
    method: 'POST', path: '/api/v1/mapping-rules',
    handle: ({ body }) => ({ id: `mr-${Date.now().toString(36)}`, fieldMaps: [], status: 'draft', ...asObj(body), createdAt: ago(0), updatedAt: ago(0) }),
  },
  {
    method: 'PUT', path: /^\/api\/v1\/mapping-rules\/([^/]+)$/,
    handle: ({ match, body }) => ({ ...(MAPPING_RULES.find(r => r.id === match[1]) || MAPPING_RULES[0]), ...asObj(body), id: match[1], updatedAt: ago(0) }),
  },

  // Connector API catalogue (Connectors tab, tool builder)
  {
    method: 'GET', path: '/api/v1/automation/connector-apis',
    handle: ({ query }) => ({ items: CONNECTOR_APIS.filter(a => !query.get('target_system') || a.target_system === query.get('target_system')).map(specOf) }),
  },

  // Connector API registry and workbench
  { method: 'GET', path: '/api/v1/connector-apis/diagnostic', handle: () => connectorDiagnostic() },
  { method: 'POST', path: '/api/v1/connector-apis/smoke-test', handle: () => smokeReport() },
  {
    method: 'GET', path: '/api/v1/connector-apis',
    handle: ({ query }) => {
      const items = enrichedList(query.get('target_system'));
      return { items, totals: listTotals(items) };
    },
  },
  {
    method: 'GET', path: /^\/api\/v1\/connector-apis\/([^/]+)\/events$/,
    handle: ({ match, query }) => ({ events: auditEvents(decodeURIComponent(match[1]), Number(query.get('limit')) || 20) }),
  },
  {
    method: 'GET', path: /^\/api\/v1\/connector-apis\/([^/]+)\/canary-payload$/,
    handle: ({ match }) => {
      const a = CONNECTOR_APIS.find(x => x.api_id === decodeURIComponent(match[1])) || CONNECTOR_APIS[0];
      return { api_id: a.api_id, payload: canaryPayload(a) };
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/connector-apis\/([^/]+)\/invoke$/,
    handle: ({ match, body }) => invokeResult(decodeURIComponent(match[1]), asObj(asObj(body).payload)),
  },
  {
    method: 'GET', path: /^\/api\/v1\/connector-apis\/([^/]+)$/,
    handle: ({ match }) => {
      const id = decodeURIComponent(match[1]);
      const i = Math.max(0, CONNECTOR_APIS.findIndex(x => x.api_id === id));
      return { ...enriched(CONNECTOR_APIS[i], i), recent_events: auditEvents(CONNECTOR_APIS[i].api_id, 5) };
    },
  },

  // Virtual data API registry
  {
    method: 'GET', path: '/api/v1/vdl-apis',
    handle: ({ query }) => {
      const items = VDL_APIS.filter(a =>
        (!query.get('virtual_entity') || a.virtual_entity === query.get('virtual_entity')) && (!query.get('verb') || a.verb === query.get('verb')));
      return { total: items.length, items };
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/vdl-apis\/([^/]+)\/invoke$/,
    handle: ({ match, body }) => vdlInvoke(decodeURIComponent(match[1]), asObj(asObj(body).args)),
  },
  { method: 'GET', path: /^\/api\/v1\/vdl-apis\/([^/]+)$/, handle: ({ match }) => VDL_APIS.find(a => a.api_id === decodeURIComponent(match[1])) || VDL_APIS[0] },
];
