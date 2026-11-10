import { useEffect, useRef, useState } from 'react';
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  useDroppable,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  horizontalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Icon } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';
import type { DraftTab } from './ViewBuilderTypes';

interface TabStripProps {
  tabs: DraftTab[];
  activeTabId?: string;
  onSelect: (tabId: string) => void;
  onRemove: (tabId: string) => void;
  onReorder: (tabIds: string[]) => void;
  onAddBlankTab: () => void;
  /** Rename in place (double-click a tab). Omit to rename only from the tab settings. */
  onRename?: (tabId: string, label: string) => void;
}

/**
 * The view's tabs as they will appear: click to select, drag to reorder,
 * double-click to rename, the cross to remove.
 */
export function TabStrip({
  tabs,
  activeTabId,
  onSelect,
  onRemove,
  onReorder,
  onAddBlankTab,
  onRename,
}: TabStripProps) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const labelOf = (id: string | number) => tabs.find((t) => t.tabId === id)?.label || 'Untitled';

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = tabs.findIndex((t) => t.tabId === active.id);
    const newIndex = tabs.findIndex((t) => t.tabId === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    const reordered = arrayMove(tabs, oldIndex, newIndex);
    onReorder(reordered.map((t) => t.tabId));
  };

  return (
    <div className="scrollbar-hide flex shrink-0 items-stretch gap-1 overflow-x-auto border-b border-border px-3 sm:px-5">
      <DndContext
        sensors={sensors}
        onDragEnd={handleDragEnd}
        accessibility={{
          // Read tab names, not their internal ids.
          screenReaderInstructions: { draggable: 'Press Enter to open this tab, F2 to rename it, and Alt with the left or right arrow to move it.' },
          announcements: {
            onDragStart: ({ active }) => `Picked up tab ${labelOf(active.id)}.`,
            onDragOver: ({ active, over }) => (over ? `Tab ${labelOf(active.id)} is over tab ${labelOf(over.id)}.` : `Tab ${labelOf(active.id)} is not over a tab.`),
            onDragEnd: ({ active, over }) => (over ? `Tab ${labelOf(active.id)} was dropped at the place of ${labelOf(over.id)}.` : `Tab ${labelOf(active.id)} was dropped.`),
            onDragCancel: ({ active }) => `Moving tab ${labelOf(active.id)} was cancelled.`,
          },
        }}
      >
        <SortableContext items={tabs.map((t) => t.tabId)} strategy={horizontalListSortingStrategy}>
          {tabs.map((tab) => (
            <SortableTab
              key={tab.tabId}
              tab={tab}
              active={tab.tabId === activeTabId}
              onSelect={() => onSelect(tab.tabId)}
              onRemove={() => onRemove(tab.tabId)}
              onRename={onRename ? (label) => onRename(tab.tabId, label) : undefined}
              onMove={(step) => {
                const from = tabs.findIndex((t) => t.tabId === tab.tabId);
                const to = from + step;
                if (from < 0 || to < 0 || to >= tabs.length) return;
                onReorder(arrayMove(tabs, from, to).map((t) => t.tabId));
              }}
            />
          ))}
        </SortableContext>
      </DndContext>
      <NewTabDropZone onAddBlank={onAddBlankTab} first={tabs.length === 0} />
    </div>
  );
}

interface SortableTabProps {
  tab: DraftTab;
  active: boolean;
  onSelect: () => void;
  onRemove: () => void;
  onRename?: (label: string) => void;
}

function SortableTab({ tab, active, onSelect, onRemove, onRename, onMove }: SortableTabProps & { onMove?: (step: -1 | 1) => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: tab.tabId,
  });
  const [renaming, setRenaming] = useState(false);
  const [text, setText] = useState(tab.label);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (renaming) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [renaming]);

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const startRename = () => {
    if (!onRename) return;
    setText(tab.label);
    setRenaming(true);
  };
  const commitRename = () => {
    setRenaming(false);
    if (onRename && text !== tab.label) onRename(text);
  };

  const label = tab.label || 'Untitled';

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...(renaming ? {} : listeners)}
      {...(renaming ? {} : attributes)}
      aria-pressed={active}
      aria-label={`${label}${tab.dashboardId ? '' : ', no dashboard chosen'}`}
      title={onRename ? 'Drag, or press Alt and an arrow key, to reorder. Double-click or press F2 to rename.' : 'Drag, or press Alt and an arrow key, to reorder.'}
      onClick={onSelect}
      onDoubleClick={startRename}
      onKeyDown={(e) => {
        if (renaming) return;
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(); }
        if (e.key === 'F2') { e.preventDefault(); startRename(); }
        // Keyboard alternative to dragging.
        if (e.altKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight') && onMove) {
          e.preventDefault();
          onMove(e.key === 'ArrowLeft' ? -1 : 1);
          requestAnimationFrame(() => (e.currentTarget as HTMLElement | null)?.focus());
        }
      }}
      className={cn(
        'group relative flex h-10 shrink-0 cursor-pointer select-none items-center gap-1.5 rounded-t-md pl-2 pr-1 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'after:absolute after:inset-x-0 after:-bottom-px after:h-0.5 after:rounded-full after:bg-primary after:transition-transform after:duration-300 after:ease-brand-out',
        active ? 'text-foreground after:scale-x-100' : 'text-muted-foreground after:scale-x-0 hover:text-foreground',
      )}
    >
      {!tab.dashboardId && <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-warning" aria-hidden="true" />}
      {renaming ? (
        <input
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={commitRename}
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commitRename();
            if (e.key === 'Escape') setRenaming(false);
          }}
          aria-label="Tab label"
          className="h-7 w-36 rounded border border-border-strong bg-card px-1.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      ) : (
        <span className="max-w-[180px] truncate">{label}</span>
      )}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        onDoubleClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
        className={cn(
          'flex h-6 w-6 shrink-0 items-center justify-center rounded text-subtle-foreground transition-opacity hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          active ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
        )}
        aria-label={`Remove tab ${label}`}
        title="Remove tab"
      >
        <Icon name="close" className="h-3 w-3" />
      </button>
    </div>
  );
}

interface NewTabDropZoneProps {
  onAddBlank: () => void;
  first?: boolean;
}

function NewTabDropZone({ onAddBlank, first }: NewTabDropZoneProps) {
  const { setNodeRef, isOver } = useDroppable({ id: 'tabstrip-new-tab' });
  return (
    <button
      ref={setNodeRef}
      type="button"
      onClick={onAddBlank}
      className={cn(
        'my-1.5 ml-1 flex h-7 shrink-0 items-center gap-1.5 self-center rounded-md border border-dashed px-2.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        isOver
          ? 'border-brand/60 bg-brand/10 text-primary dark:text-brand-hi'
          : 'border-border-strong text-muted-foreground hover:border-brand/50 hover:text-foreground',
      )}
      title="Add an empty tab, or drop a dashboard here"
    >
      <Icon name="plus" className="h-3 w-3" />
      {isOver ? 'Drop to add as a tab' : first ? 'Add the first tab' : 'Add tab'}
    </button>
  );
}

export default TabStrip;
