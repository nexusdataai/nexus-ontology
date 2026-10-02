import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Loader2, Play, Database,
  ChevronDown, ChevronRight, RefreshCw, Activity,
} from 'lucide-react';
import { Section, StatusBadge, formatLatency } from './_shared';
import {
  virtualDataDiagnosticsService,
  VirtualEntityDiagnostic,
  VirtualEntityIndexEntry,
  VirtualEntityCheck,
} from '@/services/virtualDataDiagnosticsService';

type Filter = 'all' | 'healthy' | 'degraded' | 'unhealthy' | 'unknown';

function CheckRow({ c }: { c: VirtualEntityCheck }) {
  return (
    <div className="border-l-2 border-border/60 pl-3 py-2 text-xs space-y-1">
      <div className="flex items-center gap-2 flex-wrap">
        <StatusBadge status={c.status} />
        <span className="font-mono text-[10px]">{c.code}</span>
        <span className="text-muted-foreground">{c.message}</span>
      </div>
      {c.suggestion && (
        <div className="text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-1">
          {c.suggestion}
        </div>
      )}
    </div>
  );
}

function EntityRow({
  entry,
  result,
  running,
  onRun,
}: {
  entry: VirtualEntityIndexEntry;
  result?: VirtualEntityDiagnostic;
  running: boolean;
  onRun: () => void;
}) {
  const [open, setOpen] = useState(false);
  const status = result?.overall ?? 'unknown';
  const expandable = !!result;

  return (
    <div className="border-b border-border/40 last:border-b-0">
      <div
        className={`flex items-center gap-3 px-3 py-2 text-xs ${expandable ? 'cursor-pointer hover:bg-muted/30' : ''}`}
        onClick={() => expandable && setOpen(!open)}
      >
        <div className="w-4 flex-shrink-0">
          {expandable ? (open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />) : null}
        </div>
        <div className="w-24 flex-shrink-0">
          {result ? (
            <StatusBadge status={status} />
          ) : (
            <Badge variant="outline" className="text-[10px] text-muted-foreground">unrun</Badge>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium truncate">{entry.virtualEntity}</div>
          <div className="text-[10px] text-muted-foreground truncate">
            {entry.sourceSchemas.join(', ') || '-'}
          </div>
        </div>
        <div className="w-20 flex-shrink-0 text-right">
          <span className="font-mono">
            {entry.activeRuleCount}/{entry.totalRuleCount}
          </span>
          <span className="block text-[9px] text-muted-foreground">active/total</span>
        </div>
        <div className="w-32 flex-shrink-0 flex flex-wrap gap-1">
          {entry.sourceSystems.slice(0, 3).map(s => (
            <Badge key={s} variant="outline" className="text-[9px]">{s}</Badge>
          ))}
        </div>
        <div className="w-16 flex-shrink-0 text-right text-muted-foreground">
          {result?.rowCount != null ? `${result.rowCount}` : '-'}
        </div>
        <div className="w-20 flex-shrink-0 text-right text-muted-foreground">
          {result ? formatLatency(result.latencyMs) : '-'}
        </div>
        <div className="w-24 flex-shrink-0 text-right">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-[10px]"
            disabled={running}
            onClick={(e) => { e.stopPropagation(); onRun(); }}
          >
            {running ? <Loader2 className="h-3 w-3 animate-spin" /> : <><Play className="h-3 w-3 mr-1" /> Run</>}
          </Button>
        </div>
      </div>
      {open && result && (
        <div className="px-6 pb-3 pt-1 space-y-2 bg-muted/10">
          <div className="text-[11px] text-muted-foreground flex items-center gap-3 flex-wrap">
            {result.sourceType && <span>type: <span className="font-mono">{result.sourceType}</span></span>}
            {result.sourceSystem && <span>system: <span className="font-mono">{result.sourceSystem}</span></span>}
            {result.sourceTable && <span>table: <span className="font-mono">{result.sourceSchema}.{result.sourceTable}</span></span>}
            {result.ruleId && <span>rule: <span className="font-mono">{result.ruleId.slice(0, 12)}</span></span>}
            <span className="ml-auto">scanned {new Date(result.scannedAt).toLocaleTimeString()}</span>
          </div>
          {result.checks.map((c, i) => (
            <CheckRow key={`${c.code}-${i}`} c={c} />
          ))}
          {result.sampleRow && (
            <div className="text-[11px] mt-2 border-t border-border/40 pt-2">
              <div className="text-muted-foreground mb-1">Sample row:</div>
              <pre className="bg-muted/40 rounded px-2 py-1 font-mono text-[10px] overflow-x-auto">
                {JSON.stringify(result.sampleRow, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function VirtualDataDiagnosticsPanel() {
  const [index, setIndex] = useState<VirtualEntityIndexEntry[]>([]);
  const [results, setResults] = useState<Record<string, VirtualEntityDiagnostic>>({});
  const [running, setRunning] = useState<Record<string, boolean>>({});
  const [runAllRunning, setRunAllRunning] = useState(false);
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);

  const refreshIndex = useCallback(async () => {
    try {
      const data = await virtualDataDiagnosticsService.listIndex();
      setIndex(data);
    } catch (e: any) {
      setError(e?.message || 'Failed to load virtual entity index');
    }
  }, []);

  useEffect(() => {
    refreshIndex();
  }, [refreshIndex]);

  const runOne = useCallback(async (entity: string) => {
    setRunning(prev => ({ ...prev, [entity]: true }));
    setError(null);
    try {
      const result = await virtualDataDiagnosticsService.runOne(entity);
      setResults(prev => ({ ...prev, [entity]: result }));
    } catch (e: any) {
      setError(e?.message || `Failed to diagnose ${entity}`);
    } finally {
      setRunning(prev => ({ ...prev, [entity]: false }));
    }
  }, []);

  const runAll = useCallback(async () => {
    setRunAllRunning(true);
    setError(null);
    setResults({});
    try {
      await virtualDataDiagnosticsService.streamRunAll({}, (evt) => {
        if (evt.type === 'entity') {
          setResults(prev => ({ ...prev, [evt.data.virtualEntity]: evt.data }));
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
        const hay = [
          e.virtualEntity,
          e.sourceSystems.join(' '),
          e.sourceSchemas.join(' '),
        ].join(' ').toLowerCase();
        if (!hay.includes(q)) return false;
      }
      const r = results[e.virtualEntity];
      const status: Filter = r ? (r.overall as Filter) : 'unknown';
      if (filter !== 'all' && filter !== status) return false;
      return true;
    });
  }, [index, results, filter, search]);

  const counts = useMemo(() => {
    let healthy = 0, degraded = 0, unhealthy = 0, unrun = 0;
    for (const e of index) {
      const r = results[e.virtualEntity];
      if (!r) unrun++;
      else if (r.overall === 'healthy') healthy++;
      else if (r.overall === 'degraded') degraded++;
      else unhealthy++;
    }
    return { healthy, degraded, unhealthy, unrun };
  }, [index, results]);

  return (
    <div className="p-6 space-y-4 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold mb-1">Virtual Data Diagnostics</h2>
          <p className="text-sm text-muted-foreground">
            Live probe for every mapped virtual entity - mapping rule, source schema/table resolution, backend load state, field-map sanity, query execution, row count, and null-field audit
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={refreshIndex} disabled={runAllRunning}>
            <RefreshCw className="h-4 w-4 mr-2" /> Reload
          </Button>
          <Button onClick={runAll} disabled={runAllRunning || index.length === 0}>
            {runAllRunning ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Running...</> : <><Play className="h-4 w-4 mr-2" /> Run All</>}
          </Button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          {error}
        </div>
      )}

      <Section
        title={`Mapped Virtual Entities (${index.length})`}
        icon={Database}
        status={
          counts.unhealthy > 0 ? 'unhealthy'
          : counts.degraded > 0 ? 'degraded'
          : counts.healthy > 0 ? 'healthy'
          : 'unknown'
        }
        defaultOpen={true}
        rightSlot={
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
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
              className="h-7 text-[10px] capitalize"
              onClick={() => setFilter(f)}
            >
              {f}
            </Button>
          ))}
          <Input
            placeholder="Search by entity, system, schema..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-7 text-[10px] flex-1 min-w-[200px]"
          />
        </div>

        <div className="rounded border border-border/60 bg-muted/5">
          <div className="flex items-center gap-3 px-3 py-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground border-b border-border/40">
            <div className="w-4 flex-shrink-0" />
            <div className="w-24 flex-shrink-0">Status</div>
            <div className="flex-1 min-w-0">Virtual Entity</div>
            <div className="w-20 flex-shrink-0 text-right">Rules</div>
            <div className="w-32 flex-shrink-0">Systems</div>
            <div className="w-16 flex-shrink-0 text-right">Rows</div>
            <div className="w-20 flex-shrink-0 text-right">Latency</div>
            <div className="w-24 flex-shrink-0 text-right">Action</div>
          </div>
          {filtered.length === 0 ? (
            <div className="px-3 py-6 text-xs text-center text-muted-foreground">
              No virtual entities match the current filter.
            </div>
          ) : (
            filtered.map(e => (
              <EntityRow
                key={e.virtualEntity}
                entry={e}
                result={results[e.virtualEntity]}
                running={!!running[e.virtualEntity] || runAllRunning}
                onRun={() => runOne(e.virtualEntity)}
              />
            ))
          )}
        </div>
      </Section>
    </div>
  );
}
