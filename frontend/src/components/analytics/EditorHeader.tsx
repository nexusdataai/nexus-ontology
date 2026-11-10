/**
 * Sticky header shared by the dashboard and view screens (builder and viewer):
 * back link to the library, the object's name, its state, and the actions.
 * Presentational only.
 */
import * as React from 'react';
import { Icon } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';

interface EditorHeaderProps {
  backLabel: string;
  onBack: () => void;
  /** The name: an inline input in builders, a heading in viewers. */
  title: React.ReactNode;
  /** Saved state, version, counts: quiet text next to the name. */
  meta?: React.ReactNode;
  /** Controls on the right. One primary button. */
  actions?: React.ReactNode;
  /** Optional second row (description, variables). */
  children?: React.ReactNode;
  className?: string;
}

export function EditorHeader({ backLabel, onBack, title, meta, actions, children, className }: EditorHeaderProps) {
  return (
    <header className={cn('sticky top-0 z-20 border-b border-border bg-background/95 px-4 pb-3 pt-2.5 backdrop-blur-sm sm:px-6', className)}>
      <button
        type="button"
        onClick={onBack}
        className="-ml-1 inline-flex h-6 items-center gap-1 rounded px-1 text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Icon name="chevron-left" className="h-3 w-3" /> {backLabel}
      </button>
      <div className="mt-1 flex flex-wrap items-center justify-between gap-x-4 gap-y-2.5">
        <div className="flex min-w-0 flex-1 basis-72 flex-wrap items-center gap-x-3 gap-y-1">
          {title}
          {meta}
        </div>
        {actions && <div className="flex max-w-full flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children}
    </header>
  );
}

/** Saved / unsaved state as quiet text with a dot. */
export function SaveState({ state, detail }: { state: 'new' | 'dirty' | 'saved' | 'saving'; detail?: string }) {
  const label = { new: 'Not saved yet', dirty: 'Unsaved changes', saved: 'All changes saved', saving: 'Saving' }[state];
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap text-xs text-muted-foreground" aria-live="polite">
      <span
        aria-hidden="true"
        className={cn('inline-block h-1.5 w-1.5 rounded-full', state === 'saved' ? 'bg-success' : state === 'saving' ? 'bg-primary' : 'bg-warning')}
      />
      {label}
      {detail && <span className="num text-subtle-foreground">· {detail}</span>}
    </span>
  );
}

/** Inline editable name: looks like a heading until hovered or focused. */
export const NameInput = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'h-9 min-w-0 max-w-md flex-1 basis-48 truncate rounded-md border border-transparent bg-transparent px-2 text-lg font-medium tracking-tight text-foreground transition-colors placeholder:text-subtle-foreground hover:border-border focus:border-border-strong focus:bg-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        '-ml-2',
        className,
      )}
      {...props}
    />
  ),
);
NameInput.displayName = 'NameInput';
