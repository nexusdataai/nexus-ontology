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
import { Icon } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';
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
      {/* Heading */}
      <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h2 className="text-xl font-medium tracking-tight text-foreground">License</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            The plan this installation runs on, when it ends and what it includes.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={fetchStatus}
          disabled={isLoadingStatus}
          data-testid="refresh-button"
        >
          <Icon name="refresh" className={cn('h-3.5 w-3.5', isLoadingStatus && 'animate-spin')} />
          Refresh
        </Button>
      </header>

      {/* Summary. Also shows the connection error, with retry, when the status cannot be read. */}
      <LicenseStatusCard
        status={status}
        isLoading={isLoadingStatus}
        error={statusError}
        onRefresh={fetchStatus}
      />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="line">
          <TabsTrigger value="status">Overview</TabsTrigger>
          <TabsTrigger value="features">Features</TabsTrigger>
          <TabsTrigger value="audit">History</TabsTrigger>
        </TabsList>

        {/* Overview: renew, activate, deactivate */}
        <TabsContent value="status" className="mt-0">
          {isLicenseActive && (
            <Block title="Renew" description="Extend the current license with a renewal key from your account manager.">
              <LicenseRenewalForm
                onRenew={handleRenew}
                isRenewing={isRenewing}
                error={renewalError}
                currentExpiration={status?.expires_at || null}
                isLicenseActive={isLicenseActive}
              />
            </Block>
          )}

          {isLicenseActive ? (
            <Block title="Deactivate or replace" description="Take the license off this installation, for example to move it or to activate a different one.">
              <LicenseActivationForm
                onActivate={handleActivate}
                isActivating={isActivating}
                error={activationError}
                isLicenseActive={isLicenseActive}
              />
              <Button
                variant="outline"
                className="mt-4 text-destructive hover:text-destructive"
                onClick={() => setShowDeactivateDialog(true)}
                data-testid="deactivate-button"
              >
                Deactivate license
              </Button>
            </Block>
          ) : (
            <Block title="Activate" description="Enter the license key you received to switch on the licensed features.">
              <LicenseActivationForm
                onActivate={handleActivate}
                isActivating={isActivating}
                error={activationError}
                isLicenseActive={isLicenseActive}
              />
            </Block>
          )}
        </TabsContent>

        {/* Features */}
        <TabsContent value="features" className="mt-6">
          <FeatureAccessList
            currentTier={status?.tier || null}
            features={features}
            isLoading={isLoadingFeatures}
          />
        </TabsContent>

        {/* History */}
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

/** One section of the overview: what it is on the left, the controls on the right. */
function Block({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-x-10 gap-y-4 border-b border-border py-7 last:border-b-0 xl:grid-cols-[240px_minmax(0,1fr)]">
      <div>
        <h3 className="text-md font-medium text-foreground">{title}</h3>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

export default LicensePage;
