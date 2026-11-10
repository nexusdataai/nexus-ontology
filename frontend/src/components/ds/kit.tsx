/**
 * Composite building blocks for product screens.
 * ----------------------------------------------------------------------------
 * Screens are assembled from these, so every area shares one visual language:
 * quiet surfaces, hairlines, text-first metrics, one blue accent.
 * Presentational only: no data fetching in here.
 */
import * as React from 'react';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Icon, type IconName } from '@/components/ds/Icon';

/* ------------------------------------------------------------------- tones */

export type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

const TONE_TEXT: Record<Tone, string> = {
  neutral: 'text-muted-foreground',
  info: 'text-primary dark:text-brand-hi',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-destructive',
};
const TONE_BG: Record<Tone, string> = {
  neutral: 'bg-border-strong',
  info: 'bg-primary',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-destructive',
};

/** Map any backend status word to a tone. Add words here, not in screens. */
export function toneOf(status?: string | null): Tone {
  const s = String(status || '').toLowerCase().replace(/[\s-]+/g, '_');
  if (/^(ok|pass|passed|success|succeeded|completed|complete|done|active|healthy|connected|enabled|available|mapped|verified|approved|valid|online|up|true|low|read_only)$/.test(s)) return 'success';
  if (/^(running|in_progress|processing|executing|planning|planned|syncing|started|queued|info|virtual|medium_low)$/.test(s)) return 'info';
  if (/^(warn|warning|degraded|pending|paused|awaiting_approval|partial|stale|medium|draft|low_risk_write|low_risk|expiring|unverified|skipped)$/.test(s)) return 'warning';
  if (/^(fail|failed|error|errored|critical|high|blocked|rejected|down|offline|expired|unmapped|invalid|cancelled|canceled|high_risk_write|high_risk|cross_system|disabled|false)$/.test(s)) return 'danger';
  return 'neutral';
}

const LIVE = /^(running|in_progress|processing|executing|planning|syncing)$/;

/* ------------------------------------------------------------- StatusPill */

interface StatusPillProps {
  /** Backend status word. Used for the tone and, if no children, the label. */
  status?: string | null;
  tone?: Tone;
  /** Pulse the dot (defaults to true for running-type statuses). */
  live?: boolean;
  /** "dot" = dot + text (default, quiet). "soft" = tinted pill for emphasis. */
  variant?: 'dot' | 'soft';
  className?: string;
  children?: React.ReactNode;
}

/** The one way to show a status anywhere in the product. */
export function StatusPill({ status, tone, live, variant = 'dot', className, children }: StatusPillProps) {
  const t = tone || toneOf(status);
  const key = String(status || '').toLowerCase().replace(/[\s-]+/g, '_');
  const isLive = live ?? LIVE.test(key);
  const label = children ?? String(status || '').replace(/[_-]+/g, ' ');
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap text-xs font-medium',
        variant === 'soft'
          ? cn('rounded-md border px-2 py-0.5', {
              neutral: 'border-border bg-surface-2 text-muted-foreground',
              info: 'border-info/25 bg-info/10 text-info',
              success: 'border-success/25 bg-success/10 text-success',
              warning: 'border-warning/25 bg-warning/10 text-warning',
              danger: 'border-destructive/25 bg-destructive/10 text-destructive',
            }[t])
          : 'text-foreground',
        className,
      )}
    >
      <span className={cn(isLive ? 'dot-live' : 'inline-block h-1.5 w-1.5 rounded-full bg-current', TONE_TEXT[t])} aria-hidden="true" />
      <span className="first-letter:uppercase">{label}</span>
    </span>
  );
}

/* ------------------------------------------------------------------ Panel */

interface PanelProps extends Omit<React.HTMLAttributes<HTMLElement>, 'title'> {
  title?: React.ReactNode;
  description?: React.ReactNode;
  /** Controls on the right of the header. */
  actions?: React.ReactNode;
  footer?: React.ReactNode;
  /** No body padding: for tables and lists that run edge to edge. */
  flush?: boolean;
  bodyClassName?: string;
}

