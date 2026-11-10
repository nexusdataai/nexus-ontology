import { useId } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { AreaFill, gridProps, axisProps, lineProps, ChartTooltip, cursorLine, CHART_MARGIN, seriesColor } from '@/components/ds/charts';
import { PanelState, fieldLabel, compactNumber } from '../_shared';

export function LineChartPanel({ data, options, height, loading }: PanelProps) {
  const gid = useId().replace(/:/g, '');
  if (loading || data.length === 0 || data[0].length === 0) return <PanelState loading={loading} />;

  const frame = data[0];
  const xKey = (options.xKey as string) || frame.fields[0]?.name || 'name';
  const yKey = (options.yKey as string) || (frame.fields.length > 1 ? frame.fields[1].name : 'value');
  const rows = dataFrameToRows(frame).map(r => ({ ...r, [yKey]: Number(r[yKey] ?? 0) }));

  return (
    <div className="h-full px-3 pb-3 pt-1">
      <ResponsiveContainer width="100%" height={Math.max(height - 16, 100)}>
        <AreaChart data={rows} margin={CHART_MARGIN}>
          <defs><AreaFill id={gid} color={seriesColor(0)} /></defs>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey={xKey} {...axisProps} />
          <YAxis {...axisProps} width={44} tickFormatter={(v) => compactNumber(Number(v), 0)} />
          <Tooltip content={<ChartTooltip valueFormatter={(v) => compactNumber(Number(v))} />} cursor={cursorLine} />
          <Area dataKey={yKey} name={fieldLabel(yKey)} stroke={seriesColor(0)} fill={`url(#${gid})`} {...lineProps} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
