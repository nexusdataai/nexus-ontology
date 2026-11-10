import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { InlineError, KeyValues, Meter, StatusPill, SubHeading, TableShell, type Tone } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import apiClient from '@/services/apiClient';

interface DiagData {
  connection_health: string;
  auth_method: string | null;
  token_status: string;
  token_expires_at: string | null;
  api_quota_daily_limit: number;
  api_quota_used: number;
  api_quota_remaining: number;
  folders_configured: number;
  total_files_discovered: number;
  files_by_type: Record<string, number>;
  recent_syncs: Array<{ timestamp: string; files_processed: number; duration_ms: number; errors: number }>;
  recent_errors: Array<{ timestamp: string; message: string }>;
  last_sync_at: string | null;
  last_sync_duration_ms: number | null;
  last_sync_files_processed: number | null;
}

const HEALTH_CONFIG: Record<string, { tone: Tone; label: string }> = {
  healthy: { tone: 'success', label: 'Healthy' },
  degraded: { tone: 'warning', label: 'Degraded' },
  disconnected: { tone: 'danger', label: 'Disconnected' },
  unknown: { tone: 'neutral', label: 'Unknown' },
};

const formatDateTime = (iso: string) => {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

const HEAD = 'whitespace-nowrap border-b border-border bg-surface-2 px-4 py-2.5 text-xs font-medium text-muted-foreground';

export default function GoogleDriveDiagnostics() {
  const [data, setData] = useState<DiagData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDiagnostics = useCallback(async () => {
    setLoading(true);
    try {
      const result: any = await apiClient.get('/api/v1/connectors/gdrive/diagnostics');
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDiagnostics(); }, [fetchDiagnostics]);

  if (loading && !data) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-6 w-72 max-w-full" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!data) {
    return <InlineError onRetry={fetchDiagnostics}>The diagnostics could not be loaded.</InlineError>;
  }

  const health = HEALTH_CONFIG[data.connection_health] || HEALTH_CONFIG.unknown;
  const quotaPct = data.api_quota_daily_limit > 0 ? (data.api_quota_used / data.api_quota_daily_limit) * 100 : 0;
  const recentSyncs = data.recent_syncs || [];
  const recentErrors = data.recent_errors || [];
  const fileTypes = Object.entries(data.files_by_type || {});

  return (
    <div className="space-y-8">
      {/* Verdict */}
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <h3 className="text-md font-medium text-foreground">Connection</h3>
            <StatusPill tone={health.tone} variant="soft">{health.label}</StatusPill>
          </div>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            <span className="num font-medium text-foreground">{data.total_files_discovered.toLocaleString()}</span> files found in{' '}
            <span className="num font-medium text-foreground">{data.folders_configured}</span> {data.folders_configured === 1 ? 'folder' : 'folders'}
            {data.last_sync_at && <>, last synced {formatDateTime(data.last_sync_at)}</>}.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchDiagnostics} disabled={loading}>
          <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
        </Button>
      </div>

      {/* Facts and quota */}
      <div className="grid gap-x-12 gap-y-8 xl:grid-cols-2">
        <KeyValues
          items={[
            { label: 'Sign-in token', value: data.token_status === 'valid' ? 'Valid' : String(data.token_status || 'Unknown').replace(/_/g, ' ') },
            { label: 'Token expires', value: data.token_expires_at ? formatDateTime(data.token_expires_at) : 'Not reported' },
            { label: 'Folders watched', value: <span className="num">{data.folders_configured}</span> },
            { label: 'Files found', value: <span className="num">{data.total_files_discovered.toLocaleString()}</span> },
            ...(fileTypes.length > 0
              ? [{ label: 'By type', value: <span className="num">{fileTypes.map(([type, n]) => `${n.toLocaleString()} ${type.toUpperCase()}`).join(' · ')}</span> }]
              : []),
          ]}
        />

        <div>
          <SubHeading>Requests to Google today</SubHeading>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="num text-foreground">
              <span className="font-medium">{data.api_quota_used.toLocaleString()}</span> of {data.api_quota_daily_limit.toLocaleString()}
            </span>
            <span className="num text-muted-foreground">{Math.round(quotaPct)}%</span>
          </div>
          <Meter value={data.api_quota_used} max={data.api_quota_daily_limit || 1} className="mt-2 h-1.5" label="Daily request allowance used" />
          <p className="num mt-2 text-xs text-muted-foreground">{data.api_quota_remaining.toLocaleString()} requests left today</p>
        </div>
      </div>

      {/* Syncs and errors */}
      <div className="grid gap-x-12 gap-y-8 xl:grid-cols-2">
        <div className="min-w-0">
          <SubHeading>Recent syncs</SubHeading>
          {recentSyncs.length > 0 ? (
            <TableShell>
              <table className="w-full min-w-[420px] border-collapse text-sm">
                <thead>
                  <tr>
                    <th scope="col" className={cn(HEAD, 'text-left')}>When</th>
                    <th scope="col" className={cn(HEAD, 'text-right')}>Files</th>
                    <th scope="col" className={cn(HEAD, 'text-right')}>Took</th>
                    <th scope="col" className={cn(HEAD, 'text-left')}>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {recentSyncs.map((sync, i) => (
                    <tr key={i} className="rise border-b border-border last:border-b-0" style={{ '--i': i } as React.CSSProperties}>
                      <td className="num whitespace-nowrap px-4 py-2.5 text-muted-foreground">{formatDateTime(sync.timestamp)}</td>
                      <td className="num px-4 py-2.5 text-right text-foreground">{sync.files_processed}</td>
                      <td className="num whitespace-nowrap px-4 py-2.5 text-right text-muted-foreground">{(sync.duration_ms / 1000).toFixed(1)} s</td>
                      <td className="whitespace-nowrap px-4 py-2.5">
                        {sync.errors > 0
                          ? <StatusPill tone="danger">{sync.errors} {sync.errors === 1 ? 'error' : 'errors'}</StatusPill>
                          : <StatusPill tone="success">No errors</StatusPill>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableShell>
          ) : (
            <p className="border-t border-border py-4 text-sm text-muted-foreground">No syncs have run yet.</p>
          )}
        </div>

        <div className="min-w-0">
          <SubHeading>Recent errors</SubHeading>
          {recentErrors.length > 0 ? (
            <ul className="border-t border-border">
              {recentErrors.map((err, i) => (
                <li key={i} className="rise border-b border-border py-3" style={{ '--i': i } as React.CSSProperties}>
                  <p className="text-sm text-foreground">{err.message}</p>
                  <p className="num mt-0.5 text-xs text-muted-foreground">{formatDateTime(err.timestamp)}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="border-t border-border py-4 text-sm text-muted-foreground">No errors recorded.</p>
          )}
        </div>
      </div>
    </div>
  );
}
