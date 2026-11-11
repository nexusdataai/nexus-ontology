import { useEffect, useMemo, useState } from 'react';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Skeleton } from './ui/skeleton';
import { Icon, type IconName } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { SolutionCover } from '@/components/apps/SolutionCover';
import { useNavigate } from 'react-router-dom';
import {
  solutionsCatalogService,
  SolutionCatalogEntry,
  SolutionSearchHit,
} from '@/services/solutionsCatalogService';

// ---------------------------------------------------------------------------
// Static icon + color maps.
// The API returns icon/color strings; we map them to real Lucide components
// and Tailwind classes here so the DDB payload stays presentation-agnostic.
// ---------------------------------------------------------------------------

/** The API sends Lucide-style icon names; map them to the product icon set. */
const ICON_MAP: Record<string, IconName> = {
  ShoppingCart: 'shopping-cart', TrendingUp: 'trend-up', Package: 'box', FileText: 'document',
  Factory: 'factory', Shield: 'shield-check', Users: 'users', Leaf: 'leaf', Truck: 'truck',
  BarChart3: 'chart-bar', Receipt: 'receipt', ClipboardList: 'clipboard', Sparkles: 'sparkles',
};

const CATEGORIES = ['All', 'Finance', 'Planning', 'Operations', 'Risk', 'Revenue', 'ESG', 'CPQ'];

function resolveIcon(name?: string): IconName {
  return (name && ICON_MAP[name]) || 'apps';
}

// ---------------------------------------------------------------------------

