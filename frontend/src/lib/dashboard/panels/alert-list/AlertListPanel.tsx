import { StatusPill } from '@/components/ds/kit';
import { Icon } from '@/components/ds/Icon';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { PanelState, fieldLabel } from '../_shared';

interface Alert {
  type?: string;
  severity?: string;
  entity_id?: string;
  description?: string;
  action?: string;
}

export function AlertListPanel({ data, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].length === 0) {
    return (
      <PanelState loading={loading} text="No alerts" />
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

  const sevOf = (a: Alert) => String(a.severity || 'low').toLowerCase();
  const rank: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  const sorted = [...alerts].sort((a, b) => (rank[sevOf(a)] ?? 9) - (rank[sevOf(b)] ?? 9));

  if (sorted.length === 0) return <PanelState text="Nothing needs attention" />;

  return (
    <ul className="scroll-thin overflow-y-auto border-t border-border" style={{ height: Math.max(height, 100) }}>
      {sorted.map((alert, i) => (
        <li key={i} className="border-b border-border px-4 py-3 last:border-b-0">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <StatusPill status={sevOf(alert)} variant="soft" />
            <span className="text-sm font-medium text-foreground">{fieldLabel(alert.type || 'alert')}</span>
            {alert.entity_id && <span className="ml-auto font-mono text-xs text-muted-foreground">{alert.entity_id}</span>}
          </div>
          {alert.description && <p className="mt-1.5 text-sm text-muted-foreground">{alert.description}</p>}
          {alert.action && (
            <p className="mt-1.5 flex items-start gap-1.5 text-xs text-foreground">
              <Icon name="arrow-right" className="mt-0.5 h-3 w-3 shrink-0 text-primary dark:text-brand-hi" />
              <span>{alert.action}</span>
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
