/**
 * Reasoning: the AI Copilot agent, ReAct tool catalogue, tools registry,
 * tool builder, and the tool diagnostics the registry browser reads.
 * (The planning playground search lives in control-plane.ts.)
 */
import {
  type SampleRoute, type ToolDef,
  TOOLS, CONNECTOR_APIS, PEOPLE,
  ago, asObj, between, pick, sse, emailOf, entityByName, entityRows, toolParamsSchema, callersOf, HOUR, DAY,
} from '../fixtures';
import { searchDocs } from './control-plane';

// ---------------------------------------------------------------------------
// Tool catalogue
// ---------------------------------------------------------------------------

const registered = (t: ToolDef) => ({
  name: t.name,
  description: t.description,
  risk_level: t.risk,
  requires_approval: !!t.approval,
  parameters: toolParamsSchema(t),
  group: t.group,
  tags: t.tags,
  connector_api: t.connectorApi || null,
  cacheable: t.risk === 'read_only',
});

/** Tools written in the Tool Builder (the rest are built in). */
const USER_TOOLS = ['compute_price_variance', 'find_surplus_stock', 'summarise_findings', 'create_procurement_alert', 'forecast_demand'];
const isUserTool = (name: string) => USER_TOOLS.includes(name);

const registryRow = (t: ToolDef, i: number) => ({
  tool_id: t.name,
  display_name: t.name.replace(/_/g, ' ').replace(/^./, ch => ch.toUpperCase()),
  group: isUserTool(t.name) ? 'dynamic' : t.group,
  description: t.description,
  risk_level: t.risk,
  requires_approval: !!t.approval,
  cacheable: t.risk === 'read_only',
  connector_api: t.connectorApi || null,
  tags: t.tags,
  parameters: toolParamsSchema(t),
  yaml_present: t.name !== 'summarise_findings',
  use_case_refs: between(`ucr-${t.name}`, 0, 6),
  has_canary: i % 7 !== 5,
});

const registryReport = () => {
  const tools = TOOLS.map(registryRow);
  const count = (key: (r: ReturnType<typeof registryRow>) => string) => tools.reduce<Record<string, number>>((acc, r) => { acc[key(r)] = (acc[key(r)] || 0) + 1; return acc; }, {});
  return {
    totals: {
      registered_tools: tools.length,
      yaml_tools: tools.filter(t => t.yaml_present).length + 1,
      yaml_only_orphans: 1,
      registry_only_orphans: 1,
      by_group: count(r => r.group),
      by_risk_level: count(r => r.risk_level),
    },
    tools,
    yaml_only_orphans: ['reconcile_bank_statement'],
    registry_only_orphans: ['summarise_findings'],
    overall: 'degraded',
  };
};

const ddbEntry = (t: ToolDef, i: number) => ({
  toolId: t.name,
  description: t.description,
  parameters: toolParamsSchema(t),
  riskLevel: t.risk,
  requiresApproval: !!t.approval,
  cacheable: t.risk === 'read_only',
  connectorApi: t.connectorApi || null,
  tags: t.tags,
  toolKind: isUserTool(t.name) ? 'user' : 'builtin',
  bucket: t.group,
  group: t.group,
  streaming: false,
  codeRef: isUserTool(t.name) ? `tools/${t.name}@v${1 + (i % 3)}` : `ai_engine.tools.${t.group}.${t.name}`,
  source: isUserTool(t.name) ? 'tool-builder' : 'registry-sync',
  updatedAt: ago(HOUR * (3 + i * 17)),
});

