/**
 * LogsModal Component
 *
 * Full log of one step of one run.
 * Supports both controlled mode (isOpen/onClose) and trigger mode.
 */

import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Icon } from '../ds/Icon';
import { EmptyState } from '../ds/primitives';
import { Chips, InlineError } from '../ds/kit';
import { cn } from '../../lib/utils';
import { LogEntry, LogLevel } from '../../types/callProcessingJourney';

export interface LogsModalProps {
  journeyId: string;
  stepId: string;
  stepName?: string;
  jobId?: string;  // Job ID to fetch logs for
  stageId?: string;
  // Controlled mode props
  isOpen?: boolean;
  onClose?: () => void;
  // Trigger mode prop
  trigger?: React.ReactNode;
}

type LevelFilter = 'all' | 'warning' | 'error';

export function LogsModal({
  journeyId,
  stepId,
  stepName = 'Step',
  jobId,
  stageId,
  isOpen: controlledIsOpen,
  onClose,
  trigger,
}: LogsModalProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // View-only filter on the lines already loaded.
  const [level, setLevel] = useState<LevelFilter>('all');

  // Use controlled or internal open state
  const isOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalOpen;
  const setIsOpen = controlledIsOpen !== undefined
    ? (open: boolean) => !open && onClose?.()
    : setInternalOpen;

  useEffect(() => {
    console.log(`📋 LogsModal: isOpen=${isOpen}, jobId=${jobId}, stepId=${stepId}`);
    if (isOpen && stepId && journeyId) {
      loadLogs();
    }
  }, [isOpen, stepId, journeyId, jobId]);

  const loadLogs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (!jobId) {
        console.log('📋 No jobId provided, cannot fetch logs');
        setLogs([]);
        return;
      }

      // Direct API call - no service wrapper complexity
      const configRes = await fetch('/config.json');
      const config = await configRes.json();
      const baseUrl = config?.api?.baseUrl || '';

      const url = `${baseUrl}/api/v1/journeys/${journeyId}/jobs/${jobId}/logs?step_name=${stepId}&limit=500`;
      console.log(`📋 Fetching logs from: ${url}`);

      const response = await fetch(url);
      const json = await response.json();
      console.log('📋 API Response:', json);

      // API returns { success, data: { logs: [...] } }
      const logsArray = json?.data?.logs || [];
      console.log(`📋 Found ${logsArray.length} logs`);

      if (logsArray.length > 0) {
        const mappedLogs: LogEntry[] = logsArray.map((log: any) => ({
          timestamp: log.timestamp,
          level: (log.level || 'info').toLowerCase(),
          message: log.message,
          step_id: log.step_id,
          job_id: log.job_id,
        }));
        setLogs(mappedLogs);
      } else {
        setLogs([]);
      }
    } catch (err) {
      console.error('Error loading logs:', err);
      setError('Failed to load logs');
      setLogs([]);
    } finally {
      setIsLoading(false);
    }
  };

  const levelClass = (l: LogLevel): string => {
    switch (l) {
      case 'error': return 'text-destructive';
      case 'warning': return 'text-warning';
      case 'debug': return 'text-subtle-foreground';
      default: return 'text-muted-foreground';
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    try {
      return new Date(timestamp).toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return timestamp;
    }
  };

  const isWarn = (l: string) => l === 'warning' || l === 'warn';
  const warnings = logs.filter(l => isWarn(l.level)).length;
  const errors = logs.filter(l => l.level === 'error').length;
  const shown = level === 'all' ? logs : logs.filter(l => (level === 'error' ? l.level === 'error' : isWarn(l.level)));

  const copyAll = () => {
    const text = shown.map(l => `${l.timestamp} ${String(l.level).toUpperCase()} ${l.message}`).join('\n');
    navigator.clipboard?.writeText(text).catch(() => {});
  };

  const dialogContent = (
    <DialogContent className="flex max-h-[85dvh] max-w-4xl flex-col gap-0 p-0" data-testid="logs-modal">
      <DialogHeader className="border-b border-border px-5 pb-4 pt-5 pr-12 text-left">
        <DialogTitle className="text-lg font-medium">{stepName} log</DialogTitle>
        <DialogDescription className="text-sm text-muted-foreground">
          {jobId ? <>Run <span className="mono-id">{jobId}</span>. </> : null}
          {isLoading ? 'Loading lines.' : `${logs.length.toLocaleString()} ${logs.length === 1 ? 'line' : 'lines'}${errors ? `, ${errors} ${errors === 1 ? 'error' : 'errors'}` : ''}${warnings ? `, ${warnings} ${warnings === 1 ? 'warning' : 'warnings'}` : ''}.`}
        </DialogDescription>
      </DialogHeader>

      {!isLoading && !error && logs.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-2">
          <Chips<LevelFilter>
            label="Filter by level"
            value={level}
            onChange={setLevel}
            options={[
              { value: 'all', label: 'All', count: logs.length },
              { value: 'warning', label: 'Warnings', count: warnings },
              { value: 'error', label: 'Errors', count: errors },
            ]}
          />
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={copyAll}><Icon name="copy" /> Copy</Button>
            <Button variant="ghost" size="sm" onClick={loadLogs}><Icon name="refresh" /> Refresh</Button>
          </div>
        </div>
      )}

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {isLoading ? (
          <div className="space-y-2" aria-label="Loading log">
            {[0, 1, 2, 3, 4, 5, 6, 7].map(i => <Skeleton key={i} className="h-4" style={{ width: `${92 - (i % 4) * 14}%` }} />)}
          </div>
        ) : error ? (
          <div data-testid="logs-error">
            <InlineError onRetry={loadLogs}>The log could not be loaded.</InlineError>
          </div>
        ) : logs.length === 0 ? (
          <div data-testid="logs-empty">
            <EmptyState
              icon="terminal"
              title="No log lines for this step"
              description={jobId ? 'The step has not written anything in this run.' : 'Run the journey once to see its log here.'}
            />
          </div>
        ) : shown.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">No lines at this level.</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border bg-surface-2/70 p-3 font-mono text-xs leading-5">
            {shown.map((log, index) => (
              <div
                key={`${log.timestamp}-${index}`}
                className={cn('flex flex-col gap-x-3 rounded-sm px-1 sm:flex-row sm:items-start', log.level === 'error' && 'bg-destructive/10')}
                data-testid={`log-entry-${index}`}
              >
                <span className="num shrink-0 select-none whitespace-nowrap text-subtle-foreground">{formatTimestamp(log.timestamp)}</span>
                <span className={cn('w-14 shrink-0', levelClass(log.level))} data-testid={`log-level-${index}`}>{log.level}</span>
                <span className={cn('min-w-0 flex-1 whitespace-pre-wrap break-words', log.level === 'error' ? 'text-destructive' : 'text-foreground')}>{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </DialogContent>
  );

  // Trigger mode - with DialogTrigger
  if (trigger) {
    return (
      <Dialog open={internalOpen} onOpenChange={setInternalOpen}>
        <DialogTrigger asChild>
          {trigger}
        </DialogTrigger>
        {dialogContent}
      </Dialog>
    );
  }

  // Controlled mode - no trigger
  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {dialogContent}
    </Dialog>
  );
}

export default LogsModal;
