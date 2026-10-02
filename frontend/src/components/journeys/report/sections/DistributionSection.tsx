import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ReportSectionDistribution } from '@/types/callProcessingJourney';

interface Props {
  section: ReportSectionDistribution;
}

/**
 * Renders a horizontal-bar distribution of buckets. Schema-driven --
 * the backend builder counts occurrences across all completed jobs at
 * a single source path (scalar or list); each unique value becomes a
 * bucket.
 */
export function DistributionSection({ section }: Props) {
  const buckets = section.buckets || [];
  const max = buckets.reduce((m, b) => Math.max(m, b.count), 0) || 1;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span>{section.title}</span>
          <span className="text-xs text-muted-foreground font-normal">
            {section.total} items
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {buckets.length === 0 && (
          <div className="text-xs text-muted-foreground italic py-2 text-center">
            No data yet.
          </div>
        )}
        <div className="space-y-1.5">
          {buckets.map((b) => (
            <div key={b.label} className="flex items-center gap-2 text-xs">
              <span className="w-32 shrink-0 truncate" title={b.label}>{b.label}</span>
              <div className="flex-1 h-3 bg-muted/30 rounded overflow-hidden">
                <div
                  className="h-full bg-primary/60"
                  style={{ width: `${(b.count * 100) / max}%` }}
                />
              </div>
              <span className="w-12 text-right tabular-nums">{b.count}</span>
              <span className="w-12 text-right tabular-nums text-muted-foreground">
                {b.percentage.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default DistributionSection;
