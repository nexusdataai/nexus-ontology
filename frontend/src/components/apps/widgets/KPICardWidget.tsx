import { Skeleton } from '@/components/ui/skeleton';
import { AnimatedNumber } from '@/components/ds/AnimatedNumber';
import { cn } from '@/lib/utils';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

/**
 * One headline number with its target. Rendered as a cell of the KPI strip
 * (see DashboardRenderer), so it has no border of its own.
 */
export function KPICardWidget({ widget, data, loading }: Props) {
  const { config } = widget;

  if (loading) {
    return (
      <div className="h-full bg-card p-5" aria-busy="true">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="mt-3 h-8 w-24" />
        <Skeleton className="mt-4 h-1 w-full" />
      </div>
    );
  }

  let value: number | null = null;
  if (!config.placeholder && data?.rows?.length > 0) {
    const col = widget.query.columns?.[0];
    const rows: any[] = data.rows;
    const agg = String(widget.query.aggregation || '').toLowerCase();
    // The query endpoint can return the plain rows instead of one aggregated
    // row. When it does, work the figure out here so a count is a count and
    // an average is an average, not the first row.
    const aggregated = rows.length === 1 && col !== undefined && typeof rows[0][col] === 'number';
    let parsed = NaN;
    if (agg && !aggregated && col) {
      if (agg === 'count') {
        parsed = typeof data.total === 'number' && data.total > rows.length ? data.total : rows.length;
      } else {
        const nums = rows.map(r => (typeof r[col] === 'number' ? r[col] : parseFloat(r[col]))).filter(n => !Number.isNaN(n));
        if (nums.length > 0) {
          const sum = nums.reduce((x, y) => x + y, 0);
          parsed = agg === 'sum' ? sum : agg === 'min' ? Math.min(...nums) : agg === 'max' ? Math.max(...nums) : sum / nums.length;
        }
      }
    } else {
      const raw = col ? rows[0][col] : undefined;
      parsed = typeof raw === 'number' ? raw : parseFloat(raw);
    }
    if (!Number.isNaN(parsed)) value = parsed * ((config.multiply as number) || 1);
  }

  const isCurrency = config.format === 'currency';
  const unit = isCurrency ? '' : String(config.unit || '');
  const format = (n: number) =>
    isCurrency || String(widget.query.aggregation || '').toLowerCase() === 'count'
      ? `${isCurrency ? '$' : ''}${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
      : n.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  const target = config.target as number | undefined;
  const lower = config.direction === 'lower';
  const hasTarget = target !== undefined && value !== null;
  const onTarget = hasTarget ? (lower ? value! <= target! : value! >= target!) : null;
  const scale = hasTarget ? Math.max(value!, target!) * 1.2 || 1 : 1;
  const valuePct = hasTarget ? Math.min(100, (value! / scale) * 100) : 0;
  const targetPct = hasTarget ? Math.min(100, (target! / scale) * 100) : 0;
  const unitWord = unit === '%' ? '%' : unit ? ` ${unit}` : '';

  return (
    <div className="flex h-full flex-col bg-card p-5">
      <p className="truncate text-sm text-muted-foreground">{widget.title}</p>
      <p className={cn('mt-2 flex items-baseline', unit === '%' ? 'gap-0.5' : 'gap-1.5')}>
        <AnimatedNumber value={value} format={format} className="num text-3xl font-medium tracking-tight text-foreground" />
        {unit && value !== null && <span className="text-sm text-muted-foreground">{unit}</span>}
      </p>

      {target !== undefined ? (
        <div className="mt-auto pt-4">
          <div className="relative h-1 rounded-full bg-surface-3" role="img" aria-label={`${widget.title}: ${value ?? 'no value'}, target ${target}${unitWord}`}>
            {hasTarget && (
              <>
                <div
                  className={cn('grow-x absolute inset-y-0 left-0 rounded-full', onTarget ? 'bg-success' : 'bg-destructive')}
                  style={{ width: `${valuePct}%` }}
                />
                <span className="absolute -top-1 h-3 w-px bg-foreground/60" style={{ left: `${targetPct}%` }} aria-hidden="true" />
              </>
            )}
          </div>
          <div className="mt-2 flex items-center justify-between gap-2 text-xs">
            <span className="text-muted-foreground">
              Target {lower ? 'under' : 'over'} <span className="num text-foreground">{target}{unitWord}</span>
            </span>
            {onTarget !== null && (
              <span className={cn('font-medium', onTarget ? 'text-success' : 'text-destructive')}>{onTarget ? 'On target' : 'Off target'}</span>
            )}
          </div>
        </div>
      ) : (
        <p className="mt-auto pt-4 text-xs text-muted-foreground">{value === null ? 'Waiting for the first run' : 'Latest snapshot'}</p>
      )}
    </div>
  );
}
