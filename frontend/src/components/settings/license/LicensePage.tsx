/**
 * LicensePage Component
 * 
 * Main container component that orchestrates all license management functionality.
 * Manages state for status, loading, errors, and coordinates child components.
 * 
 * Requirements: 1.1, 7.1, 8.1, 8.2, 8.3, 8.4
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { 
  Key, 
  RefreshCw, 
  History, 
  Sparkles,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { licenseService } from '@/services/licenseService';
import { 
  LicenseStatusData, 
  LicenseError,
  AuditLogEntry,
  FeatureAccessItem
} from '@/types/license';

// Import child components
import { LicenseStatusCard } from './LicenseStatusCard';
import { LicenseActivationForm } from './LicenseActivationForm';
import { LicenseRenewalForm } from './LicenseRenewalForm';
import { LicenseDeactivateDialog } from './LicenseDeactivateDialog';
import { AuditLogTable } from './AuditLogTable';
import { FeatureAccessList } from './FeatureAccessList';

// ============================================================================
// Constants
// ============================================================================

const PAGE_SIZE = 10;

// Sample features for demo (in production, these would come from backend)
const SAMPLE_FEATURES: FeatureAccessItem[] = [
  {
    feature_id: 'basic_deployment',
    feature_name: 'Basic Deployment',
    description: 'Deploy single-instance applications',
    required_tier: 'basic',
    is_allowed: true
  },
  {
    feature_id: 'multi_env',
    feature_name: 'Multi-Environment Support',
    description: 'Deploy to dev, staging, and production environments',
    required_tier: 'professional',
    is_allowed: false
  },
  {
    feature_id: 'advanced_monitoring',
    feature_name: 'Advanced Monitoring',
    description: 'Real-time metrics and alerting',
    required_tier: 'professional',
    is_allowed: false
  },
  {
    feature_id: 'sso_integration',
    feature_name: 'SSO Integration',
    description: 'SAML 2.0 and OAuth 2.0 single sign-on',
    required_tier: 'enterprise',
    is_allowed: false
  },
  {
    feature_id: 'audit_compliance',
    feature_name: 'Audit & Compliance',
    description: 'Detailed audit logs and compliance reporting',
    required_tier: 'enterprise',
    is_allowed: false
  }
];

// ============================================================================
// Main Component
// ============================================================================

export function LicensePage() {
  // Status state
  const [status, setStatus] = useState<LicenseStatusData | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Activation state
  const [isActivating, setIsActivating] = useState(false);
  const [activationError, setActivationError] = useState<LicenseError | null>(null);

  // Renewal state
  const [isRenewing, setIsRenewing] = useState(false);
  const [renewalError, setRenewalError] = useState<LicenseError | null>(null);

  // Deactivation state
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false);
  const [isDeactivating, setIsDeactivating] = useState(false);

  // Audit log state
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);
  const [totalLogCount, setTotalLogCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [dateRange, setDateRange] = useState<{ start: Date | null; end: Date | null }>({
    start: null,
    end: null
  });

  // Features state
  const [features] = useState<FeatureAccessItem[]>(SAMPLE_FEATURES);
  const [isLoadingFeatures] = useState(false);

  // Active tab
  const [activeTab, setActiveTab] = useState('status');

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const fetchStatus = useCallback(async () => {
    setIsLoadingStatus(true);
    setStatusError(null);
    
    try {
      const response = await licenseService.getStatus();
      setStatus(response.data);
    } catch (error) {
      const licenseError = error as LicenseError;
      setStatusError(licenseError.message || 'Failed to fetch license status');
      setStatus(null);
    } finally {
      setIsLoadingStatus(false);
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    setIsLoadingLogs(true);
    
    try {
      const response = await licenseService.getAuditLogs({
        start_date: dateRange.start?.toISOString().split('T')[0],
        end_date: dateRange.end?.toISOString().split('T')[0],
        limit: PAGE_SIZE,
        offset: (currentPage - 1) * PAGE_SIZE
      });
      setAuditLogs(response.data);
      // Estimate total count (backend should return this)
      setTotalLogCount(response.data.length < PAGE_SIZE ? 
        (currentPage - 1) * PAGE_SIZE + response.data.length : 
        currentPage * PAGE_SIZE + 1
      );
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
      setAuditLogs([]);
    } finally {
      setIsLoadingLogs(false);
    }
  }, [currentPage, dateRange]);

  // Initial load
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Fetch audit logs when tab changes or pagination/filter changes
  useEffect(() => {
    if (activeTab === 'audit') {
      fetchAuditLogs();
    }
  }, [activeTab, fetchAuditLogs]);

  // ============================================================================
  // Action Handlers
  // ============================================================================

  const handleActivate = async (licenseKey: string, instanceId?: string) => {
    setIsActivating(true);
    setActivationError(null);
    
    try {
      await licenseService.activateLicense({
        license_key: licenseKey,
        instance_id: instanceId
      });
      // Refresh status after activation
      await fetchStatus();
    } catch (error) {
      const licenseError = error as LicenseError;
      setActivationError(licenseError);
      throw error;
    } finally {
      setIsActivating(false);
    }
  };

  const handleRenew = async (renewalKey: string) => {
    setIsRenewing(true);
    setRenewalError(null);
    
    try {
      await licenseService.renewLicense({ renewal_key: renewalKey });
      // Refresh status after renewal
      await fetchStatus();
    } catch (error) {
      const licenseError = error as LicenseError;
      setRenewalError(licenseError);
      throw error;
    } finally {
      setIsRenewing(false);
    }
  };

  const handleDeactivate = async (reason: string) => {
    setIsDeactivating(true);
    
    try {
      await licenseService.deactivateLicense({
        reason,
        confirm: true
      });
      setShowDeactivateDialog(false);
      // Refresh status after deactivation
      await fetchStatus();
    } catch (error) {
      throw error;
    } finally {
      setIsDeactivating(false);
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleDateRangeChange = (start: Date | null, end: Date | null) => {
    setDateRange({ start, end });
    setCurrentPage(1); // Reset to first page on filter change
  };

  // ============================================================================
  // Computed Values
  // ============================================================================

  const isLicenseActive = status?.license_status === 'active' || 
                          status?.license_status === 'grace_period';

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="space-y-6" data-testid="license-page">
      {/* Header with Refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Key className="h-6 w-6" />
            License Management
          </h2>
          <p className="text-gray-500 mt-1">
            Manage your software license and view feature access
          </p>
        </div>
        <Button
          variant="outline"
          onClick={fetchStatus}
          disabled={isLoadingStatus}
          data-testid="refresh-button"
        >
          {isLoadingStatus ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4 mr-2" />
          )}
          Refresh
        </Button>
      </div>

      {/* Network Error Banner */}
      {statusError && (
        <div 
          className="flex items-center justify-between p-4 bg-red-50 rounded-lg border border-red-200"
          data-testid="network-error-banner"
        >
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <div>
              <p className="font-medium text-red-800">Connection Error</p>
              <p className="text-sm text-red-600">{statusError}</p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchStatus}
            data-testid="retry-button"
          >
            Retry
          </Button>
        </div>
      )}

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="status" className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            Status & Actions
          </TabsTrigger>
          <TabsTrigger value="audit" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            Audit Log
          </TabsTrigger>
          <TabsTrigger value="features" className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Features
          </TabsTrigger>
        </TabsList>

        {/* Status & Actions Tab */}
        <TabsContent value="status" className="space-y-6 mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Status Card */}
            <LicenseStatusCard
              status={status}
              isLoading={isLoadingStatus}
              error={statusError}
              onRefresh={fetchStatus}
            />

            {/* Activation or Renewal Form */}
            <div className="space-y-6">
              <LicenseActivationForm
                onActivate={handleActivate}
                isActivating={isActivating}
                error={activationError}
                isLicenseActive={isLicenseActive}
              />

              <LicenseRenewalForm
                onRenew={handleRenew}
                isRenewing={isRenewing}
                error={renewalError}
                currentExpiration={status?.expires_at || null}
                isLicenseActive={isLicenseActive}
              />
            </div>
          </div>

          {/* Deactivate Button */}
          {isLicenseActive && (
            <div className="flex justify-end">
              <Button
                variant="outline"
                className="text-red-600 border-red-200 hover:bg-red-50"
                onClick={() => setShowDeactivateDialog(true)}
                data-testid="deactivate-button"
              >
                Deactivate License
              </Button>
            </div>
          )}
        </TabsContent>

        {/* Audit Log Tab */}
        <TabsContent value="audit" className="mt-6">
          <AuditLogTable
            logs={auditLogs}
            isLoading={isLoadingLogs}
            totalCount={totalLogCount}
            pageSize={PAGE_SIZE}
            currentPage={currentPage}
            onPageChange={handlePageChange}
            onDateRangeChange={handleDateRangeChange}
          />
        </TabsContent>

        {/* Features Tab */}
        <TabsContent value="features" className="mt-6">
          <FeatureAccessList
            currentTier={status?.tier || null}
            features={features}
            isLoading={isLoadingFeatures}
          />
        </TabsContent>
      </Tabs>

      {/* Deactivate Dialog */}
      <LicenseDeactivateDialog
        isOpen={showDeactivateDialog}
        onClose={() => setShowDeactivateDialog(false)}
        onConfirm={handleDeactivate}
        isDeactivating={isDeactivating}
        licenseId={status?.license_id || null}
      />
    </div>
  );
}

export default LicensePage;
