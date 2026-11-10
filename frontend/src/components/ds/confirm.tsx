/**
 * In-app confirmation dialog. Replaces window.confirm everywhere.
 *
 *   if (!(await confirmDialog({ title: 'Delete this journey?', description: 'This cannot be undone.', destructive: true }))) return;
 *
 * <ConfirmHost /> is mounted once in App.tsx.
 */
import * as React from 'react';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface ConfirmOptions {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Style the confirm button as destructive (delete, purge, revoke). */
  destructive?: boolean;
}

interface Pending extends ConfirmOptions {
  resolve: (ok: boolean) => void;
}

let push: ((p: Pending) => void) | null = null;

export function confirmDialog(options: ConfirmOptions | string): Promise<boolean> {
  const opts: ConfirmOptions = typeof options === 'string' ? { title: options } : options;
  return new Promise<boolean>((resolve) => {
    if (!push) {
      // Host not mounted (should not happen): fall back to the browser dialog.
      resolve(window.confirm(opts.title));
      return;
    }
    push({ ...opts, resolve });
  });
}

export function ConfirmHost() {
  const [pending, setPending] = React.useState<Pending | null>(null);

  React.useEffect(() => {
    push = (p) => setPending(p);
    return () => { push = null; };
  }, []);

  const close = (ok: boolean) => {
    pending?.resolve(ok);
    setPending(null);
  };

  return (
    <AlertDialog open={!!pending} onOpenChange={(open) => { if (!open) close(false); }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{pending?.title}</AlertDialogTitle>
          <AlertDialogDescription className={pending?.description ? undefined : 'sr-only'}>
            {pending?.description || 'Please confirm this action.'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => close(false)}>{pending?.cancelLabel || 'Cancel'}</AlertDialogCancel>
          <AlertDialogAction
            onClick={() => close(true)}
            className={cn(pending?.destructive && buttonVariants({ variant: 'destructive' }))}
          >
            {pending?.confirmLabel || (pending?.destructive ? 'Delete' : 'Confirm')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
