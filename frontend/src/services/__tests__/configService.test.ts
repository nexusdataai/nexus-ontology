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
    it('should validate any partial config (backend auth mode)', () => {
      const validConfig: AppConfig = {
        api: { baseUrl: 'https://api.example.com', timeout: 30000 },
        deploymentMode: 'local',
        bypassAuth: false,
        environment: 'development',
        dataSource: 'api',
        enableFallback: true,
      };

      const result = validateConfig(validConfig);

      expect(result.valid).toBe(true);
      expect(result.missingFields).toHaveLength(0);
      expect(result.errors).toHaveLength(0);
    });

    it('should accept empty api.baseUrl (nginx proxy)', () => {
      const config: Partial<AppConfig> = {
        api: { baseUrl: '', timeout: 30000 },
        bypassAuth: true,
        environment: 'development',
      };

      const result = validateConfig(config);

      expect(result.valid).toBe(true);
      expect(result.missingFields).toHaveLength(0);
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
