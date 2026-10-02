import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ReportSectionTimeline } from '@/types/callProcessingJourney';
import { Badge } from '@/components/ui/badge';

interface Props {
  section: ReportSectionTimeline;
}

const STATE_COLOR: Record<string, string> = {
  pending: 'bg-amber-500/15 text-amber-500 border-amber-500/30',
  in_progress: 'bg-blue-500/15 text-blue-500 border-blue-500/30',
  awaiting_step_approval: 'bg-amber-500/15 text-amber-500 border-amber-500/30',
  completed: 'bg-green-500/15 text-green-500 border-green-500/30',
  failed: 'bg-red-500/15 text-red-500 border-red-500/30',
  rejected: 'bg-red-500/15 text-red-500 border-red-500/30',
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
              <span className="text-[10px] font-mono text-muted-foreground w-40 shrink-0">
                {(e.timestamp || '').slice(0, 19).replace('T', ' ')}
              </span>
              <Badge variant="outline" className={`text-[9px] ${STATE_COLOR[e.fromState || ''] || ''}`}>
                {e.fromState || '--'}
              </Badge>
              <span className="text-muted-foreground">-&gt;</span>
              <Badge variant="outline" className={`text-[9px] ${STATE_COLOR[e.toState || ''] || ''}`}>
                {e.toState || '--'}
              </Badge>
              {e.stepId && (
                <span className="font-mono text-[10px] text-muted-foreground">
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
