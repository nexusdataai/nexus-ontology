import React from 'react';
import { Card } from '@/components/ui/card';
import type { ReportKpiValue } from '@/types/callProcessingJourney';
import { formatValue, statusColorClass } from './formatters';
import { getIcon } from './iconMap';
import { cn } from '@/lib/utils';

interface Props {
  kpi: ReportKpiValue;
  compact?: boolean;
}

/**
 * One KPI tile: icon + value (formatted per ``kpi.format``) + label.
 * Status -> coloured value when the backend report builder ran the
 * value through a threshold rule.
 */
export function KpiCard({ kpi, compact = false }: Props) {
  const Icon = getIcon(kpi.icon);
  const valueText = formatValue(kpi.value, kpi.format);
  const valueColour = statusColorClass(kpi.status);
  return (
    <Card className={cn('p-3 flex flex-col gap-1', compact && 'p-2')}>
      <div className="flex items-center justify-between text-muted-foreground">
        <Icon className={cn(compact ? 'h-3.5 w-3.5' : 'h-4 w-4')} />
      </div>
      <div className={cn('font-semibold', compact ? 'text-base' : 'text-lg', valueColour)}>
        {valueText}
      </div>
      <div className={cn('text-muted-foreground', compact ? 'text-xs' : 'text-xs')}>
        {kpi.label}
      </div>
    </Card>
  );
}

export default KpiCard;