/** A believable result for running a tool with some arguments. */
function toolResult(name: string): unknown {
  const t = TOOLS.find(x => x.name === name);
  const entityFor: Record<string, string> = {
    query_ar_invoices: 'AR_Invoice', get_customer_credit_status: 'Account', query_inventory_positions: 'Inventory_Position',
    query_purchase_orders: 'Purchase_Order', query_vendor_master: 'Vendor_Master', query_market_signals: 'Market_Signal',
    query_contract_documents: 'Contract_Document', virtual_query: 'Opportunity', find_surplus_stock: 'Inventory_Position',
  };
  const e = entityByName(entityFor[name] || '');
  if (name === 'semantic_search') return { results: searchDocs('credit limit approval', 3).map(r => ({ source_id: r.source_id, content_type: r.content_type, similarity: r.similarity })) };
  if (name === 'get_customer_credit_status') return { account_id: 'ACC-1004', name: 'Cascade Convenience Stores', credit_limit: 750000, open_balance: 842300, utilisation_pct: 112.3, risk_tier: 'High', on_hold: false };
  if (name === 'compute_price_variance') return { orders_checked: 212, above_threshold: 9, largest: { po_number: '4500001214', vendor: 'Alucan Packaging GmbH', variance_pct: 7.4 } };
  if (name === 'forecast_demand') return { sku: 'FG-1002', region: 'West', weeks: [46, 47, 48, 49].map((w, i) => ({ week: `2026-W${w}`, forecast_qty: 18400 + i * 1250, low: 16900 + i * 1100, high: 20100 + i * 1400 })) };
  if (name === 'summarise_findings') return { summary: 'Three suppliers moved into the high-risk band this week. Port congestion at Rotterdam is the main driver.', words: 24 };
  if (e) return { rows: entityRows(e, 3), row_count: e.totalRows, source: e.name };
  if (t && t.risk !== 'read_only') return { success: true, record_id: `REC-${between(`rec-${name}`, 10000, 99999)}`, audit_event_id: `evt-${between(`evt-${name}`, 100000, 999999)}`, simulator_writeback: true };
  return { ok: true };
}

const canaryParams = (t: ToolDef) => {
  const sample: Record<string, unknown> = {
    query: 'credit limit approval', limit: 5, entity: 'Opportunity', status: 'Overdue', days_past_due: 30, account_id: 'ACC-1004', plant: 'PL02',
    stock_status: 'Below reorder point', vendor_id: 'V-1001', category: 'Packaging', severity: 'High', days: 7, threshold_pct: 5,
    material_id: 'FG-1003', min_days_of_supply: 45, sku: 'FG-1002', region: 'West', weeks: 4, audience: 'Supply chain review',
    recipient: 'collections@kinetiq-beverages.example', message: 'Sample notification', action_type: 'dunning_notice', entity_id: 'INV-88127',
    invoice_id: 'INV-88127', level: 2, po_number: '4500001214', reason: 'Price 7.4% above contract', from_plant: 'PL01', to_plant: 'PL02',
    quantity: 9000, new_limit: 900000, justification: 'Sustained volume growth', customer_id: '40004',
  };
  return Object.fromEntries(Object.keys(t.params).map(k => [k, sample[k] ?? 'sample']));
};

function canaryResult(t: ToolDef, i: number) {
  const skip = t.risk === 'high_risk_write';
  const fail = t.name === 'query_contract_documents';
  return {
    tool_id: t.name,
    group: isUserTool(t.name) ? 'dynamic' : t.group,
    risk_level: t.risk,
    requires_approval: !!t.approval,
    connector_api: t.connectorApi || null,
    status: skip ? 'skip' : fail ? 'fail' : 'pass',
    duration_ms: skip ? 0 : fail ? 30008 : between(`canary-${t.name}`, 90, 1900),
    params: canaryParams(t),
    marker: t.risk === 'read_only' ? null : `canary-${(1000 + i).toString(36)}`,
    ...(skip ? { reason: 'High-risk write: needs approval, not run in bulk' } : {}),
    ...(fail ? { error: 'Timed out reading /Procurement/Contracts (Google Drive quota exceeded)' } : {}),
    ...(!skip && !fail ? { result_preview: JSON.stringify(toolResult(t.name)).slice(0, 180) } : {}),
  };
}

