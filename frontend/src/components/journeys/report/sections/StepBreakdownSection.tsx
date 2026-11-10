import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ReportSectionStepBreakdown } from '@/types/callProcessingJourney';

interface Props {
  section: ReportSectionStepBreakdown;
}

export function StepBreakdownSection({ section }: Props) {
  const steps = section.steps || [];
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{section.title}</CardTitle>
      </CardHeader>
      <CardContent>
        {steps.length === 0 && (
          <div className="text-xs text-muted-foreground italic py-2 text-center">
            No step data yet.
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="px-2 py-1 font-medium">Step</th>
                <th className="px-2 py-1 font-medium">Tool</th>
                <th className="px-2 py-1 font-medium text-right">Completed</th>
                <th className="px-2 py-1 font-medium text-right">Failed</th>
                <th className="px-2 py-1 font-medium text-right">Other</th>
                <th className="px-2 py-1 font-medium text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {steps.map((s) => (
                <tr key={s.step_id} className="border-b last:border-b-0 hover:bg-muted/30">
                  <td className="px-2 py-1">
                    <div className="font-medium">{s.name}</div>
                    <div className="text-xs font-mono text-muted-foreground">{s.step_id}</div>
                  </td>
                  <td className="px-2 py-1">
                    {s.tool ? (
                      <Badge variant="outline" className="text-xs">{s.tool}</Badge>
                    ) : (
                      <span className="text-muted-foreground">--</span>
                    )}
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums text-success">{s.completed}</td>
                  <td className="px-2 py-1 text-right tabular-nums text-destructive">{s.failed}</td>
                  <td className="px-2 py-1 text-right tabular-nums text-muted-foreground">
                    {s.other + s.pending}
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums font-medium">{s.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

export default StepBreakdownSection;
