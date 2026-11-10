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
import { Icon } from '@/components/ds/Icon';
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
    <div className="px-5 py-4 sm:pl-[4.6rem]">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          {views.length === 0 ? 'Nothing attached yet.' : 'Shown in this order in the solution menu. Drag to reorder.'}
          {(reordering || creating) && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin" />}
        </p>
        <Button size="sm" onClick={() => setPickerOpen(true)} disabled={creating}>
          <Icon name="plus" className="h-3.5 w-3.5" /> Attach a view
        </Button>
      </div>

      {views.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border-strong px-4 py-6 text-center text-sm text-muted-foreground">
          Attach a view to show its dashboards inside <span className="font-medium text-foreground">{app.shortName}</span>.
        </p>
      ) : (
        <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
          <SortableContext
            items={views.map((v) => v.viewId)}
            strategy={verticalListSortingStrategy}
          >
            <ol className="overflow-hidden rounded-lg border border-border bg-card">
              {views.map((link, i) => (
                <SortableRow
                  key={link.viewId}
                  index={i}
                  link={link}
                  summary={viewLookup.get(link.viewId)}
                  removing={removingId === link.viewId}
                  onRemove={() => handleRemove(link.viewId)}
                  onOpen={() => nav(`/views/${link.viewId}`)}
                  onEdit={() => nav(`/views/builder/${link.viewId}`)}
                />
              ))}
            </ol>
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
  index: number;
  link: SolutionViewLink;
  summary?: ViewSummary;
  removing: boolean;
  onRemove: () => void;
  onOpen: () => void;
  onEdit: () => void;
}

function SortableRow({ index, link, summary, removing, onRemove, onOpen, onEdit }: SortableRowProps) {
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
    <li
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-3 border-b border-border bg-card px-3 py-2.5 last:border-b-0',
        isDragging && 'relative z-10 rounded-lg border border-brand shadow-lg',
      )}
    >
      <button
        type="button"
        {...listeners}
        {...attributes}
        aria-label={`Reorder ${label}`}
        className="flex h-7 w-5 shrink-0 cursor-grab items-center justify-center rounded text-subtle-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:cursor-grabbing"
      >
        <span className="grid grid-cols-2 gap-[3px]" aria-hidden="true">
          {[0, 1, 2, 3, 4, 5].map(d => <span key={d} className="h-[3px] w-[3px] rounded-full bg-current" />)}
        </span>
      </button>
      <span className="num w-4 shrink-0 text-xs text-muted-foreground">{index + 1}</span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-foreground">{label}</div>
        {description && <div className="truncate text-xs text-muted-foreground">{description}</div>}
      </div>
      <span className="hidden shrink-0 text-xs text-muted-foreground sm:block"><span className="num">{tabCount}</span> {tabCount === 1 ? 'tab' : 'tabs'}</span>
      <Button variant="ghost" size="sm" onClick={onOpen}>Open</Button>
      <Button variant="ghost" size="sm" onClick={onEdit}>Edit</Button>
      <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-destructive" onClick={onRemove} disabled={removing} aria-label={`Detach ${label}`} title="Detach from this solution">
        <Icon name={removing ? 'spinner' : 'close'} className={cn('h-3.5 w-3.5', removing && 'animate-spin')} />
      </Button>
    </li>
  );
}

export default SolutionViewsEditor;