function canaryReport(body: Record<string, any>) {
  const ids: string[] | undefined = Array.isArray(body.tool_ids) && body.tool_ids.length ? body.tool_ids : undefined;
  const results = TOOLS
    .filter(t => (!ids || ids.includes(t.name)) && (!body.only_read_only || t.risk === 'read_only'))
    .map(canaryResult);
  const n = (s: string) => results.filter(r => r.status === s).length;
  return {
    totals: { checked: results.length, pass: n('pass'), fail: n('fail'), skip: n('skip'), read_only_failures: results.filter(r => r.status === 'fail' && r.risk_level === 'read_only').length, duration_ms: results.reduce((s, r) => s + r.duration_ms, 0) },
    results,
    overall: n('fail') ? 'degraded' : 'healthy',
  };
}

const contractsReport = () => ({
  totals: { checked: TOOLS.length, errors: 1, warnings: 3, tools_with_issues: 3 },
  issues_by_tool: {
    summarise_findings: [{ severity: 'error', code: 'yaml_missing', message: 'Registered tool has no YAML definition under enterprise-knowledge/tools.' }],
    create_procurement_alert: [
      { severity: 'warning', code: 'no_connector_api', message: 'Write tool declares no connector API, so the write cannot be verified.' },
      { severity: 'warning', code: 'no_example', message: 'No example invocation in the tool YAML.' },
    ],
    query_market_signals: [{ severity: 'warning', code: 'param_undocumented', message: "Parameter 'days' has no default value documented." }],
  },
  overall: 'degraded',
});

const connectorApisReport = () => {
  const apis = CONNECTOR_APIS.map((a, i) => {
    const callers = callersOf(a.api_id);
    const never = a.api_id === 'sap.production_order.list' || a.api_id === 'external.gdrive.contract.get';
    return {
      api_id: a.api_id, target_system: a.target_system, operation: a.operation, risk_level: a.risk_level, description: a.description, tags: a.tags,
      has_request_schema: true, has_response_schema: a.api_id !== 'external.gdrive.contract.get',
      tool_callers: callers, tool_caller_count: callers.length, simulator_writeback: a.simulator_writeback,
      audit_count: never ? 0 : between(`audit-${a.api_id}`, 3, 240) + i,
      last_invocation_ts: never ? null : ago(14 + i * 53),
      verified: !never && a.api_id !== 'sap.purchase_order.block',
    };
  });
  const count = (key: (a: (typeof apis)[number]) => string) => apis.reduce<Record<string, number>>((acc, a) => { acc[key(a)] = (acc[key(a)] || 0) + 1; return acc; }, {});
  const orphans = apis.filter(a => a.tool_caller_count === 0).map(a => a.api_id);
  return {
    totals: { checked: apis.length, errors: 1, warnings: 2, orphans: orphans.length, verified: apis.filter(a => a.verified).length, never_invoked: apis.filter(a => a.audit_count === 0).length, by_target_system: count(a => a.target_system), by_risk_level: count(a => a.risk_level) },
    apis,
    issues_by_api: {
      'sap.purchase_order.block': [{ severity: 'error', code: 'audit_missing', message: 'High-risk write does not record an audit event.' }],
      'external.gdrive.contract.get': [{ severity: 'warning', code: 'no_response_schema', message: 'No response schema declared.' }],
      'sfdc.opportunity.list': [{ severity: 'warning', code: 'no_tool_caller', message: 'No ReAct tool calls this API.' }],
    },
    orphan_api_ids: orphans,
    overall: 'degraded',
  };
};

// ---------------------------------------------------------------------------
// Tool builder
// ---------------------------------------------------------------------------

