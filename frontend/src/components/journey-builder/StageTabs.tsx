import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Icon } from '@/components/ds/Icon';
import type { BuilderStageState } from './builderState';
import { confirmDialog } from '@/components/ds/confirm';

interface Props {
  stages: BuilderStageState[];
  activeStageId: string;
  onActiveChange: (stageId: string) => void;
  onAdd: () => void;
  onRename: (stageId: string, newName: string) => void;
  onDelete: (stageId: string) => void;
  className?: string;
}

const ICON_BTN = 'flex h-5 w-5 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

/**
 * Horizontal tab strip rendered above the Journey Builder canvas.
 * One tab per stage; clicking switches the active stage which causes
 * the canvas to remount with that stage's nodes / edges.
 *
 * Affordances per tab:
 *   - Click the tab body to activate it.
 *   - Double-click (or click the pencil icon when active) to rename.
 *   - Click the trash icon on the active stage to delete (the last stage
 *     cannot be deleted -- every journey has at least one stage).
 *
 * Plus a trailing "Add stage" button to add a new stage at the end.
 */
export function StageTabs({
  stages, activeStageId, onActiveChange, onAdd, onRename, onDelete, className,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');

  const beginEdit = (s: BuilderStageState) => {
    setEditingId(s.stageId);
    setDraft(s.name);
  };

  const commitEdit = () => {
    if (editingId == null) return;
    const trimmed = draft.trim();
    if (trimmed) onRename(editingId, trimmed);
    setEditingId(null);
    setDraft('');
  };

  const cancelEdit = () => {
    setEditingId(null);
    setDraft('');
  };

  return (
    <div role="tablist" aria-label="Stages" className={cn('mb-2 flex flex-wrap items-center gap-1', className)}>
      {stages.map((s, i) => {
        const active = s.stageId === activeStageId;
        const editing = editingId === s.stageId;
        return (
          <div
            key={s.stageId}
            role="tab"
            tabIndex={0}
            aria-selected={active}
            className={cn(
              'flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              active
                ? 'border-border-strong bg-accent font-medium text-foreground'
                : 'cursor-pointer border-transparent text-muted-foreground hover:bg-accent/70 hover:text-foreground',
            )}
            onClick={() => !editing && onActiveChange(s.stageId)}
            onKeyDown={(e) => { if (!editing && e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); onActiveChange(s.stageId); } }}
            onDoubleClick={(e) => { e.stopPropagation(); beginEdit(s); }}
          >
            <span className="num text-xs font-normal text-subtle-foreground">{i + 1}</span>
            {editing ? (
              <Input
                autoFocus
                value={draft}
                aria-label="Stage name"
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') commitEdit();
                  if (e.key === 'Escape') cancelEdit();
                }}
                onClick={(e) => e.stopPropagation()}
                className="h-6 w-32 px-1.5 text-sm"
              />
            ) : (
              <span>{s.name}</span>
            )}
            {active && !editing && (
              <>
                <button
                  type="button"
                  className={ICON_BTN}
                  title="Rename stage"
                  aria-label="Rename stage"
                  onClick={(e) => { e.stopPropagation(); beginEdit(s); }}
                >
                  <Icon name="edit" className="h-3 w-3" />
                </button>
                {stages.length > 1 && (
                  <button
                    type="button"
                    className={cn(ICON_BTN, 'hover:text-destructive')}
                    title="Delete stage"
                    aria-label="Delete stage"
                    onClick={async (e) => {
                      e.stopPropagation();
                      if (await confirmDialog({ title: `Delete stage "${s.name}"?`, description: 'Its steps and connections will be lost.', destructive: true })) {
                        onDelete(s.stageId);
                      }
                    }}
                  >
                    <Icon name="trash" className="h-3 w-3" />
                  </button>
                )}
              </>
            )}
            {editing && (
              <>
                <button
                  type="button"
                  className={cn(ICON_BTN, 'text-foreground')}
                  title="Save (Enter)"
                  aria-label="Save name"
                  onClick={(e) => { e.stopPropagation(); commitEdit(); }}
                >
                  <Icon name="check" className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  className={ICON_BTN}
                  title="Cancel (Esc)"
                  aria-label="Cancel rename"
                  onClick={(e) => { e.stopPropagation(); cancelEdit(); }}
                >
                  <Icon name="close" className="h-3 w-3" />
                </button>
              </>
            )}
          </div>
        );
      })}
      <button
        type="button"
        onClick={onAdd}
        title="Add a new stage"
        className="flex h-8 items-center gap-1.5 rounded-md border border-dashed border-border-strong px-2.5 text-sm text-muted-foreground transition-colors hover:bg-accent/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Icon name="plus" className="h-3 w-3" /> Add stage
      </button>
    </div>
  );
}

export default StageTabs;
