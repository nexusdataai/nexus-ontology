/**
 * StageJobsModal Component
 *
 * Every run of a journey, in a dialog. Opens from its own trigger, or is
 * controlled by the parent through `open` / `onOpenChange`.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Icon } from '../ds/Icon';
import { EmptyState } from '../ds/primitives';
import { InlineError, Meter, StatusPill } from '../ds/kit';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';
import { JobExecution } from '../../types/callProcessingJourney';

interface StageJobsModalProps {
  journeyId: string;
  journeyName?: string;
  trigger?: React.ReactNode;
  onJobAction?: (jobId: string, action: string) => void;
  onViewJob?: (jobId: string) => void;
  /** Controlled mode: the parent owns the open state and no trigger is rendered. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function StageJobsModal({
  journeyId,
  journeyName = 'Journey',
  trigger,
  onJobAction,
  onViewJob,
  open: controlledOpen,
  onOpenChange,
}: StageJobsModalProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const controlled = controlledOpen !== undefined;
  const isOpen = controlled ? !!controlledOpen : internalOpen;
  const setIsOpen = (next: boolean) => {
    if (controlled) onOpenChange?.(next);
    else setInternalOpen(next);
  };
  const [jobs, setJobs] = useState<JobExecution[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // Load jobs when modal opens
  const loadJobs = useCallback(async () => {
    if (!journeyId) return;

    try {
      setIsLoading(true);
      setError('');

      const response = await callProcessingJourneyService.getJobHistory(journeyId);

      if (response.success && response.data) {
        setJobs(response.data);
      } else {
        setJobs([]);
        setError(response.error?.message || 'No jobs found');
      }
    } catch (err) {
      console.error('Error loading jobs:', err);
      setError(err instanceof Error ? err.message : 'Failed to load jobs');
      setJobs([]);
    } finally {
      setIsLoading(false);
    }
  }, [journeyId]);

  // Calculate duration between start and end time
  const calculateDuration = (startedAt?: any, completedAt?: any): string => {
    if (!startedAt) return 'Not started';
    if (!completedAt) return 'Running';

    try {
      const diffMs = new Date(completedAt).getTime() - new Date(startedAt).getTime();
      if (!Number.isFinite(diffMs)) return 'Not recorded';
      const diffMins = Math.round(diffMs / (1000 * 60));

      if (diffMins < 1) return 'Under 1 min';
      if (diffMins < 60) return `${diffMins} min`;

      const hours = Math.floor(diffMins / 60);
      const mins = diffMins % 60;
      return `${hours} h ${mins} min`;
    } catch {
      return 'Not recorded';
    }
  };

  // Format timestamp for display
  const formatTimestamp = (date?: any): string => {
    if (!date) return '';
    try {
      const d = new Date(date);
      if (Number.isNaN(d.getTime())) return '';
      return d.toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  // Load jobs when modal opens
  useEffect(() => {
    if (isOpen) {
      loadJobs();
    }
  }, [isOpen, loadJobs]);

  // Auto-refresh every 10 seconds when modal is open
  useEffect(() => {
    if (!isOpen) return;

    const refreshInterval = setInterval(() => {
      loadJobs();
    }, 10000);

    return () => clearInterval(refreshInterval);
  }, [isOpen, loadJobs]);

  // Calculate stats
  const stats = {
    total: jobs.length,
    completed: jobs.filter(j => j.status === 'completed').length,
    running: jobs.filter(j => j.status === 'running').length,
    failed: jobs.filter(j => j.status === 'failed').length,
    totalCalls: jobs.reduce((acc, j) => acc + ((j as any).itemsProcessed || 0), 0),
  };

  const firstLoad = isLoading && jobs.length === 0;

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {!controlled && (
        <DialogTrigger asChild>
          {trigger || (
            <Button variant="outline" size="sm">
              <Icon name="history" /> All runs
            </Button>
          )}
        </DialogTrigger>
      )}
      <DialogContent className="flex h-[85dvh] max-w-6xl flex-col gap-0 p-0">
        <DialogHeader className="border-b border-border px-5 pb-4 pt-5 pr-12 text-left">
          <DialogTitle className="text-lg font-medium">All runs</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            {journeyName}.{' '}
            {firstLoad ? 'Loading runs.' : (
              <span className="num">
                {stats.total} {stats.total === 1 ? 'run' : 'runs'}: {stats.completed} completed, {stats.running} running, {stats.failed} failed. {stats.totalCalls.toLocaleString()} records processed in total.
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-2">
          <p className="text-xs text-muted-foreground">Refreshes every 10 seconds while open.</p>
          <Button variant="ghost" size="sm" onClick={loadJobs} disabled={isLoading}>
            <Icon name={isLoading ? 'spinner' : 'refresh'} className={isLoading ? 'animate-spin' : undefined} /> Refresh
          </Button>
        </div>

        <div className="scroll-thin min-h-0 flex-1 overflow-auto">
          {firstLoad ? (
            <div className="space-y-3 p-5" aria-label="Loading runs">
              {[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : error ? (
            <div className="p-5">
              <InlineError onRetry={loadJobs}>{error === 'No jobs found' ? 'The runs could not be loaded.' : error}</InlineError>
            </div>
          ) : jobs.length === 0 ? (
            <div className="p-5">
              <EmptyState icon="history" title="No runs yet" description="Run the journey once and it will be listed here." />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Run</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Finished</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead className="text-right">Records</TableHead>
                  <TableHead className="w-36">Progress</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-px" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((job, index) => {
                  const j = job as any;
                  const pct = Math.max(0, Math.min(100, Math.round(Number(j.progress) || 0)));
                  return (
                    <TableRow key={job.id} className="group">
                      <TableCell>
                        <span className="font-mono text-xs font-medium text-foreground">{job.id}</span>
                        {index === 0 && <span className="ml-2 text-xs text-primary dark:text-brand-hi">Latest</span>}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{j.stageName || job.stageId}</TableCell>
                      <TableCell className="num whitespace-nowrap">{formatTimestamp(j.startedAt) || 'Not started'}</TableCell>
                      <TableCell className="num whitespace-nowrap text-muted-foreground">{formatTimestamp(j.completedAt) || 'Not finished'}</TableCell>
                      <TableCell className="num whitespace-nowrap">{calculateDuration(j.startedAt, j.completedAt)}</TableCell>
                      <TableCell className="num text-right">
                        {(j.itemsProcessed || 0).toLocaleString()} <span className="text-muted-foreground">of {(j.itemsTotal || 0).toLocaleString()}</span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Meter value={pct} tone={job.status === 'failed' ? 'danger' : 'info'} label="Progress" />
                          <span className="num w-9 shrink-0 text-right text-xs text-muted-foreground">{pct}%</span>
                        </div>
                      </TableCell>
                      <TableCell><StatusPill status={job.status} /></TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7"
                            title="Show this run in the studio"
                            onClick={() => {
                              setIsOpen(false);
                              onViewJob?.(job.id);
                            }}
                          >
                            View
                          </Button>
                          {job.status === 'completed' && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => onJobAction?.(job.id, 'repeat')}
                              title="Run again"
                              aria-label="Run again"
                            >
                              <Icon name="play" className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default StageJobsModal;
