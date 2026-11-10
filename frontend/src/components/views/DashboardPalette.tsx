import { useCallback, useEffect, useMemo, useState } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { InlineError, SearchInput } from '@/components/ds/kit';
import { dashboardService, type DashboardListItem } from '@/services/dashboardService';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface DashboardPaletteProps {
  className?: string;
  /** Add the dashboard as a new tab without dragging. */
  onAdd?: (dashboard: DashboardListItem) => void;
  /** Dashboards already used by a tab (shown as "In this view"). */
  usedIds?: string[];
}

/** The dashboards that can become tabs: drag one onto the tabs, or add it with the plus. */
export function DashboardPalette({ className, onAdd, usedIds }: DashboardPaletteProps) {
  const [items, setItems] = useState<DashboardListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [query, setQuery] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setFailed(false);
    dashboardService
      .list()
      .then(setItems)
      .catch(() => {
        setFailed(true);
        toast.error('Failed to load dashboards for palette');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter(
      (d) => d.title.toLowerCase().includes(q) || (d.description || '').toLowerCase().includes(q)
    );
  }, [items, query]);

  const used = useMemo(() => new Set(usedIds || []), [usedIds]);

  return (
    <aside className={cn('flex min-h-0 flex-col border-r border-border bg-sidebar/40', className)} aria-label="Dashboards">
      <div className="border-b border-border px-3 pb-3 pt-3.5">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-sm font-medium text-foreground">Dashboards</h2>
          {!loading && !failed && <span className="num text-xs text-subtle-foreground">{filtered.length}</span>}
        </div>
        <p className="mb-2.5 mt-0.5 text-xs text-muted-foreground">Drag one onto the tabs, or add it with the plus.</p>
        <SearchInput value={query} onChange={setQuery} placeholder="Search dashboards" className="w-full sm:w-full" />
      </div>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <div className="space-y-3 p-3" aria-busy="true">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-3.5 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : failed ? (
          <div className="p-3">
            <InlineError onRetry={load}>The dashboards could not be loaded.</InlineError>
          </div>
        ) : filtered.length === 0 ? (
          <p className="px-3 py-6 text-center text-xs text-muted-foreground">
            {items.length === 0 ? 'No dashboards yet. Create one in AI Analytics first.' : 'No dashboard matches this search.'}
          </p>
        ) : (
          <ul>
            {filtered.map((d) => (
              <li key={d.uid} className="border-b border-border last:border-b-0">
                <DraggableDashboard dashboard={d} onAdd={onAdd} used={used.has(d.uid)} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}

interface DraggableDashboardProps {
  dashboard: DashboardListItem;
  onAdd?: (dashboard: DashboardListItem) => void;
  used?: boolean;
}

function DraggableDashboard({ dashboard, onAdd, used }: DraggableDashboardProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `dashboard:${dashboard.uid}`,
    data: { dashboard },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={cn(
        'group flex cursor-grab items-start gap-2 px-3 py-2.5 transition-colors hover:bg-accent/60 focus-visible:bg-accent/60 focus-visible:outline-none active:cursor-grabbing',
        isDragging && 'bg-accent opacity-60'
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-foreground">{dashboard.title}</div>
        {dashboard.description && (
          <div className="truncate text-xs text-muted-foreground">{dashboard.description}</div>
        )}
        <div className="num mt-0.5 text-xs text-subtle-foreground">
          {dashboard.panelCount} {dashboard.panelCount === 1 ? 'panel' : 'panels'}
          {used && ' · in this view'}
        </div>
      </div>
      {onAdd && (
        <button
          type="button"
          onClick={() => onAdd(dashboard)}
          onKeyDown={(e) => e.stopPropagation()}
          aria-label={`Add ${dashboard.title} as a tab`}
          title="Add as a tab"
          className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded text-muted-foreground opacity-0 transition-opacity hover:bg-brand/10 hover:text-primary focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring group-hover:opacity-100 dark:hover:text-brand-hi"
        >
          <Icon name="plus" className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

export default DashboardPalette;
