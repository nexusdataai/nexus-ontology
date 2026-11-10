import { useEffect, useMemo, useState } from 'react';
import { Search, AppWindow } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import type { ViewSummary } from '@/lib/foundry/model';

interface SolutionViewPickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  availableViews: ViewSummary[];
  attachedIds: string[];
  onConfirm: (selectedViewIds: string[]) => void | Promise<void>;
}

export function SolutionViewPicker({
  open,
  onOpenChange,
  availableViews,
  attachedIds,
  onConfirm,
}: SolutionViewPickerProps) {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelected(new Set());
    }
  }, [open]);

  const attachedSet = useMemo(() => new Set(attachedIds), [attachedIds]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return availableViews.filter((v) => {
      if (!q) return true;
      return (
        v.name.toLowerCase().includes(q) ||
        (v.description || '').toLowerCase().includes(q)
      );
    });
  }, [availableViews, query]);

  const toggle = (viewId: string) => {
    if (attachedSet.has(viewId)) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(viewId)) next.delete(viewId);
      else next.add(viewId);
      return next;
    });
  };

  const handleConfirm = () => {
    onConfirm(Array.from(selected));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-sm">Add Views</DialogTitle>
          <DialogDescription className="text-xs">
            Pick one or more Views to attach to this Solution.
          </DialogDescription>
        </DialogHeader>

        <div className="relative">
          <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search views..."
            className="h-7 pl-8 text-xs"
            autoFocus
          />
        </div>

        <ScrollArea className="max-h-72 pr-2">
          {filtered.length === 0 ? (
            <div className="text-xs text-muted-foreground p-4 text-center">
              No views match.
            </div>
          ) : (
            <div className="space-y-1">
              {filtered.map((v) => {
                const isAttached = attachedSet.has(v.viewId);
                const isSelected = selected.has(v.viewId);
                return (
                  <label
                    key={v.viewId}
                    className={cn(
                      'flex items-start gap-2 p-2 rounded-md border text-xs transition-colors',
                      isAttached
                        ? 'opacity-60 bg-muted cursor-not-allowed'
                        : 'cursor-pointer hover:bg-muted/50',
                      isSelected && 'border-primary bg-primary/5',
                    )}
                  >
                    <Checkbox
                      checked={isAttached || isSelected}
                      disabled={isAttached}
                      onCheckedChange={() => toggle(v.viewId)}
                      className="mt-0.5"
                    />
                    <AppWindow className="h-3.5 w-3.5 mt-0.5 text-muted-foreground shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium truncate">{v.name}</div>
                      {v.description && (
                        <div className="text-xs text-muted-foreground truncate">
                          {v.description}
                        </div>
                      )}
                      <div className="text-xs text-muted-foreground">
                        {v.tabCount} tabs
                        {isAttached && ' · already attached'}
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button size="sm" onClick={handleConfirm} disabled={selected.size === 0}>
            Add {selected.size > 0 ? `(${selected.size})` : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default SolutionViewPicker;
