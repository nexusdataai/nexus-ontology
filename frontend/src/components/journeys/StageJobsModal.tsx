/**
 * StageJobsModal Component
 * 
 * Modal to view all jobs for call processing journey.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
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
import { Badge } from '../ui/badge';
import { 
  Eye, 
  Play, 
  Clock, 
  CheckCircle, 
  XCircle, 
  Loader2,
  RotateCcw,
  Calendar,
  TrendingUp,
  Phone,
} from 'lucide-react';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';
import { JobExecution } from '../../types/callProcessingJourney';

interface StageJobsModalProps {
  journeyId: string;
  journeyName?: string;
  trigger?: React.ReactNode;
  onJobAction?: (jobId: string, action: string) => void;
  onViewJob?: (jobId: string) => void;
}

export function StageJobsModal({
  journeyId,
  journeyName = 'Call Processing',
  trigger,
  onJobAction,
  onViewJob,
}: StageJobsModalProps) {
  const [isOpen, setIsOpen] = useState(false);
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
  const calculateDuration = (startedAt?: Date, completedAt?: Date): string => {
    if (!startedAt) return '-';
    if (!completedAt) return 'Running...';
    
    try {
      const diffMs = completedAt.getTime() - startedAt.getTime();
      const diffMins = Math.round(diffMs / (1000 * 60));
      
      if (diffMins < 1) return '< 1m';
      if (diffMins < 60) return `${diffMins}m`;
      
      const hours = Math.floor(diffMins / 60);
      const mins = diffMins % 60;
      return `${hours}h ${mins}m`;
    } catch {
      return '-';
    }
  };

  // Format timestamp for display
  const formatTimestamp = (date?: Date): string => {
    if (!date) return '-';
    try {
      return date.toLocaleString();
    } catch {
      return '-';
    }
  };

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'running':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  // Get status badge color
  const getStatusBadgeColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'running':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
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
    totalCalls: jobs.reduce((acc, j) => acc + (j.itemsProcessed || 0), 0),
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm" className="gap-2">
            <TrendingUp className="h-4 w-4" />
            View All Jobs
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-6xl h-[85vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            All Jobs - {journeyName}
          </DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-4 flex-1 min-h-0 overflow-hidden">
          {/* Header Stats */}
          <div className="flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>Total Jobs: <strong>{stats.total}</strong></span>
              <span className="text-green-600">Completed: {stats.completed}</span>
              <span className="text-blue-600">Running: {stats.running}</span>
              <span className="text-red-600">Failed: {stats.failed}</span>
              <span>Total Calls: <strong>{stats.totalCalls}</strong></span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadJobs}
              disabled={isLoading}
              className="gap-2"
            >
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
              Refresh
            </Button>
          </div>

          {/* Jobs Table */}
          <div className="flex-1 min-h-0 overflow-auto border rounded-md">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span>Loading jobs...</span>
                </div>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-muted-foreground">
                  <XCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>{error}</p>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={loadJobs}
                    className="mt-2"
                  >
                    Retry
                  </Button>
                </div>
              </div>
            ) : jobs.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-muted-foreground">
                  <Calendar className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No jobs found</p>
                  <p className="text-xs mt-1">Start a new job to see it here</p>
                </div>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">Status</TableHead>
                    <TableHead>Job ID</TableHead>
                    <TableHead>Stage</TableHead>
                    <TableHead>Start Time</TableHead>
                    <TableHead>End Time</TableHead>
                    <TableHead className="w-20">Duration</TableHead>
                    <TableHead className="text-right">Calls</TableHead>
                    <TableHead className="text-right">Progress</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job, index) => (
                    <TableRow key={job.id} className="hover:bg-muted/50">
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(job.status)}
                          <Badge variant="outline" className={`text-xs ${getStatusBadgeColor(job.status)}`}>
                            {job.status}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        <span className="font-medium">{job.id}</span>
                        {index === 0 && (
                          <Badge variant="secondary" className="ml-2 text-xs">Latest</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">
                        {job.stageName || job.stageId}
                      </TableCell>
                      <TableCell className="text-xs">
                        {formatTimestamp(job.startedAt)}
                      </TableCell>
                      <TableCell className="text-xs">
                        {formatTimestamp(job.completedAt)}
                      </TableCell>
                      <TableCell className="text-xs">
                        {calculateDuration(job.startedAt, job.completedAt)}
                      </TableCell>
                      <TableCell className="text-right text-sm">
                        {job.itemsProcessed || 0} / {job.itemsTotal || 0}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge variant="outline">
                          {job.progress}%
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-8 w-8 p-0"
                            title="View details in studio"
                            onClick={() => {
                              setIsOpen(false);
                              onViewJob?.(job.id);
                            }}
                          >
                            <Eye className="h-3 w-3" />
                          </Button>
                          {job.status === 'completed' && (
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-8 w-8 p-0"
                              onClick={() => onJobAction?.(job.id, 'repeat')}
                              title="Repeat this job"
                            >
                              <Play className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default StageJobsModal;

