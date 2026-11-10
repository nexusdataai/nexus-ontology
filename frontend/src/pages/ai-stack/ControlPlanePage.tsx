import { ModalOverlay, ModalPanel } from '@/components/ds/Modal';
import { useState, useEffect, useCallback } from 'react';
import Layout from '@/components/Layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageTabsBar, useUrlTab, type TabSection } from '@/components/ds/PageTabs';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Icon } from '@/components/ds/Icon';
import { AnimatedNumber } from '@/components/ds/AnimatedNumber';
import { EmptyState, SectionHeader } from '@/components/ds/primitives';
import {
  CodeBlock, DetailSheet, InlineError, KeyValues, MetricStrip, Panel, SearchInput, StatusPill, SubHeading, TableShell,
} from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
import { apiClient } from '@/services/apiClient';
import { ontoApi, type OntoDocument, type OntoStats } from '@/services/ontoApi';
import { SemanticRagStudioPanel } from '@/components/journeys/SemanticRagStudioPanel';
import KnowledgeGraphView from '@/components/control-plane/KnowledgeGraphView';
import BuildIndexPanel from '@/components/rag/BuildIndexPanel';
import OntoDataManager from '@/components/rag/OntoDataManager';
import {
  knowledgePipelinesService,
  KnowledgePipeline,
  KnowledgePipelineRun,
} from '@/services/knowledgePipelinesService';

/** Tabs grouped into sections. Item values are the original ?tab= values. */
const CP_SECTIONS: TabSection[] = [
  { label: 'Knowledge', icon: 'network', items: [
    { value: 'semantic', label: 'Pipeline' },
    { value: 'knowledge', label: 'Index' },
    { value: 'explorer', label: 'Graph' },
  ] },
  { label: 'Policies', icon: 'shield-check', items: [{ value: 'policies', label: 'Policy builder' }] },
  { label: 'Workflows', icon: 'workflow', items: [{ value: 'workflows', label: 'Workflows' }] },
  { label: 'Integrations', icon: 'plug', items: [{ value: 'integrations', label: 'Integration rules' }] },
];

export default function ControlPlanePage() {
  const [tab, setTab] = useUrlTab('semantic');

  return (
    <Layout>
      <Tabs value={tab} onValueChange={setTab}>
        <PageTabsBar
          title="Control Plane"
          description="The enterprise knowledge the agent reasons over: ontology, knowledge graph, policies, workflows and integration rules."
          sections={CP_SECTIONS}
          value={tab}
          onChange={setTab}
        />
        <TabsContent value="semantic" className="mt-0"><SemanticLayerInner /></TabsContent>
        <TabsContent value="knowledge" className="mt-0 h-pane-sub"><KnowledgeFormationInner /></TabsContent>
        <TabsContent value="explorer" className="mt-0 h-pane-sub"><KnowledgeGraphView /></TabsContent>
        <TabsContent value="policies" className="mt-0 h-pane"><PolicyBuilderInner /></TabsContent>
        <TabsContent value="workflows" className="mt-0 h-pane"><WorkflowRulesInner /></TabsContent>
        <TabsContent value="integrations" className="mt-0 h-pane"><IntegrationRulesInner /></TabsContent>
      </Tabs>
    </Layout>
  );
}

// ============================================================================
// Shared
// ============================================================================

interface SimulatorStatus {
  loaded: boolean;
  tables: number;
  rows: number;
}

interface CpStats {
  total_embeddings: number;
  graph_nodes: number;
  graph_edges: number;
  onto_schema: number;
  onto_policy: number;
  onto_workflow: number;
  onto_integration: number;
  fdw_tables: number;
  embedding_available: boolean;
  virtual_entities?: number;
  mapped_entities?: number;
  virtual_only_entities?: number;
  unmapped_entities?: number;
  mapping_rules_total?: number;
  mapping_rules_active?: number;
  entities_by_system?: Record<string, number>;
  simulator_status?: Record<string, SimulatorStatus>;
}

const fmt = (n?: number | null): string => (n == null ? '0' : n.toLocaleString());

const formatDateTime = (iso?: string | null): string => {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};

