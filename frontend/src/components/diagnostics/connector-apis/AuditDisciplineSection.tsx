import { Badge } from '@/components/ui/badge';
import type { AuditDisciplineReport, Smell } from '@/services/connectorApiWorkbenchService';

interface Props {
  report: AuditDisciplineReport;
}

function smellBadge(smell: Smell) {
  const cls =
    smell === 'ok' ? 'text-success border-success/30 bg-success/10'
    : smell === 'never_called' ? 'text-warning border-warning/30 bg-warning/10'
    : 'text-destructive border-destructive/30 bg-destructive/10';
  return <Badge variant="outline" className={`text-xs ${cls}`}>{smell}</Badge>;
}

export default function AuditDisciplineSection({ report }: Props) {
  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Specs checked" value={report.totals.checked} />
        <Stat label="ok" value={report.totals.ok} tone="green" />
        <Stat label="never called" value={report.totals.never_called} tone={report.totals.never_called ? 'amber' : 'green'} />
        <Stat label="audit missing" value={report.totals.audit_missing} tone={report.totals.audit_missing ? 'red' : 'green'} />
      </div>

      <div className="border rounded-md max-h-96 overflow-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-muted/40">
            <tr className="text-left">
              <th className="px-2 py-1">api_id</th>
              <th className="px-2 py-1">system</th>
              <th className="px-2 py-1">risk</th>
              <th className="px-2 py-1">total</th>
              <th className="px-2 py-1">24h</th>
              <th className="px-2 py-1">last_event_ts</th>
              <th className="px-2 py-1">smell</th>
            </tr>
          </thead>
          <tbody>
            {report.rows.map(r => (
              <tr key={r.api_id} className="border-t border-border/40">
                <td className="px-2 py-1 font-mono">{r.api_id}</td>
                <td className="px-2 py-1 text-muted-foreground">{r.target_system}</td>
                <td className="px-2 py-1 text-muted-foreground">{r.risk_level}</td>
                <td className="px-2 py-1 font-mono">{r.total_events}</td>
                <td className="px-2 py-1 font-mono">{r.events_24h}</td>
                <td className="px-2 py-1 font-mono text-xs text-muted-foreground">{r.last_event_ts || '-'}</td>
                <td className="px-2 py-1">{smellBadge(r.smell)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: 'green' | 'amber' | 'red' }) {
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
