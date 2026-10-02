import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Minus, Loader2 } from 'lucide-react';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

export function KPICardWidget({ widget, data, loading }: Props) {
  if (loading) {
    return (
      <Card>
        <CardContent className="pt-4 flex items-center justify-center h-20">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const { config } = widget;
  const isPlaceholder = config.placeholder;

  let rawValue: number | string = '--';
  if (!isPlaceholder && data?.rows?.length > 0) {
    const col = widget.query.columns?.[0];
    if (col && data.rows[0][col] !== undefined) {
      rawValue = data.rows[0][col];
    }
  }

  let display = rawValue;
  if (typeof rawValue === 'string' && rawValue !== '--') {
    const parsed = parseFloat(rawValue);
    if (!isNaN(parsed)) {
      let v = parsed;
      if (config.multiply) v = v * (config.multiply as number);
      if (config.format === 'currency') {
        display = `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
      } else {
        display = `${v.toFixed(1)}${config.unit || ''}`;
      }
      rawValue = v;
    }
  } else if (typeof rawValue === 'number') {
    let v = rawValue;
    if (config.multiply) v = v * (config.multiply as number);
    if (config.format === 'currency') {
      display = `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    } else {
      display = `${v.toFixed(1)}${config.unit || ''}`;
    }
    rawValue = v;
  }

  const numValue = typeof rawValue === 'number' ? rawValue : NaN;
  const target = config.target as number | undefined;
  let trend: 'good' | 'bad' | 'neutral' = 'neutral';
  if (target !== undefined && !isNaN(numValue)) {
    if (config.direction === 'lower') {
      trend = numValue <= target ? 'good' : 'bad';
    } else {
      trend = numValue >= target ? 'good' : 'bad';
    }
  }

  const TrendIcon = trend === 'good' ? TrendingUp : trend === 'bad' ? TrendingDown : Minus;
  const trendColor = trend === 'good' ? 'text-green-500' : trend === 'bad' ? 'text-red-500' : 'text-muted-foreground';

  return (
    <Card>
      <CardContent className="pt-4">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{widget.title}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-2xl font-bold">{String(display)}</span>
          {target !== undefined && (
            <TrendIcon className={`h-4 w-4 ${trendColor}`} />
          )}
        </div>
        {target !== undefined && (
          <Badge variant="outline" className="text-[9px] mt-1">Target: {config.direction === 'lower' ? '<' : '>'} {target}{config.unit || ''}</Badge>
        )}
      </CardContent>
    </Card>
  );
}
