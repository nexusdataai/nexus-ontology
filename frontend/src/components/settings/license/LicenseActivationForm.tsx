/**
 * LicenseActivationForm Component
 *
 * Form for entering and activating license keys.
 * Includes client-side validation and loading states.
 * Renders bare (no surface of its own): the page places it in a section.
 *
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
 */

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Icon } from '@/components/ds/Icon';
import { Field } from '@/components/ds/kit';
import {
  LicenseActivationFormProps,
  isValidLicenseKeyFormat
} from '@/types/license';

// ============================================================================
// Validation
// ============================================================================

export interface ValidationResult {
  isValid: boolean;
  error: string | null;
}

export function validateLicenseKey(key: string): ValidationResult {
  if (!key.trim()) {
    return { isValid: false, error: 'License key is required' };
  }

  if (!isValidLicenseKeyFormat(key.trim())) {
    return {
      isValid: false,
      error: 'Invalid license key format. Expected format: v1.TIER.DATE.HOLDER.FEATURES.SIGNATURE'
    };
  }

  return { isValid: true, error: null };
}

// ============================================================================
// Main Component
// ============================================================================

export function LicenseActivationForm({
  onActivate,
  isActivating,
  error,
  isLicenseActive
}: LicenseActivationFormProps) {
  const [licenseKey, setLicenseKey] = useState('');
  const [instanceId, setInstanceId] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Client-side validation
    const validation = validateLicenseKey(licenseKey);
    if (!validation.isValid) {
      setValidationError(validation.error);
      return;
    }

    setValidationError(null);
    setShowSuccess(false);

    try {
      await onActivate(licenseKey.trim(), instanceId.trim() || undefined);
      setShowSuccess(true);
      setLicenseKey('');
      setInstanceId('');
    } catch {
      // Error is handled by parent via error prop
    }
  };

  const handleKeyChange = (value: string) => {
    setLicenseKey(value);
    if (validationError) {
      setValidationError(null);
    }
    if (showSuccess) {
      setShowSuccess(false);
    }
  };

  // If a license is already active, there is nothing to enter
  if (isLicenseActive) {
    return (
      <p className="text-sm text-muted-foreground">
        License is active. Deactivate the current license to activate a new one.
      </p>
    );
  }

  const displayError = validationError || (error?.message);
  const errorCode = error?.code;

  return (
    <form onSubmit={handleSubmit} className="max-w-xl space-y-4">
      <Field label="License key" htmlFor="license-key">
        <Input
          id="license-key"
          type="text"
          value={licenseKey}
          onChange={(e) => handleKeyChange(e.target.value)}
          placeholder="v1.PRO.20251231.HOLDER123.ALL.signature"
          className="font-mono"
          aria-invalid={displayError ? true : undefined}
          disabled={isActivating}
          data-testid="license-key-input"
        />
      </Field>

      <Field label="Instance ID (optional)" htmlFor="instance-id" hint="Only for installations with several instances. Leave empty for a single instance.">
        <Input
          id="instance-id"
          type="text"
          value={instanceId}
          onChange={(e) => setInstanceId(e.target.value)}
          placeholder="my-instance-001"
          className="font-mono sm:max-w-xs"
          disabled={isActivating}
          data-testid="instance-id-input"
        />
      </Field>

      {displayError && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
          data-testid="activation-error"
        >
          <Icon name="alert-triangle" className="mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p className="font-medium">Activation failed</p>
            <p>{displayError}</p>
            {errorCode && <p className="mt-1 font-mono text-xs">Error code: {errorCode}</p>}
          </div>
        </div>
      )}

      {showSuccess && (
        <p role="status" className="flex items-center gap-2 text-sm text-foreground" data-testid="activation-success">
          <Icon name="check-circle" className="h-4 w-4 text-success" />
          License activated.
        </p>
      )}

      <Button type="submit" disabled={isActivating || !licenseKey.trim()} data-testid="activate-button">
        {isActivating && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
        {isActivating ? 'Activating...' : 'Activate license'}
      </Button>
    </form>
  );
}

export default LicenseActivationForm;
