import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { PanelProps } from '../types';

export function KPICardPanel({ data, options, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Loading...' : 'No data'}
      </div>
    );
  }

  const frame = data[0];
  const valueFieldName = (options.valueField as string) || frame.fields[0]?.name;
  const valueField = frame.fields.find((f) => f.name === valueFieldName) ?? frame.fields[0];
  const rawValue = valueField?.values?.[0];

  const unit = (options.unit as string) || '';
  const format = options.format as string | undefined;
  const target = options.target as number | undefined;
  const direction = (options.direction as string) || 'higher';
  const multiply = options.multiply as number | undefined;

  let numValue = typeof rawValue === 'number' ? rawValue : parseFloat(String(rawValue));
  if (isNaN(numValue)) {
    return (
      <div className="flex flex-col justify-center h-full px-4">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{valueFieldName}</p>
        <span className="text-2xl font-bold mt-1">{String(rawValue ?? '--')}</span>
      </div>
    );
  }

  if (multiply) numValue *= multiply;

  let display: string;
  if (format === 'currency') {
    display = `$${numValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  } else {
    display = `${numValue.toFixed(1)}${unit}`;
  }

  let trend: 'good' | 'bad' | 'neutral' = 'neutral';
  if (target !== undefined) {
    trend = direction === 'lower' ? (numValue <= target ? 'good' : 'bad') : (numValue >= target ? 'good' : 'bad');
  }

  const TrendIcon = trend === 'good' ? TrendingUp : trend === 'bad' ? TrendingDown : Minus;
  const trendColor = trend === 'good' ? 'text-green-500' : trend === 'bad' ? 'text-red-500' : 'text-muted-foreground';

  return (
    <div className="flex flex-col justify-center h-full px-4">
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{valueFieldName}</p>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-2xl font-bold">{display}</span>
        {target !== undefined && <TrendIcon className={`h-4 w-4 ${trendColor}`} />}
      </div>
      {target !== undefined && (
        <Badge variant="outline" className="text-[9px] mt-1 w-fit">
          Target: {direction === 'lower' ? '<' : '>'} {target}{unit}
        </Badge>
      )}
    </div>
  );
}
