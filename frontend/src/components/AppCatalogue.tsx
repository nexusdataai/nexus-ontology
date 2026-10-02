import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Input } from './ui/input';
import {
  ShoppingCart, BarChart3, Package, Factory, Truck, Users, Leaf, Shield, Search,
  TrendingUp, AlertTriangle, FileText, ArrowRight, Clock, Zap,
  Receipt, ClipboardList, Loader2, Sparkles,
} from 'lucide-react';
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

const ICON_MAP: Record<string, React.ElementType> = {
  ShoppingCart, TrendingUp, Package, FileText, Factory, Shield, Users, Leaf,
  Truck, BarChart3, Receipt, ClipboardList, Sparkles,
};

const DEFAULT_COLOR = 'from-slate-500 to-slate-700';

const CATEGORIES = ['All', 'Finance', 'Planning', 'Operations', 'Risk', 'Revenue', 'ESG', 'CPQ'];

function resolveIcon(name?: string): React.ElementType {
  return (name && ICON_MAP[name]) || Sparkles;
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

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="h-6 w-6 text-primary" />
            Supply Chain Solutions
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Enterprise AI solutions powered by the Semantic Ontology Layer
            {loading ? '' : ` — ${apps.length} solutions`}
          </p>
        </div>
      </div>

      {/* NLP search bar (Phase 5) */}
      <Card>
        <CardContent className="p-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary shrink-0" />
          <Input
            value={nlpQuery}
            onChange={(e) => setNlpQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') runNlpSearch(); }}
            placeholder="Describe your goal — e.g. 'reduce DSO' or 'stop stockouts in EMEA'"
            className="flex-1"
          />
          <Button size="sm" onClick={runNlpSearch} disabled={nlpBusy}>
            {nlpBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Search className="h-3.5 w-3.5 mr-1" />}
            NLP search
          </Button>
          {nlpHits.length > 0 && (
            <Button size="sm" variant="ghost" onClick={() => { setNlpQuery(''); setNlpHits([]); }}>
              Clear
            </Button>
          )}
        </CardContent>
      </Card>

      {nlpHits.length > 0 && (
        <div className="text-xs text-muted-foreground">
          Top matches (by similarity):
          <span className="ml-2 space-x-1">
            {nlpHits.map((h) => (
              <Badge key={h.source_id} variant="outline" className="text-[10px]">
                {h.source_id} ({Math.round((h.similarity || 0) * 100)}%)
              </Badge>
            ))}
          </span>
        </div>
      )}

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filter by name or description..." className="pl-9" />
        </div>
        <div className="flex gap-1 flex-wrap">
          {CATEGORIES.map((c) => (
            <Button key={c} variant={category === c ? 'default' : 'outline'} size="sm" onClick={() => setCategory(c)}>
              {c}
            </Button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading solutions catalog...
        </div>
      )}

      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded p-2">
          Failed to load solutions: {error}
        </div>
      )}

      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {orderedForNlp.map((app) => {
            const Icon = resolveIcon(app.icon);
            const color = app.color || DEFAULT_COLOR;
            const nlpMatch = nlpHitIds.has(app.solutionId);
            const status = app.status || 'available';
            return (
              <Card
                key={app.solutionId}
                className={`group hover:border-primary/50 transition-all duration-200 hover:shadow-lg overflow-hidden ${
                  nlpMatch ? 'border-primary/70 ring-1 ring-primary/50' : ''
                }`}
              >
                <div className={`h-1.5 bg-gradient-to-r ${color}`} />
                <CardContent className="pt-4 pb-4 space-y-3">
                  <div className="flex items-start justify-between">
                    <div className={`p-2.5 rounded-xl bg-gradient-to-br ${color} bg-opacity-10`}>
                      <Icon className="h-6 w-6 text-white" />
                    </div>
                    <div className="flex items-center gap-1.5">
                      {app.priority && <Badge variant="outline" className="text-[9px]">{app.priority}</Badge>}
                      <Badge className={status === 'available' ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-amber-500/20 text-amber-400 border-amber-500/30'}>
                        {status === 'available' ? 'Available' : 'Coming Soon'}
                      </Badge>
                      {nlpMatch && (
                        <Badge className="bg-primary/20 text-primary border-primary/30 text-[9px]">
                          <Sparkles className="h-2.5 w-2.5 mr-0.5" /> Match
                        </Badge>
                      )}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-semibold text-sm">{app.title}</h3>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{app.description}</p>
                  </div>

                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground flex-wrap">
                    {app.timeToValue && <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{app.timeToValue}</span>}
                    {(app.entities || []).length > 0 && <span>{app.entities!.length} entities</span>}
                    {app.category && <span>{app.category}</span>}
                  </div>

                  {(app.kpis || []).length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {app.kpis!.map((kpi, i) => (
                        <Badge key={i} variant="outline" className="text-[8px] font-mono">{kpi}</Badge>
                      ))}
                    </div>
                  )}

                  {(app.entities || []).length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1 border-t border-border/50">
                      {app.entities!.slice(0, 3).map((e) => (
                        <span key={e} className="text-[9px] px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground">{e}</span>
                      ))}
                      {app.entities!.length > 3 && (
                        <span className="text-[9px] px-1.5 py-0.5 text-muted-foreground">+{app.entities!.length - 3}</span>
                      )}
                    </div>
                  )}

                  {status === 'available' ? (
                    <Button size="sm" className="w-full" onClick={() => nav(`/apps/${app.solutionId}`)}>
                      <ArrowRight className="h-3.5 w-3.5 mr-1" /> Open App
                    </Button>
                  ) : (
                    <Button size="sm" variant="outline" className="w-full" disabled>
                      <AlertTriangle className="h-3.5 w-3.5 mr-1" /> Coming Soon
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
          {orderedForNlp.length === 0 && (
            <div className="col-span-full text-center text-sm text-muted-foreground py-8">
              No solutions match the current filters.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
