import { useState } from 'react';
import { CheckCircle2, ChevronDown, ChevronRight, MinusCircle, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
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

const STATUS_PILL: Record<string, string> = {
  completed: 'bg-green-500/15 text-green-300 border-green-500/30',
  awaiting_step_approval: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  failed: 'bg-red-500/15 text-red-300 border-red-500/30',
};

function statusIcon(status?: string) {
  if (status === 'completed') return <CheckCircle2 className="h-3.5 w-3.5 text-green-300" />;
  if (status === 'failed') return <XCircle className="h-3.5 w-3.5 text-red-300" />;
  return <MinusCircle className="h-3.5 w-3.5 text-amber-300" />;
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
    <div className={cn('rounded-md border bg-card/40 p-2 space-y-2', className)}>
      <div className="flex items-center gap-2 px-1">
        {statusIcon(status)}
        <span className="text-xs font-medium">Run results</span>
        {run_id && (
          <span className="text-[10px] font-mono text-muted-foreground">{run_id}</span>
        )}
        {status && (
          <Badge variant="outline" className={cn('text-[10px] ml-auto', STATUS_PILL[status] || '')}>
            {status}
          </Badge>
        )}
      </div>
      {error && (
        <div className="text-[11px] text-red-300 bg-red-500/10 border border-red-500/30 rounded p-2">
          {error}
        </div>
      )}
      {stepEntries.length === 0 && !error && (
        <div className="text-[11px] text-muted-foreground px-1">No step results yet.</div>
      )}
      <div className="space-y-1">
        {stepEntries.map(([stepId, result]) => {
          const isOpen = expanded.has(stepId);
          const completed = (completed_steps || []).includes(stepId);
          const errored = result && typeof result === 'object' && 'error' in (result as any);
          return (
            <div key={stepId} className="border rounded">
              <button
                className="w-full flex items-center gap-2 px-2 py-1 text-left hover:bg-muted/30"
                onClick={() => toggle(stepId)}
              >
                {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                {errored
                  ? <XCircle className="h-3 w-3 text-red-300" />
                  : completed
                    ? <CheckCircle2 className="h-3 w-3 text-green-300" />
                    : <MinusCircle className="h-3 w-3 text-amber-300" />}
                <span className="font-mono text-[11px] truncate flex-1">{stepId}</span>
              </button>
              {isOpen && (
                <pre className="text-[10px] font-mono bg-muted/30 p-2 max-h-48 overflow-auto whitespace-pre-wrap">
{JSON.stringify(result, null, 2)}
                </pre>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default RunResultsPanel;
