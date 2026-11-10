import { useEffect, useMemo, useState } from 'react';
import { Layers, Loader2, Search, AppWindow, Plus, X } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
          className="h-8"
          disabled={disabled || !viewId}
          title={!viewId ? 'Save the view first to manage solutions' : undefined}
        >
          <Layers className="h-3.5 w-3.5 mr-1" />
          Solutions
          {attachedCount > 0 && (
            <span className="ml-1 text-xs bg-primary/10 text-primary rounded-full px-1.5 py-0.5">
              {attachedCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="px-3 pt-3 pb-2 border-b">
          <div className="text-xs font-semibold text-muted-foreground mb-2">
            Solutions for this View
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

        {loading ? (
          <div className="flex items-center justify-center h-24">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <ScrollArea className="max-h-72">
            {filteredSolutions.length > 0 ? (
              <div className="p-2 space-y-1">
                {filteredSolutions.map((s) => {
                  const app = s.appId ? appLookup.get(s.appId) : undefined;
                  const Icon = app?.icon;
                  const attached = isAttached(s.solutionId);
                  const isPending = pending.has(s.solutionId);
                  return (
                    <button
                      key={s.solutionId}
                      onClick={() => toggleMembership(s.solutionId)}
                      disabled={isPending}
                      className={cn(
                        'w-full flex items-start gap-2 p-2 rounded-md text-left text-xs transition-colors hover:bg-muted/50',
                        attached && 'bg-primary/5',
                      )}
                    >
                      <Checkbox
                        checked={attached}
                        disabled={isPending}
                        onCheckedChange={() => toggleMembership(s.solutionId)}
                        className="mt-0.5"
                      />
                      {Icon && app ? (
                        <div className={`p-1 rounded bg-gradient-to-br ${app.color} shrink-0`}>
                          <Icon className="h-3 w-3 text-white" />
                        </div>
                      ) : (
                        <AppWindow className="h-3.5 w-3.5 mt-0.5 text-muted-foreground" />
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="font-medium truncate">{s.name}</div>
                        {s.appId && (
                          <div className="text-xs text-muted-foreground font-mono truncate">
                            {s.appId}
                          </div>
                        )}
                      </div>
                      {isPending && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="p-3 text-xs text-muted-foreground text-center">
                {solutions.length === 0
                  ? 'No solutions yet. Link to an app below.'
                  : 'No matches.'}
              </div>
            )}

            {unlinkedApps.length > 0 && (
              <div className="border-t p-2 space-y-1">
                <div className="text-xs text-muted-foreground px-2 py-1">
                  Link to an unused app
                </div>
                {unlinkedApps.map((app) => {
                  const Icon = app.icon;
                  const isCreating = creatingForAppId === app.id;
                  return (
                    <button
                      key={app.id}
                      onClick={() => handleCreateAndAttach(app.id)}
                      disabled={isCreating}
                      className="w-full flex items-center gap-2 p-2 rounded-md text-left text-xs hover:bg-muted/50 transition-colors"
                    >
                      <div className={`p-1 rounded bg-gradient-to-br ${app.color} shrink-0`}>
                        <Icon className="h-3 w-3 text-white" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-medium truncate">{app.name}</div>
                        <div className="text-xs text-muted-foreground truncate">
                          {app.id}
                        </div>
                      </div>
                      {isCreating ? (
                        <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                      ) : (
                        <Plus className="h-3 w-3 text-muted-foreground" />
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </ScrollArea>
        )}

        <div className="border-t px-3 py-2 flex items-center justify-end">
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setOpen(false)}>
            <X className="h-3 w-3 mr-1" /> Close
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default ViewSolutionsPicker;
