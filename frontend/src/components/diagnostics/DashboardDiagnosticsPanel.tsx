import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Loader2, Play, Database, Server, ChevronDown, ChevronRight, RefreshCw, Activity } from 'lucide-react';
import { Section, StatusBadge, formatLatency } from './_shared';
import {
  dashboardDiagnosticsService,
  DashboardDiagnostic,
  DashboardIndexEntry,
  BackendsDiagnostic,
  PanelDiagnostic,
} from '@/services/dashboardDiagnosticsService';

type Filter = 'all' | 'healthy' | 'degraded' | 'unhealthy' | 'unknown';

function PanelRow({ p }: { p: PanelDiagnostic }) {
  return (
    <div className="border-l-2 border-border/60 pl-3 py-2 text-xs space-y-1">
      <div className="flex items-center gap-2 flex-wrap">
        <StatusBadge status={p.status} />
        <span className="font-medium">{p.panelTitle || `Panel ${p.panelId}`}</span>
        <span className="text-muted-foreground">[{p.panelType}]</span>
        <span className="text-muted-foreground">{p.entity}</span>
        {p.sourceType && (
          <Badge variant="outline" className="text-xs">{p.sourceType}</Badge>
        )}
      </div>
      <div className="text-muted-foreground flex items-center gap-3 flex-wrap">
        <span>code: <span className="font-mono">{p.code}</span></span>
        {p.rowCount != null && <span>rows: {p.rowCount}</span>}
        <span>latency: {formatLatency(p.latencyMs)}</span>
      </div>
      {p.suggestion && (
        <div className="text-warning bg-warning/10 border border-warning/20 rounded px-2 py-1">
          {p.suggestion}
        </div>
      )}
      {p.errorMessage && (
        <div className="text-destructive bg-destructive/10 border border-destructive/20 rounded px-2 py-1 font-mono break-all">
          {p.errorMessage}
        </div>
      )}
      {p.missingFields.length > 0 && (
        <div className="text-muted-foreground">
          missing columns: <span className="font-mono">{p.missingFields.join(', ')}</span>
        </div>
      )}
      {p.nullGroupColumns.length > 0 && (
        <div className="text-muted-foreground">
          null group keys: <span className="font-mono">{p.nullGroupColumns.join(', ')}</span>
        </div>
      )}
    </div>
  );
}

