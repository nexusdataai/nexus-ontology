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

const SERIES_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#64748b'];

export function TrendPanel({ data, options, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Loading...' : 'No data'}
      </div>
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const xKey = (options.xKey as string) || frame.fields[0]?.name || 'x';
  const drawStyle = (options.drawStyle as string) || 'line';
  const fillOpacity = (options.fillOpacity as number) ?? 0;
  const lineWidth = (options.lineWidth as number) ?? 2;
  const showPoints = (options.showPoints as boolean) ?? true;
  const showLegend = (options.showLegend as boolean) ?? true;
  const chartHeight = Math.max(height - 40, 100);

  const yFields = (options.yFields as string[]) ||
    frame.fields
      .filter((f) => f.name !== xKey && f.type === 'number')
      .map((f) => f.name);

  if (yFields.length === 0 && frame.fields.length > 1) {
    yFields.push(frame.fields[1].name);
  }

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <ComposedChart data={rows} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
        <XAxis dataKey={xKey} tick={{ fontSize: 9 }} />
        <YAxis tick={{ fontSize: 10 }} width={45} />
        <Tooltip contentStyle={{ fontSize: 11 }} />
        {showLegend && yFields.length > 1 && (
          <Legend wrapperStyle={{ fontSize: 10 }} />
        )}
        {yFields.map((field, i) => {
          const color = SERIES_COLORS[i % SERIES_COLORS.length];
          if (drawStyle === 'bars') {
            return (
              <Bar
                key={field}
                dataKey={field}
                fill={color}
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
              dot={showPoints ? { r: 3 } : false}
            />
          );
        })}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
