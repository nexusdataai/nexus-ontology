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
import { Icon } from '@/components/ds/Icon';
import { Field } from '@/components/ds/kit';
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
      <DialogContent className="sm:max-w-[440px]" data-testid="deactivate-dialog">
        <DialogHeader>
          <DialogTitle>Deactivate this license?</DialogTitle>
          <DialogDescription>
            Licensed features stop working until a license is activated again.
            {licenseId && <> License <span className="font-mono text-xs text-foreground">{licenseId}</span>.</>}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <Field label="Reason" htmlFor="deactivation-reason" hint="At least 5 characters. It is kept in the license history.">
            <Textarea
              id="deactivation-reason"
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (error) setError(null);
              }}
              placeholder="Why is this license being deactivated?"
              aria-invalid={error ? true : undefined}
              disabled={isDeactivating}
              rows={3}
              data-testid="deactivation-reason-input"
            />
          </Field>

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2.5 rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
              data-testid="deactivation-error"
            >
              <Icon name="alert-triangle" className="mt-0.5 shrink-0" />
              <p>{error}</p>
            </div>
          )}

          <p className="flex items-start gap-2 text-sm text-muted-foreground">
            <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0 text-subtle-foreground" />
            Whether the same license can be activated again depends on your license terms.
          </p>
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
            {isDeactivating && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
            {isDeactivating ? 'Deactivating...' : 'Deactivate license'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default LicenseDeactivateDialog;
