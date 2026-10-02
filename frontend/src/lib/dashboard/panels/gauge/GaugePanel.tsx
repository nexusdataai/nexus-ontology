import type { PanelProps } from '../types';

export function GaugePanel({ data, options, width, height, loading }: PanelProps) {
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
  const rawValue = Number(valueField?.values?.[0] ?? 0);
  const min = (options.min as number) ?? 0;
  const max = (options.max as number) ?? 100;
  const unit = (options.unit as string) || '';

  const thresholds = (options.thresholds as Array<{ value: number; color: string }>) || [
    { value: 0, color: '#22c55e' },
    { value: 70, color: '#f59e0b' },
    { value: 90, color: '#ef4444' },
  ];

  const pct = Math.min(Math.max((rawValue - min) / (max - min), 0), 1);
  let color = thresholds[0]?.color || '#22c55e';
  for (const t of thresholds) {
    if (rawValue >= t.value) color = t.color;
  }

  const size = Math.min(width - 32, height - 40, 200);
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 10;
  const startAngle = Math.PI * 0.75;
  const endAngle = Math.PI * 2.25;
  const sweepAngle = endAngle - startAngle;

  const bgPath = describeArc(cx, cy, r, startAngle, endAngle);
  const valAngle = startAngle + sweepAngle * pct;
  const valPath = describeArc(cx, cy, r, startAngle, valAngle);

  return (
    <div className="flex flex-col items-center justify-center h-full">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <path d={bgPath} fill="none" stroke="currentColor" strokeWidth={8} opacity={0.1} strokeLinecap="round" />
        <path d={valPath} fill="none" stroke={color} strokeWidth={8} strokeLinecap="round" />
      </svg>
      <div className="text-center -mt-4">
        <span className="text-2xl font-bold">{rawValue.toFixed(1)}</span>
        {unit && <span className="text-sm text-muted-foreground ml-1">{unit}</span>}
      </div>
    </div>
  );
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number): string {
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
}
