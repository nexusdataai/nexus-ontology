import { useState, type CSSProperties } from 'react';
import { Icon } from '@/components/ds/Icon';
import { InlineError, StatusPill } from '@/components/ds/kit';
import { cn } from '@/lib/utils';

interface RunEnvelope {
  run_id?: string | null;
  status?: string;
  step_results?: Record<string, any>;
  completed_steps?: string[];
  pending_step?: { step_id: string; tool?: string } | null;
  error?: string | null;
}

interface Props {
  envelope: RunEnvelope | null;
  className?: string;
}

/**
 * Collapsible panel showing per-step results from the last run.
 *
 * Renders the canonical RunEnvelope shape from /api/v1/yaml-journeys/run
 * (also returned by /journey-builder/run after the rewrite). Each step
 * is one collapsible row; the top header shows overall status + run id.
 */
export function RunResultsPanel({ envelope, className }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  if (!envelope) return null;

  const { run_id, status, step_results, completed_steps, error } = envelope;
  const stepEntries = step_results ? Object.entries(step_results) : [];

  const toggle = (k: string) => {
    setExpanded((curr) => {
      const next = new Set(curr);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });
  };

  return (
    <div className={cn('overflow-hidden rounded-xl border border-border bg-card', className)}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border px-3 py-2.5">
        <span className="text-sm font-medium text-foreground">Run results</span>
        {run_id && (
          <span className="min-w-0 truncate font-mono text-xs text-muted-foreground" title={run_id}>{run_id}</span>
        )}
        {status && <StatusPill status={status} className="ml-auto" />}
      </div>
      {error && <InlineError className="m-3">{error}</InlineError>}
      {stepEntries.length === 0 && !error && (
        <div className="px-3 py-3 text-sm text-muted-foreground">No step results yet.</div>
      )}
      {stepEntries.length > 0 && (
        <ul>
          {stepEntries.map(([stepId, result], i) => {
            const isOpen = expanded.has(stepId);
            const completed = (completed_steps || []).includes(stepId);
            const errored = result && typeof result === 'object' && 'error' in (result as any);
            return (
              <li key={stepId} className="rise border-b border-border last:border-b-0" style={{ '--i': i } as CSSProperties}>
                <button
                  type="button"
                  aria-expanded={isOpen}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-surface-2/60 focus-visible:bg-surface-2/60 focus-visible:outline-none"
                  onClick={() => toggle(stepId)}
                >
                  <Icon name={isOpen ? 'chevron-down' : 'chevron-right'} className="h-3 w-3 shrink-0 text-subtle-foreground" />
                  <span className="min-w-0 flex-1 truncate font-mono text-xs text-foreground">{stepId}</span>
                  {errored
                    ? <StatusPill tone="danger">Failed</StatusPill>
                    : completed
                      ? <StatusPill tone="success">Done</StatusPill>
                      : <StatusPill tone="warning">Waiting</StatusPill>}
                </button>
                {isOpen && (
                  <pre className="scroll-thin max-h-48 overflow-auto whitespace-pre-wrap border-t border-border bg-surface-2/70 p-3 font-mono text-xs leading-5 text-foreground">
{JSON.stringify(result, null, 2)}
                  </pre>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default RunResultsPanel;
