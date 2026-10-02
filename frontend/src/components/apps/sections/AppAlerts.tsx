import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Bell, AlertTriangle, CheckCircle2, Loader2, RefreshCw } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import type { AppConfig } from '@/config/appRegistry';

const SEVERITY_STYLE: Record<string, string> = {
  Critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  High: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  Medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  Low: 'bg-green-500/20 text-green-400 border-green-500/30',
};

interface Props { app: AppConfig; }

export function AppAlerts({ app }: Props) {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAlerts = () => {
    setLoading(true);
    apiClient.get(`/api/v1/apps/${app.id}/alerts`)
      .then((d: any) => setAlerts(d.alerts || []))
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadAlerts(); }, [app.id]);

  const bySeverity = alerts.reduce<Record<string, number>>((acc, a) => {
    acc[a.severity] = (acc[a.severity] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2"><Bell className="h-5 w-5 text-amber-400" /> Alerts</h2>
          <p className="text-xs text-muted-foreground">{alerts.length} active alerts for {app.name}</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadAlerts} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      {/* Severity summary */}
      <div className="flex gap-3">
        {['Critical', 'High', 'Medium', 'Low'].map(s => (
          <Card key={s} className="flex-1">
            <CardContent className="pt-3 pb-3 text-center">
              <p className="text-[10px] text-muted-foreground">{s}</p>
              <p className="text-xl font-bold">{bySeverity[s] || 0}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Alert list */}
      <Card>
        <CardContent className="p-0">
          <ScrollArea className="h-[400px]">
            {loading ? (
              <div className="flex items-center justify-center py-20"><Loader2 className="h-5 w-5 animate-spin" /></div>
            ) : alerts.length > 0 ? (
              <div className="divide-y divide-border/50">
                {alerts.map((alert, i) => (
                  <div key={i} className="flex items-start gap-3 px-4 py-3 hover:bg-muted/20">
                    <AlertTriangle className={`h-4 w-4 mt-0.5 shrink-0 ${
                      alert.severity === 'Critical' ? 'text-red-400' :
                      alert.severity === 'High' ? 'text-orange-400' : 'text-amber-400'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className={`text-[9px] ${SEVERITY_STYLE[alert.severity] || ''}`}>
                          {alert.severity}
                        </Badge>
                        <span className="text-xs font-medium">{alert.type?.replace(/_/g, ' ')}</span>
                        {alert.entity_id && <span className="text-[10px] text-muted-foreground font-mono">{alert.entity_id}</span>}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">{alert.description}</p>
                      {alert.action && <p className="text-[10px] text-blue-400 mt-0.5">{alert.action}</p>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
                <CheckCircle2 className="h-8 w-8 mb-2 opacity-30" />
                <p className="text-sm">No alerts</p>
                <p className="text-xs mt-1">Run the associated journey to generate alerts</p>
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
