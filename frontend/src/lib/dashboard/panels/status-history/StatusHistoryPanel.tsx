import { useMemo } from 'react';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';

const STATUS_COLORS: Record<string, string> = {
  ok: '#22c55e', good: '#22c55e', up: '#22c55e', online: '#22c55e', healthy: '#22c55e', pass: '#22c55e',
  warning: '#f59e0b', degraded: '#f59e0b', slow: '#f59e0b', partial: '#f59e0b',
  error: '#ef4444', critical: '#ef4444', down: '#ef4444', fail: '#ef4444', offline: '#ef4444',
  unknown: '#64748b', na: '#64748b', pending: '#64748b',
  maintenance: '#8b5cf6', info: '#3b82f6',
};

const FALLBACK_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#64748b'];

export function StatusHistoryPanel({ data, options, width, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length < 3) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Loading...' : 'No data (need entity, time, status fields)'}
      </div>
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
              className="text-[8px] text-muted-foreground text-center truncate"
              style={{ width: cellSize }}
            >
              {t.length > 5 ? t.slice(-5) : t}
            </div>
          ))}
        </div>
        {entities.map((entity) => (
          <div key={entity} className="flex items-center gap-1">
            <span
              className="text-[10px] text-muted-foreground truncate text-right flex-shrink-0"
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
