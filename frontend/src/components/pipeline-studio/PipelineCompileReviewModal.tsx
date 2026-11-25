import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export interface CompilePreview {
  valid: boolean;
  enabledSteps?: string[];
  issues?: { message: string }[];
  warnings?: { message: string }[];
  compileMode?: string;
}

export default function PipelineCompileReviewModal({
  open,
  preview,
  deploying,
  onClose,
  onConfirmDeploy,
}: {
  open: boolean;
  preview: CompilePreview | null;
  deploying: boolean;
  onClose: () => void;
  onConfirmDeploy: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Review &amp; deploy</DialogTitle>
          <DialogDescription>Compiled pipeline steps and validation before production snapshot.</DialogDescription>
        </DialogHeader>
        {preview && (
          <div className="space-y-3 text-sm">
            <p className="text-muted-foreground">
              Mode: <span className="font-mono text-foreground">{preview.compileMode || 'etl_linear'}</span>
            </p>
            {preview.enabledSteps?.length ? (
              <div>
                <p className="text-xs font-medium text-muted-foreground">Runtime steps</p>
                <ul className="mt-1 list-inside list-disc font-mono text-xs">
                  {preview.enabledSteps.map(s => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {preview.issues?.map((i, idx) => (
              <p key={`e-${idx}`} className="text-destructive">{i.message}</p>
            ))}
            {preview.warnings?.map((w, idx) => (
              <p key={`w-${idx}`} className="text-amber-600 dark:text-amber-400">{w.message}</p>
            ))}
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={onConfirmDeploy}
            disabled={!preview?.valid || deploying}
          >
            {deploying ? 'Deploying…' : 'Deploy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}