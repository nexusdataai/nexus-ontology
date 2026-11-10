import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { PanelState } from '../_shared';

const DEFAULT_THRESHOLDS = [
  { value: 0, color: 'hsl(var(--success))' },
  { value: 70, color: 'hsl(var(--warning))' },
  { value: 90, color: 'hsl(var(--destructive))' },
];

export function BarGaugePanel({ data, options, width, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length === 0) {
    return (
      <PanelState loading={loading} text="No data" />
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const nameKey = (options.nameKey as string) || frame.fields[0]?.name || 'name';
  const valueKey = (options.valueKey as string) || (frame.fields.length > 1 ? frame.fields[1].name : 'value');
  const min = (options.min as number) ?? 0;
  const max = (options.max as number) ?? 100;
  const orientation = (options.orientation as string) || 'horizontal';
  const displayMode = (options.displayMode as string) || 'gradient';
  const showUnfilled = (options.showUnfilled as boolean) ?? true;
  const thresholds = (options.thresholds as Array<{ value: number; color: string }>) || DEFAULT_THRESHOLDS;

  const items = rows.map((r) => ({
    name: String(r[nameKey] ?? ''),
    value: Number(r[valueKey] ?? 0),
  }));

  const getColor = (value: number): string => {
    let color = thresholds[0]?.color || 'hsl(var(--success))';
    for (const t of thresholds) {
      if (value >= t.value) color = t.color;
    }
    return color;
  };

  const isVertical = orientation === 'vertical';

  if (isVertical) {
    const barWidth = Math.max(Math.min((width - 40) / items.length - 8, 48), 16);
    return (
      <div className="flex items-end justify-center gap-2 h-full px-4 pb-6 pt-2 overflow-x-auto">
        {items.map((item, i) => {
          const pct = Math.min(Math.max((item.value - min) / (max - min), 0), 1);
          const color = getColor(item.value);
          const barHeight = Math.max((height - 60) * pct, 2);
          return (
            <div key={i} className="flex flex-col items-center gap-1" style={{ width: barWidth }}>
              <span className="text-xs font-medium tabular-nums">{item.value.toFixed(1)}</span>
              <div
                className="relative rounded-t-sm w-full"
                style={{ height: height - 60 }}
              >
                {showUnfilled && (
                  <div className="absolute inset-0 rounded-t-sm bg-muted/30" />
                )}
                <div
                  className="absolute bottom-0 left-0 right-0 rounded-t-sm transition-all"
                  style={{
                    height: barHeight,
                    background: displayMode === 'gradient'
                      ? `linear-gradient(to top, color-mix(in srgb, ${color} 80%, transparent), ${color})`
                      : color,
                  }}
                />
              </div>
              <span className="text-xs text-muted-foreground truncate w-full text-center">
                {item.name}
              </span>
            </div>
          );
        })}
      </div>
    );
  }

  const barHeight = Math.max(Math.min((height - 20) / items.length - 8, 32), 12);

  return (
    <div className="flex flex-col gap-1.5 px-4 py-2 h-full overflow-y-auto">
      {items.map((item, i) => {
        const pct = Math.min(Math.max((item.value - min) / (max - min), 0), 1);
        const color = getColor(item.value);
        return (
          <div key={i} className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground w-20 truncate text-right flex-shrink-0">
              {item.name}
            </span>
            <div
              className="relative flex-1 rounded-sm overflow-hidden"
              style={{ height: barHeight }}
            >
              {showUnfilled && (
                <div className="absolute inset-0 bg-muted/30 rounded-sm" />
              )}
              <div
                className="absolute inset-y-0 left-0 rounded-sm transition-all"
                style={{
                  width: `${pct * 100}%`,
                  background: displayMode === 'gradient'
                    ? `linear-gradient(to right, color-mix(in srgb, ${color} 80%, transparent), ${color})`
                    : displayMode === 'lcd'
                      ? `repeating-linear-gradient(to right, ${color} 0px, ${color} 4px, transparent 4px, transparent 6px)`
                      : color,
                }}
              />
            </div>
            <span className="text-xs font-medium tabular-nums w-12 flex-shrink-0">
              {item.value.toFixed(1)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
