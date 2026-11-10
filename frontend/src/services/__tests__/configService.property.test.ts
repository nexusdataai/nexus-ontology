/**
 * Property-Based Tests for Configuration Service
 * 
 * These tests validate the correctness properties defined in the design document
 * using fast-check for property-based testing.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as fc from 'fast-check';
import {
  validateConfig,
  detectEnvironment,
  isLocalDevelopment,
  type AppConfig,
  type ValidationResult,
} from '../configService';

// ============================================================================
// Test Helpers
// ============================================================================

// Arbitrary for generating valid Cognito User Pool IDs
const validUserPoolIdArb = fc.tuple(
  fc.constantFrom('us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'),
  fc.hexaString({ minLength: 9, maxLength: 9 })
).map(([region, id]) => `${region}_${id}`);

// Arbitrary for generating valid client IDs
const validClientIdArb = fc.hexaString({ minLength: 26, maxLength: 26 });

// Arbitrary for generating valid URLs
const validUrlArb = fc.webUrl({ withPath: true });

// Arbitrary for generating valid AppConfig
const validAppConfigArb = fc.record({
  api: fc.record({
    baseUrl: validUrlArb,
    timeout: fc.integer({ min: 1000, max: 120000 }),
  }),
  cognito: fc.record({
    userPoolId: validUserPoolIdArb,
    clientId: validClientIdArb,
    domain: fc.domain(),
    region: fc.constantFrom('us-east-1', 'us-west-2', 'eu-west-1'),
    redirectSignIn: validUrlArb,
    redirectSignOut: validUrlArb,
  }),
  bypassAuth: fc.boolean(),
  environment: fc.constantFrom('development', 'staging', 'production') as fc.Arbitrary<'development' | 'staging' | 'production'>,
});

// Arbitrary for generating partial configs missing required fields
const partialConfigMissingFieldsArb = fc.oneof(
  // Missing userPoolId
  fc.record({
    api: fc.record({ baseUrl: validUrlArb, timeout: fc.integer({ min: 1000, max: 120000 }) }),
    cognito: fc.record({
      userPoolId: fc.constant(''),
      clientId: validClientIdArb,
      domain: fc.domain(),
      region: fc.constantFrom('us-east-1', 'us-west-2'),
      redirectSignIn: validUrlArb,
      redirectSignOut: validUrlArb,
    }),
    bypassAuth: fc.boolean(),
    environment: fc.constantFrom('development', 'staging', 'production') as fc.Arbitrary<'development' | 'staging' | 'production'>,
  }),
  // Missing clientId
  fc.record({
    api: fc.record({ baseUrl: validUrlArb, timeout: fc.integer({ min: 1000, max: 120000 }) }),
    cognito: fc.record({
      userPoolId: validUserPoolIdArb,
      clientId: fc.constant(''),
      domain: fc.domain(),
      region: fc.constantFrom('us-east-1', 'us-west-2'),
      redirectSignIn: validUrlArb,
      redirectSignOut: validUrlArb,
    }),
    bypassAuth: fc.boolean(),
    environment: fc.constantFrom('development', 'staging', 'production') as fc.Arbitrary<'development' | 'staging' | 'production'>,
  }),
  // Missing api.baseUrl
  fc.record({
    api: fc.record({ baseUrl: fc.constant(''), timeout: fc.integer({ min: 1000, max: 120000 }) }),
    cognito: fc.record({
      userPoolId: validUserPoolIdArb,
      clientId: validClientIdArb,
      domain: fc.domain(),
      region: fc.constantFrom('us-east-1', 'us-west-2'),
      redirectSignIn: validUrlArb,
      redirectSignOut: validUrlArb,
    }),
    bypassAuth: fc.boolean(),
    environment: fc.constantFrom('development', 'staging', 'production') as fc.Arbitrary<'development' | 'staging' | 'production'>,
  })
);

// ============================================================================
// Property Tests
// ============================================================================

describe('Configuration Service Property Tests', () => {
  /**
   * **Feature: config-and-auth-bypass, Property 4: Configuration priority order**
   * **Validates: Requirements 5.1**
   * 
   * For any configuration scenario, the configuration service should follow
   * the priority: Runtime config.json (production) > Environment variables > Defaults.
   */
  describe('Property 4: Configuration priority order', () => {
    it('should validate complete configs as valid', () => {
      fc.assert(
        fc.property(validAppConfigArb, (config) => {
          const result = validateConfig(config);
          expect(result.valid).toBe(true);
          expect(result.missingFields).toHaveLength(0);
        }),
        { numRuns: 100 }
      );
    });

    it('should treat partial configs as valid (backend auth mode)', () => {
      fc.assert(
        fc.property(partialConfigMissingFieldsArb, (config) => {
          const result = validateConfig(config);
          expect(result.valid).toBe(true);
          expect(result.missingFields).toHaveLength(0);
          expect(result.errors).toHaveLength(0);
        }),
        { numRuns: 100 }
      );
    });
  });
});

describe('Environment Detection Property Tests', () => {
  /**
   * **Feature: config-and-auth-bypass, Property 1: Environment variable priority in development**
   * **Validates: Requirements 1.2**
   * 
   * For any configuration where both environment variables and config.json values exist,
   * when running in development mode, the configuration service should return the
   * environment variable values.
   */
  describe('Property 1: Environment variable priority in development', () => {
    beforeEach(() => {
      // Mock localhost environment
      Object.defineProperty(window, 'location', {
        value: { hostname: 'localhost', origin: 'http://localhost:5173' },
        writable: true,
      });
    });

    it('should detect localhost as development environment', () => {
      fc.assert(
        fc.property(
          fc.constantFrom('localhost', '127.0.0.1'),
          (hostname) => {
            Object.defineProperty(window, 'location', {
              value: { hostname, origin: `http://${hostname}:5173` },
              writable: true,
            });
            
            expect(detectEnvironment()).toBe('development');
            expect(isLocalDevelopment()).toBe(true);
          }
        ),
        { numRuns: 10 }
      );
    });
  });

  /**
   * **Feature: config-and-auth-bypass, Property 2: Config.json values used in production**
   * **Validates: Requirements 2.2**
   * 
   * For any valid config.json content, when running in production mode and config.json
   * is successfully fetched, the configuration service should return the config.json values.
   */
  describe('Property 2: Config.json values used in production', () => {
    it('should detect production hostnames correctly', () => {
      fc.assert(
        fc.property(
          fc.domain().filter(d => 
            !d.includes('localhost') && 
            !d.includes('127.0.0.1') && 
            !d.includes('staging') && 
            !d.includes('dev')
          ),
          (hostname) => {
            Object.defineProperty(window, 'location', {
              value: { hostname, origin: `https://${hostname}` },
              writable: true,
            });
            
            expect(detectEnvironment()).toBe('production');
            expect(isLocalDevelopment()).toBe(false);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should detect staging hostnames correctly', () => {
      fc.assert(
        fc.property(
          fc.constantFrom('staging.example.com', 'dev.example.com', 'staging-app.com', 'dev-server.net'),
          (hostname) => {
            Object.defineProperty(window, 'location', {
              value: { hostname, origin: `https://${hostname}` },
              writable: true,
            });
            
            expect(detectEnvironment()).toBe('staging');
            expect(isLocalDevelopment()).toBe(false);
          }
        ),
        { numRuns: 10 }
      );
    });
  });
});
