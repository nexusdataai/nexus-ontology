/**
 * LicenseActivationForm Tests
 * 
 * Property 2: License Key Validation
 * Property 4: Loading State UI
 * Validates: Requirements 2.2, 2.6
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import * as fc from 'fast-check';
import { LicenseActivationForm, validateLicenseKey } from '../LicenseActivationForm';
import { LICENSE_KEY_PATTERN } from '@/types/license';

// Valid license key format: v1.TIER.YYYYMMDD.HOLDER_ID.FEATURES.SIGNATURE
const VALID_KEY_EXAMPLE = 'v1.PRO.20251231.HOLDER123.ALL.c2lnbmF0dXJl';

describe('LicenseActivationForm', () => {
  describe('Property 2: License Key Validation', () => {
    /**
     * Property 2: License Key Validation
     * For any string that does not match the license key format pattern,
     * the LicenseActivationForm SHALL display a validation error and
     * SHALL NOT call the backend API.
     * Validates: Requirements 2.2
     */

    it('should reject empty strings', () => {
      const result = validateLicenseKey('');
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('License key is required');
    });

    it('should reject whitespace-only strings', () => {
      fc.assert(
        fc.property(
          fc.stringOf(fc.constantFrom(' ', '\t', '\n')).filter(s => s.length > 0),
          (whitespace) => {
            const result = validateLicenseKey(whitespace);
            expect(result.isValid).toBe(false);
          }
        ),
        { numRuns: 20 }
      );
    });

    it('should reject random strings that do not match license key format', () => {
      fc.assert(
        fc.property(
          fc.string().filter(s => s.trim().length > 0 && !LICENSE_KEY_PATTERN.test(s)),
          (invalidKey) => {
            const result = validateLicenseKey(invalidKey);
            expect(result.isValid).toBe(false);
            expect(result.error).toContain('Invalid license key format');
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should accept valid license key format', () => {
      const validKeys = [
        'v1.BAS.20251231.HOLDER123.ALL.c2lnbmF0dXJl',
        'v1.PRO.20240101.COMPANY.FEAT1.YWJjZGVm',
        'v1.ENT.20261231.ORG123.ALL.dGVzdA=='
      ];

      validKeys.forEach(key => {
        const result = validateLicenseKey(key);
        expect(result.isValid).toBe(true);
        expect(result.error).toBeNull();
      });
    });

    it('should NOT call onActivate when validation fails', async () => {
      const onActivate = vi.fn();
      
      render(
        <LicenseActivationForm
          onActivate={onActivate}
          isActivating={false}
          error={null}
          isLicenseActive={false}
        />
      );

      const input = screen.getByTestId('license-key-input');
      const button = screen.getByTestId('activate-button');

      // Enter invalid key
      fireEvent.change(input, { target: { value: 'invalid-key' } });
      fireEvent.click(button);

      await waitFor(() => {
        expect(screen.getByTestId('activation-error')).toBeTruthy();
      });

      expect(onActivate).not.toHaveBeenCalled();
    });

    it('should call onActivate when validation passes', async () => {
      const onActivate = vi.fn().mockResolvedValue(undefined);
      
      render(
        <LicenseActivationForm
          onActivate={onActivate}
          isActivating={false}
          error={null}
          isLicenseActive={false}
        />
      );

      const input = screen.getByTestId('license-key-input');
      const button = screen.getByTestId('activate-button');

      fireEvent.change(input, { target: { value: VALID_KEY_EXAMPLE } });
      fireEvent.click(button);

      await waitFor(() => {
        expect(onActivate).toHaveBeenCalledWith(VALID_KEY_EXAMPLE, undefined);
      });
    });
  });

  describe('Property 4: Loading State UI', () => {
    /**
     * Property 4: Loading State UI
     * For any async operation in progress (isActivating), the form SHALL
     * disable its submit button and display a loading indicator.
     * Validates: Requirements 2.6
     */

    it('should disable button and show spinner when isActivating is true', () => {
      render(
        <LicenseActivationForm
          onActivate={vi.fn()}
          isActivating={true}
          error={null}
          isLicenseActive={false}
        />
      );

      const button = screen.getByTestId('activate-button') as HTMLButtonElement;
      expect(button.disabled).toBe(true);
      expect(button.textContent).toContain('Activating...');
    });

    it('should enable button when isActivating is false and key is entered', () => {
      render(
        <LicenseActivationForm
          onActivate={vi.fn()}
          isActivating={false}
          error={null}
          isLicenseActive={false}
        />
      );

      const input = screen.getByTestId('license-key-input');
      const button = screen.getByTestId('activate-button') as HTMLButtonElement;

      // Initially disabled (no key)
      expect(button.disabled).toBe(true);

      // Enter key
      fireEvent.change(input, { target: { value: VALID_KEY_EXAMPLE } });
      expect(button.disabled).toBe(false);
    });

    it('should disable inputs during activation', () => {
      render(
        <LicenseActivationForm
          onActivate={vi.fn()}
          isActivating={true}
          error={null}
          isLicenseActive={false}
        />
      );

      const keyInput = screen.getByTestId('license-key-input') as HTMLInputElement;
      const instanceInput = screen.getByTestId('instance-id-input') as HTMLInputElement;

      expect(keyInput.disabled).toBe(true);
      expect(instanceInput.disabled).toBe(true);
    });
  });

  describe('Error Display', () => {
    it('should display error message and code from props', () => {
      render(
        <LicenseActivationForm
          onActivate={vi.fn()}
          isActivating={false}
          error={{
            type: 'api',
            message: 'License key already in use',
            code: 'ALREADY_ACTIVATED',
            retryable: false
          }}
          isLicenseActive={false}
        />
      );

      const errorElement = screen.getByTestId('activation-error');
      expect(errorElement.textContent).toContain('License key already in use');
      expect(errorElement.textContent).toContain('ALREADY_ACTIVATED');
    });
  });

  describe('Active License State', () => {
    it('should show active license message when isLicenseActive is true', () => {
      render(
        <LicenseActivationForm
          onActivate={vi.fn()}
          isActivating={false}
          error={null}
          isLicenseActive={true}
        />
      );

      expect(screen.getByText(/License is active/)).toBeTruthy();
      expect(screen.queryByTestId('license-key-input')).toBeFalsy();
    });
  });
});
