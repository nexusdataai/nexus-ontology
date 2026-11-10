/**
 * The pipeline of a journey as one stepper.
 *
 * Wide screens: numbered nodes on one horizontal line; the selected step's
 * detail is rendered below by the parent. Narrow screens: a vertical
 * timeline (`StepRail`, the kit Timeline with room for block content) with
 * the selected step's detail opening inside its item.
 *
 * One hue: done = primary, running = primary with a live dot and a flowing
 * connector, pending = neutral, failed = destructive.
 */
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

function Connector({ from, to }: { from: StepStatus; to: StepStatus }) {
  const reached = from === 'completed' && to !== 'pending';
  const flowing = from === 'completed' && to === 'running';
  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none absolute top-[17px] h-0.5 overflow-visible"
      style={{ left: 'calc(50% + 22px)', width: 'calc(100% - 44px)' }}
    >
      <line x1="0" y1="1" x2="100%" y2="1" strokeWidth="1.5" stroke={reached ? 'hsl(var(--primary))' : 'hsl(var(--border-strong))'} strokeOpacity={flowing ? 0.35 : 1} />
      {flowing && <line x1="0" y1="1" x2="100%" y2="1" strokeWidth="1.5" stroke="hsl(var(--brand-hi))" className="flow-line" />}
    </svg>
  );
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

  return (
    <div className="scroll-thin overflow-x-auto pb-1">
      <ol className="flex min-w-full" style={{ minWidth: steps.length * 104 }}>
        {steps.map((s, i) => {
          const selected = s.id === selectedId;
          return (
            <li key={s.id} className="rise relative min-w-0 flex-1" style={{ ['--i' as any]: i }}>
              {i < steps.length - 1 && <Connector from={s.status} to={steps[i + 1].status} />}
              <button
                type="button"
                onClick={() => onSelect(s.id, i)}
                aria-current={selected ? 'step' : undefined}
                aria-label={`Step ${i + 1}, ${s.name}, ${STATUS_WORD[s.status]}`}
                className="group flex w-full flex-col items-center px-1.5 pt-0.5 text-center focus-visible:outline-none"
              >
                <span className="rounded-full transition-transform duration-200 ease-brand group-hover:-translate-y-px group-focus-visible:ring-2 group-focus-visible:ring-ring">
                  <Node status={s.status} index={i} selected={selected} />
                </span>
                <span
                  className={cn(
                    'mt-2.5 line-clamp-2 text-xs leading-4 transition-colors duration-150',
                    selected ? 'font-medium text-foreground' : 'text-muted-foreground group-hover:text-foreground',
                    s.status === 'failed' && !selected && 'text-destructive',
                  )}
                >
                  {s.name}
                </span>
                <span className={cn('mt-2 h-0.5 w-8 rounded-full transition-colors duration-200', selected ? 'bg-primary' : 'bg-transparent')} aria-hidden="true" />
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export default StepPipeline;
