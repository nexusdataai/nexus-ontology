import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Icon } from '@/components/ds/Icon';
import { CodeBlock, InlineError, KeyValues, SearchInput, StatusPill, SubHeading, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import {
  reactToolsDiagnosticsService,
  type RegistryReport,
  type RegistryToolRow,
  type CanaryReport,
  type CanaryResult,
} from '@/services/reactToolsDiagnosticsService';
import { cn } from '@/lib/utils';
import { RiskPill, ToolSystem, riskLabel } from '@/components/reasoning/toolMeta';
import { RegistryTable } from './RegistryTable';
import { FacetFilters } from './FacetFilters';
import { DetailDrawer } from './DetailDrawer';
import { ExecuteDrawer, adapterFromTool } from './ExecuteDrawer';
import type {
  RegistryColumn, FacetDescriptor, FacetState, ExecuteAdapter,
} from './types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function riskTone(risk: string): 'ok' | 'warn' | 'err' {
  return risk === 'read_only' ? 'ok' : risk === 'high_risk_write' ? 'err' : 'warn';
}

const sentence = (s: string) => {
  const t = String(s || '').replace(/[_-]+/g, ' ').trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : '';
};

const CHECK_LABEL: Record<string, string> = { pass: 'Passed', fail: 'Failed', skip: 'Skipped' };

function toolKindOf(row: RegistryToolRow): string {
  // Mirror Tool.effective_tool_kind() server-side heuristic so the UI
  // can group tools by kind even when explicit field is absent.
  const tk = (row as any).tool_kind;
  if (tk) return String(tk);
  if (row.connector_api) return 'mutate';
  if (row.risk_level === 'read_only') return 'read';
  return 'analyze';
}

function filterToolText(t: RegistryToolRow, q: string): boolean {
  if (!q) return true;
  const needle = q.toLowerCase();
  return (
    t.tool_id.toLowerCase().includes(needle)
    || (t.description || '').toLowerCase().includes(needle)
    || t.group.toLowerCase().includes(needle)
    || (t.connector_api || '').toLowerCase().includes(needle)
    || (t.tags || []).some((tag) => tag.toLowerCase().includes(needle))
  );
}

function applyFacets(rows: RegistryToolRow[], facets: FacetState): RegistryToolRow[] {
  const groupSel = facets.group;
  const riskSel = facets.risk_level;
  const kindSel = facets.tool_kind;
  const yamlSel = facets.yaml_present;
  const canarySel = facets.has_canary;
  const approvalSel = facets.requires_approval;

  return rows.filter((r) => {
    if (groupSel?.size && !groupSel.has(r.group)) return false;
    if (riskSel?.size && !riskSel.has(r.risk_level)) return false;
    if (kindSel?.size && !kindSel.has(toolKindOf(r))) return false;
    if (yamlSel?.size && !yamlSel.has(r.yaml_present ? 'yes' : 'no')) return false;
    if (canarySel?.size && !canarySel.has(r.has_canary ? 'yes' : 'no')) return false;
    if (approvalSel?.size && !approvalSel.has(r.requires_approval ? 'yes' : 'no')) return false;
    return true;
  });
}

