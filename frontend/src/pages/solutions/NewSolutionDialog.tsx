import { useEffect, useMemo, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { APP_REGISTRY, type AppConfig } from '@/config/appRegistry';
import { solutionService } from '@/services/solutionService';
import type { Solution } from '@/lib/foundry/model';

interface NewSolutionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** appIds that are already linked to a backend Solution; filtered out. */
  excludedAppIds: string[];
  onCreated: (solution: Solution) => void;
}

export function NewSolutionDialog({
  open,
  onOpenChange,
  excludedAppIds,
  onCreated,
}: NewSolutionDialogProps) {
  const [selected, setSelected] = useState<AppConfig | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  const candidateApps = useMemo(() => {
    const excluded = new Set(excludedAppIds);
    return APP_REGISTRY.filter((a) => !excluded.has(a.id));
  }, [excludedAppIds]);

  useEffect(() => {
    if (open) {
      setSelected(null);
      setName('');
      setDescription('');
    }
  }, [open]);

  const handleSelectApp = (app: AppConfig) => {
    setSelected(app);
    setName(app.name);
    setDescription(app.description);
  };

  const handleCreate = async () => {
    if (!selected || !name.trim()) return;
    setSaving(true);
    try {
      const created = await solutionService.create({
        appId: selected.id,
        name: name.trim(),
        description: description.trim() || undefined,
      });
      toast.success('Solution created');
      onCreated(created);
      onOpenChange(false);
    } catch (e: any) {
      toast.error(e?.message || 'Failed to create solution');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-sm">New Solution</DialogTitle>
          <DialogDescription className="text-xs">
            Pick an app to back this Solution. Each app can only be linked once.
          </DialogDescription>
        </DialogHeader>

        {candidateApps.length === 0 ? (
          <div className="text-xs text-muted-foreground p-4 text-center border border-dashed rounded-md">
            All apps are already linked to a Solution.
          </div>
        ) : (
          <>
            <div className="space-y-1.5">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Linked App
              </div>
              <ScrollArea className="max-h-44 pr-2">
                <div className="space-y-1">
                  {candidateApps.map((app) => {
                    const Icon = app.icon;
                    const isActive = selected?.id === app.id;
                    return (
                      <button
                        key={app.id}
                        onClick={() => handleSelectApp(app)}
                        className={cn(
                          'w-full flex items-start gap-2 p-2 rounded-md border text-left text-xs transition-colors',
                          isActive
                            ? 'border-primary bg-primary/5'
                            : 'hover:bg-muted/50',
                        )}
                      >
                        <div className={`p-1 rounded bg-gradient-to-br ${app.color} shrink-0`}>
                          <Icon className="h-3 w-3 text-white" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="font-medium truncate">{app.name}</div>
                          <div className="text-[10px] text-muted-foreground truncate">
                            {app.id}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </ScrollArea>
            </div>

            <div className="space-y-1.5">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Name
              </div>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Solution name"
                className="h-7 text-xs"
                disabled={!selected}
              />
            </div>

            <div className="space-y-1.5">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Description
              </div>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional"
                className="text-xs min-h-16"
                disabled={!selected}
              />
            </div>
          </>
        )}

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleCreate}
            disabled={!selected || !name.trim() || saving}
          >
            {saving ? 'Creating...' : 'Create'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default NewSolutionDialog;
