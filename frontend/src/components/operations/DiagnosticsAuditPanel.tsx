/**
 * Diagnostics audit panel (AI-OPs plane, Phase 1).
 *
 * Lists persisted diagnostic runs from `/api/v1/diagnostics/history`. Scope
 * selector limits to a single family (e.g. "o2c", "react-tools"); clicking
 * a row opens a drawer with the recorded JSON payload.
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { RefreshCw, Loader2, ChevronRight, X } from 'lucide-react';
import {
  diagnosticsHistoryService,
  DiagnosticRun,
} from '@/services/diagnosticsHistoryService';

const KNOWN_SCOPES = [
  'o2c',
  'df',
  'io',
  'pa',
  'pq',
  'scr',
  'c360',
  'esg',
  'cpq',
  'simulators',
  'react-tools',
  'automation',
  'virtual-data',
  'dashboard',
  'connector-apis',
  'connector-apis-smoke',
];

export function DiagnosticsAuditPanel() {
  const [scopes, setScopes] = useState<string[]>(KNOWN_SCOPES);
  const [scope, setScope] = useState<string>('o2c');
  const [runs, setRuns] = useState<DiagnosticRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<DiagnosticRun | null>(null);

  const loadScopes = async () => {
    try {
      const r = await diagnosticsHistoryService.listScopes();
      const merged = Array.from(new Set([...(r.scopes || []), ...KNOWN_SCOPES])).sort();
      setScopes(merged);
    } catch {
      // fall back to KNOWN_SCOPES
    }
  };

  const load = async (target: string) => {
    setLoading(true);
    setError(null);
    try {
      const r = await diagnosticsHistoryService.list(target, 50);
      setRuns(r.items || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to load history');
      setRuns([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScopes();
    load(scope);
  }, []);

  useEffect(() => {
    load(scope);
  }, [scope]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Diagnostics Audit</h2>
          <p className="text-xs text-muted-foreground">
            Every diagnostic route call is captured. Pick a scope to browse recent runs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            className="text-xs px-2 py-1 rounded-md border bg-background"
          >
            {scopes.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <Button size="sm" variant="outline" onClick={() => load(scope)} disabled={loading}>
            {loading ? (
              <Loader2 className="h-3 w-3 animate-spin mr-1" />
            ) : (
              <RefreshCw className="h-3 w-3 mr-1" />
            )}
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded p-2">
          {error}
        </div>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            Runs for <span className="font-mono">{scope}</span>{' '}
            <Badge variant="outline" className="ml-2 text-[10px]">{runs.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-6 justify-center">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading...
            </div>
          ) : runs.length === 0 ? (
            <div className="text-sm text-muted-foreground italic py-6 text-center">
              No runs recorded for scope <span className="font-mono">{scope}</span> yet.
            </div>
          ) : (
            <div className="divide-y">
              {runs.map((r) => (
                <button
                  key={r.run_id}
                  onClick={() => setSelected(r)}
                  className="w-full flex items-center justify-between py-2 px-1 text-left hover:bg-muted/40 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Badge variant="outline" className="text-[10px]">
                      {new Date(r.recordedAt).toLocaleString()}
                    </Badge>
                    <span className="font-mono text-[10px] text-muted-foreground truncate">
                      {r.run_id}
                    </span>
                    {r.summary && Object.keys(r.summary).length > 0 && (
                      <span className="text-[10px] text-muted-foreground">
                        {Object.entries(r.summary)
                          .slice(0, 2)
                          .map(([k, v]) => `${k}=${String(v)}`)
                          .join(' · ')}
                      </span>
                    )}
                  </div>
                  <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {selected && (
        <div
          className="fixed inset-0 z-40 bg-black/50 flex items-center justify-center p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="bg-card border rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <div>
                <h3 className="text-sm font-semibold">
                  {selected.scope} · {new Date(selected.recordedAt).toLocaleString()}
                </h3>
                <p className="text-[10px] text-muted-foreground font-mono">{selected.run_id}</p>
              </div>
              <Button size="sm" variant="ghost" onClick={() => setSelected(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 min-h-0 overflow-auto p-4">
              <pre className="text-[11px] font-mono whitespace-pre-wrap break-words bg-muted/40 rounded p-3">
                {JSON.stringify(selected.result ?? selected, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
