import { Badge } from '@/components/ui/badge';
import type { DiagSummary } from '@/services/connectorApiWorkbenchService';

interface Props {
  summary: DiagSummary;
}

export default function SummarySection({ summary }: Props) {
  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="APIs" value={summary.checked} />
        <Kpi label="Verified" value={summary.verified} tone="green" />
        <Kpi label="Never invoked" value={summary.never_invoked} tone={summary.never_invoked ? 'amber' : 'green'} />
        <Kpi label="Orphans (no caller)" value={summary.orphans} tone={summary.orphans ? 'amber' : 'green'} />
        <Kpi label="With verify hint" value={summary.with_hint} />
        <Kpi label="Without verify hint" value={summary.without_hint} tone={summary.without_hint ? 'amber' : 'green'} />
        <Kpi label="Audit events 24h" value={summary.audit_events_24h} />
        <Kpi label="Health" value={summary.overall} tone={
          summary.overall === 'healthy' ? 'green'
          : summary.overall === 'unhealthy' ? 'red'
          : 'amber'
        } />
      </div>
      <div className="flex items-center gap-2 flex-wrap text-xs">
        <span className="text-muted-foreground">Target system:</span>
        {Object.entries(summary.by_target_system).map(([k, v]) => (
          <Badge key={k} variant="outline" className="text-xs">{v} {k}</Badge>
        ))}
      </div>
      <div className="flex items-center gap-2 flex-wrap text-xs">
        <span className="text-muted-foreground">Risk level:</span>
        {Object.entries(summary.by_risk_level).map(([k, v]) => (
          <Badge key={k} variant="outline" className={`text-xs ${
            k === 'high_risk_write' ? 'text-destructive border-destructive/30'
            : k === 'low_risk_write' ? 'text-warning border-warning/30'
            : 'text-success border-success/30'
          }`}>{v} {k}</Badge>
        ))}
      </div>
    </div>
  );
}

function Kpi({ label, value, tone }: { label: string; value: number | string; tone?: 'green' | 'amber' | 'red' }) {
  const cls = tone === 'green' ? 'text-success'
    : tone === 'amber' ? 'text-warning'
    : tone === 'red' ? 'text-destructive'
    : '';
  return (
    <div>
      <div className="text-muted-foreground text-xs">{label}</div>
      <div className={`font-mono ${cls}`}>{value}</div>
    </div>
  );
}
