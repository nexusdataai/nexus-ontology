/**
 * LicenseDeactivateDialog Component
 * 
 * Confirmation dialog for license deactivation.
 * Requires reason input before confirming.
 * 
 * Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
 */

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { 
  AlertTriangle, 
  Loader2,
  AlertCircle
} from 'lucide-react';
import { LicenseDeactivateDialogProps, LicenseError } from '@/types/license';

// ============================================================================
// Main Component
// ============================================================================

export function LicenseDeactivateDialog({
  isOpen,
  onClose,
  onConfirm,
  isDeactivating,
  licenseId
}: LicenseDeactivateDialogProps) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    // Validate reason
    if (!reason.trim()) {
      setError('Please provide a reason for deactivation');
      return;
    }

    if (reason.trim().length < 5) {
      setError('Reason must be at least 5 characters');
      return;
    }

    setError(null);
    
    try {
      await onConfirm(reason.trim());
      // Reset state on success
      setReason('');
      setError(null);
    } catch (err) {
      // Handle error from parent
      const licenseError = err as LicenseError;
      setError(licenseError.message || 'Deactivation failed');
    }
  };

  const handleClose = () => {
    if (!isDeactivating) {
      setReason('');
      setError(null);
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]" data-testid="deactivate-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            Deactivate License
          </DialogTitle>
          <DialogDescription>
            This action will deactivate your current license. You will need to activate a new license to continue using premium features.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* License ID Display */}
          {licenseId && (
            <div className="p-3 bg-gray-50 rounded-lg border">
              <p className="text-sm text-gray-600">
                License ID: <span className="font-mono font-medium">{licenseId}</span>
              </p>
            </div>
          )}

          {/* Reason Input */}
          <div className="space-y-2">
            <Label htmlFor="deactivation-reason">
              Reason for deactivation *
            </Label>
            <Textarea
              id="deactivation-reason"
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (error) setError(null);
              }}
              placeholder="Please explain why you are deactivating this license..."
              className={error ? 'border-red-500' : ''}
              disabled={isDeactivating}
              rows={3}
              data-testid="deactivation-reason-input"
            />
            <p className="text-xs text-muted-foreground">
              This information helps us improve our service.
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <div 
              className="flex items-start gap-2 p-3 bg-red-50 rounded-lg border border-red-200"
              data-testid="deactivation-error"
            >
              <AlertCircle className="h-4 w-4 text-red-500 mt-0.5" />
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Warning */}
          <div className="flex items-start gap-2 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
            <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
            <div className="text-sm text-yellow-800">
              <p className="font-medium">Warning</p>
              <p>After deactivation, you may be able to reactivate this license depending on your license terms.</p>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isDeactivating}
            data-testid="cancel-button"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={isDeactivating || !reason.trim()}
            data-testid="confirm-deactivate-button"
          >
            {isDeactivating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Deactivating...
              </>
            ) : (
              'Deactivate License'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default LicenseDeactivateDialog;
