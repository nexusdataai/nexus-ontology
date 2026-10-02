import { useMemo } from 'react';
import { Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';

const COLOR_SCHEMES: Record<string, string[]> = {
  blues: ['#1e3a5f', '#1e5090', '#2563eb', '#60a5fa', '#bfdbfe'],
  greens: ['#14532d', '#166534', '#22c55e', '#86efac', '#dcfce7'],
  reds: ['#7f1d1d', '#991b1b', '#ef4444', '#fca5a5', '#fee2e2'],
  spectral: ['#2563eb', '#22c55e', '#f59e0b', '#ef4444', '#7c3aed'],
};

export function HeatmapPanel({ data, options, width, height, loading }: PanelProps) {
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
  const yKey = (options.yKey as string) || (frame.fields.length > 1 ? frame.fields[1].name : 'y');
  const valueKey = (options.valueKey as string) || (frame.fields.length > 2 ? frame.fields[2].name : 'value');
  const colorScheme = (options.colorScheme as string) || 'blues';
  const cellGap = (options.cellGap as number) ?? 1;
  const showTooltip = (options.showTooltip as boolean) ?? true;

  const { grid, xLabels, yLabels, minVal, maxVal } = useMemo(() => {
    const xSet = new Set<string>();
    const ySet = new Set<string>();
    const map: Record<string, number> = {};
    let mn = Infinity;
    let mx = -Infinity;

    for (const row of rows) {
      const x = String(row[xKey] ?? '');
      const y = String(row[yKey] ?? '');
      const v = Number(row[valueKey] ?? 0);
      xSet.add(x);
      ySet.add(y);
      map[`${x}|${y}`] = v;
      if (v < mn) mn = v;
      if (v > mx) mx = v;
    }

    return {
      grid: map,
      xLabels: Array.from(xSet),
      yLabels: Array.from(ySet),
      minVal: mn === Infinity ? 0 : mn,
      maxVal: mx === -Infinity ? 1 : mx,
    };
  }, [rows, xKey, yKey, valueKey]);

  const colors = COLOR_SCHEMES[colorScheme] || COLOR_SCHEMES.blues;
  const labelMarginX = 60;
  const labelMarginY = 24;
  const availW = width - labelMarginX - 20;
  const availH = height - labelMarginY - 40;
  const cellW = xLabels.length > 0 ? Math.max(availW / xLabels.length - cellGap, 4) : 20;
  const cellH = yLabels.length > 0 ? Math.max(availH / yLabels.length - cellGap, 4) : 20;

  const getColor = (value: number): string => {
    if (maxVal === minVal) return colors[Math.floor(colors.length / 2)];
    const pct = (value - minVal) / (maxVal - minVal);
    const idx = Math.min(Math.floor(pct * colors.length), colors.length - 1);
    return colors[colors.length - 1 - idx];
  };

  return (
    <div className="relative h-full w-full overflow-auto p-2">
      <svg
        width={labelMarginX + xLabels.length * (cellW + cellGap)}
        height={labelMarginY + yLabels.length * (cellH + cellGap) + 20}
      >
        {yLabels.map((yLabel, yi) => (
          <text
            key={`yl-${yi}`}
            x={labelMarginX - 4}
            y={labelMarginY + yi * (cellH + cellGap) + cellH / 2}
            textAnchor="end"
            dominantBaseline="central"
            className="fill-muted-foreground"
            fontSize={9}
          >
            {yLabel.length > 8 ? yLabel.slice(0, 8) + '…' : yLabel}
          </text>
        ))}

        {xLabels.map((xLabel, xi) => (
          <text
            key={`xl-${xi}`}
            x={labelMarginX + xi * (cellW + cellGap) + cellW / 2}
            y={labelMarginY + yLabels.length * (cellH + cellGap) + 12}
            textAnchor="middle"
            className="fill-muted-foreground"
            fontSize={9}
          >
            {xLabel.length > 6 ? xLabel.slice(0, 6) + '…' : xLabel}
          </text>
        ))}

        {xLabels.map((xLabel, xi) =>
          yLabels.map((yLabel, yi) => {
            const val = grid[`${xLabel}|${yLabel}`] ?? 0;
            return (
              <rect
                key={`${xi}-${yi}`}
                x={labelMarginX + xi * (cellW + cellGap)}
                y={labelMarginY + yi * (cellH + cellGap)}
                width={cellW}
                height={cellH}
                fill={getColor(val)}
                rx={1}
              >
                {showTooltip && (
                  <title>{`${xLabel}, ${yLabel}: ${val.toFixed(2)}`}</title>
                )}
              </rect>
            );
          }),
        )}
      </svg>
    </div>
  );
}
