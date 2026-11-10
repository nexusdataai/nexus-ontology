import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Loader2, Play, RefreshCw, BookOpen, Wrench, Server, ChevronDown, ChevronRight, AlertTriangle, Network, Database, Activity, CheckCircle2, XCircle, MinusCircle } from 'lucide-react';
import { Section, StatusBadge, formatLatency } from './_shared';
import {
  automationDiagnosticsService,
  AutomationDryRunReport,
  AutomationUseCaseRow,
  ToolCatalogueReport,
  SavedJourneysReport,
  CopilotRuntimeReport,
  SmokeTestReport,
  GraphIntegrityReport,
} from '@/services/automationDiagnosticsService';
import {
  dataSourceModeService,
  DataSourceModeReport,
} from '@/services/dataSourceModeService';

type Filter = 'all' | 'pass' | 'warn' | 'fail';

function UseCaseRowView({ uc }: { uc: AutomationUseCaseRow }) {
  const [open, setOpen] = useState(uc.status !== 'pass');
  return (
    <div className="border border-border/60 rounded-md mb-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-surface-2/60 text-left"
      >
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          {open ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
          <StatusBadge status={uc.status} />
          <span className="font-medium truncate">{uc.title}</span>
          <span className="font-mono text-xs text-muted-foreground truncate">{uc.use_case_id}</span>
          <Badge variant="outline" className="text-xs">{uc.solution_id}</Badge>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
          <span>{uc.stage_count}st / {uc.step_count}sp</span>
          {uc.high_risk_steps > 0 && (
            <span className="text-warning flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" /> {uc.high_risk_steps} HR
            </span>
          )}
          {uc.missing_tools.length > 0 && (
            <span className="text-destructive">missing tools: {uc.missing_tools.length}</span>
          )}
          {uc.missing_connector_apis.length > 0 && (
            <span className="text-destructive">missing apis: {uc.missing_connector_apis.length}</span>
          )}
        </div>
      </button>
      {open && (
        <div className="px-4 pb-3 pt-1 text-xs space-y-2 border-t border-border/60">
          <div className="text-muted-foreground">
            <span className="font-mono">{uc.yaml_file}</span>
          </div>
          {uc.tags.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-muted-foreground">tags:</span>
              {uc.tags.map(t => (
                <Badge key={t} variant="outline" className="text-xs">{t}</Badge>
              ))}
            </div>
          )}
          {uc.kpi_impact.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-muted-foreground">kpi:</span>
              {uc.kpi_impact.map(k => (
                <Badge key={k} variant="outline" className="text-xs bg-primary/10">{k}</Badge>
              ))}
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <div className="text-muted-foreground mb-1">Tools ({uc.tool_refs.length})</div>
              <div className="flex items-center gap-1 flex-wrap">
                {uc.tool_refs.length === 0 && <span className="text-muted-foreground italic">none</span>}
                {uc.tool_refs.map(t => {
                  const missing = uc.missing_tools.includes(t);
                  return (
                    <span
                      key={t}
                      className={`px-1.5 py-0.5 rounded font-mono text-xs ${missing ? 'bg-destructive/20 text-destructive border border-destructive/30' : 'bg-surface-2'}`}
                      title={missing ? 'Not registered in ToolRegistry' : ''}
                    >
                      {t}
                    </span>
                  );
                })}
              </div>
            </div>
            <div>
              <div className="text-muted-foreground mb-1">Connector APIs ({uc.connector_api_refs.length})</div>
              <div className="flex items-center gap-1 flex-wrap">
                {uc.connector_api_refs.length === 0 && <span className="text-muted-foreground italic">none</span>}
                {uc.connector_api_refs.map(a => {
                  const missing = uc.missing_connector_apis.includes(a);
                  return (
                    <span
                      key={a}
                      className={`px-1.5 py-0.5 rounded font-mono text-xs ${missing ? 'bg-destructive/20 text-destructive border border-destructive/30' : 'bg-surface-2'}`}
                      title={missing ? 'Not in connector_apis registry' : ''}
                    >
                      {a}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase 2 panels
// ---------------------------------------------------------------------------

function MetadataDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      title={`${label}: ${ok ? 'present' : 'missing'}`}
      className={`inline-flex items-center gap-1 text-xs ${ok ? 'text-success' : 'text-muted-foreground'}`}
    >
      {ok ? <CheckCircle2 className="h-3 w-3" /> : <MinusCircle className="h-3 w-3 opacity-50" />}
      {label}
    </span>
  );
}

function ToolCatalogueSection({ report, loading }: { report: ToolCatalogueReport | null; loading: boolean }) {
  const [filter, setFilter] = useState('');
  const [groupFilter, setGroupFilter] = useState<string>('');

  const filtered = useMemo(() => {
    if (!report) return [];
    const q = filter.trim().toLowerCase();
    return report.tools.filter(t => {
      if (groupFilter && t.group !== groupFilter) return false;
      if (!q) return true;
      return (
        t.tool_id.toLowerCase().includes(q) ||
        t.display_name.toLowerCase().includes(q) ||
        t.tags.some(tg => tg.toLowerCase().includes(q))
      );
    });
  }, [report, filter, groupFilter]);

  if (loading && !report) {
    return <div className="text-xs text-muted-foreground italic">Loading tool catalogue...</div>;
  }
  if (!report) return null;

  const t = report.totals;
  const m = report.metadata_quality;
  const r = report.risk_distribution;
  const yamlTotal = t.yaml_tools || 1;

  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <div className="text-muted-foreground text-xs">YAML tools</div>
          <div className="font-mono">{t.yaml_tools}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Registered tools</div>
          <div className="font-mono">{t.registered_tools}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">YAML-only orphans</div>
          <div className={`font-mono ${t.yaml_only_orphans ? 'text-destructive' : ''}`}>{t.yaml_only_orphans}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Registry-only orphans</div>
          <div className={`font-mono ${t.registry_only_orphans ? 'text-warning' : ''}`}>{t.registry_only_orphans}</div>
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap text-xs">
        <span className="text-muted-foreground">Risk:</span>
        <Badge variant="outline" className="text-xs bg-success/10 text-success">{r.read_only} read-only</Badge>
        <Badge variant="outline" className="text-xs bg-warning/10 text-warning">{r.low_risk_write} low-risk</Badge>
        <Badge variant="outline" className="text-xs bg-destructive/10 text-destructive">{r.high_risk_write} high-risk</Badge>
      </div>

      <div className="flex items-center gap-3 flex-wrap text-xs">
        <span className="text-muted-foreground">Metadata quality:</span>
        <Badge variant="outline" className="text-xs">consumes {m.with_consumes_entities}/{yamlTotal}</Badge>
        <Badge variant="outline" className="text-xs">produces {m.with_produces_entities}/{yamlTotal}</Badge>
        <Badge variant="outline" className="text-xs">connector_api {m.with_connector_api}/{yamlTotal}</Badge>
        <Badge variant="outline" className="text-xs">tags {m.with_tags}/{yamlTotal}</Badge>
        <Badge variant="outline" className="text-xs">example {m.with_example_invocation}/{yamlTotal}</Badge>
      </div>

      <div className="flex items-center gap-2 flex-wrap text-xs">
        <span className="text-muted-foreground">Groups:</span>
        <Button
          size="sm"
          variant={!groupFilter ? 'default' : 'outline'}
          className="h-6 text-xs px-2"
          onClick={() => setGroupFilter('')}
        >
          all ({t.yaml_tools})
        </Button>
        {Object.entries(t.groups).map(([g, c]) => (
          <Button
            key={g}
            size="sm"
            variant={groupFilter === g ? 'default' : 'outline'}
            className="h-6 text-xs px-2"
            onClick={() => setGroupFilter(groupFilter === g ? '' : g)}
          >
            {g} ({c})
          </Button>
        ))}
      </div>

      {report.yaml_only_orphans.length > 0 && (
        <div className="text-xs border-l-2 border-destructive/40 pl-3 py-1">
          <div className="text-destructive mb-1">YAML refers to tools not registered ({report.yaml_only_orphans.length}):</div>
          <div className="flex items-center gap-1 flex-wrap">
            {report.yaml_only_orphans.map(t => (
              <span key={t} className="px-1.5 py-0.5 rounded bg-destructive/20 text-destructive border border-destructive/30 font-mono text-xs">{t}</span>
            ))}
          </div>
        </div>
      )}

      {report.registry_only_orphans.length > 0 && (
        <div className="text-xs border-l-2 border-warning/40 pl-3 py-1">
          <div className="text-warning mb-1">Tools registered but no YAML ({report.registry_only_orphans.length}) - invisible to KG retrieval:</div>
          <div className="flex items-center gap-1 flex-wrap">
            {report.registry_only_orphans.map(t => (
              <span key={t} className="px-1.5 py-0.5 rounded bg-warning/10 text-warning border border-warning/30 font-mono text-xs">{t}</span>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center gap-2">
        <Input
          placeholder="Filter tools..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="h-7 max-w-xs text-xs"
        />
        <span className="text-xs text-muted-foreground">{filtered.length} / {report.tools.length}</span>
      </div>

      <div className="border rounded-md max-h-80 overflow-auto">
        <table className="w-full border-collapse text-sm">
          <thead className="sticky top-0 bg-surface-2">
            <tr className="text-left">
              <th className="px-2 py-1">Tool</th>
              <th className="px-2 py-1">Group</th>
              <th className="px-2 py-1">Risk</th>
              <th className="px-2 py-1">Metadata</th>
              <th className="px-2 py-1">Connector API</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(tool => (
              <tr key={tool.tool_id} className="border-t border-border hover:bg-surface-2/60">
                <td className="px-2 py-1">
                  <div className="font-mono">{tool.tool_id}</div>
                  {!tool.yaml_present && (
                    <Badge variant="outline" className="text-xs text-warning border-warning/30 mt-0.5">no yaml</Badge>
                  )}
                  {!tool.registered && (
                    <Badge variant="outline" className="text-xs text-destructive border-destructive/30 mt-0.5">not registered</Badge>
                  )}
                </td>
                <td className="px-2 py-1 text-muted-foreground">{tool.group}</td>
                <td className="px-2 py-1">
                  <span className={
                    tool.risk_level === 'high_risk_write' ? 'text-destructive' :
                    tool.risk_level === 'low_risk_write' ? 'text-warning' : 'text-success'
                  }>{tool.risk_level}</span>
                  {tool.requires_approval && (
                    <Badge variant="outline" className="text-xs ml-1">approval</Badge>
                  )}
                </td>
                <td className="px-2 py-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <MetadataDot ok={tool.consumes_count > 0} label="consumes" />
                    <MetadataDot ok={tool.produces_count > 0} label="produces" />
                    <MetadataDot ok={tool.tags.length > 0} label="tags" />
                    <MetadataDot ok={tool.example_invocation} label="example" />
                  </div>
                </td>
                <td className="px-2 py-1 font-mono text-muted-foreground">
                  {tool.connector_api || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function GraphIntegritySection({
  report, integrity, runtime, loading,
}: {
  report: ToolCatalogueReport | null;
  integrity: GraphIntegrityReport | null;
  runtime: CopilotRuntimeReport | null;
  loading: boolean;
}) {
  if (loading && !integrity && !runtime) {
    return <div className="text-xs text-muted-foreground italic">Loading graph health...</div>;
  }

  const vec = runtime?.vector_index || {};
  const ageOk = !!runtime?.knowledge_graph?.age_available;

  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs">
        {([
          ['onto_use_case', 'Use Cases'],
          ['onto_stage', 'Stages'],
          ['onto_step', 'Steps'],
          ['onto_tool_binding', 'Bindings'],
          ['onto_connector_api', 'APIs'],
          ['onto_tool', 'Tools'],
        ] as const).map(([key, label]) => (
          <div key={key} className="rounded border border-border/50 p-2">
            <div className="text-muted-foreground text-xs">{label}</div>
            <div className="font-mono text-base">{vec[key] ?? 0}</div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3 flex-wrap text-xs">
        <span className="text-muted-foreground">Knowledge graph backend:</span>
        {ageOk ? (
          <Badge variant="outline" className="text-xs bg-success/10 text-success border-success/30">AGE Cypher</Badge>
        ) : (
          <Badge variant="outline" className="text-xs bg-warning/10 text-warning border-warning/30">metadata fallback</Badge>
        )}
        {integrity && (
          <>
            <span className="text-muted-foreground">| Use cases checked:</span>
            <span className="font-mono">{integrity.use_cases_checked}</span>
            <span className="text-muted-foreground">| Broken edges:</span>
            <span className={`font-mono ${integrity.broken_edges.length ? 'text-destructive' : ''}`}>
              {integrity.broken_edges.length}
            </span>
          </>
        )}
      </div>

      {integrity && integrity.broken_edges.length > 0 && (
        <div className="text-xs border-l-2 border-destructive/40 pl-3 py-1 space-y-1">
          {integrity.broken_edges.slice(0, 12).map((e, i) => (
            <div key={i} className="font-mono">
              <span className="text-muted-foreground">{e.use_case_id}</span>
              <span className="text-destructive"> -[{e.type}]-&gt; </span>
              <span className="text-destructive">{e.missing_target}</span>
            </div>
          ))}
          {integrity.broken_edges.length > 12 && (
            <div className="text-muted-foreground italic">
              ... and {integrity.broken_edges.length - 12} more
            </div>
          )}
        </div>
      )}

      {integrity && integrity.orphan_registry_tools && integrity.orphan_registry_tools.length > 0 && (
        <div className="text-xs">
          <div className="text-muted-foreground mb-1">
            Orphan registry tools (no use case references): {integrity.orphan_registry_tools.length}
          </div>
          <div className="flex items-center gap-1 flex-wrap">
            {integrity.orphan_registry_tools.slice(0, 30).map(t => (
              <span key={t} className="px-1.5 py-0.5 rounded bg-surface-2 font-mono text-xs">{t}</span>
            ))}
            {integrity.orphan_registry_tools.length > 30 && (
              <span className="text-muted-foreground italic">+{integrity.orphan_registry_tools.length - 30} more</span>
            )}
          </div>
        </div>
      )}

      {report?.errors && report.errors.length > 0 && (
        <div className="text-xs text-destructive">
          {report.errors.length} indexer error(s) - see Tool Catalogue panel.
        </div>
      )}
    </div>
  );
}

function SavedJourneysSection({ report, loading }: { report: SavedJourneysReport | null; loading: boolean }) {
  if (loading && !report) {
    return <div className="text-xs text-muted-foreground italic">Loading saved journeys...</div>;
  }
  if (!report) return null;

  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <div className="text-muted-foreground text-xs">Total saved</div>
          <div className="font-mono">{report.total}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Broken (need re-author)</div>
          <div className={`font-mono ${report.broken_journeys.length ? 'text-destructive' : ''}`}>
            {report.broken_journeys.length}
          </div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">By kind</div>
          <div className="flex items-center gap-1 flex-wrap">
            {Object.entries(report.by_kind).map(([k, v]) => (
              <Badge key={k} variant="outline" className="text-xs">{k}: {v}</Badge>
            ))}
            {Object.keys(report.by_kind).length === 0 && (
              <span className="text-muted-foreground text-xs">-</span>
            )}
          </div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">By solution</div>
          <div className="flex items-center gap-1 flex-wrap">
            {Object.entries(report.by_solution).slice(0, 3).map(([k, v]) => (
              <Badge key={k} variant="outline" className="text-xs">{k}: {v}</Badge>
            ))}
            {Object.keys(report.by_solution).length > 3 && (
              <span className="text-muted-foreground text-xs">+{Object.keys(report.by_solution).length - 3}</span>
            )}
            {Object.keys(report.by_solution).length === 0 && (
              <span className="text-muted-foreground text-xs">-</span>
            )}
          </div>
        </div>
      </div>

      {report.broken_journeys.length > 0 && (
        <div className="text-xs border-l-2 border-destructive/40 pl-3 py-1 space-y-1">
          <div className="text-destructive mb-1">Journeys that no longer validate:</div>
          {report.broken_journeys.slice(0, 8).map(j => (
            <div key={j.journey_id} className="space-y-0.5">
              <div className="font-mono">{j.title || j.journey_id}</div>
              <div className="text-muted-foreground">
                {j.missing_tools.length > 0 && (
                  <span>missing tools: <span className="text-destructive">{j.missing_tools.join(', ')}</span></span>
                )}
                {j.missing_connector_apis.length > 0 && (
                  <span className="ml-2">missing apis: <span className="text-destructive">{j.missing_connector_apis.join(', ')}</span></span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {report.recent.length > 0 && (
        <div>
          <div className="text-muted-foreground text-xs mb-1">Recent saves</div>
          <div className="border rounded-md max-h-72 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead className="sticky top-0 bg-surface-2">
                <tr className="text-left">
                  <th className="px-2 py-1">Title</th>
                  <th className="px-2 py-1">Kind</th>
                  <th className="px-2 py-1">Solution</th>
                  <th className="px-2 py-1">Steps</th>
                  <th className="px-2 py-1">Author</th>
                  <th className="px-2 py-1">Updated</th>
                </tr>
              </thead>
              <tbody>
                {report.recent.map(j => (
                  <tr key={j.journey_id} className="border-t border-border">
                    <td className="px-2 py-1">
                      <span className="font-mono">{j.title || j.journey_id}</span>
                      {!j.validation_ok && (
                        <Badge variant="outline" className="ml-1 text-xs text-destructive border-destructive/30">broken</Badge>
                      )}
                    </td>
                    <td className="px-2 py-1 text-muted-foreground">{j.kind}</td>
                    <td className="px-2 py-1 text-muted-foreground">{j.solution_id || '-'}</td>
                    <td className="px-2 py-1 font-mono">{j.step_count}</td>
                    <td className="px-2 py-1 text-muted-foreground">{j.createdBy || '-'}</td>
                    <td className="px-2 py-1 text-muted-foreground">
                      {j.updatedAt ? new Date(j.updatedAt).toLocaleString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {report.total === 0 && (
        <div className="text-xs text-muted-foreground italic">
          No saved journeys yet. Use the AI Copilot tab to plan and save a journey.
        </div>
      )}
    </div>
  );
}

function CopilotRuntimeSection({
  report, modes, loading,
}: {
  report: CopilotRuntimeReport | null;
  modes: DataSourceModeReport | null;
  loading: boolean;
}) {
  if (loading && !report) {
    return <div className="text-xs text-muted-foreground italic">Loading runtime status...</div>;
  }
  if (!report) return null;

  const ss = report.session_store;
  const total = Math.max(1, ss.recent_count);
  const statusColor = (s: string): string => {
    if (s === 'completed') return 'bg-success/40 text-success';
    if (s === 'awaiting_step_approval') return 'bg-warning/40 text-warning';
    if (s === 'rejected' || s === 'error') return 'bg-destructive/40 text-destructive';
    return 'bg-primary/40 text-primary';
  };

  return (
    <div className="space-y-3 text-sm">
      {modes && (
        <div>
          <div className="text-muted-foreground text-xs mb-1">Data Source Modes</div>
          <div className="flex items-center gap-2 flex-wrap">
            {(modes.available_sources || []).map(src => {
              const mode = modes.modes[src] || modes.default;
              return (
                <Badge
                  key={src}
                  variant="outline"
                  className={`text-xs ${
                    mode === 'simulator'
                      ? 'bg-warning/10 text-warning border-warning/30'
                      : 'bg-success/10 text-success border-success/30'
                  }`}
                  title={`${src}: ${mode}`}
                >
                  {src}: {mode}
                </Badge>
              );
            })}
            <Badge variant="outline" className="text-xs text-muted-foreground">
              default {modes.default}
            </Badge>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <div className="text-muted-foreground text-xs">Session store</div>
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={
                ss.mode === 'pg'
                  ? 'text-success border-success/30'
                  : 'text-warning border-warning/30'
              }
            >
              {ss.mode}
            </Badge>
            {ss.mode === 'memory' && (
              <span className="text-xs text-warning">multi-replica unsafe</span>
            )}
          </div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Recent sessions</div>
          <div className="font-mono">{ss.recent_count}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Stuck approvals (24h)</div>
          <div className={`font-mono ${ss.stuck_awaiting_approval_24h ? 'text-warning' : ''}`}>
            {ss.stuck_awaiting_approval_24h}
          </div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Registries</div>
          <div className="font-mono text-xs">
            {report.tool_registry_size} tools, {report.connector_api_registry_size} APIs
          </div>
        </div>
      </div>

      {Object.keys(ss.by_status).length > 0 && (
        <div>
          <div className="text-muted-foreground text-xs mb-1">Sessions by status</div>
          <div className="flex h-3 rounded overflow-hidden border border-border/50">
            {Object.entries(ss.by_status).map(([status, n]) => {
              const pct = (n / total) * 100;
              return (
                <div
                  key={status}
                  className={statusColor(status)}
                  style={{ width: `${pct}%` }}
                  title={`${status}: ${n}`}
                />
              );
            })}
          </div>
          <div className="flex items-center gap-2 flex-wrap mt-1 text-xs">
            {Object.entries(ss.by_status).map(([status, n]) => (
              <Badge key={status} variant="outline" className="text-xs">
                {status}: {n}
              </Badge>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="text-muted-foreground text-xs mb-1">Vector index</div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
          {Object.entries(report.vector_index).map(([ct, n]) => (
            <div key={ct} className="border border-border/50 rounded px-2 py-1">
              <div className="text-muted-foreground text-xs font-mono">{ct}</div>
              <div className="font-mono">{n}</div>
            </div>
          ))}
          {Object.keys(report.vector_index).length === 0 && (
            <span className="text-muted-foreground italic text-xs">No vector store rows reported</span>
          )}
        </div>
      </div>
    </div>
  );
}

function SmokeTestSection({
  report, loading, onRun,
}: { report: SmokeTestReport | null; loading: boolean; onRun: () => void }) {
  if (!report && !loading) {
    return (
      <div className="text-xs text-muted-foreground space-y-2">
        <p>End-to-end check: plan -&gt; execute -&gt; save -&gt; list -&gt; run-saved -&gt; cleanup.</p>
        <p>Click <span className="font-mono">Run smoke test</span> in the section header to validate the full Copilot stack against the live registries.</p>
      </div>
    );
  }
  if (loading && !report) {
    return (
      <div className="text-xs text-muted-foreground italic flex items-center gap-2">
        <Loader2 className="h-3 w-3 animate-spin" /> Running end-to-end smoke test...
      </div>
    );
  }
  if (!report) return null;

  const stageIcon = (s: string) => {
    if (s === 'pass') return <CheckCircle2 className="h-3.5 w-3.5 text-success" />;
    if (s === 'fail') return <XCircle className="h-3.5 w-3.5 text-destructive" />;
    return <MinusCircle className="h-3.5 w-3.5 text-muted-foreground" />;
  };

  return (
    <div className="space-y-3 text-sm">
      <div className="text-xs text-muted-foreground">
        <span className="font-mono">{report.goal}</span>
      </div>
      <div className="space-y-2">
        {report.stages.map(stg => (
          <div key={stg.name} className="flex items-start gap-3 border border-border/40 rounded px-3 py-2">
            <div className="mt-0.5">{stageIcon(stg.status)}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium">{stg.name}</span>
                <Badge variant="outline" className="text-xs">{stg.status}</Badge>
                <span className="text-xs text-muted-foreground">{formatLatency(stg.duration_ms)}</span>
              </div>
              {stg.detail && Object.keys(stg.detail).length > 0 && (
                <pre className="text-xs text-muted-foreground mt-1 whitespace-pre-wrap break-all font-mono">
                  {JSON.stringify(stg.detail)}
                </pre>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 text-xs">
        {report.session_id && <span className="text-muted-foreground">session: <span className="font-mono">{report.session_id}</span></span>}
        {report.journey_id && <span className="text-muted-foreground">journey: <span className="font-mono">{report.journey_id}</span></span>}
      </div>
    </div>
  );
}

export default function AutomationDiagnosticsPanel() {
  const [report, setReport] = useState<AutomationDryRunReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');

  const [toolCat, setToolCat] = useState<ToolCatalogueReport | null>(null);
  const [savedJourneys, setSavedJourneys] = useState<SavedJourneysReport | null>(null);
  const [runtime, setRuntime] = useState<CopilotRuntimeReport | null>(null);
  const [integrity, setIntegrity] = useState<GraphIntegrityReport | null>(null);
  const [modes, setModes] = useState<DataSourceModeReport | null>(null);
  const [phase2Loading, setPhase2Loading] = useState(false);
  const [smoke, setSmoke] = useState<SmokeTestReport | null>(null);
  const [smokeLoading, setSmokeLoading] = useState(false);

  const load = useCallback(async (force = false) => {
    setLoading(true); setError(null);
    setPhase2Loading(true);
    try {
      const fn = force ? automationDiagnosticsService.dryRun : automationDiagnosticsService.status;
      const r = await fn();
      setReport(r);
    } catch (e: any) {
      setError(e?.message || 'Automation diagnostics failed');
    } finally {
      setLoading(false);
    }
    // Phase 2 sections fan-out in parallel; failures are non-fatal.
    try {
      const [tc, sj, rt, gi, dm] = await Promise.allSettled([
        automationDiagnosticsService.toolCatalogue(),
        automationDiagnosticsService.savedJourneys(),
        automationDiagnosticsService.copilotRuntime(),
        automationDiagnosticsService.graphIntegrity(),
        dataSourceModeService.list(),
      ]);
      if (tc.status === 'fulfilled') setToolCat(tc.value);
      if (sj.status === 'fulfilled') setSavedJourneys(sj.value);
      if (rt.status === 'fulfilled') setRuntime(rt.value);
      if (gi.status === 'fulfilled') setIntegrity(gi.value);
      if (dm.status === 'fulfilled') setModes(dm.value);
    } finally {
      setPhase2Loading(false);
    }
  }, []);

  const runSmoke = useCallback(async () => {
    setSmokeLoading(true);
    try {
      const r = await automationDiagnosticsService.smokeTest();
      setSmoke(r);
    } catch (e: any) {
      setSmoke({
        overall: 'unhealthy',
        goal: '',
        session_id: null,
        journey_id: null,
        stages: [{ name: 'request', status: 'fail', duration_ms: 0, detail: { error: e?.message } }],
      });
    } finally {
      setSmokeLoading(false);
    }
  }, []);

  useEffect(() => { load(false); }, [load]);

  const filtered = useMemo(() => {
    if (!report) return [];
    const q = search.trim().toLowerCase();
    return report.use_cases.filter(uc => {
      if (filter !== 'all' && uc.status !== filter) return false;
      if (!q) return true;
      return (
        uc.use_case_id.toLowerCase().includes(q) ||
        uc.title.toLowerCase().includes(q) ||
        uc.solution_id.toLowerCase().includes(q)
      );
    });
  }, [report, filter, search]);

  const counts = useMemo(() => {
    if (!report) return { pass: 0, warn: 0, fail: 0 };
    let pass = 0, warn = 0, fail = 0;
    for (const uc of report.use_cases) {
      if (uc.status === 'pass') pass++;
      else if (uc.status === 'warn') warn++;
      else fail++;
    }
    return { pass, warn, fail };
  }, [report]);

  return (
    <div className="page space-y-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-medium tracking-tight text-foreground">Automation Diagnostics
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Validates every Use Case YAML and cross-references each tool / connector_api against the live registries used by the AI Copilot.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => load(false)} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          <Button size="sm" onClick={() => load(true)} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Play className="h-4 w-4 mr-1" />}
            Run Dry-Run
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/25 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {report && (
        <>
          <Section
            title="Summary"
            icon={BookOpen}
            status={report.overall}
            defaultOpen
            rightSlot={
              <span className="text-xs text-muted-foreground">{report.totals.use_cases} use cases</span>
            }
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <div className="text-muted-foreground text-xs">Stages / Steps</div>
                <div className="font-mono">{report.totals.stages} / {report.totals.steps}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Tool bindings</div>
                <div className="font-mono">{report.totals.tool_bindings}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Connector APIs</div>
                <div className="font-mono">{report.totals.connector_apis}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">High-risk steps</div>
                <div className="font-mono">{report.totals.high_risk_steps}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Pass / Warn / Fail</div>
                <div className="font-mono">
                  <span className="text-success">{counts.pass}</span> /{' '}
                  <span className="text-warning">{counts.warn}</span> /{' '}
                  <span className="text-destructive">{counts.fail}</span>
                </div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Missing tools</div>
                <div className={`font-mono ${report.totals.missing_tools ? 'text-destructive' : ''}`}>
                  {report.totals.missing_tools}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Missing connector APIs</div>
                <div className={`font-mono ${report.totals.missing_connector_apis ? 'text-destructive' : ''}`}>
                  {report.totals.missing_connector_apis}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Validation errors</div>
                <div className={`font-mono ${report.validation_errors ? 'text-destructive' : ''}`}>
                  {report.validation_errors}
                </div>
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground font-mono">{report.yaml_root}</div>
          </Section>

          <Section
            title={`Tool Catalogue (${toolCat?.totals.yaml_tools ?? 0} YAML / ${toolCat?.totals.registered_tools ?? 0} registered)`}
            icon={Wrench}
            status={toolCat?.overall || 'ok'}
            defaultOpen={false}
          >
            <ToolCatalogueSection report={toolCat} loading={phase2Loading} />
          </Section>

          <Section
            title={`Knowledge Graph (${integrity?.broken_edges.length ?? 0} broken edges)`}
            icon={Network}
            status={
              integrity?.broken_edges.length
                ? 'fail'
                : runtime?.knowledge_graph.age_available
                  ? 'ok'
                  : 'warn'
            }
            defaultOpen={false}
          >
            <GraphIntegritySection
              report={toolCat}
              integrity={integrity}
              runtime={runtime}
              loading={phase2Loading}
            />
          </Section>

          <Section
            title={`Saved Journeys (${savedJourneys?.total ?? 0})`}
            icon={BookOpen}
            status={savedJourneys?.overall === 'unknown' ? 'warn' : (savedJourneys?.overall || 'ok')}
            defaultOpen={false}
          >
            <SavedJourneysSection report={savedJourneys} loading={phase2Loading} />
          </Section>

          <Section
            title={`Copilot Runtime (${runtime?.session_store.mode ?? 'unknown'} store)`}
            icon={Database}
            status={runtime?.overall || 'ok'}
            defaultOpen={false}
          >
            <CopilotRuntimeSection report={runtime} modes={modes} loading={phase2Loading} />
          </Section>

          <Section
            title="End-to-End Smoke Test"
            icon={Activity}
            status={smoke?.overall || 'ok'}
            defaultOpen={false}
            rightSlot={
              <div onClick={(e) => e.stopPropagation()}>
                <Button size="sm" onClick={runSmoke} disabled={smokeLoading}>
                  {smokeLoading
                    ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                    : <Play className="h-3.5 w-3.5 mr-1" />}
                  Run smoke test
                </Button>
              </div>
            }
          >
            <SmokeTestSection report={smoke} loading={smokeLoading} onRun={runSmoke} />
          </Section>

          <Section
            title="Registries"
            icon={Server}
            status="ok"
            defaultOpen={false}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <div className="text-muted-foreground mb-1">
                  ToolRegistry ({report.registry.known_tools.length})
                </div>
                <div className="flex items-center gap-1 flex-wrap">
                  {report.registry.known_tools.map(t => (
                    <span key={t} className="px-1.5 py-0.5 rounded bg-surface-2 font-mono text-xs">{t}</span>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground mb-1">
                  Connector APIs ({report.registry.known_connector_apis.length})
                </div>
                <div className="flex items-center gap-1 flex-wrap">
                  {report.registry.known_connector_apis.map(a => (
                    <span key={a} className="px-1.5 py-0.5 rounded bg-surface-2 font-mono text-xs">{a}</span>
                  ))}
                </div>
              </div>
            </div>
          </Section>

          {report.errors.length > 0 && (
            <Section title="YAML validation errors" icon={AlertTriangle} status="fail" defaultOpen>
              <div className="space-y-2 text-xs">
                {report.errors.map((e, i) => (
                  <div key={i} className="border-l-2 border-destructive/40 pl-3">
                    <div className="font-mono text-destructive">{e.file}</div>
                    <pre className="text-muted-foreground whitespace-pre-wrap break-all">{e.error}</pre>
                  </div>
                ))}
              </div>
            </Section>
          )}

          <Section
            title={`Use cases (${filtered.length} / ${report.use_cases.length})`}
            icon={Wrench}
            status={report.overall}
            defaultOpen
            rightSlot={
              <div
                className="flex items-center gap-2"
                onClick={(e) => e.stopPropagation()}
              >
                <Input
                  placeholder="Filter..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="h-7 w-40 text-xs"
                />
                {(['all', 'pass', 'warn', 'fail'] as Filter[]).map(f => (
                  <Button
                    key={f}
                    size="sm"
                    variant={filter === f ? 'default' : 'outline'}
                    className="h-7 text-xs px-2"
                    onClick={() => setFilter(f)}
                  >
                    {f}
                  </Button>
                ))}
              </div>
            }
          >
            <div>
              {filtered.length === 0 && (
                <div className="text-xs text-muted-foreground italic">No use cases match the current filter.</div>
              )}
              {filtered.map(uc => <UseCaseRowView key={uc.use_case_id} uc={uc} />)}
            </div>
          </Section>
        </>
      )}

      {!report && !error && !loading && (
        <div className="text-sm text-muted-foreground">No automation diagnostics yet.</div>
      )}
    </div>
  );
}
