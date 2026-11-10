import { useEffect, useMemo, useState } from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { SearchInput } from '@/components/ds/kit';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import type { Solution, SolutionSummary } from '@/lib/foundry/model';
import { solutionService } from '@/services/solutionService';
import { APP_REGISTRY } from '@/config/appRegistry';

interface ViewSolutionsPickerProps {
  viewId?: string;
  /** Trigger button is disabled until the view has been saved. */
  disabled?: boolean;
}

export function ViewSolutionsPicker({ viewId, disabled }: ViewSolutionsPickerProps) {
  const [open, setOpen] = useState(false);
  const [solutions, setSolutions] = useState<SolutionSummary[]>([]);
  const [details, setDetails] = useState<Record<string, Solution>>({});
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState('');
  const [creatingForAppId, setCreatingForAppId] = useState<string | null>(null);

  const appLookup = useMemo(() => {
    const m = new Map<string, (typeof APP_REGISTRY)[number]>();
    APP_REGISTRY.forEach((a) => m.set(a.id, a));
    return m;
  }, []);

  const refresh = async () => {
    if (!viewId) return;
    setLoading(true);
    try {
      const list = await solutionService.list();
      const detailMap: Record<string, Solution> = {};
      await Promise.all(
        list.map(async (s) => {
          try {
            detailMap[s.solutionId] = await solutionService.get(s.solutionId);
          } catch {
            /* skip */
          }
        }),
      );
      setSolutions(list);
      setDetails(detailMap);
    } catch {
      toast.error('Failed to load solutions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, viewId]);

  const isAttached = (solutionId: string) => {
    if (!viewId) return false;
    const detail = details[solutionId];
    return !!detail?.views.some((v) => v.viewId === viewId);
  };

  const toggleMembership = async (solutionId: string) => {
    if (!viewId) return;
    setPending((prev) => new Set(prev).add(solutionId));
    try {
      const attached = isAttached(solutionId);
      const updated = attached
        ? await solutionService.removeView(solutionId, viewId)
        : await solutionService.addView(solutionId, viewId);
      setDetails((prev) => ({ ...prev, [solutionId]: updated }));
      setSolutions((prev) =>
        prev.map((s) =>
          s.solutionId === solutionId ? { ...s, viewCount: updated.views.length } : s,
        ),
      );
      toast.success(attached ? 'Detached from solution' : 'Attached to solution');
    } catch (e: any) {
      toast.error(e?.message || 'Failed to update solution');
    } finally {
      setPending((prev) => {
        const next = new Set(prev);
        next.delete(solutionId);
        return next;
      });
    }
  };

  const handleCreateAndAttach = async (appId: string) => {
    if (!viewId) return;
    setCreatingForAppId(appId);
    try {
      const app = appLookup.get(appId);
      const created = await solutionService.create({
        appId,
        name: app?.name || appId,
        description: app?.description,
      });
      const linked = await solutionService.addView(created.solutionId, viewId);
      setDetails((prev) => ({ ...prev, [linked.solutionId]: linked }));
      setSolutions((prev) => [
        ...prev,
        {
          solutionId: linked.solutionId,
          name: linked.name,
          description: linked.description,
          appId: linked.appId,
          icon: linked.icon,
          viewCount: linked.views.length,
          createdAt: linked.createdAt,
          updatedAt: linked.updatedAt,
          createdBy: linked.createdBy,
        },
      ]);
      toast.success(`Solution created and view attached to ${app?.shortName || appId}`);
    } catch (e: any) {
      toast.error(e?.message || 'Failed to create solution');
    } finally {
      setCreatingForAppId(null);
    }
  };

  const filteredSolutions = useMemo(() => {
    if (!query.trim()) return solutions;
    const q = query.toLowerCase();
    return solutions.filter((s) => {
      const app = s.appId ? appLookup.get(s.appId) : undefined;
      return (
        s.name.toLowerCase().includes(q) ||
        (app?.name || '').toLowerCase().includes(q) ||
        (s.appId || '').toLowerCase().includes(q)
      );
    });
  }, [solutions, query, appLookup]);

  const linkedAppIds = solutions.map((s) => s.appId).filter((x): x is string => Boolean(x));
  const unlinkedApps = useMemo(() => {
    const set = new Set(linkedAppIds);
    return APP_REGISTRY.filter((a) => !set.has(a.id));
  }, [linkedAppIds]);

  const attachedCount = solutions.reduce(
    (acc, s) => (isAttached(s.solutionId) ? acc + 1 : acc),
    0,
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled || !viewId}
          title={!viewId ? 'Save the view first, then attach it to a solution' : 'Choose the solutions that show this view'}
        >
          <Icon name="apps" className="h-3.5 w-3.5" />
          Solutions
          {attachedCount > 0 && <span className="num text-xs text-muted-foreground">{attachedCount}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[min(340px,calc(100vw-2rem))] p-0">
        <div className="border-b border-border px-3 pb-3 pt-3.5">
          <div className="text-sm font-medium text-foreground">Show this view in</div>
          <p className="mb-2.5 mt-0.5 text-xs text-muted-foreground">
            Attached solutions list the view in their side menu. Changes apply straight away.
          </p>
          <SearchInput value={query} onChange={setQuery} placeholder="Search solutions" className="w-full sm:w-full" />
        </div>

        {loading ? (
          <div className="space-y-3 p-3" aria-busy="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex items-center gap-2.5">
                <Skeleton className="h-4 w-4" />
                <Skeleton className="h-4 flex-1" />
              </div>
            ))}
          </div>
        ) : (
          <ScrollArea className="max-h-72">
            {filteredSolutions.length > 0 ? (
              <ul className="p-1.5">
                {filteredSolutions.map((s) => {
                  const app = s.appId ? appLookup.get(s.appId) : undefined;
                  const AppIcon = app?.icon;
                  const attached = isAttached(s.solutionId);
                  const isPending = pending.has(s.solutionId);
                  return (
                    <li key={s.solutionId}>
                      <button
                        type="button"
                        onClick={() => toggleMembership(s.solutionId)}
                        disabled={isPending}
                        aria-pressed={attached}
                        className={cn(
                          'flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left text-sm transition-colors hover:bg-accent/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                          attached && 'bg-accent',
                        )}
                      >
                        <Checkbox checked={attached} disabled={isPending} tabIndex={-1} aria-hidden="true" className="pointer-events-none" />
                        {AppIcon ? (
                          <AppIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
                        ) : (
                          <Icon name="apps" className="text-muted-foreground" />
                        )}
                        <span className="min-w-0 flex-1 truncate font-medium text-foreground">{s.name}</span>
                        {isPending && <Icon name="spinner" className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="px-3 py-5 text-center text-xs text-muted-foreground">
                {solutions.length === 0
                  ? 'No solutions yet. Start one from an app below.'
                  : 'No solution matches this search.'}
              </p>
            )}

            {unlinkedApps.length > 0 && (
              <div className="border-t border-border p-1.5">
                <div className="px-2 pb-1 pt-1.5 text-xs text-muted-foreground">
                  Start a solution for an app and attach this view
                </div>
                <ul>
                  {unlinkedApps.map((app) => {
                    const AppIcon = app.icon;
                    const isCreating = creatingForAppId === app.id;
                    return (
                      <li key={app.id}>
                        <button
                          type="button"
                          onClick={() => handleCreateAndAttach(app.id)}
                          disabled={isCreating}
                          className="flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left text-sm transition-colors hover:bg-accent/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <AppIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
                          <span className="min-w-0 flex-1 truncate text-foreground">{app.name}</span>
                          <Icon name={isCreating ? 'spinner' : 'plus'} className={cn('h-3.5 w-3.5 text-muted-foreground', isCreating && 'animate-spin')} />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </ScrollArea>
        )}

        <div className="flex items-center justify-end border-t border-border px-3 py-2">
          <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
            Done
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default ViewSolutionsPicker;
