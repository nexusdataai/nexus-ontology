/**
 * LicenseStatusCard Tests
 * 
 * Property 1: Status Indicator Mapping
 * Property 8: Days Remaining Display
 * Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import * as fc from 'fast-check';
import { LicenseStatusCard, getStatusColor, getStatusLabel } from '../LicenseStatusCard';
import { 
  LicenseStatus, 
  LicenseStatusData,
  STATUS_COLORS,
  STATUS_LABELS 
} from '@/types/license';

// All possible license statuses
const ALL_STATUSES: LicenseStatus[] = [
  'active',
  'expired',
  'grace_period',
  'not_activated',
  'revoked',
  'deactivated'
];

describe('LicenseStatusCard', () => {
  describe('Property 1: Status Indicator Mapping', () => {
    /**
     * Property 1: Status Indicator Mapping
     * For any license status value, the LicenseStatusCard SHALL render
     * the correct color indicator and label according to the status-to-indicator mapping.
     * Validates: Requirements 1.2, 1.3, 1.4, 1.5
     */

    it('should map all statuses to correct colors', () => {
      fc.assert(
        fc.property(
          fc.constantFrom(...ALL_STATUSES),
          (status) => {
            const color = getStatusColor(status);
            const expectedColor = STATUS_COLORS[status];
            expect(color).toBe(expectedColor);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should map all statuses to correct labels', () => {
      fc.assert(
        fc.property(
          fc.constantFrom(...ALL_STATUSES),
          (status) => {
            const label = getStatusLabel(status);
            const expectedLabel = STATUS_LABELS[status];
            expect(label).toBe(expectedLabel);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should render correct indicator for active status', () => {
      const status: LicenseStatusData = {
        license_status: 'active',
        license_id: 'LIC-123',
        tier: 'professional',
        holder_name: 'Test Co',
        activated_at: '2024-01-01',
        expires_at: '2025-01-01',
        days_remaining: 100,
        is_expiring_soon: false,
        expiration_warning: null,
        features: [],
        grace_period: null,
        usage_stats: null,
        message: null,
        activation_instructions: null
      };

      render(<LicenseStatusCard status={status} isLoading={false} error={null} onRefresh={() => {}} />);
      
      const indicator = screen.getByTestId('status-indicator');
      expect(indicator.getAttribute('data-status')).toBe('active');
      expect(indicator.getAttribute('data-color')).toBe('green');
      expect(indicator.textContent).toContain('Active');
    });

    it('should render correct indicator for expired status', () => {
      const status: LicenseStatusData = {
        license_status: 'expired',
        license_id: 'LIC-123',
        tier: 'basic',
        holder_name: 'Test Co',
        activated_at: '2023-01-01',
        expires_at: '2024-01-01',
        days_remaining: 0,
        is_expiring_soon: false,
        expiration_warning: null,
        features: [],
        grace_period: null,
        usage_stats: null,
        message: null,
        activation_instructions: null
      };

      render(<LicenseStatusCard status={status} isLoading={false} error={null} onRefresh={() => {}} />);
      
      const indicator = screen.getByTestId('status-indicator');
      expect(indicator.getAttribute('data-status')).toBe('expired');
      expect(indicator.getAttribute('data-color')).toBe('red');
      expect(indicator.textContent).toContain('Expired');
    });

    it('should render correct indicator for grace_period status', () => {
      const status: LicenseStatusData = {
        license_status: 'grace_period',
        license_id: 'LIC-123',
        tier: 'professional',
        holder_name: 'Test Co',
        activated_at: '2024-01-01',
        expires_at: '2024-12-01',
        days_remaining: 0,
        is_expiring_soon: false,
        expiration_warning: null,
        features: [],
        grace_period: {
          is_in_grace_period: true,
          grace_period_ends_at: '2024-12-08',
          days_remaining: 7,
          restrictions: ['read-only']
        },
        usage_stats: null,
        message: null,
        activation_instructions: null
      };

      render(<LicenseStatusCard status={status} isLoading={false} error={null} onRefresh={() => {}} />);
      
      const indicator = screen.getByTestId('status-indicator');
      expect(indicator.getAttribute('data-status')).toBe('grace_period');
      expect(indicator.getAttribute('data-color')).toBe('yellow');
      expect(indicator.textContent).toContain('Grace Period');
    });

    it('should render correct indicator for not_activated status', () => {
      render(<LicenseStatusCard status={null} isLoading={false} error={null} onRefresh={() => {}} />);
      
      const indicator = screen.getByTestId('status-indicator');
      expect(indicator.getAttribute('data-status')).toBe('not_activated');
      expect(indicator.getAttribute('data-color')).toBe('gray');
      expect(indicator.textContent).toContain('Not Activated');
    });
  });


  describe('Property 8: Days Remaining Display', () => {
    /**
     * Property 8: Days Remaining Display
     * For any active license status with days_remaining value, the LicenseStatusCard
     * SHALL display the days remaining. When days_remaining <= 30, an expiration
     * warning SHALL be displayed.
     * Validates: Requirements 1.6, 1.7
     */

    it('should display days remaining for active licenses', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 1, max: 365 }),
          (daysRemaining) => {
            const status: LicenseStatusData = {
              license_status: 'active',
              license_id: 'LIC-123',
              tier: 'professional',
              holder_name: 'Test Co',
              activated_at: '2024-01-01',
              expires_at: '2025-01-01',
              days_remaining: daysRemaining,
              is_expiring_soon: daysRemaining <= 30,
              expiration_warning: daysRemaining <= 30 ? 'License expiring soon' : null,
              features: [],
              grace_period: null,
              usage_stats: null,
              message: null,
              activation_instructions: null
            };

            const { container, unmount } = render(
              <LicenseStatusCard status={status} isLoading={false} error={null} onRefresh={() => {}} />
            );
            
            const daysElement = container.querySelector('[data-testid="days-remaining"]');
            expect(daysElement).toBeTruthy();
            expect(daysElement?.textContent).toContain(`${daysRemaining} days remaining`);
            
            unmount();
          }
        ),
        { numRuns: 50 }
      );
    });

    it('should show expiration warning when days_remaining <= 30', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 1, max: 30 }),
          (daysRemaining) => {
            const status: LicenseStatusData = {
              license_status: 'active',
              license_id: 'LIC-123',
              tier: 'professional',
              holder_name: 'Test Co',
              activated_at: '2024-01-01',
              expires_at: '2025-01-01',
              days_remaining: daysRemaining,
              is_expiring_soon: true,
              expiration_warning: 'Your license is expiring soon. Please renew.',
              features: [],
              grace_period: null,
              usage_stats: null,
              message: null,
              activation_instructions: null
            };

            const { container, unmount } = render(
              <LicenseStatusCard status={status} isLoading={false} error={null} onRefresh={() => {}} />
            );
            
            const warningElement = container.querySelector('[data-testid="expiration-warning"]');
            expect(warningElement).toBeTruthy();
            
            unmount();
          }
        ),
        { numRuns: 30 }
      );
    });

    it('should NOT show expiration warning when days_remaining > 30', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 31, max: 365 }),
          (daysRemaining) => {
            const status: LicenseStatusData = {
              license_status: 'active',
              license_id: 'LIC-123',
              tier: 'professional',
              holder_name: 'Test Co',
              activated_at: '2024-01-01',
              expires_at: '2025-01-01',
              days_remaining: daysRemaining,
              is_expiring_soon: false,
              expiration_warning: null,
              features: [],
              grace_period: null,
              usage_stats: null,
              message: null,
              activation_instructions: null
            };

            const { container, unmount } = render(
              <LicenseStatusCard status={status} isLoading={false} error={null} onRefresh={() => {}} />
            );
            
            const warningElement = container.querySelector('[data-testid="expiration-warning"]');
            expect(warningElement).toBeFalsy();
            
            unmount();
          }
        ),
        { numRuns: 30 }
      );
    });
  });

  describe('Loading and Error States', () => {
    it('should show loading spinner when loading', () => {
      render(<LicenseStatusCard status={null} isLoading={true} error={null} onRefresh={() => {}} />);
      
      // Should show loading state
      expect(screen.queryByTestId('status-indicator')).toBeFalsy();
    });

    it('should show error message and retry button on error', () => {
      const onRefresh = vi.fn();
      render(
        <LicenseStatusCard 
          status={null} 
          isLoading={false} 
          error="Network error" 
          onRefresh={onRefresh} 
        />
      );
      
      expect(screen.getByText('Connection Error')).toBeTruthy();
      expect(screen.getByText('Network error')).toBeTruthy();
      expect(screen.getByText('Retry')).toBeTruthy();
    });

    it('should display grace period info when in grace period', () => {
      const status: LicenseStatusData = {
        license_status: 'grace_period',
        license_id: 'LIC-123',
        tier: 'professional',
        holder_name: 'Test Co',
        activated_at: '2024-01-01',
        expires_at: '2024-12-01',
        days_remaining: 0,
        is_expiring_soon: false,
        expiration_warning: null,
        features: [],
        grace_period: {
          is_in_grace_period: true,
          grace_period_ends_at: '2024-12-08',
          days_remaining: 5,
          restrictions: ['read-only', 'no-exports']
        },
        usage_stats: null,
        message: null,
        activation_instructions: null
      };

      render(<LicenseStatusCard status={status} isLoading={false} error={null} onRefresh={() => {}} />);
      
      const gracePeriodInfo = screen.getByTestId('grace-period-info');
      expect(gracePeriodInfo).toBeTruthy();
      expect(gracePeriodInfo.textContent).toContain('5 days remaining');
      expect(gracePeriodInfo.textContent).toContain('read-only');
    });
  });
});
