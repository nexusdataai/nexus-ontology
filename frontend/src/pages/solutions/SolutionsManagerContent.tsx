import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { Chips, SearchInput, Toolbar } from '@/components/ds/kit';
import { EmptyState } from '@/components/ds/primitives';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import type { Solution, ViewSummary } from '@/lib/foundry/model';
import { solutionService } from '@/services/solutionService';
import { viewService } from '@/services/viewService';
import { APP_REGISTRY, type AppConfig } from '@/config/appRegistry';
import { SolutionViewsEditor } from './SolutionViewsEditor';
import { confirmDialog } from '@/components/ds/confirm';

interface SolutionsManagerContentProps {
  hideHeading?: boolean;
}

export function SolutionsManagerContent({ hideHeading = false }: SolutionsManagerContentProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [solutionsByApp, setSolutionsByApp] = useState<Record<string, Solution | null>>({});
  const [views, setViews] = useState<ViewSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [scope, setScope] = useState<'all' | 'with' | 'without'>('all');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [unmappingId, setUnmappingId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [allSolutions, allViews] = await Promise.all([
        solutionService.list().catch(() => []),
        viewService.list().catch(() => []),
      ]);

      // Hydrate full Solution detail (with views[]) for those that exist.
      const detailed = await Promise.all(
        allSolutions.map((s) =>
          solutionService.get(s.solutionId).catch(() => null),
        ),
      );
      const byAppId: Record<string, Solution | null> = {};
      for (const app of APP_REGISTRY) byAppId[app.id] = null;
      for (const sol of detailed) {
        if (sol && sol.appId) byAppId[sol.appId] = sol;
      }
      setSolutionsByApp(byAppId);
      setViews(allViews);
    } catch {
      toast.error('Failed to load solution mappings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const handleSolutionChanged = useCallback((sol: Solution) => {
    if (!sol.appId) return;
    setSolutionsByApp((prev) => ({ ...prev, [sol.appId!]: sol }));
  }, []);

  const handleUnmapAll = useCallback(
    async (app: AppConfig, sol: Solution) => {
      if (!(await confirmDialog({ title: `Remove all view mappings from ${app.shortName}?`, description: 'The views themselves are kept.', confirmLabel: 'Remove', destructive: true }))) return;
      setUnmappingId(sol.solutionId);
      try {
        await solutionService.delete(sol.solutionId);
        setSolutionsByApp((prev) => ({ ...prev, [app.id]: null }));
        toast.success(`Unmapped ${app.shortName}`);
      } catch {
        toast.error('Failed to unmap');
      } finally {
        setUnmappingId(null);
      }
    },
    [],
  );

  const toggleExpanded = useCallback((appId: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(appId)) next.delete(appId);
      else next.add(appId);
      return next;
    });
  }, []);

  // Honour ?solutionId=… deep link by auto-expanding the matching app row.
  const deepLinkSolutionId = searchParams.get('solutionId');
  useEffect(() => {
    if (!deepLinkSolutionId || loading) return;
    const targetAppId = Object.entries(solutionsByApp).find(
      ([, sol]) => sol?.solutionId === deepLinkSolutionId,
    )?.[0];
    if (!targetAppId || expanded.has(targetAppId)) return;
    toggleExpanded(targetAppId);
    const next = new URLSearchParams(searchParams);
    next.delete('solutionId');
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deepLinkSolutionId, loading, solutionsByApp]);

  const filteredApps = useMemo(() => {
    if (!search.trim()) return APP_REGISTRY;
    const q = search.toLowerCase();
    return APP_REGISTRY.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        a.id.toLowerCase().includes(q) ||
        (a.description || '').toLowerCase().includes(q),
    );
  }, [search]);

  const mappedCount = APP_REGISTRY.filter(a => (solutionsByApp[a.id]?.views.length ?? 0) > 0).length;
  const shownApps = filteredApps.filter(a => {
    const n = solutionsByApp[a.id]?.views.length ?? 0;
    return scope === 'all' || (scope === 'with' ? n > 0 : n === 0);
  });
  const viewName = (id: string, fallback?: string) => fallback || views.find(v => v.viewId === id)?.name || 'View';

  return (
    <div className={hideHeading ? '' : 'page'}>
      <div className="mb-6 max-w-3xl">
        <h2 className="text-xl font-medium tracking-tight text-foreground">Attach views to solutions</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          A view you attach here appears in that solution's side menu, under Views. Drag to set the order.
          {!loading && <> <span className="num font-medium text-foreground">{mappedCount}</span> of <span className="num font-medium text-foreground">{APP_REGISTRY.length}</span> solutions have views attached.</>}
        </p>
      </div>

      <Toolbar>
        <SearchInput value={search} onChange={setSearch} placeholder="Search solutions" className="w-full sm:w-72" />
        <Chips
          label="Filter solutions"
          value={scope}
          onChange={(v) => setScope(v as 'all' | 'with' | 'without')}
          options={[
            { value: 'all', label: 'All', count: APP_REGISTRY.length },
            { value: 'with', label: 'With views', count: mappedCount },
            { value: 'without', label: 'Without views', count: APP_REGISTRY.length - mappedCount },
          ]}
        />
      </Toolbar>

      <div className="mt-4">
        {loading ? (
          <div className="space-y-px overflow-hidden rounded-xl border border-border" aria-busy="true">
            {[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-16 w-full rounded-none" />)}
          </div>
        ) : shownApps.length === 0 ? (
          <EmptyState icon="apps" title="No solutions match" description="Try another search or clear the filter." />
        ) : (
          <ul className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
            {shownApps.map((app, i) => {
              const sol = solutionsByApp[app.id] ?? null;
              const AppIcon = app.icon;
              const isOpen = expanded.has(app.id);
              const linked = sol?.views ?? [];
              const isUnmapping = !!sol && unmappingId === sol.solutionId;

              return (
                <li key={app.id} className="rise border-b border-border last:border-b-0" style={{ ['--i' as any]: Math.min(i, 10) }}>
                  <div className={cn('flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3.5 transition-colors', isOpen && 'bg-surface-2/60')}>
                    <button
                      type="button"
                      onClick={() => toggleExpanded(app.id)}
                      aria-expanded={isOpen}
                      className="flex min-w-0 flex-1 items-center gap-3.5 rounded text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-foreground">
                        <AppIcon className="h-[18px] w-[18px]" strokeWidth={1.5} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-foreground">{app.name}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {linked.length === 0
                            ? 'No views attached'
                            : linked.slice(0, 3).map((v: any) => viewName(v.viewId, v.displayName)).join(', ') + (linked.length > 3 ? ` and ${linked.length - 3} more` : '')}
                        </span>
                      </span>
                    </button>
                    <span className={cn('num shrink-0 text-xs', linked.length > 0 ? 'text-foreground' : 'text-muted-foreground')}>
                      {linked.length} {linked.length === 1 ? 'view' : 'views'}
                    </span>
                    {sol && linked.length > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="shrink-0 text-muted-foreground hover:text-destructive"
                        onClick={() => handleUnmapAll(app, sol)}
                        disabled={isUnmapping}
                      >
                        <Icon name={isUnmapping ? 'spinner' : 'trash'} className={cn('h-3.5 w-3.5', isUnmapping && 'animate-spin')} />
                        <span className="hidden sm:inline">Remove all</span>
                      </Button>
                    )}
                    <Button variant={isOpen ? 'secondary' : 'outline'} size="sm" className="shrink-0" onClick={() => toggleExpanded(app.id)}>
                      {isOpen ? 'Done' : linked.length > 0 ? 'Manage views' : <><Icon name="plus" className="h-3.5 w-3.5" /> Attach a view</>}
                    </Button>
                  </div>

                  {isOpen && (
                    <div className="animate-fade-in border-t border-border bg-background/40">
                      <SolutionViewsEditor
                        app={app}
                        solution={sol}
                        availableViews={views}
                        onSolutionChanged={handleSolutionChanged}
                      />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

export default SolutionsManagerContent;
