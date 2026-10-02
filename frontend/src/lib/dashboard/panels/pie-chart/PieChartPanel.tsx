import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';

const DEFAULT_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b', '#ec4899', '#14b8a6'];

export function PieChartPanel({ data, options, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Loading...' : 'No data'}
      </div>
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const nameKey = (options.nameKey as string) || frame.fields[0]?.name || 'name';
  const valueKey = (options.valueKey as string) || (frame.fields.length > 1 ? frame.fields[1].name : 'value');
  const colorMap = (options.colors as Record<string, string>) || {};
  const chartHeight = Math.max(height - 40, 100);

  const chartData = rows.map((r) => ({
    name: String(r[nameKey] ?? 'unknown'),
    value: Number(r[valueKey] ?? 0),
  }));

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={Math.min(chartHeight / 3, 80)}
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          labelLine={false}
        >
          {chartData.map((entry, i) => (
            <Cell key={i} fill={colorMap[entry.name] || DEFAULT_COLORS[i % DEFAULT_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={{ fontSize: 11 }} />
        <Legend wrapperStyle={{ fontSize: 10 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
