/**
 * LicenseRenewalForm Component
 *
 * Form for renewing licenses with renewal keys.
 * Shows current expiration and new expiration after renewal.
 * Renders bare (no surface of its own): the page places it in a section.
 *
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
 */

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Icon } from '@/components/ds/Icon';
import { Field } from '@/components/ds/kit';
import { LicenseRenewalFormProps } from '@/types/license';

// ============================================================================
// Validation
// ============================================================================

export interface RenewalValidationResult {
  isValid: boolean;
  error: string | null;
}

export function validateRenewalKey(key: string): RenewalValidationResult {
  if (!key.trim()) {
    return { isValid: false, error: 'Renewal key is required' };
  }

  // Renewal keys should be at least 10 characters
  if (key.trim().length < 10) {
    return { isValid: false, error: 'Renewal key is too short' };
  }

  return { isValid: true, error: null };
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatDate(dateString: string | null): string {
  if (!dateString) return 'Not set';
  try {
    return new Date(dateString).toLocaleDateString('en-GB', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  } catch {
    return dateString;
  }
}

// ============================================================================
// Main Component
// ============================================================================

export function LicenseRenewalForm({
  onRenew,
  isRenewing,
  error,
  currentExpiration,
  isLicenseActive
}: LicenseRenewalFormProps) {
  const [renewalKey, setRenewalKey] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [newExpiration, setNewExpiration] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Client-side validation
    const validation = validateRenewalKey(renewalKey);
    if (!validation.isValid) {
      setValidationError(validation.error);
      return;
    }

    setValidationError(null);
    setShowSuccess(false);
    setNewExpiration(null);

    try {
      await onRenew(renewalKey.trim());
      setShowSuccess(true);
      setRenewalKey('');
      // Note: newExpiration would be set by parent after successful renewal
    } catch {
      // Error is handled by parent via error prop
    }
  };

  const handleKeyChange = (value: string) => {
    setRenewalKey(value);
    if (validationError) {
      setValidationError(null);
    }
    if (showSuccess) {
      setShowSuccess(false);
    }
  };

  // Hide form when no license is activated (Property 5)
  if (!isLicenseActive) {
    return null;
  }

  const displayError = validationError || (error?.message);
  const errorCode = error?.code;

  return (
    <div className="max-w-xl" data-testid="renewal-form">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field
          label="Renewal key"
          htmlFor="renewal-key"
          hint={currentExpiration
            ? <span data-testid="current-expiration">The license currently runs until <span className="text-foreground">{formatDate(currentExpiration)}</span>.</span>
            : undefined}
        >
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              id="renewal-key"
              type="text"
              value={renewalKey}
              onChange={(e) => handleKeyChange(e.target.value)}
              placeholder="Paste the renewal key"
              className="font-mono"
              aria-invalid={displayError ? true : undefined}
              disabled={isRenewing}
              data-testid="renewal-key-input"
            />
            <Button type="submit" className="shrink-0" disabled={isRenewing || !renewalKey.trim()} data-testid="renew-button">
              {isRenewing && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
              {isRenewing ? 'Renewing...' : 'Renew license'}
            </Button>
          </div>
        </Field>

        {displayError && (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
            data-testid="renewal-error"
          >
            <Icon name="alert-triangle" className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="font-medium">Renewal failed</p>
              <p>{displayError}</p>
              {errorCode && <p className="mt-1 font-mono text-xs">Error code: {errorCode}</p>}
            </div>
          </div>
        )}

        {showSuccess && (
          <div role="status" className="text-sm text-foreground" data-testid="renewal-success">
            <p className="flex items-center gap-2">
              <Icon name="check-circle" className="h-4 w-4 text-success" />
              License renewed.
            </p>
            {newExpiration && (
              <p className="mt-0.5 pl-6 text-muted-foreground">New expiry date: {formatDate(newExpiration)}</p>
            )}
          </div>
        )}
      </form>
    </div>
  );
}

export default LicenseRenewalForm;
