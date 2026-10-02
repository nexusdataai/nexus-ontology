/**
 * License Service
 * 
 * Provides methods for interacting with the License Management backend API.
 * Supports status checking, activation, deactivation, renewal, and audit logs.
 * 
 * API Base Path: /api/v1/license/
 */

import {
  LicenseStatusResponse,
  LicenseActivationRequest,
  LicenseActivationResponse,
  LicenseDeactivationRequest,
  LicenseDeactivationResponse,
  LicenseRenewalRequest,
  LicenseRenewalResponse,
  LicenseValidationResponse,
  AuditLogsParams,
  AuditLogsResponse,
  FeatureAccessResponse,
  LicenseError,
  LicenseErrorType,
} from '../types/license';

// ============================================================================
// Configuration Cache
// ============================================================================

interface LicenseConfig {
  baseUrl: string;
  timeout: number;
}

let cachedConfig: LicenseConfig | null = null;
let configLoadPromise: Promise<LicenseConfig | null> | null = null;

// Validation cache
interface ValidationCache {
  result: LicenseValidationResponse | null;
  timestamp: number;
}

const VALIDATION_CACHE_TTL = 5 * 60 * 1000; // 5 minutes
let validationCache: ValidationCache = { result: null, timestamp: 0 };

// Default API URL (empty = use nginx proxy to internal backend service)
const DEFAULT_API_URL = '';

// API base path for license endpoints
const LICENSE_API_PATH = '/api/v1/license';

// ============================================================================
// License Service Class
// ============================================================================

class LicenseService {
  private serverUrlOverride: string | null = null;

  /**
   * Set a manual override for the server URL
   */
  setServerUrlOverride(url: string | null): void {
    this.serverUrlOverride = url;
    if (url !== null) {
      console.log('🔧 License URL override set:', url);
    } else {
      console.log('🔧 License URL override cleared');
    }
  }

  /**
   * Get the current server URL override
   */
  getServerUrlOverride(): string | null {
    return this.serverUrlOverride;
  }


  /**
   * Load configuration from config.json
   */
  private async loadConfig(): Promise<LicenseConfig> {
    if (cachedConfig) {
      return cachedConfig;
    }

    if (configLoadPromise) {
      const result = await configLoadPromise;
      if (result) return result;
    }

    configLoadPromise = (async () => {
      try {
        const response = await fetch('/config.json', {
          cache: 'no-store',
          headers: { 'Accept': 'application/json' }
        });

        if (!response.ok) {
          console.warn('⚠️ Failed to fetch config.json for license settings');
          return null;
        }

        const config = await response.json();
        
        cachedConfig = {
          baseUrl: config.api?.baseUrl || DEFAULT_API_URL,
          timeout: config.api?.timeout || 30000
        };

        console.log('✅ License config loaded:', { baseUrl: cachedConfig.baseUrl });
        return cachedConfig;
      } catch (error) {
        console.error('❌ Error loading license config:', error);
        return null;
      }
    })();

    const result = await configLoadPromise;
    if (!result) {
      return {
        baseUrl: DEFAULT_API_URL,
        timeout: 30000
      };
    }
    return result;
  }

  /**
   * Get the server URL
   */
  async getServerUrl(): Promise<string> {
    if (this.serverUrlOverride) {
      return this.serverUrlOverride;
    }
    const config = await this.loadConfig();
    return config.baseUrl;
  }

  /**
   * Get the full API URL for a license endpoint
   */
  private async getApiUrl(endpoint: string): Promise<string> {
    const serverUrl = await this.getServerUrl();
    return `${serverUrl}${LICENSE_API_PATH}${endpoint}`;
  }

  /**
   * Create headers for API requests
   */
  private createHeaders(): Record<string, string> {
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
  }

