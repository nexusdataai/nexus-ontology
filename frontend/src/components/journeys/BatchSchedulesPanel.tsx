import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';
import { Skeleton } from '../ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { InlineError, StatusPill } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { confirmDialog } from '@/components/ds/confirm';
import { cn } from '@/lib/utils';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';
import { BatchScheduleDialog } from './BatchScheduleDialog';

interface BatchSchedule {
  scheduleId: string;
  journeyId: string;
  stageId: string;
  intervalMinutes: number;
  enabled: boolean;
  timezone: string;
  lastRunAt: string | null;
  nextRunAt: string | null;
  lastJobId: string | null;
  lastJobStatus: string | null;
  createdAt: string;
  createdBy: string;
}

export interface BatchSchedulesPanelProps {
  journeyId?: string;
  journeyName?: string;
  onScheduleChanged?: () => void;
}

const INTERVAL_LABELS: Record<number, string> = {
  5: 'Every 5 min',
  10: 'Every 10 min',
  15: 'Every 15 min',
  30: 'Every 30 min',
  60: 'Every hour',
  360: 'Every 6 hours',
  1440: 'Daily',
};

function formatInterval(minutes: number): string {
  return INTERVAL_LABELS[minutes] || `Every ${minutes} min`;
}

function formatTime(iso: string | null): string {
  if (!iso) return 'Not yet';
  try {
    return new Date(iso).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '-';
  }
}

export function BatchSchedulesPanel({ journeyId, journeyName, onScheduleChanged }: BatchSchedulesPanelProps) {
  const [schedules, setSchedules] = useState<BatchSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editSchedule, setEditSchedule] = useState<BatchSchedule | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);
  const [runningNow, setRunningNow] = useState<string | null>(null);

  const loadSchedules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await callProcessingJourneyService.listSchedules(journeyId);
      if (res.success && res.data) {
        setSchedules(res.data as BatchSchedule[]);
      } else {
        setError(res.error?.message || 'Failed to load schedules');
      }
    } catch (e: any) {
      setError(e.message || 'Unexpected error');
    } finally {
      setLoading(false);
    }
  }, [journeyId]);

  useEffect(() => {
    loadSchedules();
  }, [loadSchedules]);

  const handleToggle = async (scheduleId: string) => {
    setToggling(scheduleId);
    try {
      await callProcessingJourneyService.toggleSchedule(scheduleId);
      await loadSchedules();
      onScheduleChanged?.();
    } catch {
      // silently fail, reload will show current state
    } finally {
      setToggling(null);
    }
  };

  const handleDelete = async (scheduleId: string) => {
    try {
      await callProcessingJourneyService.deleteSchedule(scheduleId);
      await loadSchedules();
      onScheduleChanged?.();
    } catch {
      // silently fail
    }
  };

  const handleRunNow = async (scheduleId: string) => {
    setRunningNow(scheduleId);
    try {
      await callProcessingJourneyService.runScheduleNow(scheduleId);
      await loadSchedules();
      onScheduleChanged?.();
    } catch {
      // silently fail
    } finally {
      setRunningNow(null);
    }
  };

  const active = schedules.filter(s => s.enabled).length;
  const failed = schedules.filter(s => s.lastJobStatus === 'failed').length;
  const pretty = (id: string) => String(id || '').replace(/[-_]+/g, ' ').replace(/^\w/, c => c.toUpperCase());
  const confirmDelete = async (s: BatchSchedule) => {
    const ok = await confirmDialog({ title: 'Delete this schedule?', description: `${pretty(s.journeyId)}, ${pretty(s.stageId)} will no longer run automatically.`, confirmLabel: 'Delete', destructive: true });
    if (ok) handleDelete(s.scheduleId);
  };

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-xl font-medium tracking-tight text-foreground">Scheduled jobs</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            {schedules.length === 0
              ? 'Journey stages that run on a timer. Add a schedule from a journey in AI Automation.'
              : <><span className="num font-medium text-foreground">{active}</span> of <span className="num font-medium text-foreground">{schedules.length}</span> schedules are on{failed > 0 && <>, <span className="num font-medium text-destructive">{failed}</span> failed on the last run</>}.</>}
          </p>
        </div>
        <Button variant="outline" onClick={loadSchedules} disabled={loading}>
          <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
        </Button>
      </header>

      {error && <InlineError onRetry={loadSchedules}>{error}</InlineError>}

      {loading && schedules.length === 0 ? (
        <div className="space-y-px overflow-hidden rounded-xl border border-border" aria-busy="true">
          {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-16 w-full rounded-none" />)}
        </div>
      ) : schedules.length === 0 && !error ? (
        <EmptyState icon="calendar" title="Nothing is scheduled" description="Open a journey in AI Automation and choose Schedule on a stage to run it automatically." />
      ) : schedules.length > 0 ? (
        <div className="scroll-thin overflow-x-auto rounded-xl border border-border bg-card shadow-xs">
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <thead>
              <tr>
                {['On', 'Journey and stage', 'Runs', 'Last run', 'Next run', ''].map((h, i) => (
                  <th key={i} scope="col" className="whitespace-nowrap border-b border-border bg-surface-2 px-5 py-2.5 text-left text-xs font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {schedules.map((s) => (
                <tr key={s.scheduleId} className={cn('group border-b border-border transition-colors last:border-b-0 hover:bg-surface-2/60', !s.enabled && 'text-muted-foreground')}>
                  <td className="w-16 px-5 py-3">
                    <Switch checked={s.enabled} onCheckedChange={() => handleToggle(s.scheduleId)} disabled={toggling === s.scheduleId} aria-label={s.enabled ? 'Pause this schedule' : 'Turn this schedule on'} />
                  </td>
                  <td className="px-5 py-3">
                    <div className={cn('font-medium', s.enabled ? 'text-foreground' : 'text-muted-foreground')}>{pretty(s.journeyId)}</div>
                    <div className="text-xs text-muted-foreground">{pretty(s.stageId)}</div>
                  </td>
                  <td className="whitespace-nowrap px-5 py-3">{formatInterval(s.intervalMinutes)}</td>
                  <td className="whitespace-nowrap px-5 py-3">
                    <div className="text-xs text-muted-foreground">{formatTime(s.lastRunAt)}</div>
                    {s.lastJobStatus && <StatusPill status={s.lastJobStatus} className="mt-0.5" />}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-xs">
                    {s.enabled ? <span className="text-foreground">{formatTime(s.nextRunAt)}</span> : 'Paused'}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="outline" size="sm" onClick={() => handleRunNow(s.scheduleId)} disabled={runningNow === s.scheduleId}>
                        <Icon name={runningNow === s.scheduleId ? 'spinner' : 'play'} className={cn('h-3 w-3', runningNow === s.scheduleId && 'animate-spin')} /> Run now
                      </Button>
                      <Button variant="ghost" size="sm" aria-label="Edit schedule" title="Edit schedule" onClick={() => { setEditSchedule(s); setDialogOpen(true); }}>
                        <Icon name="edit" className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="sm" aria-label="Delete schedule" title="Delete schedule" className="text-muted-foreground hover:text-destructive" onClick={() => confirmDelete(s)}>
                        <Icon name="trash" className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {dialogOpen && editSchedule && (
        <BatchScheduleDialog
          open={dialogOpen}
          onClose={() => {
            setDialogOpen(false);
            setEditSchedule(null);
          }}
          journeyId={editSchedule.journeyId}
          journeyName={journeyName}
          stageId={editSchedule.stageId}
          existingSchedule={editSchedule}
          onSaved={() => { loadSchedules(); onScheduleChanged?.(); }}
        />
      )}
    </div>
  );
}