const SOURCE: Record<string, string> = {
  compute_price_variance: `def run(ctx, threshold_pct: float = 5.0):
    """Compare purchase order prices with contracted prices."""
    contracts = {c["Vendor_ID"]: c for c in ctx.vdl.query("Contract_Document")}
    flagged = []
    for po in ctx.vdl.query("Purchase_Order", filters={"Status": "Open"}):
        contract = contracts.get(po["Vendor_ID"])
        if not contract:
            continue
        unit_price = po["Net_Value"] / po["Quantity"]
        variance = (unit_price - contract["Contracted_Price"]) / contract["Contracted_Price"] * 100
        if variance > threshold_pct:
            flagged.append({"po_number": po["PO_Number"], "variance_pct": round(variance, 1)})
    ctx.log.info("price check done", flagged=len(flagged))
    return {"orders_checked": len(contracts), "above_threshold": len(flagged), "orders": flagged}
`,
  find_surplus_stock: `def run(ctx, material_id: str, min_days_of_supply: float = 45):
    """Plants holding more than a given number of days of supply."""
    rows = ctx.vdl.query("Inventory_Position", filters={"Material_ID": material_id})
    surplus = [r for r in rows if r["Days_Of_Supply"] >= min_days_of_supply]
    return {"material_id": material_id, "plants": [r["Plant"] for r in surplus], "rows": surplus}
`,
  summarise_findings: `def run(ctx, audience: str = "operations"):
    """Write a short summary of the results gathered so far."""
    notes = ctx.memory.recent(limit=20)
    prompt = f"Summarise for {audience} in under 150 words:\\n" + "\\n".join(n.text for n in notes)
    return {"summary": ctx.llm.complete(prompt, max_tokens=300)}
`,
  create_procurement_alert: `def run(ctx, po_number: str, reason: str):
    """Raise an alert for the category buyer."""
    po = ctx.vdl.get("Purchase_Order", po_number)
    alert = {"type": "price_variance", "severity": "High", "entity_id": po_number, "description": reason}
    ctx.results.append("PA_Alert", alert)
    return {"success": True, "alert": alert, "buyer": po.get("Buyer")}
`,
  forecast_demand: `def run(ctx, sku: str, region: str = "all", weeks: int = 4):
    """Forecast demand for a SKU and region over the next weeks."""
    history = ctx.vdl.query("Opportunity", filters={"Product_Family__c": sku}, limit=5000)
    model = ctx.models.load("demand-ensemble-v3")
    return {"sku": sku, "region": region, "weeks": model.predict(history, horizon=weeks)}
`,
};

const builderTools = () => TOOLS.filter(t => isUserTool(t.name)).map((t, i) => ({
  tool_id: t.name,
  name: t.name,
  description: t.description,
  risk_level: t.risk,
  requires_approval: !!t.approval,
  cacheable: t.risk === 'read_only',
  connector_api: t.connectorApi || null,
  tags: t.tags,
  current_version: 1 + ((i * 2) % 4),
  status: 'active' as const,
  createdBy: emailOf(pick(PEOPLE, i + 3)),
  createdAt: ago(DAY * (34 - i * 5)),
  updatedAt: ago(HOUR * (5 + i * 41)),
}));

const toolDoc = (toolId: string) => {
  const summary = builderTools().find(t => t.tool_id === toolId) || builderTools()[0];
  const t = TOOLS.find(x => x.name === summary.tool_id)!;
  return { ...summary, parameters: toolParamsSchema(t), source_code: SOURCE[t.name] || SOURCE.find_surplus_stock, source_sha256: `sha256:${between(`sha-${t.name}`, 1e11, 9e11).toString(16)}c41f`, changelog: 'Handle suppliers without an active contract' };
};

const toolVersions = (toolId: string) => {
  const doc = toolDoc(toolId);
  const notes = ['Initial version', 'Add structured logging', 'Handle suppliers without an active contract', 'Round variance to one decimal'];
  return Array.from({ length: doc.current_version }, (_, k) => {
    const version = doc.current_version - k;
    return { tool_id: doc.tool_id, version, source_code: doc.source_code, parameters: doc.parameters, source_sha256: `sha256:${between(`sha-${toolId}-${version}`, 1e11, 9e11).toString(16)}c41f`, changelog: notes[version - 1] || 'Update', createdBy: emailOf(pick(PEOPLE, version + 2)), createdAt: ago(HOUR * 5 + k * DAY * 6) };
  });
};

