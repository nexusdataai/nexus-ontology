/**
 * LogsModal Component
 * 
 * Modal for viewing step logs with color-coded log levels.
 * Supports both controlled mode (open/onClose) and trigger mode.
 */

import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../ui/dialog';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { Loader2 } from 'lucide-react';
import { LogEntry, LogLevel } from '../../types/callProcessingJourney';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';

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

  const getLogLevelColor = (level: LogLevel): string => {
    switch (level) {
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'info':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'debug':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getLogTextColor = (level: LogLevel): string => {
    switch (level) {
      case 'error':
        return 'text-red-700';
      case 'warning':
        return 'text-yellow-700';
      case 'info':
        return 'text-blue-700';
      case 'debug':
        return 'text-gray-600';
      default:
        return 'text-gray-700';
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const dialogContent = (
    <DialogContent className="max-w-4xl max-h-[80vh]" data-testid="logs-modal">
      <DialogHeader>
        <DialogTitle>{stepName} Logs</DialogTitle>
      </DialogHeader>

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span className="ml-2">Loading logs...</span>
        </div>
      ) : error ? (
        <div className="text-center py-8 text-red-500" data-testid="logs-error">
          {error}
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground" data-testid="logs-empty">
          No logs available for this step
        </div>
      ) : (
        <ScrollArea className="h-[500px] pr-4">
          <div className="space-y-2 font-mono text-sm">
            {logs.map((log, index) => (
              <div
                key={`${log.timestamp}-${index}`}
                className={`p-3 rounded border ${getLogLevelColor(log.level)}`}
                data-testid={`log-entry-${index}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Badge
                    variant="outline"
                    className={getLogLevelColor(log.level)}
                    data-testid={`log-level-${index}`}
                  >
                    {log.level.toUpperCase()}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatTimestamp(log.timestamp)}
                  </span>
                </div>
                <p className={`whitespace-pre-wrap ${getLogTextColor(log.level)}`}>
                  {log.message}
                </p>
              </div>
            ))}
          </div>
        </ScrollArea>
      )}
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
