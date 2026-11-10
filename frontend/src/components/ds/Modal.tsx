/**
 * Modal for larger custom panels (reports, detail views, test benches).
 * Built on Radix Dialog, so it traps focus, closes on Esc and on a click
 * outside, and is announced to screen readers.
 *
 *   {open && (
 *     <ModalOverlay onClose={close}>
 *       <ModalPanel label="Mapping audit report" className="max-w-5xl">…</ModalPanel>
 *     </ModalOverlay>
 *   )}
 *
 * For a short form or a confirmation use ui/dialog or ds/confirm instead.
 * Never hand-build a `fixed inset-0` overlay.
 */
import * as React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { cn } from '@/lib/utils';

export function ModalOverlay({ onClose, children }: { onClose: () => void; children: React.ReactNode }) {
  return (
    <DialogPrimitive.Root open onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/55 backdrop-blur-[3px] data-[state=open]:animate-fade-in" />
        {children}
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

interface ModalPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Accessible name of the modal (read by screen readers). */
  label: string;
}

export const ModalPanel = React.forwardRef<HTMLDivElement, ModalPanelProps>(
  ({ label, className, children, ...props }, ref) => (
    <DialogPrimitive.Content
      ref={ref}
      aria-describedby={undefined}
      className={cn(
        'fixed left-1/2 top-1/2 z-50 flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-xl border border-border bg-popover text-popover-foreground shadow-lg focus:outline-none data-[state=open]:animate-scale-in',
        className,
      )}
      {...props}
    >
      <DialogPrimitive.Title className="sr-only">{label}</DialogPrimitive.Title>
      {children}
    </DialogPrimitive.Content>
  ),
);
ModalPanel.displayName = 'ModalPanel';
