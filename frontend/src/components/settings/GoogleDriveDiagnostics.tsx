import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity, CheckCircle2, XCircle, AlertTriangle, Clock,
  Loader2, RefreshCw, HardDrive, BarChart3,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
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

const HEALTH_CONFIG: Record<string, { color: string; icon: React.ElementType; label: string }> = {
  healthy: { color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: CheckCircle2, label: 'Healthy' },
  degraded: { color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: AlertTriangle, label: 'Degraded' },
  disconnected: { color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: XCircle, label: 'Disconnected' },
  unknown: { color: 'bg-muted text-muted-foreground', icon: Clock, label: 'Unknown' },
};

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

  if (loading) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  }

  if (!data) {
    return (
      <div className="text-center py-10">
        <p className="text-sm text-muted-foreground">Unable to load diagnostics</p>
        <Button variant="outline" size="sm" className="mt-2" onClick={fetchDiagnostics}>
          <RefreshCw className="h-3.5 w-3.5 mr-1" /> Retry
        </Button>
      </div>
    );
  }

  const health = HEALTH_CONFIG[data.connection_health] || HEALTH_CONFIG.unknown;
  const HealthIcon = health.icon;
  const quotaPct = data.api_quota_daily_limit > 0 ? (data.api_quota_used / data.api_quota_daily_limit) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <Activity className="h-4 w-4" /> Diagnostics
        </h3>
        <Button variant="outline" size="sm" onClick={fetchDiagnostics}>
          <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <Badge className={health.color}>
              <HealthIcon className="h-3 w-3 mr-1" /> {health.label}
            </Badge>
            <p className="text-[10px] text-muted-foreground mt-2">Connection Health</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <div className="text-lg font-bold">{data.token_status === 'valid' ? 'Valid' : data.token_status}</div>
            <p className="text-[10px] text-muted-foreground">Token Status</p>
            {data.token_expires_at && (
              <p className="text-[9px] text-muted-foreground mt-1">Expires: {new Date(data.token_expires_at).toLocaleString()}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <div className="text-lg font-bold">{data.folders_configured}</div>
            <p className="text-[10px] text-muted-foreground">Folders Configured</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <div className="text-lg font-bold">{data.total_files_discovered.toLocaleString()}</div>
            <p className="text-[10px] text-muted-foreground">Files Discovered</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="h-4 w-4" /> API Quota Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <Progress value={quotaPct} className="flex-1 h-2" />
            <span className="text-xs font-mono">{data.api_quota_used.toLocaleString()} / {data.api_quota_daily_limit.toLocaleString()}</span>
          </div>
          <p className="text-[10px] text-muted-foreground mt-1">{data.api_quota_remaining.toLocaleString()} requests remaining today</p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Recent Syncs</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[200px]">
              {data.recent_syncs.length > 0 ? (
                <table className="w-full text-xs">
                  <thead><tr className="bg-muted/30">
                    <th className="px-3 py-1.5 text-left font-medium">Time</th>
                    <th className="px-3 py-1.5 text-right font-medium">Files</th>
                    <th className="px-3 py-1.5 text-right font-medium">Duration</th>
                    <th className="px-3 py-1.5 text-right font-medium">Errors</th>
                  </tr></thead>
                  <tbody className="divide-y divide-border/50">
                    {data.recent_syncs.map((sync, i) => (
                      <tr key={i} className="hover:bg-muted/20">
                        <td className="px-3 py-1.5">{new Date(sync.timestamp).toLocaleString()}</td>
                        <td className="px-3 py-1.5 text-right font-mono">{sync.files_processed}</td>
                        <td className="px-3 py-1.5 text-right font-mono">{(sync.duration_ms / 1000).toFixed(1)}s</td>
                        <td className="px-3 py-1.5 text-right">
                          {sync.errors > 0 ? <span className="text-red-400">{sync.errors}</span> : <span className="text-green-400">0</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-xs text-muted-foreground text-center py-8">No sync history yet</p>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Recent Errors</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[200px]">
              {data.recent_errors.length > 0 ? (
                <div className="divide-y divide-border/50">
                  {data.recent_errors.map((err, i) => (
                    <div key={i} className="px-3 py-2">
                      <p className="text-[10px] text-muted-foreground">{new Date(err.timestamp).toLocaleString()}</p>
                      <p className="text-xs text-red-400 mt-0.5">{err.message}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground text-center py-8">No errors recorded</p>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
