import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Switch } from '../ui/switch';
import {
  Calendar,
  Trash2,
  RefreshCw,
  Clock,
  Loader2,
  AlertCircle,
  Pencil,
  Play,
} from 'lucide-react';
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
  return INTERVAL_LABELS[minutes] || `Every ${minutes}m`;
}

function formatTime(iso: string | null): string {
  if (!iso) return '-';
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

function statusColor(status: string | null): string {
  switch (status) {
    case 'in_progress':
      return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
    case 'completed':
      return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
    case 'failed':
      return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
    default:
      return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
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

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Calendar className="h-4 w-4" />
            Batch Schedules
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={loadSchedules} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading && schedules.length === 0 && (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            Loading schedules...
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 py-4 text-sm text-red-500">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {!loading && schedules.length === 0 && !error && (
          <div className="text-center py-8 text-muted-foreground text-sm">
            No batch schedules configured
          </div>
        )}

        {schedules.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Journey / Stage</th>
                  <th className="pb-2 pr-4 font-medium">Interval</th>
                  <th className="pb-2 pr-4 font-medium">Last Run</th>
                  <th className="pb-2 pr-4 font-medium">Next Run</th>
                  <th className="pb-2 pr-4 font-medium">Status</th>
                  <th className="pb-2 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {schedules.map((s) => (
                  <tr key={s.scheduleId} className="border-b last:border-b-0">
                    <td className="py-3 pr-4">
                      <div className="font-medium">{s.journeyId}</div>
                      <div className="text-xs text-muted-foreground">{s.stageId}</div>
                    </td>
                    <td className="py-3 pr-4">
                      <Badge variant="outline" className="text-xs">
                        {formatInterval(s.intervalMinutes)}
                      </Badge>
                    </td>
                    <td className="py-3 pr-4 text-xs">
                      <div>{formatTime(s.lastRunAt)}</div>
                      {s.lastJobStatus && (
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium mt-0.5 ${statusColor(s.lastJobStatus)}`}>
                          {s.lastJobStatus}
                        </span>
                      )}
                    </td>
                    <td className="py-3 pr-4 text-xs">
                      {s.enabled ? (
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatTime(s.nextRunAt)}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">Paused</span>
                      )}
                    </td>
                    <td className="py-3 pr-4">
                      <Switch
                        checked={s.enabled}
                        onCheckedChange={() => handleToggle(s.scheduleId)}
                        disabled={toggling === s.scheduleId}
                      />
                    </td>
                    <td className="py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-950/30"
                          onClick={() => handleRunNow(s.scheduleId)}
                          disabled={runningNow === s.scheduleId}
                        >
                          {runningNow === s.scheduleId ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Play className="h-3.5 w-3.5 mr-1" />
                          )}
                          Run Now
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0"
                          onClick={() => {
                            setEditSchedule(s);
                            setDialogOpen(true);
                          }}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-red-500 hover:text-red-600"
                          onClick={() => handleDelete(s.scheduleId)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>

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
    </Card>
  );
}
