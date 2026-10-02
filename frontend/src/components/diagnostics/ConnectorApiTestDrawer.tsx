import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2, ChevronRight, Loader2, MinusCircle, Play, RefreshCw, X, XCircle,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatLatency } from './_shared';
import {
  connectorApiWorkbenchService,
  type AuditEvent,
  type ConnectorAPIDetail,
  type InvokeResponse,
  type Verdict,
} from '@/services/connectorApiWorkbenchService';
import { reactToolsDiagnosticsService } from '@/services/reactToolsDiagnosticsService';

interface Props {
  apiId: string;
  onClose: () => void;
}

type ResultTab = 'response' | 'verification' | 'audit' | 'curl';

function verdictBadge(v: Verdict | null) {
  if (!v) return null;
  const cls =
    v === 'verified' ? 'bg-green-500/15 text-green-300 border-green-500/30'
    : v === 'no_change' ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
    : v === 'audit_missing' ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
    : 'bg-red-500/15 text-red-300 border-red-500/30';
  return (
    <Badge variant="outline" className={`text-[10px] ${cls}`}>{v}</Badge>
  );
}

function statusIcon(s?: string) {
  if (s === 'pass' || s === 'verified') return <CheckCircle2 className="h-3.5 w-3.5 text-green-300" />;
  if (s === 'fail' || s === 'http_error') return <XCircle className="h-3.5 w-3.5 text-red-300" />;
  return <MinusCircle className="h-3.5 w-3.5 text-amber-300" />;
}

function buildCurl(api: ConnectorAPIDetail, body: Record<string, unknown>): string {
  const parts = api.operation.split(' ');
  const method = parts[0] || 'POST';
  let path = parts[1] || '';
  const remaining: Record<string, unknown> = { ...body };
  Object.keys(remaining).forEach((k) => {
    const ph = `{${k}}`;
    if (path.includes(ph)) {
      path = path.replace(ph, String(remaining[k]));
      delete remaining[k];
    }
  });
  const json = JSON.stringify(remaining, null, 2);
  return `curl -X ${method} \\\n  http://localhost:8000${path} \\\n  -H 'Content-Type: application/json' \\\n  -d '${json}'`;
}

