import { Badge } from '@/components/ui/badge';
import type { CatalogueHealthReport, CatalogueIssue } from '@/services/connectorApiWorkbenchService';

interface Props {
  report: CatalogueHealthReport;
}

export default function CatalogueHealthSection({ report }: Props) {
  const entries = Object.entries(report.issues_by_api).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Specs checked" value={report.totals.checked} />
        <Stat label="Errors" value={report.totals.errors} tone={report.totals.errors ? 'red' : 'green'} />
        <Stat label="Warnings" value={report.totals.warnings} tone={report.totals.warnings ? 'amber' : 'green'} />
        <Stat label="Specs with issues" value={report.totals.specs_with_issues} />
      </div>
      {entries.length === 0 ? (
        <div className="text-xs text-muted-foreground italic">No catalogue issues found.</div>
      ) : (
        <div className="space-y-2">
          {entries.map(([apiId, issues]) => (
            <div key={apiId} className="border border-border/40 rounded-md px-3 py-2">
              <div className="font-mono text-xs mb-1">{apiId}</div>
              <div className="space-y-1">
                {issues.map((it: CatalogueIssue, i: number) => (
                  <div key={i} className="flex items-start gap-2 text-xs">
                    <Badge
                      variant="outline"
                      className={`text-xs shrink-0 ${
                        it.severity === 'error'
                          ? 'text-destructive border-destructive/30 bg-destructive/10'
                          : 'text-warning border-warning/30 bg-warning/10'
                      }`}
                    >{it.severity}</Badge>
                    <span className="font-mono text-muted-foreground shrink-0">{it.code}</span>
                    <span className="text-muted-foreground">{it.message}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
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
