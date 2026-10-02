/**
 * AuditLogTable Component
 * 
 * Paginated table displaying license audit history.
 * Includes event type icons, expandable rows, and date filtering.
 * 
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { 
  History,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  CheckCircle,
  XCircle,
  Key,
  Shield,
  RefreshCw,
  AlertTriangle,
  Clock,
  Lock,
  Unlock,
  Loader2,
  Calendar
} from 'lucide-react';
import { 
  AuditLogTableProps, 
  AuditLogEntry, 
  LicenseEventType,
  EVENT_TYPE_LABELS 
} from '@/types/license';

// ============================================================================
// Event Type Icons
// ============================================================================

const EVENT_ICONS: Record<LicenseEventType, React.ReactNode> = {
  license_activated: <Key className="h-4 w-4 text-green-600" />,
  license_validated: <Shield className="h-4 w-4 text-blue-600" />,
  license_validation_failed: <XCircle className="h-4 w-4 text-red-600" />,
  license_deactivated: <Lock className="h-4 w-4 text-gray-600" />,
  license_renewed: <RefreshCw className="h-4 w-4 text-green-600" />,
  license_expired: <AlertTriangle className="h-4 w-4 text-red-600" />,
  grace_period_started: <Clock className="h-4 w-4 text-yellow-600" />,
  grace_period_ended: <AlertTriangle className="h-4 w-4 text-red-600" />,
  feature_access_denied: <Lock className="h-4 w-4 text-red-600" />,
  feature_access_granted: <Unlock className="h-4 w-4 text-green-600" />,
};

// ============================================================================
// Helper Functions
// ============================================================================

function formatTimestamp(timestamp: string): string {
  try {
    return new Date(timestamp).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return timestamp;
  }
}

function getEventIcon(eventType: LicenseEventType): React.ReactNode {
  return EVENT_ICONS[eventType] || <History className="h-4 w-4 text-gray-400" />;
}

function getEventLabel(eventType: LicenseEventType): string {
  return EVENT_TYPE_LABELS[eventType] || eventType;
}

// ============================================================================
// Expandable Row Component
// ============================================================================

interface ExpandableRowProps {
  entry: AuditLogEntry;
}

function ExpandableRow({ entry }: ExpandableRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <>
      <TableRow 
        className="cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
        data-testid={`audit-row-${entry.event_id}`}
      >
        <TableCell className="w-8">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400" />
          )}
        </TableCell>
        <TableCell className="whitespace-nowrap" data-testid="audit-timestamp">
          {formatTimestamp(entry.timestamp)}
        </TableCell>
        <TableCell data-testid="audit-event-type">
          <div className="flex items-center gap-2">
            {getEventIcon(entry.event_type)}
            <span>{getEventLabel(entry.event_type)}</span>
          </div>
        </TableCell>
        <TableCell data-testid="audit-result">
          {entry.result === 'success' ? (
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              <CheckCircle className="h-3 w-3 mr-1" />
              Success
            </Badge>
          ) : (
            <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
              <XCircle className="h-3 w-3 mr-1" />
              Failed
            </Badge>
          )}
        </TableCell>
      </TableRow>
      {isExpanded && (
        <TableRow className="bg-gray-50">
          <TableCell colSpan={4} className="p-4">
            <div className="space-y-2 text-sm" data-testid="audit-details">
              {entry.license_id && (
                <div>
                  <span className="font-medium text-gray-600">License ID:</span>{' '}
                  <span className="font-mono">{entry.license_id}</span>
                </div>
              )}
              {entry.ip_address && (
                <div>
                  <span className="font-medium text-gray-600">IP Address:</span>{' '}
                  <span className="font-mono">{entry.ip_address}</span>
                </div>
              )}
              {entry.user_agent && (
                <div>
                  <span className="font-medium text-gray-600">User Agent:</span>{' '}
                  <span className="text-gray-500 truncate">{entry.user_agent}</span>
                </div>
              )}
              {Object.keys(entry.details).length > 0 && (
                <div>
                  <span className="font-medium text-gray-600">Details:</span>
                  <pre className="mt-1 p-2 bg-white rounded border text-xs overflow-auto">
                    {JSON.stringify(entry.details, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function AuditLogTable({
  logs,
  isLoading,
  totalCount,
  pageSize,
  currentPage,
  onPageChange,
  onDateRangeChange
}: AuditLogTableProps) {
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  const totalPages = Math.ceil(totalCount / pageSize);

  const handleDateFilter = () => {
    onDateRangeChange(
      startDate ? new Date(startDate) : null,
      endDate ? new Date(endDate) : null
    );
  };

  const handleClearFilter = () => {
    setStartDate('');
    setEndDate('');
    onDateRangeChange(null, null);
  };

  return (
    <Card data-testid="audit-log-table">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="h-5 w-5" />
          Audit Log
        </CardTitle>
        <CardDescription>
          View license activity history and events
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Date Range Filter */}
        <div className="flex flex-wrap items-end gap-4 mb-4 p-4 bg-gray-50 rounded-lg">
          <div className="space-y-1">
            <Label htmlFor="start-date" className="text-xs">
              <Calendar className="h-3 w-3 inline mr-1" />
              Start Date
            </Label>
            <Input
              id="start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-40"
              data-testid="start-date-input"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="end-date" className="text-xs">
              <Calendar className="h-3 w-3 inline mr-1" />
              End Date
            </Label>
            <Input
              id="end-date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-40"
              data-testid="end-date-input"
            />
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleDateFilter}
            data-testid="apply-filter-button"
          >
            Apply Filter
          </Button>
          {(startDate || endDate) && (
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={handleClearFilter}
              data-testid="clear-filter-button"
            >
              Clear
            </Button>
          )}
        </div>

        {/* Loading State */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <History className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No audit log entries found</p>
          </div>
        ) : (
          <>
            {/* Table */}
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8"></TableHead>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Event</TableHead>
                    <TableHead>Result</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map((entry) => (
                    <ExpandableRow key={entry.event_id} entry={entry} />
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-gray-500">
                  Showing {((currentPage - 1) * pageSize) + 1} to{' '}
                  {Math.min(currentPage * pageSize, totalCount)} of {totalCount} entries
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onPageChange(currentPage - 1)}
                    disabled={currentPage <= 1}
                    data-testid="prev-page-button"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  <span className="text-sm text-gray-600">
                    Page {currentPage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onPageChange(currentPage + 1)}
                    disabled={currentPage >= totalPages}
                    data-testid="next-page-button"
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default AuditLogTable;
