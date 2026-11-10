import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ReportSectionAlertsList } from '@/types/callProcessingJourney';

interface Props {
  section: ReportSectionAlertsList;
}

export function AlertsListSection({ section }: Props) {
  const groups = section.groups || [];
  const alerts = section.alerts || [];
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span>{section.title}</span>
          <span className="text-xs text-muted-foreground font-normal">
            {alerts.length} alert{alerts.length === 1 ? '' : 's'}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {groups.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {groups.map((g) => (
              <Badge key={g.key} variant="outline" className="text-xs">
                {g.label}
                <span className="ml-1.5 font-mono">{g.count}</span>
              </Badge>
            ))}
          </div>
        )}
        {alerts.length === 0 && (
          <div className="text-xs text-muted-foreground italic py-2 text-center">
            No alerts.
          </div>
        )}
        <div className="space-y-1 max-h-64 overflow-auto">
          {alerts.slice(0, 50).map((a, i) => (
            <div key={i} className="text-xs border rounded p-2 bg-background/40">
              <div className="flex items-center gap-2">
                {a.type && (
                  <Badge variant="outline" className="text-xs">{a.type}</Badge>
                )}
                {a.severity && (
                  <Badge variant="outline" className="text-xs">{a.severity}</Badge>
                )}
                <span className="text-muted-foreground text-xs ml-auto">
                  {a.jobId}
                </span>
              </div>
              {a.message && <div className="mt-0.5">{a.message}</div>}
              {a.entity_id && (
                <div className="text-xs text-muted-foreground mt-0.5 font-mono">
                  {a.entity_id}
                </div>
              )}
            </div>
          ))}
          {alerts.length > 50 && (
            <div className="text-xs text-muted-foreground italic text-center pt-1">
              ... showing 50 of {alerts.length}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default AlertsListSection;
