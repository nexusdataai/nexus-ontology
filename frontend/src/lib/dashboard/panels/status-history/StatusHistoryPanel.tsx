import { useMemo } from 'react';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';
import { CHART_COLORS } from '@/components/ds/charts';
import { PanelState } from '../_shared';

const STATUS_COLORS: Record<string, string> = {
  ok: 'hsl(var(--success))', good: 'hsl(var(--success))', up: 'hsl(var(--success))', online: 'hsl(var(--success))', healthy: 'hsl(var(--success))', pass: 'hsl(var(--success))',
  warning: 'hsl(var(--warning))', degraded: 'hsl(var(--warning))', slow: 'hsl(var(--warning))', partial: 'hsl(var(--warning))',
  error: 'hsl(var(--destructive))', critical: 'hsl(var(--destructive))', down: 'hsl(var(--destructive))', fail: 'hsl(var(--destructive))', offline: 'hsl(var(--destructive))',
  unknown: 'hsl(var(--muted-foreground))', na: 'hsl(var(--muted-foreground))', pending: 'hsl(var(--muted-foreground))',
  maintenance: 'hsl(var(--chart-4))', info: 'hsl(var(--chart-1))',
};

const FALLBACK_COLORS = CHART_COLORS;

export function StatusHistoryPanel({ data, options, width, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length < 3) {
    return (
      <PanelState loading={loading} text="No data (need entity, time, status fields)" />
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const entityKey = (options.entityKey as string) || frame.fields[0]?.name || 'entity';
  const timeKey = (options.timeKey as string) || (frame.fields.length > 1 ? frame.fields[1].name : 'time');
  const statusKey = (options.statusKey as string) || (frame.fields.length > 2 ? frame.fields[2].name : 'status');
  const showValue = (options.showValue as boolean) ?? false;

  const { entities, timePeriods, grid } = useMemo(() => {
    const entitySet = new Set<string>();
    const timeSet = new Set<string>();
    const cellMap: Record<string, string> = {};

    for (const row of rows) {
      const entity = String(row[entityKey] ?? '');
      const time = String(row[timeKey] ?? '');
      const status = String(row[statusKey] ?? 'unknown');
      entitySet.add(entity);
      timeSet.add(time);
      cellMap[`${entity}|${time}`] = status;
    }

    const sortedTimes = Array.from(timeSet).sort();
    return { entities: Array.from(entitySet), timePeriods: sortedTimes, grid: cellMap };
  }, [rows, entityKey, timeKey, statusKey]);

  let colorIdx = 0;
  const colorCache: Record<string, string> = {};
  const getStatusColor = (status: string): string => {
    if (colorCache[status]) return colorCache[status];
    const lower = status.toLowerCase();
    if (STATUS_COLORS[lower]) {
      colorCache[status] = STATUS_COLORS[lower];
      return STATUS_COLORS[lower];
    }
    const c = FALLBACK_COLORS[colorIdx % FALLBACK_COLORS.length];
    colorIdx++;
    colorCache[status] = c;
    return c;
  };

  const labelWidth = 80;
  const cellSize = Math.max(Math.min((width - labelWidth - 32) / timePeriods.length - 1, 32), 8);
  const rowH = Math.max(Math.min((height - 40) / entities.length - 2, 28), 12);

  return (
    <div className="h-full overflow-auto p-2">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-1" style={{ paddingLeft: labelWidth + 8 }}>
          {timePeriods.map((t, i) => (
            <div
              key={i}
              className="text-xs text-muted-foreground text-center truncate"
              style={{ width: cellSize }}
            >
              {t.length > 5 ? t.slice(-5) : t}
            </div>
          ))}
        </div>
        {entities.map((entity) => (
          <div key={entity} className="flex items-center gap-1">
            <span
              className="text-xs text-muted-foreground truncate text-right flex-shrink-0"
              style={{ width: labelWidth }}
            >
              {entity}
            </span>
            <div className="flex gap-[1px]">
              {timePeriods.map((time, ti) => {
                const status = grid[`${entity}|${time}`] || 'unknown';
                const color = getStatusColor(status);
                return (
                  <div
                    key={ti}
                    className="rounded-[2px] flex items-center justify-center"
                    style={{ width: cellSize, height: rowH, backgroundColor: color }}
                    title={`${entity} @ ${time}: ${status}`}
                  >
                    {showValue && cellSize >= 16 && (
                      <span className="text-[7px] text-white font-medium truncate drop-shadow-sm">
                        {status.slice(0, 3)}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
