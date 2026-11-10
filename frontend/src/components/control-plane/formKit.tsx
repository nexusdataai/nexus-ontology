/**
 * Small form pieces shared by the policy, workflow and integration form
 * builders, so the three editors read as one. Presentational only.
 */
import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icon } from '@/components/ds/Icon';
import { SystemLogo } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';

/** The scrolling body of a form builder. */
export function FormBody({ children }: { children: React.ReactNode }) {
  return <div className="max-w-3xl space-y-8 px-4 py-6 sm:px-6">{children}</div>;
}

/** A form section: heading, one-line hint, then the fields. */
export function FormSection({ title, hint, count, children }: { title: string; hint?: string; count?: number; children: React.ReactNode }) {
  return (
    <section className="border-t border-border pt-6 first:border-t-0 first:pt-0">
      <div className="mb-4">
        <h3 className="text-md font-medium text-foreground">
          {title} {count != null && <span className="num text-sm font-normal text-muted-foreground">{count}</span>}
        </h3>
        {hint && <p className="mt-0.5 text-sm text-muted-foreground">{hint}</p>}
      </div>
      {children}
    </section>
  );
}

interface ChoiceProps<T extends string> {
  options: { value: T; label: React.ReactNode }[];
  /** One value, or several when `multiple` is set. */
  value: T | T[];
  onChange: (value: T) => void;
  multiple?: boolean;
  label: string;
}

/** Pick one (or several) of a few options. */
export function Choice<T extends string>({ options, value, onChange, multiple, label }: ChoiceProps<T>) {
  const isOn = (v: T) => (Array.isArray(value) ? value.includes(v) : value === v);
  return (
    <div role={multiple ? 'group' : 'radiogroup'} aria-label={label} className="flex flex-wrap gap-1.5">
      {options.map(o => {
        const on = isOn(o.value);
        return (
          <button
            key={o.value}
            type="button"
            role={multiple ? 'checkbox' : 'radio'}
            aria-checked={on}
            onClick={() => onChange(o.value)}
            className={cn(
              'inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              on ? 'border-primary/50 bg-primary/10 font-medium text-foreground' : 'border-border-strong text-muted-foreground hover:bg-accent/60 hover:text-foreground',
            )}
          >
            {on && <Icon name="check" className="h-3 w-3 text-primary dark:text-brand-hi" />}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

const NONE = '__none__';

interface SystemSelectProps {
  value: string;
  onChange: (value: string) => void;
  systems: string[];
  /** Adds a "no system" entry and shows this text when nothing is chosen. */
  emptyLabel?: string;
  label: string;
  className?: string;
}

/** Source-system picker with the system's logo on every option. */
export function SystemSelect({ value, onChange, systems, emptyLabel, label, className }: SystemSelectProps) {
  const options = value && !systems.includes(value) ? [value, ...systems] : systems;
  return (
    <Select value={value || (emptyLabel ? NONE : undefined)} onValueChange={(v) => onChange(v === NONE ? '' : v)}>
      <SelectTrigger aria-label={label} className={cn('h-9', className)}>
        <SelectValue placeholder="Choose a system" />
      </SelectTrigger>
      <SelectContent>
        {emptyLabel && <SelectItem value={NONE}>{emptyLabel}</SelectItem>}
        {options.map(s => (
          <SelectItem key={s} value={s}>
            <span className="inline-flex items-center gap-2"><SystemLogo system={s} size="xs" /> {s}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/** Icon button that removes a row. */
export function RemoveButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <Button type="button" variant="ghost" size="icon-sm" onClick={onClick} aria-label={label} className="shrink-0 text-subtle-foreground hover:text-destructive">
      <Icon name="trash" className="h-3.5 w-3.5" />
    </Button>
  );
}

/** "Add …" button under a list of rows. */
export function AddButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <Button type="button" variant="outline" size="sm" onClick={onClick}>
      <Icon name="plus" /> {children}
    </Button>
  );
}

/** Shown where a repeatable list has no rows yet. */
export function NoRows({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 text-sm text-subtle-foreground">{children}</p>;
}
