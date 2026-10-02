/**
 * License Service Tests
 * 
 * Unit tests for the license service including API calls, caching, and error handling.
 * Property 9: Validation Cache Behavior
 * Validates: Requirements 7.3
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { licenseService } from '../licenseService';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('LicenseService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    licenseService.clearConfigCache();
    
    // Mock config.json response
    mockFetch.mockImplementation((url: string) => {
      if (url === '/config.json') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            api: { baseUrl: 'http://test-api.com', timeout: 5000 }
          })
        });
      }
      return Promise.reject(new Error('Not mocked'));
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getStatus', () => {
    it('should fetch license status successfully', async () => {
      const mockStatus = {
        status: 'success',
        data: {
          license_status: 'active',
          license_id: 'LIC-12345',
          tier: 'professional',
          holder_name: 'Test Company',
          days_remaining: 30
        }
      };

      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/status')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockStatus)
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      const result = await licenseService.getStatus();
      expect(result.status).toBe('success');
      expect(result.data.license_status).toBe('active');
    });

    it('should handle API errors', async () => {
      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/status')) {
          return Promise.resolve({
            ok: false,
            status: 500,
            json: () => Promise.resolve({ detail: { message: 'Server error' } })
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      await expect(licenseService.getStatus()).rejects.toMatchObject({
        type: 'api',
        message: expect.stringContaining('Server error')
      });
    });

    it('should handle network errors', async () => {
      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        return Promise.reject(new Error('Failed to fetch'));
      });

      await expect(licenseService.getStatus()).rejects.toMatchObject({
        type: 'network',
        retryable: true
      });
    });
  });


  describe('activateLicense', () => {
    it('should activate license successfully', async () => {
      const mockResponse = {
        status: 'success',
        message: 'License activated',
        data: {
          license_id: 'LIC-12345',
          tier: 'professional',
          holder_name: 'Test Company',
          days_remaining: 365
        }
      };

      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/activate')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockResponse)
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      const result = await licenseService.activateLicense({
        license_key: 'v1.PRO.20251231.HOLDER123.ALL.signature'
      });

      expect(result.status).toBe('success');
      expect(result.data?.license_id).toBe('LIC-12345');
    });

    it('should handle invalid license key error', async () => {
      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/activate')) {
          return Promise.resolve({
            ok: false,
            status: 400,
            json: () => Promise.resolve({
              detail: { message: 'Invalid license key format', error_code: 'INVALID_FORMAT' }
            })
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      await expect(licenseService.activateLicense({
        license_key: 'invalid-key'
      })).rejects.toMatchObject({
        type: 'api',
        code: 'INVALID_FORMAT'
      });
    });

    it('should clear validation cache after successful activation', async () => {
      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/activate')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'success', message: 'Activated' })
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      // Activation should clear cache
      await licenseService.activateLicense({ license_key: 'test-key' });
      expect(licenseService.isValidationCacheValid()).toBe(false);
    });
  });

  describe('deactivateLicense', () => {
    it('should deactivate license successfully', async () => {
      const mockResponse = {
        status: 'success',
        message: 'License deactivated',
        data: {
          deactivated_at: '2025-01-01T00:00:00Z',
          previous_license_id: 'LIC-12345',
          can_reactivate: true
        }
      };

      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/deactivate')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockResponse)
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      const result = await licenseService.deactivateLicense({
        reason: 'Moving to new instance',
        confirm: true
      });

      expect(result.status).toBe('success');
      expect(result.data?.can_reactivate).toBe(true);
    });
  });

  describe('renewLicense', () => {
    it('should renew license successfully', async () => {
      const mockResponse = {
        status: 'success',
        message: 'License renewed',
        data: {
          license_id: 'LIC-12345',
          previous_expiration: '2025-01-01',
          new_expiration: '2026-01-01',
          tier: 'professional',
          tier_changed: false
        }
      };

      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/renew')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockResponse)
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      const result = await licenseService.renewLicense({
        renewal_key: 'renewal-key-123'
      });

      expect(result.status).toBe('success');
      expect(result.data?.new_expiration).toBe('2026-01-01');
    });
  });


  describe('validateLicense - Property 9: Validation Cache Behavior', () => {
    /**
     * Property 9: Validation Cache Behavior
     * For any sequence of getStatus() calls within the cache TTL period,
     * only the first call SHALL result in an API request; subsequent calls
     * SHALL return cached data.
     * Validates: Requirements 7.3
     */
    
    it('should cache validation results and reuse them', async () => {
      const mockValidation = {
        status: 'success',
        data: {
          is_valid: true,
          license_status: 'active',
          license_id: 'LIC-12345',
          tier: 'professional'
        }
      };

      let apiCallCount = 0;
      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/validate')) {
          apiCallCount++;
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockValidation)
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      // First call should hit API
      const result1 = await licenseService.validateLicense(true);
      expect(result1.data.is_valid).toBe(true);
      expect(apiCallCount).toBe(1);

      // Second call should use cache
      const result2 = await licenseService.validateLicense(true);
      expect(result2.data.is_valid).toBe(true);
      expect(apiCallCount).toBe(1); // Still 1, cache was used

      // Third call should also use cache
      const result3 = await licenseService.validateLicense(true);
      expect(result3.data.is_valid).toBe(true);
      expect(apiCallCount).toBe(1); // Still 1
    });

    it('should bypass cache when useCache is false', async () => {
      const mockValidation = {
        status: 'success',
        data: { is_valid: true, license_status: 'active' }
      };

      let apiCallCount = 0;
      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/validate')) {
          apiCallCount++;
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockValidation)
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      // First call
      await licenseService.validateLicense(true);
      expect(apiCallCount).toBe(1);

      // Second call with useCache=false should hit API
      await licenseService.validateLicense(false);
      expect(apiCallCount).toBe(2);
    });

    it('should clear cache and make new API call after clearValidationCache', async () => {
      const mockValidation = {
        status: 'success',
        data: { is_valid: true, license_status: 'active' }
      };

      let apiCallCount = 0;
      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/validate')) {
          apiCallCount++;
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockValidation)
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      // First call
      await licenseService.validateLicense(true);
      expect(apiCallCount).toBe(1);

      // Clear cache
      licenseService.clearValidationCache();
      expect(licenseService.isValidationCacheValid()).toBe(false);

      // Next call should hit API again
      await licenseService.validateLicense(true);
      expect(apiCallCount).toBe(2);
    });
  });

  describe('getAuditLogs', () => {
    it('should fetch audit logs with pagination', async () => {
      const mockLogs = {
        status: 'success',
        data: [
          { event_id: 'EVT-1', event_type: 'license_activated', result: 'success' },
          { event_id: 'EVT-2', event_type: 'license_validated', result: 'success' }
        ]
      };

      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/audit')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockLogs)
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      const result = await licenseService.getAuditLogs({ limit: 10, offset: 0 });
      expect(result.status).toBe('success');
      expect(result.data).toHaveLength(2);
    });
  });

  describe('checkFeatureAccess', () => {
    it('should check feature access', async () => {
      const mockAccess = {
        status: 'success',
        data: {
          feature_id: 'advanced-analytics',
          is_allowed: true,
          required_tier: 'professional',
          current_tier: 'enterprise'
        }
      };

      mockFetch.mockImplementation((url: string) => {
        if (url === '/config.json') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ api: { baseUrl: 'http://test-api.com' } })
          });
        }
        if (url.includes('/features/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockAccess)
          });
        }
        return Promise.reject(new Error('Not mocked'));
      });

      const result = await licenseService.checkFeatureAccess('advanced-analytics');
      expect(result.data.is_allowed).toBe(true);
    });
  });

  describe('URL override', () => {
    it('should use override URL when set', async () => {
      licenseService.setServerUrlOverride('http://custom-api.com');
      
      const url = await licenseService.getServerUrl();
      expect(url).toBe('http://custom-api.com');
      
      // Clean up
      licenseService.setServerUrlOverride(null);
    });

    it('should use config URL when override is cleared', async () => {
      licenseService.setServerUrlOverride('http://custom-api.com');
      licenseService.setServerUrlOverride(null);
      
      const url = await licenseService.getServerUrl();
      expect(url).toBe('http://test-api.com');
    });
  });
});