// ---------------------------------------------------------------------------
// Agent
// ---------------------------------------------------------------------------

interface CannedAnswer { match: RegExp; intent: string; steps: { tool: string; args: Record<string, unknown>; preview: string; blocked?: string }[]; answer: string; violations?: string[] }

const ANSWERS: CannedAnswer[] = [
  {
    match: /credit/i, intent: 'cross_system',
    steps: [
      { tool: 'semantic_search', args: { query: 'credit limit approval thresholds' }, preview: 'POL-CREDIT-001 Credit Limit Management Policy (0.93)\nWF_CREDIT_APPROVAL_V1 Credit Approval Flow (0.88)\nSALESFORCE_ACCOUNT schema (0.84)' },
      { tool: 'get_customer_credit_status', args: { account_id: 'ACC-1004' }, preview: 'Cascade Convenience Stores: limit 750,000 USD, open balance 842,300 USD (112%), risk tier High' },
      { tool: 'update_credit_limit', args: { account_id: 'ACC-1004', new_limit: 900000 }, preview: '', blocked: 'A 20% increase needs Finance VP approval (POL-CREDIT-001). The agent does not run high-risk writes without approval.' },
    ],
    answer: 'A credit limit change follows **POL-CREDIT-001**:\n\n- Up to 5%: approved automatically\n- 5 to 10%: Regional Sales Manager, within 24 hours\n- Over 10%: Finance VP, within 48 hours\n- Over 1M USD in total: CFO\n\nSalesforce `Account.Credit_Limit__c` is the source of truth. Once approved, the new limit syncs to Oracle receivables (`AR_Customer.credit_limit`) within 15 minutes. Changes are blocked during the financial close window.\n\nFor Cascade Convenience Stores, the open balance is already 112% of the 750,000 USD limit. Raising it to 900,000 USD is a 20% increase, so it needs Finance VP approval. I did not make the change.',
    violations: ['update_credit_limit blocked: approval required (POL-CREDIT-001)'],
  },
  {
    match: /stock|inventory|reorder|expir/i, intent: 'read_only',
    steps: [
      { tool: 'semantic_search', args: { query: 'inventory reorder point policy' }, preview: 'POL-INV-001 Inventory Management Policy (0.94)\nWF_REPLENISHMENT_V1 Supply Chain Replenishment (0.87)\nSAP_INVENTORY_POSITION schema (0.85)' },
      { tool: 'query_inventory_positions', args: { stock_status: 'Below reorder point' }, preview: '7 positions below reorder point. Lowest: FG-1003 at PL02 Leeds, 6.2 days of supply' },
      { tool: 'find_surplus_stock', args: { material_id: 'FG-1003', min_days_of_supply: 45 }, preview: 'PL01 Rotterdam holds 52 days of supply (21,400 cases)' },
    ],
    answer: 'Seven SKU and plant combinations are below their reorder point. The most urgent is **Citrus Surge 500ml at Leeds**: 6.2 days of supply against a 10-day lead time.\n\nRotterdam holds 52 days of supply of the same SKU. Under **POL-INV-001** the replenishment workflow prefers a transfer over new production, so the suggested action is to move 9,000 cases from Rotterdam to Leeds.\n\nSAP is the source of truth for stock levels. I only read data; no transfer was created.',
  },
  {
    match: /invoice|overdue|payment|dso|receivable|order|cash/i, intent: 'read_only',
    steps: [
      { tool: 'semantic_search', args: { query: 'overdue invoice dunning policy' }, preview: 'POL-O2C-004 Dunning and Collections Policy (0.92)\nWF_DUNNING_V1 Dunning Run (0.89)\nORACLE_AR_INVOICE schema (0.86)' },
      { tool: 'query_ar_invoices', args: { status: 'Overdue', days_past_due: 30 }, preview: '18 invoices more than 30 days past due, 1.42M USD in total. Largest: INV-88127, 184,000 USD, 47 days' },
    ],
    answer: 'There are **18 invoices more than 30 days past due**, worth 1.42M USD. Days sales outstanding stands at 38.4 days against a target of 35.\n\nUnder **POL-O2C-004**:\n\n- 1 to 30 days: reminder email\n- 31 to 60 days: second notice and a call\n- 61 to 90 days: final notice\n- Over 90 days: credit hold, approved by the Finance VP\n\nEleven invoices are due a second notice and seven a final notice. The largest is INV-88127 for Cascade Convenience Stores (184,000 USD, 47 days).',
  },
  {
    match: /supplier|vendor|risk|contract|purchase/i, intent: 'read_only',
    steps: [
      { tool: 'semantic_search', args: { query: 'supplier risk single source policy' }, preview: 'POL-PROC-001 Procurement and Sourcing Policy (0.91)\nWF_RISK_ASSESSMENT_V1 Supplier Risk Assessment (0.90)\nSAP_VENDOR_MASTER schema (0.83)' },
      { tool: 'query_vendor_master', args: { category: 'Raw_Materials' }, preview: '14 suppliers with risk above 60. Highest: NutraChem Ingredients (77)' },
      { tool: 'query_market_signals', args: { severity: 'High', days: 7 }, preview: '6 high or critical signals. Port congestion at Rotterdam, sugar price up 11% in 30 days' },
    ],
    answer: 'The supplier needing attention is **NutraChem Ingredients**: its risk score rose from 48 to 77 after a reported plant fire, and it is the only approved source for taurine premix.\n\n**POL-PROC-001** requires a qualified second source for single-source materials within 12 months. The risk assessment workflow suggests starting qualification now and reviewing the contract penalty terms.\n\nSix high or critical market signals were recorded this week. Port congestion at Rotterdam is adding about 4 days to inbound lead times.',
  },
];