function bucketize<T>(rows: T[], key: (r: T) => string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const r of rows) {
    const k = key(r);
    out[k] = (out[k] || 0) + 1;
  }
  return out;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ToolsRegistryBrowser() {
  const [report, setReport] = useState<RegistryReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [facets, setFacets] = useState<FacetState>({});
  const [selectedToolId, setSelectedToolId] = useState<string | null>(null);
  const [executeAdapter, setExecuteAdapter] = useState<ExecuteAdapter | null>(null);
  const [canaryRunning, setCanaryRunning] = useState(false);
  const [canaryByTool, setCanaryByTool] = useState<Record<string, CanaryResult>>({});
  // Local view state: the filter sheet on small screens.
  const [filtersOpen, setFiltersOpen] = useState(false);

  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // ----- load -----

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await reactToolsDiagnosticsService.registry();
      setReport(r);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // ----- ?focus=<tool_id> deep-link -----

  useEffect(() => {
    const focus = searchParams.get('focus');
    if (!focus || !report) return;
    if (report.tools.some((t) => t.tool_id === focus)) {
      setSelectedToolId(focus);
    }
  }, [report, searchParams]);

  const closeDrawer = () => {
    setSelectedToolId(null);
    if (searchParams.get('focus')) {
      const next = new URLSearchParams(searchParams);
      next.delete('focus');
      setSearchParams(next, { replace: true });
    }
  };

  // ----- derived data -----

  const rows = report?.tools || [];
  const filtered = useMemo(() => {
    const f = applyFacets(rows, facets);
    if (!search.trim()) return f;
    return f.filter((r) => filterToolText(r, search));
  }, [rows, facets, search]);

  const selectedTool = useMemo(
    () => rows.find((t) => t.tool_id === selectedToolId) || null,
    [rows, selectedToolId],
  );

  // Facet options + counts (recomputed over the BASE rows so users can
  // see how many rows each option would match).
  const facetDescriptors = useMemo<FacetDescriptor[]>(() => {
    const byGroup = bucketize(rows, (r) => r.group);
    const byRisk = bucketize(rows, (r) => r.risk_level);
    const byKind = bucketize(rows, (r) => toolKindOf(r));
    return [
      {
        key: 'risk_level',
        label: 'Risk',
        options: ['read_only', 'low_risk_write', 'high_risk_write']
          .filter((k) => byRisk[k])
          .map((k) => ({ value: k, label: riskLabel(k), count: byRisk[k] })),
      },
      {
        key: 'group',
        label: 'Group',
        options: Object.keys(byGroup).sort()
          .map((k) => ({ value: k, label: sentence(k), count: byGroup[k] })),
      },
      {
        key: 'tool_kind',
        label: 'Kind',
        options: ['read', 'analyze', 'decide', 'mutate', 'notify']
          .filter((k) => byKind[k])
          .map((k) => ({ value: k, label: sentence(k), count: byKind[k] })),
      },
      {
        key: 'yaml_present',
        label: 'Documentation',
        options: [
          { value: 'yes', label: 'Documented', count: rows.filter((r) => r.yaml_present).length },
          { value: 'no', label: 'Missing', count: rows.filter((r) => !r.yaml_present).length },
        ],
      },
      {
        key: 'has_canary',
        label: 'Health check',
        options: [
          { value: 'yes', label: 'Set up', count: rows.filter((r) => r.has_canary).length },
          { value: 'no', label: 'Not set up', count: rows.filter((r) => !r.has_canary).length },
        ],
      },
      {
        key: 'requires_approval',
        label: 'Approval',
        options: [
          { value: 'yes', label: 'Required', count: rows.filter((r) => r.requires_approval).length },
          { value: 'no', label: 'Not needed', count: rows.filter((r) => !r.requires_approval).length },
        ],
      },
    ];
  }, [rows]);

  // Headline figures, written as a sentence in the header.
  const summary = useMemo(() => {
    if (!report) return null;
    const orphans = report.totals.registry_only_orphans + report.totals.yaml_only_orphans;
    return {
      total: report.totals.registered_tools,
      documented: rows.filter((r) => r.yaml_present).length,
      withCheck: rows.filter((r) => r.has_canary).length,
      orphans,
    };
  }, [report, rows]);

  const checks = useMemo(() => {
    const all = Object.values(canaryByTool);
    return { run: all.length, pass: all.filter(c => c.status === 'pass').length, fail: all.filter(c => c.status === 'fail').length, skip: all.filter(c => c.status === 'skip').length };
  }, [canaryByTool]);

  const openConnectorApi = (api: string) =>
    navigate(`/ai-stack/data-plane?tab=connector-registry&focus=${encodeURIComponent(api)}`);

  // ----- columns -----

  const columns: RegistryColumn<RegistryToolRow>[] = [
    {
      key: 'tool_id', label: 'Tool',
      className: 'max-w-[380px]',
      sortBy: (r) => r.tool_id,
      render: (r) => (
        <div className="min-w-0">
          <div className="truncate font-mono text-sm font-medium text-foreground">{r.tool_id}</div>
          <div className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{r.description}</div>
        </div>
      ),
    },
    {
      key: 'connector_api', label: 'Reaches',
      sortBy: (r) => r.connector_api || '',
      render: (r) => r.connector_api
        ? (
          <div className="min-w-0">
            <ToolSystem api={r.connector_api} />
            <button
              type="button"
              title="Open this connector API"
              className="mt-0.5 block max-w-[220px] truncate rounded font-mono text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-brand-hi"
              onClick={(e) => { e.stopPropagation(); openConnectorApi(r.connector_api!); }}
            >
              {r.connector_api}
            </button>
          </div>
        )
        : <ToolSystem api={null} />,
    },
    {
      key: 'group', label: 'Group',
      sortBy: (r) => r.group,
      render: (r) => <span className="whitespace-nowrap text-muted-foreground">{sentence(r.group)}</span>,
    },
    {
      key: 'tool_kind', label: 'Kind',
      sortBy: (r) => toolKindOf(r),
      render: (r) => <span className="text-muted-foreground">{sentence(toolKindOf(r))}</span>,
    },
    {
      key: 'risk_level', label: 'Risk',
      sortBy: (r) => r.risk_level,
      render: (r) => (
        <div>
          <RiskPill risk={r.risk_level} />
          {r.requires_approval && <div className="mt-0.5 whitespace-nowrap text-xs text-muted-foreground">Needs approval</div>}
        </div>
      ),
    },
    {
      key: 'flags', label: 'Readiness',
      render: (r) => (
        r.yaml_present && r.has_canary
          ? <span className="text-muted-foreground">Complete</span>
          : (
            <div className="flex flex-col gap-0.5">
              {!r.yaml_present && <StatusPill tone="warning">No documentation</StatusPill>}
              {!r.has_canary && <StatusPill tone="warning">No health check</StatusPill>}
            </div>
          )
      ),
    },
    {
      key: 'last_check', label: 'Last check',
      sortBy: (r) => canaryByTool[r.tool_id]?.status || '',
      render: (r) => {
        const c = canaryByTool[r.tool_id];
        if (canaryRunning && !c) return <Skeleton className="h-4 w-16" />;
        if (!c) return <span className="text-subtle-foreground">Not run</span>;
        return (
          <div className="whitespace-nowrap">
            <StatusPill status={c.status} tone={c.status === 'skip' ? 'neutral' : undefined}>{CHECK_LABEL[c.status] || c.status}</StatusPill>
            {c.status !== 'skip' && c.duration_ms != null && <div className="num mt-0.5 text-xs text-muted-foreground">{c.duration_ms} ms</div>}
          </div>
        );
      },
    },
  ];

  // ----- actions -----

  const runCanarySlice = async () => {
    setCanaryRunning(true);
    try {
      const tool_ids = filtered.map((r) => r.tool_id);
      const rep: CanaryReport = await reactToolsDiagnosticsService.runAll({ tool_ids });
      const map: Record<string, CanaryResult> = {};
      for (const r of rep.results) map[r.tool_id] = r;
      setCanaryByTool((prev) => ({ ...prev, ...map }));
    } catch (e: any) {
      setError(`The health check run failed: ${e?.message || e}`);
    } finally {
      setCanaryRunning(false);
    }
  };

  const openRun = (tool: RegistryToolRow) => {
    const canary = canaryByTool[tool.tool_id];
    setExecuteAdapter(adapterFromTool({
      toolName: tool.tool_id,
      displayName: tool.display_name,
      paramsSchema: tool.parameters,
      defaultParams: canary?.params || {},
      riskLevel: tool.risk_level,
      connectorApi: tool.connector_api,
    }));
  };

  // ----- detail drawer tabs -----

  const drawerTabs = useMemo(() => [
    {
      key: 'overview', label: 'Overview',
      render: (t: RegistryToolRow) => (
        <KeyValues items={[
          { label: 'Reaches', value: <ToolSystem api={t.connector_api} className="justify-end" /> },
          ...(t.connector_api ? [{
            label: 'Connector API',
            value: (
              <button type="button" className="rounded font-mono text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-brand-hi" onClick={() => openConnectorApi(t.connector_api!)}>
                {t.connector_api}
              </button>
            ),
          }] : []),
          { label: 'Risk', value: <RiskPill risk={t.risk_level} /> },
          { label: 'Approval', value: t.requires_approval ? 'Required before it runs' : 'Not needed' },
          { label: 'Group', value: sentence(t.group) },
          { label: 'Kind', value: sentence(toolKindOf(t)) },
          { label: 'Results cached', value: t.cacheable ? 'Yes' : 'No' },
          { label: 'Used by playbooks', value: <span className="num">{t.use_case_refs}</span> },
          ...(t.tags && t.tags.length > 0 ? [{ label: 'Tags', value: t.tags.join(', ') }] : []),
        ]} />
      ),
    },
    {
      key: 'parameters', label: 'Parameters',
      render: (t: RegistryToolRow) => {
        const props = Object.entries((t.parameters?.properties || {}) as Record<string, { type?: string; description?: string }>);
        const required = new Set<string>(t.parameters?.required || []);
        return (
          <div className="space-y-6">
            {props.length === 0 ? (
              <p className="text-sm text-muted-foreground">This tool takes no parameters.</p>
            ) : (
              <ul className="divide-y divide-border">
                {props.map(([name, p]) => (
                  <li key={name} className="py-2.5">
                    <div className="flex flex-wrap items-baseline gap-x-2.5">
                      <span className="font-mono text-sm text-foreground">{name}</span>
                      <span className="text-xs text-muted-foreground">{p?.type || 'any'}{required.has(name) ? ', required' : ''}</span>
                    </div>
                    {p?.description && <p className="mt-0.5 text-sm text-muted-foreground">{p.description}</p>}
                  </li>
                ))}
              </ul>
            )}
            <section>
              <SubHeading>Schema</SubHeading>
              <CodeBlock maxHeight={320}>{JSON.stringify(t.parameters || {}, null, 2)}</CodeBlock>
            </section>
          </div>
        );
      },
    },
    {
      key: 'yaml', label: 'Documentation',
      render: (t: RegistryToolRow) => (
        t.yaml_present ? (
          <div className="space-y-3">
            <StatusPill tone="success">Documented</StatusPill>
            <p className="text-sm text-muted-foreground">This tool has a definition file in the knowledge repository. The agent reads it to decide when to call the tool.</p>
            <CodeBlock>{`enterprise-knowledge/tools/${t.group}/${t.tool_id}.yaml`}</CodeBlock>
          </div>
        ) : (
          <div className="space-y-3">
            <StatusPill tone="warning">No documentation</StatusPill>
            <p className="text-sm text-muted-foreground">No definition file is registered for this tool, so diagnostics list it as an orphan. Add one so the agent knows when to use it.</p>
          </div>
        )
      ),
    },
    {
      key: 'usecases', label: 'Usage',
      render: (t: RegistryToolRow) => (
        <div className="space-y-1.5 text-sm text-muted-foreground">
          {t.use_case_refs > 0
            ? <p><span className="num font-medium text-foreground">{t.use_case_refs}</span> automation {t.use_case_refs === 1 ? 'playbook uses' : 'playbooks use'} this tool.</p>
            : <p>No automation playbook uses this tool yet.</p>}
          <p>The Automation page lists the steps of each playbook.</p>
        </div>
      ),
    },
    {
      key: 'canary', label: 'Health check',
      render: (t: RegistryToolRow) => {
        const c = canaryByTool[t.tool_id];
        return (
          <div className="space-y-5">
            {!t.has_canary && (
              <p className="flex items-start gap-2 text-sm text-muted-foreground">
                <Icon name="alert-triangle" className="mt-0.5 shrink-0 text-warning" />
                No sample inputs are set up for this tool, so the bulk check skips it.
              </p>
            )}
            {c ? (
              <>
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <span className="text-muted-foreground">Last check</span>
                  <StatusPill status={c.status} tone={c.status === 'skip' ? 'neutral' : undefined}>{CHECK_LABEL[c.status] || c.status}</StatusPill>
                  {c.duration_ms != null && c.status !== 'skip' && <span className="num text-xs text-muted-foreground">{c.duration_ms} ms</span>}
                </div>
                {c.reason && <p className="text-sm text-muted-foreground">{c.reason}</p>}
                {c.error && <InlineError>{c.error}</InlineError>}
                {c.result_preview && (
                  <section>
                    <SubHeading>Result preview</SubHeading>
                    <CodeBlock maxHeight={160} wrap>{c.result_preview}</CodeBlock>
                  </section>
                )}
                {c.params && (
                  <section>
                    <SubHeading>Inputs used</SubHeading>
                    <CodeBlock maxHeight={160}>{JSON.stringify(c.params, null, 2)}</CodeBlock>
                  </section>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Not checked in this session. Use "Run health checks" above the table to test the tools in the list.</p>
            )}
          </div>
        );
      },
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [canaryByTool]);

  // ----- render -----

  const activeFilters = Object.values(facets).reduce((n, s) => n + s.size, 0);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ExecuteDrawer adapter={executeAdapter} onClose={() => setExecuteAdapter(null)} />
      <DetailDrawer
        open={!!selectedTool}
        row={selectedTool}
        title={(t) => t.tool_id}
        subtitle={(t) => t.description}
        badges={(t) => [
          { label: riskLabel(t.risk_level), tone: riskTone(t.risk_level) },
          ...(t.requires_approval ? [{ label: 'Needs approval', tone: 'warn' as const }] : []),
          ...(!t.yaml_present ? [{ label: 'No documentation', tone: 'warn' as const }] : []),
          ...(!t.has_canary ? [{ label: 'No health check', tone: 'warn' as const }] : []),
        ]}
        tabs={drawerTabs}
        footer={(t) => (
          <div className="flex items-center justify-between gap-3">
            <span className="min-w-0 truncate text-xs text-muted-foreground">
              {t.connector_api ? <>Calls <span className="font-mono">{t.connector_api}</span></> : 'Does not call a connector API'}
            </span>
            <Button onClick={() => openRun(t)}>
              <Icon name="play" /> Run tool
            </Button>
          </div>
        )}
        onClose={closeDrawer}
      />

      {/* Header */}
      <div className="shrink-0 border-b border-border px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <h2 className="text-xl font-medium tracking-tight text-foreground">Tools registry</h2>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
              {summary ? (
                <>
                  <span className="num text-foreground">{summary.total}</span> tools registered.{' '}
                  <span className="num text-foreground">{summary.documented}</span> are documented and <span className="num text-foreground">{summary.withCheck}</span> have a health check.
                  {summary.orphans > 0 && <> <span className="num text-foreground">{summary.orphans}</span> {summary.orphans === 1 ? 'entry exists' : 'entries exist'} in code or in documentation only.</>}
                  {checks.run > 0 && (
                    <> Last check: <span className="num text-foreground">{checks.pass}</span> passed, <span className={cn('num', checks.fail > 0 ? 'text-destructive' : 'text-foreground')}>{checks.fail}</span> failed, <span className="num text-foreground">{checks.skip}</span> skipped.</>
                  )}
                </>
              ) : loading ? 'Loading the registry.' : 'Every tool the agent can call, with its documentation and health.'}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button variant="outline" size="sm" onClick={load} disabled={loading}>
              <Icon name={loading ? 'spinner' : 'refresh'} className={cn(loading && 'animate-spin')} />
              Refresh
            </Button>
            <Button size="sm" onClick={runCanarySlice} disabled={canaryRunning || filtered.length === 0}>
              <Icon name={canaryRunning ? 'spinner' : 'play'} className={cn(canaryRunning && 'animate-spin')} />
              {canaryRunning ? `Checking ${filtered.length} tools` : 'Run health checks'}
            </Button>
          </div>
        </div>

        <Toolbar className="mt-4">
          <SearchInput value={search} onChange={setSearch} placeholder="Search tools, groups or tags" className="sm:w-80" />
          <Button variant="outline" size="sm" className="lg:hidden" onClick={() => setFiltersOpen(true)}>
            <Icon name="filter" /> Filters{activeFilters > 0 && <span className="num text-muted-foreground">{activeFilters}</span>}
          </Button>
          <ToolbarSpacer />
          {report && (
            <span className="text-xs text-muted-foreground">
              <span className="num text-foreground">{filtered.length}</span> of <span className="num">{rows.length}</span> shown
            </span>
          )}
        </Toolbar>
      </div>

      {/* Body */}
      <div className="grid min-h-0 flex-1 lg:grid-cols-[232px_minmax(0,1fr)]">
        <aside className="scroll-thin hidden min-h-0 overflow-y-auto border-r border-border bg-sidebar/40 px-4 py-4 lg:block">
          <FacetFilters facets={facetDescriptors} state={facets} onChange={setFacets} />
        </aside>

        <main className="flex min-h-0 min-w-0 flex-col gap-3 p-4 sm:px-6">
          {error && <InlineError onRetry={load}>{error}</InlineError>}
          <div className="relative min-h-0 flex-1">
            <div className="absolute inset-0">
              {loading && !report ? (
                <div className="h-full overflow-hidden rounded-xl border border-border bg-card" aria-busy="true">
                  <div className="divide-y divide-border">
                    {Array.from({ length: 9 }).map((_, i) => (
                      <div key={i} className="flex items-center gap-6 px-4 py-3">
                        <div className="flex-1 space-y-2"><Skeleton className="h-4 w-52" /><Skeleton className="h-3 w-3/4" /></div>
                        <Skeleton className="hidden h-4 w-24 md:block" />
                        <Skeleton className="h-4 w-20" />
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <RegistryTable<RegistryToolRow>
                  rows={filtered}
                  columns={columns}
                  rowKey={(r) => r.tool_id}
                  onSelect={(r) => setSelectedToolId(r.tool_id)}
                  selectedKey={selectedToolId || undefined}
                  emptyMessage={
                    rows.length === 0
                      ? 'No tools are registered yet.'
                      : (
                        <span className="flex flex-col items-center gap-3">
                          No tools match the search and filters.
                          <Button variant="outline" size="sm" onClick={() => { setSearch(''); setFacets({}); }}>Clear filters</Button>
                        </span>
                      )
                  }
                  height="100%"
                />
              )}
            </div>
          </div>
        </main>
      </div>

      <Sheet open={filtersOpen} onOpenChange={setFiltersOpen}>
        <SheetContent side="left" className="flex w-full flex-col gap-0 p-0 sm:max-w-xs">
          <div className="border-b border-border px-4 py-3.5 pr-12">
            <SheetTitle className="text-md font-medium">Filter tools</SheetTitle>
            <SheetDescription className="sr-only">Narrow the list of tools</SheetDescription>
          </div>
          <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <FacetFilters facets={facetDescriptors} state={facets} onChange={setFacets} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
