import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Icon } from '@/components/ds/Icon';
import { CodeBlock, InlineError, KeyValues, SearchInput, StatusPill, SubHeading, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import {
  formatNexusBundle,
  nifiProcessorService,
  type NiFiProcessorSpec,
  type ProcessorProbeResult,
  type ProcessorRegistryCapabilities,
  type ProcessorSource,
} from '@/services/nifiProcessorService';
import { RegistryTable } from './RegistryTable';
import { FacetFilters } from './FacetFilters';
import { DetailDrawer } from './DetailDrawer';
import { ExecuteDrawer, adapterFromProcessor } from './ExecuteDrawer';
import type { ExecuteAdapter, FacetDescriptor, FacetState, RegistryColumn, DetailDrawerTab } from './types';

const CHECK_LABEL: Record<string, string> = { pass: 'Passed', fail: 'Failed', skip: 'Skipped' };

function filterText(row: NiFiProcessorSpec, q: string): boolean {
  if (!q) return true;
  const n = q.toLowerCase();
  return (
    row.processorId.toLowerCase().includes(n)
    || (row.label || '').toLowerCase().includes(n)
    || (row.description || '').toLowerCase().includes(n)
    || (row.tags || []).some(t => t.toLowerCase().includes(n))
    || (row.bundle || '').toLowerCase().includes(n)
    || (row.nifiClass || '').toLowerCase().includes(n)
  );
}

function applyFacets(rows: NiFiProcessorSpec[], facets: FacetState): NiFiProcessorSpec[] {
  const runtimeSel = facets.runtime;
  const bundleSel = facets.bundle;
  return rows.filter(r => {
    if (runtimeSel?.size && !runtimeSel.has(r.runtime || 'stub')) return false;
    if (bundleSel?.size && !bundleSel.has(formatNexusBundle(r.bundle))) return false;
    return true;
  });
}

function bucketize<T>(rows: T[], key: (r: T) => string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const r of rows) {
    const k = key(r) || '—';
    out[k] = (out[k] || 0) + 1;
  }
  return out;
}

function shortId(processorId: string): string {
  return processorId.startsWith('nifi.') ? processorId.slice(5) : processorId;
}

