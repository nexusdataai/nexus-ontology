import { useEffect, useRef, useState, useCallback } from 'react';
import type { PanelQuery, PanelData, TimeRange } from '../types';
import { PanelQueryRunner } from './PanelQueryRunner';

export function useQueryRunner(
  targets: PanelQuery[],
  timeRange?: TimeRange,
  refreshIntervalMs?: number,
) {
  const runnerRef = useRef<PanelQueryRunner | null>(null);
  const [panelData, setPanelData] = useState<PanelData>({ state: 'idle', frames: [] });

  if (!runnerRef.current) {
    runnerRef.current = new PanelQueryRunner();
  }

  useEffect(() => {
    const runner = runnerRef.current!;
    const unsub = runner.subscribe(setPanelData);
    return unsub;
  }, []);

  useEffect(() => {
    const runner = runnerRef.current!;
    const hasQueries = targets.some((t) => !t.hide && t.entity);
    if (hasQueries) {
      runner.run(targets, timeRange);
    } else {
      setPanelData({ state: 'done', frames: [], timeRange });
    }
  }, [targets, timeRange]);

  useEffect(() => {
    const runner = runnerRef.current!;
    if (refreshIntervalMs && refreshIntervalMs > 0) {
      runner.setRefreshInterval(refreshIntervalMs, targets, timeRange);
    } else {
      runner.clearRefreshInterval();
    }
    return () => runner.clearRefreshInterval();
  }, [refreshIntervalMs, targets, timeRange]);

  useEffect(() => {
    return () => {
      runnerRef.current?.destroy();
    };
  }, []);

  const runQuery = useCallback(() => {
    runnerRef.current?.run(targets, timeRange);
  }, [targets, timeRange]);

  return { panelData, runQuery };
}
