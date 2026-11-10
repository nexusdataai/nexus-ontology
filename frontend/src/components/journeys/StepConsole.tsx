/**
 * StepConsole Component
 * 
 * Real-time console display for step logs.
 * Shows logs in a terminal-like interface with color-coded log levels.
 */

import { useEffect, useRef, useState } from 'react';
import { Button } from '../ui/button';
import { Icon } from '../ds/Icon';
import { LogEntry } from '../../types/callProcessingJourney';
import { cn } from '../../lib/utils';

export interface StepConsoleProps {
  logs: LogEntry[];
  isExpanded?: boolean;
  onToggle?: () => void;
  maxHeight?: string;
  autoScroll?: boolean;
  showHeader?: boolean;
  stepName?: string;
  stepStatus?: 'pending' | 'running' | 'completed' | 'failed';
  taskProgress?: { current: number; total: number } | null;
  onClear?: () => void;
}

// Level word colour. Only warnings and errors carry a status colour.
const LOG_LEVEL_COLORS: Record<string, string> = {
  debug: 'text-subtle-foreground',
  info: 'text-muted-foreground',
  warning: 'text-warning',
  warn: 'text-warning',
  error: 'text-destructive',
};

/** The backend can emit the same line twice in a row; show it once. */
function dedupe(logs: LogEntry[]): LogEntry[] {
  const ms = (t: unknown) => { const n = new Date(t as string).getTime(); return Number.isNaN(n) ? 0 : n; };
  return logs.filter((l, i) => {
    if (i === 0) return true;
    const p = logs[i - 1];
    // The two copies are written a few milliseconds apart.
    return !(l.message === p.message && l.level === p.level && Math.abs(ms(l.timestamp) - ms(p.timestamp)) < 1500);
  });
}

export function StepConsole({
  logs: rawLogs,
  isExpanded = false,
  onToggle,
  maxHeight = '200px',
  autoScroll = true,
  showHeader = true,
  stepName = 'Step',
  stepStatus = 'pending',
  taskProgress = null,
  onClear,
}: StepConsoleProps) {
  const logs = dedupe(rawLogs);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && isAtBottom && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll, isAtBottom]);

  // Track if user has scrolled away from bottom
  const handleScroll = () => {
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      setIsAtBottom(scrollHeight - scrollTop - clientHeight < 10);
    }
  };

  // Scroll to bottom manually
  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      setIsAtBottom(true);
    }
  };

  // Format timestamp for display
  const formatTimestamp = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return timestamp;
    }
  };

  // Download logs as text file
  const downloadLogs = () => {
    const content = logs
      .map((log) => `[${formatTimestamp(log.timestamp)}] [${log.level.toUpperCase()}] ${log.message}`)
      .join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${stepName.toLowerCase().replace(/\s+/g, '-')}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const running = stepStatus === 'running';

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface-2/70">
      {/* Header */}
      {showHeader && (
        <div className="flex items-center justify-between gap-3 border-b border-border px-3 py-2">
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={isExpanded}
            className="flex min-w-0 flex-1 items-center gap-2 text-left text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Icon name={isExpanded ? 'chevron-up' : 'chevron-down'} className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate font-medium">{stepName} output</span>
            <span className="num text-xs text-subtle-foreground">{logs.length} lines</span>
            {running && <span className="dot-live shrink-0 text-primary dark:text-brand-hi" aria-hidden="true" />}
            {taskProgress && running && (
              <span className="num text-xs text-muted-foreground">{taskProgress.current} of {taskProgress.total}</span>
            )}
          </button>
          {isExpanded && logs.length > 0 && (
            <div className="flex shrink-0 items-center gap-1">
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={downloadLogs} aria-label="Download output" title="Download output">
                <Icon name="download" className="h-3.5 w-3.5" />
              </Button>
              {onClear && (
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClear} aria-label="Clear output" title="Clear output">
                  <Icon name="trash" className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Console content */}
      {isExpanded && (
        <div className="relative">
          {!showHeader && logs.length > 0 && (
            <div className="absolute right-2 top-2 z-10 flex items-center gap-1 rounded-md border border-border bg-card p-0.5">
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={downloadLogs} aria-label="Download output" title="Download output">
                <Icon name="download" className="h-3.5 w-3.5" />
              </Button>
              {onClear && (
                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClear} aria-label="Clear output" title="Clear output">
                  <Icon name="trash" className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          )}
          <div
            ref={scrollRef}
            className="scroll-thin overflow-y-auto overflow-x-hidden font-mono text-xs leading-5"
            style={{ maxHeight }}
            onScroll={handleScroll}
          >
            {logs.length === 0 ? (
              <p className="px-3 py-4 font-sans text-sm text-muted-foreground">
                {running ? 'Waiting for the first line of output.' : 'No output yet. Lines appear here when the step runs.'}
              </p>
            ) : (
              <div className="p-3">
                {logs.map((log, index) => (
                  <div key={index} className={cn('flex items-start gap-3 rounded-sm px-1', log.level === 'error' && 'bg-destructive/10')}>
                    <span className="num shrink-0 select-none text-subtle-foreground">{formatTimestamp(log.timestamp)}</span>
                    <span className={cn('w-12 shrink-0', LOG_LEVEL_COLORS[log.level] || LOG_LEVEL_COLORS.info)}>{log.level}</span>
                    <span className={cn('min-w-0 flex-1 break-words', log.level === 'error' ? 'text-destructive' : 'text-foreground')}>{log.message}</span>
                  </div>
                ))}
                {running && (
                  <div className="mt-1 flex items-center gap-2 px-1 text-subtle-foreground">
                    <span className="dot-live text-primary dark:text-brand-hi" aria-hidden="true" /> <span className="font-sans">Live</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Scroll to bottom button */}
          {!isAtBottom && logs.length > 5 && (
            <div className="pointer-events-none absolute inset-x-0 bottom-2 flex justify-center">
              <Button variant="outline" size="sm" className="pointer-events-auto h-7 bg-card text-xs shadow-sm" onClick={scrollToBottom}>
                <Icon name="chevron-down" className="h-3 w-3" /> Latest lines
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Compact inline version for embedding in step cards
export function InlineStepConsole({
  logs: rawLogs,
  maxLines = 3,
  onExpand,
}: {
  logs: LogEntry[];
  maxLines?: number;
  onExpand?: () => void;
}) {
  const logs = dedupe(rawLogs);
  const recentLogs = logs.slice(-maxLines);

  if (logs.length === 0) {
    return null;
  }

  return (
    <button
      type="button"
      className="mt-2 block w-full rounded-md border border-border bg-surface-2/70 p-2 text-left font-mono text-xs transition-colors hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      onClick={onExpand}
    >
      {recentLogs.map((log, index) => (
        <span key={index} className="flex items-center gap-2 truncate py-0.5">
          <span className={cn('shrink-0', LOG_LEVEL_COLORS[log.level] || 'text-muted-foreground')}>{log.level}</span>
          <span className="truncate text-foreground">{log.message}</span>
        </span>
      ))}
      {logs.length > maxLines && (
        <span className="mt-1 block font-sans text-xs text-muted-foreground">
          {logs.length - maxLines} more lines. Select to open.
        </span>
      )}
    </button>
  );
}

export default StepConsole;
