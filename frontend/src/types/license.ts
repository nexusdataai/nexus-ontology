/**
 * License Management Types
 * 
 * TypeScript interfaces and types for license management functionality.
 * Matches the backend License API models.
 */

// ============================================================================
// Enums
// ============================================================================

export type LicenseStatus = 
  | 'active' 
  | 'expired' 
  | 'grace_period' 
  | 'revoked' 
  | 'deactivated' 
  | 'not_activated';

export type LicenseTier = 'basic' | 'professional' | 'enterprise';

export type LicenseEventType = 
  | 'license_activated'
  | 'license_validated'
  | 'license_validation_failed'
  | 'license_deactivated'
  | 'license_renewed'
  | 'license_expired'
  | 'grace_period_started'
  | 'grace_period_ended'
  | 'feature_access_denied'
  | 'feature_access_granted';

// ============================================================================
// Grace Period Info
// ============================================================================

export interface GracePeriodInfo {
  is_in_grace_period: boolean;
  grace_period_ends_at: string | null;
  days_remaining: number | null;
  restrictions: string[];
}

// ============================================================================
// License Status Data
// ============================================================================

export interface LicenseStatusData {
  license_status: LicenseStatus;
  license_id: string | null;
  tier: LicenseTier | null;
  holder_name: string | null;
  activated_at: string | null;
  expires_at: string | null;
  days_remaining: number | null;
  is_expiring_soon: boolean;
  expiration_warning: string | null;
  features: string[];
  grace_period: GracePeriodInfo | null;
  usage_stats: Record<string, number> | null;
  message: string | null;
  activation_instructions: string | null;
}


// ============================================================================
// Activation Types
// ============================================================================

export interface LicenseActivationRequest {
  license_key: string;
  instance_id?: string;
  metadata?: Record<string, unknown>;
}

export interface LicenseActivationData {
  license_id: string;
  tier: LicenseTier;
  holder_name: string;
  holder_id: string;
  activated_at: string;
  expires_at: string;
  days_remaining: number;
  features: string[];
  is_active: boolean;
}

