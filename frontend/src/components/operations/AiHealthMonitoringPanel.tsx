/**
 * AI Health Central monitoring panel (AI-OPs plane, Phase 1).
 *
 * Reads plane-by-plane health snapshots from `/api/v1/ai-health/*` and
 * renders a per-plane card grid + a "Run now" button + a small sparkline
 * of recent snapshots.
 */

import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import {
  Activity,
  Database,
  Brain,
  Cpu,
  Layers,
  RefreshCw,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import {
  aiHealthService,
  HealthSnapshot,
  HealthVerdict,
  PlaneKey,
  PlaneSnapshot,
} from '@/services/aiHealthService';

const PLANE_META: { key: PlaneKey; label: string; icon: React.ReactNode }[] = [
  { key: 'ai_ops', label: 'AI-OPs', icon: <Activity className="h-4 w-4" /> },
  { key: 'data', label: 'Data Plane', icon: <Database className="h-4 w-4" /> },
  { key: 'control', label: 'Control Plane', icon: <Brain className="h-4 w-4" /> },
  { key: 'reasoning', label: 'Reasoning Plane', icon: <Cpu className="h-4 w-4" /> },
  { key: 'workspace', label: 'Workspace', icon: <Layers className="h-4 w-4" /> },
];

const verdictColor = (v: HealthVerdict) =>
  v === 'healthy'
    ? 'bg-green-500/20 text-green-300 border-green-500/30'
    : v === 'degraded'
    ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
    : v === 'unhealthy'
    ? 'bg-red-500/20 text-red-300 border-red-500/30'
    : 'bg-muted text-muted-foreground';

const verdictBar = (v: HealthVerdict) =>
  v === 'healthy'
    ? 'bg-green-500'
    : v === 'degraded'
    ? 'bg-amber-500'
    : v === 'unhealthy'
    ? 'bg-red-500'
    : 'bg-muted';

function PlaneCard({ plane, snapshot }: { plane: (typeof PLANE_META)[number]; snapshot?: PlaneSnapshot }) {
  const status: HealthVerdict = (snapshot?.status as HealthVerdict) || 'unknown';
  const counts = snapshot?.counts || {};
  const errors = snapshot?.errors || [];
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-2">
            {plane.icon}
            {plane.label}
          </span>
          <Badge variant="outline" className={`text-[10px] ${verdictColor(status)}`}>
            {status}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {Object.keys(counts).length === 0 ? (
          <div className="text-xs text-muted-foreground italic">No metrics recorded yet.</div>
        ) : (
          <div className="space-y-1">
            {Object.entries(counts).map(([k, v]) => (
              <div key={k} className="flex justify-between text-xs">
                <span className="text-muted-foreground">{k.replace(/_/g, ' ')}</span>
                <span className="font-mono font-medium">{String(v)}</span>
              </div>
            ))}
          </div>
        )}
        {errors.length > 0 && (
          <div className="mt-3 space-y-1">
            {errors.slice(0, 3).map((e, i) => (
              <div key={i} className="flex items-start gap-1.5 text-[10px] text-amber-300">
                <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                <span className="break-all">{e}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Sparkline({ items }: { items: HealthSnapshot[] }) {
  if (items.length === 0) {
    return <div className="text-xs text-muted-foreground italic">No history yet.</div>;
  }
  return (
    <div className="flex items-end gap-0.5 h-8">
      {items
        .slice()
        .reverse()
        .map((s, i) => {
          const height = s.verdict === 'healthy' ? 100 : s.verdict === 'degraded' ? 60 : s.verdict === 'unhealthy' ? 25 : 10;
          return (
            <div
              key={s.iso_ts + i}
              className={`w-1.5 rounded-t ${verdictBar(s.verdict as HealthVerdict)}`}
              style={{ height: `${height}%` }}
              title={`${s.iso_ts} — ${s.verdict}`}
            />
          );
        })}
    </div>
  );
}

export function AiHealthMonitoringPanel() {
  const [latest, setLatest] = useState<HealthSnapshot | null>(null);
  const [history, setHistory] = useState<HealthSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [l, ts] = await Promise.all([
        aiHealthService.latest('all'),
        aiHealthService.timeseries('all', 48),
      ]);
      setLatest(l && !l.empty ? l : null);
      setHistory(ts.items || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to load AI health');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const runNow = async () => {
    setRunning(true);
    try {
      const snap = await aiHealthService.runNow('all');
      setLatest(snap);
      await load();
    } catch (e: any) {
      setError(e?.message || 'Failed to trigger snapshot');
    } finally {
      setRunning(false);
    }
  };

  const rollup: HealthVerdict = (latest?.verdict as HealthVerdict) || 'unknown';
  const planes = latest?.planes || {};

  const recordedAt = useMemo(() => {
    if (!latest?.iso_ts) return null;
    try {
      return new Date(latest.iso_ts).toLocaleString();
    } catch {
      return latest.iso_ts;
    }
  }, [latest]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">AI Health Central</h2>
          <p className="text-xs text-muted-foreground">
            Plane-by-plane health rollup — snapshots persist every 15 minutes to the health table.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className={`text-[11px] ${verdictColor(rollup)}`}>
            Overall: {rollup}
          </Badge>
          <Button size="sm" variant="outline" onClick={runNow} disabled={running || loading}>
            {running ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <RefreshCw className="h-3 w-3 mr-1" />}
            Run now
          </Button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded p-2">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading...
        </div>
      ) : latest ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {PLANE_META.map((p) => (
              <PlaneCard key={p.key} plane={p} snapshot={planes[p.key] as PlaneSnapshot | undefined} />
            ))}
          </div>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Rollup Trend (last {history.length} snapshots)</CardTitle>
            </CardHeader>
            <CardContent>
              <Sparkline items={history} />
              {recordedAt && (
                <p className="text-[10px] text-muted-foreground mt-2">
                  Latest snapshot: {recordedAt} ({latest.elapsed_ms}ms)
                </p>
              )}
            </CardContent>
          </Card>
        </>
      ) : (
        <div className="rounded border p-6 text-center text-sm text-muted-foreground">
          No health snapshots recorded yet. Click "Run now" to generate one.
        </div>
      )}
    </div>
  );
}
