import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ds/Icon';
import { StatusPill } from '@/components/ds/kit';
import { cn } from '@/lib/utils';

interface PendingStep {
  step_id: string;
  stage_id?: string;
  tool?: string;
  params_preview?: Record<string, unknown>;
}

interface Props {
  runId: string;
  pending: PendingStep;
  onApprove: (stepId: string) => Promise<void> | void;
  onReject: (stepId: string) => Promise<void> | void;
  className?: string;
}

/**
 * Inline approval card the canvas surfaces above the toolbar when a
 * run pauses on a ``requires_approval`` step. Same envelope shape the
 * Copilot UI consumes, so the visual style stays consistent.
 */
export function PendingStepCard({ runId, pending, onApprove, onReject, className }: Props) {
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null);

  const handle = async (action: 'approve' | 'reject') => {
    setBusy(action);
    try {
      if (action === 'approve') await onApprove(pending.step_id);
      else await onReject(pending.step_id);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className={cn(
      'flex flex-wrap items-start gap-x-4 gap-y-3 rounded-xl border border-border-strong bg-card p-4 shadow-xs',
      className,
    )}>
      <div className="min-w-0 flex-1 basis-64">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
          <StatusPill tone="warning" variant="soft">Waiting for approval</StatusPill>
          <span className="text-sm font-medium text-foreground">
            Step <span className="font-mono text-xs">{pending.step_id}</span>
          </span>
        </div>
        <div className="mt-1.5 text-xs text-muted-foreground">
          {pending.tool && <>Tool <span className="font-mono text-foreground">{pending.tool}</span>, </>}
          run <span className="font-mono">{runId}</span>
          {pending.stage_id ? <>, stage <span className="font-mono">{pending.stage_id}</span></> : ''}
        </div>
        {pending.params_preview && (
          <pre className="scroll-thin mt-3 max-h-32 overflow-auto rounded-lg border border-border bg-surface-2/70 p-2.5 font-mono text-xs leading-5 text-foreground">
{JSON.stringify(pending.params_preview, null, 2)}
          </pre>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={!!busy}
          onClick={() => handle('reject')}
        >
          <Icon name={busy === 'reject' ? 'spinner' : 'close'} className={cn('h-3.5 w-3.5', busy === 'reject' && 'animate-spin')} />
          Reject
        </Button>
        <Button
          size="sm"
          disabled={!!busy}
          onClick={() => handle('approve')}
        >
          <Icon name={busy === 'approve' ? 'spinner' : 'check'} className={cn('h-3.5 w-3.5', busy === 'approve' && 'animate-spin')} />
          Approve
        </Button>
      </div>
    </div>
  );
}

export default PendingStepCard;