export function AppCatalogue() {
  const nav = useNavigate();
  const [apps, setApps] = useState<SolutionCatalogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [nlpQuery, setNlpQuery] = useState('');
  const [nlpBusy, setNlpBusy] = useState(false);
  const [nlpHits, setNlpHits] = useState<SolutionSearchHit[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const r = await solutionsCatalogService.list();
        if (!cancelled) setApps(r.items || []);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const filtered = useMemo(() => {
    return apps.filter((a) => {
      if (
        search
        && !a.title?.toLowerCase().includes(search.toLowerCase())
        && !a.description?.toLowerCase().includes(search.toLowerCase())
      ) return false;
      if (category !== 'All' && a.category !== category) return false;
      return true;
    });
  }, [apps, search, category]);

  const runNlpSearch = async () => {
    const q = nlpQuery.trim();
    if (!q) {
      setNlpHits([]);
      return;
    }
    setNlpBusy(true);
    try {
      const r = await solutionsCatalogService.search(q, 3);
      setNlpHits(r.items || []);
    } catch (e) {
      setNlpHits([]);
    } finally {
      setNlpBusy(false);
    }
  };

  const nlpHitIds = new Set(nlpHits.map((h) => h.source_id));
  const orderedForNlp = nlpHits.length
    ? [
        ...filtered.filter((a) => nlpHitIds.has(a.solutionId)),
        ...filtered.filter((a) => !nlpHitIds.has(a.solutionId)),
      ]
    : filtered;

  const GOALS = ['Reduce DSO', 'Stop stockouts', 'Cut maverick spend', 'Spot supplier risk early', 'Raise first-pass yield'];
  const askGoal = async (goal: string) => {
    setNlpQuery(goal);
    setNlpBusy(true);
    try {
      const r = await solutionsCatalogService.search(goal, 3);
      setNlpHits(r.items || []);
    } catch {
      setNlpHits([]);
    } finally {
      setNlpBusy(false);
    }
  };

  const counts = CATEGORIES.reduce<Record<string, number>>((acc, c) => {
    acc[c] = c === 'All' ? apps.length : apps.filter(a => a.category === c).length;
    return acc;
  }, {});
  const liveCount = apps.filter(a => (a.status || 'available') === 'available').length;
  // Every solution uses the same card, three to a row. Matches for a goal are listed first.
  const rest = orderedForNlp;
  const openApp = (a: SolutionCatalogEntry) => { if ((a.status || 'available') === 'available') nav(`/apps/${a.solutionId}`); };

  return (
    <div className="page">
      {/* Hero: start from the outcome, not from a list */}
      <section className="relative overflow-hidden rounded-2xl border border-border bg-card px-5 py-6 shadow-xs sm:px-8 sm:py-7">
        <div
          className="pointer-events-none absolute inset-0 opacity-70 [mask-image:radial-gradient(ellipse_at_top_right,black,transparent_70%)]"
          style={{ backgroundImage: 'radial-gradient(hsl(var(--border-strong)) 1px, transparent 1px)', backgroundSize: '20px 20px' }}
          aria-hidden="true"
        />
        <div className="relative max-w-3xl">
          <p className="text-sm text-muted-foreground">
            Solutions{!loading && <> · <span className="num text-foreground">{liveCount}</span> ready to run, <span className="num text-foreground">{apps.length}</span> in the catalogue</>}
          </p>
          <h1 className="mt-2 text-2xl font-medium tracking-tight text-foreground">What do you want to improve?</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground sm:text-md">
            Each solution is a packaged business application that runs on your own data and knowledge graph. Describe the outcome and we will point you to the right one.
          </p>

          <div className="mt-4 flex items-center gap-2 rounded-xl border border-border-strong bg-background p-1.5 pl-4 shadow-sm transition-[border-color,box-shadow] duration-200 focus-within:border-brand focus-within:ring-2 focus-within:ring-ring/25">
            <Icon name="sparkles" className="h-4 w-4 shrink-0 text-primary dark:text-brand-hi" />
            <Input
              value={nlpQuery}
              onChange={(e) => setNlpQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') runNlpSearch(); }}
              placeholder="For example: reduce DSO, or stop stockouts in EMEA"
              aria-label="Describe your goal"
              className="h-10 flex-1 border-0 bg-transparent px-0 text-md shadow-none hover:border-0 focus-visible:border-0 focus-visible:ring-0"
            />
            {nlpHits.length > 0 && (
              <Button size="sm" variant="ghost" onClick={() => { setNlpQuery(''); setNlpHits([]); }}>Clear</Button>
            )}
            <Button onClick={runNlpSearch} disabled={nlpBusy}>
              <Icon name={nlpBusy ? 'spinner' : 'search'} className={nlpBusy ? 'animate-spin' : undefined} />
              <span className="hidden sm:inline">Find solutions</span>
            </Button>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">Try</span>
            {GOALS.map(g => (
              <button
                key={g}
                type="button"
                onClick={() => askGoal(g)}
                className="rounded-full border border-border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-brand/50 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {g}
              </button>
            ))}
          </div>

          {nlpHits.length > 0 && (
            <p className="mt-4 animate-fade-up text-sm text-foreground">
              <Icon name="check-circle" className="mr-1.5 inline h-4 w-4 text-success" />
              {nlpHits.length} {nlpHits.length === 1 ? 'solution fits' : 'solutions fit'} that goal. They are marked and listed first.
            </p>
          )}
        </div>
      </section>

      {/* Filters */}
      <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-3">
        <div className="scrollbar-hide -mx-1 flex min-w-0 flex-1 gap-1 overflow-x-auto px-1" role="tablist" aria-label="Category">
          {CATEGORIES.filter(c => c === 'All' || loading || counts[c] > 0).map((c) => {
            const on = category === c;
            return (
              <button
                key={c}
                type="button"
                role="tab"
                aria-selected={on}
                onClick={() => setCategory(c)}
                className={`flex h-8 shrink-0 items-center gap-1.5 rounded-md px-3 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  on ? 'bg-accent font-medium text-foreground' : 'text-muted-foreground hover:bg-accent/70 hover:text-foreground'
                }`}
              >
                {c}
                {!loading && <span className="num text-xs text-muted-foreground">{counts[c]}</span>}
              </button>
            );
          })}
        </div>
        <div className="relative w-full sm:w-64">
          <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-subtle-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filter by name" aria-label="Filter by name" className="h-9 pl-9" />
        </div>
      </div>

      {error && (
        <div role="alert" className="mt-4 rounded-md border border-destructive/25 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          Could not load solutions: {error}
        </div>
      )}

      {loading && (
        <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-80 rounded-2xl" />)}
        </div>
      )}

      {!loading && (
        <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {rest.map((app, i) => {
            const nlpMatch = nlpHitIds.has(app.solutionId);
            const available = (app.status || 'available') === 'available';
            return (
              <article
                key={app.solutionId}
                style={{ '--i': Math.min(i, 9) } as React.CSSProperties}
                onClick={() => openApp(app)}
                className={`rise group flex flex-col overflow-hidden rounded-2xl border bg-card shadow-xs transition-[border-color,box-shadow,transform] duration-300 ease-brand-out ${
                  available ? 'cursor-pointer hover:-translate-y-1 hover:border-brand/50 hover:shadow-lg' : ''
                } ${nlpMatch ? 'border-brand/60 ring-1 ring-brand/30' : 'border-border'}`}
              >
                <SolutionCover icon={resolveIcon(app.icon)} className={`border-b border-border ${available ? '' : 'opacity-50 grayscale'}`} />
                <div className="flex flex-1 flex-col p-5">
                  <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
                    <span className="truncate">{app.category || 'Solution'}</span>
                    {nlpMatch ? <Badge variant="info">Matches your goal</Badge>
                      : available ? <span className="inline-flex shrink-0 items-center gap-1.5 font-medium text-foreground"><span className="dot-live text-success" aria-hidden="true" />Ready to run</span>
                      : <Badge variant="neutral">Coming soon</Badge>}
                  </div>
                  <h3 className="mt-2 truncate text-lg font-medium tracking-tight text-foreground" title={app.title}>{app.title}</h3>
                  <p className="mt-1 line-clamp-2 min-h-10 text-sm text-muted-foreground">{app.description}</p>

                  {/* One line of targets on every card, so the cards line up. */}
                  <ul className="mt-4 flex h-6 flex-wrap gap-1.5 overflow-hidden">
                    {(app.kpis || []).slice(0, 3).map(k => (
                      <li key={k} className="num whitespace-nowrap rounded-md border border-border bg-surface-2/70 px-2 py-0.5 text-xs text-muted-foreground">{k}</li>
                    ))}
                  </ul>

                  <div className="min-h-5 flex-1" />
                  <div className="flex items-center justify-between gap-3 border-t border-border pt-3 text-xs text-muted-foreground">
                    <span className="flex min-w-0 items-center gap-3">
                      {app.timeToValue && <span className="inline-flex items-center gap-1"><Icon name="clock" className="h-3.5 w-3.5" />{app.timeToValue}</span>}
                      {(app.entities || []).length > 0 && <span><span className="num">{app.entities!.length}</span> entities</span>}
                    </span>
                    {available && (
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); openApp(app); }}
                        className="inline-flex shrink-0 items-center gap-1 rounded text-sm font-medium text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        Open <Icon name="arrow-right" className="h-3.5 w-3.5 transition-transform duration-300 ease-brand-out group-hover:translate-x-0.5" />
                      </button>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
          {orderedForNlp.length === 0 && !error && (
            <div className="col-span-full">
              <EmptyState icon="apps" title="No solutions match" description="Try another category or clear the filter." />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
