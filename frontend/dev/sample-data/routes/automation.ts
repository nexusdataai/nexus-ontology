/**
 * AI Automation: journeys, the Journey Studio (stages, jobs, logs, schedules,
 * reports), journeys saved from the Copilot, the Copilot planner, the journey
 * builder and the automation registry. Data pipelines are journeys too.
 */
import {
  type SampleRoute, type Journey,
  JOURNEYS, ALL_JOURNEYS, COPILOT_JOURNEYS, STAGE_STEPS, TOOLS, PEOPLE, ADMIN_EMAIL,
  ago, ahead, asObj, between, pad, pick, round, emailOf, HOUR, DAY,
} from '../fixtures';
import { KPIS, alertsFor, runQuery } from '../rows';

// ---------------------------------------------------------------------------
// Journeys
// ---------------------------------------------------------------------------

const copilotDoc = (id: string) => COPILOT_JOURNEYS.find(j => j.journey_id === id);

/** A journey for any id: known ones from fixtures, Copilot-saved ones projected, anything else a blank journey. */
function journeyById(id: string): Journey {
  const known = ALL_JOURNEYS.find(j => j.id === id);
  if (known) return known;
  const doc = copilotDoc(id);
  const total = doc ? between(`cj-total-${id}`, 4, 9) : 0;
  return {
    ...JOURNEYS[0],
    id, journeyId: id, journey_id: id,
    name: doc?.title || 'New journey',
    description: doc?.description || '',
    type: doc?.solution_id || 'custom',
    solution_id: doc?.solution_id || 'custom',
    status: doc ? 'completed' : 'created',
    created_at: doc?.createdAt || ago(1), createdAt: doc?.createdAt || ago(1),
    updated_at: doc?.updatedAt || ago(1), updatedAt: doc?.updatedAt || ago(1),
    total_jobs: total, totalJobs: total, jobCount: total,
    completed_jobs: Math.max(0, total - 1), completedJobs: Math.max(0, total - 1),
    running_jobs: 0, runningJobs: 0,
    failed_jobs: total ? 1 : 0, failedJobs: total ? 1 : 0,
    success_rate: total ? round(((total - 1) * 100) / total, 1) : 0,
    avg_duration_seconds: doc ? 64 : 0,
    overallProgress: doc ? 100 : 0,
    stages: [{ stageId: 'main', name: doc?.title || 'Main', description: doc?.description || '', order: 0, status: doc ? 'completed' : 'pending', progress: doc ? 100 : 0 }],
  };
}

const stageOf = (j: Journey) => j.stages[0];
/** Step ids of a journey, in order. */
const stepsOf = (j: Journey): string[] => copilotDoc(j.id)?.steps.map(s => s.step_id) || STAGE_STEPS[stageOf(j).stageId] || ['run'];

function listJourneys(query: URLSearchParams) {
  const type = query.get('type');
  const component = query.get('component_type');
  const status = query.get('status');
  const search = (query.get('search') || '').toLowerCase();
  // Pipelines are listed only when asked for by component type.
  let list = component ? ALL_JOURNEYS.filter(j => j.odaComponentType === component) : JOURNEYS;
  if (type) list = list.filter(j => j.type === type || stageOf(j).stageId === type.replace(/-/g, '_'));
  if (status) list = list.filter(j => j.status === status || (status === 'created' && j.status === 'pending'));
  if (search) list = list.filter(j => j.name.toLowerCase().includes(search));
  return { success: true, data: list, total: list.length };
}

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