function DashboardRow({
  entry,
  result,
  running,
  onRun,
}: {
  entry: DashboardIndexEntry;
  result?: DashboardDiagnostic;
  running: boolean;
  onRun: () => void;
}) {
  const [open, setOpen] = useState(false);
  const status = result?.status ?? 'unknown';
  const expandable = !!result;
  return (
    <div className="border-b border-border/40 last:border-b-0">
      <div
        className={`flex items-center gap-3 px-3 py-2 text-xs ${expandable ? 'cursor-pointer hover:bg-surface-2/60' : ''}`}
        onClick={() => expandable && setOpen(!open)}
      >
        <div className="w-4 flex-shrink-0">
          {expandable ? (open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />) : null}
        </div>
        <div className="w-24 flex-shrink-0">
          {result ? <StatusBadge status={status} /> : <Badge variant="outline" className="text-xs text-muted-foreground">unrun</Badge>}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium truncate">{entry.title}</div>
          <div className="text-xs text-muted-foreground truncate">{entry.uid}</div>
        </div>
        <div className="w-16 flex-shrink-0 text-right">
          <span className="font-mono">{entry.panelCount}p</span>
        </div>
        <div className="w-44 flex-shrink-0 flex flex-wrap gap-1">
          {entry.tags.slice(0, 3).map(t => (
            <Badge key={t} variant="outline" className="text-xs">{t}</Badge>
          ))}
        </div>
        <div className="w-20 flex-shrink-0 text-right text-muted-foreground">
          {result ? formatLatency(result.durationMs) : '-'}
        </div>
        <div className="w-24 flex-shrink-0 text-right">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            disabled={running}
            onClick={(e) => { e.stopPropagation(); onRun(); }}
          >
            {running ? <Loader2 className="h-3 w-3 animate-spin" /> : <><Play className="h-3 w-3 mr-1" /> Run</>}
          </Button>
        </div>
      </div>
      {open && result && (
        <div className="px-6 pb-3 pt-1 space-y-2 bg-muted/10">
          <div className="text-xs text-muted-foreground">
            {result.healthyCount} pass | {result.degradedCount} warn | {result.unhealthyCount} fail
            <span className="ml-2">scanned {new Date(result.scannedAt).toLocaleTimeString()}</span>
          </div>
          {result.panels.map(p => (
            <PanelRow key={`${p.panelId}-${p.targetRefId}`} p={p} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DashboardDiagnosticsPanel() {
  const [index, setIndex] = useState<DashboardIndexEntry[]>([]);
  const [results, setResults] = useState<Record<string, DashboardDiagnostic>>({});
  const [running, setRunning] = useState<Record<string, boolean>>({});
  const [runAllRunning, setRunAllRunning] = useState(false);
  const [backends, setBackends] = useState<BackendsDiagnostic | null>(null);
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);

  const refreshIndex = useCallback(async () => {
    try {
      const data = await dashboardDiagnosticsService.listIndex();
      setIndex(data);
    } catch (e: any) {
      setError(e?.message || 'Failed to load dashboard list');
    }
  }, []);

  const refreshBackends = useCallback(async () => {
    try {
      const data = await dashboardDiagnosticsService.backendsCheck();
      setBackends(data);
    } catch {
      setBackends(null);
    }
  }, []);

  useEffect(() => {
    refreshIndex();
    refreshBackends();
  }, [refreshIndex, refreshBackends]);

  const runOne = useCallback(async (uid: string) => {
    setRunning(prev => ({ ...prev, [uid]: true }));
    setError(null);
    try {
      const result = await dashboardDiagnosticsService.runOne(uid);
      setResults(prev => ({ ...prev, [uid]: result }));
    } catch (e: any) {
      setError(e?.message || `Failed to diagnose ${uid}`);
    } finally {
      setRunning(prev => ({ ...prev, [uid]: false }));
    }
  }, []);

  const runAll = useCallback(async () => {
    setRunAllRunning(true);
    setError(null);
    setResults({});
    try {
      await dashboardDiagnosticsService.streamRunAll({}, (evt) => {
        if (evt.type === 'dashboard') {
          setResults(prev => ({ ...prev, [evt.data.uid]: evt.data }));
        } else if (evt.type === 'error') {
          setError(evt.data.message);
        }
      });
    } catch (e: any) {
      setError(e?.message || 'Run-all failed');
    } finally {
      setRunAllRunning(false);
    }
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return index.filter(e => {
      if (q) {
        const hay = `${e.title} ${e.uid} ${(e.tags || []).join(' ')}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      const r = results[e.uid];
      const status: Filter = r ? r.status as Filter : 'unknown';
      if (filter !== 'all' && filter !== status) return false;
      return true;
    });
  }, [index, results, filter, search]);

  const counts = useMemo(() => {
    let healthy = 0, degraded = 0, unhealthy = 0, unrun = 0;
    for (const e of index) {
      const r = results[e.uid];
      if (!r) unrun++;
      else if (r.status === 'healthy') healthy++;
      else if (r.status === 'degraded') degraded++;
      else unhealthy++;
    }
    return { healthy, degraded, unhealthy, unrun };
  }, [index, results]);

  const overall = backends?.overall ?? 'healthy';

  return (
    <div className="page space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-medium tracking-tight text-foreground">Dashboard Diagnostics</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Live checks for every saved dashboard - mapping rules, backend reachability, query execution, schema, and latency
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => { refreshIndex(); refreshBackends(); }} disabled={runAllRunning}>
            <RefreshCw className="h-4 w-4 mr-2" /> Reload
          </Button>
          <Button onClick={runAll} disabled={runAllRunning || index.length === 0}>
            {runAllRunning ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Running checks</> : <><Play className="h-4 w-4 mr-2" /> Run All</>}
          </Button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded px-3 py-2">
          {error}
        </div>
      )}

      <Section
        title="Backend status"
        icon={Server}
        status={overall}
        defaultOpen={true}
        rightSlot={
          <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={(e) => { e.stopPropagation(); refreshBackends(); }}>
            <RefreshCw className="h-3 w-3 mr-1" /> Recheck
          </Button>
        }
      >
        {!backends ? (
          <div className="text-xs text-muted-foreground">Loading backend status...</div>
        ) : (
          <div className="space-y-2">
            {backends.backends.map(b => (
              <div key={b.name} className="flex items-center gap-3 text-xs">
                <StatusBadge status={b.status} />
                <span className="font-medium w-40">{b.name}</span>
                <span className="text-muted-foreground w-20">{b.kind}</span>
                <span className="text-muted-foreground flex-1 truncate">{b.detail}</span>
                <span className="text-muted-foreground">{formatLatency(b.latencyMs)}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section
        title={`Dashboards (${index.length})`}
        icon={Database}
        status={
          counts.unhealthy > 0 ? 'unhealthy'
          : counts.degraded > 0 ? 'degraded'
          : counts.healthy > 0 ? 'healthy'
          : 'unknown'
        }
        defaultOpen={true}
        rightSlot={
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span><Activity className="h-3 w-3 inline" /> {counts.healthy} pass | {counts.degraded} warn | {counts.unhealthy} fail | {counts.unrun} unrun</span>
          </div>
        }
      >
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          {(['all', 'healthy', 'degraded', 'unhealthy', 'unknown'] as Filter[]).map(f => (
            <Button
              key={f}
              size="sm"
              variant={filter === f ? 'default' : 'outline'}
              className="h-7 text-xs capitalize"
              onClick={() => setFilter(f)}
            >
              {f}
            </Button>
          ))}
          <Input
            placeholder="Search by title, uid, tag..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-7 text-xs flex-1 min-w-[200px]"
          />
        </div>

        <div className="rounded border border-border/60 bg-muted/5">
          <div className="flex items-center gap-3 px-3 py-2 text-xs font-medium text-muted-foreground border-b border-border/40">
            <div className="w-4 flex-shrink-0" />
            <div className="w-24 flex-shrink-0">Status</div>
            <div className="flex-1 min-w-0">Dashboard</div>
            <div className="w-16 flex-shrink-0 text-right">Panels</div>
            <div className="w-44 flex-shrink-0">Tags</div>
            <div className="w-20 flex-shrink-0 text-right">Duration</div>
            <div className="w-24 flex-shrink-0 text-right">Action</div>
          </div>
          {filtered.length === 0 ? (
            <div className="px-3 py-6 text-xs text-center text-muted-foreground">
              No dashboards match the current filter.
            </div>
          ) : (
            filtered.map(e => (
              <DashboardRow
                key={e.uid}
                entry={e}
                result={results[e.uid]}
                running={!!running[e.uid] || runAllRunning}
                onRun={() => runOne(e.uid)}
              />
            ))
          )}
        </div>
      </Section>
    </div>
  );
}
