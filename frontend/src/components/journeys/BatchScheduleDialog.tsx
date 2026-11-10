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
import { Switch } from '../ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Icon } from '../ds/Icon';
import { Field, InlineError } from '../ds/kit';
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
    ? new Date(Date.now() + selectedPreset.minutes * 60 * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';
  // An existing schedule may carry an interval that is not one of the presets.
  const customInterval = !selectedPreset && intervalMinutes ? intervalMinutes : null;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit schedule' : 'Schedule this journey'}</DialogTitle>
          <DialogDescription>
            {journeyName ? `Run "${journeyName}" automatically at a fixed interval.` : 'Run the journey automatically at a fixed interval.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <Field label="Run interval" htmlFor="schedule-interval">
            <Select value={intervalMinutes} onValueChange={setIntervalMinutes}>
              <SelectTrigger id="schedule-interval">
                <SelectValue placeholder="Select interval" />
              </SelectTrigger>
              <SelectContent>
                {customInterval && <SelectItem value={customInterval}>Every {customInterval} minutes</SelectItem>}
                {INTERVAL_PRESETS.map((preset) => (
                  <SelectItem key={preset.value} value={preset.value}>
                    {preset.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field label="Time zone" htmlFor="schedule-timezone">
            <Select value={timezone} onValueChange={setTimezone}>
              <SelectTrigger id="schedule-timezone">
                <SelectValue placeholder="Select time zone" />
              </SelectTrigger>
              <SelectContent>
                {!TIMEZONES.includes(timezone) && <SelectItem value={timezone}>{timezone}</SelectItem>}
                {TIMEZONES.map((tz) => (
                  <SelectItem key={tz} value={tz}>
                    {tz.replace(/_/g, ' ')}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <div className="flex items-center justify-between gap-4 border-t border-border pt-4">
            <label htmlFor="schedule-enabled" className="min-w-0">
              <span className="block text-sm font-medium text-foreground">Schedule is on</span>
              <span className="block text-xs text-muted-foreground">
                {enabled && nextRunPreview ? `The first run starts at about ${nextRunPreview}.` : 'Saved, but no runs start until you turn it on.'}
              </span>
            </label>
            <Switch id="schedule-enabled" checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {error && <InlineError>{error}</InlineError>}
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          {isEdit && (
            <Button variant="ghost" onClick={handleDelete} disabled={saving} className="text-destructive hover:bg-destructive/10 hover:text-destructive sm:mr-auto">
              Delete schedule
            </Button>
          )}
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Icon name="spinner" className="animate-spin" />}
            {isEdit ? 'Save schedule' : 'Create schedule'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
