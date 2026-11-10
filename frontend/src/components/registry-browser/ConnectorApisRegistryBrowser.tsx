import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Activity, AlertTriangle, BookOpen, CheckCircle2, Clock, Database, Loader2,
  Play, Plug, RefreshCw, Search, ShieldCheck, Target, Wrench,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import {
  connectorApiWorkbenchService,
  type AuditEvent,
  type ConnectorAPIListResponse,
  type ConnectorAPIRowEnriched,
} from '@/services/connectorApiWorkbenchService';
import { RegistryTable } from './RegistryTable';
import { StatsTiles } from './StatsTiles';
import { FacetFilters } from './FacetFilters';
import { DetailDrawer } from './DetailDrawer';
import { ExecuteDrawer, adapterFromConnectorApi } from './ExecuteDrawer';
import type {
  RegistryColumn, FacetDescriptor, FacetState, StatTile, ExecuteAdapter,
} from './types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const RISK_PILL: Record<string, string> = {
  read_only: 'bg-success/15 text-success',
  low_risk_write: 'bg-warning/15 text-warning',
  high_risk_write: 'bg-destructive/15 text-destructive',
};

const SYSTEM_PILL: Record<string, string> = {
  oracle: 'bg-destructive/15 text-destructive border-destructive/30',
  sap: 'bg-primary/15 text-primary border-primary/30',
  sfdc: 'bg-primary/15 text-primary border-primary/30',
  external: 'bg-primary/15 text-primary border-primary/30',
};

function riskTone(risk: string): 'ok' | 'warn' | 'err' {
  return risk === 'read_only' ? 'ok' : risk === 'high_risk_write' ? 'err' : 'warn';
}

function filterApiText(a: ConnectorAPIRowEnriched, q: string): boolean {
  if (!q) return true;
  const needle = q.toLowerCase();
  return (
    a.api_id.toLowerCase().includes(needle)
    || (a.description || '').toLowerCase().includes(needle)
    || a.target_system.toLowerCase().includes(needle)
    || (a.operation || '').toLowerCase().includes(needle)
    || (a.tags || []).some((tag) => tag.toLowerCase().includes(needle))
    || (a.tool_callers || []).some((t) => t.toLowerCase().includes(needle))
  );
}

