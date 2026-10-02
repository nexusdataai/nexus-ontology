/**
 * StepConsole Component
 * 
 * Real-time console display for step logs.
 * Shows logs in a terminal-like interface with color-coded log levels.
 */

import { useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronUp, Terminal, Trash2, Download } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
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

// Log level colors for terminal display
const LOG_LEVEL_COLORS: Record<string, string> = {
  debug: 'text-gray-400',
  info: 'text-blue-400',
  warning: 'text-yellow-400',
  warn: 'text-yellow-400',
  error: 'text-red-400',
};

const LOG_LEVEL_BADGE_COLORS: Record<string, string> = {
  debug: 'bg-gray-700 text-gray-300',
  info: 'bg-blue-900/50 text-blue-300',
  warning: 'bg-yellow-900/50 text-yellow-300',
  warn: 'bg-yellow-900/50 text-yellow-300',
  error: 'bg-red-900/50 text-red-300',
};

export function StepConsole({
  logs,
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

  // Get status indicator color
  const getStatusColor = () => {
    switch (stepStatus) {
      case 'running':
        return 'bg-blue-500';
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="rounded-lg border border-border bg-muted dark:bg-gray-900 overflow-hidden">
      {/* Header */}
      {showHeader && (
        <div
          className="flex items-center justify-between px-3 py-2 bg-muted/50 dark:bg-gray-800/50 border-b border-border cursor-pointer hover:bg-muted dark:hover:bg-gray-800/70 transition-colors"
          onClick={onToggle}
        >
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-muted-foreground">{stepName} Logs</span>
            <Badge variant="outline" className="text-xs bg-muted text-muted-foreground">
              {logs.length}
            </Badge>
            {/* Status indicator */}
            <div className={cn('w-2 h-2 rounded-full', getStatusColor())} />
            {/* Task progress */}
            {taskProgress && stepStatus === 'running' && (
              <Badge variant="outline" className="text-xs bg-blue-900/30 text-blue-300 border-blue-700">
                {taskProgress.current}/{taskProgress.total} tasks
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            {isExpanded && logs.length > 0 && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 text-gray-400 hover:text-foreground"
                  onClick={(e) => {
                    e.stopPropagation();
                    downloadLogs();
                  }}
                  title="Download logs"
                >
                  <Download className="h-3 w-3" />
                </Button>
                {onClear && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 text-gray-400 hover:text-foreground"
                    onClick={(e) => {
                      e.stopPropagation();
                      onClear();
                    }}
                    title="Clear logs"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </>
            )}
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-gray-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-400" />
            )}
          </div>
        </div>
      )}

      {/* Console Content */}
      {isExpanded && (
        <div
          ref={scrollRef}
          className="font-mono text-xs overflow-y-auto overflow-x-hidden"
          style={{ maxHeight }}
          onScroll={handleScroll}
        >
          {logs.length === 0 ? (
            <div className="p-4 text-gray-500 text-center">
              No logs yet. Logs will appear here when the step runs.
            </div>
          ) : (
            <div className="p-2 space-y-0.5">
              {logs.map((log, index) => (
                <div
                  key={index}
                  className={cn(
                    'flex items-start gap-2 py-0.5 px-1 rounded hover:bg-muted/50',
                    log.level === 'error' && 'bg-red-950/20'
                  )}
                >
                  <span className="text-gray-500 flex-shrink-0 select-none">
                    {formatTimestamp(log.timestamp)}
                  </span>
                  <span
                    className={cn(
                      'px-1.5 py-0 rounded text-[10px] uppercase flex-shrink-0',
                      LOG_LEVEL_BADGE_COLORS[log.level] || LOG_LEVEL_BADGE_COLORS.info
                    )}
                  >
                    {log.level}
                  </span>
                  <span className={cn('flex-1 break-all', LOG_LEVEL_COLORS[log.level] || 'text-gray-300')}>
                    {log.message}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Scroll to bottom button */}
          {!isAtBottom && logs.length > 5 && (
            <div className="sticky bottom-2 flex justify-center">
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-xs bg-muted border-border text-muted-foreground hover:bg-accent"
                onClick={scrollToBottom}
              >
                <ChevronDown className="h-3 w-3 mr-1" />
                Scroll to bottom
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
  logs,
  maxLines = 3,
  onExpand,
}: {
  logs: LogEntry[];
  maxLines?: number;
  onExpand?: () => void;
}) {
  const recentLogs = logs.slice(-maxLines);

  if (logs.length === 0) {
    return null;
  }

  return (
    <div
      className="mt-2 bg-muted dark:bg-gray-900/80 rounded-md p-2 font-mono text-xs cursor-pointer hover:bg-accent dark:hover:bg-gray-900"
      onClick={onExpand}
    >
      {recentLogs.map((log, index) => (
        <div key={index} className="flex items-center gap-2 py-0.5 truncate">
          <span className={cn('flex-shrink-0', LOG_LEVEL_COLORS[log.level] || 'text-gray-400')}>
            [{log.level.toUpperCase().charAt(0)}]
          </span>
          <span className="text-gray-300 truncate">{log.message}</span>
        </div>
      ))}
      {logs.length > maxLines && (
        <div className="text-gray-500 text-center mt-1 text-[10px]">
          +{logs.length - maxLines} more logs • Click to expand
        </div>
      )}
    </div>
  );
}

export default StepConsole;
