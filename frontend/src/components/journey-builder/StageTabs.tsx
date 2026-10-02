import { useState } from 'react';
import { Plus, Pencil, Trash2, Check, X as XIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BuilderStageState } from './builderState';

interface Props {
  stages: BuilderStageState[];
  activeStageId: string;
  onActiveChange: (stageId: string) => void;
  onAdd: () => void;
  onRename: (stageId: string, newName: string) => void;
  onDelete: (stageId: string) => void;
  className?: string;
}

/**
 * Horizontal tab strip rendered above the Journey Builder canvas.
 * One tab per stage; clicking switches the active stage which causes
 * the canvas to remount with that stage's nodes / edges.
 *
 * Affordances per tab:
 *   - Click the tab body to activate it.
 *   - Double-click (or click the pencil icon when active) to rename.
 *   - Click the X icon on a non-last stage to delete (the last stage
 *     cannot be deleted -- every journey has at least one stage).
 *
 * Plus a trailing ``+`` button to add a new stage at the end.
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
    <div className={cn('flex items-center gap-1 mb-2 flex-wrap', className)}>
      {stages.map((s) => {
        const active = s.stageId === activeStageId;
        const editing = editingId === s.stageId;
        return (
          <div
            key={s.stageId}
            role="tab"
            aria-selected={active}
            className={cn(
              'flex items-center gap-1 h-7 px-2 rounded border text-xs transition-colors',
              active
                ? 'bg-primary/15 border-primary/40 text-primary'
                : 'bg-card border-border hover:bg-muted/30 cursor-pointer',
            )}
            onClick={() => !editing && onActiveChange(s.stageId)}
            onDoubleClick={(e) => { e.stopPropagation(); beginEdit(s); }}
          >
            {editing ? (
              <input
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') commitEdit();
                  if (e.key === 'Escape') cancelEdit();
                }}
                onClick={(e) => e.stopPropagation()}
                className="h-5 text-xs px-1 bg-background border rounded w-28"
              />
            ) : (
              <span className="font-medium">{s.name}</span>
            )}
            {active && !editing && (
              <>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground"
                  title="Rename stage"
                  onClick={(e) => { e.stopPropagation(); beginEdit(s); }}
                >
                  <Pencil className="h-3 w-3" />
                </button>
                {stages.length > 1 && (
                  <button
                    type="button"
                    className="text-muted-foreground hover:text-red-300"
                    title="Delete stage"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm(`Delete stage "${s.name}"? Its steps and connections will be lost.`)) {
                        onDelete(s.stageId);
                      }
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                )}
              </>
            )}
            {editing && (
              <>
                <button
                  type="button"
                  className="text-green-400 hover:text-green-300"
                  title="Save (Enter)"
                  onClick={(e) => { e.stopPropagation(); commitEdit(); }}
                >
                  <Check className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground"
                  title="Cancel (Esc)"
                  onClick={(e) => { e.stopPropagation(); cancelEdit(); }}
                >
                  <XIcon className="h-3 w-3" />
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
        className="flex items-center gap-1 h-7 px-2 rounded border border-dashed text-xs text-muted-foreground hover:text-foreground hover:bg-muted/30"
      >
        <Plus className="h-3 w-3" /> Stage
      </button>
    </div>
  );
}

export default StageTabs;
