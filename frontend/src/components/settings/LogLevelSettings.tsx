/**
 * Log level settings
 *
 * Administrators view and change how much the server writes to its logs.
 * The change takes effect at once and can be kept across restarts.
 * Rows follow the settings page language: what it is on the left, the
 * control on the right, divided by hairlines.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { apiClient } from '@/services/apiClient';

// Types
interface LogLevelInfo {
  level: string;
  source: string;
  timestamp: string;
}

interface LogLevelUpdateResult {
  status: string;
  previous_level: string;
  new_level: string;
  ssm_updated: boolean;
  loggers_updated: number;
  timestamp: string;
}

interface EnvironmentInfo {
  environment: string;
  region: string;
  is_aws: boolean;
  is_localstack: boolean;
  log_level: string;
  timestamp: string;
}

// Log level options with descriptions
const LOG_LEVELS = [
  { value: 'DEBUG', label: 'Debug', description: 'Everything, the most detail' },
  { value: 'INFO', label: 'Info', description: 'Normal day-to-day messages' },
  { value: 'WARNING', label: 'Warning', description: 'Warnings and anything worse' },
  { value: 'ERROR', label: 'Error', description: 'Errors and critical failures' },
  { value: 'CRITICAL', label: 'Critical', description: 'Critical failures only' },
];

const SOURCE_LABEL: Record<string, string> = {
  ssm: 'the parameter store',
  env: 'the server environment',
  default: 'the built-in default',
};

const Row: React.FC<{ title: string; description?: React.ReactNode; htmlFor?: string; children: React.ReactNode }> = ({ title, description, htmlFor, children }) => (
  <div className="grid gap-x-10 gap-y-3 border-b border-border py-5 last:border-b-0 xl:grid-cols-[240px_minmax(0,1fr)]">
    <div>
      <label htmlFor={htmlFor} className="text-sm font-medium text-foreground">{title}</label>
      {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
    </div>
    <div className="min-w-0">{children}</div>
  </div>
);

const LogLevelSettings: React.FC = () => {
  const [currentLevel, setCurrentLevel] = useState<LogLevelInfo | null>(null);
  const [environmentInfo, setEnvironmentInfo] = useState<EnvironmentInfo | null>(null);
  const [selectedLevel, setSelectedLevel] = useState<string>('');
  const [persistToSSM, setPersistToSSM] = useState(true);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<LogLevelUpdateResult | null>(null);

  // Fetch current log level and environment info
  const fetchLogLevel = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [levelResponse, envResponse] = await Promise.all([
        apiClient.get<LogLevelInfo>('/api/v1/config/log-level', { requireAuth: false }),
        apiClient.get<EnvironmentInfo>('/api/v1/config/environment', { requireAuth: false }),
      ]);

      setCurrentLevel(levelResponse);
      setSelectedLevel(levelResponse.level);
      setEnvironmentInfo(envResponse);
    } catch (err) {
      console.error('Failed to fetch log level:', err);
      setError('Failed to fetch current log level. Backend may be unavailable.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogLevel();
  }, [fetchLogLevel]);

  // Update log level
  const handleUpdateLogLevel = async () => {
    if (!selectedLevel || selectedLevel === currentLevel?.level) {
      return;
    }

    try {
      setUpdating(true);
      setError(null);
      setSuccess(null);

      const result = await apiClient.put<LogLevelUpdateResult>(
        '/api/v1/config/log-level',
        {
          level: selectedLevel,
          persist_to_ssm: persistToSSM,
        },
        { requireAuth: false }
      );

      setLastUpdate(result);
      setCurrentLevel({
        level: result.new_level,
        source: result.ssm_updated ? 'ssm' : 'env',
        timestamp: result.timestamp,
      });

      const ssmNote = result.ssm_updated ? ' and kept for future restarts' : '';
      setSuccess(
        `Log level changed from ${result.previous_level} to ${result.new_level}${ssmNote}. ` +
        `Updated ${result.loggers_updated} loggers.`
      );
    } catch (err) {
      console.error('Failed to update log level:', err);
      setError('Failed to update log level. Check backend connectivity.');
    } finally {
      setUpdating(false);
    }
  };

  const hasChanges = selectedLevel && selectedLevel !== currentLevel?.level;
  const current = LOG_LEVELS.find(l => l.value === currentLevel?.level);
  const platform = environmentInfo
    ? environmentInfo.is_localstack ? 'LocalStack' : environmentInfo.is_aws ? 'AWS ECS' : 'Local'
    : null;

  return (
    <section className="border-t border-border pt-6">
      <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h3 className="text-md font-medium text-foreground">Server log level</h3>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            How much the server writes to its logs. A change takes effect at once, with no restart.
          </p>
          {environmentInfo && (
            <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{environmentInfo.environment}</span>
              <span aria-hidden="true">·</span>
              <span>{environmentInfo.region}</span>
              <span aria-hidden="true">·</span>
              <span>{platform}</span>
            </p>
          )}
        </div>
        <Button variant="outline" onClick={fetchLogLevel} disabled={loading || updating}>
          <Icon name="refresh" className={cn('h-3.5 w-3.5', loading && 'animate-spin')} /> Refresh
        </Button>
      </header>

      {error && <InlineError className="mt-4" onRetry={currentLevel ? undefined : fetchLogLevel}>{error}</InlineError>}

      {success && (
        <p role="status" className="mt-4 flex items-start gap-2 text-sm text-foreground">
          <Icon name="check-circle" className="mt-0.5 h-4 w-4 shrink-0 text-success" />
          {success}
        </p>
      )}

      {loading && !currentLevel ? (
        <div className="mt-5 space-y-4" aria-busy="true">
          <Skeleton className="h-12 w-full max-w-2xl" />
          <Skeleton className="h-12 w-full max-w-2xl" />
        </div>
      ) : currentLevel ? (
        <div className="mt-2">
          <Row
            title="Level"
            htmlFor="log-level"
            description={
              <>
                Now <span className="font-medium text-foreground">{current?.label || currentLevel.level || 'Unknown'}</span>
                {current ? `: ${current.description.charAt(0).toLowerCase()}${current.description.slice(1)}.` : '.'}{' '}
                Set by {SOURCE_LABEL[currentLevel.source] || SOURCE_LABEL.default}.
              </>
            }
          >
            <Select value={selectedLevel} onValueChange={setSelectedLevel}>
              <SelectTrigger id="log-level" className="w-full sm:max-w-md">
                <SelectValue placeholder="Select log level" />
              </SelectTrigger>
              <SelectContent>
                {LOG_LEVELS.map((level) => (
                  <SelectItem key={level.value} value={level.value}>
                    <span className="font-medium text-foreground">{level.label}</span>
                    <span className="ml-2 text-muted-foreground">{level.description}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Row>

          {/* Keep across restarts */}
          {environmentInfo?.is_aws && (
            <Row
              title="Keep after a restart"
              htmlFor="persist-ssm"
              description={persistToSSM
                ? 'The level is saved to the parameter store and stays after the server restarts.'
                : 'The level applies until the server restarts, then goes back to the saved one.'}
            >
              <div className="flex h-9 items-center gap-2.5">
                <Switch id="persist-ssm" checked={persistToSSM} onCheckedChange={setPersistToSSM} />
                <span className="text-sm text-muted-foreground">{persistToSSM ? 'On' : 'Off'}</span>
              </div>
            </Row>
          )}

          <div className="flex flex-wrap items-center gap-3 pt-5">
            <Button onClick={handleUpdateLogLevel} disabled={!hasChanges || updating}>
              {updating && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
              {updating ? 'Applying' : 'Apply log level'}
            </Button>
            {hasChanges && !updating && <span className="text-sm text-muted-foreground">Unsaved change</span>}
            {lastUpdate && !hasChanges && (
              <span className="num text-xs text-muted-foreground">
                Last changed {new Date(lastUpdate.timestamp).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                {lastUpdate.ssm_updated && ', kept after a restart'}
              </span>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
};

export default LogLevelSettings;
