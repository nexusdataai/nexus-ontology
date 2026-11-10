import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { ChartTooltip, CHART_MARGIN, axisProps, gridProps, barProps, cursorBand, seriesColor } from '@/components/ds/charts';
import { PanelState, fieldLabel, compactNumber } from '../_shared';

/**
 * Categories as ranked horizontal bars (labels stay readable, values are
 * exact). Time-like x axes are drawn as columns.
 */
export function BarChartPanel({ data, options, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].length === 0) return <PanelState loading={loading} />;

  const frame = data[0];
  const xKey = (options.xKey as string) || frame.fields[0]?.name || 'name';
  const yKey = (options.yKey as string) || (frame.fields.length > 1 ? frame.fields[1].name : 'value');
  const rows = dataFrameToRows(frame).map(r => ({ name: String(r[xKey] ?? '—'), value: Number(r[yKey] ?? 0) }));
  const timeLike = /(date|day|week|month|quarter|year|period|time)/i.test(xKey);

  if (timeLike) {
    return (
      <div className="h-full p-3">
        <ResponsiveContainer width="100%" height={Math.max(height - 24, 100)}>
          <BarChart data={rows} margin={CHART_MARGIN}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="name" {...axisProps} />
            <YAxis {...axisProps} width={44} tickFormatter={(v) => compactNumber(Number(v), 0)} />
            <Tooltip content={<ChartTooltip valueFormatter={(v) => compactNumber(Number(v))} />} cursor={cursorBand} />
            <Bar dataKey="value" name={fieldLabel(yKey)} fill={seriesColor(0)} {...barProps} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  const rowH = 30;
  const fit = Math.max(3, Math.floor((height - 24) / rowH));
  const sorted = [...rows].sort((a, b) => b.value - a.value);
  const shown = sorted.slice(0, fit);
  const max = Math.max(...shown.map(r => r.value), 0) || 1;

  return (
    <ol className="flex h-full flex-col justify-center gap-2.5 px-4 py-3">
      {shown.map((r, i) => (
        <li key={`${r.name}-${i}`} className="group grid grid-cols-[minmax(0,32%)_minmax(0,1fr)_auto] items-center gap-3 text-sm">
          <span className="truncate text-muted-foreground transition-colors group-hover:text-foreground" title={r.name}>{r.name}</span>
          <span className="h-2 overflow-hidden rounded-full bg-surface-3">
            <span className="grow-x block h-full rounded-full bg-primary" style={{ width: `${Math.max(2, (r.value / max) * 100)}%`, opacity: i === 0 ? 1 : 0.72, ['--i' as any]: i }} />
          </span>
          <span className="num w-14 text-right font-medium text-foreground">{compactNumber(r.value)}</span>
        </li>
      ))}
    </ol>
  );
}
