import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ReportSectionTimeline } from '@/types/callProcessingJourney';
import { Badge } from '@/components/ui/badge';

interface Props {
  section: ReportSectionTimeline;
}

const STATE_COLOR: Record<string, string> = {
  pending: 'bg-warning/15 text-warning border-warning/30',
  in_progress: 'bg-primary/15 text-primary border-primary/30',
  awaiting_step_approval: 'bg-warning/15 text-warning border-warning/30',
  completed: 'bg-success/15 text-success border-success/30',
  failed: 'bg-destructive/15 text-destructive border-destructive/30',
  rejected: 'bg-destructive/15 text-destructive border-destructive/30',
  cancelled: 'bg-muted text-muted-foreground border-muted-foreground/30',
};

export function TimelineSection({ section }: Props) {
  const events = section.events || [];
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{section.title}</CardTitle>
      </CardHeader>
      <CardContent>
        {events.length === 0 && (
          <div className="text-xs text-muted-foreground italic py-2 text-center">
            No transitions recorded yet.
          </div>
        )}
        <div className="space-y-1.5 max-h-64 overflow-auto">
          {events.map((e, i) => (
            <div key={i} className="flex items-center gap-2 text-xs border-b last:border-b-0 py-1">
              <span className="text-xs font-mono text-muted-foreground w-40 shrink-0">
                {(e.timestamp || '').slice(0, 19).replace('T', ' ')}
              </span>
              <Badge variant="outline" className={`text-xs ${STATE_COLOR[e.fromState || ''] || ''}`}>
                {e.fromState || '--'}
              </Badge>
              <span className="text-muted-foreground">-&gt;</span>
              <Badge variant="outline" className={`text-xs ${STATE_COLOR[e.toState || ''] || ''}`}>
                {e.toState || '--'}
              </Badge>
              {e.stepId && (
                <span className="font-mono text-xs text-muted-foreground">
                  step:{e.stepId}
                </span>
              )}
              {e.reason && (
                <span className="text-muted-foreground italic truncate" title={e.reason}>
                  {e.reason}
                </span>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default TimelineSection;