  /**
   * Handle fetch errors and convert to structured error
   */
  private handleError(error: unknown, context: string): LicenseError {
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        return { 
          type: 'timeout', 
          message: `${context}: Request timed out`,
          retryable: true 
        };
      }
      if (error.message.includes('fetch') || error.message.includes('network') || error.message.includes('Failed to fetch')) {
        return { 
          type: 'network', 
          message: `${context}: Network error - cannot connect to server`,
          retryable: true 
        };
      }
      return { 
        type: 'unknown', 
        message: `${context}: ${error.message}`,
        retryable: false,
        details: { error } 
      };
    }
    return { 
      type: 'unknown', 
      message: `${context}: Unknown error occurred`,
      retryable: false,
      details: { error } 
    };
  }


  // ============================================================================
  // Status Methods
  // ============================================================================

  /**
   * Get current license status
   * GET /api/v1/license/status
   */
  async getStatus(): Promise<LicenseStatusResponse> {
    const url = await this.getApiUrl('/status');
    const config = await this.loadConfig();
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: this.createHeaders(),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw {
          type: 'api' as LicenseErrorType,
          message: errorData.detail?.message || `Failed to get status: ${response.status}`,
          code: errorData.detail?.error_code,
          retryable: response.status >= 500
        } as LicenseError;
      }

      const data = await response.json();
      return data as LicenseStatusResponse;
    } catch (error) {
      clearTimeout(timeoutId);
      if ((error as LicenseError).type) {
        throw error;
      }
      throw this.handleError(error, 'Get status failed');
    }
  }

  /**
   * Validate current license
   * GET /api/v1/license/validate
   */
  async validateLicense(useCache: boolean = true): Promise<LicenseValidationResponse> {
    // Check cache first
    if (useCache && validationCache.result) {
      const age = Date.now() - validationCache.timestamp;
      if (age < VALIDATION_CACHE_TTL) {
        console.log('📦 Using cached validation result');
        return validationCache.result;
      }
    }

    const url = await this.getApiUrl('/validate');
    const config = await this.loadConfig();
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: this.createHeaders(),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw {
          type: 'api' as LicenseErrorType,
          message: errorData.detail?.message || `Validation failed: ${response.status}`,
          code: errorData.detail?.error_code,
          retryable: response.status >= 500
        } as LicenseError;
      }

      const data = await response.json() as LicenseValidationResponse;
      
      // Update cache
      validationCache = {
        result: data,
        timestamp: Date.now()
      };

      return data;
    } catch (error) {
      clearTimeout(timeoutId);
      if ((error as LicenseError).type) {
        throw error;
      }
      throw this.handleError(error, 'Validation failed');
    }
  }


  // ============================================================================
  // Activation Methods
  // ============================================================================

  /**
   * Activate a license key
   * POST /api/v1/license/activate
   */
  async activateLicense(request: LicenseActivationRequest): Promise<LicenseActivationResponse> {
    const url = await this.getApiUrl('/activate');
    const config = await this.loadConfig();
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: this.createHeaders(),
        body: JSON.stringify(request),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const data = await response.json();

      if (!response.ok) {
        throw {
          type: 'api' as LicenseErrorType,
          message: data.detail?.message || data.message || `Activation failed: ${response.status}`,
          code: data.detail?.error_code || data.error_code,
          retryable: false,
          details: data.detail?.details || data.details
        } as LicenseError;
      }

      // Clear validation cache on successful activation
      this.clearValidationCache();

      return data as LicenseActivationResponse;
    } catch (error) {
      clearTimeout(timeoutId);
      if ((error as LicenseError).type) {
        throw error;
      }
      throw this.handleError(error, 'Activation failed');
    }
  }

  /**
   * Deactivate current license
   * POST /api/v1/license/deactivate
   */
  async deactivateLicense(request: LicenseDeactivationRequest): Promise<LicenseDeactivationResponse> {
    const url = await this.getApiUrl('/deactivate');
    const config = await this.loadConfig();
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: this.createHeaders(),
        body: JSON.stringify(request),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const data = await response.json();

      if (!response.ok) {
        throw {
          type: 'api' as LicenseErrorType,
          message: data.detail?.message || data.message || `Deactivation failed: ${response.status}`,
          code: data.detail?.error_code || data.error_code,
          retryable: false
        } as LicenseError;
      }

      // Clear validation cache on successful deactivation
      this.clearValidationCache();

      return data as LicenseDeactivationResponse;
    } catch (error) {
      clearTimeout(timeoutId);
      if ((error as LicenseError).type) {
        throw error;
      }
      throw this.handleError(error, 'Deactivation failed');
    }
  }

  /**
   * Renew license with renewal key
   * POST /api/v1/license/renew
   */
  async renewLicense(request: LicenseRenewalRequest): Promise<LicenseRenewalResponse> {
    const url = await this.getApiUrl('/renew');
    const config = await this.loadConfig();
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: this.createHeaders(),
        body: JSON.stringify(request),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const data = await response.json();

      if (!response.ok) {
        throw {
          type: 'api' as LicenseErrorType,
          message: data.detail?.message || data.message || `Renewal failed: ${response.status}`,
          code: data.detail?.error_code || data.error_code,
          retryable: false
        } as LicenseError;
      }

      // Clear validation cache on successful renewal
      this.clearValidationCache();

      return data as LicenseRenewalResponse;
    } catch (error) {
      clearTimeout(timeoutId);
      if ((error as LicenseError).type) {
        throw error;
      }
      throw this.handleError(error, 'Renewal failed');
    }
  }


  // ============================================================================
  // Audit Log Methods
  // ============================================================================

  /**
   * Get license audit logs
   * GET /api/v1/license/audit
   */
  async getAuditLogs(params: AuditLogsParams = {}): Promise<AuditLogsResponse> {
    const config = await this.loadConfig();
    
    // Build query params
    const queryParams = new URLSearchParams();
    if (params.start_date) queryParams.set('start_date', params.start_date);
    if (params.end_date) queryParams.set('end_date', params.end_date);
    if (params.limit) queryParams.set('limit', String(params.limit));
    if (params.offset) queryParams.set('offset', String(params.offset));

    const queryString = queryParams.toString();
    const url = await this.getApiUrl(`/audit${queryString ? `?${queryString}` : ''}`);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: this.createHeaders(),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw {
          type: 'api' as LicenseErrorType,
          message: errorData.detail?.message || `Failed to get audit logs: ${response.status}`,
          code: errorData.detail?.error_code,
          retryable: response.status >= 500
        } as LicenseError;
      }

      const data = await response.json();
      return data as AuditLogsResponse;
    } catch (error) {
      clearTimeout(timeoutId);
      if ((error as LicenseError).type) {
        throw error;
      }
      throw this.handleError(error, 'Get audit logs failed');
    }
  }

  // ============================================================================
  // Feature Access Methods
  // ============================================================================

  /**
   * Check feature access
   * GET /api/v1/license/features/{feature_id}
   */
  async checkFeatureAccess(featureId: string): Promise<FeatureAccessResponse> {
    const url = await this.getApiUrl(`/features/${featureId}`);
    const config = await this.loadConfig();
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: this.createHeaders(),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw {
          type: 'api' as LicenseErrorType,
          message: errorData.detail?.message || `Failed to check feature access: ${response.status}`,
          code: errorData.detail?.error_code,
          retryable: response.status >= 500
        } as LicenseError;
      }

      const data = await response.json();
      return data as FeatureAccessResponse;
    } catch (error) {
      clearTimeout(timeoutId);
      if ((error as LicenseError).type) {
        throw error;
      }
      throw this.handleError(error, 'Check feature access failed');
    }
  }

  // ============================================================================
  // Cache Management
  // ============================================================================

  /**
   * Clear validation cache
   */
  clearValidationCache(): void {
    validationCache = { result: null, timestamp: 0 };
    console.log('🗑️ Validation cache cleared');
  }

  /**
   * Clear all cached configuration
   */
  clearConfigCache(): void {
    cachedConfig = null;
    configLoadPromise = null;
    this.clearValidationCache();
  }

  /**
   * Check if validation cache is valid
   */
  isValidationCacheValid(): boolean {
    if (!validationCache.result) return false;
    const age = Date.now() - validationCache.timestamp;
    return age < VALIDATION_CACHE_TTL;
  }

  /**
   * Get validation cache TTL in milliseconds
   */
  getValidationCacheTTL(): number {
    return VALIDATION_CACHE_TTL;
  }
}

// Export singleton instance
export const licenseService = new LicenseService();
export default licenseService;
