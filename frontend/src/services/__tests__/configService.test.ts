/**
 * Unit Tests for Configuration Service
 * 
 * Tests for config service initialization, environment detection,
 * and config caching behavior.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  validateConfig,
  detectEnvironment,
  isLocalDevelopment,
  clearConfigCache,
  getConfigSource,
  type AppConfig,
} from '../configService';

// ============================================================================
// Test Setup
// ============================================================================

describe('Configuration Service Unit Tests', () => {
  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
    clearConfigCache();
    
    // Default to localhost
    Object.defineProperty(window, 'location', {
      value: {
        hostname: 'localhost',
        origin: 'http://localhost:5173',
      },
      writable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // Environment Detection Tests
  // ==========================================================================

  describe('Environment Detection', () => {
    it('should detect localhost as development', () => {
      Object.defineProperty(window, 'location', {
        value: { hostname: 'localhost', origin: 'http://localhost:5173' },
        writable: true,
      });
      
      expect(detectEnvironment()).toBe('development');
      expect(isLocalDevelopment()).toBe(true);
    });

    it('should detect 127.0.0.1 as development', () => {
      Object.defineProperty(window, 'location', {
        value: { hostname: '127.0.0.1', origin: 'http://127.0.0.1:5173' },
        writable: true,
      });
      
      expect(detectEnvironment()).toBe('development');
      expect(isLocalDevelopment()).toBe(true);
    });

    it('should detect staging hostname as staging', () => {
      Object.defineProperty(window, 'location', {
        value: { hostname: 'staging.example.com', origin: 'https://staging.example.com' },
        writable: true,
      });
      
      expect(detectEnvironment()).toBe('staging');
      expect(isLocalDevelopment()).toBe(false);
    });

    it('should detect dev hostname as staging', () => {
      Object.defineProperty(window, 'location', {
        value: { hostname: 'dev.example.com', origin: 'https://dev.example.com' },
        writable: true,
      });
      
      expect(detectEnvironment()).toBe('staging');
      expect(isLocalDevelopment()).toBe(false);
    });

    it('should detect production hostname as production', () => {
      Object.defineProperty(window, 'location', {
        value: { hostname: 'app.example.com', origin: 'https://app.example.com' },
        writable: true,
      });
      
      expect(detectEnvironment()).toBe('production');
      expect(isLocalDevelopment()).toBe(false);
    });
  });

  // ==========================================================================
  // Configuration Validation Tests
  // ==========================================================================

  describe('Configuration Validation', () => {
    it('should validate a complete valid config', () => {
      const validConfig: AppConfig = {
        api: {
          baseUrl: 'https://api.example.com',
          timeout: 30000,
        },
        cognito: {
          userPoolId: 'us-east-1_abc123XYZ',
          clientId: 'abcdef1234567890abcdef1234',
          domain: 'auth.example.com',
          region: 'us-east-1',
          redirectSignIn: 'http://localhost:5173/auth/callback',
          redirectSignOut: 'http://localhost:5173/login',
        },
        bypassAuth: false,
        environment: 'development',
      };

      const result = validateConfig(validConfig);
      
      expect(result.valid).toBe(true);
      expect(result.missingFields).toHaveLength(0);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect missing userPoolId', () => {
      const config: Partial<AppConfig> = {
        api: { baseUrl: 'https://api.example.com', timeout: 30000 },
        cognito: {
          userPoolId: '',
          clientId: 'abcdef1234567890abcdef1234',
          domain: 'auth.example.com',
          region: 'us-east-1',
          redirectSignIn: 'http://localhost:5173/auth/callback',
          redirectSignOut: 'http://localhost:5173/login',
        },
        bypassAuth: false,
        environment: 'development',
      };

      const result = validateConfig(config);
      
      expect(result.valid).toBe(false);
      expect(result.missingFields).toContain('cognito.userPoolId');
    });

    it('should detect missing clientId', () => {
      const config: Partial<AppConfig> = {
        api: { baseUrl: 'https://api.example.com', timeout: 30000 },
        cognito: {
          userPoolId: 'us-east-1_abc123XYZ',
          clientId: '',
          domain: 'auth.example.com',
          region: 'us-east-1',
          redirectSignIn: 'http://localhost:5173/auth/callback',
          redirectSignOut: 'http://localhost:5173/login',
        },
        bypassAuth: false,
        environment: 'development',
      };

      const result = validateConfig(config);
      
      expect(result.valid).toBe(false);
      expect(result.missingFields).toContain('cognito.clientId');
    });

    it('should detect missing api.baseUrl', () => {
      const config: Partial<AppConfig> = {
        api: { baseUrl: '', timeout: 30000 },
        cognito: {
          userPoolId: 'us-east-1_abc123XYZ',
          clientId: 'abcdef1234567890abcdef1234',
          domain: 'auth.example.com',
          region: 'us-east-1',
          redirectSignIn: 'http://localhost:5173/auth/callback',
          redirectSignOut: 'http://localhost:5173/login',
        },
        bypassAuth: false,
        environment: 'development',
      };

      const result = validateConfig(config);
      
      expect(result.valid).toBe(false);
      expect(result.missingFields).toContain('api.baseUrl');
    });

    it('should detect multiple missing fields', () => {
      const config: Partial<AppConfig> = {
        api: { baseUrl: '', timeout: 30000 },
        cognito: {
          userPoolId: '',
          clientId: '',
          domain: 'auth.example.com',
          region: 'us-east-1',
          redirectSignIn: 'http://localhost:5173/auth/callback',
          redirectSignOut: 'http://localhost:5173/login',
        },
        bypassAuth: false,
        environment: 'development',
      };

      const result = validateConfig(config);
      
      expect(result.valid).toBe(false);
      expect(result.missingFields).toContain('cognito.userPoolId');
      expect(result.missingFields).toContain('cognito.clientId');
      expect(result.missingFields).toContain('api.baseUrl');
      expect(result.missingFields).toHaveLength(3);
    });

    it('should detect invalid userPoolId format', () => {
      const config: Partial<AppConfig> = {
        api: { baseUrl: 'https://api.example.com', timeout: 30000 },
        cognito: {
          userPoolId: 'invalid-format-no-underscore',
          clientId: 'abcdef1234567890abcdef1234',
          domain: 'auth.example.com',
          region: 'us-east-1',
          redirectSignIn: 'http://localhost:5173/auth/callback',
          redirectSignOut: 'http://localhost:5173/login',
        },
        bypassAuth: false,
        environment: 'development',
      };

      const result = validateConfig(config);
      
      expect(result.errors.some(e => e.includes('userPoolId'))).toBe(true);
    });

    it('should handle undefined cognito config', () => {
      const config: Partial<AppConfig> = {
        api: { baseUrl: 'https://api.example.com', timeout: 30000 },
        bypassAuth: false,
        environment: 'development',
      };

      const result = validateConfig(config);
      
      expect(result.valid).toBe(false);
      expect(result.missingFields).toContain('cognito.userPoolId');
      expect(result.missingFields).toContain('cognito.clientId');
    });

    it('should handle undefined api config', () => {
      const config: Partial<AppConfig> = {
        cognito: {
          userPoolId: 'us-east-1_abc123XYZ',
          clientId: 'abcdef1234567890abcdef1234',
          domain: 'auth.example.com',
          region: 'us-east-1',
          redirectSignIn: 'http://localhost:5173/auth/callback',
          redirectSignOut: 'http://localhost:5173/login',
        },
        bypassAuth: false,
        environment: 'development',
      };

      const result = validateConfig(config);
      
      expect(result.valid).toBe(false);
      expect(result.missingFields).toContain('api.baseUrl');
    });
  });

  // ==========================================================================
  // Cache Management Tests
  // ==========================================================================

  describe('Cache Management', () => {
    it('should clear config cache', () => {
      // Initially no source
      expect(getConfigSource()).toBeNull();
      
      // Clear cache should not throw
      expect(() => clearConfigCache()).not.toThrow();
      
      // Source should still be null after clear
      expect(getConfigSource()).toBeNull();
    });
  });
});