export default function NiFiProcessorRegistryBrowser() {
  const [rows, setRows] = useState<NiFiProcessorSpec[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [facets, setFacets] = useState<FacetState>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [executeAdapter, setExecuteAdapter] = useState<ExecuteAdapter | null>(null);
  const [probeById, setProbeById] = useState<Record<string, ProcessorProbeResult>>({});
  const [probeRunning, setProbeRunning] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [sourceById, setSourceById] = useState<Record<string, ProcessorSource>>({});
  const [sourceLoading, setSourceLoading] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<ProcessorRegistryCapabilities | null>(null);

  const [searchParams, setSearchParams] = useSearchParams();
  const executionEnabled = capabilities?.runtimeExecution === true;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await nifiProcessorService.listProcessors();
      setRows(r.items || []);
      setCapabilities(r.capabilities ?? { runtimeExecution: false });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const focus = searchParams.get('focus');
    if (!focus || !rows.length) return;
    if (rows.some(r => r.processorId === focus)) setSelectedId(focus);
  }, [rows, searchParams]);

  const filtered = useMemo(() => {
    const f = applyFacets(rows, facets);
    if (!search.trim()) return f;
    return f.filter(r => filterText(r, search));
  }, [rows, facets, search]);

  const selected = useMemo(
    () => rows.find(r => r.processorId === selectedId) || null,
    [rows, selectedId],
  );

  const liveCount = useMemo(() => rows.filter(r => r.runtime === 'live').length, [rows]);

  const facetDescriptors = useMemo<FacetDescriptor[]>(() => {
    const byRuntime = bucketize(rows, r => r.runtime || 'stub');
    const byBundle = bucketize(rows, r => formatNexusBundle(r.bundle));
    return [
      {
        key: 'runtime',
        label: 'Runtime',
        options: ['live', 'stub']
          .filter(k => byRuntime[k])
          .map(k => ({ value: k, label: k === 'live' ? 'Live (Python)' : 'Stub (catalog only)', count: byRuntime[k] })),
      },
      {
        key: 'bundle',
        label: 'Bundle',
        options: Object.keys(byBundle).sort()
          .map(k => ({ value: k, label: k, count: byBundle[k] })),
      },
    ];
  }, [rows]);

  const checks = useMemo(() => {
    const all = Object.values(probeById);
    return {
      run: all.length,
      pass: all.filter(c => c.status === 'pass').length,
      fail: all.filter(c => c.status === 'fail').length,
      skip: all.filter(c => c.status === 'skip').length,
    };
  }, [probeById]);

  const closeDrawer = () => {
    setSelectedId(null);
    if (searchParams.get('focus')) {
      const next = new URLSearchParams(searchParams);
      next.delete('focus');
      setSearchParams(next, { replace: true });
    }
  };

  const loadSource = useCallback(async (processorId: string) => {
    if (sourceById[processorId]) return;
    setSourceLoading(processorId);
    try {
      const src = await nifiProcessorService.getSource(processorId);
      setSourceById(prev => ({ ...prev, [processorId]: src }));
    } catch {
      setSourceById(prev => ({
        ...prev,
        [processorId]: {
          processorId,
          available: false,
          path: '',
          language: 'python',
          source: '',
          reason: 'Failed to load source',
        },
      }));
    } finally {
      setSourceLoading(null);
    }
  }, [sourceById]);

  useEffect(() => {
    if (selected?.runtime === 'live') loadSource(selected.processorId);
  }, [selected, loadSource]);

  const resync = async () => {
    setSyncing(true);
    try {
      await nifiProcessorService.resync();
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSyncing(false);
    }
  };

  const runProbes = async () => {
    if (!executionEnabled) return;
    const liveIds = filtered.filter(r => r.runtime === 'live').map(r => r.processorId);
    if (!liveIds.length) return;
    setProbeRunning(true);
    try {
      const rep = await nifiProcessorService.probeBatch(liveIds);
      const map: Record<string, ProcessorProbeResult> = {};
      for (const r of rep.results) map[r.processorId] = r;
      setProbeById(prev => ({ ...prev, ...map }));
    } catch (e: unknown) {
      setError(`Probe run failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setProbeRunning(false);
    }
  };

  const openRun = async (row: NiFiProcessorSpec) => {
    let defaults = { params: {}, content: '{}', attributes: {} as Record<string, unknown> };
    try {
      const d = await nifiProcessorService.probeDefaults(row.processorId);
      defaults = { params: d.params || {}, content: d.content || '{}', attributes: (d.attributes || {}) as Record<string, unknown> };
    } catch { /* use empty defaults */ }
    setExecuteAdapter(adapterFromProcessor({
      processorId: row.processorId,
      displayName: row.label || shortId(row.processorId),
      properties: row.properties,
      defaultProbe: defaults,
    }));
  };

  const columns: RegistryColumn<NiFiProcessorSpec>[] = [
    {
      key: 'processor',
      label: 'Processor',
      className: 'max-w-[360px]',
      sortBy: r => r.label || r.processorId,
      render: r => (
        <div className="min-w-0">
          <div className="truncate font-mono text-sm font-medium text-foreground">{shortId(r.processorId)}</div>
          <div className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{r.description || r.processorId}</div>
        </div>
      ),
    },
    {
      key: 'bundle',
      label: 'Bundle',
      sortBy: r => r.bundle || '',
      render: r => <span className="whitespace-nowrap text-muted-foreground">{formatNexusBundle(r.bundle)}</span>,
    },
    {
      key: 'io',
      label: 'Inputs / outputs',
      className: 'hidden xl:table-cell max-w-[200px]',
      render: r => (
        <div className="text-xs text-muted-foreground">
          <span className="num text-foreground">{(r.properties || []).length}</span> props
          {' · '}
          <span className="num text-foreground">{(r.relationships || []).length}</span> rel
        </div>
      ),
    },
    {
      key: 'runtime',
      label: 'Runtime',
      sortBy: r => r.runtime || 'stub',
      render: r => (
        <StatusPill tone={r.runtime === 'live' ? 'success' : 'neutral'}>
          {r.runtime === 'live' ? 'Live' : 'Stub'}
        </StatusPill>
      ),
    },
    {
      key: 'readiness',
      label: 'Readiness',
      render: r => (
        r.runtime === 'live'
          ? <span className="text-muted-foreground">Runnable</span>
          : <StatusPill tone="warning">Not implemented</StatusPill>
      ),
    },
    {
      key: 'last_probe',
      label: 'Last probe',
      sortBy: r => probeById[r.processorId]?.status || '',
      render: r => {
        const c = probeById[r.processorId];
        if (probeRunning && r.runtime === 'live' && !c) return <Skeleton className="h-4 w-16" />;
        if (!c) return <span className="text-subtle-foreground">Not run</span>;
        return (
          <div className="whitespace-nowrap">
            <StatusPill status={c.status} tone={c.status === 'skip' ? 'neutral' : undefined}>
              {CHECK_LABEL[c.status] || c.status}
            </StatusPill>
            {c.status !== 'skip' && c.duration_ms != null && (
              <div className="num mt-0.5 text-xs text-muted-foreground">{c.duration_ms} ms</div>
            )}
          </div>
        );
      },
    },
  ];

  const drawerTabs = useMemo<DetailDrawerTab<NiFiProcessorSpec>[]>(() => [
    {
      key: 'overview',
      label: 'Overview',
      render: t => (
        <KeyValues items={[
          { label: 'Processor ID', value: <span className="font-mono text-xs">{t.processorId}</span> },
          { label: 'NiFi class', value: <span className="font-mono text-xs break-all">{t.nifiClass || '—'}</span> },
          { label: 'Bundle', value: formatNexusBundle(t.bundle) },
          { label: 'Runtime', value: t.runtime === 'live' ? 'Python (live)' : 'Catalog stub' },
          { label: 'Category', value: t.category || 'nexus' },
          { label: 'Code ref', value: t.codeRef || (t.runtime === 'live' ? 'src.services.flow_processors' : '—') },
          ...(t.tags?.length ? [{ label: 'Tags', value: t.tags.join(', ') }] : []),
        ]} />
      ),
    },
    {
      key: 'inputs',
      label: 'Inputs',
      render: t => (
        <div className="space-y-6">
          <section>
            <SubHeading>FlowFile</SubHeading>
            <p className="text-sm text-muted-foreground">
              Each run takes a <strong>content</strong> body plus <strong>attributes</strong> (for example <code className="font-mono text-xs">mime.type</code>).
            </p>
          </section>
          <section>
            <SubHeading>Properties</SubHeading>
            {(t.properties || []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No configurable properties in the harvest metadata.</p>
            ) : (
              <ul className="divide-y divide-border">
                {(t.properties || []).map(p => (
                  <li key={p.name} className="py-2.5">
                    <div className="flex flex-wrap items-baseline gap-x-2">
                      <span className="font-mono text-sm">{p.displayName || p.name}</span>
                      {p.required && <span className="text-xs text-muted-foreground">required</span>}
                    </div>
                    {p.default != null && <p className="mt-0.5 text-xs text-muted-foreground">Default: {String(p.default)}</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ),
    },
    {
      key: 'outputs',
      label: 'Outputs',
      render: t => (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Processors route FlowFiles to <strong>relationships</strong> (for example success / failure / original).
          </p>
          <div className="flex flex-wrap gap-2">
            {(t.relationships || []).map(rel => (
              <StatusPill key={rel.name} variant="soft">{rel.name}</StatusPill>
            ))}
          </div>
          {(t.relationships || []).length === 0 && (
            <p className="text-sm text-muted-foreground">No relationships listed in catalog metadata.</p>
          )}
        </div>
      ),
    },
    {
      key: 'code',
      label: 'Code',
      render: t => {
        const src = sourceById[t.processorId];
        if (sourceLoading === t.processorId && !src) {
          return <Skeleton className="h-48 w-full" />;
        }
        if (!src) {
          return (
            <p className="text-sm text-muted-foreground">
              {t.runtime === 'live' ? 'Loading Python source…' : 'Stub processors have no Nexus Python implementation yet.'}
            </p>
          );
        }
        if (!src.available) {
          return (
            <div className="space-y-3">
              <StatusPill tone="warning">No source</StatusPill>
              <p className="text-sm text-muted-foreground">{src.reason}</p>
              {t.nifiClass && <CodeBlock>{t.nifiClass}</CodeBlock>}
            </div>
          );
        }
        return (
          <div className="space-y-3">
            <StatusPill tone="success">Python implementation</StatusPill>
            <CodeBlock>{src.path}</CodeBlock>
            <CodeBlock maxHeight={420}>{src.source}</CodeBlock>
          </div>
        );
      },
    },
    {
      key: 'probe',
      label: 'Probe',
      render: t => {
        const c = probeById[t.processorId];
        return (
          <div className="space-y-4">
            {t.runtime !== 'live' && (
              <p className="text-sm text-muted-foreground">Stub processors are skipped in batch probes until a Python port exists.</p>
            )}
            {c ? (
              <>
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <StatusPill status={c.status}>{CHECK_LABEL[c.status] || c.status}</StatusPill>
                  {c.duration_ms != null && <span className="num text-xs text-muted-foreground">{c.duration_ms} ms</span>}
                </div>
                {c.reason && <p className="text-sm text-muted-foreground">{c.reason}</p>}
                {c.error && <InlineError>{c.error}</InlineError>}
                {c.result_preview && <CodeBlock maxHeight={160} wrap>{c.result_preview}</CodeBlock>}
                {c.params && (
                  <section>
                    <SubHeading>Inputs used</SubHeading>
                    <CodeBlock maxHeight={200}>{JSON.stringify(c.params, null, 2)}</CodeBlock>
                  </section>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Not probed in this session. Use &quot;Run probes&quot; for live processors or open Run from the drawer footer.
              </p>
            )}
          </div>
        );
      },
    },
  ], [probeById, sourceById, sourceLoading]);

  const activeFilters = Object.values(facets).reduce((n, s) => n + s.size, 0);
  const liveFiltered = filtered.filter(r => r.runtime === 'live').length;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ExecuteDrawer adapter={executeAdapter} onClose={() => setExecuteAdapter(null)} />
      <DetailDrawer
        open={!!selected}
        row={selected}
        title={t => shortId(t.processorId)}
        subtitle={t => t.description}
        badges={t => [
          { label: t.runtime === 'live' ? 'Live' : 'Stub', tone: t.runtime === 'live' ? 'ok' : 'muted' },
          { label: formatNexusBundle(t.bundle), tone: 'info' },
        ]}
        tabs={drawerTabs}
        footer={t => (
          <div className="flex items-center justify-between gap-3">
            <span className="min-w-0 truncate text-xs text-muted-foreground font-mono">{t.processorId}</span>
            <Button onClick={() => openRun(t)} disabled={!executionEnabled || t.runtime !== 'live'}>
              <Icon name="play" /> Run processor
            </Button>
          </div>
        )}
        onClose={closeDrawer}
        defaultTab="overview"
      />

      <div className="shrink-0 border-b border-border px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <h2 className="text-xl font-medium tracking-tight text-foreground">Processor registry</h2>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
              {rows.length > 0 ? (
                <>
                  <span className="num text-foreground">{rows.length}</span> processors in the Nexus catalog.{' '}
                  <span className="num text-foreground">{liveCount}</span> have a live Python runtime.
                  {checks.run > 0 && (
                    <> Last probe: <span className="num text-foreground">{checks.pass}</span> passed,{' '}
                      <span className={cn('num', checks.fail > 0 && 'text-destructive')}>{checks.fail}</span> failed,{' '}
                      <span className="num text-foreground">{checks.skip}</span> skipped.</>
                  )}
                </>
              ) : loading ? 'Loading processors…' : 'Harvested NiFi processors with metadata, ports, and probes.'}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button variant="outline" size="sm" onClick={load} disabled={loading}>
              <Icon name={loading ? 'spinner' : 'refresh'} className={cn(loading && 'animate-spin')} />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={resync} disabled={syncing}>
              <Icon name={syncing ? 'spinner' : 'database'} className={cn(syncing && 'animate-spin')} />
              Sync catalog
            </Button>
            <Button
              size="sm"
              onClick={runProbes}
              disabled={!executionEnabled || probeRunning || liveFiltered === 0}
              title={executionEnabled ? undefined : capabilities?.message}
            >
              <Icon name={probeRunning ? 'spinner' : 'play'} className={cn(probeRunning && 'animate-spin')} />
              {probeRunning ? `Probing ${liveFiltered}` : 'Run probes'}
            </Button>
          </div>
        </div>

        <Toolbar className="mt-4">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search processors, tags, bundle…"
            className="sm:w-80"
          />
          <Button variant="outline" size="sm" className="lg:hidden" onClick={() => setFiltersOpen(true)}>
            <Icon name="filter" /> Filters{activeFilters > 0 && <span className="num text-muted-foreground">{activeFilters}</span>}
          </Button>
          <ToolbarSpacer />
          <span className="text-xs text-muted-foreground">
            <span className="num text-foreground">{filtered.length}</span> of <span className="num">{rows.length}</span> shown
          </span>
        </Toolbar>
      </div>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[232px_minmax(0,1fr)]">
        <aside className="scroll-thin hidden min-h-0 overflow-y-auto border-r border-border bg-sidebar/40 px-4 py-4 lg:block">
          <FacetFilters facets={facetDescriptors} state={facets} onChange={setFacets} />
        </aside>

        <main className="flex min-h-0 min-w-0 flex-col gap-3 p-4 sm:px-6">
          {!executionEnabled && (
            <InlineError>
              {capabilities?.message || 'Inline dry-run is off. Deploy as a Nexus journey (stage nexus_flow) to run processors; catalog browse still works.'}
            </InlineError>
          )}
          {error && <InlineError onRetry={load}>{error}</InlineError>}
          <div className="relative min-h-0 flex-1">
            <div className="absolute inset-0">
              {loading && rows.length === 0 ? (
                <div className="h-full overflow-hidden rounded-xl border border-border bg-card" aria-busy="true">
                  <div className="divide-y divide-border">
                    {Array.from({ length: 8 }).map((_, i) => (
                      <div key={i} className="flex items-center gap-6 px-4 py-3">
                        <div className="flex-1 space-y-2"><Skeleton className="h-4 w-52" /><Skeleton className="h-3 w-3/4" /></div>
                        <Skeleton className="h-4 w-24" />
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <RegistryTable<NiFiProcessorSpec>
                  rows={filtered}
                  columns={columns}
                  rowKey={r => r.processorId}
                  onSelect={r => setSelectedId(r.processorId)}
                  selectedKey={selectedId || undefined}
                  emptyMessage={
                    rows.length === 0
                      ? 'No processors registered yet.'
                      : (
                        <span className="flex flex-col items-center gap-3">
                          No processors match the search and filters.
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
            <SheetTitle className="text-md font-medium">Filter processors</SheetTitle>
            <SheetDescription className="sr-only">Narrow the processor list</SheetDescription>
          </div>
          <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <FacetFilters facets={facetDescriptors} state={facets} onChange={setFacets} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}