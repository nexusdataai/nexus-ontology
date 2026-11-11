import { useEffect, useMemo, useState } from 'react';
import { humanize } from '@/components/journeys/studio/format';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { Icon } from '@/components/ds/Icon';
import { Chips, SearchInput, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { confirmDialog } from '@/components/ds/confirm';
import { LibraryCard } from '@/components/analytics/LibraryCard';
import { viewService } from '@/services/viewService';
import type { ViewSummary } from '@/lib/foundry/model';

interface ViewListContentProps {
  hideHeading?: boolean;
}

export function ViewListContent({ hideHeading = false }: ViewListContentProps) {
  const navigate = useNavigate();
  const [views, setViews] = useState<ViewSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [tag, setTag] = useState<string>('all');

  const load = () => {
    setLoading(true);
    viewService
      .list(search)
      .then(setViews)
      .catch(() => toast.error('Failed to load views'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [search]);

  const handleDelete = async (viewId: string) => {
    try {
      await viewService.delete(viewId);
      setViews((prev) => prev.filter((v) => v.viewId !== viewId));
      toast.success('View deleted');
    } catch {
      toast.error('Delete failed');
    }
  };

  const tags = useMemo(() => {
    const m = new Map<string, number>();
    for (const it of views) for (const t of it.tags || []) m.set(t, (m.get(t) || 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [views]);
  const shown = tag === 'all' ? views : views.filter(it => (it.tags || []).includes(tag));

  const confirmDelete = async (id: string, name: string) => {
    const ok = await confirmDialog({ title: `Delete "${name}"?`, description: 'This cannot be undone.', destructive: true, confirmLabel: 'Delete' });
    if (ok) handleDelete(id);
  };

  return (
    <div className={hideHeading ? '' : 'page'}>
      {!hideHeading && (
        <div className="mb-6">
          <h1 className="text-lg font-medium tracking-tight text-foreground">Views</h1>
          <p className="mt-1 text-sm text-muted-foreground">Tabbed collections of dashboards that you can attach to a solution.</p>
        </div>
      )}

      <Toolbar>
        <SearchInput value={search} onChange={setSearch} placeholder="Search views" className="w-full sm:w-72" />
        {tags.length > 0 && (
          <Chips
            label="Filter by tag"
            value={tag}
            onChange={setTag}
            options={[{ value: 'all', label: 'All', count: views.length }, ...tags.map(([t, n]) => ({ value: t, label: humanize(t), count: n }))]}
          />
        )}
        <ToolbarSpacer />
        <Button onClick={() => navigate('/views/builder')}>
          <Icon name="plus" className="h-3.5 w-3.5" /> New view
        </Button>
      </Toolbar>

      <div className="mt-5">
        {loading && views.length === 0 ? (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3" aria-busy="true">
            {[0, 1, 2].map(i => <Skeleton key={i} className="h-64 rounded-xl" />)}
          </div>
        ) : shown.length === 0 ? (
          <EmptyState
            icon="layers"
            title={search || tag !== 'all' ? 'Nothing matches' : 'No views yet'}
            description={search || tag !== 'all' ? 'Try another search or clear the filter.' : 'Group dashboards into tabs and attach the view to a solution.'}
            action={!search && tag === 'all' ? <Button onClick={() => navigate('/views/builder')}><Icon name="plus" className="h-3.5 w-3.5" /> Create the first view</Button> : undefined}
          />
        ) : (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {shown.map((it, i) => (
              <LibraryCard
                key={it.viewId}
                id={it.viewId}
                kind="view"
                title={it.name}
                description={it.description}
                count={it.tabCount}
                updatedAt={it.updatedAt}
                tags={it.tags}
                index={i}
                onOpen={() => navigate(`/views/${it.viewId}`)}
                actions={[
                  { label: 'Open', icon: 'eye', onSelect: () => navigate(`/views/${it.viewId}`) },
                  { label: 'Edit', icon: 'edit', onSelect: () => navigate(`/views/builder/${it.viewId}`) },
                  { label: 'Delete', icon: 'trash', destructive: true, onSelect: () => confirmDelete(it.viewId, it.name) },
                ]}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default ViewListContent;