/** "6 hours ago". Falls back to the date for anything older than a month. */
const timeAgo = (iso?: string | null): string => {
  if (!iso) return '';
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '';
  const min = Math.round((Date.now() - t) / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min} min ago`;
  const h = Math.round(min / 60);
  if (h < 24) return `${h} ${h === 1 ? 'hour' : 'hours'} ago`;
  const d = Math.round(h / 24);
  if (d < 31) return `${d} ${d === 1 ? 'day' : 'days'} ago`;
  return formatDateTime(iso);
};

const humanize = (s: string): string => {
  const t = String(s || '').replace(/^onto_/, '').replace(/[_-]+/g, ' ').trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : '';
};

/** Content types of the knowledge index, in the order they are shown. */
const CONTENT_TYPES: { key: string; label: string; plural: string; description: string }[] = [
  { key: 'onto_schema', label: 'Schema', plural: 'Schemas', description: 'Entities, their fields and how they map to source systems' },
  { key: 'onto_policy', label: 'Policy', plural: 'Policies', description: 'Business rules, limits and approval thresholds' },
  { key: 'onto_workflow', label: 'Workflow', plural: 'Workflows', description: 'Process steps that span systems' },
  { key: 'onto_integration', label: 'Integration', plural: 'Integrations', description: 'Field-level sync rules between systems' },
];

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(CONTENT_TYPES.map(t => [t.key, t.label]));
const typePlural = (key: string): string => CONTENT_TYPES.find(t => t.key === key)?.plural || humanize(key);

/** One horizontal bar, drawn in the single accent. */
function ShareBar({ value, max, index = 0, className }: { value: number; max: number; index?: number; className?: string }) {
  const pct = max > 0 ? Math.max(value > 0 ? 2 : 0, (value / max) * 100) : 0;
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-surface-3', className)} aria-hidden="true">
      <div className="grow-x h-full rounded-full bg-primary" style={{ width: `${pct}%`, '--i': index } as React.CSSProperties} />
    </div>
  );
}

// ============================================================================
// Knowledge pipelines registry
// ============================================================================

const STAGE_LABEL: Record<string, string> = {
  extract_unified_schema: 'Read schema',
  resolve_fdw_mapping: 'Resolve mappings',
  extract_fdw: 'Read source tables',
  extract_mapping_rules: 'Read mapping rules',
  extract_policies: 'Read policies',
  extract_workflows: 'Read workflows',
  extract_integrations: 'Read integrations',
  normalize: 'Merge',
  enrich: 'Enrich',
  chunk_embed: 'Split and embed',
  load_vector: 'Load vector index',
  load_graph: 'Load graph',
  validate: 'Check quality',
  index_nlq_exemplars: 'Index example questions',
};

const OUTPUT_LABEL: Record<string, string> = {
  onto_schema: 'Schema documents',
  onto_policy: 'Policy documents',
  onto_workflow: 'Workflow documents',
  onto_integration: 'Integration documents',
  pgvector: 'Vector index',
  graph: 'Knowledge graph',
  nlq_exemplar: 'Question exemplars',
};

const runTime = (run?: KnowledgePipelineRun): string => (run?.SK ? run.SK.replace('RUN#', '') : (run?.recordedAt || ''));
const runStatus = (run: KnowledgePipelineRun): string => (run.success === false ? 'failed' : 'completed');
const runCounts = (run?: KnowledgePipelineRun): string =>
  Object.entries(run?.counts || {}).map(([k, v]) => `${fmt(v)} ${k.replace(/_/g, ' ')}`).join(' · ');

function StageFlow({ pipeline }: { pipeline: KnowledgePipeline }) {
  const stages = pipeline.stageIds || [];
  const outputs = pipeline.outputs || [];
  return (
    <ol className="flex flex-wrap items-center gap-x-1 gap-y-1.5 text-xs">
      {stages.map((id, i) => (
        <li key={id} className="flex items-center gap-1">
          {i > 0 && <Icon name="chevron-right" className="h-3 w-3 text-subtle-foreground" />}
          <span className="rounded-md bg-surface-2 px-2 py-0.5 text-muted-foreground">{STAGE_LABEL[id] || humanize(id)}</span>
        </li>
      ))}
      {outputs.length > 0 && (
        <li className="flex items-center gap-1.5 pl-0.5">
          <Icon name="arrow-right" className="h-3 w-3 text-primary dark:text-brand-hi" />
          <span className="font-medium text-foreground">{outputs.map(o => OUTPUT_LABEL[o] || humanize(o)).join(', ')}</span>
        </li>
      )}
    </ol>
  );
}

function KnowledgePipelinesTable() {
  const [pipelines, setPipelines] = useState<KnowledgePipeline[]>([]);
  const [runsByPipeline, setRunsByPipeline] = useState<Record<string, KnowledgePipelineRun[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Presentation only: the pipeline whose runs are open in the side sheet.
  const [openId, setOpenId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await knowledgePipelinesService.list();
      const items = r.items || [];
      setPipelines(items);
      const runsMap: Record<string, KnowledgePipelineRun[]> = {};
      for (const p of items) {
        try {
          const runs = await knowledgePipelinesService.listRuns(p.pipelineId, 5);
          runsMap[p.pipelineId] = runs.items || [];
        } catch {
          runsMap[p.pipelineId] = [];
        }
      }
      setRunsByPipeline(runsMap);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const allRuns = Object.values(runsByPipeline).flat();
  const latest = allRuns.map(runTime).filter(Boolean).sort().pop();
  const failedLatest = pipelines.filter(p => runsByPipeline[p.pipelineId]?.[0]?.success === false).length;
  const open = pipelines.find(p => p.pipelineId === openId) || null;
  const openRuns = open ? runsByPipeline[open.pipelineId] || [] : [];

  const summary = loading && pipelines.length === 0 ? 'Loading the pipeline registry'
    : pipelines.length === 0 ? 'What each pipeline reads, the stages it runs and what it writes.'
    : [
        `${pipelines.length} pipelines`,
        latest && `last run ${timeAgo(latest)}`,
        failedLatest > 0 ? `${failedLatest} failed on the last run` : allRuns.length > 0 && 'all succeeded on the last run',
      ].filter(Boolean).join(' · ');

  return (
    <section>
      <SectionHeader
        title="Stages"
        description={summary}
        actions={
          <Button variant="ghost" size="sm" onClick={load} disabled={loading}>
            <Icon name="refresh" className={loading ? 'animate-spin' : undefined} /> Refresh
          </Button>
        }
      />

      <div className="mt-4">
        {loading && pipelines.length === 0 ? (
          <div className="space-y-px overflow-hidden rounded-xl border border-border" aria-busy="true">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-6 bg-card px-5 py-4">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-4 flex-1" />
                <Skeleton className="h-4 w-24" />
              </div>
            ))}
          </div>
        ) : error ? (
          <InlineError onRetry={load}>The pipeline registry could not be loaded. {error}</InlineError>
        ) : pipelines.length === 0 ? (
          <EmptyState icon="route" title="No pipelines registered" description="Pipelines appear here after the knowledge processor has run for the first time." />
        ) : (
          <Panel flush>
            <ul className="divide-y divide-border">
              {pipelines.map((p, i) => {
                const runs = runsByPipeline[p.pipelineId] || [];
                const last = runs[0];
                const lastTs = runTime(last);
                return (
                  <li key={p.pipelineId} className="rise" style={{ '--i': Math.min(i, 8) } as React.CSSProperties}>
                    <button
                      type="button"
                      onClick={() => setOpenId(p.pipelineId)}
                      className="grid w-full gap-x-6 gap-y-2.5 px-4 py-3.5 text-left transition-colors duration-150 hover:bg-surface-2/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:px-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)_180px] lg:items-center"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-foreground">{p.name || p.pipelineId}</span>
                        <span className="mt-0.5 line-clamp-2 block text-sm text-muted-foreground">{p.description}</span>
                      </span>
                      <StageFlow pipeline={p} />
                      <span className="flex min-w-0 items-center justify-between gap-3 lg:flex-col lg:items-end lg:gap-0.5">
                        {last ? (
                          <>
                            <StatusPill status={runStatus(last)}>{last.success === false ? 'Failed' : 'Succeeded'}</StatusPill>
                            <span className="truncate text-xs text-muted-foreground" title={formatDateTime(lastTs)}>{timeAgo(lastTs) || 'Time not recorded'}</span>
                          </>
                        ) : (
                          <span className="text-xs text-subtle-foreground">Not run yet</span>
                        )}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </Panel>
        )}
      </div>

      <DetailSheet
        open={!!open}
        onOpenChange={(o) => { if (!o) setOpenId(null); }}
        title={open?.name || open?.pipelineId || 'Pipeline'}
        description={open?.description}
        meta={open && openRuns[0] && <StatusPill status={runStatus(openRuns[0])} variant="soft">{openRuns[0].success === false ? 'Last run failed' : 'Last run succeeded'}</StatusPill>}
      >
        {open && (
          <div className="space-y-7">
            <section>
              <SubHeading>Stages</SubHeading>
              <StageFlow pipeline={open} />
            </section>

            <section>
              <SubHeading action={<span className="text-xs text-muted-foreground">Latest {openRuns.length}</span>}>Recent runs</SubHeading>
              {openRuns.length === 0 ? (
                <p className="border-y border-border py-3 text-sm text-muted-foreground">This pipeline has not run yet.</p>
              ) : (
                <ul className="border-t border-border">
                  {openRuns.map((run, i) => {
                    const ts = runTime(run);
                    return (
                      <li key={`${run.jobId || ts}-${i}`} className="border-b border-border py-2.5">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-sm text-foreground">{formatDateTime(ts) || 'Time not recorded'}</span>
                          <StatusPill status={runStatus(run)}>{run.success === false ? 'Failed' : 'Succeeded'}</StatusPill>
                        </div>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {runCounts(run) || 'No counts recorded'}
                          {run.jobId && <> · <span className="mono-id">{run.jobId}</span></>}
                        </p>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section>
              <SubHeading>Technical details</SubHeading>
              <KeyValues
                className="border-t border-border"
                items={[
                  { label: 'Pipeline ID', value: open.pipelineId, mono: true },
                  { label: 'Stage IDs', value: (open.stageIds || []).join(', ') || 'None', mono: true },
                  { label: 'Writes to', value: (open.outputs || []).join(', ') || 'None', mono: true },
                  { label: 'Registry updated', value: formatDateTime(open.updatedAt) || 'Not recorded' },
                ]}
              />
            </section>
          </div>
        )}
      </DetailSheet>
    </section>
  );
}

// ============================================================================
// Knowledge pipeline (object page)
// ============================================================================

const SOURCE_SYSTEMS = [
  { key: 'Salesforce', simKey: 'sfdc', label: 'Salesforce CRM', desc: 'Customers, orders, opportunities' },
  { key: 'Oracle', simKey: 'oracle', label: 'Oracle ERP', desc: 'Finance, receivables, payables, ledger' },
  { key: 'SAP', simKey: 'sap', label: 'SAP S/4HANA', desc: 'Inventory, supply chain, production' },
  { key: 'Google_Drive', simKey: '', label: 'Google Drive', desc: 'Contracts and documents' },
  { key: 'Social_Listening', simKey: '', label: 'Social listening', desc: 'Market signals and sentiment' },
  { key: 'File_Uploads', simKey: '', label: 'File uploads', desc: 'Invoices and lab reports' },
];

function SemanticLayerInner() {
  const [stats, setStats] = useState<CpStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [showKnowledgeData, setShowKnowledgeData] = useState(false);
  const [showIndexReport, setShowIndexReport] = useState(false);
  // Presentation only.
  const [statsError, setStatsError] = useState(false);

  const refreshStats = useCallback(() => {
    setStatsLoading(true);
    apiClient.get<CpStats>('/api/v1/control-plane/stats')
      .then((d) => { setStats(d); setStatsError(false); })
      .catch(() => { setStatsError(true); })
      .finally(() => setStatsLoading(false));
  }, []);

  useEffect(() => { refreshStats(); }, []);

  // Auto-refresh stats every 30 seconds
  useEffect(() => {
    const interval = setInterval(refreshStats, 30000);
    return () => clearInterval(interval);
  }, [refreshStats]);

  const s = stats;
  const firstLoad = statsLoading && !stats;
  const documents = s ? s.onto_schema + s.onto_policy + s.onto_workflow + s.onto_integration : null;
  const metricValue = (n: number | null | undefined) => (firstLoad ? <Skeleton className="h-7 w-20" /> : <AnimatedNumber value={n} placeholder="0" />);

  const breakdown = [
    { label: 'Schema documents', value: s?.onto_schema || 0 },
    { label: 'Policy documents', value: s?.onto_policy || 0 },
    { label: 'Workflow documents', value: s?.onto_workflow || 0 },
    { label: 'Integration documents', value: s?.onto_integration || 0 },
  ];
  const breakdownMax = Math.max(1, ...breakdown.map(b => b.value));

  const entityMap = s?.entities_by_system || {};
  const simMap = s?.simulator_status || {};
  const activeSources = SOURCE_SYSTEMS.filter(src => (entityMap[src.key] || 0) > 0);
  const mapped = s?.mapped_entities || 0;
  const virtual = s?.virtual_only_entities || 0;
  const unmapped = s?.unmapped_entities || 0;
  const mappingTotal = mapped + virtual + unmapped || 1;

  const exportReport = () => {
    const blob = new Blob([JSON.stringify(s, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'knowledge-index-report.json'; a.click();
  };

  return (
    <div className="page space-y-10">
      {/* What the pipeline is, its state and its headline numbers */}
      <section>
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
          <div className="min-w-0 max-w-3xl">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <h2 className="text-xl font-medium tracking-tight text-foreground sm:text-2xl">Knowledge pipeline</h2>
              {s && (
                <StatusPill tone={s.embedding_available ? 'success' : 'warning'} variant="soft">
                  {s.embedding_available ? 'Embedding service active' : 'Embedding service not reachable'}
                </StatusPill>
              )}
            </div>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Reads schemas, mapping rules, policies, workflows and integration rules, then writes the vector index and the knowledge graph the agent reasons over.
              {s && <> It currently holds <span className="num text-foreground">{fmt(s.onto_schema)}</span> schemas, <span className="num text-foreground">{fmt(s.onto_policy)}</span> policies, <span className="num text-foreground">{fmt(s.onto_workflow)}</span> workflows and <span className="num text-foreground">{fmt(s.onto_integration)}</span> integration rules.</>}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="ghost" size="sm" onClick={refreshStats} disabled={statsLoading}>
              <Icon name="refresh" className={statsLoading ? 'animate-spin' : undefined} /> Refresh
            </Button>
          </div>
        </div>

        {statsError && !stats ? (
          <InlineError className="mt-5" onRetry={refreshStats}>The pipeline numbers could not be loaded.</InlineError>
        ) : (
          <MetricStrip
            className="mt-5"
            columns={4}
            items={[
              { label: 'Documents', value: metricValue(documents), hint: 'Across four content types', onClick: () => setShowIndexReport(true) },
              { label: 'Embeddings', value: metricValue(s?.total_embeddings), hint: 'Chunks in the vector index' },
              { label: 'Graph nodes', value: metricValue(s?.graph_nodes), hint: 'Entities, policies, workflows' },
              { label: 'Graph edges', value: metricValue(s?.graph_edges), hint: 'Relationships between them' },
            ]}
          />
        )}
      </section>

      {/* Knowledge Pipeline registry (Phase 3.4): KP# rows + last run timestamps. */}
      <KnowledgePipelinesTable />

      {/* Journey Studio View (Knowledge Processor): run, schedule, job history */}
      <section>
        <SectionHeader title="Run and schedule" description="Start the knowledge processor, set a schedule and follow each run." />
        <div className="mt-4">
          <SemanticRagStudioPanel
            hideBackButton
            hideStatsCards
            hideHeader
            overrideReportButton={
              <Button variant="outline" className="flex items-center gap-2" onClick={() => setShowIndexReport(true)}>
                <Icon name="document" />Index report
              </Button>
            }
            extraHeaderButtons={
              <Button variant="outline" onClick={() => setShowKnowledgeData(true)}>
                <Icon name="database" />Knowledge data
              </Button>
            }
          />
        </div>
      </section>

      {/* Knowledge Data Modal */}
      {showKnowledgeData && (
        <ModalOverlay onClose={() => setShowKnowledgeData(false)}>
          <ModalPanel label="Knowledge data store" className="max-w-[800px]">
            <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border px-5 py-4">
              <div className="min-w-0">
                <h3 className="text-lg font-medium text-foreground">Knowledge data</h3>
                <p className="mt-0.5 text-sm text-muted-foreground">What the pipeline reads: connected sources, the virtual data layer and the knowledge files.</p>
              </div>
              <Button variant="ghost" size="icon-sm" onClick={() => setShowKnowledgeData(false)} aria-label="Close">
                <Icon name="close" />
              </Button>
            </div>
            <div className="scroll-thin min-h-0 flex-1 space-y-8 overflow-y-auto px-5 py-5">
              {/* Connected data sources, from stats */}
              <section>
                <SubHeading>Connected sources</SubHeading>
                {activeSources.length === 0 ? (
                  <p className="border-y border-border py-3 text-sm text-muted-foreground">No source system has entities in the virtual data layer yet.</p>
                ) : (
                  <ul className="border-t border-border">
                    {activeSources.map(src => {
                      const entityCount = entityMap[src.key] || 0;
                      const sim = src.simKey ? simMap[src.simKey] : undefined;
                      return (
                        <li key={src.key} className="flex items-center gap-3 border-b border-border py-2.5">
                          <SystemLogo system={src.key} tile size="sm" />
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-sm font-medium text-foreground">{src.label}</div>
                            <div className="truncate text-xs text-muted-foreground">
                              {src.desc}
                              {sim ? (sim.loaded ? ` · simulator: ${sim.tables} tables, ${sim.rows.toLocaleString()} rows` : ' · simulator not loaded') : ''}
                            </div>
                          </div>
                          <span className="shrink-0 text-sm text-muted-foreground"><span className="num text-foreground">{entityCount}</span> {entityCount === 1 ? 'entity' : 'entities'}</span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </section>

              {/* Virtual entity summary */}
              <section>
                <SubHeading>Virtual data layer</SubHeading>
                <p className="text-sm text-muted-foreground">
                  <span className="num font-medium text-foreground">{s?.virtual_entities || 0}</span> entities across{' '}
                  <span className="num font-medium text-foreground">{Object.keys(entityMap).length}</span> systems,
                  with <span className="num font-medium text-foreground">{s?.mapping_rules_active || 0}</span> active mapping rules.
                </p>
                <div className="mt-3 flex h-1.5 gap-px overflow-hidden rounded-full bg-surface-3" role="img" aria-label={`${mapped} mapped, ${virtual} virtual, ${unmapped} unmapped`}>
                  {mapped > 0 && <div className="grow-x bg-success" style={{ width: `${(mapped / mappingTotal) * 100}%` }} />}
                  {virtual > 0 && <div className="grow-x bg-warning" style={{ width: `${(virtual / mappingTotal) * 100}%`, '--i': 1 } as React.CSSProperties} />}
                  {unmapped > 0 && <div className="grow-x bg-border-strong" style={{ width: `${(unmapped / mappingTotal) * 100}%`, '--i': 2 } as React.CSSProperties} />}
                </div>
                <div className="mt-2.5 flex flex-wrap gap-x-5 gap-y-1">
                  <StatusPill tone="success" className="font-normal"><span className="num">{mapped}</span> mapped</StatusPill>
                  <StatusPill tone="warning" className="font-normal"><span className="num">{virtual}</span> virtual only</StatusPill>
                  <StatusPill tone="neutral" className="font-normal"><span className="num">{unmapped}</span> unmapped</StatusPill>
                </div>
                <KeyValues
                  className="mt-4 border-t border-border"
                  columns={2}
                  items={[
                    { label: 'Schema entities', value: <span className="num">{fmt(s?.virtual_entities)}</span> },
                    { label: 'Mapped entities', value: <span className="num">{fmt(s?.mapped_entities)}</span> },
                    { label: 'Active mapping rules', value: <span className="num">{fmt(s?.mapping_rules_active)}</span> },
                    { label: 'Policies', value: <span className="num">{fmt(s?.onto_policy)}</span> },
                    { label: 'Workflows', value: <span className="num">{fmt(s?.onto_workflow)}</span> },
                    { label: 'Integration rules', value: <span className="num">{fmt(s?.onto_integration)}</span> },
                  ]}
                />
              </section>

              {/* Onto Data Manager */}
              <section>
                <SubHeading>Knowledge files</SubHeading>
                <OntoDataManager />
              </section>
            </div>
          </ModalPanel>
        </ModalOverlay>
      )}

      {/* Index Report Modal */}
      {showIndexReport && (
        <ModalOverlay onClose={() => setShowIndexReport(false)}>
          <ModalPanel label="Knowledge index report" className="max-w-[600px]">
            <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border px-5 py-4">
              <div className="min-w-0">
                <h3 className="text-lg font-medium text-foreground">Index report</h3>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  {s
                    ? <>The index holds <span className="num text-foreground">{fmt(documents)}</span> documents as <span className="num text-foreground">{fmt(s.total_embeddings)}</span> embeddings.</>
                    : 'The index numbers are not available yet.'}
                </p>
              </div>
              <Button variant="ghost" size="icon-sm" onClick={() => setShowIndexReport(false)} aria-label="Close">
                <Icon name="close" />
              </Button>
            </div>
            <div className="scroll-thin min-h-0 flex-1 space-y-7 overflow-y-auto px-5 py-5">
              <MetricStrip
                columns={2}
                items={[
                  { label: 'Total embeddings', value: s ? fmt(s.total_embeddings) : 'None' },
                  { label: 'Graph nodes', value: s ? fmt(s.graph_nodes) : 'None' },
                ]}
              />
              <section>
                <SubHeading>Index breakdown</SubHeading>
                <ul className="border-t border-border">
                  {breakdown.map((item, i) => (
                    <li key={item.label} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] items-center gap-4 border-b border-border py-2.5 text-sm">
                      <span className="truncate text-foreground">{item.label}</span>
                      <ShareBar value={item.value} max={breakdownMax} index={i} />
                      <span className="num w-14 text-right font-medium text-foreground">{item.value.toLocaleString()}</span>
                    </li>
                  ))}
                </ul>
              </section>
              <section>
                <SubHeading>Graph database</SubHeading>
                <KeyValues
                  className="border-t border-border"
                  items={[
                    { label: 'Nodes', value: <span className="num">{s ? fmt(s.graph_nodes) : 'None'}</span> },
                    { label: 'Edges', value: <span className="num">{s ? fmt(s.graph_edges) : 'None'}</span> },
                    { label: 'Embedding service', value: <StatusPill tone={s?.embedding_available ? 'success' : 'warning'}>{s?.embedding_available ? 'Active' : 'Inactive'}</StatusPill> },
                  ]}
                />
              </section>
            </div>
            <div className="flex shrink-0 items-center justify-end gap-2 border-t border-border px-5 py-3">
              <Button variant="outline" size="sm" onClick={exportReport} disabled={!s}>
                <Icon name="download" /> Export JSON
              </Button>
              <Button size="sm" onClick={() => setShowIndexReport(false)}>Done</Button>
            </div>
          </ModalPanel>
        </ModalOverlay>
      )}
    </div>
  );
}

// ============================================================================
// Knowledge index: report first, then the document browser
// ============================================================================

function docDisplayName(doc: OntoDocument): string {
  const meta = doc.metadata || {};
  if (meta.object_name) return meta.object_name;
  return doc.source_id.replace(/_V1_0$/, '').replace(/^[^_]+_/, '').replace(/_/g, ' ');
}

const docSystem = (doc: OntoDocument): string => doc.metadata?.source_system || doc.metadata?.system || '';

type IndexView = 'overview' | 'documents';
type DocTab = 'content' | 'fields';

function KnowledgeFormationInner() {
  const [category, setCategory] = useState('onto_schema');
  const [query, setQuery] = useState('');
  const [documents, setDocuments] = useState<OntoDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [pageSize] = useState(50);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<OntoDocument | null>(null);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [lastIndexedAt, setLastIndexedAt] = useState<string | null>(null);
  const [showMetadata, setShowMetadata] = useState(false);

  // Presentation only.
  const [view, setView] = useState<IndexView>('overview');
  const [docTab, setDocTab] = useState<DocTab>('content');
  const [totals, setTotals] = useState<{ embeddings: number; documents: number } | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [docsError, setDocsError] = useState<string | null>(null);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [filesOpen, setFilesOpen] = useState(false);

  const loadStats = useCallback(() => {
    setStatsLoading(true);
    setStatsError(null);
    ontoApi.getStats().then((d: OntoStats) => {
      setStats(d.by_content_type || {});
      setLastIndexedAt(d.last_indexed_at || null);
      setTotals({ embeddings: d.total_embeddings || 0, documents: d.onto_documents || 0 });
    }).catch((e: any) => {
      setStatsError(e?.message || 'The index status could not be loaded.');
    }).finally(() => setStatsLoading(false));
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const fetchDocuments = useCallback(async (cat: string, off: number, q: string) => {
    setLoading(true);
    setDocsError(null);
    try {
      const data = await ontoApi.listDocuments({
        content_type: cat,
        offset: off,
        limit: pageSize,
        q: q || undefined,
      });
      setDocuments(data.documents || []);
      setTotal(data.total || 0);
    } catch (e: any) {
      setDocuments([]);
      setTotal(0);
      setDocsError(e?.message || 'The documents could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  useEffect(() => {
    setOffset(0);
    setSelected(null);
    fetchDocuments(category, 0, query);
  }, [category]);

  useEffect(() => {
    fetchDocuments(category, offset, query);
  }, [offset]);

  const handleSearch = () => {
    setOffset(0);
    setSelected(null);
    fetchDocuments(category, 0, query);
  };

  // The detail is never blank: show the first document of the page.
  useEffect(() => {
    if (documents.length === 0) return;
    if (!selected || !documents.some(d => d.source_id === selected.source_id)) {
      setSelected(documents[0]);
      setDocTab('content');
    }
  }, [documents, selected]);

  const onQueryChange = (v: string) => {
    setQuery(v);
    // Clearing the box shows everything again without a second step.
    if (v === '' && query !== '') {
      setOffset(0);
      setSelected(null);
      fetchDocuments(category, 0, '');
    }
  };

  const selectDocument = (doc: OntoDocument) => {
    setSelected(doc);
    setDocTab('content');
    setShowMetadata(false);
    setBrowseOpen(false);
  };

  const browseType = (key: string) => {
    setCategory(key);
    setView('documents');
  };

  const onBuildComplete = () => {
    loadStats();
    fetchDocuments(category, offset, query);
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.floor(offset / pageSize) + 1;

  const typeKeys = [...CONTENT_TYPES.map(t => t.key), ...Object.keys(stats).filter(k => !CATEGORY_LABELS[k])];
  const typeRows = typeKeys.map(key => {
    const known = CONTENT_TYPES.find(t => t.key === key);
    return { key, plural: known?.plural || humanize(key), description: known?.description || 'Other indexed content', count: stats[key] || 0 };
  });
  const documentTotal = typeRows.reduce((n, r) => n + r.count, 0) || totals?.documents || 0;
  const typesWithContent = typeRows.filter(r => r.count > 0).length;
  const maxCount = Math.max(1, ...typeRows.map(r => r.count));
  const isBuilt = documentTotal > 0;
  const firstStats = statsLoading && !totals;

  /* -------------------------------------------------------- document list */

  const list = (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 space-y-2.5 border-b border-border p-3">
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="h-8" aria-label="Content type"><SelectValue /></SelectTrigger>
          <SelectContent>
            {typeRows.map(r => (
              <SelectItem key={r.key} value={r.key}>
                {r.plural} <span className="num text-muted-foreground">{r.count}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <SearchInput
          value={query}
          onChange={onQueryChange}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
          placeholder="Search, then press Enter"
          className="sm:w-full"
        />
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {loading && documents.length === 0 ? (
          <div className="space-y-3 p-4" aria-busy="true">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-4 w-3/5" />
                <Skeleton className="h-3 w-2/5" />
              </div>
            ))}
          </div>
        ) : docsError ? (
          <div className="p-3"><InlineError onRetry={() => fetchDocuments(category, offset, query)}>{docsError}</InlineError></div>
        ) : documents.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-muted-foreground">
            {query ? 'No documents match this search.' : `No ${typePlural(category).toLowerCase()} are indexed yet.`}
          </p>
        ) : (
          <ul className={cn('p-2 transition-opacity duration-150', loading && 'opacity-60')}>
            {documents.map((doc, i) => {
              const on = selected?.source_id === doc.source_id;
              const system = docSystem(doc);
              const domain = doc.metadata?.domain || '';
              return (
                <li key={doc.source_id} className="rise" style={{ '--i': Math.min(i, 10) } as React.CSSProperties}>
                  <button
                    type="button"
                    onClick={() => selectDocument(doc)}
                    aria-current={on ? 'true' : undefined}
                    className={cn(
                      'flex w-full items-start gap-2.5 rounded-md px-2 py-2 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      on ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground',
                    )}
                  >
                    {system && <SystemLogo system={system} size="xs" className="mt-0.5" />}
                    <span className="min-w-0 flex-1">
                      <span className={cn('block truncate text-sm text-foreground', on && 'font-medium')}>{docDisplayName(doc)}</span>
                      <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                        {[system && systemName(system), domain].filter(Boolean).join(' · ') || CATEGORY_LABELS[doc.content_type] || humanize(doc.content_type)}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="flex shrink-0 items-center justify-between gap-2 border-t border-border px-3 py-2 text-xs text-muted-foreground">
          <span className="num truncate">{offset + 1} to {Math.min(offset + pageSize, total)} of {total}</span>
          <div className="flex shrink-0 items-center gap-1">
            <Button variant="outline" size="icon-sm" className="h-7 w-7" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))} aria-label="Previous page">
              <Icon name="chevron-left" className="h-3.5 w-3.5" />
            </Button>
            <span className="num px-1">{currentPage} / {totalPages}</span>
            <Button variant="outline" size="icon-sm" className="h-7 w-7" disabled={offset + pageSize >= total} onClick={() => setOffset(offset + pageSize)} aria-label="Next page">
              <Icon name="chevron-right" className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );

  /* ------------------------------------------------------ document detail */

  const keyFields: any[] = selected?.metadata?.key_field_details || [];
  const selectedSystem = selected ? docSystem(selected) : '';

  const detail = !selected ? (
    loading ? (
      <div className="space-y-4 p-5 sm:p-6" aria-busy="true">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-7 w-64 max-w-full" />
        <Skeleton className="h-4 w-80 max-w-full" />
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-4 w-full max-w-3xl" />)}
      </div>
    ) : docsError ? (
      <div className="p-5 sm:p-6"><InlineError onRetry={() => fetchDocuments(category, offset, query)}>{docsError}</InlineError></div>
    ) : (
      <div className="p-5 sm:p-6">
        <EmptyState
          icon="document"
          title={query ? 'No documents match this search' : `No ${typePlural(category).toLowerCase()} indexed yet`}
          description={query ? 'Clear the search or choose another content type.' : 'Build the index from the Overview to fill this content type.'}
          action={!query && <Button variant="outline" onClick={() => setView('overview')}>Go to overview</Button>}
        />
      </div>
    )
  ) : (
    <Tabs value={docTab} onValueChange={(v) => setDocTab(v as DocTab)} className="flex min-h-0 flex-1 flex-col">
      <header className="shrink-0 px-4 pt-5 sm:px-6">
        <p className="text-xs text-muted-foreground">{CATEGORY_LABELS[selected.content_type] || humanize(selected.content_type)} document</p>
        <h2 className="mt-0.5 break-words text-xl font-medium tracking-tight text-foreground sm:text-2xl">{docDisplayName(selected)}</h2>
        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
          {selectedSystem && (
            <>
              <span className="inline-flex items-center gap-1.5 text-foreground"><SystemLogo system={selectedSystem} size="sm" /> {systemName(selectedSystem)}</span>
              <span aria-hidden="true">·</span>
            </>
          )}
          {selected.metadata?.domain && <><span>{selected.metadata.domain}</span><span aria-hidden="true">·</span></>}
          {selected.metadata?.scor_process && <><span>SCOR: {selected.metadata.scor_process}</span><span aria-hidden="true">·</span></>}
          <span>{selected.updated_at ? `Indexed ${formatDateTime(selected.updated_at)}` : 'Index time not recorded'}</span>
        </div>
        <TabsList variant="line" className="mt-4">
          <TabsTrigger value="content">Content</TabsTrigger>
          <TabsTrigger value="fields">Key fields <span className="num text-xs font-normal text-subtle-foreground">{keyFields.length}</span></TabsTrigger>
        </TabsList>
      </header>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
        <TabsContent value="content" className="mt-0">
          <div className="max-w-3xl">
            <p className="whitespace-pre-wrap break-words text-sm leading-6 text-foreground">{selected.content}</p>

            {/* Metadata (collapsible) */}
            <div className="mt-8 border-t border-border pt-4">
              <button
                type="button"
                onClick={() => setShowMetadata(!showMetadata)}
                aria-expanded={showMetadata}
                className="inline-flex items-center gap-1.5 rounded-sm text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Icon name={showMetadata ? 'chevron-down' : 'chevron-right'} className="h-3.5 w-3.5" />
                Technical details
              </button>
              {showMetadata && (
                <div className="mt-3 space-y-3">
                  <KeyValues items={[{ label: 'Source ID', value: selected.source_id, mono: true }, { label: 'Content type', value: selected.content_type, mono: true }]} />
                  {selected.metadata && Object.keys(selected.metadata).length > 0 && (
                    <CodeBlock maxHeight={300}>{JSON.stringify(selected.metadata, null, 2)}</CodeBlock>
                  )}
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="fields" className="mt-0">
          {keyFields.length === 0 ? (
            <EmptyState icon="table" title="No key fields recorded" description="This document does not list key fields. Schema documents usually do." />
          ) : (
            <TableShell className="max-w-4xl">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Field</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Meaning</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {keyFields.map((f: any, i: number) => (
                    <TableRow key={i}>
                      <TableCell className="py-2.5 font-mono text-xs text-foreground">{f.name}</TableCell>
                      <TableCell className="py-2.5 font-mono text-xs text-muted-foreground">{f.data_type || <span className="text-subtle-foreground">Not set</span>}</TableCell>
                      <TableCell className="py-2.5 text-sm text-muted-foreground">{f.semantic || <span className="text-subtle-foreground">Not described</span>}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableShell>
          )}
        </TabsContent>
      </div>
    </Tabs>
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Verdict, then the two views */}
      <div className="shrink-0 border-b border-border px-4 pt-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <h2 className="text-lg font-medium tracking-tight text-foreground">Knowledge index</h2>
              {!firstStats && !statsError && (
                <StatusPill tone={isBuilt ? 'success' : 'warning'} variant="soft">{isBuilt ? 'Built' : 'Not built yet'}</StatusPill>
              )}
            </div>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {firstStats ? 'Checking the index' : statsError ? 'The index status is not available.' : isBuilt ? (
                <>
                  <span className="num text-foreground">{fmt(documentTotal)}</span> documents in <span className="num text-foreground">{typesWithContent}</span> content types
                  {lastIndexedAt && <>, last indexed {formatDateTime(lastIndexedAt)}</>}.
                </>
              ) : 'Nothing is indexed yet. Build the index so the agent can search enterprise knowledge.'}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setFilesOpen(true)}>
            <Icon name="folder" /> Knowledge files
          </Button>
        </div>
        <Tabs value={view} onValueChange={(v) => setView(v as IndexView)}>
          <TabsList variant="line" className="mt-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="documents">Documents <span className="num text-xs font-normal text-subtle-foreground">{fmt(documentTotal)}</span></TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Overview. Kept mounted so a running build keeps its progress. */}
      <div className={cn('scroll-thin min-h-0 flex-1 overflow-y-auto', view !== 'overview' && 'hidden')}>
        <div className="mx-auto w-full max-w-[1440px] space-y-6 px-4 py-6 sm:px-6 lg:px-8">
          {statsError && <InlineError onRetry={loadStats}>{statsError}</InlineError>}

          <MetricStrip
            columns={4}
            items={[
              { label: 'Documents', value: firstStats ? <Skeleton className="h-7 w-16" /> : <AnimatedNumber value={documentTotal} />, hint: 'Searchable by the agent' },
              { label: 'Embeddings', value: firstStats ? <Skeleton className="h-7 w-20" /> : <AnimatedNumber value={totals?.embeddings ?? 0} />, hint: 'Chunks in the vector index' },
              { label: 'Content types', value: firstStats ? <Skeleton className="h-7 w-10" /> : <>{typesWithContent} <span className="text-base font-normal text-muted-foreground">of {typeRows.length}</span></>, hint: typesWithContent === typeRows.length ? 'All have content' : 'Some are empty', tone: !firstStats && typesWithContent < typeRows.length ? 'warning' : undefined },
              { label: 'Last indexed', value: firstStats ? <Skeleton className="h-7 w-24" /> : (timeAgo(lastIndexedAt) || 'Never'), hint: formatDateTime(lastIndexedAt) || 'No build recorded' },
            ]}
          />

          <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
            <section className="min-w-0">
              <SectionHeader title="Content types" description="What is in the index, by kind of knowledge." />
              <TableShell className="mt-3">
                <Table className="min-w-[560px]">
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Documents</TableHead>
                      <TableHead className="w-[22%]">Share</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-10"><span className="sr-only">Actions</span></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {typeRows.map((r, i) => (
                      <TableRow key={r.key} className="group cursor-pointer" onClick={() => browseType(r.key)}>
                        <TableCell className="py-3">
                          <div className="text-sm font-medium text-foreground">{r.plural}</div>
                          <div className="text-xs text-muted-foreground">{r.description}</div>
                        </TableCell>
                        <TableCell className="num py-3 text-right text-sm text-foreground">
                          {firstStats ? <Skeleton className="ml-auto h-4 w-10" /> : fmt(r.count)}
                        </TableCell>
                        <TableCell className="py-3">{!firstStats && <ShareBar value={r.count} max={maxCount} index={i} />}</TableCell>
                        <TableCell className="py-3">
                          {firstStats ? <Skeleton className="h-4 w-16" /> : <StatusPill tone={r.count > 0 ? 'success' : 'warning'}>{r.count > 0 ? 'Indexed' : 'Empty'}</StatusPill>}
                        </TableCell>
                        <TableCell className="py-3 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => { e.stopPropagation(); browseType(r.key); }}
                            aria-label={`Browse ${r.plural.toLowerCase()}`}
                            className="text-muted-foreground lg:opacity-0 lg:focus-visible:opacity-100 lg:group-hover:opacity-100"
                          >
                            Browse <Icon name="arrow-right" className="h-3.5 w-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableShell>
            </section>

            <BuildIndexPanel built={isBuilt} onComplete={onBuildComplete} />
          </div>
        </div>
      </div>

      {/* Documents: list and detail */}
      <div className={cn('min-h-0 flex-1 grid-rows-[minmax(0,1fr)] lg:grid-cols-[300px_minmax(0,1fr)]', view === 'documents' ? 'grid' : 'hidden')}>
        <aside className="hidden min-h-0 border-r border-border bg-sidebar/40 lg:block" aria-label="Indexed documents">{list}</aside>

        <Sheet open={browseOpen} onOpenChange={setBrowseOpen}>
          <SheetContent side="left" className="flex w-full flex-col gap-0 p-0 sm:max-w-sm">
            <div className="border-b border-border px-4 pb-3 pt-4 pr-12">
              <SheetTitle className="text-md font-medium">Indexed documents</SheetTitle>
              <SheetDescription className="sr-only">Choose a document</SheetDescription>
            </div>
            <div className="min-h-0 flex-1">{list}</div>
          </SheetContent>
        </Sheet>

        <div className="flex min-h-0 min-w-0 flex-col">
          <div className="shrink-0 border-b border-border px-4 py-2 lg:hidden">
            <Button variant="outline" size="sm" className="w-full justify-between" onClick={() => setBrowseOpen(true)}>
              <span className="flex min-w-0 items-center gap-2">
                <Icon name="list" className="h-3.5 w-3.5" />
                <span className="truncate">{selected ? docDisplayName(selected) : 'Browse documents'}</span>
              </span>
              <span className="flex items-center gap-1.5 font-normal text-muted-foreground">
                <span className="num">{total}</span>
                <Icon name="chevron-down" className="h-3.5 w-3.5" />
              </span>
            </Button>
          </div>
          {detail}
        </div>
      </div>

      <DetailSheet
        open={filesOpen}
        onOpenChange={setFilesOpen}
        title="Knowledge files"
        description="The policy, workflow and integration files the index is built from. Rebuild the index after you change them."
        wide
      >
        <OntoDataManager />
      </DetailSheet>
    </div>
  );
}

// ============================================================================
// Policy Builder / Workflow Rules / Integration Rules (Part 2A)
// ============================================================================

import { KnowledgeEditor, PolicyPreview, WorkflowPreview, IntegrationPreview } from '@/components/control-plane/KnowledgeEditor';
import { POLICY_TEMPLATES, WORKFLOW_TEMPLATES, INTEGRATION_TEMPLATES } from '@/components/control-plane/templates';
import PolicyFormBuilder from '@/components/control-plane/PolicyFormBuilder';
import WorkflowFormBuilder from '@/components/control-plane/WorkflowFormBuilder';
import IntegrationFormBuilder from '@/components/control-plane/IntegrationFormBuilder';

function PolicyBuilderInner() {
  return (
    <KnowledgeEditor
      category="policies"
      fileExtension=".md"
      templates={POLICY_TEMPLATES}
      title="Policies"
      description="Business policies the agent must follow: limits, approval thresholds and restrictions."
      renderPreview={(content) => <PolicyPreview content={content} />}
      formBuilder={({ content, onChange }) => <PolicyFormBuilder content={content} onChange={onChange} />}
    />
  );
}

function WorkflowRulesInner() {
  return (
    <KnowledgeEditor
      category="workflows"
      fileExtension=".yaml"
      templates={WORKFLOW_TEMPLATES}
      title="Workflows"
      description="Process flows that span Salesforce, Oracle ERP, SAP and Google Drive, step by step."
      renderPreview={(content) => <WorkflowPreview content={content} />}
      formBuilder={({ content, onChange }) => <WorkflowFormBuilder content={content} onChange={onChange} />}
    />
  );
}

function IntegrationRulesInner() {
  return (
    <KnowledgeEditor
      category="integrations"
      fileExtension=".yaml"
      templates={INTEGRATION_TEMPLATES}
      title="Integration rules"
      description="Field-level sync rules between enterprise systems: what moves, in which direction and how often."
      renderPreview={(content) => <IntegrationPreview content={content} />}
      formBuilder={({ content, onChange }) => <IntegrationFormBuilder content={content} onChange={onChange} />}
    />
  );
}
