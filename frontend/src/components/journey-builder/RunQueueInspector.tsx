import { useEffect, useState } from 'react';
import { apiClient } from '@/services/apiClient';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { confirmDialog } from '@/components/ds/confirm';

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

const HEAD = 'border-b border-border bg-surface-2 px-3 py-2 text-xs font-medium text-muted-foreground';

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
    if (!(await confirmDialog({ title: 'Purge every queue for this run?', description: 'Items that are not yet acknowledged are lost.', confirmLabel: 'Purge', destructive: true }))) return;
    try {
      await apiClient.delete(`/api/v1/control-plane/runs/${encodeURIComponent(runId)}/queues`);
      load();
    } catch (e: any) {
      setError(e?.message || 'purge failed');
    }
  };

  const rows = Object.entries(snapshot?.queues || {});

  return (
    <div className={cn('overflow-hidden rounded-xl border border-border bg-card text-sm', className)}>
      <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
        <div className="font-medium text-foreground">Data queues</div>
        <div className="flex items-center gap-1">
          <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-muted-foreground" onClick={load} disabled={loading} title="Refresh" aria-label="Refresh queues">
            <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
          </Button>
          <Button
            size="sm" variant="ghost" className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive" onClick={handlePurge}
            title="Purge every queue for this run"
            aria-label="Purge every queue for this run"
            disabled={!rows.length}
          >
            <Icon name="trash" className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {error && <InlineError className="m-3" onRetry={load}>{error}</InlineError>}

      {loading && !snapshot && !error && (
        <div className="space-y-2 p-3" aria-busy="true">
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-4/5" />
        </div>
      )}

      {rows.length === 0 && !loading && !error && (
        <div className="px-3 py-4 text-sm text-muted-foreground">No active queues for this run.</div>
      )}

      {rows.length > 0 && (
        <div className="scroll-thin overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr>
                <th scope="col" className={HEAD}>Queue</th>
                <th scope="col" className={cn(HEAD, 'w-20 text-right')}>Depth</th>
                <th scope="col" className={cn(HEAD, 'w-20 text-right')}>Pending</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([key, info]) => (
                <tr key={key} className="border-b border-border last:border-b-0">
                  <td className="max-w-[280px] truncate px-3 py-2 font-mono text-xs text-foreground" title={key}>
                    {_shortenKey(key)}
                  </td>
                  <td className={cn('num px-3 py-2 text-right', info.depth > 0 ? 'font-medium text-foreground' : 'text-subtle-foreground')}>
                    {info.depth}
                  </td>
                  <td className={cn('num px-3 py-2 text-right', info.pending > 0 ? 'font-medium text-foreground' : 'text-subtle-foreground')}>
                    {info.pending}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default RunQueueInspector;
