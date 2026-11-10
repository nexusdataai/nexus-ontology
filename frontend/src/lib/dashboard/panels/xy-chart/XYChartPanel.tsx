import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { gridProps, axisProps, ChartTooltip, cursorLine, CHART_MARGIN, CHART_COLORS } from '@/components/ds/charts';
import { PanelState } from '../_shared';

const SERIES_COLORS = CHART_COLORS;

export function XYChartPanel({ data, options, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length < 2) {
    return (
      <PanelState loading={loading} text="No data (need at least 2 numeric fields)" />
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const numericFields = frame.fields.filter((f) => f.type === 'number');
  const xField = (options.xField as string) || numericFields[0]?.name || frame.fields[0].name;
  const yField = (options.yField as string) || (numericFields.length > 1 ? numericFields[1].name : frame.fields[1].name);
  const sizeField = options.sizeField as string | undefined;
  const colorField = options.colorField as string | undefined;
  const pointSize = (options.pointSize as number) ?? 8;
  const color = (options.color as string) || 'hsl(var(--chart-1))';
  const chartHeight = Math.max(height - 40, 100);

  if (colorField) {
    const groups: Record<string, Array<Record<string, unknown>>> = {};
    for (const row of rows) {
      const key = String(row[colorField] ?? 'default');
      if (!groups[key]) groups[key] = [];
      groups[key].push(row);
    }

    const groupKeys = Object.keys(groups);

    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <ScatterChart margin={CHART_MARGIN}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey={xField} type="number" {...axisProps} name={xField} />
          <YAxis dataKey={yField} type="number" {...axisProps} width={45} name={yField} />
          {sizeField && <ZAxis dataKey={sizeField} range={[20, 400]} name={sizeField} />}
          <Tooltip content={<ChartTooltip />} cursor={cursorLine} />
          {groupKeys.map((key, i) => (
            <Scatter
              key={key}
              name={key}
              data={groups[key]}
              fill={SERIES_COLORS[i % SERIES_COLORS.length]}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <ScatterChart margin={CHART_MARGIN}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey={xField} type="number" {...axisProps} name={xField} />
        <YAxis dataKey={yField} type="number" {...axisProps} width={45} name={yField} />
        {sizeField && <ZAxis dataKey={sizeField} range={[20, 400]} name={sizeField} />}
        <Tooltip content={<ChartTooltip />} cursor={cursorLine} />
        <Scatter data={rows} fill={color} r={pointSize / 2} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
