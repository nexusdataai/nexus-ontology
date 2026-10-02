import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { PanelProps } from '../types';

export function HistogramPanel({ data, options, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Loading...' : 'No data'}
      </div>
    );
  }

  const frame = data[0];
  const valueFieldName = (options.valueField as string) || frame.fields[0]?.name;
  const valueField = frame.fields.find((f) => f.name === valueFieldName) ?? frame.fields[0];
  const values = valueField.values.map(Number).filter((v) => !isNaN(v));

  if (values.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        No numeric data
      </div>
    );
  }

  const bucketCount = (options.bucketCount as number) || 0;
  const color = (options.color as string) || '#3b82f6';
  const fillOpacity = (options.fillOpacity as number) ?? 0.8;
  const chartHeight = Math.max(height - 40, 100);

  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal;

  const numBuckets = bucketCount > 0
    ? bucketCount
    : Math.max(Math.min(Math.ceil(Math.sqrt(values.length)), 30), 5);

  const bucketSize = range > 0 ? range / numBuckets : 1;

  const buckets: { label: string; count: number; from: number; to: number }[] = [];
  for (let i = 0; i < numBuckets; i++) {
    const from = minVal + i * bucketSize;
    const to = from + bucketSize;
    buckets.push({
      label: `${from.toFixed(1)}`,
      count: 0,
      from,
      to,
    });
  }

  for (const v of values) {
    let idx = Math.floor((v - minVal) / bucketSize);
    if (idx >= numBuckets) idx = numBuckets - 1;
    if (idx < 0) idx = 0;
    buckets[idx].count++;
  }

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={buckets} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
        <XAxis dataKey="label" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 10 }} width={35} allowDecimals={false} />
        <Tooltip
          contentStyle={{ fontSize: 11 }}
          formatter={(value: number) => [value, 'Count']}
          labelFormatter={(label: string, payload: Array<{ payload?: { from?: number; to?: number } }>) => {
            const item = payload?.[0]?.payload;
            if (item) return `${item.from?.toFixed(2)} – ${item.to?.toFixed(2)}`;
            return label;
          }}
        />
        <Bar dataKey="count" fill={color} fillOpacity={fillOpacity} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