function applyFacets(rows: ConnectorAPIRowEnriched[], facets: FacetState): ConnectorAPIRowEnriched[] {
  const sysSel = facets.target_system;
  const riskSel = facets.risk_level;
  const callerSel = facets.has_callers;
  const verSel = facets.verified;
  const writebackSel = facets.simulator_writeback;
  return rows.filter((a) => {
    if (sysSel?.size && !sysSel.has(a.target_system)) return false;
    if (riskSel?.size && !riskSel.has(a.risk_level)) return false;
    if (callerSel?.size && !callerSel.has(a.tool_caller_count > 0 ? 'yes' : 'no')) return false;
    if (verSel?.size && !verSel.has(a.verified ? 'yes' : 'no')) return false;
    if (writebackSel?.size && !writebackSel.has(a.simulator_writeback ? 'yes' : 'no')) return false;
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

export default function ConnectorApisRegistryBrowser() {
  const [data, setData] = useState<ConnectorAPIListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [facets, setFacets] = useState<FacetState>({});
  const [selectedApiId, setSelectedApiId] = useState<string | null>(null);
  const [executeAdapter, setExecuteAdapter] = useState<ExecuteAdapter | null>(null);
  const [eventsByApi, setEventsByApi] = useState<Record<string, AuditEvent[]>>({});
  const [canaryByApi, setCanaryByApi] = useState<Record<string, Record<string, unknown>>>({});

  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // ----- load -----

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await connectorApiWorkbenchService.list();
      setData(r);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // ?focus=<api_id> deep link
  useEffect(() => {
    const focus = searchParams.get('focus');
    if (!focus || !data) return;
    if (data.items.some((a) => a.api_id === focus)) {
      setSelectedApiId(focus);
    }
  }, [data, searchParams]);

  const closeDrawer = () => {
    setSelectedApiId(null);
    if (searchParams.get('focus')) {
      const next = new URLSearchParams(searchParams);
      next.delete('focus');
      setSearchParams(next, { replace: true });
    }
  };

  // ----- derived -----

  const rows = data?.items || [];
  const filtered = useMemo(() => {
    const f = applyFacets(rows, facets);
    if (!search.trim()) return f;
    return f.filter((r) => filterApiText(r, search));
  }, [rows, facets, search]);

  const selectedApi = useMemo(
    () => rows.find((a) => a.api_id === selectedApiId) || null,
    [rows, selectedApiId],
  );

  // Lazy-load events + canary payload when a row is selected (and not cached).
  useEffect(() => {
    if (!selectedApi) return;
    const id = selectedApi.api_id;
    if (eventsByApi[id] === undefined) {
      connectorApiWorkbenchService
        .events(id, 50)
        .then((r) => setEventsByApi((prev) => ({ ...prev, [id]: r.events || [] })))
        .catch(() => setEventsByApi((prev) => ({ ...prev, [id]: [] })));
    }
    if (canaryByApi[id] === undefined) {
      connectorApiWorkbenchService
        .canaryPayload(id)
        .then((r) => setCanaryByApi((prev) => ({ ...prev, [id]: r.payload || {} })))
        .catch(() => setCanaryByApi((prev) => ({ ...prev, [id]: {} })));
    }
  }, [selectedApi, eventsByApi, canaryByApi]);

  const facetDescriptors = useMemo<FacetDescriptor[]>(() => {
    const bySys = bucketize(rows, (r) => r.target_system);
    const byRisk = bucketize(rows, (r) => r.risk_level);
    return [
      {
        key: 'target_system',
        label: 'Target system',
        options: ['oracle', 'sap', 'sfdc', 'external']
          .filter((k) => bySys[k])
          .map((k) => ({ value: k, count: bySys[k] })),
      },
      {
        key: 'risk_level',
        label: 'Risk',
        options: ['read_only', 'low_risk_write', 'high_risk_write']
          .filter((k) => byRisk[k])
          .map((k) => ({ value: k, label: k.replace(/_/g, ' '), count: byRisk[k] })),
      },
      {
        key: 'has_callers',
        label: 'Tool callers',
        options: [
          { value: 'yes', label: 'has callers', count: rows.filter((r) => r.tool_caller_count > 0).length },
          { value: 'no', label: 'orphan', count: rows.filter((r) => r.tool_caller_count === 0).length },
        ],
      },
      {
        key: 'verified',
        label: 'Invocation history',
        options: [
          { value: 'yes', label: 'verified', count: rows.filter((r) => r.verified).length },
          { value: 'no', label: 'never invoked', count: rows.filter((r) => !r.verified).length },
        ],
      },
      {
        key: 'simulator_writeback',
        label: 'Simulator writeback',
        options: [
          { value: 'yes', label: 'enabled', count: rows.filter((r) => r.simulator_writeback).length },
          { value: 'no', label: 'disabled', count: rows.filter((r) => !r.simulator_writeback).length },
        ],
      },
    ];
  }, [rows]);

  const tiles = useMemo<StatTile[]>(() => {
    if (!data) return [];
    const totals = data.totals;
    return [
      {
        title: 'Total APIs',
        value: totals.checked,
        tone: 'ok',
        breakdown: Object.entries(totals.by_target_system || {})
          .map(([k, v]) => ({ label: k, value: v })),
      },
      {
        title: 'By risk',
        value: Object.keys(totals.by_risk_level || {}).length,
        breakdown: [
          { label: 'read_only', value: totals.by_risk_level?.read_only || 0, tone: 'ok' as const },
          { label: 'low_risk', value: totals.by_risk_level?.low_risk_write || 0, tone: 'warn' as const },
          { label: 'high_risk', value: totals.by_risk_level?.high_risk_write || 0, tone: 'err' as const },
        ],
      },
      {
        title: 'Verified',
        value: `${totals.verified} / ${totals.checked}`,
        tone: totals.verified === totals.checked ? 'ok' : 'warn',
        hint: 'APIs with at least one Audit_Event',
      },
      {
        title: 'Never invoked',
        value: totals.never_invoked,
        tone: totals.never_invoked === 0 ? 'ok' : 'warn',
        hint: 'No Audit_Event tagged with this api_id',
      },
      {
        title: 'Orphans',
        value: totals.orphans,
        tone: totals.orphans === 0 ? 'ok' : 'warn',
        hint: 'No registered tool binds this API',
      },
    ];
  }, [data]);

  // ----- columns -----

  const columns: RegistryColumn<ConnectorAPIRowEnriched>[] = [
    {
      key: 'api_id', label: 'API id',
      className: 'font-mono text-[12px]',
      sortBy: (r) => r.api_id,
      render: (r) => (
        <div className="flex flex-col gap-0.5">
          <span>{r.api_id}</span>
          <span className="text-xs text-muted-foreground line-clamp-1">{r.description}</span>
        </div>
      ),
    },
    {
      key: 'target_system', label: 'System',
      sortBy: (r) => r.target_system,
      render: (r) => (
        <Badge variant="outline" className={cn('text-xs', SYSTEM_PILL[r.target_system] || SYSTEM_PILL.external)}>
          {r.target_system}
        </Badge>
      ),
    },
    {
      key: 'operation', label: 'Operation',
      className: 'font-mono text-xs text-muted-foreground',
      sortBy: (r) => r.operation,
      render: (r) => <span title={r.operation}>{r.operation}</span>,
    },
    {
      key: 'risk_level', label: 'Risk',
      sortBy: (r) => r.risk_level,
      render: (r) => (
        <Badge variant="outline" className={cn('text-xs', RISK_PILL[r.risk_level] || RISK_PILL.low_risk_write)}>
          {r.risk_level.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      key: 'callers', label: 'Callers',
      sortBy: (r) => r.tool_caller_count,
      render: (r) => (
        <span className={cn('text-xs font-mono', r.tool_caller_count === 0 && 'text-warning')}>
          {r.tool_caller_count}
        </span>
      ),
    },
    {
      key: 'audit', label: 'Audit',
      sortBy: (r) => r.audit_count || 0,
      render: (r) => (
        <div className="flex items-center gap-1">
          <span className="text-xs font-mono">{r.audit_count ?? 0}</span>
          {r.verified
            ? <CheckCircle2 className="h-3 w-3 text-success" />
            : <AlertTriangle className="h-3 w-3 text-warning" />}
        </div>
      ),
    },
  ];

  // ----- actions -----

  const openRun = (api: ConnectorAPIRowEnriched) => {
    setExecuteAdapter(adapterFromConnectorApi({
      apiId: api.api_id,
      displayName: api.api_id,
      paramsSchema: api.request_schema,
      defaultParams: canaryByApi[api.api_id] || {},
      riskLevel: api.risk_level,
    }));
  };

  // ----- drawer tabs -----

  const drawerTabs = [
    {
      key: 'overview', label: 'Overview',
      render: (a: ConnectorAPIRowEnriched) => (
        <div className="space-y-2 text-xs">
          <div><span className="text-muted-foreground">Description:</span> {a.description || '-'}</div>
          <div className="grid grid-cols-2 gap-y-1">
            <div><span className="text-muted-foreground">Target:</span> {a.target_system}</div>
            <div><span className="text-muted-foreground">Risk:</span> {a.risk_level}</div>
            <div className="col-span-2 font-mono text-xs">
              <span className="text-muted-foreground">Operation: </span>{a.operation}
            </div>
            <div><span className="text-muted-foreground">Writeback:</span> {a.simulator_writeback ? 'enabled' : 'disabled'}</div>
            <div><span className="text-muted-foreground">Verified:</span> {a.verified ? 'yes' : 'no'}</div>
            <div><span className="text-muted-foreground">Audit count:</span> {a.audit_count ?? 0}</div>
            <div><span className="text-muted-foreground">Last invocation:</span>{' '}
              {a.last_invocation_ts ? new Date(a.last_invocation_ts).toLocaleString() : '-'}
            </div>
          </div>
          {a.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {a.tags.map((t) => (
                <Badge key={t} variant="outline" className="text-xs">{t}</Badge>
              ))}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'request', label: 'Request',
      render: (a: ConnectorAPIRowEnriched) => (
        <pre className="text-xs font-mono bg-muted/30 border rounded p-2 max-h-80 overflow-auto whitespace-pre-wrap">
{JSON.stringify(a.request_schema || {}, null, 2)}
        </pre>
      ),
    },
    {
      key: 'response', label: 'Response',
      render: (a: ConnectorAPIRowEnriched) => (
        <pre className="text-xs font-mono bg-muted/30 border rounded p-2 max-h-80 overflow-auto whitespace-pre-wrap">
{JSON.stringify(a.response_schema || {}, null, 2)}
        </pre>
      ),
    },
    {
      key: 'callers', label: 'Tool callers',
      render: (a: ConnectorAPIRowEnriched) => (
        <div className="text-xs space-y-2">
          {a.tool_callers.length === 0 && (
            <div className="text-warning flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" /> No registered tool calls this API. Treated as an orphan in Diagnostics.
            </div>
          )}
          {a.tool_callers.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {a.tool_callers.map((tool) => (
                <Badge
                  key={tool}
                  variant="outline"
                  className="cursor-pointer hover:bg-primary/10 font-mono text-xs"
                  onClick={() => navigate(`/ai-stack/reasoning?tab=tools-reg&focus=${encodeURIComponent(tool)}`)}
                  title={`Open ${tool} in Tools Registry`}
                >
                  {tool}
                </Badge>
              ))}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'audit', label: 'Audit events',
      render: (a: ConnectorAPIRowEnriched) => {
        const events = eventsByApi[a.api_id];
        if (events === undefined) {
          return (
            <div className="text-xs text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading events...
            </div>
          );
        }
        if (events.length === 0) {
          return <div className="text-xs text-muted-foreground">No audit events recorded for this API.</div>;
        }
        return (
          <div className="space-y-2 text-xs">
            {events.map((ev) => (
              <div key={ev.event_id} className="border rounded p-2 bg-muted/20">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span><Clock className="inline h-3 w-3 mr-1" />{new Date(ev.event_ts).toLocaleString()}</span>
                  <span className="font-mono">{ev.actor}</span>
                </div>
                <div className="font-mono mt-1">
                  <span className="text-primary">{ev.verb}</span> -&gt; <span>{ev.target}</span>
                </div>
                {ev.payload && (
                  <pre className="text-xs font-mono text-muted-foreground/80 mt-1 overflow-auto max-h-24">
{JSON.stringify(ev.payload, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        );
      },
    },
    {
      key: 'canary', label: 'Canary payload',
      render: (a: ConnectorAPIRowEnriched) => {
        const payload = canaryByApi[a.api_id];
        if (payload === undefined) {
          return (
            <div className="text-xs text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading canary payload...
            </div>
          );
        }
        return (
          <div className="space-y-2 text-xs">
            <div className="text-muted-foreground">Sample payload assembled from <code>request_schema</code>:</div>
            <pre className="text-xs font-mono bg-muted/30 border rounded p-2 max-h-72 overflow-auto whitespace-pre-wrap">
{JSON.stringify(payload, null, 2)}
            </pre>
            <div className="text-xs text-muted-foreground">
              The Run button pre-fills this payload into the execute drawer.
            </div>
          </div>
        );
      },
    },
  ];

  // ----- render -----

  return (
    <div className="flex h-full">
      <ExecuteDrawer adapter={executeAdapter} onClose={() => setExecuteAdapter(null)} />
      <DetailDrawer
        open={!!selectedApi}
        row={selectedApi}
        title={(a) => a.api_id}
        subtitle={(a) => a.description}
        badges={(a) => [
          { label: a.target_system, tone: 'info' },
          { label: a.risk_level.replace(/_/g, ' '), tone: riskTone(a.risk_level) },
          ...(a.verified ? [{ label: 'verified', tone: 'ok' as const }] : [{ label: 'never invoked', tone: 'warn' as const }]),
          ...(a.tool_caller_count === 0 ? [{ label: 'orphan', tone: 'warn' as const }] : []),
        ]}
        tabs={drawerTabs}
        footer={(a) => (
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {a.tool_caller_count > 0
                ? `${a.tool_caller_count} tool caller(s)`
                : 'No tool caller'}
            </span>
            <Button size="sm" onClick={() => openRun(a)}>
              <Play className="h-3.5 w-3.5 mr-1" /> Run
            </Button>
          </div>
        )}
        onClose={closeDrawer}
      />

      {/* Header */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="p-4 pb-3 border-b bg-card/40 space-y-3">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <Plug className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold">Connector APIs Registry</h2>
              {data && (
                <span className="text-xs bg-muted/60 px-2 py-0.5 rounded">
                  {filtered.length} / {rows.length}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={load} disabled={loading}>
                {loading ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5 mr-1" />}
                Refresh
              </Button>
            </div>
          </div>

          <StatsTiles tiles={tiles} />

          <div className="flex items-center gap-2">
            <div className="relative flex-1 max-w-md">
              <Search className="h-3.5 w-3.5 absolute left-2 top-2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search api_id, description, target, operation, tags, callers..."
                className="pl-7 h-8 text-xs"
              />
            </div>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          <aside className="w-56 shrink-0 border-r p-3 overflow-auto">
            <FacetFilters facets={facetDescriptors} state={facets} onChange={setFacets} />
          </aside>

          <main className="flex-1 p-3 overflow-hidden flex flex-col">
            {error && (
              <div className="text-xs text-destructive bg-destructive/10 border border-destructive/30 rounded p-2 mb-2">
                {error}
              </div>
            )}
            {loading && !data ? (
              <div className="flex items-center gap-2 text-muted-foreground text-sm py-12 justify-center">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading connector APIs...
              </div>
            ) : (
              <RegistryTable<ConnectorAPIRowEnriched>
                rows={filtered}
                columns={columns}
                rowKey={(r) => r.api_id}
                onSelect={(r) => setSelectedApiId(r.api_id)}
                selectedKey={selectedApiId || undefined}
                emptyMessage={
                  <span className="flex items-center justify-center gap-2">
                    <BookOpen className="h-3.5 w-3.5" /> No connector APIs match the current filters.
                  </span>
                }
                height="calc(100vh - 360px)"
              />
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
