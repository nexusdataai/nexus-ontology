import type { DashboardWidget } from '@/config/dashboardWidgets';
import { StatusPill } from '@/components/ds/kit';
import { Icon } from '@/components/ds/Icon';
import { WidgetFrame, labelOf } from './WidgetFrame';

interface Alert {
  type?: string;
  severity?: string;
  entity_id?: string;
  description?: string;
  action?: string;
}

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

const sev = (a: Alert) => String(a.severity || 'low').toLowerCase();
const ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export function AlertListWidget({ widget, data, loading }: Props) {
  let alerts: Alert[] = [];

  if (data?.rows?.length > 0) {
    const first = data.rows[0];
    if (first.alerts) {
      try {
        const parsed = typeof first.alerts === 'string' ? JSON.parse(first.alerts) : first.alerts;
        if (Array.isArray(parsed)) alerts = parsed;
      } catch {
        alerts = [];
      }
    } else if (first.type || first.severity) {
      alerts = data.rows;
    }
  }

  const sorted = [...alerts].sort((a, b) => (ORDER[sev(a)] ?? 9) - (ORDER[sev(b)] ?? 9));
  const urgent = alerts.filter(a => sev(a) === 'critical' || sev(a) === 'high').length;

  return (
    <WidgetFrame
      title={widget.title}
      description={alerts.length ? `${alerts.length} open${urgent ? `, ${urgent} need attention now` : ''}` : undefined}
      loading={loading}
      empty={alerts.length === 0}
      emptyText="Nothing needs attention"
      flush
      minHeight={200}
    >
      <ul className="scroll-thin max-h-[340px] overflow-y-auto border-t border-border">
        {sorted.map((alert, i) => (
          <li key={i} className="rise border-b border-border px-5 py-3 last:border-b-0" style={{ ['--i' as any]: Math.min(i, 8) }}>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <StatusPill status={alert.severity || 'low'} variant="soft" />
              <span className="text-sm font-medium text-foreground">{labelOf(alert.type || 'alert')}</span>
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
    </WidgetFrame>
  );
}
