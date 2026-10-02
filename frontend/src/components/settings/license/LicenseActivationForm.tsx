/**
 * LicenseActivationForm Component
 * 
 * Form for entering and activating license keys.
 * Includes client-side validation and loading states.
 * 
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Key, 
  Loader2, 
  CheckCircle,
  AlertCircle,
  Server
} from 'lucide-react';
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

  // If license is already active, show different UI
  if (isLicenseActive) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            License Activation
          </CardTitle>
          <CardDescription>
            A license is already activated on this instance
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg border border-green-200">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <p className="text-green-800">
              License is active. Deactivate the current license to activate a new one.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const displayError = validationError || (error?.message);
  const errorCode = error?.code;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Key className="h-5 w-5" />
          Activate License
        </CardTitle>
        <CardDescription>
          Enter your license key to activate this instance
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* License Key Input */}
          <div className="space-y-2">
            <Label htmlFor="license-key">License Key *</Label>
            <Input
              id="license-key"
              type="text"
              value={licenseKey}
              onChange={(e) => handleKeyChange(e.target.value)}
              placeholder="v1.PRO.20251231.HOLDER123.ALL.signature..."
              className={`font-mono ${displayError ? 'border-red-500' : ''}`}
              disabled={isActivating}
              data-testid="license-key-input"
            />
          </div>

          {/* Instance ID Input (Optional) */}
          <div className="space-y-2">
            <Label htmlFor="instance-id" className="flex items-center gap-2">
              <Server className="h-4 w-4" />
              Instance ID (Optional)
            </Label>
            <Input
              id="instance-id"
              type="text"
              value={instanceId}
              onChange={(e) => setInstanceId(e.target.value)}
              placeholder="my-instance-001"
              disabled={isActivating}
              data-testid="instance-id-input"
            />
            <p className="text-xs text-muted-foreground">
              For multi-instance deployments. Leave empty for single instance.
            </p>
          </div>

          {/* Error Display */}
          {displayError && (
            <div 
              className="flex items-start gap-3 p-3 bg-red-50 rounded-lg border border-red-200"
              data-testid="activation-error"
            >
              <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
              <div>
                <p className="text-red-800 font-medium">Activation Failed</p>
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
              className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200"
              data-testid="activation-success"
            >
              <CheckCircle className="h-5 w-5 text-green-600" />
              <p className="text-green-800">License activated successfully!</p>
            </div>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isActivating || !licenseKey.trim()}
            className="w-full"
            data-testid="activate-button"
          >
            {isActivating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Activating...
              </>
            ) : (
              <>
                <Key className="h-4 w-4 mr-2" />
                Activate License
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default LicenseActivationForm;
