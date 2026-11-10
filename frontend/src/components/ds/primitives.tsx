/**
 * Design-system primitives shared by every screen.
 * Keep them small and presentational: no data fetching in here.
 */
import * as React from 'react';
import { cn } from '@/lib/utils';
import { Icon, type IconName } from '@/components/ds/Icon';

/* ---------------------------------------------------------------- PageHeader */

interface PageHeaderProps {
  title: string;
  description?: string;
  eyebrow?: string;
  /** Buttons / controls aligned to the right (stack below on phones). */
  actions?: React.ReactNode;
  className?: string;
}

/** The one page title block. Every routed page starts with this. */
export function PageHeader({ title, description, eyebrow, actions, className }: PageHeaderProps) {
  return (
    <div className={cn('flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between', className)}>
      <div className="min-w-0">
        {eyebrow && <div className="eyebrow mb-2">{eyebrow}</div>}
        <h1 className="text-2xl font-medium tracking-tight text-foreground sm:text-3xl">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/* ------------------------------------------------------------- SectionHeader */

export function SectionHeader({ title, description, actions, className }: Omit<PageHeaderProps, 'eyebrow'>) {
  return (
    <div className={cn('flex items-end justify-between gap-3', className)}>
      <div className="min-w-0">
        <h2 className="text-md font-medium text-foreground">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

/* ----------------------------------------------------------------- IconTile */

type Tone = 'brand' | 'neutral' | 'success' | 'warning' | 'danger';

const TONE_TILE: Record<Tone, string> = {
  brand: 'border-brand/25 bg-brand/10 text-primary dark:text-brand-hi',
  neutral: 'border-border bg-surface-2 text-muted-foreground',
  success: 'border-success/25 bg-success/10 text-success',
  warning: 'border-warning/25 bg-warning/10 text-warning',
  danger: 'border-destructive/25 bg-destructive/10 text-destructive',
};

interface IconTileProps {
  icon: IconName;
  tone?: Tone;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

/** Square icon badge used at the start of cards, rows and headers. */
export function IconTile({ icon, tone = 'neutral', size = 'md', className }: IconTileProps) {
  const box = size === 'sm' ? 'h-7 w-7 rounded-md' : size === 'lg' ? 'h-11 w-11 rounded-xl' : 'h-9 w-9 rounded-lg';
  const ic = size === 'sm' ? 'h-3.5 w-3.5' : size === 'lg' ? 'h-5 w-5' : 'h-4 w-4';
  return (
    <span className={cn('inline-flex shrink-0 items-center justify-center border transition-colors duration-200', box, TONE_TILE[tone], className)}>
      <Icon name={icon} className={ic} />
    </span>
  );
}

/* ---------------------------------------------------------------- StatusDot */

const TONE_TEXT: Record<Tone, string> = {
  brand: 'text-brand',
  neutral: 'text-subtle-foreground',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-destructive',
};

export function StatusDot({ tone = 'neutral', live, className }: { tone?: Tone; live?: boolean; className?: string }) {
  return <span className={cn(live ? 'dot-live' : 'inline-block h-2 w-2 rounded-full bg-current', TONE_TEXT[tone], className)} aria-hidden="true" />;
}

/* --------------------------------------------------------------------- Kbd */

export function Kbd({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <kbd className={cn('inline-flex h-5 min-w-5 items-center justify-center rounded border border-border-strong bg-surface-2 px-1 font-mono text-[11px] font-medium text-muted-foreground', className)}>
      {children}
    </kbd>
  );
}

/* ----------------------------------------------------------------- StatTile */

interface StatTileProps {
  label: string;
  value: React.ReactNode;
  hint?: string;
  onClick?: () => void;
  className?: string;
}

/** Compact number + label. Becomes a button when onClick is set. */
export function StatTile({ label, value, hint, onClick, className }: StatTileProps) {
  const inner = (
    <>
      <div className="text-lg font-medium leading-6 text-foreground">{value}</div>
      <div className="mt-0.5 truncate text-xs text-muted-foreground">{label}</div>
      {hint && <div className="mt-0.5 truncate text-xs text-subtle-foreground">{hint}</div>}
    </>
  );
  const base = 'rounded-lg border border-border bg-surface-2/70 px-3 py-2.5 text-left';
  if (!onClick) return <div className={cn(base, className)}>{inner}</div>;
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className={cn(base, 'transition-[border-color,background-color,transform] duration-200 ease-brand hover:-translate-y-px hover:border-brand/40 hover:bg-brand/5', className)}
    >
      {inner}
    </button>
  );
}

/* --------------------------------------------------------------- EmptyState */

interface EmptyStateProps {
  icon?: IconName;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center rounded-xl border border-dashed border-border-strong px-6 py-12 text-center', className)}>
      {icon && <IconTile icon={icon} size="lg" className="mb-4" />}
      <h3 className="text-md font-medium text-foreground">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
