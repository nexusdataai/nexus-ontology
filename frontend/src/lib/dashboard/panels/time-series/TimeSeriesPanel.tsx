import {
  ComposedChart,
  Line,
  Area,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { gridProps, axisProps, ChartTooltip, cursorLine, CHART_MARGIN, CHART_COLORS } from '@/components/ds/charts';
import { PanelState } from '../_shared';

const SERIES_COLORS = CHART_COLORS;

export function TimeSeriesPanel({ data, options, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length === 0) {
    return (
      <PanelState loading={loading} text="No data" />
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const xKey = (options.xKey as string) || frame.fields[0]?.name || 'time';
  const drawStyle = (options.drawStyle as string) || 'line';
  const fillOpacity = (options.fillOpacity as number) ?? (drawStyle === 'line' ? 0 : 0.3);
  const lineWidth = (options.lineWidth as number) ?? 2;
  const showPoints = (options.showPoints as boolean) ?? false;
  const stacking = (options.stacking as string) || 'none';
  const legendPosition = (options.legendPosition as string) || 'bottom';
  const showLegend = (options.showLegend as boolean) ?? true;
  const chartHeight = Math.max(height - 40, 100);

  const yFields = (options.yFields as string[]) ||
    frame.fields
      .filter((f) => f.name !== xKey && f.type === 'number')
      .map((f) => f.name);

  if (yFields.length === 0 && frame.fields.length > 1) {
    yFields.push(frame.fields[1].name);
  }

  const stackId = stacking !== 'none' ? 'stack' : undefined;

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <ComposedChart data={rows} margin={CHART_MARGIN}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey={xKey} {...axisProps} />
        <YAxis {...axisProps} width={45} />
        <Tooltip content={<ChartTooltip />} cursor={cursorLine} />
        {showLegend && (
          <Legend
            wrapperStyle={{ fontSize: 12, color: 'hsl(var(--muted-foreground))' }} iconType="square" iconSize={8}
            verticalAlign={legendPosition === 'bottom' ? 'bottom' : 'top'}
          />
        )}
        {yFields.map((field, i) => {
          const color = SERIES_COLORS[i % SERIES_COLORS.length];
          if (drawStyle === 'bars') {
            return (
              <Bar
                key={field}
                dataKey={field}
                fill={color}
                stackId={stackId}
                fillOpacity={0.8}
                radius={[2, 2, 0, 0]}
              />
            );
          }
          if (fillOpacity > 0) {
            return (
              <Area
                key={field}
                type="monotone"
                dataKey={field}
                stroke={color}
                fill={color}
                fillOpacity={fillOpacity}
                strokeWidth={lineWidth}
                stackId={stackId}
                dot={showPoints ? { r: 2 } : false}
              />
            );
          }
          return (
            <Line
              key={field}
              type="monotone"
              dataKey={field}
              stroke={color}
              strokeWidth={lineWidth}
              dot={showPoints ? { r: 2 } : false}
            />
          );
        })}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
