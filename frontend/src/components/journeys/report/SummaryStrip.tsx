import type { ReportKpiValue } from '@/types/callProcessingJourney';
import { KpiCard } from './KpiCard';

interface Props {
  kpis: ReportKpiValue[];
}

/**
 * Horizontal strip of summary KPI cards at the top of the report
 * modal. Mirrors the visual the legacy "Call Processing Report" shows
 * but the cards are schema-driven now -- O2C journeys show DSO /
 * match rate, demand journeys show MAPE / stockout risk, etc.
 */
export function SummaryStrip({ kpis }: Props) {
  if (!kpis || kpis.length === 0) return null;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
      {kpis.map((k) => <KpiCard key={k.key} kpi={k} />)}
    </div>
  );
}

export default SummaryStrip;
