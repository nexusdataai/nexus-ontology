import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Alert, AlertDescription } from '../ui/alert';
import { Loader2, AlertCircle, Calendar, Clock } from 'lucide-react';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';

export interface BatchScheduleDialogProps {
  open: boolean;
  onClose: () => void;
  journeyId: string;
  journeyName?: string;
  stageId: string;
  existingSchedule?: any;
  onSaved: () => void;
}

const INTERVAL_PRESETS = [
  { value: '5', label: 'Every 5 minutes', minutes: 5 },
  { value: '10', label: 'Every 10 minutes', minutes: 10 },
  { value: '15', label: 'Every 15 minutes', minutes: 15 },
  { value: '30', label: 'Every 30 minutes', minutes: 30 },
  { value: '60', label: 'Every hour', minutes: 60 },
  { value: '360', label: 'Every 6 hours', minutes: 360 },
  { value: '1440', label: 'Daily', minutes: 1440 },
];

const TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Berlin',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Australia/Sydney',
];

export function BatchScheduleDialog({
  open,
  onClose,
  journeyId,
  journeyName,
  stageId,
  existingSchedule,
  onSaved,
}: BatchScheduleDialogProps) {
  const [intervalMinutes, setIntervalMinutes] = useState('5');
  const [enabled, setEnabled] = useState(true);
  const [timezone, setTimezone] = useState('UTC');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = !!existingSchedule;

  useEffect(() => {
    if (existingSchedule) {
      setIntervalMinutes(String(existingSchedule.intervalMinutes));
      setEnabled(existingSchedule.enabled ?? true);
      setTimezone(existingSchedule.timezone || 'UTC');
    } else {
      setIntervalMinutes('5');
      setEnabled(true);
      setTimezone('UTC');
    }
    setError(null);
  }, [existingSchedule, open]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      if (isEdit) {
        const res = await callProcessingJourneyService.updateSchedule(existingSchedule.scheduleId, {
          interval_minutes: parseInt(intervalMinutes),
          enabled,
          timezone,
        });
        if (!res.success) {
          setError(res.error?.message || 'Failed to update schedule');
          return;
        }
      } else {
        const res = await callProcessingJourneyService.createSchedule({
          journey_id: journeyId,
          stage_id: stageId,
          interval_minutes: parseInt(intervalMinutes),
          enabled,
          timezone,
        });
        if (!res.success) {
          setError(res.error?.message || 'Failed to create schedule');
          return;
        }
      }
      onSaved();
      onClose();
    } catch (e: any) {
      setError(e.message || 'Unexpected error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!existingSchedule) return;
    setSaving(true);
    setError(null);
    try {
      const res = await callProcessingJourneyService.deleteSchedule(existingSchedule.scheduleId);
      if (!res.success) {
        setError(res.error?.message || 'Failed to delete schedule');
        return;
      }
      onSaved();
      onClose();
    } catch (e: any) {
      setError(e.message || 'Unexpected error');
    } finally {
      setSaving(false);
    }
  };

  const selectedPreset = INTERVAL_PRESETS.find(p => p.value === intervalMinutes);
  const nextRunPreview = selectedPreset
    ? new Date(Date.now() + selectedPreset.minutes * 60 * 1000).toLocaleTimeString()
    : '';

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            {isEdit ? 'Edit Batch Schedule' : 'Create Batch Schedule'}
          </DialogTitle>
          <DialogDescription>
            {journeyName ? `Schedule periodic execution for "${journeyName}"` : 'Schedule periodic job execution'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Interval Preset */}
          <div className="space-y-2">
            <Label>Run Interval</Label>
            <Select value={intervalMinutes} onValueChange={setIntervalMinutes}>
              <SelectTrigger>
                <SelectValue placeholder="Select interval" />
              </SelectTrigger>
              <SelectContent>
                {INTERVAL_PRESETS.map((preset) => (
                  <SelectItem key={preset.value} value={preset.value}>
                    {preset.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Timezone */}
          <div className="space-y-2">
            <Label>Timezone</Label>
            <Select value={timezone} onValueChange={setTimezone}>
              <SelectTrigger>
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent>
                {TIMEZONES.map((tz) => (
                  <SelectItem key={tz} value={tz}>
                    {tz}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Enable / Disable */}
          <div className="flex items-center justify-between">
            <div>
              <Label>Enabled</Label>
              <p className="text-xs text-muted-foreground">Start scheduling immediately</p>
            </div>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {/* Next run preview */}
          {enabled && nextRunPreview && (
            <div className="flex items-center gap-2 rounded-md border p-3 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>First run approximately at {nextRunPreview}</span>
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="flex gap-2">
          {isEdit && (
            <Button variant="destructive" onClick={handleDelete} disabled={saving} className="mr-auto">
              Delete
            </Button>
          )}
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isEdit ? 'Update' : 'Create Schedule'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
