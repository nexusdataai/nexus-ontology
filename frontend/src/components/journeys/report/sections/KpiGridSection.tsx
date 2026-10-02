import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ReportSectionKpiGrid } from '@/types/callProcessingJourney';
import { KpiCard } from '../KpiCard';

interface Props {
  section: ReportSectionKpiGrid;
}

export function KpiGridSection({ section }: Props) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{section.title}</CardTitle>
        {section.description && (
          <p className="text-xs text-muted-foreground">{section.description}</p>
        )}
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {(section.kpis || []).map((k) => <KpiCard key={k.key} kpi={k} compact />)}
        </div>
      </CardContent>
    </Card>
  );
}

export default KpiGridSection;
