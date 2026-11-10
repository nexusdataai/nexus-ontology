import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { DashboardWidget } from '@/config/dashboardWidgets';
import { ChartTooltip, CHART_MARGIN, axisProps, gridProps, barProps, cursorBand, seriesColor } from '@/components/ds/charts';
import { WidgetFrame, labelOf, compact } from './WidgetFrame';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

const MAX_RANKED = 8;

/**
 * Categories are shown as a ranked list of horizontal bars (readable labels,
 * exact values). Long series fall back to a column chart.
 */
export function BarChartWidget({ widget, data, loading }: Props) {
  const { config } = widget;
  const xKey = (config.xKey as string) || 'name';
  const yKey = (config.yKey as string) || 'value';

  const rows: { name: string; value: number }[] = (data?.rows ?? [])
    .map((r: any) => ({ name: String(r[xKey] ?? '—'), value: Number(r[yKey] ?? 0) }))
    .filter((r: { value: number }) => Number.isFinite(r.value));

  const ranked = !/(date|day|week|month|quarter|year|period|time)/i.test(xKey);
  const sorted = ranked ? [...rows].sort((a, b) => b.value - a.value).slice(0, MAX_RANKED) : rows;
  const max = Math.max(...sorted.map(r => r.value), 0) || 1;

  return (
    <WidgetFrame
      title={widget.title}
      description={`${labelOf(yKey)} by ${labelOf(xKey).toLowerCase()}`}
      aside={rows.length > 0 ? <span className="text-xs text-muted-foreground">{ranked && rows.length > MAX_RANKED ? `Top ${MAX_RANKED} of ${rows.length}` : `${rows.length} items`}</span> : null}
      loading={loading}
      empty={rows.length === 0}
    >
      {ranked ? (
        <ol className="space-y-3">
          {sorted.map((r, i) => (
            <li key={`${r.name}-${i}`} className="group grid grid-cols-[minmax(0,34%)_minmax(0,1fr)_auto] items-center gap-3 text-sm">
              <span className="truncate text-muted-foreground transition-colors group-hover:text-foreground" title={r.name}>{r.name}</span>
              <span className="h-2 overflow-hidden rounded-full bg-surface-3">
                <span
                  className="grow-x block h-full rounded-full bg-primary transition-opacity group-hover:opacity-100"
                  style={{ width: `${Math.max(2, (r.value / max) * 100)}%`, opacity: i === 0 ? 1 : 0.72, ['--i' as any]: i }}
                />
              </span>
              <span className="num w-14 text-right font-medium text-foreground">{compact(r.value)}</span>
            </li>
          ))}
        </ol>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={sorted} margin={CHART_MARGIN}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="name" {...axisProps} />
            <YAxis {...axisProps} width={44} tickFormatter={(v) => compact(Number(v), 0)} />
            <Tooltip content={<ChartTooltip valueFormatter={(v) => compact(Number(v))} />} cursor={cursorBand} />
            <Bar dataKey="value" name={labelOf(yKey)} fill={seriesColor(0)} {...barProps} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </WidgetFrame>
  );
}
