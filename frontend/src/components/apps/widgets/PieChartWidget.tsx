import { useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import type { DashboardWidget } from '@/config/dashboardWidgets';
import { ChartTooltip, seriesColor } from '@/components/ds/charts';
import { cn } from '@/lib/utils';
import { WidgetFrame, labelOf, compact } from './WidgetFrame';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

const MAX_SLICES = 5;
const OTHER_COLOR = 'hsl(var(--surface-3))';

/**
 * Share of a whole as a donut with the total in the middle and a legend that
 * carries the exact numbers. More than five categories fold into "Other".
 */
export function PieChartWidget({ widget, data, loading }: Props) {
  const { query } = widget;
  const groupBy = query.groupBy || query.columns?.[0] || 'name';
  const valueKey = query.columns?.[1] || 'value';
  const [active, setActive] = useState<number | null>(null);

  const all: { name: string; value: number }[] = (data?.rows ?? [])
    .map((r: any) => ({ name: labelOf(r[groupBy] || r.name || 'Unknown'), value: Number(r[valueKey] ?? r.value ?? 0) }))
    .filter((r: { value: number }) => Number.isFinite(r.value) && r.value > 0)
    .sort((a: { value: number }, b: { value: number }) => b.value - a.value);

  const fold = all.length > MAX_SLICES + 1;
  const head = fold ? all.slice(0, MAX_SLICES) : all;
  const tail = fold ? all.slice(MAX_SLICES) : [];
  const rows = tail.length ? [...head, { name: `Other (${tail.length})`, value: tail.reduce((s, r) => s + r.value, 0) }] : head;
  const total = rows.reduce((s, r) => s + r.value, 0);
  const colorAt = (i: number) => (tail.length && i === rows.length - 1 ? OTHER_COLOR : seriesColor(i));
  const shown = active !== null ? rows[active] : null;

  return (
    <WidgetFrame title={widget.title} description={`Share by ${labelOf(groupBy).toLowerCase()}`} loading={loading} empty={rows.length === 0}>
      <div className="grid items-center gap-6 sm:grid-cols-[180px_minmax(0,1fr)]">
        <div className="relative mx-auto h-[180px] w-[180px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={rows}
                dataKey="value"
                nameKey="name"
                innerRadius={62}
                outerRadius={86}
                paddingAngle={rows.length > 1 ? 2 : 0}
                cornerRadius={3}
                startAngle={90}
                endAngle={-270}
                stroke="none"
                animationDuration={900}
                animationEasing="ease-out"
                onMouseEnter={(_, i) => setActive(i)}
                onMouseLeave={() => setActive(null)}
              >
                {rows.map((_, i) => (
                  <Cell key={i} fill={colorAt(i)} opacity={active === null || active === i ? 1 : 0.35} style={{ transition: 'opacity 160ms ease', outline: 'none' }} />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip hideLabel valueFormatter={(v) => `${compact(Number(v))} · ${((Number(v) / (total || 1)) * 100).toFixed(0)}%`} />} wrapperStyle={{ zIndex: 20 }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
            <span className="num text-2xl font-medium tracking-tight text-foreground">{compact(shown ? shown.value : total)}</span>
            <span className="max-w-[104px] truncate text-xs text-muted-foreground">{shown ? shown.name : 'Total'}</span>
          </div>
        </div>

        <ul className="min-w-0 space-y-1">
          {rows.map((r, i) => {
            const pct = (r.value / (total || 1)) * 100;
            return (
              <li
                key={r.name}
                onMouseEnter={() => setActive(i)}
                onMouseLeave={() => setActive(null)}
                className={cn('flex items-center gap-3 rounded-md px-2 py-1.5 text-sm transition-colors', active === i && 'bg-surface-2')}
              >
                <span className="h-2.5 w-2.5 shrink-0 rounded-[3px]" style={{ background: colorAt(i) }} aria-hidden="true" />
                <span className="min-w-0 flex-1 truncate text-foreground" title={r.name}>{r.name}</span>
                <span className="num text-muted-foreground">{compact(r.value)}</span>
                <span className="num w-10 text-right font-medium text-foreground">{pct.toFixed(0)}%</span>
              </li>
            );
          })}
        </ul>
      </div>
    </WidgetFrame>
  );
}
