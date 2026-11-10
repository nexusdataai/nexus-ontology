import type { PanelProps } from '../types';
import { AnimatedNumber } from '@/components/ds/AnimatedNumber';
import { cn } from '@/lib/utils';
import { PanelState, fieldLabel } from '../_shared';

/** One headline number, with a target marker when the panel has a target. */
export function KPICardPanel({ data, options, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length === 0) return <PanelState loading={loading} />;

  const frame = data[0];
  const valueFieldName = (options.valueField as string) || frame.fields[0]?.name;
  const valueField = frame.fields.find((f) => f.name === valueFieldName) ?? frame.fields[0];
  const rawValue = valueField?.values?.[0];

  const isCurrency = options.format === 'currency';
  const unit = isCurrency ? '' : (options.unit as string) || '';
  const target = options.target as number | undefined;
  const lower = ((options.direction as string) || 'higher') === 'lower';
  const multiply = options.multiply as number | undefined;

  let value = typeof rawValue === 'number' ? rawValue : parseFloat(String(rawValue));
  if (Number.isNaN(value)) {
    return (
      <div className="flex h-full flex-col justify-center px-4">
        <span className="truncate text-2xl font-medium tracking-tight text-foreground">{String(rawValue ?? '—')}</span>
        <span className="mt-1 text-xs text-muted-foreground">{fieldLabel(valueFieldName)}</span>
      </div>
    );
  }
  if (multiply) value *= multiply;

  const format = (n: number) =>
    isCurrency ? `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : n.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const onTarget = target !== undefined ? (lower ? value <= target : value >= target) : null;
  const scale = target !== undefined ? Math.max(value, target) * 1.2 || 1 : 1;
  const unitWord = unit === '%' ? '%' : unit ? ` ${unit}` : '';

  return (
    <div className="flex h-full flex-col justify-center px-4 py-2">
      <p className={cn('flex items-baseline', unit === '%' ? 'gap-0.5' : 'gap-1.5')}>
        <AnimatedNumber value={value} format={format} className="num text-3xl font-medium tracking-tight text-foreground" />
        {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
      </p>
      {target !== undefined && (
        <div className="mt-3">
          <div className="relative h-1 rounded-full bg-surface-3">
            <div className={cn('grow-x absolute inset-y-0 left-0 rounded-full', onTarget ? 'bg-success' : 'bg-destructive')} style={{ width: `${Math.min(100, (value / scale) * 100)}%` }} />
            <span className="absolute -top-1 h-3 w-px bg-foreground/60" style={{ left: `${Math.min(100, (target / scale) * 100)}%` }} aria-hidden="true" />
          </div>
          <div className="mt-1.5 flex items-center justify-between gap-2 text-xs">
            <span className="truncate text-muted-foreground">Target {lower ? 'under' : 'over'} <span className="num text-foreground">{target}{unitWord}</span></span>
            <span className={cn('shrink-0 font-medium', onTarget ? 'text-success' : 'text-destructive')}>{onTarget ? 'On target' : 'Off target'}</span>
          </div>
        </div>
      )}
    </div>
  );
}
