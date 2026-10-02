import { useMemo, useState } from 'react';
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Plus, Trash2, Loader2, AppWindow, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import type { Solution, ViewSummary, SolutionViewLink } from '@/lib/foundry/model';
import type { AppConfig } from '@/config/appRegistry';
import { solutionService } from '@/services/solutionService';
import { SolutionViewPicker } from './SolutionViewPicker';

interface SolutionViewsEditorProps {
  /** The backing app for lazy-create when no Solution row exists yet. */
  app: AppConfig;
  /** Existing backend Solution, or null until the user maps the first view. */
  solution: Solution | null;
  availableViews: ViewSummary[];
  onSolutionChanged: (next: Solution) => void;
}

export function SolutionViewsEditor({
  app,
  solution,
  availableViews,
  onSolutionChanged,
}: SolutionViewsEditorProps) {
  const nav = useNavigate();
  const [reordering, setReordering] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const viewLookup = useMemo(() => {
    const m = new Map<string, ViewSummary>();
    availableViews.forEach((v) => m.set(v.viewId, v));
    return m;
  }, [availableViews]);

  const handleDragEnd = async (event: DragEndEvent) => {
    if (!solution) return;
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = solution.views.findIndex((v) => v.viewId === active.id);
    const newIndex = solution.views.findIndex((v) => v.viewId === over.id);
    if (oldIndex < 0 || newIndex < 0) return;

    const reordered = arrayMove(solution.views, oldIndex, newIndex);
    const optimistic: Solution = { ...solution, views: reordered.map((v, i) => ({ ...v, order: i })) };
    onSolutionChanged(optimistic);

    setReordering(true);
    try {
      const updated = await solutionService.reorderViews(
        solution.solutionId,
        reordered.map((v) => v.viewId),
      );
      onSolutionChanged(updated);
    } catch (e: any) {
      toast.error(e?.message || 'Failed to reorder views');
      onSolutionChanged(solution);
    } finally {
      setReordering(false);
    }
  };

  const handleRemove = async (viewId: string) => {
    if (!solution) return;
    setRemovingId(viewId);
    try {
      const updated = await solutionService.removeView(solution.solutionId, viewId);
      onSolutionChanged(updated);
      toast.success('View detached from solution');
    } catch (e: any) {
      toast.error(e?.message || 'Failed to remove view');
    } finally {
      setRemovingId(null);
    }
  };

  const ensureSolution = async (): Promise<Solution> => {
    if (solution) return solution;
    setCreating(true);
    try {
      const created = await solutionService.create({
        appId: app.id,
        name: app.name,
        description: app.description,
      });
      onSolutionChanged(created);
      return created;
    } finally {
      setCreating(false);
    }
  };

  const handlePicked = async (newViewIds: string[]) => {
    setPickerOpen(false);
    if (newViewIds.length === 0) return;
    try {
      let current = await ensureSolution();
      for (const vid of newViewIds) {
        current = await solutionService.addView(current.solutionId, vid);
      }
      onSolutionChanged(current);
      toast.success(
        newViewIds.length === 1 ? 'View mapped' : `${newViewIds.length} views mapped`,
      );
    } catch (e: any) {
      toast.error(e?.message || 'Failed to map view');
    }
  };

  const attachedIds = solution?.views.map((v) => v.viewId) ?? [];
  const views = solution?.views ?? [];

  return (
    <div className="border-t bg-muted/20 p-3 space-y-2">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Views mapped to this Solution
          {(reordering || creating) && (
            <Loader2 className="inline-block h-3 w-3 ml-2 animate-spin text-muted-foreground" />
          )}
        </div>
        <Button
          size="sm"
          variant="outline"
          className="h-7"
          onClick={() => setPickerOpen(true)}
          disabled={creating}
        >
          <Plus className="h-3.5 w-3.5 mr-1" /> Add View
        </Button>
      </div>

      {views.length === 0 ? (
        <div className="border border-dashed border-border rounded-md p-4 text-center text-xs text-muted-foreground">
          No views mapped yet. Click "Add View" to surface dashboards as menu items
          inside <span className="font-medium text-foreground">{app.shortName}</span>.
        </div>
      ) : (
        <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
          <SortableContext
            items={views.map((v) => v.viewId)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-1.5">
              {views.map((link) => (
                <SortableRow
                  key={link.viewId}
                  link={link}
                  summary={viewLookup.get(link.viewId)}
                  removing={removingId === link.viewId}
                  onRemove={() => handleRemove(link.viewId)}
                  onOpen={() => nav(`/views/${link.viewId}`)}
                  onEdit={() => nav(`/views/builder/${link.viewId}`)}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}

      <SolutionViewPicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        availableViews={availableViews}
        attachedIds={attachedIds}
        onConfirm={handlePicked}
      />
    </div>
  );
}

interface SortableRowProps {
  link: SolutionViewLink;
  summary?: ViewSummary;
  removing: boolean;
  onRemove: () => void;
  onOpen: () => void;
  onEdit: () => void;
}

function SortableRow({ link, summary, removing, onRemove, onOpen, onEdit }: SortableRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: link.viewId,
  });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const label = link.displayName || link.name || summary?.name || link.viewId;
  const description = summary?.description;
  const tabCount = summary?.tabCount ?? 0;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-2 px-2 py-1.5 rounded-md border bg-background',
        isDragging && 'ring-1 ring-primary',
      )}
    >
      <span
        {...listeners}
        {...attributes}
        className="cursor-grab active:cursor-grabbing text-muted-foreground/70 hover:text-foreground p-1"
      >
        <GripVertical className="h-3.5 w-3.5" />
      </span>
      <AppWindow className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="text-xs font-medium truncate">{label}</div>
        {description && (
          <div className="text-[10px] text-muted-foreground truncate">{description}</div>
        )}
      </div>
      <span className="text-[10px] text-muted-foreground shrink-0">{tabCount} tabs</span>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 text-muted-foreground"
        onClick={onOpen}
        title="Open view"
      >
        <ExternalLink className="h-3 w-3" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 px-2 text-[10px] text-muted-foreground"
        onClick={onEdit}
        title="Edit view"
      >
        Edit
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 text-destructive"
        onClick={onRemove}
        disabled={removing}
        title="Detach"
      >
        {removing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
      </Button>
    </div>
  );
}

export default SolutionViewsEditor;
