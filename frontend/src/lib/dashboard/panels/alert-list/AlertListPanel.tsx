import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';

interface Alert {
  type?: string;
  severity?: string;
  entity_id?: string;
  description?: string;
  action?: string;
}

const SEVERITY_CONFIG: Record<string, { color: string; icon: typeof AlertTriangle }> = {
  critical: { color: 'bg-red-500/10 text-red-700 border-red-500/30', icon: AlertCircle },
  high: { color: 'bg-orange-500/10 text-orange-700 border-orange-500/30', icon: AlertTriangle },
  medium: { color: 'bg-amber-500/10 text-amber-700 border-amber-500/30', icon: AlertTriangle },
  low: { color: 'bg-blue-500/10 text-blue-700 border-blue-500/30', icon: Info },
};

export function AlertListPanel({ data, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Loading...' : 'No alerts'}
      </div>
    );
  }

  const rows = dataFrameToRows(data[0]);
  let alerts: Alert[] = [];

  if (rows.length > 0) {
    const first = rows[0];
    if (first.alerts) {
      try {
        const parsed = typeof first.alerts === 'string' ? JSON.parse(first.alerts) : first.alerts;
        if (Array.isArray(parsed)) alerts = parsed;
      } catch {
        alerts = [];
      }
    } else if (first.type || first.severity) {
      alerts = rows as unknown as Alert[];
    }
  }

  const listHeight = Math.max(height - 40, 100);

  return (
    <ScrollArea style={{ height: listHeight }} className="px-4 pb-4">
      <div className="space-y-2">
        {alerts.length === 0 ? (
          <div className="flex items-center justify-center h-20 text-sm text-muted-foreground">No alerts</div>
        ) : (
          alerts.map((alert, i) => {
            const sev = SEVERITY_CONFIG[alert.severity || 'low'] || SEVERITY_CONFIG.low;
            const Icon = sev.icon;
            return (
              <div key={i} className={`rounded-md border p-3 ${sev.color}`}>
                <div className="flex items-start gap-2">
                  <Icon className="h-4 w-4 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <Badge variant="outline" className="text-[9px]">{alert.type || 'alert'}</Badge>
                      <Badge variant="outline" className="text-[9px]">{alert.severity || 'low'}</Badge>
                      {alert.entity_id && <span className="text-[9px] text-muted-foreground font-mono">{alert.entity_id}</span>}
                    </div>
                    <p className="text-xs">{alert.description}</p>
                    {alert.action && <p className="text-[10px] mt-1 opacity-70">Action: {alert.action}</p>}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </ScrollArea>
  );
}
