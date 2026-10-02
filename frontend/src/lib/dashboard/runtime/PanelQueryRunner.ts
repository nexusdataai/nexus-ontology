import type { PanelQuery, PanelData, TimeRange, DataFrame } from '../types';
import { getVDLDataSource } from '../datasources/vdl-datasource';

export class PanelQueryRunner {
  private _lastData: PanelData = { state: 'idle', frames: [] };
  private _subscribers: Set<(data: PanelData) => void> = new Set();
  private _refreshTimer: ReturnType<typeof setInterval> | null = null;

  subscribe(callback: (data: PanelData) => void): () => void {
    this._subscribers.add(callback);
    callback(this._lastData);
    return () => {
      this._subscribers.delete(callback);
    };
  }

  private emit(data: PanelData) {
    this._lastData = data;
    for (const cb of this._subscribers) {
      cb(data);
    }
  }

  async run(targets: PanelQuery[], timeRange?: TimeRange): Promise<void> {
    const activeTargets = targets.filter((t) => !t.hide && t.entity);
    if (activeTargets.length === 0) {
      this.emit({ state: 'done', frames: [], timeRange });
      return;
    }

    this.emit({ state: 'loading', frames: this._lastData.frames, timeRange });

    try {
      const ds = getVDLDataSource();
      const response = await ds.query({ queries: activeTargets, timeRange });

      const frames: DataFrame[] = [];
      let error: string | undefined;

      for (const target of activeTargets) {
        const result = response.results[target.refId];
        if (result) {
          if (result.error) {
            error = error ? `${error}; ${result.error}` : result.error;
          }
          frames.push(...result.frames);
        }
      }

      this.emit({
        state: error ? 'error' : 'done',
        frames,
        error,
        timeRange,
      });
    } catch (err) {
      this.emit({
        state: 'error',
        frames: [],
        error: err instanceof Error ? err.message : 'Query execution failed',
        timeRange,
      });
    }
  }

  setRefreshInterval(intervalMs: number, targets: PanelQuery[], timeRange?: TimeRange) {
    this.clearRefreshInterval();
    if (intervalMs > 0) {
      this._refreshTimer = setInterval(() => {
        this.run(targets, timeRange);
      }, intervalMs);
    }
  }

  clearRefreshInterval() {
    if (this._refreshTimer) {
      clearInterval(this._refreshTimer);
      this._refreshTimer = null;
    }
  }

  getData(): PanelData {
    return this._lastData;
  }

  destroy() {
    this.clearRefreshInterval();
    this._subscribers.clear();
  }
}
