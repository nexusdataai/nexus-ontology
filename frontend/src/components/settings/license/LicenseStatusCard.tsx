/**
 * LicenseStatusCard Component
 * 
 * Displays the current license status with visual indicators.
 * Shows tier, holder name, expiration date, and days remaining.
 * 
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Clock,
  Shield,
  Building,
  Calendar,
  Loader2
} from 'lucide-react';
import {
  LicenseStatusData,
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

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const color = getStatusColor(status);
  const label = getStatusLabel(status);
  
  const colorClasses: Record<string, string> = {
    green: 'bg-green-500',
    red: 'bg-red-500',
    yellow: 'bg-yellow-500',
    gray: 'bg-gray-500',
  };

  const badgeVariants: Record<string, string> = {
    green: 'bg-green-100 text-green-800 border-green-200',
    red: 'bg-red-100 text-red-800 border-red-200',
    yellow: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    gray: 'bg-gray-100 text-gray-800 border-gray-200',
  };

  const Icon = color === 'green' ? CheckCircle : 
               color === 'red' ? XCircle : 
               color === 'yellow' ? AlertTriangle : Clock;

  return (
    <Badge 
      variant="outline" 
      className={`${badgeVariants[color]} flex items-center gap-1.5 px-3 py-1`}
      data-testid="status-indicator"
      data-status={status}
      data-color={color}
    >
      <span className={`w-2 h-2 rounded-full ${colorClasses[color]}`} />
      <Icon className="h-3.5 w-3.5" />
      <span className="font-medium">{label}</span>
    </Badge>
  );
}


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
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            License Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error && !status) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              License Status
            </CardTitle>
            <Button variant="outline" size="sm" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3 p-4 bg-red-50 rounded-lg border border-red-200">
            <XCircle className="h-5 w-5 text-red-500" />
            <div>
              <p className="font-medium text-red-800">Connection Error</p>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Not activated state
  if (!status || status.license_status === 'not_activated') {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              License Status
            </CardTitle>
            <StatusIndicator status="not_activated" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <Clock className="h-5 w-5 text-gray-500" />
              <div>
                <p className="font-medium text-gray-800">No License Activated</p>
                <p className="text-sm text-gray-600">
                  {status?.activation_instructions || 'Enter a license key below to activate your license.'}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const licenseStatus = status.license_status;
  const isExpiringSoon = status.is_expiring_soon;
  const isGracePeriod = licenseStatus === 'grace_period';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            License Status
          </CardTitle>
          <div className="flex items-center gap-2">
            <StatusIndicator status={licenseStatus} />
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={onRefresh}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* License Details Grid */}
        <div className="grid grid-cols-2 gap-4">
          {/* Tier */}
          {status.tier && (
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Tier</p>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="font-semibold">
                  {TIER_LABELS[status.tier]}
                </Badge>
              </div>
            </div>
          )}

          {/* License ID */}
          {status.license_id && (
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">License ID</p>
              <p className="font-mono text-sm">{status.license_id}</p>
            </div>
          )}

          {/* Holder */}
          {status.holder_name && (
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Licensed To</p>
              <div className="flex items-center gap-2">
                <Building className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm font-medium">{status.holder_name}</p>
              </div>
            </div>
          )}

          {/* Expiration */}
          {status.expires_at && (
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Expires</p>
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm">
                  {new Date(status.expires_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Days Remaining */}
        {status.days_remaining !== null && status.days_remaining !== undefined && licenseStatus === 'active' && (
          <div 
            className={`flex items-center gap-3 p-3 rounded-lg border ${
              isExpiringSoon 
                ? 'bg-yellow-50 border-yellow-200' 
                : 'bg-green-50 border-green-200'
            }`}
            data-testid="days-remaining"
          >
            <Clock className={`h-5 w-5 ${isExpiringSoon ? 'text-yellow-600' : 'text-green-600'}`} />
            <div>
              <p className={`font-medium ${isExpiringSoon ? 'text-yellow-800' : 'text-green-800'}`}>
                {status.days_remaining} days remaining
              </p>
              {isExpiringSoon && status.expiration_warning && (
                <p className="text-sm text-yellow-600" data-testid="expiration-warning">
                  {status.expiration_warning}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Grace Period Warning */}
        {isGracePeriod && status.grace_period && (
          <div 
            className="flex items-center gap-3 p-3 rounded-lg border bg-yellow-50 border-yellow-200"
            data-testid="grace-period-info"
          >
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            <div>
              <p className="font-medium text-yellow-800">
                Grace Period - {status.grace_period.days_remaining} days remaining
              </p>
              {status.grace_period.restrictions.length > 0 && (
                <p className="text-sm text-yellow-600">
                  Restrictions: {status.grace_period.restrictions.join(', ')}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Features */}
        {status.features && status.features.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Enabled Features</p>
            <div className="flex flex-wrap gap-1">
              {status.features.slice(0, 5).map((feature) => (
                <Badge key={feature} variant="outline" className="text-xs">
                  {feature}
                </Badge>
              ))}
              {status.features.length > 5 && (
                <Badge variant="outline" className="text-xs">
                  +{status.features.length - 5} more
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* Status Message */}
        {status.message && (
          <p className="text-sm text-muted-foreground">{status.message}</p>
        )}
      </CardContent>
    </Card>
  );
}

export default LicenseStatusCard;
