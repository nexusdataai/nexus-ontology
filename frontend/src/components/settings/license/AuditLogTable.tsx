/**
 * AuditLogTable Component
 *
 * License history: a date filter, a paged table, and a side sheet with the
 * details of one event.
 *
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
 */

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { CodeBlock, DetailSheet, Field, KeyValues, StatusPill, SubHeading, TableShell } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import {
  AuditLogTableProps,
  AuditLogEntry,
  LicenseEventType,
  EVENT_TYPE_LABELS
} from '@/types/license';

// ============================================================================
// Helper Functions
// ============================================================================

function formatTimestamp(timestamp: string): string {
  try {
    return new Date(timestamp).toLocaleString('en-GB', {
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

/** Labels come in title case from the shared types; shown in sentence case. */
function getEventLabel(eventType: LicenseEventType): string {
  const label = EVENT_TYPE_LABELS[eventType] || String(eventType).replace(/_/g, ' ');
  return label.charAt(0).toUpperCase() + label.slice(1).toLowerCase();
}

// ============================================================================
// Row
// ============================================================================

interface ExpandableRowProps {
  entry: AuditLogEntry;
  index: number;
  onOpen: (entry: AuditLogEntry) => void;
}

function ExpandableRow({ entry, index, onOpen }: ExpandableRowProps) {
  return (
    <tr
      tabIndex={0}
      className="rise cursor-pointer border-b border-border transition-colors last:border-b-0 hover:bg-surface-2/60 focus-visible:bg-surface-2/60 focus-visible:outline-none"
      style={{ '--i': index } as React.CSSProperties}
      onClick={() => onOpen(entry)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen(entry); } }}
      data-testid={`audit-row-${entry.event_id}`}
    >
      <td className="num whitespace-nowrap px-5 py-3 text-muted-foreground" data-testid="audit-timestamp">
        {formatTimestamp(entry.timestamp)}
      </td>
      <td className="px-5 py-3 font-medium text-foreground" data-testid="audit-event-type">
        {getEventLabel(entry.event_type)}
      </td>
      <td className="whitespace-nowrap px-5 py-3" data-testid="audit-result">
        {entry.result === 'success'
          ? <StatusPill tone="success">Success</StatusPill>
          : <StatusPill tone="danger">Failed</StatusPill>}
      </td>
      <td className="w-10 px-3 py-3 text-right text-subtle-foreground">
        <Icon name="chevron-right" className="h-3.5 w-3.5" />
      </td>
    </tr>
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
  const [openEntry, setOpenEntry] = useState<AuditLogEntry | null>(null);

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
    <div className="space-y-4" data-testid="audit-log-table">
      {/* Date range filter */}
      <div className="flex flex-wrap items-end gap-3">
        <Field label="From" htmlFor="start-date">
          <Input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="h-8 w-40"
            data-testid="start-date-input"
          />
        </Field>
        <Field label="To" htmlFor="end-date">
          <Input
            id="end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="h-8 w-40"
            data-testid="end-date-input"
          />
        </Field>
        <Button variant="outline" size="sm" onClick={handleDateFilter} data-testid="apply-filter-button">
          Apply
        </Button>
        {(startDate || endDate) && (
          <Button variant="ghost" size="sm" onClick={handleClearFilter} data-testid="clear-filter-button">
            Clear
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-px overflow-hidden rounded-xl border border-border" aria-busy="true">
          {[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-12 w-full rounded-none" />)}
        </div>
      ) : logs.length === 0 ? (
        <EmptyState
          icon="history"
          title="No license events found"
          description={startDate || endDate ? 'Nothing was recorded between these dates. Try a wider range.' : 'Activations, renewals and checks are listed here as they happen.'}
        />
      ) : (
        <>
          <TableShell>
            <table className="w-full min-w-[520px] border-collapse text-sm">
              <thead>
                <tr>
                  {['When', 'Event', 'Result', ''].map((h, i) => (
                    <th key={i} scope="col" className="whitespace-nowrap border-b border-border bg-surface-2 px-5 py-2.5 text-left text-xs font-medium text-muted-foreground">
                      {h || <span className="sr-only">Open</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.map((entry, i) => (
                  <ExpandableRow key={entry.event_id} entry={entry} index={i} onOpen={setOpenEntry} />
                ))}
              </tbody>
            </table>
          </TableShell>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="num text-sm text-muted-foreground">
                Showing {((currentPage - 1) * pageSize) + 1} to{' '}
                {Math.min(currentPage * pageSize, totalCount)} of {totalCount}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onPageChange(currentPage - 1)}
                  disabled={currentPage <= 1}
                  data-testid="prev-page-button"
                >
                  <Icon name="chevron-left" className="h-3.5 w-3.5" />
                  Previous
                </Button>
                <span className="num text-sm text-muted-foreground">
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
                  <Icon name="chevron-right" className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* One event */}
      <DetailSheet
        open={!!openEntry}
        onOpenChange={(open) => { if (!open) setOpenEntry(null); }}
        title={openEntry ? getEventLabel(openEntry.event_type) : 'Event'}
        description={openEntry ? formatTimestamp(openEntry.timestamp) : undefined}
        meta={openEntry && (openEntry.result === 'success'
          ? <StatusPill tone="success" variant="soft">Success</StatusPill>
          : <StatusPill tone="danger" variant="soft">Failed</StatusPill>)}
      >
        {openEntry && (
          <div className="space-y-6" data-testid="audit-details">
            <KeyValues
              items={[
                ...(openEntry.license_id ? [{ label: 'License ID', value: openEntry.license_id, mono: true }] : []),
                ...(openEntry.ip_address ? [{ label: 'IP address', value: openEntry.ip_address, mono: true }] : []),
                { label: 'Event ID', value: openEntry.event_id, mono: true },
              ]}
            />
            {openEntry.user_agent && (
              <div>
                <SubHeading>Sent from</SubHeading>
                <p className="break-words text-sm text-muted-foreground">{openEntry.user_agent}</p>
              </div>
            )}
            {Object.keys(openEntry.details || {}).length > 0 && (
              <div>
                <SubHeading>Details</SubHeading>
                <CodeBlock>{JSON.stringify(openEntry.details, null, 2)}</CodeBlock>
              </div>
            )}
          </div>
        )}
      </DetailSheet>
    </div>
  );
}

export default AuditLogTable;