/** A titled surface. Use for one coherent object; never nest panels. */
export function Panel({ title, description, actions, footer, flush, className, bodyClassName, children, ...rest }: PanelProps) {
  return (
    <section className={cn('flex min-w-0 flex-col overflow-hidden rounded-xl border border-border bg-card shadow-xs', className)} {...rest}>
      {(title || actions) && (
        <header className="flex min-h-[52px] flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border px-4 py-2.5 sm:px-5">
          <div className="min-w-0">
            {title && <h2 className="truncate text-md font-medium text-foreground">{title}</h2>}
            {description && <p className="truncate text-xs text-muted-foreground">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={cn('min-h-0 flex-1', !flush && 'p-4 sm:p-5', bodyClassName)}>{children}</div>
      {footer && <footer className="border-t border-border px-4 py-2.5 text-xs text-muted-foreground sm:px-5">{footer}</footer>}
    </section>
  );
}

/* ---------------------------------------------------------------- Toolbar */

/** Row of filters on the left and actions on the right (wraps on phones). */
export function Toolbar({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn('flex flex-wrap items-center gap-2.5', className)}>{children}</div>;
}
export function ToolbarSpacer() {
  return <div className="hidden flex-1 sm:block" />;
}

interface SearchInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function SearchInput({ value, onChange, className, placeholder = 'Search', ...rest }: SearchInputProps) {
  return (
    <div className={cn('relative w-full sm:w-64', className)}>
      <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-subtle-foreground" />
      <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder} className="h-8 pl-9 pr-8" {...rest} />
      {value && (
        <button type="button" onClick={() => onChange('')} aria-label="Clear search" className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-subtle-foreground hover:text-foreground">
          <Icon name="close" className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ Chips */

export interface ChipOption<T extends string = string> {
  value: T;
  label: React.ReactNode;
  count?: number;
}

interface ChipsProps<T extends string> {
  options: ChipOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label?: string;
  className?: string;
}

/** Single-select filter chips (categories, statuses, systems). */
export function Chips<T extends string>({ options, value, onChange, label, className }: ChipsProps<T>) {
  return (
    <div role="tablist" aria-label={label} className={cn('scrollbar-hide -mx-1 flex min-w-0 gap-1 overflow-x-auto px-1', className)}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="tab"
            aria-selected={on}
            onClick={() => onChange(o.value)}
            className={cn(
              'inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md px-2.5 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              on ? 'bg-accent font-medium text-foreground' : 'text-muted-foreground hover:bg-accent/70 hover:text-foreground',
            )}
          >
            {o.label}
            {o.count != null && <span className={cn('num text-xs', on ? 'text-muted-foreground' : 'text-subtle-foreground')}>{o.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

/* -------------------------------------------------------------- Sparkline */

export function Sparkline({ data, tone = 'info', className, fill = true }: { data: number[]; tone?: Tone; className?: string; fill?: boolean }) {
  const id = React.useId();
  if (!data || data.length < 2) return null;
  const w = 100, h = 28;
  const min = Math.min(...data), max = Math.max(...data);
  const span = max - min || 1;
  const pts = data.map((v, i) => [(i / (data.length - 1)) * w, h - 2 - ((v - min) / span) * (h - 4)] as const);
  const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className={cn('h-7 w-24', TONE_TEXT[tone], className)} aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.28" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill && <path d={`${line} L${w},${h} L0,${h} Z`} fill={`url(#${id})`} />}
      <path d={line} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

/* ------------------------------------------------------------ MetricStrip */

export interface Metric {
  label: string;
  value: React.ReactNode;
  /** Small line under the value: target, delta, unit. */
  hint?: React.ReactNode;
  tone?: Tone;
  spark?: number[];
  onClick?: () => void;
}

/**
 * Headline numbers as one strip divided by hairlines (not separate boxes).
 * 2 columns on phones, up to `columns` on desktop.
 */
export function MetricStrip({ items, columns = 4, className }: { items: Metric[]; columns?: 2 | 3 | 4 | 5 | 6; className?: string }) {
  const cols = { 2: 'lg:grid-cols-2', 3: 'lg:grid-cols-3', 4: 'lg:grid-cols-4', 5: 'lg:grid-cols-5', 6: 'lg:grid-cols-3 xl:grid-cols-6' }[columns];
  return (
    <dl className={cn('grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border bg-border', cols, className)}>
      {items.map((m) => {
        const Tag: any = m.onClick ? 'button' : 'div';
        return (
          <Tag
            key={m.label}
            {...(m.onClick ? { type: 'button', onClick: m.onClick } : {})}
            className={cn('flex min-w-0 items-end justify-between gap-3 bg-card p-4 text-left sm:p-5', m.onClick && 'transition-colors hover:bg-surface-2/70')}
          >
            <div className="min-w-0">
              <dt className="truncate text-sm text-muted-foreground">{m.label}</dt>
              <dd className="num mt-1.5 truncate text-2xl font-medium tracking-tight text-foreground">{m.value}</dd>
              {m.hint && <div className={cn('mt-0.5 truncate text-xs', m.tone && m.tone !== 'neutral' ? TONE_TEXT[m.tone] : 'text-muted-foreground')}>{m.hint}</div>}
            </div>
            {m.spark && <Sparkline data={m.spark} tone={m.tone && m.tone !== 'neutral' ? m.tone : 'info'} className="mb-1 shrink-0" />}
          </Tag>
        );
      })}
    </dl>
  );
}

/* ------------------------------------------------------------- KeyValues */

export interface KV {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}

/** Label / value rows divided by hairlines. `columns={2}` for wide areas. */
export function KeyValues({ items, columns = 1, className }: { items: KV[]; columns?: 1 | 2; className?: string }) {
  return (
    <dl className={cn(columns === 2 ? 'grid gap-x-10 sm:grid-cols-2' : '', className)}>
      {items.map((kv) => (
        <div key={kv.label} className="flex items-baseline justify-between gap-4 border-b border-border py-2 text-sm last:border-b-0">
          <dt className="shrink-0 text-muted-foreground">{kv.label}</dt>
          <dd className={cn('min-w-0 truncate text-right text-foreground', kv.mono && 'font-mono text-xs')}>{kv.value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  );
}

/* ------------------------------------------------------------------ Meter */

export function Meter({ value, max = 100, tone = 'info', className, label }: { value: number; max?: number; tone?: Tone; className?: string; label?: string }) {
  const pct = Math.max(0, Math.min(100, (value / (max || 1)) * 100));
  return (
    <div role="meter" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max} aria-label={label} className={cn('h-1 w-full overflow-hidden rounded-full bg-surface-3', className)}>
      <div className={cn('h-full rounded-full transition-[width] duration-slow ease-brand-out', TONE_BG[tone])} style={{ width: `${pct}%` }} />
    </div>
  );
}

/* -------------------------------------------------------------- CodeBlock */

export function CodeBlock({ children, className, maxHeight = 320, wrap }: { children: string; className?: string; maxHeight?: number; wrap?: boolean }) {
  const [copied, setCopied] = React.useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(children).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    }).catch(() => {});
  };
  return (
    <div className={cn('group relative overflow-hidden rounded-lg border border-border bg-surface-2/70', className)}>
      <button
        type="button"
        onClick={copy}
        aria-label="Copy"
        className="absolute right-2 top-2 flex h-7 items-center gap-1 rounded-md border border-border bg-card px-2 text-xs text-muted-foreground opacity-0 transition-opacity hover:text-foreground focus-visible:opacity-100 group-hover:opacity-100"
      >
        <Icon name={copied ? 'check' : 'copy'} className="h-3.5 w-3.5" /> {copied ? 'Copied' : 'Copy'}
      </button>
      <pre className={cn('scroll-thin overflow-auto p-3 font-mono text-xs leading-5 text-foreground', wrap && 'whitespace-pre-wrap break-words')} style={{ maxHeight }}>{children}</pre>
    </div>
  );
}

/* ------------------------------------------------------------ DetailSheet */

interface DetailSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: React.ReactNode;
  description?: React.ReactNode;
  /** Badges / status shown under the title. */
  meta?: React.ReactNode;
  /** Buttons pinned to the bottom. */
  footer?: React.ReactNode;
  /** Wider sheet for tables or code (default 520px). */
  wide?: boolean;
  children: React.ReactNode;
}

/** Right-hand sheet for inspecting one item without leaving the list. */
export function DetailSheet({ open, onOpenChange, title, description, meta, footer, wide, children }: DetailSheetProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className={cn('flex w-full flex-col gap-0 p-0', wide ? 'sm:max-w-[760px]' : 'sm:max-w-[520px]')}>
        <div className="border-b border-border px-5 pb-4 pt-5 pr-12">
          <SheetTitle className="text-lg font-medium leading-6">{title}</SheetTitle>
          <SheetDescription className={cn('mt-1 text-sm text-muted-foreground', !description && 'sr-only')}>{description || 'Details'}</SheetDescription>
          {meta && <div className="mt-3 flex flex-wrap items-center gap-2">{meta}</div>}
        </div>
        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-5">{children}</div>
        {footer && <div className="flex flex-wrap items-center justify-end gap-2 border-t border-border px-5 py-3">{footer}</div>}
      </SheetContent>
    </Sheet>
  );
}

/** Heading for a block inside a sheet or a page column. */
export function SubHeading({ children, action, className }: { children: React.ReactNode; action?: React.ReactNode; className?: string }) {
  return (
    <div className={cn('mb-2 flex items-baseline justify-between gap-3', className)}>
      <h3 className="text-sm font-medium text-foreground">{children}</h3>
      {action}
    </div>
  );
}

/* --------------------------------------------------------------- Timeline */

export interface TimelineItem {
  id: string | number;
  title: React.ReactNode;
  description?: React.ReactNode;
  status?: string;
  meta?: React.ReactNode;
  icon?: IconName;
  action?: React.ReactNode;
}

/** Ordered steps with a status rail (journey stages, pipeline steps, runs). */
export function Timeline({ items, className }: { items: TimelineItem[]; className?: string }) {
  return (
    <ol className={cn('relative', className)}>
      {items.map((it, i) => {
        const tone = toneOf(it.status);
        const done = tone === 'success';
        const live = LIVE.test(String(it.status || '').toLowerCase());
        return (
          <li key={it.id} className="relative flex gap-3.5 pb-5 last:pb-0">
            {i < items.length - 1 && <span className={cn('absolute left-[13px] top-7 h-[calc(100%-28px)] w-px', done ? 'bg-success/40' : 'bg-border-strong')} aria-hidden="true" />}
            <span
              className={cn(
                'relative mt-0.5 flex h-[27px] w-[27px] shrink-0 items-center justify-center rounded-full border text-xs font-medium',
                done && 'border-success/40 bg-success/10 text-success',
                live && 'border-brand/50 bg-brand/10 text-primary dark:text-brand-hi',
                tone === 'danger' && 'border-destructive/40 bg-destructive/10 text-destructive',
                tone === 'warning' && 'border-warning/40 bg-warning/10 text-warning',
                !done && !live && tone !== 'danger' && tone !== 'warning' && 'border-border-strong bg-card text-muted-foreground',
              )}
            >
              {done ? <Icon name="check" className="h-3 w-3" /> : live ? <span className="dot-live" /> : it.icon ? <Icon name={it.icon} className="h-3 w-3" /> : <span className="num">{i + 1}</span>}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <span className="text-sm font-medium text-foreground">{it.title}</span>
                <span className="flex items-center gap-3 text-xs text-muted-foreground">{it.meta}{it.action}</span>
              </div>
              {it.description && <p className="mt-0.5 text-sm text-muted-foreground">{it.description}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/* ------------------------------------------------------------------ Field */

export function Field({ label, hint, htmlFor, children, className }: { label: string; hint?: React.ReactNode; htmlFor?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('min-w-0', className)}>
      <label htmlFor={htmlFor} className="mb-1.5 block text-xs font-medium text-muted-foreground">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-subtle-foreground">{hint}</p>}
    </div>
  );
}

/* ------------------------------------------------------------ InlineError */

export function InlineError({ children, onRetry, className }: { children: React.ReactNode; onRetry?: () => void; className?: string }) {
  return (
    <div role="alert" className={cn('flex items-start gap-2.5 rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2.5 text-sm text-destructive', className)}>
      <Icon name="alert-triangle" className="mt-0.5" />
      <div className="min-w-0 flex-1">{children}</div>
      {onRetry && <button type="button" onClick={onRetry} className="shrink-0 font-medium underline underline-offset-4">Retry</button>}
    </div>
  );
}

/** Table wrapper: rounded, bordered, scrolls sideways on small screens. */
export function TableShell({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn('scroll-thin overflow-x-auto rounded-xl border border-border bg-card shadow-xs', className)}>{children}</div>;
}
