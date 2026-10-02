import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle, BookOpen, CheckCircle2, FileText, Loader2, Play,
  RefreshCw, Search, ShieldCheck, Wrench,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  reactToolsDiagnosticsService,
  type RegistryReport,
  type RegistryToolRow,
  type CanaryReport,
  type CanaryResult,
} from '@/services/reactToolsDiagnosticsService';
import { cn } from '@/lib/utils';
import { RegistryTable } from './RegistryTable';
import { StatsTiles } from './StatsTiles';
import { FacetFilters } from './FacetFilters';
import { DetailDrawer } from './DetailDrawer';
import { ExecuteDrawer, adapterFromTool } from './ExecuteDrawer';
import type {
  RegistryColumn, FacetDescriptor, FacetState, StatTile, ExecuteAdapter,
} from './types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const RISK_PILL: Record<string, string> = {
  read_only: 'bg-green-500/15 text-green-300',
  low_risk_write: 'bg-amber-500/15 text-amber-300',
  high_risk_write: 'bg-red-500/15 text-red-300',
};

function riskTone(risk: string): 'ok' | 'warn' | 'err' {
  return risk === 'read_only' ? 'ok' : risk === 'high_risk_write' ? 'err' : 'warn';
}

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
        key: 'group',
        label: 'Group',
        options: Object.keys(byGroup).sort()
          .map((k) => ({ value: k, count: byGroup[k] })),
      },
      {
        key: 'risk_level',
        label: 'Risk',
        options: ['read_only', 'low_risk_write', 'high_risk_write']
          .filter((k) => byRisk[k])
          .map((k) => ({ value: k, label: k.replace(/_/g, ' '), count: byRisk[k] })),
      },
      {
        key: 'tool_kind',
        label: 'Kind',
        options: ['read', 'analyze', 'decide', 'mutate', 'notify']
          .filter((k) => byKind[k])
          .map((k) => ({ value: k, count: byKind[k] })),
      },
      {
        key: 'yaml_present',
        label: 'YAML doc',
        options: [
          { value: 'yes', label: 'present', count: rows.filter((r) => r.yaml_present).length },
          { value: 'no', label: 'missing', count: rows.filter((r) => !r.yaml_present).length },
        ],
      },
      {
        key: 'has_canary',
        label: 'Canary',
        options: [
          { value: 'yes', label: 'has canary', count: rows.filter((r) => r.has_canary).length },
          { value: 'no', label: 'no canary', count: rows.filter((r) => !r.has_canary).length },
        ],
      },
      {
        key: 'requires_approval',
        label: 'Approval',
        options: [
          { value: 'yes', label: 'required', count: rows.filter((r) => r.requires_approval).length },
          { value: 'no', label: 'auto', count: rows.filter((r) => !r.requires_approval).length },
        ],
      },
    ];
  }, [rows]);

  const tiles = useMemo<StatTile[]>(() => {
    if (!report) return [];
    const byGroup = report.totals.by_group || {};
    const byRisk = report.totals.by_risk_level || {};
    const byKind = bucketize(rows, (r) => toolKindOf(r));
    const yamlCount = rows.filter((r) => r.yaml_present).length;
    const canaryCount = rows.filter((r) => r.has_canary).length;
    return [
      {
        title: 'Total tools',
        value: report.totals.registered_tools,
        tone: 'ok',
        breakdown: Object.entries(byGroup).slice(0, 5)
          .map(([k, v]) => ({ label: k, value: v })),
      },
      {
        title: 'By risk',
        value: Object.keys(byRisk).length,
        breakdown: [
          { label: 'read_only', value: byRisk.read_only || 0, tone: 'ok' as const },
          { label: 'low_risk', value: byRisk.low_risk_write || 0, tone: 'warn' as const },
          { label: 'high_risk', value: byRisk.high_risk_write || 0, tone: 'err' as const },
        ],
      },
      {
        title: 'By kind',
        value: Object.keys(byKind).length,
        breakdown: Object.entries(byKind)
          .map(([k, v]) => ({ label: k, value: v })),
      },
      {
        title: 'YAML coverage',
        value: `${yamlCount} / ${rows.length}`,
        tone: yamlCount === rows.length ? 'ok' : 'warn',
        hint: `${report.totals.yaml_tools} YAML doc(s) total`,
      },
      {
        title: 'Canary coverage',
        value: `${canaryCount} / ${rows.length}`,
        tone: canaryCount === rows.length ? 'ok' : 'warn',
        hint: 'Tools with curated canary params',
      },
      {
        title: 'Orphans',
        value: report.totals.registry_only_orphans + report.totals.yaml_only_orphans,
        tone: (report.totals.registry_only_orphans + report.totals.yaml_only_orphans) === 0 ? 'ok' : 'warn',
        hint: 'Code without YAML / YAML without code',
      },
    ];
  }, [report, rows]);

  // ----- columns -----

  const columns: RegistryColumn<RegistryToolRow>[] = [
    {
      key: 'tool_id', label: 'Tool',
      className: 'font-mono text-[12px]',
      sortBy: (r) => r.tool_id,
      render: (r) => (
        <div className="flex flex-col gap-0.5">
          <span>{r.tool_id}</span>
          <span className="text-[10px] text-muted-foreground line-clamp-1">{r.description}</span>
        </div>
      ),
    },
    {
      key: 'group', label: 'Group',
      sortBy: (r) => r.group,
      render: (r) => <span className="text-[11px]">{r.group}</span>,
    },
    {
      key: 'risk_level', label: 'Risk',
      sortBy: (r) => r.risk_level,
      render: (r) => (
        <Badge variant="outline" className={cn('text-[10px]', RISK_PILL[r.risk_level] || RISK_PILL.low_risk_write)}>
          {r.risk_level.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      key: 'tool_kind', label: 'Kind',
      sortBy: (r) => toolKindOf(r),
      render: (r) => <span className="text-[11px]">{toolKindOf(r)}</span>,
    },
    {
      key: 'connector_api', label: 'Connector API',
      className: 'font-mono text-[11px]',
      sortBy: (r) => r.connector_api || '',
      render: (r) => r.connector_api
        ? (
          <span
            className="text-blue-300 cursor-pointer hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/ai-stack/data-plane?tab=connector-registry&focus=${encodeURIComponent(r.connector_api!)}`);
            }}
          >
            {r.connector_api}
          </span>
        )
        : <span className="text-muted-foreground">-</span>,
    },
    {
      key: 'flags', label: 'Flags',
      render: (r) => (
        <div className="flex items-center gap-1 flex-wrap">
          {r.yaml_present && (
            <Badge variant="outline" className="text-[10px] bg-blue-500/10 text-blue-300 border-blue-500/30">
              <FileText className="h-2.5 w-2.5 mr-0.5" /> yaml
            </Badge>
          )}
          {r.has_canary && (
            <Badge variant="outline" className="text-[10px] bg-green-500/10 text-green-300 border-green-500/30">
              <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" /> canary
            </Badge>
          )}
          {r.requires_approval && (
            <Badge variant="outline" className="text-[10px] bg-amber-500/10 text-amber-300 border-amber-500/30">
              <ShieldCheck className="h-2.5 w-2.5 mr-0.5" /> approval
            </Badge>
          )}
        </div>
      ),
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
      setError(`canary run failed: ${e?.message || e}`);
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

  const drawerTabs = [
    {
      key: 'overview', label: 'Overview',
      render: (t: RegistryToolRow) => (
        <div className="space-y-2 text-xs">
          <div><span className="text-muted-foreground">Description:</span> {t.description || '-'}</div>
          <div className="grid grid-cols-2 gap-y-1">
            <div><span className="text-muted-foreground">Group:</span> {t.group}</div>
            <div><span className="text-muted-foreground">Kind:</span> {toolKindOf(t)}</div>
            <div><span className="text-muted-foreground">Risk:</span> {t.risk_level}</div>
            <div><span className="text-muted-foreground">Approval:</span> {t.requires_approval ? 'required' : 'no'}</div>
            <div><span className="text-muted-foreground">Cacheable:</span> {t.cacheable ? 'yes' : 'no'}</div>
            <div><span className="text-muted-foreground">Use case refs:</span> {t.use_case_refs}</div>
          </div>
          {t.connector_api && (
            <div>
              <span className="text-muted-foreground">Connector API: </span>
              <span
                className="text-blue-300 hover:underline cursor-pointer font-mono"
                onClick={() => navigate(`/ai-stack/data-plane?tab=connector-registry&focus=${encodeURIComponent(t.connector_api!)}`)}
              >
                {t.connector_api}
              </span>
            </div>
          )}
          {t.tags && t.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {t.tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-[10px]">{tag}</Badge>
              ))}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'parameters', label: 'Parameters',
      render: (t: RegistryToolRow) => (
        <pre className="text-[11px] font-mono bg-muted/30 border rounded p-2 max-h-80 overflow-auto whitespace-pre-wrap">
{JSON.stringify(t.parameters || {}, null, 2)}
        </pre>
      ),
    },
    {
      key: 'yaml', label: 'YAML',
      render: (t: RegistryToolRow) => (
        <div className="text-xs space-y-2">
          {t.yaml_present
            ? (
              <>
                <Badge variant="outline" className="bg-blue-500/10 text-blue-300 border-blue-500/30">
                  <FileText className="h-3 w-3 mr-1" /> YAML present
                </Badge>
                <div className="text-muted-foreground">
                  Tool YAML at <code className="bg-muted/40 px-1 rounded">enterprise-knowledge/tools/{t.group}/{t.tool_id}.yaml</code>.
                  Raw body fetch is a follow-up; this v1 surfaces presence + parameters above.
                </div>
              </>
            )
            : (
              <div className="text-amber-300 flex items-start gap-1">
                <AlertTriangle className="h-3 w-3 mt-0.5" />
                <span>No YAML doc registered for this tool. Treated as a registry-only orphan in Diagnostics.</span>
              </div>
            )}
        </div>
      ),
    },
    {
      key: 'usecases', label: 'Code refs',
      render: (t: RegistryToolRow) => (
        <div className="text-xs space-y-1">
          {t.use_case_refs > 0 ? (
            <div className="text-muted-foreground">
              Referenced by <span className="text-foreground font-medium">{t.use_case_refs}</span> automation playbook(s).
            </div>
          ) : (
            <div className="text-muted-foreground">No automation playbook references this tool yet.</div>
          )}
          <div className="text-muted-foreground">
            See the Automation page for the per-playbook step list.
          </div>
        </div>
      ),
    },
    {
      key: 'canary', label: 'Canary',
      render: (t: RegistryToolRow) => {
        const c = canaryByTool[t.tool_id];
        return (
          <div className="text-xs space-y-2">
            {!t.has_canary && (
              <div className="text-amber-300">No CANARY_PARAMS entry for this tool.</div>
            )}
            {c ? (
              <>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Last canary:</span>
                  <Badge variant="outline" className={cn(
                    'text-[10px]',
                    c.status === 'pass' && 'bg-green-500/15 text-green-300 border-green-500/30',
                    c.status === 'fail' && 'bg-red-500/15 text-red-300 border-red-500/30',
                    c.status === 'skip' && 'bg-amber-500/15 text-amber-300 border-amber-500/30',
                  )}>{c.status}</Badge>
                  {c.duration_ms != null && <span className="text-muted-foreground">{c.duration_ms} ms</span>}
                </div>
                {c.result_preview && (
                  <pre className="font-mono text-[11px] bg-muted/30 border rounded p-2 max-h-32 overflow-auto whitespace-pre-wrap">{c.result_preview}</pre>
                )}
                {c.error && (
                  <pre className="font-mono text-[11px] text-red-300 bg-red-500/10 border border-red-500/30 rounded p-2 max-h-32 overflow-auto whitespace-pre-wrap">{c.error}</pre>
                )}
                {c.params && (
                  <div>
                    <div className="text-[10px] text-muted-foreground mb-0.5">Canary params:</div>
                    <pre className="font-mono text-[11px] bg-muted/30 border rounded p-2 max-h-32 overflow-auto whitespace-pre-wrap">{JSON.stringify(c.params, null, 2)}</pre>
                  </div>
                )}
              </>
            ) : (
              <div className="text-muted-foreground">No canary cached. Run "Run canary slice" to populate.</div>
            )}
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
        open={!!selectedTool}
        row={selectedTool}
        title={(t) => t.tool_id}
        subtitle={(t) => t.description}
        badges={(t) => [
          { label: t.group, tone: 'info' },
          { label: t.risk_level.replace(/_/g, ' '), tone: riskTone(t.risk_level) },
          { label: toolKindOf(t), tone: 'muted' },
          ...(t.requires_approval ? [{ label: 'approval', tone: 'warn' as const }] : []),
          ...(t.yaml_present ? [{ label: 'yaml', tone: 'info' as const }] : []),
          ...(t.has_canary ? [{ label: 'canary', tone: 'ok' as const }] : []),
        ]}
        tabs={drawerTabs}
        footer={(t) => (
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-muted-foreground">
              {t.connector_api ? `binds -> ${t.connector_api}` : 'No connector binding'}
            </span>
            <Button size="sm" onClick={() => openRun(t)}>
              <Play className="h-3.5 w-3.5 mr-1" /> Run
            </Button>
          </div>
        )}
        onClose={closeDrawer}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 pb-3 border-b bg-card/40 space-y-3">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <Wrench className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold">ReAct Tools Registry</h2>
              {report && (
                <span className="text-[11px] bg-muted/60 px-2 py-0.5 rounded">
                  {filtered.length} / {rows.length}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={load} disabled={loading}>
                {loading ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5 mr-1" />}
                Refresh
              </Button>
              <Button size="sm" onClick={runCanarySlice} disabled={canaryRunning || filtered.length === 0}>
                {canaryRunning ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-1" />}
                Run canary slice
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
                placeholder="Search tool_id, description, group, connector_api, tags..."
                className="pl-7 h-8 text-xs"
              />
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 flex overflow-hidden">
          <aside className="w-56 shrink-0 border-r p-3 overflow-auto">
            <FacetFilters facets={facetDescriptors} state={facets} onChange={setFacets} />
          </aside>

          <main className="flex-1 p-3 overflow-hidden flex flex-col">
            {error && (
              <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded p-2 mb-2">
                {error}
              </div>
            )}
            {loading && !report ? (
              <div className="flex items-center gap-2 text-muted-foreground text-sm py-12 justify-center">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading registry...
              </div>
            ) : (
              <RegistryTable<RegistryToolRow>
                rows={filtered}
                columns={columns}
                rowKey={(r) => r.tool_id}
                onSelect={(r) => setSelectedToolId(r.tool_id)}
                selectedKey={selectedToolId || undefined}
                emptyMessage={
                  <span className="flex items-center justify-center gap-2">
                    <BookOpen className="h-3.5 w-3.5" /> No tools match the current filters.
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
