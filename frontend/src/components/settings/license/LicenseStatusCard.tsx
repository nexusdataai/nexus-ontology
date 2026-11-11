/**
 * LicenseStatusCard Component
 *
 * The license summary: reads like a statement. Plan, who it is licensed to,
 * the license ID, when it expires and how much of the term is left.
 *
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
 */

import React from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { InlineError, Meter, StatusPill, type Tone } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import {
  LicenseStatus,
  STATUS_COLORS,
  STATUS_LABELS,
  TIER_LABELS,
  LicenseStatusCardProps
} from '@/types/license';

// ============================================================================
// Status Indicator Component
// ============================================================================

interface StatusIndicatorProps {
  status: LicenseStatus;
}

export function getStatusColor(status: LicenseStatus): string {
  return STATUS_COLORS[status] || 'gray';
}

export function getStatusLabel(status: LicenseStatus): string {
  return STATUS_LABELS[status] || 'Unknown';
}

const COLOR_TONE: Record<string, Tone> = {
  green: 'success',
  red: 'danger',
  yellow: 'warning',
  gray: 'neutral',
};

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const color = getStatusColor(status);
  const label = getStatusLabel(status);

  return (
    <span className="inline-flex shrink-0" data-testid="status-indicator" data-status={status} data-color={color}>
      <StatusPill tone={COLOR_TONE[color] || 'neutral'} variant="soft">
        {/* Labels come in title case from the shared types; shown in sentence case. */}
        <span className="lowercase">{label}</span>
      </StatusPill>
    </span>
  );
}

// ============================================================================
// Helpers
// ============================================================================

const SURFACE = 'rounded-xl border border-border bg-card p-5 shadow-xs sm:p-6';

function formatDate(value: string | null): string {
  if (!value) return 'Not set';
  const d = new Date(value);
  return isNaN(d.getTime()) ? value : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
}

const prettyFeature = (id: string) => id.replace(/[_-]+/g, ' ').replace(/^\w/, c => c.toUpperCase());

const DAY_MS = 86_400_000;

// ============================================================================
// Main Component
// ============================================================================

export function LicenseStatusCard({
  status,
  isLoading,
  error,
  onRefresh
}: LicenseStatusCardProps) {

  // Loading state
  if (isLoading && !status) {
    return (
      <section className={SURFACE} aria-busy="true" aria-label="License summary">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="mt-3 h-4 w-72 max-w-full" />
        <Skeleton className="mt-6 h-1 w-full" />
        <Skeleton className="mt-3 h-4 w-56" />
      </section>
    );
  }

  // Error state
  if (error && !status) {
    return (
      <InlineError onRetry={onRefresh}>
        <span className="block font-medium lowercase first-letter:uppercase">Connection Error</span>
        <span className="block">{error}</span>
      </InlineError>
    );
  }

  // Not activated state
  if (!status || status.license_status === 'not_activated') {
    return (
      <section className={SURFACE} aria-label="License summary">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-xl font-medium tracking-tight text-foreground">No license yet</h3>
            <p className="mt-1 max-w-xl text-sm text-muted-foreground">
              {status?.activation_instructions && !/\/api\/|^(POST|GET|PUT)/i.test(status.activation_instructions)
                ? status.activation_instructions
                : 'Enter a license key below to activate this installation.'}
            </p>
          </div>
          <StatusIndicator status="not_activated" />
        </div>
      </section>
    );
  }

  const licenseStatus = status.license_status;
  const isExpiringSoon = status.is_expiring_soon;
  const isGracePeriod = licenseStatus === 'grace_period';
  const hasDays = status.days_remaining !== null && status.days_remaining !== undefined;

  // Length of the term, to draw how much of it is left.
  const start = status.activated_at ? new Date(status.activated_at).getTime() : NaN;
  const end = status.expires_at ? new Date(status.expires_at).getTime() : NaN;
  const termDays = !isNaN(start) && !isNaN(end) && end > start
    ? Math.round((end - start) / DAY_MS)
    : Math.max(status.days_remaining || 0, 365);

  return (
    <section className={SURFACE} aria-label="License summary">
      {/* Who and what */}
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h3 className="text-xl font-medium tracking-tight text-foreground">
            {status.tier ? `${TIER_LABELS[status.tier]} plan` : 'License'}
          </h3>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
            {status.holder_name && <span>Licensed to <span className="text-foreground">{status.holder_name}</span></span>}
            {status.holder_name && status.license_id && <span aria-hidden="true">·</span>}
            {status.license_id && <span className="font-mono text-xs text-foreground">{status.license_id}</span>}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <StatusIndicator status={licenseStatus} />
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-muted-foreground" onClick={onRefresh} disabled={isLoading} aria-label="Refresh license status">
            <Icon name="refresh" className={cn('h-3.5 w-3.5', isLoading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* Term */}
      {(status.expires_at || hasDays) && (
        <div className="mt-5 border-t border-border pt-5">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <p className="text-sm text-muted-foreground">
              {status.expires_at
                ? <>{licenseStatus === 'expired' ? 'Expired on' : 'Expires on'} <span className="font-medium text-foreground">{formatDate(status.expires_at)}</span></>
                : 'No expiry date set'}
              {status.activated_at && <>, activated {formatDate(status.activated_at)}</>}
            </p>
            {hasDays && licenseStatus === 'active' && (
              <p className={cn('num text-sm font-medium', isExpiringSoon ? 'text-warning' : 'text-foreground')} data-testid="days-remaining">
                {status.days_remaining} days remaining
              </p>
            )}
          </div>
          {hasDays && licenseStatus === 'active' && (
            <Meter
              value={Math.max(status.days_remaining || 0, 0)}
              max={termDays}
              tone={isExpiringSoon ? 'warning' : 'info'}
              className="mt-3 h-1.5"
              label="Time left on the license"
            />
          )}
          {licenseStatus === 'active' && isExpiringSoon && status.expiration_warning && (
            <p className="mt-3 flex items-start gap-2 text-sm text-foreground" data-testid="expiration-warning">
              <Icon name="alert-triangle" className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
              {status.expiration_warning}
            </p>
          )}
        </div>
      )}

      {/* Grace period */}
      {isGracePeriod && status.grace_period && (
        <div className="mt-5 border-t border-border pt-5" data-testid="grace-period-info">
          <p className="flex items-start gap-2 text-sm font-medium text-foreground">
            <Icon name="alert-triangle" className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
            <span>Grace period: {status.grace_period.days_remaining} days remaining</span>
          </p>
          {status.grace_period.restrictions.length > 0 && (
            <p className="mt-1 pl-6 text-sm text-muted-foreground">
              Restrictions: {status.grace_period.restrictions.join(', ')}
            </p>
          )}
        </div>
      )}

      {/* What is included */}
      {status.features && status.features.length > 0 && (
        <p className="mt-5 border-t border-border pt-4 text-sm text-muted-foreground">
          Includes <span className="num font-medium text-foreground">{status.features.length}</span> {status.features.length === 1 ? 'feature' : 'features'}:{' '}
          {status.features.map(prettyFeature).join(', ')}.
        </p>
      )}

      {/* Status message */}
      {status.message && (
        <p className="mt-3 text-sm text-muted-foreground">{status.message}</p>
      )}
    </section>
  );
}

export default LicenseStatusCard;
