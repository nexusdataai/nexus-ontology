/**
 * LicenseRenewalForm Component
 * 
 * Form for renewing licenses with renewal keys.
 * Shows current expiration and new expiration after renewal.
 * 
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  RefreshCw, 
  Loader2, 
  CheckCircle,
  AlertCircle,
  Calendar
} from 'lucide-react';
import { LicenseRenewalFormProps, LicenseError } from '@/types/license';

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
  if (!dateString) return 'N/A';
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
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
    <Card data-testid="renewal-form">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <RefreshCw className="h-5 w-5" />
          Renew License
        </CardTitle>
        <CardDescription>
          Extend your license with a renewal key
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Current Expiration Display */}
        {currentExpiration && (
          <div className="mb-4 p-3 bg-gray-50 rounded-lg border" data-testid="current-expiration">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Calendar className="h-4 w-4" />
              <span>Current expiration:</span>
              <span className="font-medium text-gray-900">{formatDate(currentExpiration)}</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Renewal Key Input */}
          <div className="space-y-2">
            <Label htmlFor="renewal-key">Renewal Key *</Label>
            <Input
              id="renewal-key"
              type="text"
              value={renewalKey}
              onChange={(e) => handleKeyChange(e.target.value)}
              placeholder="Enter your renewal key..."
              className={`font-mono ${displayError ? 'border-red-500' : ''}`}
              disabled={isRenewing}
              data-testid="renewal-key-input"
            />
          </div>

          {/* Error Display */}
          {displayError && (
            <div 
              className="flex items-start gap-3 p-3 bg-red-50 rounded-lg border border-red-200"
              data-testid="renewal-error"
            >
              <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
              <div>
                <p className="text-red-800 font-medium">Renewal Failed</p>
                <p className="text-sm text-red-600">{displayError}</p>
                {errorCode && (
                  <p className="text-xs text-red-500 mt-1">Error code: {errorCode}</p>
                )}
              </div>
            </div>
          )}

          {/* Success Display */}
          {showSuccess && (
            <div 
              className="flex items-start gap-3 p-3 bg-green-50 rounded-lg border border-green-200"
              data-testid="renewal-success"
            >
              <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
              <div>
                <p className="text-green-800 font-medium">License renewed successfully!</p>
                {newExpiration && (
                  <p className="text-sm text-green-600">
                    New expiration: {formatDate(newExpiration)}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isRenewing || !renewalKey.trim()}
            className="w-full"
            data-testid="renew-button"
          >
            {isRenewing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Renewing...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Renew License
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default LicenseRenewalForm;