const DEFAULT_ANSWER: CannedAnswer = {
  match: /./, intent: 'read_only',
  steps: [{ tool: 'semantic_search', args: { query: '' }, preview: '' }],
  answer: '',
};

function agentResponse(question: string) {
  const canned = ANSWERS.find(a => a.match.test(question)) || DEFAULT_ANSWER;
  const hits = searchDocs(question, 5);
  const isDefault = canned === DEFAULT_ANSWER;
  const stepDefs = isDefault
    ? [{ tool: 'semantic_search', args: { query: question, limit: 5 }, preview: hits.map(h => `${h.metadata.object_name} (${h.similarity})`).join('\n'), blocked: undefined as string | undefined }]
    : canned.steps;
  const steps = [
    ...stepDefs.map((s, i) => ({
      step: i + 1, tool: s.tool, action: 'tool_call', args: s.args,
      ...(s.blocked ? { blocked: true, reason: s.blocked } : { result_preview: s.preview }),
      duration_ms: between(`agent-${s.tool}-${i}`, 180, 2400),
    })),
    { step: stepDefs.length + 1, action: 'final_answer', duration_ms: between(`agent-final-${question.length}`, 900, 2800) },
  ];
  const answer = isDefault
    ? `Here is what the knowledge index holds on that:\n\n${hits.slice(0, 4).map(h => `- **${h.metadata.object_name}** (${h.content_type.replace('onto_', '')}, ${h.metadata.source_system || 'Internal'})`).join('\n')}\n\nAsk about a specific entity, policy or workflow and I can go further, for example the approval steps for a credit limit change or which SKUs are below their reorder point.`
    : canned.answer;
  return {
    answer,
    intent: canned.intent,
    session_id: `sess-${Date.now().toString(36)}`,
    steps,
    total_steps: steps.length,
    total_tokens: between(`tok-${question.length}`, 2400, 9800),
    policy_violations: canned.violations || [],
  };
}

