/**
 * Diagnostics audit panel (AI-OPs plane, Phase 1).
 *
 * Lists persisted diagnostic runs from `/api/v1/diagnostics/history`. Scope
 * selector limits to a single family (e.g. "o2c", "react-tools"); clicking
 * a row opens a drawer with the recorded JSON payload.
 */

import { useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Icon } from '@/components/ds/Icon';
import { CodeBlock, DetailSheet, InlineError, KeyValues, StatusPill, SubHeading } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { cn } from '@/lib/utils';
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

const SCOPE_LABEL: Record<string, string> = {
  o2c: 'Order-to-Cash', df: 'Demand forecasting', io: 'Inventory', pa: 'Procurement', pq: 'Production', scr: 'Supply chain risk',
  c360: 'Customer 360', esg: 'ESG', cpq: 'Trade CPQ', simulators: 'Simulators', 'react-tools': 'Agent tools', automation: 'Automation',
  'virtual-data': 'Virtual data', dashboard: 'Dashboards', 'connector-apis': 'Connector APIs', 'connector-apis-smoke': 'Connector API tests',
};
const scopeLabel = (s: string) => SCOPE_LABEL[s] || s.replace(/[-_]/g, ' ').replace(/^\w/, c => c.toUpperCase());
const when = (iso: string) => { const d = new Date(iso); return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }); };
const pretty = (k: string) => k.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
const STATUS_KEYS = ['overall_status', 'overall', 'status', 'verdict'];

function runStatus(r: DiagnosticRun): string | null {
  const s = (r.summary || {}) as Record<string, unknown>;
  for (const k of STATUS_KEYS) if (typeof s[k] === 'string') return s[k] as string;
  const res = (r.result || {}) as Record<string, unknown>;
  for (const k of STATUS_KEYS) if (typeof res[k] === 'string') return res[k] as string;
  return null;
}

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

  const facts = (r: DiagnosticRun) => Object.entries(r.summary || {}).filter(([k, v]) => !STATUS_KEYS.includes(k) && v !== null && typeof v !== 'object');

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-xl font-medium tracking-tight text-foreground">Audit log</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Every diagnostics run is recorded with its full result. Choose an area to see its recent runs.</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={scope} onValueChange={setScope}>
            <SelectTrigger className="h-9 w-[220px]" aria-label="Area"><SelectValue /></SelectTrigger>
            <SelectContent className="max-h-80">
              {scopes.map((s) => <SelectItem key={s} value={s}>{scopeLabel(s)}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={() => load(scope)} disabled={loading}>
            <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
          </Button>
        </div>
      </header>

      {error && <InlineError onRetry={() => load(scope)}>{error}</InlineError>}

      {loading && runs.length === 0 ? (
        <div className="space-y-px overflow-hidden rounded-xl border border-border" aria-busy="true">
          {[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-14 w-full rounded-none" />)}
        </div>
      ) : runs.length === 0 && !error ? (
        <EmptyState icon="history" title={`No runs recorded for ${scopeLabel(scope)}`} description="Run its diagnostics and the result will be kept here." />
      ) : runs.length > 0 ? (
        <>
          <p className="text-sm text-muted-foreground"><span className="num font-medium text-foreground">{runs.length}</span> most recent runs for {scopeLabel(scope)}</p>
          <ul className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
            {runs.map((r, i) => {
              const status = runStatus(r);
              return (
                <li key={r.run_id} className="rise border-b border-border last:border-b-0" style={{ ['--i' as any]: Math.min(i, 12) }}>
                  <button
                    type="button"
                    onClick={() => setSelected(r)}
                    className="group flex w-full items-center gap-4 px-5 py-3 text-left transition-colors hover:bg-surface-2/70 focus-visible:bg-surface-2 focus-visible:outline-none"
                  >
                    <span className="w-44 shrink-0 text-sm text-foreground">{when(r.recordedAt)}</span>
                    <span className="w-28 shrink-0">{status ? <StatusPill status={status} /> : <span className="text-xs text-muted-foreground">Recorded</span>}</span>
                    <span className="hidden min-w-0 flex-1 truncate text-sm text-muted-foreground md:block">
                      {facts(r).slice(0, 3).map(([k, v]) => `${pretty(k)} ${String(v)}`).join(' · ')}
                    </span>
                    <span className="ml-auto hidden max-w-[180px] truncate font-mono text-xs text-subtle-foreground lg:block">{r.run_id}</span>
                    <Icon name="chevron-right" className="h-3.5 w-3.5 shrink-0 text-subtle-foreground transition-transform group-hover:translate-x-0.5" />
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      ) : null}

      <DetailSheet
        open={!!selected}
        onOpenChange={(o) => { if (!o) setSelected(null); }}
        title={selected ? `${scopeLabel(selected.scope)} run` : ''}
        description={selected ? when(selected.recordedAt) : undefined}
        meta={selected && runStatus(selected) ? <StatusPill status={runStatus(selected)!} variant="soft" /> : undefined}
        wide
      >
        {selected && (
          <div className="space-y-6">
            <KeyValues items={[{ label: 'Run ID', value: selected.run_id, mono: true }, ...facts(selected).map(([k, v]) => ({ label: pretty(k), value: String(v) }))]} />
            <div>
              <SubHeading>Full recorded result</SubHeading>
              <CodeBlock maxHeight={520}>{JSON.stringify(selected.result ?? selected, null, 2)}</CodeBlock>
            </div>
          </div>
        )}
      </DetailSheet>
    </div>
  );
}
