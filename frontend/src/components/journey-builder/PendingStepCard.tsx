import { useState } from 'react';
import { Check, Loader2, ShieldCheck, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
      'rounded-md border border-amber-500/40 bg-amber-500/10 text-foreground p-3 flex items-start gap-3',
      className,
    )}>
      <ShieldCheck className="h-5 w-5 text-amber-300 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium">
          Approval required for step <span className="font-mono">{pending.step_id}</span>
          {pending.tool && (
            <Badge variant="outline" className="ml-2 text-[10px] bg-card/60">{pending.tool}</Badge>
          )}
        </div>
        <div className="text-[11px] text-muted-foreground mt-0.5">
          Run <span className="font-mono">{runId}</span>
          {pending.stage_id ? ` -- stage ${pending.stage_id}` : ''}
        </div>
        {pending.params_preview && (
          <pre className="text-[10px] font-mono bg-card/40 border rounded p-2 mt-2 max-h-32 overflow-auto">
{JSON.stringify(pending.params_preview, null, 2)}
          </pre>
        )}
      </div>
      <div className="flex flex-col gap-1 shrink-0">
        <Button
          size="sm"
          className="bg-green-600 hover:bg-green-700 text-white"
          disabled={!!busy}
          onClick={() => handle('approve')}
        >
          {busy === 'approve' ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Check className="h-3.5 w-3.5 mr-1" />}
          Approve
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={!!busy}
          onClick={() => handle('reject')}
        >
          {busy === 'reject' ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <X className="h-3.5 w-3.5 mr-1" />}
          Reject
        </Button>
      </div>
    </div>
  );
}

export default PendingStepCard;
