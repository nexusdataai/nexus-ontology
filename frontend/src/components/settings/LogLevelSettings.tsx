/**
 * Log Level Settings Component
 * 
 * Allows administrators to view and change the backend log level at runtime.
 * Changes are persisted to AWS SSM Parameter Store and take effect immediately.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { AlertCircle, CheckCircle2, RefreshCw, Settings2, Server } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
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
  { value: 'DEBUG', label: 'Debug', description: 'Most verbose - all messages', color: 'text-purple-600' },
  { value: 'INFO', label: 'Info', description: 'Standard operational messages', color: 'text-blue-600' },
  { value: 'WARNING', label: 'Warning', description: 'Warnings and above only', color: 'text-yellow-600' },
  { value: 'ERROR', label: 'Error', description: 'Errors and critical only', color: 'text-red-600' },
  { value: 'CRITICAL', label: 'Critical', description: 'Critical failures only', color: 'text-red-800' },
];

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

      const ssmNote = result.ssm_updated ? ' and persisted to SSM' : '';
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

  // Get source badge color
  const getSourceBadge = (source: string) => {
    switch (source) {
      case 'ssm':
        return 'bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-300';
      case 'env':
        return 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Backend Log Level
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading configuration...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings2 className="h-5 w-5" />
          Backend Log Level
        </CardTitle>
        <CardDescription>
          Control the verbosity of backend logs. Changes take effect immediately without restart.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Success Alert */}
        {success && (
          <Alert className="border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20">
            <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
            <AlertDescription className="text-green-800 dark:text-green-300">{success}</AlertDescription>
          </Alert>
        )}

        {/* Environment Info */}
        {environmentInfo && (
          <div className="p-4 bg-muted rounded-lg border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Server className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium text-sm text-foreground">Environment</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <span className="text-muted-foreground">Environment:</span>
                <span className="ml-1 font-medium text-foreground">{environmentInfo.environment}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Region:</span>
                <span className="ml-1 font-medium text-foreground">{environmentInfo.region}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Platform:</span>
                <span className="ml-1 font-medium">
                  {environmentInfo.is_localstack ? 'LocalStack' : environmentInfo.is_aws ? 'AWS ECS' : 'Local'}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Source:</span>
                <span className={`ml-1 px-2 py-0.5 rounded text-xs font-medium ${getSourceBadge(currentLevel?.source || 'default')}`}>
                  {currentLevel?.source?.toUpperCase() || 'DEFAULT'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Current Level Display */}
        <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
          <div>
            <Label className="text-base font-medium">Current Log Level</Label>
            <p className="text-sm text-muted-foreground">
              {LOG_LEVELS.find(l => l.value === currentLevel?.level)?.description || 'Unknown level'}
            </p>
          </div>
          <div className={`text-2xl font-bold ${LOG_LEVELS.find(l => l.value === currentLevel?.level)?.color || 'text-muted-foreground'}`}>
            {currentLevel?.level || 'Unknown'}
          </div>
        </div>

        {/* Level Selector */}
        <div className="space-y-3">
          <Label htmlFor="log-level">Select New Log Level</Label>
          <Select value={selectedLevel} onValueChange={setSelectedLevel}>
            <SelectTrigger id="log-level" className="w-full">
              <SelectValue placeholder="Select log level" />
            </SelectTrigger>
            <SelectContent>
              {LOG_LEVELS.map((level) => (
                <SelectItem key={level.value} value={level.value}>
                  <div className="flex items-center gap-2">
                    <span className={`font-medium ${level.color}`}>{level.label}</span>
                    <span className="text-muted-foreground">-</span>
                    <span className="text-muted-foreground text-sm">{level.description}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Persist to SSM Toggle */}
        {environmentInfo?.is_aws && (
          <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
            <div>
              <Label htmlFor="persist-ssm" className="text-base font-medium">
                Persist to SSM
              </Label>
              <p className="text-sm text-muted-foreground">
                {persistToSSM 
                  ? 'Change will be saved to SSM Parameter Store and persist across restarts' 
                  : 'Change will only affect current session and reset on restart'}
              </p>
            </div>
            <Switch
              id="persist-ssm"
              checked={persistToSSM}
              onCheckedChange={setPersistToSSM}
            />
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3 pt-2">
          <Button
            onClick={handleUpdateLogLevel}
            disabled={!hasChanges || updating}
            className="flex items-center gap-2"
          >
            {updating && <RefreshCw className="h-4 w-4 animate-spin" />}
            {updating ? 'Updating...' : 'Apply Log Level'}
          </Button>
          <Button
            variant="outline"
            onClick={fetchLogLevel}
            disabled={loading || updating}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Last Update Info */}
        {lastUpdate && (
          <div className="text-xs text-muted-foreground pt-2">
            Last updated: {new Date(lastUpdate.timestamp).toLocaleString()}
            {lastUpdate.ssm_updated && ' (persisted to SSM)'}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default LogLevelSettings;
