import { useMemo } from 'react';
import type { PanelProps } from '../types';
import { dataFrameToRows } from '../../types';

const STATE_COLORS: Record<string, string> = {
  ok: '#22c55e',
  good: '#22c55e',
  running: '#22c55e',
  active: '#22c55e',
  up: '#22c55e',
  online: '#22c55e',
  healthy: '#22c55e',
  warning: '#f59e0b',
  degraded: '#f59e0b',
  slow: '#f59e0b',
  pending: '#f59e0b',
  error: '#ef4444',
  critical: '#ef4444',
  down: '#ef4444',
  offline: '#ef4444',
  failed: '#ef4444',
  stopped: '#ef4444',
  idle: '#64748b',
  unknown: '#64748b',
  maintenance: '#8b5cf6',
};

const FALLBACK_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#64748b'];

export function StateTimelinePanel({ data, options, width, height, loading }: PanelProps) {
  if (loading || data.length === 0 || data[0].fields.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Loading...' : 'No data'}
      </div>
    );
  }

  const frame = data[0];
  const rows = dataFrameToRows(frame);
  const entityKey = (options.entityKey as string) || frame.fields[0]?.name || 'entity';
  const timeKey = (options.timeKey as string) || (frame.fields.length > 1 ? frame.fields[1].name : 'time');
  const stateKey = (options.stateKey as string) || (frame.fields.length > 2 ? frame.fields[2].name : 'state');
  const rowHeight = (options.rowHeight as number) ?? 28;
  const showValue = (options.showValue as string) || 'auto';
  const colorMap = (options.colorMap as Record<string, string>) || {};

  const { entities, timeRange, segments } = useMemo(() => {
    const entitySet = new Set<string>();
    const segMap: Record<string, Array<{ time: number; state: string }>> = {};
    let tMin = Infinity;
    let tMax = -Infinity;

    for (const row of rows) {
      const entity = String(row[entityKey] ?? '');
      const time = new Date(row[timeKey] as string).getTime();
      const state = String(row[stateKey] ?? 'unknown');
      entitySet.add(entity);
      if (!segMap[entity]) segMap[entity] = [];
      segMap[entity].push({ time, state });
      if (time < tMin) tMin = time;
      if (time > tMax) tMax = time;
    }

    for (const k of Object.keys(segMap)) {
      segMap[k].sort((a, b) => a.time - b.time);
    }

    return {
      entities: Array.from(entitySet),
      timeRange: { min: tMin, max: tMax },
      segments: segMap,
    };
  }, [rows, entityKey, timeKey, stateKey]);

  if (entities.length === 0 || timeRange.min === Infinity) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        No timeline data
      </div>
    );
  }

  const labelWidth = 80;
  const barAreaWidth = width - labelWidth - 32;
  const totalDuration = timeRange.max - timeRange.min || 1;
  let colorIdx = 0;
  const stateColorCache: Record<string, string> = {};

  const getStateColor = (state: string): string => {
    if (colorMap[state]) return colorMap[state];
    if (stateColorCache[state]) return stateColorCache[state];
    const lower = state.toLowerCase();
    if (STATE_COLORS[lower]) {
      stateColorCache[state] = STATE_COLORS[lower];
      return STATE_COLORS[lower];
    }
    const c = FALLBACK_COLORS[colorIdx % FALLBACK_COLORS.length];
    colorIdx++;
    stateColorCache[state] = c;
    return c;
  };

  return (
    <div className="h-full overflow-auto px-3 py-2">
      {entities.map((entity) => {
        const segs = segments[entity] || [];
        return (
          <div key={entity} className="flex items-center gap-2 mb-1" style={{ height: rowHeight }}>
            <span
              className="text-[10px] text-muted-foreground truncate flex-shrink-0 text-right"
              style={{ width: labelWidth }}
            >
              {entity}
            </span>
            <div className="flex-1 relative rounded-sm overflow-hidden bg-muted/20" style={{ height: rowHeight - 4 }}>
              {segs.map((seg, i) => {
                const nextTime = i < segs.length - 1 ? segs[i + 1].time : timeRange.max;
                const left = ((seg.time - timeRange.min) / totalDuration) * 100;
                const w = ((nextTime - seg.time) / totalDuration) * 100;
                const color = getStateColor(seg.state);
                const showLabel = showValue === 'always' || (showValue === 'auto' && w > 8);
                return (
                  <div
                    key={i}
                    className="absolute inset-y-0 flex items-center justify-center"
                    style={{ left: `${left}%`, width: `${Math.max(w, 0.5)}%`, backgroundColor: color }}
                    title={`${entity}: ${seg.state}`}
                  >
                    {showLabel && (
                      <span className="text-[8px] text-white font-medium truncate px-0.5 drop-shadow-sm">
                        {seg.state}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
