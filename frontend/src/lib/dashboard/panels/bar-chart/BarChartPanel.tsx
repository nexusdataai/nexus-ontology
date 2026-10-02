import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';

export function BarChartPanel({ data, options, width, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Loading...' : 'No data'}
      </div>
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const xKey = (options.xKey as string) || frame.fields[0]?.name || 'name';
  const yKey = (options.yKey as string) || (frame.fields.length > 1 ? frame.fields[1].name : 'value');
  const color = (options.color as string) || '#3b82f6';
  const chartHeight = Math.max(height - 40, 100);

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={rows} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
        <XAxis dataKey={xKey} tick={{ fontSize: 9 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 10 }} width={45} />
        <Tooltip contentStyle={{ fontSize: 11 }} />
        <Bar dataKey={yKey} fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
