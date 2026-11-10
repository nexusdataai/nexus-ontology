import { useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { ChartTooltip, seriesColor } from '@/components/ds/charts';
import { cn } from '@/lib/utils';
import { PanelState, fieldLabel, compactNumber } from '../_shared';

const MAX_SLICES = 5;
const OTHER_COLOR = 'hsl(var(--surface-3))';

/** Share of a whole: donut with the total in the middle and a legend with exact numbers. */
export function PieChartPanel({ data, options, width, height, loading }: PanelProps) {
  const [active, setActive] = useState<number | null>(null);
  if (loading || data.length === 0 || data[0].length === 0) return <PanelState loading={loading} />;

  const frame = data[0];
  const nameKey = (options.nameKey as string) || frame.fields[0]?.name || 'name';
  const valueKey = (options.valueKey as string) || (frame.fields.length > 1 ? frame.fields[1].name : 'value');

  const all = dataFrameToRows(frame)
    .map(r => ({ name: fieldLabel(r[nameKey] ?? 'Unknown'), value: Number(r[valueKey] ?? 0) }))
    .filter(r => Number.isFinite(r.value) && r.value > 0)
    .sort((a, b) => b.value - a.value);
  const fold = all.length > MAX_SLICES + 1;
  const head = fold ? all.slice(0, MAX_SLICES) : all;
  const tail = fold ? all.slice(MAX_SLICES) : [];
  const rows = tail.length ? [...head, { name: `Other (${tail.length})`, value: tail.reduce((s, r) => s + r.value, 0) }] : head;
  const total = rows.reduce((s, r) => s + r.value, 0);
  const colorAt = (i: number) => (tail.length && i === rows.length - 1 ? OTHER_COLOR : seriesColor(i));
  const shown = active !== null ? rows[active] : null;

  const side = width >= 420;
  const d = Math.max(96, Math.min(height - 24, side ? width * 0.42 : height - 110, 200));

  return (
    <div className={cn('flex h-full items-center gap-5 px-4 py-3', !side && 'flex-col justify-center gap-3')}>
      <div className="relative shrink-0" style={{ width: d, height: d }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={rows}
              dataKey="value"
              nameKey="name"
              innerRadius={d / 2 - 26}
              outerRadius={d / 2 - 4}
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
            <Tooltip content={<ChartTooltip hideLabel valueFormatter={(v) => `${compactNumber(Number(v))} · ${((Number(v) / (total || 1)) * 100).toFixed(0)}%`} />} wrapperStyle={{ zIndex: 20 }} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="num text-xl font-medium tracking-tight text-foreground">{compactNumber(shown ? shown.value : total)}</span>
          <span className="max-w-[60%] truncate text-xs text-muted-foreground">{shown ? shown.name : 'Total'}</span>
        </div>
      </div>

      <ul className={cn('min-w-0 space-y-0.5', side ? 'flex-1' : 'w-full')}>
        {rows.map((r, i) => (
          <li
            key={r.name}
            onMouseEnter={() => setActive(i)}
            onMouseLeave={() => setActive(null)}
            className={cn('flex items-center gap-2.5 rounded-md px-2 py-1 text-sm transition-colors', active === i && 'bg-surface-2')}
          >
            <span className="h-2.5 w-2.5 shrink-0 rounded-[3px]" style={{ background: colorAt(i) }} aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate text-foreground" title={r.name}>{r.name}</span>
            <span className="num w-10 text-right font-medium text-foreground">{((r.value / (total || 1)) * 100).toFixed(0)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
