/**
 * JourneyCard Component
 * 
 * Displays a journey card with name, ID, status badge, progress bar,
 * current stage, creation time, and action buttons.
 * 
 * Requirements: 2.5, 2.6
 */

import { Card, CardContent, CardHeader } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import {
  Eye,
  Clock,
  Loader2,
  Trash2,
} from 'lucide-react';
import { CallProcessingJourney } from '../../types/callProcessingJourney';
import {
  getJourneyStatusColor,
  formatRelativeTime,
} from '../../utils/journeyUtils';

export interface JourneyCardProps {
  journey: CallProcessingJourney;
  onViewStudio: (journeyId: string) => void;
  onDelete: (journeyId: string) => void;
  isActionLoading?: boolean;
}

export function JourneyCard({
  journey,
  onViewStudio,
  onDelete,
  isActionLoading = false,
}: JourneyCardProps) {
  const isRunning = journey.status === 'running';
  
  // Can delete if journey is not running
  const canDelete = journey.status !== 'running';

  return (
    <Card className="hover:shadow-md transition-shadow" data-testid="journey-card">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className="font-semibold text-lg" data-testid="journey-name">
              {journey.name}
            </h3>
            <p className="text-xs text-muted-foreground font-mono" data-testid="journey-id">
              {journey.id.slice(0, 8)}...
            </p>
          </div>
          <Badge
            className={getJourneyStatusColor(journey.status)}
            data-testid="journey-status"
          >
            {isRunning && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
            {journey.status}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Stats Grid - Row 1: Jobs */}
        <div className="grid grid-cols-4 gap-2 text-center py-2 bg-muted/30 rounded-lg">
          <div>
            <p className="text-lg font-bold">{journey.metrics.totalJobs}</p>
            <p className="text-[10px] text-muted-foreground">Jobs</p>
          </div>
          <div>
            <p className="text-lg font-bold text-green-600">{journey.metrics.completedJobs}</p>
            <p className="text-[10px] text-muted-foreground">Done</p>
          </div>
          <div>
            <p className="text-lg font-bold text-blue-600">{journey.metrics.runningJobs}</p>
            <p className="text-[10px] text-muted-foreground">Running</p>
          </div>
          <div>
            <p className="text-lg font-bold text-red-600">{journey.metrics.failedJobs}</p>
            <p className="text-[10px] text-muted-foreground">Failed</p>
          </div>
        </div>

        {/* Stats Grid - Row 2: Calls & Success Rate */}
        <div className="grid grid-cols-2 gap-2 text-center py-2 bg-muted/30 rounded-lg">
          <div>
            <p className="text-lg font-bold text-purple-600">
              {journey.metrics.totalJobs > 0 
                ? Math.round((journey.metrics.completedJobs * 100) / Math.max(journey.metrics.completedJobs + journey.metrics.failedJobs, 1))
                : 0}%
            </p>
            <p className="text-[10px] text-muted-foreground">Success Rate</p>
          </div>
          <div>
            <p className="text-lg font-bold text-indigo-600">{journey.metrics.averageJobDuration > 0 ? Math.round(journey.metrics.averageJobDuration / 1000) + 's' : '0s'}</p>
            <p className="text-[10px] text-muted-foreground">Avg Duration</p>
          </div>
        </div>

        {/* Type & Creation Time */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <Badge variant="outline" className="text-xs" data-testid="journey-type">
            {journey.name?.toLowerCase().includes('semantic') || journey.name?.toLowerCase().includes('rag')
              ? 'semantic-rag'
              : (journey as any).odaComponentType === 'data-pipeline' || journey.name?.toLowerCase().includes('etl')
              ? 'etl-pipeline'
              : journey.type}
          </Badge>
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span data-testid="journey-created-at">
              {formatRelativeTime(journey.createdAt)}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2 border-t">
          <Button
            variant="default"
            size="sm"
            onClick={() => onViewStudio(journey.id)}
            className="flex-1"
            data-testid="view-studio-button"
          >
            <Eye className="h-3 w-3 mr-1" />
            Journey Studio
          </Button>

          {canDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(journey.id)}
              disabled={isActionLoading}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
              data-testid="action-delete-button"
            >
              {isActionLoading ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Trash2 className="h-3 w-3" />
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default JourneyCard;
