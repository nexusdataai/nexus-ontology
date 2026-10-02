import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  Search,
  Plus,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import type { Solution, ViewSummary } from '@/lib/foundry/model';
import { solutionService } from '@/services/solutionService';
import { viewService } from '@/services/viewService';
import { APP_REGISTRY, type AppConfig } from '@/config/appRegistry';
import { SolutionViewsEditor } from './SolutionViewsEditor';

interface SolutionsManagerContentProps {
  hideHeading?: boolean;
}

export function SolutionsManagerContent({ hideHeading = false }: SolutionsManagerContentProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [solutionsByApp, setSolutionsByApp] = useState<Record<string, Solution | null>>({});
  const [views, setViews] = useState<ViewSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
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
      if (!confirm(`Remove all view mappings from ${app.shortName}?`)) return;
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

  return (
    <div className={hideHeading ? '' : 'p-6 max-w-6xl mx-auto'}>
      <div className="mb-6">
        {!hideHeading && (
          <div className="mb-3">
            <h1 className="text-lg font-semibold">Solution Mapping</h1>
          </div>
        )}
        <p className="text-xs text-muted-foreground max-w-3xl">
          Map Views to existing Solutions. Each linked View becomes a left-menu item
          inside its Solution UI (e.g. View1, View2). Solutions are defined by the
          app catalogue and shown below; the backend Solution row is created
          automatically the first time you map a View to one.
        </p>
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          className="h-8 pl-9 text-xs"
          placeholder="Search solutions..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : filteredApps.length === 0 ? (
        <div className="flex items-center justify-center h-24 border-2 border-dashed border-border rounded-lg">
          <p className="text-sm text-muted-foreground">No solutions match your search</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredApps.map((app) => {
            const sol = solutionsByApp[app.id] ?? null;
            const Icon = app.icon;
            const isOpen = expanded.has(app.id);
            const viewCount = sol?.views.length ?? 0;
            const isUnmapping = sol && unmappingId === sol.solutionId;

            return (
              <Card key={app.id} className="overflow-hidden">
                <button
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/30 transition-colors"
                  onClick={() => toggleExpanded(app.id)}
                >
                  {isOpen ? (
                    <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  ) : (
                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  )}
                  <div className={`p-1.5 rounded bg-gradient-to-br ${app.color} shrink-0`}>
                    <Icon className="h-3.5 w-3.5 text-white" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{app.name}</span>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {app.id}
                      </span>
                    </div>
                    {app.description && (
                      <div className="text-[10px] text-muted-foreground truncate">
                        {app.description}
                      </div>
                    )}
                  </div>
                  <span
                    className={cn(
                      'text-[10px] px-2 py-0.5 rounded-full shrink-0',
                      viewCount > 0
                        ? 'bg-primary/10 text-primary'
                        : 'bg-muted text-muted-foreground',
                    )}
                  >
                    {viewCount} {viewCount === 1 ? 'view' : 'views'}
                  </span>
                  {!isOpen && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 shrink-0"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpanded(app.id);
                      }}
                    >
                      <Plus className="h-3.5 w-3.5 mr-1" /> Add View
                    </Button>
                  )}
                  {sol && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-destructive shrink-0"
                      title="Unmap all views"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleUnmapAll(app, sol);
                      }}
                      disabled={isUnmapping || false}
                    >
                      {isUnmapping ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  )}
                </button>

                {isOpen && (
                  <SolutionViewsEditor
                    app={app}
                    solution={sol}
                    availableViews={views}
                    onSolutionChanged={handleSolutionChanged}
                  />
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default SolutionsManagerContent;