function agentStream(question: string) {
  const data = agentResponse(question);
  const events: Record<string, unknown>[] = [
    { type: 'status', message: 'Classifying the question' },
    { type: 'intent', intent: data.intent },
  ];
  const max = 10;
  for (const s of data.steps) {
    events.push({ type: 'step_start', step: s.step, max_steps: max });
    if ('tool' in s && s.tool) {
      events.push({ type: 'tool_call', step: s.step, tool: s.tool, args: (s as any).args });
      if ((s as any).blocked) events.push({ type: 'tool_blocked', step: s.step, tool: s.tool, reason: (s as any).reason });
      else events.push({ type: 'tool_result', step: s.step, tool: s.tool, duration_ms: s.duration_ms, preview: (s as any).result_preview });
    }
  }
  events.push({ type: 'answer', data });
  return sse(events);
}

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

export const reasoningRoutes: SampleRoute[] = [
  // AI Copilot
  { method: 'POST', path: '/api/v1/control-plane/agent/stream', handle: ({ body }) => agentStream(String(asObj(body).question || '')) },
  { method: 'POST', path: '/api/v1/control-plane/agent', handle: ({ body }) => agentResponse(String(asObj(body).question || '').replace(/^\[Context:[^\]]*\]\s*/, '')) },

  // ReAct tool catalogue
  { method: 'GET', path: '/api/v1/control-plane/tools', handle: () => ({ tools: TOOLS.map(registered), total: TOOLS.length }) },
  {
    method: 'POST', path: /^\/api\/v1\/control-plane\/tools\/([^/]+)\/execute$/,
    handle: ({ match }) => {
      const name = decodeURIComponent(match[1]);
      const t = TOOLS.find(x => x.name === name);
      const needsApproval = !!t?.approval;
      return {
        tool: name, risk_level: t?.risk || 'read_only', success: !needsApproval,
        result: needsApproval ? { error: 'approval_required', message: 'This tool changes data in a source system and needs approval before it runs.' } : toolResult(name),
        elapsed_ms: between(`exec-${name}`, 120, 2100),
      };
    },
  },

  // Tools registry (durable view)
  { method: 'POST', path: '/api/v1/tools-registry/resync', handle: () => ({ synced: TOOLS.length }) },
  {
    method: 'GET', path: '/api/v1/tools-registry',
    handle: ({ query }) => {
      const items = TOOLS.map(ddbEntry).filter(t => !query.get('group') || t.group === query.get('group'));
      return { total: items.length, items };
    },
  },
  {
    method: 'GET', path: /^\/api\/v1\/tools-registry\/([^/]+)$/,
    handle: ({ match }) => {
      const i = Math.max(0, TOOLS.findIndex(t => t.name === decodeURIComponent(match[1])));
      return ddbEntry(TOOLS[i], i);
    },
  },

  // Tool diagnostics (registry browser, journey builder palette, AI Ops)
  { method: 'GET', path: '/api/v1/diagnostics/react-tools/registry', handle: () => registryReport() },
  { method: 'GET', path: '/api/v1/diagnostics/react-tools/contracts', handle: () => contractsReport() },
  { method: 'GET', path: '/api/v1/diagnostics/react-tools/connector-apis', handle: () => connectorApisReport() },
  { method: 'POST', path: '/api/v1/diagnostics/react-tools/run', handle: ({ body }) => canaryReport(asObj(body)) },
  {
    method: 'POST', path: /^\/api\/v1\/diagnostics\/react-tools\/([^/]+)\/execute$/,
    handle: ({ match, body }) => {
      const name = decodeURIComponent(match[1]);
      const i = Math.max(0, TOOLS.findIndex(t => t.name === name));
      const t = TOOLS[i];
      const base = canaryResult(t, i);
      const params = asObj(asObj(body).params);
      return { ...base, status: base.status === 'skip' ? 'pass' : base.status, reason: undefined, duration_ms: base.duration_ms || between(`x-${name}`, 200, 1800), params: Object.keys(params).length ? params : base.params, result: base.status === 'fail' ? undefined : toolResult(name), result_preview: base.status === 'fail' ? undefined : JSON.stringify(toolResult(name)).slice(0, 180) };
    },
  },

  // Tool builder
  {
    method: 'GET', path: '/api/v1/tools/export',
    handle: () => ({ exported_at: ago(0), tools: builderTools().map(t => { const d = toolDoc(t.tool_id); return { name: d.name, description: d.description, parameters: d.parameters, risk_level: d.risk_level, requires_approval: d.requires_approval, cacheable: d.cacheable, connector_api: d.connector_api, tags: d.tags, source_code: d.source_code }; }) }),
  },
  { method: 'POST', path: '/api/v1/tools/import', handle: ({ body }) => ({ imported: 0, updated: (asObj(body).tools || []).length, skipped: 0, errors: [] }) },
  {
    method: 'GET', path: '/api/v1/tools',
    handle: ({ query }) => {
      const search = (query.get('search') || '').toLowerCase();
      return builderTools().filter(t =>
        (!search || `${t.name} ${t.description}`.toLowerCase().includes(search))
        && (!query.get('tag') || t.tags.includes(query.get('tag')!))
        && (!query.get('risk_level') || t.risk_level === query.get('risk_level')));
    },
  },
  {
    method: 'POST', path: '/api/v1/tools',
    handle: ({ body }) => {
      const b = asObj(body);
      return { tool_id: b.name, parameters: { type: 'object', properties: {} }, tags: [], requires_approval: false, cacheable: false, connector_api: null, ...b, current_version: 1, status: 'active', createdBy: emailOf(PEOPLE[0]), createdAt: ago(0), updatedAt: ago(0), changelog: 'Initial version' };
    },
  },
  { method: 'GET', path: /^\/api\/v1\/tools\/([^/]+)\/versions\/(\d+)$/, handle: ({ match }) => ({ ...toolDoc(decodeURIComponent(match[1])), current_version: Number(match[2]) }) },
  { method: 'GET', path: /^\/api\/v1\/tools\/([^/]+)\/versions$/, handle: ({ match }) => toolVersions(decodeURIComponent(match[1])) },
  { method: 'POST', path: /^\/api\/v1\/tools\/([^/]+)\/restore\/(\d+)$/, handle: ({ match }) => ({ ...toolDoc(decodeURIComponent(match[1])), changelog: `Restored version ${match[2]}`, updatedAt: ago(0) }) },
  {
    method: 'POST', path: /^\/api\/v1\/tools\/([^/]+)\/test$/,
    handle: ({ match, body }) => {
      const id = decodeURIComponent(match[1]);
      const now = Date.now();
      const ts = (ms: number) => new Date(now + ms).toISOString();
      return {
        status: 'pass', duration_ms: between(`test-${id}`, 140, 1600), result: toolResult(id), error: null,
        logs: [
          { ts: ts(0), level: 'info', msg: 'tool started', kw: asObj(asObj(body).params) },
          { ts: ts(180), level: 'info', msg: 'virtual data layer query', kw: { entity: 'Purchase_Order', rows: 212 } },
          { ts: ts(420), level: 'warning', msg: 'skipped rows without an active contract', kw: { rows: 4 } },
          { ts: ts(610), level: 'info', msg: 'tool finished' },
        ],
      };
    },
  },
  { method: 'GET', path: /^\/api\/v1\/tools\/([^/]+)$/, handle: ({ match }) => toolDoc(decodeURIComponent(match[1])) },
  {
    method: 'PUT', path: /^\/api\/v1\/tools\/([^/]+)$/,
    handle: ({ match, body }) => {
      const doc = toolDoc(decodeURIComponent(match[1]));
      const { if_unchanged_updated_at: _ignored, ...changes } = asObj(body);
      return { ...doc, ...changes, current_version: doc.current_version + 1, updatedAt: ago(0) };
    },
  },
  { method: 'DELETE', path: /^\/api\/v1\/tools\/([^/]+)$/, handle: ({ match }) => ({ deleted: true, tool_id: decodeURIComponent(match[1]) }) },
];
