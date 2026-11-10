import { useState } from 'react';
import { StatusPill, type Tone } from '@/components/ds/kit';
import { Icon } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';

/**
 * Shared pieces for the platform diagnostics panels (dashboards, virtual
 * data, simulators …). The per-solution panels use SolutionDiagnosticsView.
 */
const LABEL: Record<string, string> = {
  pass: 'Passed', ok: 'OK', healthy: 'Healthy', warn: 'Warning', degraded: 'Degraded', fail: 'Failed',
  unhealthy: 'Unhealthy', no_data: 'No data', missing: 'Missing', inactive: 'Inactive', error: 'Error',
};
const TONE: Record<string, Tone> = { no_data: 'danger', missing: 'danger', inactive: 'warning' };

/** Kept for callers that read the label map directly. */
export const STATUS_BADGE: Record<string, { label: string }> = Object.fromEntries(Object.entries(LABEL).map(([k, label]) => [k, { label }]));

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return <StatusPill status={status} tone={TONE[status]} variant="soft">{label ?? LABEL[status] ?? status.replace(/_/g, ' ')}</StatusPill>;
}

export function Section({
  title,
  icon: IconCmp,
  status,
  defaultOpen,
  children,
  rightSlot,
}: {
  title: string;
  icon: React.ElementType;
  status: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  rightSlot?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen ?? true);
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
      <div className="flex items-center gap-3 px-5 py-3.5">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          className="flex min-w-0 flex-1 items-center gap-3 rounded text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <IconCmp className="h-[18px] w-[18px] shrink-0 text-muted-foreground" strokeWidth={1.5} />
          <span className="truncate text-md font-medium text-foreground">{title}</span>
        </button>
        {rightSlot}
        <StatusBadge status={status} />
        <button type="button" onClick={() => setOpen(!open)} aria-label={open ? 'Collapse' : 'Expand'} className="rounded p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Icon name="chevron-down" className={cn('h-4 w-4 transition-transform duration-200', open && 'rotate-180')} />
        </button>
      </div>
      {open && <div className="animate-fade-in border-t border-border px-5 py-4">{children}</div>}
    </section>
  );
}

export function formatLatency(ms?: number | null): string {
  if (ms == null) return '-';
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}
