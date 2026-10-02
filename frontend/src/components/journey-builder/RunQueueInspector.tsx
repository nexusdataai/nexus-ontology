import { useEffect, useState } from 'react';
import { Loader2, RefreshCw, Trash2 } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

/**
 * Inspector for the Data Queues subsystem. Fetches a per-queue
 * snapshot for the given ``runId`` and renders a small table with
 * depth + pending counts. Used inside the RunResultsPanel drawer while
 * a dataflow journey is paused / running.
 *
 * Mounts a Purge button that calls the matching DELETE endpoint so an
 * operator can clear an apparently-stuck queue without restarting the
 * runner.
 */

interface QueueSnapshotEntry {
  depth: number;
  pending: number;
  seq?: number;
}

interface QueueSnapshotResponse {
  run_id: string;
  queues: Record<string, QueueSnapshotEntry>;
}

interface Props {
  runId: string;
  className?: string;
  /** Optional poll interval in milliseconds. 0 disables auto-refresh. */
  pollIntervalMs?: number;
}

function _shortenKey(key: string): string {
  // Keys look like ``nexus:queue:<run_id>:<from_step>.<rel>-><to_step>.<param>``.
  // Strip the prefix to keep the table readable.
  const arrow = key.indexOf(':queue:');
  if (arrow < 0) return key;
  const tail = key.slice(arrow + ':queue:'.length);
  const colon = tail.indexOf(':');
  return colon >= 0 ? tail.slice(colon + 1) : tail;
}

export function RunQueueInspector({ runId, className, pollIntervalMs = 0 }: Props) {
  const [snapshot, setSnapshot] = useState<QueueSnapshotResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<QueueSnapshotResponse>(
        `/api/v1/control-plane/runs/${encodeURIComponent(runId)}/queues`,
      );
      setSnapshot(data);
    } catch (e: any) {
      setError(e?.message || 'failed to load queue snapshot');
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    if (pollIntervalMs <= 0) return undefined;
    const t = window.setInterval(load, pollIntervalMs);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, pollIntervalMs]);

  const handlePurge = async () => {
    if (!runId) return;
    if (!window.confirm('Purge every queue for this run? Items not yet acked are lost.')) return;
    try {
      await apiClient.delete(`/api/v1/control-plane/runs/${encodeURIComponent(runId)}/queues`);
      load();
    } catch (e: any) {
      setError(e?.message || 'purge failed');
    }
  };

  const rows = Object.entries(snapshot?.queues || {});

  return (
    <div className={cn('border rounded-md bg-card text-xs', className)}>
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b">
        <div className="font-medium">Data queues</div>
        <div className="flex items-center gap-1">
          <Button size="sm" variant="ghost" onClick={load} disabled={loading} title="Refresh">
            {loading
              ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
              : <RefreshCw className="h-3.5 w-3.5" />}
          </Button>
          <Button
            size="sm" variant="ghost" onClick={handlePurge}
            title="Purge every queue for this run"
            disabled={!rows.length}
          >
            <Trash2 className="h-3.5 w-3.5 text-red-300" />
          </Button>
        </div>
      </div>

      {error && (
        <div className="px-3 py-2 text-red-300">
          {error}
        </div>
      )}

      {rows.length === 0 && !loading && !error && (
        <div className="px-3 py-4 text-muted-foreground italic">No active queues for this run.</div>
      )}

      {rows.length > 0 && (
        <table className="w-full text-left">
          <thead className="bg-muted/30 text-[10px] uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-1.5 font-medium">Queue</th>
              <th className="px-3 py-1.5 font-medium w-16 text-right">Depth</th>
              <th className="px-3 py-1.5 font-medium w-16 text-right">Pending</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([key, info]) => (
              <tr key={key} className="border-t">
                <td className="px-3 py-1.5 font-mono text-[11px] truncate" title={key}>
                  {_shortenKey(key)}
                </td>
                <td className="px-3 py-1.5 text-right">
                  <Badge variant="outline" className={cn(
                    'text-[10px]',
                    info.depth > 0 && 'bg-blue-500/10 text-blue-300 border-blue-500/30',
                  )}>
                    {info.depth}
                  </Badge>
                </td>
                <td className="px-3 py-1.5 text-right">
                  <Badge variant="outline" className={cn(
                    'text-[10px]',
                    info.pending > 0 && 'bg-amber-500/10 text-amber-300 border-amber-500/30',
                  )}>
                    {info.pending}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default RunQueueInspector;
