import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Loader2, Play, RefreshCw, Wrench, Network, Zap, Settings2,
  ShieldCheck, CheckCircle2, XCircle, MinusCircle, ExternalLink,
} from 'lucide-react';
import { Section, formatLatency } from './_shared';
import ConnectorApiTestDrawer from './ConnectorApiTestDrawer';
import {
  reactToolsDiagnosticsService,
  RegistryReport,
  RegistryToolRow,
  ContractsReport,
  ContractIssue,
  ConnectorAPIReport,
  CanaryReport,
  CanaryResult,
  ExecuteResult,
} from '@/services/reactToolsDiagnosticsService';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function riskColor(risk: string): string {
  if (risk === 'high_risk_write') return 'text-red-300';
  if (risk === 'low_risk_write') return 'text-amber-300';
  return 'text-green-300';
}

function statusIcon(s: string) {
  if (s === 'pass') return <CheckCircle2 className="h-3.5 w-3.5 text-green-300" />;
  if (s === 'fail') return <XCircle className="h-3.5 w-3.5 text-red-300" />;
  return <MinusCircle className="h-3.5 w-3.5 text-muted-foreground" />;
}

// ---------------------------------------------------------------------------
// Registry section
// ---------------------------------------------------------------------------

function RegistrySection({
  report, loading, onInspect, search, setSearch, groupFilter, setGroupFilter,
}: {
  report: RegistryReport | null;
  loading: boolean;
  onInspect: (tool: RegistryToolRow) => void;
  search: string;
  setSearch: (v: string) => void;
  groupFilter: string;
  setGroupFilter: (v: string) => void;
}) {
  const filtered = useMemo(() => {
    if (!report) return [];
    const q = search.trim().toLowerCase();
    return report.tools.filter(t => {
      if (groupFilter && t.group !== groupFilter) return false;
      if (!q) return true;
      return t.tool_id.toLowerCase().includes(q)
        || t.description.toLowerCase().includes(q)
        || t.tags.some(tg => tg.toLowerCase().includes(q));
    });
  }, [report, search, groupFilter]);

  if (loading && !report) {
    return <div className="text-xs text-muted-foreground italic">Loading registry...</div>;
  }
  if (!report) return null;
  const t = report.totals;

  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <div className="text-muted-foreground text-xs">Registered</div>
          <div className="font-mono">{t.registered_tools}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">YAML</div>
          <div className="font-mono">{t.yaml_tools}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">YAML-only orphans</div>
          <div className={`font-mono ${t.yaml_only_orphans ? 'text-red-300' : ''}`}>{t.yaml_only_orphans}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Registry-only orphans</div>
          <div className={`font-mono ${t.registry_only_orphans ? 'text-amber-300' : ''}`}>{t.registry_only_orphans}</div>
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap text-xs">
        <span className="text-muted-foreground">Risk:</span>
        {Object.entries(t.by_risk_level).map(([k, v]) => (
          <Badge
            key={k}
            variant="outline"
            className={`text-[10px] ${
              k === 'high_risk_write' ? 'bg-red-500/10 text-red-300' :
              k === 'low_risk_write' ? 'bg-amber-500/10 text-amber-300' :
              'bg-green-500/10 text-green-300'
            }`}
          >
            {v} {k}
          </Badge>
        ))}
      </div>

      <div className="flex items-center gap-2 flex-wrap text-xs">
        <span className="text-muted-foreground">Groups:</span>
        <Button
          size="sm"
          variant={!groupFilter ? 'default' : 'outline'}
          className="h-6 text-[10px] px-2"
          onClick={() => setGroupFilter('')}
        >
          all ({t.registered_tools})
        </Button>
        {Object.entries(t.by_group).map(([g, c]) => (
          <Button
            key={g}
            size="sm"
            variant={groupFilter === g ? 'default' : 'outline'}
            className="h-6 text-[10px] px-2"
            onClick={() => setGroupFilter(groupFilter === g ? '' : g)}
          >
            {g} ({c})
          </Button>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <Input
          placeholder="Filter tools..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="h-7 max-w-xs text-xs"
        />
        <span className="text-xs text-muted-foreground">{filtered.length} / {report.tools.length}</span>
      </div>

      <div className="border rounded-md max-h-96 overflow-auto">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 bg-muted/40">
            <tr className="text-left">
              <th className="px-2 py-1">Tool</th>
              <th className="px-2 py-1">Group</th>
              <th className="px-2 py-1">Risk</th>
              <th className="px-2 py-1">YAML</th>
              <th className="px-2 py-1">Canary</th>
              <th className="px-2 py-1">Use cases</th>
              <th className="px-2 py-1">Connector API</th>
              <th className="px-2 py-1"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(t => (
              <tr key={t.tool_id} className="border-t border-border/40 hover:bg-muted/20">
                <td className="px-2 py-1 font-mono">{t.tool_id}</td>
                <td className="px-2 py-1 text-muted-foreground">{t.group}</td>
                <td className="px-2 py-1">
                  <span className={riskColor(t.risk_level)}>{t.risk_level}</span>
                  {t.requires_approval && (
                    <Badge variant="outline" className="text-[9px] ml-1">approval</Badge>
                  )}
                </td>
                <td className="px-2 py-1">
                  {t.yaml_present
                    ? <CheckCircle2 className="h-3.5 w-3.5 text-green-300" />
                    : <MinusCircle className="h-3.5 w-3.5 text-amber-400" />}
                </td>
                <td className="px-2 py-1">
                  {t.has_canary
                    ? <CheckCircle2 className="h-3.5 w-3.5 text-green-300" />
                    : <MinusCircle className="h-3.5 w-3.5 text-muted-foreground" />}
                </td>
                <td className="px-2 py-1 font-mono">{t.use_case_refs}</td>
                <td className="px-2 py-1 font-mono text-muted-foreground">{t.connector_api || '-'}</td>
                <td className="px-2 py-1">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-6 text-[10px] px-2"
                    onClick={() => onInspect(t)}
                  >
                    Inspect
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(report.yaml_only_orphans.length > 0) && (
        <div className="text-xs border-l-2 border-red-500/40 pl-3 py-1">
          <div className="text-red-300 mb-1">YAML-only orphans (YAML exists, tool not registered):</div>
          <div className="flex items-center gap-1 flex-wrap">
            {report.yaml_only_orphans.map(t => (
              <span key={t} className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30 font-mono text-[10px]">{t}</span>
            ))}
          </div>
        </div>
      )}
      {(report.registry_only_orphans.length > 0) && (
        <div className="text-xs border-l-2 border-amber-500/40 pl-3 py-1">
          <div className="text-amber-300 mb-1">Registry-only orphans (registered, no YAML):</div>
          <div className="flex items-center gap-1 flex-wrap">
            {report.registry_only_orphans.map(t => (
              <span key={t} className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 font-mono text-[10px]">{t}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Contracts section
// ---------------------------------------------------------------------------

function ContractsSection({ report, loading }: { report: ContractsReport | null; loading: boolean }) {
  if (loading && !report) {
    return <div className="text-xs text-muted-foreground italic">Loading contract checks...</div>;
  }
  if (!report) return null;
  const issues = Object.entries(report.issues_by_tool);
  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <div className="text-muted-foreground text-xs">Tools checked</div>
          <div className="font-mono">{report.totals.checked}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Errors</div>
          <div className={`font-mono ${report.totals.errors ? 'text-red-300' : ''}`}>{report.totals.errors}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Warnings</div>
          <div className={`font-mono ${report.totals.warnings ? 'text-amber-300' : ''}`}>{report.totals.warnings}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Tools with issues</div>
          <div className="font-mono">{report.totals.tools_with_issues}</div>
        </div>
      </div>

      {issues.length === 0 && (
        <div className="text-xs text-muted-foreground italic">No contract issues found.</div>
      )}

      <div className="space-y-2">
        {issues.map(([toolId, items]) => (
          <div key={toolId} className="border border-border/40 rounded-md px-3 py-2">
            <div className="font-mono text-xs mb-1">{toolId}</div>
            <div className="space-y-1">
              {items.map((it: ContractIssue, idx: number) => (
                <div key={idx} className="flex items-start gap-2 text-[11px]">
                  <Badge
                    variant="outline"
                    className={`text-[9px] shrink-0 ${
                      it.severity === 'error'
                        ? 'text-red-300 border-red-500/30 bg-red-500/10'
                        : 'text-amber-300 border-amber-500/30 bg-amber-500/10'
                    }`}
                  >
                    {it.severity}
                  </Badge>
                  <span className="font-mono text-muted-foreground shrink-0">{it.code}</span>
                  <span className="text-muted-foreground">{it.message}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Connector APIs section
// ---------------------------------------------------------------------------

function ConnectorAPIsSection({
  report, loading, onTest,
}: {
  report: ConnectorAPIReport | null;
  loading: boolean;
  onTest: (apiId: string) => void;
}) {
  const [systemFilter, setSystemFilter] = useState<string>('');
  const filtered = useMemo(() => {
    if (!report) return [];
    if (!systemFilter) return report.apis;
    return report.apis.filter(a => a.target_system === systemFilter);
  }, [report, systemFilter]);

  if (loading && !report) {
    return <div className="text-xs text-muted-foreground italic">Loading connector API checks...</div>;
  }
  if (!report) return null;

  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <div className="text-muted-foreground text-xs">Connector APIs</div>
          <div className="font-mono">{report.totals.checked}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Errors</div>
          <div className={`font-mono ${report.totals.errors ? 'text-red-300' : ''}`}>{report.totals.errors}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Warnings</div>
          <div className={`font-mono ${report.totals.warnings ? 'text-amber-300' : ''}`}>{report.totals.warnings}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Orphans (no caller)</div>
          <div className={`font-mono ${report.totals.orphans ? 'text-amber-300' : ''}`}>{report.totals.orphans}</div>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap text-xs">
        <span className="text-muted-foreground">Target system:</span>
        <Button
          size="sm"
          variant={!systemFilter ? 'default' : 'outline'}
          className="h-6 text-[10px] px-2"
          onClick={() => setSystemFilter('')}
        >
          all
        </Button>
        {Object.entries(report.totals.by_target_system).map(([s, c]) => (
          <Button
            key={s}
            size="sm"
            variant={systemFilter === s ? 'default' : 'outline'}
            className="h-6 text-[10px] px-2"
            onClick={() => setSystemFilter(systemFilter === s ? '' : s)}
          >
            {s} ({c})
          </Button>
        ))}
      </div>

      <div className="border rounded-md max-h-96 overflow-auto">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 bg-muted/40">
            <tr className="text-left">
              <th className="px-2 py-1">api_id</th>
              <th className="px-2 py-1">System</th>
              <th className="px-2 py-1">Operation</th>
              <th className="px-2 py-1">Risk</th>
              <th className="px-2 py-1">Schemas</th>
              <th className="px-2 py-1">Callers</th>
              <th className="px-2 py-1">Audit</th>
              <th className="px-2 py-1"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(a => (
              <tr key={a.api_id} className="border-t border-border/40">
                <td className="px-2 py-1 font-mono">{a.api_id}</td>
                <td className="px-2 py-1 text-muted-foreground">{a.target_system}</td>
                <td className="px-2 py-1 font-mono text-[10px]">{a.operation}</td>
                <td className="px-2 py-1">
                  <span className={riskColor(a.risk_level)}>{a.risk_level}</span>
                </td>
                <td className="px-2 py-1">
                  {a.has_request_schema
                    ? <CheckCircle2 className="h-3.5 w-3.5 text-green-300 inline mr-1" />
                    : <MinusCircle className="h-3.5 w-3.5 text-amber-400 inline mr-1" />}
                  req
                  {' '}
                  {a.has_response_schema
                    ? <CheckCircle2 className="h-3.5 w-3.5 text-green-300 inline mr-1" />
                    : <MinusCircle className="h-3.5 w-3.5 text-amber-400 inline mr-1" />}
                  res
                </td>
                <td className="px-2 py-1">
                  {a.tool_caller_count === 0 ? (
                    <Badge variant="outline" className="text-[9px] text-amber-300 border-amber-500/30">orphan</Badge>
                  ) : (
                    <span className="font-mono">{a.tool_caller_count}</span>
                  )}
                </td>
                <td className="px-2 py-1 font-mono">
                  {a.verified ? (
                    <span className="text-green-300">{a.audit_count ?? 0}</span>
                  ) : (
                    <span className="text-muted-foreground">0</span>
                  )}
                </td>
                <td className="px-2 py-1">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-6 text-[10px] px-2"
                    onClick={() => onTest(a.api_id)}
                  >
                    <ExternalLink className="h-3 w-3 mr-1" /> Workbench
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {report.orphan_api_ids.length > 0 && (
        <div className="text-xs border-l-2 border-amber-500/40 pl-3 py-1">
          <div className="text-amber-300 mb-1">Connector APIs with no tool caller ({report.orphan_api_ids.length}):</div>
          <div className="flex items-center gap-1 flex-wrap">
            {report.orphan_api_ids.map(a => (
              <span key={a} className="px-1.5 py-0.5 rounded bg-muted/40 font-mono text-[10px]">{a}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Execution section
// ---------------------------------------------------------------------------

function ExecutionSection({
  report, loading, onlyReadOnly, setOnlyReadOnly, onSelectTool,
}: {
  report: CanaryReport | null;
  loading: boolean;
  onlyReadOnly: boolean;
  setOnlyReadOnly: (v: boolean) => void;
  onSelectTool: (toolId: string) => void;
}) {
  if (!report && !loading) {
    return (
      <div className="text-xs text-muted-foreground space-y-2">
        <p>Click <span className="font-mono">Run all canaries</span> in the section header to invoke every tool with safe canary parameters.</p>
        <p>Read-only tools execute against live FDW / RAG / virtual-data services. Write tools execute against the simulator and tag rows with <span className="font-mono">actor=diagnostic-runner</span>.</p>
      </div>
    );
  }
  if (loading && !report) {
    return (
      <div className="text-xs text-muted-foreground italic flex items-center gap-2">
        <Loader2 className="h-3 w-3 animate-spin" /> Running canaries...
      </div>
    );
  }
  if (!report) return null;

  const t = report.totals;
  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center gap-3 flex-wrap text-xs">
        <label className="flex items-center gap-1 cursor-pointer">
          <input type="checkbox" checked={onlyReadOnly} onChange={e => setOnlyReadOnly(e.target.checked)} />
          <span>only read-only</span>
        </label>
        <span className="text-muted-foreground">| total: <span className="font-mono">{t.checked}</span></span>
        <span className="text-green-300">pass: <span className="font-mono">{t.pass}</span></span>
        <span className="text-red-300">fail: <span className="font-mono">{t.fail}</span></span>
        <span className="text-muted-foreground">skip: <span className="font-mono">{t.skip}</span></span>
        <span className="text-muted-foreground">| total: {formatLatency(t.duration_ms)}</span>
        {t.read_only_failures > 0 && (
          <Badge variant="outline" className="text-[10px] text-red-300 border-red-500/30">
            {t.read_only_failures} read-only failure(s)
          </Badge>
        )}
      </div>

      {report.error && (
        <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          {report.error}
        </div>
      )}

      <div className="border rounded-md max-h-96 overflow-auto">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 bg-muted/40">
            <tr className="text-left">
              <th className="px-2 py-1"></th>
              <th className="px-2 py-1">Tool</th>
              <th className="px-2 py-1">Risk</th>
              <th className="px-2 py-1">Latency</th>
              <th className="px-2 py-1">Result preview</th>
              <th className="px-2 py-1">Marker</th>
            </tr>
          </thead>
          <tbody>
            {report.results.map(r => (
              <tr
                key={r.tool_id}
                className="border-t border-border/40 hover:bg-muted/20 cursor-pointer"
                onClick={() => onSelectTool(r.tool_id)}
              >
                <td className="px-2 py-1">{statusIcon(r.status)}</td>
                <td className="px-2 py-1 font-mono">{r.tool_id}</td>
                <td className="px-2 py-1">
                  <span className={riskColor(r.risk_level)}>{r.risk_level}</span>
                </td>
                <td className="px-2 py-1 font-mono">{formatLatency(r.duration_ms)}</td>
                <td className="px-2 py-1">
                  {r.status === 'skip' ? (
                    <span className="text-muted-foreground italic">{r.reason || 'skipped'}</span>
                  ) : (
                    <span className={r.status === 'fail' ? 'text-red-300' : 'text-muted-foreground'}>
                      {r.result_preview || '-'}
                    </span>
                  )}
                </td>
                <td className="px-2 py-1 text-[10px] text-muted-foreground font-mono">{r.marker || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Per-tool drilldown
// ---------------------------------------------------------------------------

function PerToolDetail({
  tool, contractIssues, lastResult, onClose, onExecuted,
}: {
  tool: RegistryToolRow;
  contractIssues: ContractIssue[];
  lastResult: CanaryResult | null;
  onClose: () => void;
  onExecuted: (r: ExecuteResult) => void;
}) {
  const properties = (tool.parameters?.properties || {}) as Record<string, any>;
  const required: string[] = tool.parameters?.required || [];
  const fieldNames = Object.keys(properties);
  const [paramJson, setParamJson] = useState<string>(() => JSON.stringify({}, null, 2));
  const [paramFields, setParamFields] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const f of fieldNames) init[f] = '';
    return init;
  });
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ExecuteResult | null>(null);
  const [editMode, setEditMode] = useState<'fields' | 'json'>('fields');
  const [error, setError] = useState<string | null>(null);

  const buildParams = (): Record<string, any> => {
    if (editMode === 'json') {
      try { return JSON.parse(paramJson || '{}'); }
      catch { throw new Error('Invalid JSON'); }
    }
    const out: Record<string, any> = {};
    for (const [k, v] of Object.entries(paramFields)) {
      if (v === '') continue;
      const ptype = properties[k]?.type;
      if (ptype === 'integer') out[k] = parseInt(v, 10);
      else if (ptype === 'number') out[k] = parseFloat(v);
      else if (ptype === 'boolean') out[k] = v === 'true';
      else if (ptype === 'array' || ptype === 'object') {
        try { out[k] = JSON.parse(v); }
        catch { out[k] = v; }
      } else {
        out[k] = v;
      }
    }
    return out;
  };

  const handleExecute = async () => {
    setError(null);
    setRunning(true);
    try {
      const params = buildParams();
      const r = await reactToolsDiagnosticsService.executeOne(tool.tool_id, params);
      setResult(r);
      onExecuted(r);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="border-2 border-primary/30 rounded-md p-4 bg-primary/5 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-primary" />
            {tool.tool_id}
            <Badge variant="outline" className={`text-[10px] ${riskColor(tool.risk_level)}`}>
              {tool.risk_level}
            </Badge>
            <Badge variant="outline" className="text-[10px]">{tool.group}</Badge>
            {tool.requires_approval && (
              <Badge variant="outline" className="text-[10px] text-amber-300 border-amber-500/30">requires approval</Badge>
            )}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">{tool.description}</div>
        </div>
        <Button size="sm" variant="outline" onClick={onClose}>
          <XCircle className="h-3.5 w-3.5" />
        </Button>
      </div>

      {tool.connector_api && (
        <div className="text-xs">
          <span className="text-muted-foreground">Connector API: </span>
          <span className="font-mono">{tool.connector_api}</span>
        </div>
      )}

      {contractIssues.length > 0 && (
        <div className="text-xs border-l-2 border-amber-500/40 pl-3 py-1 space-y-1">
          <div className="text-muted-foreground mb-1">Contract issues for this tool:</div>
          {contractIssues.map((it, i) => (
            <div key={i} className="flex items-start gap-2">
              <Badge
                variant="outline"
                className={`text-[9px] ${
                  it.severity === 'error'
                    ? 'text-red-300 border-red-500/30 bg-red-500/10'
                    : 'text-amber-300 border-amber-500/30 bg-amber-500/10'
                }`}
              >
                {it.severity}
              </Badge>
              <span className="font-mono text-muted-foreground">{it.code}</span>
              <span className="text-muted-foreground">{it.message}</span>
            </div>
          ))}
        </div>
      )}

      <div>
        <div className="text-xs text-muted-foreground mb-1">parameters JSON Schema</div>
        <pre className="text-[10px] bg-background/50 rounded p-2 overflow-auto max-h-48 font-mono">
          {JSON.stringify(tool.parameters, null, 2)}
        </pre>
      </div>

      {lastResult && (
        <div>
          <div className="text-xs text-muted-foreground mb-1">Last canary run</div>
          <div className="flex items-center gap-2 text-xs">
            {statusIcon(lastResult.status)}
            <span>{lastResult.status}</span>
            <span className="text-muted-foreground">{formatLatency(lastResult.duration_ms)}</span>
            <span className="font-mono text-muted-foreground">{lastResult.result_preview}</span>
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="text-xs text-muted-foreground">Try-it</div>
          <div className="flex gap-1 text-[10px]">
            <Button
              size="sm"
              variant={editMode === 'fields' ? 'default' : 'outline'}
              className="h-6 px-2"
              onClick={() => setEditMode('fields')}
            >
              fields
            </Button>
            <Button
              size="sm"
              variant={editMode === 'json' ? 'default' : 'outline'}
              className="h-6 px-2"
              onClick={() => setEditMode('json')}
            >
              json
            </Button>
          </div>
        </div>

        {editMode === 'fields' && (
          <div className="space-y-2">
            {fieldNames.length === 0 && (
              <div className="text-xs text-muted-foreground italic">No declared parameters; will run with empty params.</div>
            )}
            {fieldNames.map(f => {
              const spec = properties[f] || {};
              const isReq = required.includes(f);
              return (
                <div key={f} className="flex items-center gap-2">
                  <span className="text-xs font-mono w-40 shrink-0">
                    {f}
                    {isReq && <span className="text-red-400 ml-0.5">*</span>}
                    <span className="text-[10px] text-muted-foreground ml-1">{spec.type || ''}</span>
                  </span>
                  <Input
                    value={paramFields[f] || ''}
                    onChange={e => setParamFields({ ...paramFields, [f]: e.target.value })}
                    placeholder={spec.description || spec.default || ''}
                    className="h-7 text-xs"
                  />
                </div>
              );
            })}
          </div>
        )}

        {editMode === 'json' && (
          <textarea
            value={paramJson}
            onChange={e => setParamJson(e.target.value)}
            spellCheck={false}
            className="w-full h-32 text-[11px] font-mono bg-background/50 border rounded p-2"
            placeholder='{}'
          />
        )}

        {error && (
          <div className="text-xs text-red-300 mt-2">{error}</div>
        )}

        <div className="flex items-center gap-2 mt-2">
          <Button size="sm" onClick={handleExecute} disabled={running}>
            {running ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-1" />}
            Execute
          </Button>
          {result && (
            <span className="text-xs text-muted-foreground">
              {statusIcon(result.status)}
              <span className="ml-1">{result.status}</span>
              <span className="ml-2 font-mono">{formatLatency(result.duration_ms)}</span>
            </span>
          )}
        </div>

        {result && (
          <div className="mt-2">
            <div className="text-xs text-muted-foreground mb-1">Result</div>
            <pre className="text-[10px] bg-background/50 rounded p-2 overflow-auto max-h-64 font-mono">
              {JSON.stringify(result.result ?? result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function ReactToolsDiagnosticsPanel() {
  const [registry, setRegistry] = useState<RegistryReport | null>(null);
  const [contracts, setContracts] = useState<ContractsReport | null>(null);
  const [connectorAPIs, setConnectorAPIs] = useState<ConnectorAPIReport | null>(null);
  const [canaries, setCanaries] = useState<CanaryReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [smokeRunning, setSmokeRunning] = useState(false);
  const [onlyReadOnly, setOnlyReadOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [groupFilter, setGroupFilter] = useState('');
  const [selectedTool, setSelectedTool] = useState<RegistryToolRow | null>(null);
  const [workbenchApiId, setWorkbenchApiId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reg, ctr, cap] = await Promise.allSettled([
        reactToolsDiagnosticsService.registry(),
        reactToolsDiagnosticsService.contracts(),
        reactToolsDiagnosticsService.connectorAPIs(),
      ]);
      if (reg.status === 'fulfilled') setRegistry(reg.value);
      else setError(`registry: ${(reg.reason as any)?.message || reg.reason}`);
      if (ctr.status === 'fulfilled') setContracts(ctr.value);
      if (cap.status === 'fulfilled') setConnectorAPIs(cap.value);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runSmoke = useCallback(async () => {
    setSmokeRunning(true);
    try {
      const r = await reactToolsDiagnosticsService.runAll({ only_read_only: onlyReadOnly });
      setCanaries(r);
    } catch (e: any) {
      setCanaries({
        totals: { checked: 0, pass: 0, fail: 0, skip: 0, read_only_failures: 0, duration_ms: 0 },
        results: [], overall: 'unhealthy', error: e?.message || String(e),
      });
    } finally {
      setSmokeRunning(false);
    }
  }, [onlyReadOnly]);

  const handleSelectToolId = useCallback((toolId: string) => {
    if (!registry) return;
    const tool = registry.tools.find(t => t.tool_id === toolId);
    if (tool) setSelectedTool(tool);
  }, [registry]);

  const lastCanaryByTool = useMemo(() => {
    const map: Record<string, CanaryResult> = {};
    if (canaries) {
      for (const r of canaries.results) map[r.tool_id] = r;
    }
    return map;
  }, [canaries]);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Wrench className="h-5 w-5 text-blue-300" />
            ReAct Tools Diagnostics
          </h2>
          <p className="text-sm text-muted-foreground">
            Verifies the ToolRegistry, validates each tool's contract and connector_api binding, and exercises every tool end-to-end with curated canary parameters.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => load()} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          {error}
        </div>
      )}

      <Section
        title={`Registry Health (${registry?.totals.registered_tools ?? 0} tools)`}
        icon={Wrench}
        status={registry?.overall || 'ok'}
        defaultOpen
      >
        <RegistrySection
          report={registry}
          loading={loading}
          onInspect={t => setSelectedTool(t)}
          search={search}
          setSearch={setSearch}
          groupFilter={groupFilter}
          setGroupFilter={setGroupFilter}
        />
      </Section>

      <Section
        title={`Contract Verification (${contracts?.totals.errors ?? 0} errors / ${contracts?.totals.warnings ?? 0} warnings)`}
        icon={ShieldCheck}
        status={contracts?.overall || 'ok'}
        defaultOpen={false}
      >
        <ContractsSection report={contracts} loading={loading} />
      </Section>

      <Section
        title={`Connector APIs (${connectorAPIs?.totals.checked ?? 0})`}
        icon={Network}
        status={connectorAPIs?.overall || 'ok'}
        defaultOpen={false}
      >
        <ConnectorAPIsSection
          report={connectorAPIs}
          loading={loading}
          onTest={(apiId) => setWorkbenchApiId(apiId)}
        />
      </Section>

      <Section
        title={`Execution Health${canaries ? ` (${canaries.totals.pass}/${canaries.totals.checked} pass)` : ''}`}
        icon={Zap}
        status={canaries?.overall || 'ok'}
        defaultOpen
        rightSlot={
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button size="sm" onClick={runSmoke} disabled={smokeRunning}>
              {smokeRunning
                ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                : <Play className="h-3.5 w-3.5 mr-1" />}
              Run all canaries
            </Button>
          </div>
        }
      >
        <ExecutionSection
          report={canaries}
          loading={smokeRunning}
          onlyReadOnly={onlyReadOnly}
          setOnlyReadOnly={setOnlyReadOnly}
          onSelectTool={handleSelectToolId}
        />
      </Section>

      {selectedTool && (
        <Section
          title={`Per-Tool Detail: ${selectedTool.tool_id}`}
          icon={Settings2}
          status="ok"
          defaultOpen
        >
          <PerToolDetail
            tool={selectedTool}
            contractIssues={contracts?.issues_by_tool[selectedTool.tool_id] || []}
            lastResult={lastCanaryByTool[selectedTool.tool_id] || null}
            onClose={() => setSelectedTool(null)}
            onExecuted={() => { /* result is shown inline; nothing else to do */ }}
          />
        </Section>
      )}

      {!loading && !registry && !error && (
        <div className="text-sm text-muted-foreground">No diagnostics yet.</div>
      )}

      {workbenchApiId && (
        <ConnectorApiTestDrawer
          apiId={workbenchApiId}
          onClose={() => { setWorkbenchApiId(null); load(); }}
        />
      )}
    </div>
  );
}