export interface LicenseActivationResponse {
  status: 'success' | 'error';
  message: string;
  data?: LicenseActivationData;
  error_code?: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// Deactivation Types
// ============================================================================

export interface LicenseDeactivationRequest {
  reason: string;
  confirm: boolean;
}

export interface LicenseDeactivationData {
  deactivated_at: string;
  previous_license_id: string;
  can_reactivate: boolean;
}

export interface LicenseDeactivationResponse {
  status: 'success' | 'error';
  message: string;
  data?: LicenseDeactivationData;
  error_code?: string;
}

// ============================================================================
// Renewal Types
// ============================================================================

export interface LicenseRenewalRequest {
  renewal_key: string;
}

export interface LicenseRenewalData {
  license_id: string;
  previous_expiration: string;
  new_expiration: string;
  tier: LicenseTier;
  tier_changed: boolean;
  features: string[];
}

export interface LicenseRenewalResponse {
  status: 'success' | 'error';
  message: string;
  data?: LicenseRenewalData;
  error_code?: string;
}

// ============================================================================
// Status Response
// ============================================================================

export interface LicenseStatusResponse {
  status: 'success' | 'error';
  data: LicenseStatusData;
}

// ============================================================================
// Validation Types
// ============================================================================

export interface LicenseValidationResult {
  is_valid: boolean;
  license_status: LicenseStatus;
  license_id: string | null;
  tier: LicenseTier | null;
  error_code: string | null;
  message: string | null;
  is_in_grace_period: boolean;
  can_write: boolean;
}

export interface LicenseValidationResponse {
  status: 'success' | 'error';
  data: LicenseValidationResult;
}


// ============================================================================
// Audit Log Types
// ============================================================================

export interface AuditLogEntry {
  event_id: string;
  timestamp: string;
  event_type: LicenseEventType;
  license_id: string | null;
  details: Record<string, unknown>;
  result: 'success' | 'failure';
  ip_address: string | null;
  user_agent: string | null;
}

export interface AuditLogsParams {
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

export interface AuditLogsResponse {
  status: 'success' | 'error';
  data: AuditLogEntry[];
}

// ============================================================================
// Feature Access Types
// ============================================================================

export interface FeatureAccessData {
  feature_id: string;
  is_allowed: boolean;
  required_tier: LicenseTier;
  current_tier: LicenseTier | null;
  upgrade_message: string | null;
}

export interface FeatureAccessResponse {
  status: 'success' | 'error';
  data: FeatureAccessData;
}

export interface FeatureAccessItem {
  feature_id: string;
  feature_name: string;
  description: string;
  required_tier: LicenseTier;
  is_allowed: boolean;
}

// ============================================================================
// Error Types
// ============================================================================

export type LicenseErrorType = 
  | 'network'
  | 'auth'
  | 'validation'
  | 'api'
  | 'timeout'
  | 'unknown';

export interface LicenseError {
  type: LicenseErrorType;
  message: string;
  code?: string;
  details?: Record<string, unknown>;
  retryable: boolean;
}

// ============================================================================
// Component Props Interfaces
// ============================================================================

export interface LicenseStatusCardProps {
  status: LicenseStatusData | null;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export interface LicenseActivationFormProps {
  onActivate: (key: string, instanceId?: string) => Promise<void>;
  isActivating: boolean;
  error: LicenseError | null;
  isLicenseActive: boolean;
}

export interface LicenseRenewalFormProps {
  onRenew: (renewalKey: string) => Promise<void>;
  isRenewing: boolean;
  error: LicenseError | null;
  currentExpiration: string | null;
  isLicenseActive: boolean;
}

export interface LicenseDeactivateDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void>;
  isDeactivating: boolean;
  licenseId: string | null;
}

export interface AuditLogTableProps {
  logs: AuditLogEntry[];
  isLoading: boolean;
  totalCount: number;
  pageSize: number;
  currentPage: number;
  onPageChange: (page: number) => void;
  onDateRangeChange: (start: Date | null, end: Date | null) => void;
}

export interface FeatureAccessListProps {
  currentTier: LicenseTier | null;
  features: FeatureAccessItem[];
  isLoading: boolean;
}

// ============================================================================
// Constants
// ============================================================================

export const STATUS_COLORS: Record<LicenseStatus, string> = {
  active: 'green',
  expired: 'red',
  grace_period: 'yellow',
  not_activated: 'gray',
  revoked: 'red',
  deactivated: 'gray',
};

export const STATUS_LABELS: Record<LicenseStatus, string> = {
  active: 'Active',
  expired: 'Expired',
  grace_period: 'Grace Period',
  not_activated: 'Not Activated',
  revoked: 'Revoked',
  deactivated: 'Deactivated',
};

export const TIER_LEVELS: Record<LicenseTier, number> = {
  basic: 1,
  professional: 2,
  enterprise: 3,
};

export const TIER_LABELS: Record<LicenseTier, string> = {
  basic: 'Basic',
  professional: 'Professional',
  enterprise: 'Enterprise',
};

export const EVENT_TYPE_LABELS: Record<LicenseEventType, string> = {
  license_activated: 'License Activated',
  license_validated: 'License Validated',
  license_validation_failed: 'Validation Failed',
  license_deactivated: 'License Deactivated',
  license_renewed: 'License Renewed',
  license_expired: 'License Expired',
  grace_period_started: 'Grace Period Started',
  grace_period_ended: 'Grace Period Ended',
  feature_access_denied: 'Feature Access Denied',
  feature_access_granted: 'Feature Access Granted',
};

// License key format: v1.TIER.YYYYMMDD.HOLDER_ID.FEATURES.SIGNATURE
export const LICENSE_KEY_PATTERN = /^v1\.(BAS|PRO|ENT)\.\d{8}\.[A-Z0-9]+\.[A-Z0-9]+\.[A-Za-z0-9+/=]+$/;

/**
 * Validate license key format
 */
export function isValidLicenseKeyFormat(key: string): boolean {
  return LICENSE_KEY_PATTERN.test(key);
}

/**
 * Compare license tiers
 */
export function compareTiers(current: LicenseTier | null, required: LicenseTier): boolean {
  if (!current) return false;
  return TIER_LEVELS[current] >= TIER_LEVELS[required];
}