const fmtDuration = (seconds: number) => `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;

interface SampleJob {
  jobId: string; id: string; job_id: string; stageId: string; stageName: string; status: string; progress: number;
  startTime: string; startedAt: string; endTime?: string; completedAt?: string; duration?: string;
  triggeredBy: string; itemsProcessed: number; itemsTotal: number; errorCount: number;
  rowsProcessed: number; durationMs: number;
  metrics: Record<string, number>; stepResults: Record<string, { status: string; progress: number; durationSeconds?: number }>;
  currentStep: string | null; error?: string;
}

/** Index of the step a failed job stopped at. */
const FAILED_AT = 2;

function stepResultsFor(steps: string[], status: string, seconds: number, seed: string) {
  const out: SampleJob['stepResults'] = {};
  const weights = steps.map((s, i) => 0.5 + between(`${seed}-${s}-${i}`, 0, 1, 3));
  const sum = weights.reduce((a, b) => a + b, 0);
  steps.forEach((s, i) => {
    const d = round((seconds * weights[i]) / sum, 1);
    if (status === 'completed') out[s] = { status: 'completed', progress: 100, durationSeconds: d };
    else if (status === 'failed') out[s] = i < FAILED_AT ? { status: 'completed', progress: 100, durationSeconds: d } : i === FAILED_AT ? { status: 'failed', progress: 40, durationSeconds: d } : { status: 'pending', progress: 0 };
    else out[s] = i < 3 ? { status: 'completed', progress: 100, durationSeconds: d } : i === 3 ? { status: 'running', progress: 55 } : { status: 'pending', progress: 0 };
  });
  return out;
}

function jobsFor(j: Journey): SampleJob[] {
  const steps = stepsOf(j);
  const stage = stageOf(j);
  const count = Math.min(j.totalJobs, 12);
  // Interval between runs: daily for analytics journeys, 6-hourly for pipelines.
  const gap = j.odaComponentType === 'data-pipeline' ? 360 : DAY;
  // The journey was last updated when its latest job finished (or, if running, started).
  const updatedMin = Math.max(2, Math.round((Date.now() - new Date(j.updatedAt).getTime()) / 60000));
  return Array.from({ length: count }, (_, k) => {
    const number = j.totalJobs - k;
    const jobId = `JOB-${pad(number)}`;
    let status = 'completed';
    if (k === 0 && j.status === 'running') status = 'running';
    else if (k === 0 && j.status === 'failed') status = 'failed';
    else if (j.failedJobs > 0 && (k === 4 || (j.failedJobs > 2 && k === 8))) status = 'failed';
    const seconds = Math.max(8, Math.round(j.avg_duration_seconds * between(`${j.id}-${jobId}-d`, 0.8, 1.25, 2)));
    const startMin = updatedMin + k * gap + (status === 'running' ? 0 : seconds / 60);
    const itemsTotal = between(`${j.id}-${jobId}-n`, 180, 2400);
    const failedItems = status === 'failed' ? Math.round(itemsTotal * 0.6) : between(`${j.id}-${jobId}-f`, 0, 6);
    const skipped = between(`${j.id}-${jobId}-s`, 0, 40);
    const processed = status === 'running' ? Math.round(itemsTotal * 0.55) : itemsTotal - failedItems - skipped;
    const start = ago(startMin);
    const end = status === 'running' ? undefined : new Date(new Date(start).getTime() + seconds * 1000).toISOString();
    const stepResults = stepResultsFor(steps, status, seconds, `${j.id}-${jobId}`);
    const current = status === 'completed' ? steps[steps.length - 1] : status === 'failed' ? steps[Math.min(FAILED_AT, steps.length - 1)] : steps[Math.min(3, steps.length - 1)];
    return {
      jobId, id: jobId, job_id: jobId,
      stageId: stage.stageId, stageName: stage.name,
      status, progress: status === 'completed' ? 100 : status === 'failed' ? 38 : 55,
      startTime: start, startedAt: start,
      ...(end ? { endTime: end, completedAt: end, duration: fmtDuration(seconds) } : {}),
      triggeredBy: pick(['schedule', 'schedule', 'ui', 'schedule', 'api'], k),
      itemsProcessed: processed, itemsTotal, errorCount: status === 'failed' ? failedItems : 0,
      rowsProcessed: processed, durationMs: seconds * 1000,
      metrics: {
        availableCalls: itemsTotal, itemsTotal, itemsProcessed: processed, skippedTasks: skipped, newTasks: itemsTotal - skipped,
        successfulProcessing: processed, failedProcessing: failedItems, noRecording: 0,
        ...(end ? { durationSeconds: seconds } : {}),
      },
      stepResults,
      currentStep: current,
      ...(status === 'failed' ? { error: failureReason(j) } : {}),
    };
  });
}

const failureReason = (j: Journey) =>
  stageOf(j).stageId === 'procurement_analytics' ? 'Oracle payables did not respond within 30 seconds (oracle.ap_invoice.list)'
  : stageOf(j).stageId === 'etl_pipeline' ? 'Schema validation failed: column Expiry_Date has 14 values that are not dates'
  : stageOf(j).stageId === 'semantic_rag' ? 'Embedding service returned 429 (rate limit) after 3 retries'
  : 'Upstream system did not respond within 30 seconds';

function jobById(journeyId: string, jobId: string): SampleJob {
  const j = journeyById(journeyId);
  const found = jobsFor(j).find(job => job.jobId === jobId);
  if (found) return found;
  // A job started from the UI in this session: report it as finished.
  const steps = stepsOf(j);
  const seconds = Math.max(8, j.avg_duration_seconds || 42);
  return {
    jobId, id: jobId, job_id: jobId, stageId: stageOf(j).stageId, stageName: stageOf(j).name,
    status: 'completed', progress: 100, startTime: ago(1), startedAt: ago(1), endTime: ago(0), completedAt: ago(0), duration: fmtDuration(seconds),
    triggeredBy: 'ui', itemsProcessed: 1240, itemsTotal: 1240, errorCount: 0, rowsProcessed: 1240, durationMs: seconds * 1000,
    metrics: { itemsTotal: 1240, itemsProcessed: 1240, successfulProcessing: 1240, failedProcessing: 0, skippedTasks: 0, newTasks: 1240, noRecording: 0, durationSeconds: seconds },
    stepResults: stepResultsFor(steps, 'completed', seconds, `${journeyId}-${jobId}`),
    currentStep: steps[steps.length - 1],
  };
}

/** Status as the studio polls it. A job shown as running in the list reports finished here, so polling stops. */
function jobStatus(journeyId: string, jobId: string) {
  const job = jobById(journeyId, jobId);
  const j = journeyById(journeyId);
  const steps = stepsOf(j);
  const status = job.status === 'running' ? 'completed' : job.status;
  const stepResults = job.status === 'running' ? stepResultsFor(steps, 'completed', j.avg_duration_seconds || 60, `${journeyId}-${jobId}`) : job.stepResults;
  return {
    success: true,
    job_id: jobId, jobId, journey_id: journeyId,
    status,
    progress: status === 'completed' ? 100 : job.progress,
    current_step: status === 'completed' ? steps[steps.length - 1] : job.currentStep,
    currentStep: status === 'completed' ? steps[steps.length - 1] : job.currentStep,
    message: status === 'completed' ? 'All steps completed' : job.error,
    error: job.error,
    step_results: stepResults, stepResults,
    // The same results as a list, for the index build panel.
    steps: steps.map(s => ({ step_id: s, id: s, status: stepResults[s]?.status || 'pending', elapsed_seconds: stepResults[s]?.durationSeconds })),
    started_at: job.startTime, completed_at: job.endTime || ago(0),
    metrics: job.metrics,
  };
}

// ---------------------------------------------------------------------------
// Step logs
// ---------------------------------------------------------------------------

const STEP_DETAIL: Record<string, string[]> = {
  extract_unified_schema: ['Read canonical-entities.yaml: 86 entities across 6 systems', 'Built 86 virtual entity documents'],
  resolve_fdw_mapping: ['Matched 71 entities to live FDW and simulator tables', '9 entities are virtual only, 6 have no source table'],
  extract_mapping_rules: ['Loaded 118 active mapping rules', 'Enriched 71 schema documents with field mappings'],
  extract_policies: ['Parsed 14 policy documents from onto-data/policies', 'Extracted 42 rules and 9 approval tables'],
  extract_workflows: ['Parsed 23 workflow definitions from onto-data/workflows', 'Extracted 81 steps across Salesforce, SAP and Oracle'],
  extract_integrations: ['Parsed 9 integration mappings from onto-data/integrations', 'Extracted 28 field-level mappings'],
  normalize: ['Merged 132 documents, removed 3 duplicates', 'Wrote bundle.onto (438 KB)'],
  enrich: ['Generated semantic descriptions for 86 entities', 'Model: claude-sonnet, 61,204 tokens in, 18,932 tokens out'],
  chunk_embed: ['Split 132 documents into 5,630 chunks', 'Generated 5,630 embeddings (1,024 dimensions)'],
  load_vector: ['Upserted 5,630 rows into pgvector', 'Vacuumed and re-indexed onto_embeddings'],
  index_nlq_exemplars: ['Generated 344 example questions from curated YAML and schema', 'Indexed 344 exemplars'],
  load_graph: ['Loaded 412 nodes and 1,287 edges', 'Graph uses the metadata fallback (AGE extension not installed)'],
  validate: ['Ran 24 black-box retrieval scenarios', '23 passed, 1 below the recall threshold (inventory expiry rules)'],
  extract: ['Connected to the source and read the batch', 'Fetched rows in pages of 1,000'],
  validate_schema: ['Checked column names and types against the mapping rule', 'All mandatory fields present'],
  transform: ['Applied field mappings and transforms', 'Converted dates and normalised currency to USD'],
  load: ['Wrote rows to the virtual data layer', 'Upserted on the primary key'],
  verify: ['Row count matches the source', 'Null check passed for mandatory fields'],
};

function stepLogs(journeyId: string, jobId: string, stepName: string) {
  const job = jobById(journeyId, jobId);
  const result = job.stepResults[stepName];
  if (!result || result.status === 'pending') return [];
  const label = stepName.replace(/_/g, ' ');
  const total = Math.max(40, Math.round(job.itemsTotal / 4));
  const startMs = new Date(job.startTime).getTime() + Object.keys(job.stepResults).indexOf(stepName) * 9000;
  const lines: { level: string; message: string }[] = [
    { level: 'info', message: `Starting step: ${label}` },
    ...(STEP_DETAIL[stepName] || [`Loaded ${job.itemsTotal.toLocaleString('en-US')} records for ${label}`]).slice(0, 1).map(m => ({ level: 'info', message: m })),
    { level: 'info', message: `[${Math.round(total / 3)}/${total}] ${label} in progress` },
  ];
  if (result.status === 'failed') {
    lines.push({ level: 'warning', message: 'Attempt 1 of 3 failed, retrying in 5s' });
    lines.push({ level: 'warning', message: 'Attempt 2 of 3 failed, retrying in 15s' });
    lines.push({ level: 'error', message: job.error || 'Step failed' });
  } else if (result.status === 'running') {
    lines.push({ level: 'info', message: `[${Math.round(total * 0.55)}/${total}] ${label} in progress` });
  } else {
    lines.push({ level: 'info', message: `[${Math.round((total * 2) / 3)}/${total}] ${label} in progress` });
    if (between(`${jobId}-${stepName}-w`, 0, 1, 2) > 0.72) lines.push({ level: 'warning', message: 'Skipped 3 records with missing mandatory fields' });
    lines.push({ level: 'info', message: `[${total}/${total}] ${label} in progress` });
    for (const m of (STEP_DETAIL[stepName] || []).slice(1)) lines.push({ level: 'info', message: m });
    lines.push({ level: 'info', message: `Step completed in ${result.durationSeconds ?? 4}s` });
  }
  return lines.map((l, i) => ({
    timestamp: new Date(startMs + i * 1400).toISOString(),
    level: l.level.toUpperCase(),
    message: l.message,
    step_id: stepName, step_name: stepName, job_id: jobId,
  }));
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

const REPORT_META: Record<string, { prefix: string; title: string; icon: string; table: { entity: string; title: string; columns: [string, string, string][]; orderBy?: string } | null }> = {
  order_to_cash: { prefix: 'O2C', title: 'Order-to-Cash Report', icon: 'ShoppingCart', table: { entity: 'O2C_Order_Result', title: 'Highest risk orders', orderBy: 'anomaly_score DESC', columns: [['opportunity_id', 'Order', 'text'], ['account_name', 'Customer', 'text'], ['order_amount', 'Amount', 'currency'], ['match_status', 'Match', 'text'], ['anomaly_score', 'Anomaly score', 'decimal']] } },
  demand_forecasting: { prefix: 'DF', title: 'Demand Forecast Report', icon: 'TrendingUp', table: { entity: 'DF_Forecast_Result', title: 'Largest forecasts', orderBy: 'forecast_qty DESC', columns: [['sku', 'SKU', 'text'], ['region', 'Region', 'text'], ['period', 'Period', 'text'], ['forecast_qty', 'Forecast', 'integer'], ['promo_lift', 'Promo lift', 'percent']] } },
  inventory_optimization: { prefix: 'IO', title: 'Inventory Report', icon: 'Package', table: { entity: 'IO_Position_Result', title: 'Positions needing attention', orderBy: 'days_of_supply ASC', columns: [['sku', 'SKU', 'text'], ['plant', 'Plant', 'text'], ['current_qty', 'On hand', 'integer'], ['days_of_supply', 'Days of supply', 'decimal'], ['expiry_risk', 'Expiry risk', 'text']] } },
  procurement_analytics: { prefix: 'PA', title: 'Procurement Report', icon: 'Receipt', table: { entity: 'PA_Spend_Result', title: 'Largest purchase orders', orderBy: 'amount DESC', columns: [['po_id', 'Order', 'text'], ['vendor', 'Supplier', 'text'], ['category', 'Category', 'text'], ['amount', 'Amount', 'currency'], ['price_variance', 'Price variance', 'percent']] } },
  supply_chain_risk: { prefix: 'SCR', title: 'Supplier Risk Report', icon: 'Shield', table: { entity: 'SCR_Vendor_Result', title: 'Highest risk suppliers', orderBy: 'risk_score DESC', columns: [['vendor_name', 'Supplier', 'text'], ['region', 'Region', 'text'], ['risk_score', 'Risk score', 'integer'], ['otd_pct', 'On time', 'percent'], ['financial_risk', 'Financial risk', 'text']] } },
};
const KPI_LABELS: Record<string, [string, string, string]> = {
  dso: ['Days sales outstanding', 'decimal', 'Clock'], match_rate: ['Match rate', 'percent', 'CheckCircle'], leakage_rate: ['Revenue leakage', 'percent', 'AlertTriangle'], total_open_ar: ['Open receivables', 'currency', 'DollarSign'], on_time_payment_pct: ['On-time payment', 'percent', 'TrendingUp'],
  mape: ['Forecast error (MAPE)', 'percent', 'Target'], bias: ['Forecast bias', 'percent', 'Activity'], stockout_rate_pct: ['Stockout rate', 'percent', 'AlertTriangle'], total_forecast_qty: ['Forecast volume', 'integer', 'BarChart3'],
  turns: ['Inventory turns', 'decimal', 'RefreshCw'], fill_rate_pct: ['Fill rate', 'percent', 'CheckCircle'], days_of_supply: ['Days of supply', 'decimal', 'Clock'], expired_write_off_pct: ['Expiry write-off', 'percent', 'AlertTriangle'],
  total_spend: ['Total spend', 'currency', 'DollarSign'], maverick_spend_pct: ['Maverick spend', 'percent', 'AlertTriangle'], stp_rate_pct: ['Straight-through rate', 'percent', 'CheckCircle'], price_variance_pct: ['Price variance', 'percent', 'Activity'],
  avg_risk_score: ['Average risk score', 'decimal', 'Shield'], otd_pct: ['On-time delivery', 'percent', 'Truck'], single_source_count: ['Single-source materials', 'integer', 'AlertTriangle'], contract_compliance_pct: ['Contract compliance', 'percent', 'CheckCircle'],
};

function aggregateReport(journeyId: string) {
  const j = journeyById(journeyId);
  const jobs = jobsFor(j);
  const steps = stepsOf(j);
  const stageId = stageOf(j).stageId;
  const meta = REPORT_META[stageId];
  const done = jobs.filter(job => job.status === 'completed').length;
  const failed = jobs.filter(job => job.status === 'failed').length;

  const runKpis = [
    { key: 'total_jobs', label: 'Jobs', icon: 'Activity', format: 'integer', value: j.totalJobs, status: 'ok' },
    { key: 'success_rate', label: 'Success rate', icon: 'CheckCircle', format: 'percent', value: j.success_rate, status: j.success_rate >= 95 ? 'ok' : j.success_rate >= 85 ? 'warn' : 'critical' },
    { key: 'avg_duration', label: 'Average duration', icon: 'Clock', format: 'duration', value: j.avg_duration_seconds, status: 'ok' },
    { key: 'failed_jobs', label: 'Failed jobs', icon: 'AlertTriangle', format: 'integer', value: j.failedJobs, status: j.failedJobs === 0 ? 'ok' : j.failedJobs > 2 ? 'critical' : 'warn' },
  ];
  const businessKpis = meta
    ? Object.entries(KPIS[meta.prefix]).map(([key, value]) => ({ key, label: KPI_LABELS[key]?.[0] || key.replace(/_/g, ' '), icon: KPI_LABELS[key]?.[2] || 'Activity', format: KPI_LABELS[key]?.[1] || 'decimal', value, status: 'ok' }))
    : stageId === 'semantic_rag'
      ? [
          { key: 'documents', label: 'Documents indexed', icon: 'FileText', format: 'integer', value: 132, status: 'ok' },
          { key: 'embeddings', label: 'Embeddings', icon: 'Database', format: 'integer', value: 5630, status: 'ok' },
          { key: 'graph_nodes', label: 'Graph nodes', icon: 'Network', format: 'integer', value: 412, status: 'ok' },
          { key: 'graph_edges', label: 'Graph edges', icon: 'GitBranch', format: 'integer', value: 1287, status: 'ok' },
          { key: 'validation_pass_rate', label: 'Validation pass rate', icon: 'Shield', format: 'percent', value: 95.8, status: 'warn' },
        ]
      : [
          { key: 'rows_processed', label: 'Rows processed', icon: 'Database', format: 'integer', value: jobs.reduce((n, job) => n + job.itemsProcessed, 0), status: 'ok' },
          { key: 'rows_rejected', label: 'Rows rejected', icon: 'AlertTriangle', format: 'integer', value: jobs.reduce((n, job) => n + job.errorCount, 0), status: 'warn' },
        ];

  const alerts = meta ? alertsFor(meta.prefix).slice(0, 5) : jobs.filter(job => job.status === 'failed').map(job => ({ type: 'job_failed', severity: 'High', message: job.error, entity_id: job.jobId, jobId: job.jobId }));
  const sections: Record<string, unknown>[] = [
    { id: 'business_kpis', title: stageId === 'semantic_rag' ? 'Knowledge index' : 'Business results', kind: 'kpi_grid', description: 'From the latest completed job', kpis: businessKpis },
  ];
  if (meta?.table) {
    sections.push({
      id: 'top_rows', title: meta.table.title, kind: 'table', description: null,
      columns: meta.table.columns.map(([key, label, format]) => ({ key, label, format })),
      rows: runQuery({ entity: meta.table.entity, fields: meta.table.columns.map(col => col[0]), orderBy: meta.table.orderBy, limit: 8 }).rows,
    });
  }
  sections.push({
    id: 'job_outcomes', title: 'Job outcomes', kind: 'distribution', description: `Last ${jobs.length} jobs`,
    buckets: [
      { label: 'Completed', count: done, percentage: jobs.length ? round((done * 100) / jobs.length, 1) : 0 },
      { label: 'Failed', count: failed, percentage: jobs.length ? round((failed * 100) / jobs.length, 1) : 0 },
      { label: 'Running', count: jobs.length - done - failed, percentage: jobs.length ? round(((jobs.length - done - failed) * 100) / jobs.length, 1) : 0 },
    ],
    total: jobs.length,
  });
  sections.push({
    id: 'alerts', title: 'Alerts raised', kind: 'alerts_list', description: null, alerts,
    groups: ['Critical', 'High', 'Medium', 'Low'].map(s => ({ key: s.toLowerCase(), label: s, count: alerts.filter(a => a.severity === s).length })).filter(g => g.count > 0),
  });
  sections.push({
    id: 'steps', title: 'Step breakdown', kind: 'step_breakdown', description: 'Outcome of each step across recent jobs',
    steps: steps.map(s => {
      const outcomes = jobs.map(job => job.stepResults[s]?.status || 'pending');
      return {
        step_id: s, name: s.replace(/_/g, ' ').replace(/^./, ch => ch.toUpperCase()), tool: copilotDoc(j.id)?.steps.find(x => x.step_id === s)?.tool || null,
        completed: outcomes.filter(o => o === 'completed').length, failed: outcomes.filter(o => o === 'failed').length,
        pending: outcomes.filter(o => o === 'pending').length, other: outcomes.filter(o => o === 'running').length, total: outcomes.length,
      };
    }),
  });
  sections.push({
    id: 'timeline', title: 'Recent activity', kind: 'timeline', description: null,
    events: jobs.slice(0, 6).flatMap(job => [
      ...(job.endTime ? [{ fromState: 'running', toState: job.status, timestamp: job.endTime, stepId: job.currentStep, reason: job.error || `${job.jobId} finished in ${job.duration}` }] : []),
      { fromState: 'pending', toState: 'running', timestamp: job.startTime, stepId: steps[0], reason: `${job.jobId} started by ${job.triggeredBy}` },
    ]),
  });

  return {
    schema_version: '1.0',
    journey_id: j.id,
    journey_title: j.name,
    solution_id: j.solution_id,
    title: meta?.title || (stageId === 'semantic_rag' ? 'Knowledge Index Report' : 'Journey Report'),
    icon: meta?.icon || (stageId === 'semantic_rag' ? 'Brain' : 'Activity'),
    summary_kpis: runKpis,
    sections,
    total_jobs: j.totalJobs,
    generated_at: ago(0),
  };
}

// ---------------------------------------------------------------------------
// Schedules
// ---------------------------------------------------------------------------

const SCHEDULES = [
  { journeyId: 'jr-o2c-01', interval: 1440, enabled: true, lastStatus: 'completed', by: PEOPLE[1] },
  { journeyId: 'jr-dfc-01', interval: 360, enabled: true, lastStatus: 'running', by: PEOPLE[2] },
  { journeyId: 'jr-inv-01', interval: 60, enabled: false, lastStatus: 'completed', by: PEOPLE[3] },
  { journeyId: 'jr-prc-01', interval: 1440, enabled: true, lastStatus: 'failed', by: PEOPLE[4] },
  { journeyId: 'jr-rag-01', interval: 1440, enabled: true, lastStatus: 'completed', by: PEOPLE[0] },
  { journeyId: 'jr-pipe-social', interval: 360, enabled: true, lastStatus: 'running', by: PEOPLE[5] },
  { journeyId: 'jr-pipe-files', interval: 720, enabled: true, lastStatus: 'completed', by: PEOPLE[5] },
].map((s, i) => {
  const j = journeyById(s.journeyId);
  const lastRunMin = Math.round((Date.now() - new Date(j.updatedAt).getTime()) / 60000);
  return {
    scheduleId: `sch-${pad(i + 1, 3)}`,
    journeyId: s.journeyId, journeyName: j.name,
    stageId: stageOf(j).stageId,
    intervalMinutes: s.interval,
    enabled: s.enabled,
    timezone: pick(['Europe/Amsterdam', 'UTC', 'America/Chicago'], i),
    lastRunAt: ago(lastRunMin),
    nextRunAt: s.enabled ? ahead(Math.max(4, s.interval - (lastRunMin % s.interval))) : null,
    lastJobId: `JOB-${pad(j.totalJobs)}`,
    lastJobStatus: s.lastStatus,
    createdAt: ago(DAY * (20 - i)),
    createdBy: emailOf(s.by),
  };
});
const scheduleById = (id: string) => SCHEDULES.find(s => s.scheduleId === id) || SCHEDULES[0];

// ---------------------------------------------------------------------------
// Copilot (plan, execute, save) and saved journeys
// ---------------------------------------------------------------------------

const toolRisk = (tool: string) => TOOLS.find(t => t.name === tool)?.risk || 'read_only';

/** Plans the Copilot proposes, picked by keywords in the goal. */
const PLANS = [
  { match: /invoice|overdue|collect|dunning|receivable|cash|credit/i, doc: COPILOT_JOURNEYS[0], extra: { step_id: 'hold_if_over_limit', name: 'Place credit hold if over limit', tool: 'place_credit_hold', description: 'Only for customers above their credit limit' } },
  { match: /stock|inventory|transfer|reorder|replenish/i, doc: COPILOT_JOURNEYS[1], extra: null },
  { match: /contract|price|purchase|procure|spend/i, doc: COPILOT_JOURNEYS[2], extra: { step_id: 'block_orders', name: 'Block orders above 10% variance', tool: 'block_purchase_order', description: 'Hold the order until the buyer reviews it' } },
  { match: /supplier|vendor|risk|signal/i, doc: COPILOT_JOURNEYS[3], extra: null },
];
const planIndexFor = (goal: string) => Math.max(0, PLANS.findIndex(p => p.match.test(goal || '')));
const planSteps = (idx: number) => {
  const p = PLANS[idx] || PLANS[0];
  return [...p.doc.steps, ...(p.extra ? [p.extra] : [])];
};
const sessionIdx = (sessionId: string) => Number(sessionId.split('-')[1]) || 0;

const RESULT_PREVIEW: Record<string, string> = {
  query_ar_invoices: '18 invoices more than 30 days past due, 1.42M USD in total',
  get_customer_credit_status: '3 customers above 90% of their credit limit, 1 above 100%',
  send_dunning_notice: '18 notices sent: 11 second notices, 7 final notices',
  write_action_log: '19 actions recorded in O2C_Action_Log',
  place_credit_hold: 'Cascade Convenience Stores placed on credit hold',
  query_inventory_positions: '7 SKU and plant combinations below reorder point',
  find_surplus_stock: 'Surplus found at Rotterdam and Austin for 5 of 7 SKUs',
  create_transfer_proposal: '5 transfer proposals created, 31,400 cases in total',
  query_contract_documents: '38 active contracts loaded',
  query_purchase_orders: '212 open purchase orders loaded',
  compute_price_variance: '9 orders above the 5% threshold, largest 7.4%',
  create_procurement_alert: '9 alerts raised for category buyers',
  send_notification: 'Summary sent to 4 buyers',
  block_purchase_order: 'Purchase order 4500001214 blocked',
  query_vendor_master: '412 suppliers loaded, 14 with risk above 60',
  query_market_signals: '6 high or critical signals in the last 7 days',
  summarise_findings: 'One-page brief written (412 words)',
};
const completedStep = (s: { step_id: string; tool: string }, i: number) => ({
  step_id: s.step_id, tool: s.tool, status: 'completed',
  result_preview: RESULT_PREVIEW[s.tool] || 'Step completed',
  result: { summary: RESULT_PREVIEW[s.tool] || 'Step completed', rows: between(`cs-${s.step_id}`, 3, 212) },
  duration_ms: between(`cs-d-${s.step_id}-${i}`, 240, 3800),
});
const pendingOf = (s: { step_id: string; name: string; tool: string; description: string }) => ({
  step_id: s.step_id, step_name: s.name, tool: s.tool,
  params: s.tool === 'place_credit_hold' ? { customer_id: '40004', reason: 'Open balance above credit limit' } : { po_number: '4500001214', reason: 'Price 7.4% above contract' },
  params_preview: s.tool === 'place_credit_hold' ? { customer_id: '40004' } : { po_number: '4500001214' },
  rationale: `${s.description}. This is a high-risk write and needs approval.`,
  connector_api: TOOLS.find(t => t.name === s.tool)?.connectorApi || null,
  risk_level: toolRisk(s.tool),
  stage_id: 'main',
});

/** Result of running a plan up to the first step that needs approval. */
function executePlan(sessionId: string, approved: boolean | null) {
  const steps = planSteps(sessionIdx(sessionId));
  const gate = steps.findIndex(s => toolRisk(s.tool) === 'high_risk_write');
  if (gate >= 0 && approved === null) {
    return { session_id: sessionId, run_id: sessionId, status: 'awaiting_step_approval', steps: steps.slice(0, gate).map(completedStep), pending_step: pendingOf(steps[gate]) };
  }
  if (gate >= 0 && approved === false) {
    return { session_id: sessionId, run_id: sessionId, status: 'rejected', steps: [...steps.slice(0, gate).map(completedStep), { step_id: steps[gate].step_id, tool: steps[gate].tool, status: 'rejected', result_preview: 'Rejected by the approver', duration_ms: 0 }], summary: 'Stopped: the high-risk step was rejected.' };
  }
  const done = steps.map(completedStep);
  return {
    session_id: sessionId, run_id: sessionId, status: 'completed', steps: done, job_id: null,
    summary: `Completed ${done.length} steps. ${done.map(d => d.result_preview).slice(0, 3).join('. ')}.`,
  };
}

const journeyYaml = (title: string, steps: { step_id: string; name: string; tool: string }[]) => [
  `journey_id: cj-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`,
  `title: ${title}`, 'kind: copilot', 'stages:', '  - stage_id: main', `    name: ${title}`, '    steps:',
  ...steps.flatMap(s => [`      - step_id: ${s.step_id}`, `        name: ${s.name}`, `        tool: ${s.tool}`]),
].join('\n');

const savedDoc = (id: string) => {
  const doc = copilotDoc(id);
  if (!doc) return null;
  return {
    journey: {
      journey_id: doc.journey_id, title: doc.title, display_name: doc.title, description: doc.description, kind: doc.kind,
      solution_id: doc.solution_id, tags: doc.tags, createdBy: doc.createdBy, createdAt: doc.createdAt, updatedAt: doc.updatedAt,
      stages: [{ stage_id: 'main', name: doc.title, description: doc.description, steps: doc.steps.map(s => ({ ...s, id: s.step_id, params: {} })) }],
    },
  };
};

// ---------------------------------------------------------------------------
// Journey builder
// ---------------------------------------------------------------------------

const toolOutputs = () => Object.fromEntries(TOOLS.map(t => [t.name, [
  ...(t.risk === 'read_only' ? [{ key: 'rows', kind: 'list', desc: 'Records returned' }, { key: 'row_count', kind: 'number', desc: 'Number of records' }] : [{ key: 'success', kind: 'boolean', desc: 'True when the write was accepted' }, { key: 'record_id', kind: 'string', desc: 'Id of the record written' }]),
  { key: 'summary', kind: 'string', desc: 'One-line description of the result' },
]]));
const toolRelationships = () => Object.fromEntries(TOOLS.map(t => [t.name, [
  { name: 'success', description: 'The tool finished without error', auto_terminate_default: false },
  { name: 'failure', description: 'The tool raised an error', auto_terminate_default: true },
  ...(t.risk === 'read_only' ? [{ name: 'empty', description: 'No records matched', auto_terminate_default: true }] : []),
]]));

const builderSteps = (body: Record<string, any>): { id: string; tool: string }[] => {
  const flat = Array.isArray(body.steps) ? body.steps : [];
  const staged = Array.isArray(body.stages) ? body.stages.flatMap((s: any) => (Array.isArray(s.steps) ? s.steps : [])) : [];
  return (flat.length ? flat : staged).map((s: any, i: number) => ({ id: String(s.id || s.step_id || `step_${i + 1}`), tool: String(s.tool || '') }));
};

function builderValidation(body: Record<string, any>) {
  const steps = builderSteps(body);
  const errors = steps.length === 0 ? [{ severity: 'error' as const, path: 'steps', code: 'no_steps', message: 'Add at least one tool to the canvas.' }] : [];
  const warnings = steps.filter(s => toolRisk(s.tool) === 'high_risk_write').map(s => ({ severity: 'warning' as const, path: `steps.${s.id}`, code: 'approval_required', message: `Step '${s.id}' calls ${s.tool}, which pauses for approval when run.` }));
  return { valid: errors.length === 0, errors: errors.map(e => e.message), warnings: warnings.map(w => w.message), report: { errors, warnings } };
}

function builderRun(body: Record<string, any>, runId: string, approved: boolean | null) {
  const steps = builderSteps(body);
  const gate = approved === null ? steps.findIndex(s => toolRisk(s.tool) === 'high_risk_write') : -1;
  const ran = gate >= 0 ? steps.slice(0, gate) : steps;
  return {
    run_id: runId,
    status: gate >= 0 ? 'awaiting_step_approval' : 'completed',
    step_results: Object.fromEntries(ran.map((s, i) => [s.id, { status: 'completed', tool: s.tool, duration_ms: between(`br-${s.id}-${i}`, 180, 2600), result: { summary: RESULT_PREVIEW[s.tool] || 'Step completed' } }])),
    completed_steps: ran.map(s => s.id),
    pending_step: gate >= 0 ? { step_id: steps[gate].id, tool: steps[gate].tool, stage_id: 'main', params_preview: { reason: 'Needs approval before it runs' } } : null,
    error: null,
    validation_report: builderValidation(body).report,
  };
}

// ---------------------------------------------------------------------------
// Automation registry
// ---------------------------------------------------------------------------

const REGISTRY = [
  { useCaseId: 'o2c-credit-hold', solution: 'order-to-cash', title: 'Credit hold for accounts over limit', tools: ['get_customer_credit_status', 'place_credit_hold', 'write_action_log'] },
  { useCaseId: 'o2c-dunning-run', solution: 'order-to-cash', title: 'Tiered dunning run', tools: ['query_ar_invoices', 'send_dunning_notice', 'write_action_log'] },
  { useCaseId: 'o2c-dispute-case', solution: 'order-to-cash', title: 'Open dispute for quantity mismatch', tools: ['virtual_query', 'send_notification'] },
  { useCaseId: 'df-forecast-override-review', solution: 'demand-forecasting', title: 'Review expiring forecast overrides', tools: ['forecast_demand', 'send_notification'] },
  { useCaseId: 'io-inter-plant-transfer', solution: 'inventory-optimization', title: 'Inter-plant transfer proposal', tools: ['query_inventory_positions', 'find_surplus_stock', 'create_transfer_proposal'] },
  { useCaseId: 'io-expiry-discount', solution: 'inventory-optimization', title: 'Near-expiry discount workflow', tools: ['query_inventory_positions', 'send_notification'] },
  { useCaseId: 'pa-contract-price-check', solution: 'procurement-analytics', title: 'Contract price check', tools: ['query_contract_documents', 'query_purchase_orders', 'compute_price_variance', 'create_procurement_alert'] },
  { useCaseId: 'pa-block-over-variance', solution: 'procurement-analytics', title: 'Block orders above price tolerance', tools: ['compute_price_variance', 'block_purchase_order'] },
  { useCaseId: 'scr-weekly-risk-brief', solution: 'supply-chain-risk', title: 'Weekly supplier risk brief', tools: ['query_vendor_master', 'query_market_signals', 'summarise_findings'] },
  { useCaseId: 'c360-credit-limit-review', solution: 'customer-360', title: 'Credit limit review for growing accounts', tools: ['get_customer_credit_status', 'update_credit_limit'] },
].map((r, i) => {
  const yamlText = [
    `use_case_id: ${r.useCaseId}`, `title: ${r.title}`, `solution_id: ${r.solution}`, 'version: 1', 'trigger:', '  type: schedule', '  cron: "0 6 * * *"', 'stages:', '  - stage_id: main', '    steps:',
    ...r.tools.flatMap((t, k) => [`      - step_id: step_${k + 1}`, `        tool: ${t}`, `        risk_level: ${toolRisk(t)}`]),
  ].join('\n');
  return { useCaseId: r.useCaseId, solution: r.solution, sourceFile: `enterprise-knowledge/automations/${r.solution}/${r.useCaseId}.yaml`, yamlText, sizeBytes: yamlText.length, updatedAt: ago(HOUR * (7 + i * 29)) };
});

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

const J = '\\/api\\/v1\\/journeys\\/([^/]+)';

export const automationRoutes: SampleRoute[] = [
  // Journey list (Home, AI Automation, Knowledge Processor panel, data pipelines)
  { method: 'GET', path: '/api/v1/journeys/', handle: ({ query }) => listJourneys(query) },
  { method: 'GET', path: '/api/v1/journeys', handle: ({ query }) => listJourneys(query) },
  {
    method: 'POST', path: '/api/v1/journeys/',
    handle: ({ body }) => {
      const b = asObj(body);
      const id = `jr-${Date.now().toString(36)}`;
      const stages = (Array.isArray(b.stages) && b.stages.length ? b.stages : [{ stageId: 'main', name: b.name || 'Main', order: 0 }]).map((s: any) => ({ description: '', status: 'pending', progress: 0, ...s }));
      const data = { ...journeyById(id), name: b.name || 'New journey', description: b.description || '', odaComponentType: b.odaComponentType || 'resource-management', solution_id: b.solution_id || 'custom', stages };
      return { success: true, journey_id: id, journeyId: id, id, data };
    },
  },

  // Jobs
  {
    method: 'GET', path: new RegExp(`^${J}\\/jobs\\/([^/]+)\\/status$`),
    handle: ({ match }) => jobStatus(match[1], match[2]),
  },
  {
    method: 'GET', path: new RegExp(`^${J}\\/jobs\\/([^/]+)\\/logs$`),
    handle: ({ match, query }) => {
      const step = query.get('step_name');
      const job = jobById(match[1], match[2]);
      const logs = step ? stepLogs(match[1], match[2], step) : Object.keys(job.stepResults).flatMap(s => stepLogs(match[1], match[2], s));
      return { success: true, data: { logs, total: logs.length, job_id: match[2] }, logs };
    },
  },
  {
    method: 'GET', path: new RegExp(`^${J}\\/jobs\\/([^/]+)\\/report$`),
    handle: ({ match }) => {
      const job = jobById(match[1], match[2]);
      return {
        executionSummary: { tasksFound: job.itemsTotal, newTasks: job.metrics.newTasks, skippedAlreadyProcessed: job.metrics.skippedTasks, processedSuccessfully: job.itemsProcessed, failed: job.errorCount, transcriptsCollected: 0, analyzed: job.itemsProcessed },
        failedTasks: job.status === 'failed' ? [{ taskId: job.jobId, errors: [job.error || 'Job failed'] }] : [],
      };
    },
  },
  { method: 'GET', path: new RegExp(`^${J}\\/jobs\\/([^/]+)$`), handle: ({ match }) => jobById(match[1], match[2]) },
  {
    method: 'POST', path: new RegExp(`^${J}\\/jobs\\/([^/]+)\\/cancel$`),
    handle: ({ match }) => ({ success: true, job_id: match[2], status: 'cancelled' }),
  },
  {
    method: 'GET', path: new RegExp(`^${J}\\/jobs$`),
    handle: ({ match }) => {
      const jobs = jobsFor(journeyById(match[1]));
      return { success: true, jobs, data: jobs, total: jobs.length };
    },
  },
  {
    // Run a stage. The new job reports "completed" on the first status poll.
    method: 'POST', path: new RegExp(`^${J}\\/jobs$`),
    handle: ({ match, query }) => {
      const j = journeyById(match[1]);
      const jobId = `JOB-${pad(j.totalJobs + 1)}`;
      return { success: true, job_id: jobId, jobId, id: jobId, journey_id: match[1], stageId: query.get('stage_id') || stageOf(j).stageId, status: 'running', progress: 0, startTime: ago(0) };
    },
  },

  // Stages and steps
  {
    method: 'GET', path: new RegExp(`^${J}\\/stages\\/([^/]+)\\/steps\\/([^/]+)\\/logs$`),
    handle: ({ match }) => {
      const j = journeyById(match[1]);
      const job = jobsFor(j)[0];
      return job ? stepLogs(match[1], job.jobId, match[3]).map(l => ({ timestamp: l.timestamp, level: l.level.toLowerCase(), message: l.message, stepId: match[3], stageId: match[2], jobId: job.jobId })) : [];
    },
  },
  {
    method: 'GET', path: new RegExp(`^${J}\\/stages\\/([^/]+)\\/steps$`),
    handle: ({ match }) => {
      const j = journeyById(match[1]);
      const job = jobsFor(j)[0];
      return stepsOf(j).map((s, i) => ({ id: s, stepId: s, name: s.replace(/_/g, ' ').replace(/^./, ch => ch.toUpperCase()), order: i, status: job?.stepResults[s]?.status || 'pending', progress: job?.stepResults[s]?.progress || 0 }));
    },
  },
  {
    method: 'GET', path: new RegExp(`^${J}\\/stages$`),
    handle: ({ match }) => ({ success: true, stages: journeyById(match[1]).stages }),
  },
  { method: 'POST', path: new RegExp(`^${J}\\/stages$`), handle: ({ query }) => ({ success: true, stageId: query.get('stage_id') }) },

  // Reports
  { method: 'GET', path: new RegExp(`^${J}\\/aggregate-report$`), handle: ({ match }) => ({ success: true, data: aggregateReport(match[1]) }) },

  // Journey actions and detail
  {
    method: 'POST', path: new RegExp(`^${J}\\/(start|pause|resume|cancel|retry)$`),
    handle: ({ match }) => {
      const next: Record<string, string> = { start: 'running', pause: 'paused', resume: 'running', cancel: 'cancelled', retry: 'running' };
      return { ...journeyById(match[1]), status: next[match[2]] };
    },
  },
  { method: 'GET', path: new RegExp(`^${J}$`), handle: ({ match }) => ({ success: true, data: journeyById(match[1]) }) },

  // Schedules
  {
    method: 'GET', path: /^\/api\/v1\/schedules\/?$/,
    handle: ({ query }) => {
      const id = query.get('journey_id');
      const data = SCHEDULES.filter(s => !id || s.journeyId === id);
      return { success: true, data, total: data.length };
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/schedules\/?$/,
    handle: ({ body }) => {
      const b = asObj(body);
      const j = journeyById(String(b.journey_id || 'jr-o2c-01'));
      return { success: true, data: { scheduleId: `sch-${Date.now().toString(36)}`, journeyId: j.id, journeyName: j.name, stageId: b.stage_id || stageOf(j).stageId, intervalMinutes: b.interval_minutes || 60, enabled: b.enabled ?? true, timezone: b.timezone || 'UTC', lastRunAt: null, nextRunAt: ahead(b.interval_minutes || 60), lastJobId: null, lastJobStatus: null, createdAt: ago(0), createdBy: ADMIN_EMAIL } };
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/schedules\/([^/]+)\/(toggle|reset|run-now)$/,
    handle: ({ match }) => {
      const s = scheduleById(match[1]);
      if (match[2] === 'toggle') return { success: true, data: { ...s, enabled: !s.enabled, nextRunAt: s.enabled ? null : ahead(s.intervalMinutes) } };
      if (match[2] === 'run-now') return { success: true, data: { ...s, lastRunAt: ago(0), lastJobStatus: 'running' } };
      return { success: true, data: { ...s, nextRunAt: ahead(s.intervalMinutes) } };
    },
  },
  { method: 'GET', path: /^\/api\/v1\/schedules\/([^/]+)$/, handle: ({ match }) => ({ success: true, data: scheduleById(match[1]) }) },
  {
    method: 'PUT', path: /^\/api\/v1\/schedules\/([^/]+)$/,
    handle: ({ match, body }) => {
      const b = asObj(body);
      const s = scheduleById(match[1]);
      return { success: true, data: { ...s, intervalMinutes: b.interval_minutes ?? s.intervalMinutes, enabled: b.enabled ?? s.enabled, timezone: b.timezone ?? s.timezone } };
    },
  },

  // Journeys saved from the Copilot
  {
    method: 'GET', path: '/api/v1/control-plane/journeys',
    handle: ({ query }) => {
      const search = (query.get('search') || '').toLowerCase();
      const journeys = COPILOT_JOURNEYS
        .filter(j => !search || `${j.title} ${j.journey_id} ${j.tags.join(' ')}`.toLowerCase().includes(search))
        .map(({ steps: _steps, createdMin: _c, updatedMin: _u, description: _d, ...summary }) => summary);
      return { journeys, total: journeys.length };
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/control-plane\/journeys\/([^/]+)\/run$/,
    handle: ({ match }) => {
      const doc = copilotDoc(match[1]) || COPILOT_JOURNEYS[0];
      const j = journeyById(doc.journey_id);
      const steps = doc.steps.map(completedStep);
      const jobId = `JOB-${pad(j.totalJobs + 1)}`;
      return { session_id: `cps-0-${Date.now().toString(36)}`, run_id: jobId, job_id: jobId, status: 'completed', steps, summary: `${doc.title}: ${steps.length} steps completed. ${steps[steps.length - 1].result_preview}.` };
    },
  },
  {
    // Only Copilot-saved ids answer here. Any other id must stay a 404: the
    // Journey Studio probes this path to tell saved journeys from built-in ones.
    method: 'GET', path: /^\/api\/v1\/control-plane\/journeys\/(cj-[^/]+)$/,
    handle: ({ match }) => savedDoc(match[1]) || savedDoc(COPILOT_JOURNEYS[0].journey_id),
  },

  // Copilot planner
  {
    method: 'POST', path: '/api/v1/control-plane/copilot-journey',
    handle: ({ body }) => {
      const goal = String(asObj(body).goal || '');
      const idx = planIndexFor(goal);
      const p = PLANS[idx];
      const steps = planSteps(idx);
      return {
        session_id: `cps-${idx}-${Date.now().toString(36)}`,
        goal,
        plan: steps.map(s => ({ id: s.step_id, name: s.name, tool: s.tool, params: {}, rationale: s.description })),
        rag_context: ['POL-O2C-004 Dunning and Collections Policy', 'POL-CREDIT-001 Credit Limit Management Policy', 'WF_DUNNING_V1 Dunning Run', 'ORACLE_AR_INVOICE schema', 'SALESFORCE_ACCOUNT schema'].slice(0, 3 + (idx % 3)),
        playbook_context: { use_case_id: p.doc.journey_id.replace(/^cj-/, ''), title: p.doc.title, solution_id: p.doc.solution_id, score: 0.87, source: 'automation-registry', tags: p.doc.tags, consumes_entities: ['AR_Invoice', 'Account'], produces_entities: ['O2C_Action_Log'] },
        validation: {
          ok: true,
          errors: [],
          warnings: steps.filter(s => toolRisk(s.tool) === 'high_risk_write').map(s => ({ step_id: s.step_id, code: 'approval_required', message: `${s.tool} is a high-risk write and will pause for approval.` })),
        },
      };
    },
  },
  { method: 'POST', path: /^\/api\/v1\/control-plane\/copilot-journey\/([^/]+)\/execute$/, handle: ({ match }) => executePlan(decodeURIComponent(match[1]), null) },
  {
    method: 'POST', path: /^\/api\/v1\/control-plane\/copilot-journey\/([^/]+)\/approve-step$/,
    handle: ({ match, body }) => {
      const b = asObj(body);
      const approved = b.approved ?? b.approve ?? (b.decision ? b.decision === 'approve' : true);
      return executePlan(decodeURIComponent(match[1]), approved !== false);
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/control-plane\/copilot-journey\/([^/]+)\/feedback$/,
    handle: ({ match }) => ({
      session_id: decodeURIComponent(match[1]),
      revised_plan: planSteps(sessionIdx(decodeURIComponent(match[1]))).map(s => ({ id: s.step_id, name: s.name, tool: s.tool, params: {}, rationale: `${s.description} (revised after your feedback)` })),
    }),
  },
  {
    method: 'POST', path: /^\/api\/v1\/control-plane\/copilot-journey\/([^/]+)\/save$/,
    handle: ({ match, body }) => {
      const p = PLANS[sessionIdx(decodeURIComponent(match[1]))] || PLANS[0];
      const title = String(asObj(body).name || asObj(body).title || p.doc.title);
      const yaml = journeyYaml(title, planSteps(sessionIdx(decodeURIComponent(match[1]))));
      const journey_id = yaml.split('\n')[0].replace('journey_id: ', '');
      return { success: true, persisted: true, journey_id, yaml, journey_definition: { journey_id, title, display_name: title } };
    },
  },

  // Journey builder
  { method: 'GET', path: '/api/v1/control-plane/journey-builder/tool-outputs', handle: () => ({ hints: toolOutputs() }) },
  { method: 'GET', path: '/api/v1/control-plane/journey-builder/tool-relationships', handle: () => ({ relationships: toolRelationships() }) },
  { method: 'POST', path: '/api/v1/control-plane/journey-builder/validate', handle: ({ body }) => builderValidation(asObj(body)) },
  {
    method: 'POST', path: '/api/v1/control-plane/journey-builder/save',
    handle: ({ body }) => {
      const b = asObj(body);
      const title = String(b.display_name || b.name || 'Untitled journey');
      const yaml = journeyYaml(title, builderSteps(b).map(s => ({ step_id: s.id, name: s.id.replace(/_/g, ' '), tool: s.tool })));
      const journey_id = yaml.split('\n')[0].replace('journey_id: ', '');
      return { success: true, journey_id, yaml, url: `/workspace/automation?tab=copilot-saved&journeyId=${journey_id}`, validation_report: builderValidation(b).report };
    },
  },
  {
    method: 'POST', path: /^\/api\/v1\/control-plane\/journey-builder\/run\/([^/]+)\/approve-step$/,
    handle: ({ match, body }) => {
      const approved = asObj(body).approved !== false;
      const stepId = String(asObj(body).step_id || 'step');
      return {
        run_id: decodeURIComponent(match[1]),
        status: approved ? 'completed' : 'failed',
        step_results: approved ? { [stepId]: { status: 'completed', duration_ms: 640, result: { summary: 'Approved and executed' } } } : {},
        completed_steps: approved ? [stepId] : [],
        pending_step: null,
        error: approved ? null : `Step '${stepId}' was rejected`,
      };
    },
  },
  { method: 'POST', path: '/api/v1/control-plane/journey-builder/run', handle: ({ body }) => builderRun(asObj(body), `run-${Date.now().toString(36)}`, null) },
  {
    method: 'POST', path: '/api/v1/control-plane/journey-builder/suggest',
    handle: () => ({ suggestions: [{ tool: 'write_action_log', reason: 'Record what the journey did, for audit.' }, { tool: 'send_notification', reason: 'Tell the owner when the journey finishes.' }] }),
  },
  {
    method: 'GET', path: /^\/api\/v1\/control-plane\/runs\/([^/]+)\/queues$/,
    handle: ({ match }) => {
      const runId = decodeURIComponent(match[1]);
      return { run_id: runId, queues: {
        [`nexus:queue:${runId}:find_overdue.success->check_credit.invoices`]: { depth: 0, pending: 0, seq: 18 },
        [`nexus:queue:${runId}:check_credit.success->send_notice.customers`]: { depth: 3, pending: 3, seq: 15 },
        [`nexus:queue:${runId}:send_notice.success->log_actions.notices`]: { depth: 0, pending: 0, seq: 12 },
      } };
    },
  },

  // Automation registry
  {
    method: 'GET', path: '/api/v1/automation/registry',
    handle: ({ query }) => {
      const items = REGISTRY.filter(r => !query.get('solution') || r.solution === query.get('solution'));
      return { total: items.length, items };
    },
  },
  { method: 'GET', path: /^\/api\/v1\/automation\/registry\/([^/]+)$/, handle: ({ match }) => REGISTRY.find(r => r.useCaseId === decodeURIComponent(match[1])) || REGISTRY[0] },
  {
    method: 'POST', path: '/api/v1/automation/registry',
    handle: ({ body }) => {
      const b = asObj(body);
      return { useCaseId: b.use_case_id, solution: b.solution, sourceFile: b.source_file || `enterprise-knowledge/automations/${b.solution}/${b.use_case_id}.yaml`, yamlText: b.yaml_text, sizeBytes: String(b.yaml_text || '').length, updatedAt: ago(0) };
    },
  },
];

export { REGISTRY as AUTOMATION_REGISTRY, jobsFor, journeyById };
