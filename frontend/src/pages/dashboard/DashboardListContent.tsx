import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { Icon } from '@/components/ds/Icon';
import { Chips, SearchInput, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { confirmDialog } from '@/components/ds/confirm';
import { LibraryCard } from '@/components/analytics/LibraryCard';
import { dashboardService, type DashboardListItem } from '@/services/dashboardService';

interface DashboardListContentProps {
  /** Hide the page-level title block (used when embedded in tabs). */
  hideHeading?: boolean;
}

export function DashboardListContent({ hideHeading = false }: DashboardListContentProps) {
  const navigate = useNavigate();
  const [dashboards, setDashboards] = useState<DashboardListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [tag, setTag] = useState<string>('all');

  const load = () => {
    setLoading(true);
    dashboardService
      .list(search)
      .then(setDashboards)
      .catch(() => toast.error('Failed to load dashboards'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [search]);

  const handleDelete = async (uid: string) => {
    try {
      await dashboardService.delete(uid);
      setDashboards((prev) => prev.filter((d) => d.uid !== uid));
      toast.success('Dashboard deleted');
    } catch {
      toast.error('Delete failed');
    }
  };

  const handleClone = async (uid: string) => {
    try {
      const cloned = await dashboardService.clone(uid);
      toast.success('Dashboard cloned');
      navigate(`/dashboard/builder/${cloned.uid}`);
    } catch {
      toast.error('Clone failed');
    }
  };

  const tags = useMemo(() => {
    const m = new Map<string, number>();
    for (const it of dashboards) for (const t of it.tags || []) m.set(t, (m.get(t) || 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [dashboards]);
  const shown = tag === 'all' ? dashboards : dashboards.filter(it => (it.tags || []).includes(tag));

  const confirmDelete = async (id: string, name: string) => {
    const ok = await confirmDialog({ title: `Delete "${name}"?`, description: 'This cannot be undone.', destructive: true, confirmLabel: 'Delete' });
    if (ok) handleDelete(id);
  };

  return (
    <div className={hideHeading ? '' : 'page'}>
      {!hideHeading && (
        <div className="mb-6">
          <h1 className="text-2xl font-medium tracking-tight text-foreground">Dashboards</h1>
          <p className="mt-1 text-sm text-muted-foreground">Dashboards built on the virtual data layer.</p>
        </div>
      )}

      <Toolbar>
        <SearchInput value={search} onChange={setSearch} placeholder="Search dashboards" className="w-full sm:w-72" />
        {tags.length > 0 && (
          <Chips
            label="Filter by tag"
            value={tag}
            onChange={setTag}
            options={[{ value: 'all', label: 'All', count: dashboards.length }, ...tags.map(([t, n]) => ({ value: t, label: t.charAt(0).toUpperCase() + t.slice(1), count: n }))]}
          />
        )}
        <ToolbarSpacer />
        <Button onClick={() => navigate('/dashboard/builder')}>
          <Icon name="plus" className="h-3.5 w-3.5" /> New dashboard
        </Button>
      </Toolbar>

      <div className="mt-5">
        {loading && dashboards.length === 0 ? (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3" aria-busy="true">
            {[0, 1, 2].map(i => <Skeleton key={i} className="h-64 rounded-xl" />)}
          </div>
        ) : shown.length === 0 ? (
          <EmptyState
            icon="dashboard"
            title={search || tag !== 'all' ? 'Nothing matches' : 'No dashboards yet'}
            description={search || tag !== 'all' ? 'Try another search or clear the filter.' : 'Build one from the virtual data layer: pick entities, add panels, save.'}
            action={!search && tag === 'all' ? <Button onClick={() => navigate('/dashboard/builder')}><Icon name="plus" className="h-3.5 w-3.5" /> Create the first dashboard</Button> : undefined}
          />
        ) : (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {shown.map((it, i) => (
              <LibraryCard
                key={it.uid}
                id={it.uid}
                kind="dashboard"
                title={it.title}
                description={it.description}
                count={it.panelCount}
                updatedAt={it.updatedAt}
                tags={it.tags}
                index={i}
                onOpen={() => navigate(`/dashboard/view/${it.uid}`)}
                actions={[
                  { label: 'Open', icon: 'eye', onSelect: () => navigate(`/dashboard/view/${it.uid}`) },
                  { label: 'Edit', icon: 'edit', onSelect: () => navigate(`/dashboard/builder/${it.uid}`) },
                  { label: 'Duplicate', icon: 'copy', onSelect: () => handleClone(it.uid) },
                  { label: 'Delete', icon: 'trash', destructive: true, onSelect: () => confirmDelete(it.uid, it.title) },
                ]}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default DashboardListContent;
