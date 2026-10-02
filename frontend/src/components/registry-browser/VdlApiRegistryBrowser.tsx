/**
 * Virtual Data API Registry browser (Data Plane, Phase 2).
 *
 * Renders `/api/v1/vdl-apis` as a searchable table. Each row's detail
 * drawer surfaces the impl chain: verb, virtual entity, and the list of
 * Connector APIs it dispatches to (deep-linked into the Connector
 * Registry).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Loader2,
  RefreshCw,
  Search,
  Zap,
  Database,
  ChevronRight,
  X,
  Play,
  ShieldCheck,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { vdlApiService, VdlApiSpec, InvokeResult } from '@/services/vdlApiService';

const VERB_TINT: Record<string, string> = {
  read: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  write: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  upsert: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  delete: 'bg-red-500/15 text-red-300 border-red-500/30',
  aggregate: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
};

const RISK_TINT: Record<string, string> = {
  read_only: 'bg-green-500/15 text-green-300',
  low_risk_write: 'bg-amber-500/15 text-amber-300',
  high_risk_write: 'bg-red-500/15 text-red-300',
};

function matches(spec: VdlApiSpec, q: string): boolean {
  if (!q) return true;
  const n = q.toLowerCase();
  return (
    spec.api_id.toLowerCase().includes(n)
    || (spec.description || '').toLowerCase().includes(n)
    || (spec.virtual_entity || '').toLowerCase().includes(n)
    || (spec.verb || '').toLowerCase().includes(n)
    || (spec.tags || []).some((t) => t.toLowerCase().includes(n))
    || (spec.impl || []).some((b) => b.connector_api_id.toLowerCase().includes(n))
  );
}

export default function VdlApiRegistryBrowser() {
  const [rows, setRows] = useState<VdlApiSpec[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<VdlApiSpec | null>(null);
  const [invoking, setInvoking] = useState(false);
  const [invokeResult, setInvokeResult] = useState<InvokeResult | null>(null);
  const [invokeArgs, setInvokeArgs] = useState('{\n  \n}');
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await vdlApiService.list();
      setRows(r.items || []);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // ?focus=<api_id> deep link
  useEffect(() => {
    const focus = searchParams.get('focus');
    if (!focus || rows.length === 0) return;
    const match = rows.find((r) => r.api_id === focus);
    if (match) setSelected(match);
  }, [rows, searchParams]);

  const filtered = useMemo(() => rows.filter((r) => matches(r, search)), [rows, search]);

  const closeDrawer = () => {
    setSelected(null);
    setInvokeResult(null);
    setInvokeArgs('{\n  \n}');
    if (searchParams.get('focus')) {
      const next = new URLSearchParams(searchParams);
      next.delete('focus');
      setSearchParams(next, { replace: true });
    }
  };

  const runInvoke = async () => {
    if (!selected) return;
    setInvoking(true);
    setInvokeResult(null);
    try {
      let args: Record<string, unknown> = {};
      try {
        args = JSON.parse(invokeArgs);
      } catch {
        args = {};
      }
      const r = await vdlApiService.invoke(selected.api_id, args);
      setInvokeResult(r);
    } catch (e: any) {
      setInvokeResult({
        api_id: selected.api_id,
        ok: false,
        plan: { api_id: selected.api_id, verb: selected.verb, virtual_entity: selected.virtual_entity, steps: [] },
        step_results: [],
        duration_ms: 0,
        error: e?.message || String(e),
      });
    } finally {
      setInvoking(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Zap className="h-5 w-5" /> Virtual Data API Registry
            <Badge variant="outline" className="text-[10px] ml-2">
              {rows.length} registered
            </Badge>
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            VDL APIs act on virtual entities and dispatch to one or more Connector API implementations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
            <Input
              className="pl-7 h-8 w-64 text-xs"
              placeholder="Search api_id, entity, tags..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button size="sm" variant="outline" onClick={load} disabled={loading}>
            {loading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <RefreshCw className="h-3 w-3 mr-1" />}
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded p-2">
          {error}
        </div>
      )}

      <div className="rounded border">
        <div className="grid grid-cols-12 gap-2 px-3 py-2 border-b bg-muted/30 text-[10px] uppercase tracking-wider text-muted-foreground">
          <div className="col-span-4">API</div>
          <div className="col-span-1">Verb</div>
          <div className="col-span-2">Virtual Entity</div>
          <div className="col-span-2">Risk</div>
          <div className="col-span-2">Impls</div>
          <div className="col-span-1 text-right">Details</div>
        </div>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading...
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-sm text-muted-foreground italic py-8 text-center">
            {rows.length === 0
              ? 'No VDL APIs registered yet.'
              : `No matches for "${search}".`}
          </div>
        ) : (
          <div className="divide-y">
            {filtered.map((r) => (
              <button
                key={r.api_id}
                onClick={() => setSelected(r)}
                className="w-full grid grid-cols-12 gap-2 px-3 py-2 items-center text-left hover:bg-muted/40 transition-colors"
              >
                <div className="col-span-4 min-w-0">
                  <div className="font-mono text-xs truncate">{r.api_id}</div>
                  <div className="text-[10px] text-muted-foreground truncate">{r.description}</div>
                </div>
                <div className="col-span-1">
                  <Badge variant="outline" className={`text-[10px] ${VERB_TINT[r.verb] || ''}`}>
                    {r.verb}
                  </Badge>
                </div>
                <div className="col-span-2 text-xs font-medium truncate">{r.virtual_entity}</div>
                <div className="col-span-2">
                  <Badge variant="outline" className={`text-[10px] ${RISK_TINT[r.risk_level] || ''}`}>
                    {r.risk_level.replace(/_/g, ' ')}
                  </Badge>
                </div>
                <div className="col-span-2 text-[10px] text-muted-foreground">
                  {r.direct_sql ? 'direct_sql' : ''}
                  {r.direct_sql && r.impl.length > 0 ? ' · ' : ''}
                  {r.impl.length > 0 ? `${r.impl.length} connector${r.impl.length === 1 ? '' : 's'}` : ''}
                  {!r.direct_sql && r.impl.length === 0 ? '—' : ''}
                </div>
                <div className="col-span-1 flex justify-end">
                  <ChevronRight className="h-3 w-3 text-muted-foreground" />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <div
          className="fixed inset-0 z-40 bg-black/60 flex items-center justify-center p-4"
          onClick={closeDrawer}
        >
          <div
            className="bg-card border rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <div className="min-w-0">
                <h3 className="text-sm font-mono font-semibold">{selected.api_id}</h3>
                <p className="text-xs text-muted-foreground truncate">{selected.description}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={`text-[10px] ${VERB_TINT[selected.verb] || ''}`}>
                  {selected.verb}
                </Badge>
                <Badge variant="outline" className={`text-[10px] ${RISK_TINT[selected.risk_level] || ''}`}>
                  <ShieldCheck className="h-2.5 w-2.5 mr-0.5" />
                  {selected.risk_level.replace(/_/g, ' ')}
                </Badge>
                <Button size="sm" variant="ghost" onClick={closeDrawer}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="flex-1 min-h-0 overflow-auto p-4 space-y-4">
              <section>
                <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                  Target virtual entity
                </h4>
                <div className="flex items-center gap-2">
                  <Database className="h-3 w-3 text-muted-foreground" />
                  <span className="font-mono text-xs">{selected.virtual_entity}</span>
                </div>
              </section>

              {selected.direct_sql && (
                <section>
                  <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                    Direct SQL read path
                  </h4>
                  <pre className="text-[11px] font-mono bg-muted/40 rounded p-2 overflow-auto">
                    {JSON.stringify(selected.direct_sql, null, 2)}
                  </pre>
                </section>
              )}

              {selected.impl.length > 0 && (
                <section>
                  <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                    Connector API implementations ({selected.impl.length})
                  </h4>
                  <div className="space-y-2">
                    {selected.impl.map((b, i) => (
                      <div key={i} className="rounded border p-2 bg-muted/20">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <button
                            className="font-mono text-xs text-blue-300 hover:underline text-left truncate"
                            onClick={() =>
                              navigate(
                                `/ai-stack/data-plane?tab=connector-registry&focus=${encodeURIComponent(b.connector_api_id)}`,
                              )
                            }
                          >
                            {b.connector_api_id}
                          </button>
                          <Badge variant="outline" className="text-[9px]">
                            step {i + 1}
                          </Badge>
                        </div>
                        {b.arg_mapping && Object.keys(b.arg_mapping).length > 0 && (
                          <div className="text-[10px] font-mono space-y-0.5 mt-1">
                            {Object.entries(b.arg_mapping).map(([k, v]) => (
                              <div key={k} className="flex justify-between gap-2">
                                <span className="text-muted-foreground">{k}</span>
                                <span className="truncate">{v}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {selected.tags.length > 0 && (
                <section>
                  <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Tags</h4>
                  <div className="flex flex-wrap gap-1">
                    {selected.tags.map((t) => (
                      <Badge key={t} variant="outline" className="text-[10px]">
                        {t}
                      </Badge>
                    ))}
                  </div>
                </section>
              )}

              <section>
                <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                  Invoke (test)
                </h4>
                <textarea
                  className="w-full text-[11px] font-mono bg-muted/40 rounded p-2 min-h-[80px]"
                  value={invokeArgs}
                  onChange={(e) => setInvokeArgs(e.target.value)}
                  placeholder='{"customer_id": "..."}'
                />
                <div className="flex justify-end mt-2">
                  <Button size="sm" onClick={runInvoke} disabled={invoking}>
                    {invoking ? (
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                    ) : (
                      <Play className="h-3 w-3 mr-1" />
                    )}
                    Invoke
                  </Button>
                </div>
                {invokeResult && (
                  <div className="mt-2 rounded border p-2 bg-muted/30">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${
                          invokeResult.ok
                            ? 'bg-green-500/15 text-green-300'
                            : 'bg-red-500/15 text-red-300'
                        }`}
                      >
                        {invokeResult.ok ? 'ok' : 'failed'}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground">
                        {invokeResult.duration_ms}ms
                      </span>
                    </div>
                    {invokeResult.error && (
                      <div className="text-[10px] text-red-300 mb-1">{invokeResult.error}</div>
                    )}
                    <pre className="text-[11px] font-mono max-h-40 overflow-auto whitespace-pre-wrap break-words">
                      {JSON.stringify(invokeResult, null, 2)}
                    </pre>
                  </div>
                )}
              </section>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
