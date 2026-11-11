/**
 * Shared layout for the three "Usage and cost" screens (end usage, data
 * protection, cost). The backend does not report these figures yet, so the
 * screens show no numbers: each one lists what it will report and says, in
 * one clear line at the top, that it is not connected.
 */
import * as React from 'react';
import { Icon } from '@/components/ds/Icon';
import { KeyValues, type KV } from '@/components/ds/kit';

export function OpsPreview({ title, description, coming, children }: { title: string; description: string; coming: string; children: React.ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-6">
      <header>
        <h2 className="text-xl font-medium tracking-tight text-foreground">{title}</h2>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>
      </header>
      <p className="flex items-start gap-2.5 rounded-xl border border-border bg-surface-2/60 px-4 py-3 text-sm text-muted-foreground">
        <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0 text-primary dark:text-brand-hi" />
        <span><span className="font-medium text-foreground">Not connected yet.</span> {coming}</span>
      </p>
      {children}
    </div>
  );
}

/** The value shown for a figure the backend does not report yet. */
export const NOT_CONNECTED = <span className="text-subtle-foreground">Not connected</span>;

/** A list of figures a screen will report, none of them available yet. */
export const pending = (labels: string[]): KV[] => labels.map(label => ({ label, value: NOT_CONNECTED }));

/** A titled list of facts, optionally with a headline number and an action. */
export function OpsFacts({ title, headline, unit, note, items, action, index = 0 }: { title: string; headline?: React.ReactNode; unit?: string; note?: React.ReactNode; items: KV[]; action?: React.ReactNode; index?: number }) {
  return (
    <section className="rise flex flex-col rounded-xl border border-border bg-card p-5 shadow-xs" style={{ ['--i' as any]: index }}>
      <h3 className="text-sm text-muted-foreground">{title}</h3>
      {headline !== undefined && (
        <p className="mt-2 flex items-baseline gap-1.5">
          <span className="num text-3xl font-medium tracking-tight text-foreground">{headline}</span>
          {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
        </p>
      )}
      {note && <p className="mt-2 text-sm text-foreground">{note}</p>}
      <div className="mt-3 flex-1"><KeyValues items={items} /></div>
      {action && <div className="mt-4">{action}</div>}
    </section>
  );
}
