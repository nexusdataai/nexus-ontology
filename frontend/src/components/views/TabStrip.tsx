import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  useDroppable,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  horizontalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Plus, X, GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DraftTab } from './ViewBuilderTypes';

interface TabStripProps {
  tabs: DraftTab[];
  activeTabId?: string;
  onSelect: (tabId: string) => void;
  onRemove: (tabId: string) => void;
  onReorder: (tabIds: string[]) => void;
  onAddBlankTab: () => void;
}

export function TabStrip({
  tabs,
  activeTabId,
  onSelect,
  onRemove,
  onReorder,
  onAddBlankTab,
}: TabStripProps) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

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
    <div className="flex items-center gap-1.5 px-3 py-2 border-b bg-muted/30 overflow-x-auto">
      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        <SortableContext items={tabs.map((t) => t.tabId)} strategy={horizontalListSortingStrategy}>
          {tabs.map((tab) => (
            <SortableTab
              key={tab.tabId}
              tab={tab}
              active={tab.tabId === activeTabId}
              onSelect={() => onSelect(tab.tabId)}
              onRemove={() => onRemove(tab.tabId)}
            />
          ))}
        </SortableContext>
      </DndContext>
      <NewTabDropZone onAddBlank={onAddBlankTab} />
    </div>
  );
}

interface SortableTabProps {
  tab: DraftTab;
  active: boolean;
  onSelect: () => void;
  onRemove: () => void;
}

function SortableTab({ tab, active, onSelect, onRemove }: SortableTabProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: tab.tabId,
  });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      onClick={onSelect}
      className={cn(
        'flex items-center gap-1.5 pl-1 pr-1.5 py-1 rounded-md border text-xs cursor-pointer select-none shrink-0',
        active
          ? 'bg-background border-primary text-foreground shadow-sm'
          : 'bg-muted/40 border-transparent text-muted-foreground hover:bg-muted'
      )}
    >
      <span
        {...listeners}
        {...attributes}
        className="cursor-grab active:cursor-grabbing text-muted-foreground/70 hover:text-foreground"
      >
        <GripVertical className="h-3 w-3" />
      </span>
      <span className="px-1 truncate max-w-[160px]">{tab.label || 'Untitled'}</span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        className="text-muted-foreground/70 hover:text-destructive p-0.5 rounded"
        title="Remove tab"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

interface NewTabDropZoneProps {
  onAddBlank: () => void;
}

function NewTabDropZone({ onAddBlank }: NewTabDropZoneProps) {
  const { setNodeRef, isOver } = useDroppable({ id: 'tabstrip-new-tab' });
  return (
    <button
      ref={setNodeRef}
      onClick={onAddBlank}
      className={cn(
        'flex items-center gap-1 px-2 py-1 rounded-md text-xs border border-dashed shrink-0 transition-colors',
        isOver
          ? 'border-primary bg-primary/5 text-primary'
          : 'border-muted-foreground/30 text-muted-foreground hover:border-foreground hover:text-foreground'
      )}
      title="Drop a dashboard here, or click to add a blank tab"
    >
      <Plus className="h-3 w-3" />
      Add tab
    </button>
  );
}

export default TabStrip;
