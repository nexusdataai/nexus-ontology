import { useEffect, useMemo, useState } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { Loader2, LayoutDashboard, Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { dashboardService, type DashboardListItem } from '@/services/dashboardService';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface DashboardPaletteProps {
  className?: string;
}

export function DashboardPalette({ className }: DashboardPaletteProps) {
  const [items, setItems] = useState<DashboardListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');

  useEffect(() => {
    setLoading(true);
    dashboardService
      .list()
      .then(setItems)
      .catch(() => toast.error('Failed to load dashboards for palette'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter(
      (d) => d.title.toLowerCase().includes(q) || (d.description || '').toLowerCase().includes(q)
    );
  }, [items, query]);

  return (
    <div className={cn('flex flex-col h-full border-r bg-background', className)}>
      <div className="px-3 pt-3 pb-2 border-b">
        <div className="text-xs font-semibold text-muted-foreground mb-2">
          Dashboards
        </div>
        <div className="relative">
          <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search..."
            className="h-7 pl-8 text-xs"
          />
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-1.5">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-xs text-muted-foreground p-3 text-center">
            No dashboards available. Create one first.
          </div>
        ) : (
          filtered.map((d) => <DraggableDashboard key={d.uid} dashboard={d} />)
        )}
      </div>
    </div>
  );
}

interface DraggableDashboardProps {
  dashboard: DashboardListItem;
}

function DraggableDashboard({ dashboard }: DraggableDashboardProps) {
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
        'flex items-start gap-2 p-2 rounded-md border bg-card cursor-grab active:cursor-grabbing transition-shadow hover:shadow-sm',
        isDragging && 'opacity-40 ring-1 ring-primary'
      )}
    >
      <LayoutDashboard className="h-3.5 w-3.5 mt-0.5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <div className="text-xs font-medium truncate">{dashboard.title}</div>
        {dashboard.description && (
          <div className="text-xs text-muted-foreground truncate">{dashboard.description}</div>
        )}
        <div className="text-xs text-muted-foreground mt-0.5">{dashboard.panelCount} panels</div>
      </div>
    </div>
  );
}

export default DashboardPalette;
