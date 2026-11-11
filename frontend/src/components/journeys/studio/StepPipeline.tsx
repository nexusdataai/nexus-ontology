/**
 * The pipeline of a journey as one stepper.
 *
 * Wide screens: a vertical list of numbered steps (as in the original Journey
 * Studio); the parent renders the selected step's detail beside it. Narrow
 * screens: a vertical timeline (`StepRail`, the kit Timeline with room for
 * block content) with the selected step's detail opening inside its item.
 *
 * One hue: done = primary, running = primary with a live dot and a flowing
 * connector, pending = neutral, failed = destructive.
 */
import * as React from 'react';
import { useEffect, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Icon } from '@/components/ds/Icon';

export type StepStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface PipelineStep {
  id: string;
  name: string;
  description?: string;
  status: StepStatus;
  /** Short text on the right of a vertical item (duration, percent). */
  meta?: ReactNode;
}

/** True from the `lg` breakpoint up. Lets the parent mount the step detail once. */
export function useIsWide(query = '(min-width: 1024px)'): boolean {
  const [wide, setWide] = useState(() => (typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(query).matches : true));
  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia(query);
    const on = () => setWide(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, [query]);
  return wide;
}

interface StepPipelineProps {
  steps: PipelineStep[];
  selectedId?: string;
  onSelect: (id: string, index: number) => void;
  wide: boolean;
  /** Detail of the selected step. Rendered inside the item on narrow screens only. */
  detail?: ReactNode;
}

function Node({ status, index, selected }: { status: StepStatus; index: number; selected: boolean }) {
  return (
    <span
      className={cn(
        'relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm font-medium transition-[box-shadow,border-color,background-color] duration-200 ease-brand',
        status === 'completed' && 'border-primary bg-primary text-primary-foreground',
        status === 'running' && 'border-brand bg-card text-primary dark:text-brand-hi',
        status === 'failed' && 'border-destructive/60 bg-card text-destructive',
        status === 'pending' && 'border-border-strong bg-card text-muted-foreground',
        selected && 'ring-2 ring-ring/50 ring-offset-2 ring-offset-card',
      )}
    >
      {status === 'completed' ? <Icon name="check" className="h-3.5 w-3.5" />
        : status === 'running' ? <span className="dot-live" />
        : status === 'failed' ? <Icon name="close" className="h-3.5 w-3.5" />
        : <span className="num">{index + 1}</span>}
    </span>
  );
}

export interface StepRailItem {
  id: string | number;
  /** 'pending' | 'running' | 'completed' | 'failed' | 'rejected' */
  status: string;
  title: ReactNode;
  meta?: ReactNode;
  action?: ReactNode;
  /** Block content under the title (detail, results, code). */
  body?: ReactNode;
}

/** Vertical steps with a status rail. Same look as the kit Timeline; the body may hold blocks. */
export function StepRail({ items, className }: { items: StepRailItem[]; className?: string }) {
  return (
    <ol className={cn('relative', className)}>
      {items.map((it, i) => {
        const done = it.status === 'completed';
        const live = it.status === 'running';
        const failed = it.status === 'failed';
        const warn = it.status === 'rejected';
        return (
          <li key={it.id} className="relative flex gap-3.5 pb-5 last:pb-0">
            {i < items.length - 1 && <span className={cn('absolute left-[13px] top-7 h-[calc(100%-28px)] w-px', done ? 'bg-primary/50' : 'bg-border-strong')} aria-hidden="true" />}
            <span
              className={cn(
                'relative mt-0.5 flex h-[27px] w-[27px] shrink-0 items-center justify-center rounded-full border text-xs font-medium',
                done && 'border-primary bg-primary text-primary-foreground',
                live && 'border-brand bg-card text-primary dark:text-brand-hi',
                failed && 'border-destructive/60 bg-card text-destructive',
                warn && 'border-warning/60 bg-card text-warning',
                !done && !live && !failed && !warn && 'border-border-strong bg-card text-muted-foreground',
              )}
            >
              {done ? <Icon name="check" className="h-3 w-3" />
                : live ? <span className="dot-live" />
                : failed ? <Icon name="close" className="h-3 w-3" />
                : warn ? <Icon name="minus" className="h-3 w-3" />
                : <span className="num">{i + 1}</span>}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <span className="min-w-0 text-sm font-medium text-foreground">{it.title}</span>
                <span className="flex items-center gap-3 text-xs text-muted-foreground">{it.meta}{it.action}</span>
              </div>
              {it.body && <div className="mt-1 text-sm text-muted-foreground">{it.body}</div>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

const STATUS_WORD: Record<StepStatus, string> = { pending: 'not started', running: 'running', completed: 'done', failed: 'failed' };

export function StepPipeline({ steps, selectedId, onSelect, wide, detail }: StepPipelineProps) {
  if (!wide) {
    return (
      <StepRail
        items={steps.map((s, i) => {
          const selected = s.id === selectedId;
          return {
            id: s.id,
            status: s.status,
            meta: s.meta,
            title: (
              <button
                type="button"
                onClick={() => onSelect(s.id, i)}
                aria-expanded={selected}
                className={cn('rounded-sm text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring', s.status === 'failed' && 'text-destructive')}
              >
                {s.name}
              </button>
            ),
            body: selected && detail ? <div className="mt-2 text-foreground">{detail}</div> : undefined,
          };
        })}
      />
    );
  }

  // Wide screens: the steps run top to bottom, as in the original Journey
  // Studio. Every step is visible without scrolling sideways; the parent shows
  // the selected step's detail beside the list.
  return (
    <ol className="relative">
      {steps.map((s, i) => {
        const selected = s.id === selectedId;
        const next = steps[i + 1];
        const reached = !!next && s.status === 'completed' && next.status !== 'pending';
        const flowing = !!next && s.status === 'completed' && next.status === 'running';
        return (
          <li key={s.id} className="rise relative" style={{ ['--i' as string]: i } as React.CSSProperties}>
            {next && (
              <span
                aria-hidden="true"
                className={cn('absolute left-[29px] top-[44px] h-[calc(100%-36px)] w-px', reached ? 'bg-primary/70' : 'bg-border-strong', flowing && 'animate-pulse bg-brand')}
              />
            )}
            <button
              type="button"
              onClick={() => onSelect(s.id, i)}
              aria-current={selected ? 'step' : undefined}
              aria-label={`Step ${i + 1}, ${s.name}, ${STATUS_WORD[s.status]}`}
              className={cn(
                'group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                selected ? 'bg-accent' : 'hover:bg-surface-2',
              )}
            >
              <Node status={s.status} index={i} selected={selected} />
              <span className="min-w-0 flex-1">
                <span className={cn('block truncate text-sm', selected ? 'font-medium text-foreground' : 'text-foreground', s.status === 'failed' && 'text-destructive')}>{s.name}</span>
                <span className={cn('block text-xs capitalize', s.status === 'running' ? 'text-primary dark:text-brand-hi' : s.status === 'failed' ? 'text-destructive' : 'text-muted-foreground')}>{STATUS_WORD[s.status]}</span>
              </span>
              {s.meta && <span className="shrink-0 text-xs text-muted-foreground">{s.meta}</span>}
              <Icon name="chevron-right" className={cn('h-3.5 w-3.5 shrink-0 transition-opacity', selected ? 'text-foreground opacity-100' : 'text-subtle-foreground opacity-0 group-hover:opacity-100')} />
            </button>
          </li>
        );
      })}
    </ol>
  );
}

export default StepPipeline;
