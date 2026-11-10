import { ResponsiveContainer, ComposedChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from 'recharts';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { gridProps, axisProps, CHART_MARGIN, tooltipStyle } from '@/components/ds/charts';
import { PanelState } from '../_shared';

interface CandleData {
  label: string;
  open: number;
  high: number;
  low: number;
  close: number;
  range: [number, number];
  wick: [number, number];
  bullish: boolean;
}

export function CandlestickPanel({ data, options, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length < 4) {
    return (
      <PanelState loading={loading} text="No data (need open, high, low, close fields)" />
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const fieldNames = frame.fields.map((f) => f.name);

  const labelField = (options.labelField as string) || fieldNames.find((n) => /time|date|period|label/i.test(n)) || fieldNames[0];
  const openField = (options.openField as string) || fieldNames.find((n) => /open/i.test(n)) || fieldNames[1];
  const highField = (options.highField as string) || fieldNames.find((n) => /high/i.test(n)) || fieldNames[2];
  const lowField = (options.lowField as string) || fieldNames.find((n) => /low/i.test(n)) || fieldNames[3];
  const closeField = (options.closeField as string) || fieldNames.find((n) => /close/i.test(n)) || (fieldNames.length > 4 ? fieldNames[4] : fieldNames[3]);
  const colorUp = (options.colorUp as string) || 'hsl(var(--success))';
  const colorDown = (options.colorDown as string) || 'hsl(var(--destructive))';
  const chartHeight = Math.max(height - 40, 100);

  const candles: CandleData[] = rows.map((row) => {
    const o = Number(row[openField] ?? 0);
    const h = Number(row[highField] ?? 0);
    const l = Number(row[lowField] ?? 0);
    const c = Number(row[closeField] ?? 0);
    const bullish = c >= o;
    return {
      label: String(row[labelField] ?? ''),
      open: o,
      high: h,
      low: l,
      close: c,
      range: bullish ? [o, c] : [c, o],
      wick: [l, h],
      bullish,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <ComposedChart data={candles} margin={CHART_MARGIN}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey="label" {...axisProps} interval="preserveStartEnd" />
        <YAxis {...axisProps} width={50} domain={['auto', 'auto']} />
        <Tooltip
          {...tooltipStyle}
          formatter={(_: unknown, name: string, item: { payload?: CandleData }) => {
            const c = item.payload;
            if (!c) return '';
            if (name === 'wick') return [`${c.low} – ${c.high}`, 'H/L'];
            return [`${c.open} → ${c.close}`, 'O/C'];
          }}
        />
        <Bar dataKey="wick" fill="currentColor" fillOpacity={0.3} barSize={2}>
          {candles.map((c, i) => (
            <Cell key={i} fill={c.bullish ? colorUp : colorDown} fillOpacity={0.5} />
          ))}
        </Bar>
        <Bar dataKey="range" barSize={12}>
          {candles.map((c, i) => (
            <Cell key={i} fill={c.bullish ? colorUp : colorDown} />
          ))}
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  );
}