export default function ConnectorApiTestDrawer({ apiId, onClose }: Props) {
  const [detail, setDetail] = useState<ConnectorAPIDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payloadJson, setPayloadJson] = useState<string>('{}');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<InvokeResponse | null>(null);
  const [resultTab, setResultTab] = useState<ResultTab>('response');
  const [toolRunning, setToolRunning] = useState<string | null>(null);
  const [toolResult, setToolResult] = useState<{ tool: string; status: string; preview?: string; result?: any } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await connectorApiWorkbenchService.get(apiId);
      setDetail(d);
      try {
        const cp = await connectorApiWorkbenchService.canaryPayload(apiId);
        setPayloadJson(JSON.stringify(cp.payload || {}, null, 2));
      } catch {
        setPayloadJson(JSON.stringify({}, null, 2));
      }
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [apiId]);

  useEffect(() => { load(); }, [load]);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const payload = payloadJson.trim() ? JSON.parse(payloadJson) : {};
      const r = await connectorApiWorkbenchService.invoke(apiId, payload);
      setResult(r);
      setResultTab(r.verdict === 'http_error' ? 'response' : 'verification');
      load();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setRunning(false);
    }
  };

  const handleRunViaTool = async (toolId: string) => {
    setToolRunning(toolId);
    setToolResult(null);
    try {
      const payload = payloadJson.trim() ? JSON.parse(payloadJson) : {};
      const r = await reactToolsDiagnosticsService.executeOne(toolId, payload);
      setToolResult({
        tool: toolId,
        status: r.status,
        preview: r.result_preview,
        result: r.result,
      });
      load();
    } catch (e: any) {
      setToolResult({ tool: toolId, status: 'fail', preview: e?.message || String(e) });
    } finally {
      setToolRunning(null);
    }
  };

  const usePresetPayload = async () => {
    try {
      const cp = await connectorApiWorkbenchService.canaryPayload(apiId);
      setPayloadJson(JSON.stringify(cp.payload || {}, null, 2));
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  };

  const curlText = useMemo(() => {
    if (!detail) return '';
    try {
      const body = payloadJson.trim() ? JSON.parse(payloadJson) : {};
      return buildCurl(detail, body);
    } catch {
      return '';
    }
  }, [detail, payloadJson]);

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="w-full max-w-2xl bg-background border-l border-border h-full overflow-y-auto shadow-2xl">
        <div className="sticky top-0 bg-background z-10 border-b border-border px-5 py-3 flex items-center justify-between">
          <div className="min-w-0">
            <div className="font-mono text-sm truncate">{apiId}</div>
            {detail && (
              <div className="font-mono text-[10px] text-muted-foreground truncate">{detail.operation}</div>
            )}
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-5 space-y-4">
          {loading && !detail && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading API spec...
            </div>
          )}
          {error && (
            <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
              {error}
            </div>
          )}

          {detail && (
            <>
              <div className="flex flex-wrap items-center gap-2 text-[10px]">
                <Badge variant="outline">{detail.target_system}</Badge>
                <Badge variant="outline">{detail.risk_level}</Badge>
                {detail.simulator_writeback && <Badge variant="outline">simulator-writeback</Badge>}
                {detail.verified
                  ? <Badge variant="outline" className="text-green-300 border-green-500/30">verified</Badge>
                  : <Badge variant="outline" className="text-amber-300 border-amber-500/30">never invoked</Badge>}
                {!detail.has_verification_hint && (
                  <Badge variant="outline" className="text-amber-300 border-amber-500/30">no verify hint</Badge>
                )}
                {detail.tags.map(t => (
                  <Badge key={t} variant="outline">{t}</Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">{detail.description}</p>

              <div>
                <div className="text-[11px] font-semibold text-muted-foreground uppercase mb-1.5">Tool callers ({detail.tool_caller_count})</div>
                {detail.tool_callers.length === 0 ? (
                  <div className="text-xs text-amber-300">No registered tool calls this connector API.</div>
                ) : (
                  <div className="flex flex-wrap items-center gap-1.5">
                    {detail.tool_callers.map(t => (
                      <Button
                        key={t}
                        variant="outline"
                        size="sm"
                        className="h-7 text-[10px]"
                        onClick={() => handleRunViaTool(t)}
                        disabled={!!toolRunning}
                      >
                        {toolRunning === t
                          ? <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          : <Play className="h-3 w-3 mr-1" />}
                        {t}
                      </Button>
                    ))}
                  </div>
                )}
              </div>

              {toolResult && (
                <div className="text-[11px] border rounded p-2 bg-muted/20">
                  <div className="flex items-center gap-2">
                    {statusIcon(toolResult.status)}
                    <span>via tool <span className="font-mono">{toolResult.tool}</span></span>
                    <span className="text-muted-foreground">{toolResult.status}</span>
                  </div>
                  {toolResult.preview && (
                    <div className="mt-1 text-muted-foreground">{toolResult.preview}</div>
                  )}
                </div>
              )}

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="text-[11px] font-semibold text-muted-foreground uppercase">Request payload</div>
                  <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={usePresetPayload}>
                    <RefreshCw className="h-3 w-3 mr-1" /> Reset to canary
                  </Button>
                </div>
                <textarea
                  value={payloadJson}
                  onChange={(e) => setPayloadJson(e.target.value)}
                  spellCheck={false}
                  className="w-full h-40 text-[11px] font-mono bg-background/50 border rounded p-2"
                />
                <div className="text-[10px] text-muted-foreground mt-1">
                  Path placeholders ({'{...}'}) are filled from this body before dispatch. The <span className="font-mono">actor</span> defaults to <span className="font-mono">diagnostic-runner</span>.
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button onClick={handleRun} disabled={running || !!toolRunning}>
                  {running ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-1" />}
                  Run REST endpoint
                </Button>
                {result && (
                  <span className="flex items-center gap-2 text-xs">
                    {verdictBadge(result.verdict)}
                    <span className="text-muted-foreground">HTTP {result.http_status}</span>
                    <span className="text-muted-foreground">{formatLatency(result.duration_ms)}</span>
                  </span>
                )}
              </div>

              {result && (
                <div className="border rounded">
                  <div className="flex border-b bg-muted/30">
                    {(['response','verification','audit','curl'] as ResultTab[]).map(tab => (
                      <button
                        key={tab}
                        onClick={() => setResultTab(tab)}
                        className={`px-3 py-1.5 text-[11px] capitalize ${resultTab === tab ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground'}`}
                      >
                        {tab}
                      </button>
                    ))}
                  </div>
                  <div className="p-3 text-[11px]">
                    {resultTab === 'response' && (
                      <pre className="font-mono whitespace-pre-wrap break-all max-h-72 overflow-auto">
                        {JSON.stringify({
                          method: result.request.method,
                          path: result.request.path,
                          body: result.request.body,
                          http_status: result.http_status,
                          response: result.response,
                          http_error: result.http_error,
                        }, null, 2)}
                      </pre>
                    )}
                    {resultTab === 'verification' && <VerificationView result={result} />}
                    {resultTab === 'audit' && <AuditView event={result.verification.audit_event} />}
                    {resultTab === 'curl' && (
                      <pre className="font-mono whitespace-pre-wrap break-all">{curlText}</pre>
                    )}
                  </div>
                </div>
              )}

              <RecentEvents events={detail.recent_events} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function VerificationView({ result }: { result: InvokeResponse }) {
  const v = result.verification;
  if (!v.mode) {
    return (
      <div className="text-muted-foreground italic">
        No verification hint registered for this api_id. The endpoint dispatched
        successfully, but row-level diff is unavailable.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-[10px] uppercase text-muted-foreground">Schema / Table</div>
          <div className="font-mono">{v.schema}.{v.table}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase text-muted-foreground">Mode / Row count</div>
          <div className="font-mono">
            {v.mode} | {v.row_count_before} <ChevronRight className="inline h-3 w-3" /> {v.row_count_after}
          </div>
        </div>
      </div>
      {v.mode === 'patch' && (
        <div>
          <div className="text-[10px] uppercase text-muted-foreground mb-1">
            Diff ({v.row_diff.length} field{v.row_diff.length === 1 ? '' : 's'})
          </div>
          {v.row_diff.length === 0 ? (
            <div className="text-amber-300">No fields changed (idempotent or value identical).</div>
          ) : (
            <div className="border rounded">
              <table className="w-full text-[11px]">
                <thead className="bg-muted/30">
                  <tr>
                    <th className="px-2 py-1 text-left">Field</th>
                    <th className="px-2 py-1 text-left">Before</th>
                    <th className="px-2 py-1 text-left">After</th>
                  </tr>
                </thead>
                <tbody>
                  {v.row_diff.map(k => (
                    <tr key={k} className="border-t border-border/40">
                      <td className="px-2 py-1 font-mono">{k}</td>
                      <td className="px-2 py-1 font-mono text-muted-foreground">{JSON.stringify(v.before?.[k] ?? null)}</td>
                      <td className="px-2 py-1 font-mono">{JSON.stringify(v.after?.[k] ?? null)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      {(v.mode === 'post' || v.mode === 'post_prefix') && (
        <div>
          <div className="text-[10px] uppercase text-muted-foreground mb-1">Last appended row</div>
          <pre className="font-mono whitespace-pre-wrap break-all max-h-48 overflow-auto bg-muted/20 p-2 rounded">
            {JSON.stringify(v.after, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function AuditView({ event }: { event: AuditEvent | null }) {
  if (!event) {
    return <div className="text-amber-300">No audit event found for this api_id after the call.</div>;
  }
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-[10px] uppercase text-muted-foreground">event_id</div>
          <div className="font-mono">{event.event_id}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase text-muted-foreground">event_ts</div>
          <div className="font-mono">{event.event_ts}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase text-muted-foreground">actor</div>
          <div className="font-mono">{event.actor}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase text-muted-foreground">verb</div>
          <div className="font-mono">{event.verb}</div>
        </div>
        <div className="col-span-2">
          <div className="text-[10px] uppercase text-muted-foreground">target</div>
          <div className="font-mono">{event.target}</div>
        </div>
      </div>
      {event.payload && (
        <div>
          <div className="text-[10px] uppercase text-muted-foreground mb-1">payload</div>
          <pre className="font-mono whitespace-pre-wrap break-all max-h-48 overflow-auto bg-muted/20 p-2 rounded">
            {JSON.stringify(event.payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function RecentEvents({ events }: { events: AuditEvent[] }) {
  if (!events || events.length === 0) {
    return (
      <div>
        <div className="text-[11px] font-semibold text-muted-foreground uppercase mb-1.5">Recent activity</div>
        <div className="text-xs text-muted-foreground italic">No prior invocations recorded.</div>
      </div>
    );
  }
  return (
    <div>
      <div className="text-[11px] font-semibold text-muted-foreground uppercase mb-1.5">
        Recent activity ({events.length})
      </div>
      <div className="border rounded max-h-48 overflow-auto">
        <table className="w-full text-[10px]">
          <thead className="bg-muted/30 sticky top-0">
            <tr>
              <th className="px-2 py-1 text-left">ts</th>
              <th className="px-2 py-1 text-left">actor</th>
              <th className="px-2 py-1 text-left">verb</th>
              <th className="px-2 py-1 text-left">target</th>
            </tr>
          </thead>
          <tbody>
            {events.map(e => (
              <tr key={e.event_id} className="border-t border-border/40">
                <td className="px-2 py-1 font-mono">{e.event_ts}</td>
                <td className="px-2 py-1">{e.actor}</td>
                <td className="px-2 py-1 font-mono">{e.verb}</td>
                <td className="px-2 py-1 font-mono">{e.target}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export { ConnectorApiTestDrawer };
