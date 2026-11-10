import React from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { Chips, CodeBlock, InlineError, KeyValues, Meter, StatusPill, SubHeading, type KV } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import type { HybridSearchResponse, SearchResult } from '@/services/ontoApi';
import { docSystem, docTitle, metaLabel, metaValue, pct, typeLabel } from './ragMeta';

interface RetrievalBundleProps {
  results: HybridSearchResponse | null;
  /** Optional: show a loading skeleton while a search runs. */
  loading?: boolean;
  /** Optional: the last search failed. */
  error?: string | null;
  onRetry?: () => void;
}

const HIDDEN_META = new Set(['object_name', 'title', 'name']);

function ResultRow({ result, rank, selected, onSelect }: { result: SearchResult; rank: number; selected: boolean; onSelect: () => void }) {
  const system = docSystem(result);
  const score = pct(result.similarity);
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected}
      style={{ ['--i' as any]: Math.min(rank - 1, 12) }}
      className={cn(
        'rise flex w-full gap-3 border-b border-border px-4 py-3 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
        selected ? 'bg-accent' : 'hover:bg-accent/60',
      )}
    >
      <span className="num w-5 shrink-0 pt-0.5 text-right text-xs text-subtle-foreground">{rank}</span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2">
          {system && <SystemLogo system={system} size="xs" />}
          <span className={cn('min-w-0 flex-1 truncate text-sm text-foreground', selected && 'font-medium')}>{docTitle(result)}</span>
        </span>
        <span className="mt-0.5 block truncate text-xs text-muted-foreground">
          {typeLabel(result.content_type)}{system ? ` · ${systemName(system)}` : ''}{result.graph_expanded ? ' · via graph' : ''}
        </span>
        <span className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{result.content}</span>
        <span className="mt-2 flex items-center gap-2.5">
          <span className="grow-x block flex-1" style={{ ['--i' as any]: Math.min(rank - 1, 12) }}>
            <Meter value={score} label="Similarity" />
          </span>
          <span className="num w-9 shrink-0 text-right text-xs text-foreground">{score}%</span>
        </span>
      </span>
    </button>
  );
}

function ResultDetail({ result, rank }: { result: SearchResult; rank: number }) {
  const [showRaw, setShowRaw] = React.useState(false);
  React.useEffect(() => { setShowRaw(false); }, [result.source_id]);
  const system = docSystem(result);
  const score = pct(result.similarity);

  const facts: KV[] = [
    { label: 'Type', value: typeLabel(result.content_type) },
    { label: 'Found by', value: result.graph_expanded ? 'Graph expansion' : 'Vector search' },
    ...Object.entries(result.metadata || {})
      .filter(([key, value]) => !HIDDEN_META.has(key) && metaValue(value) !== '')
      .map(([key, value]): KV => {
        if (key === 'source_system' || key === 'target_system' || key === 'system') {
          return { label: metaLabel(key), value: <span className="inline-flex items-center gap-2"><SystemLogo system={String(value)} size="xs" />{systemName(String(value))}</span> };
        }
        if (key === 'risk_level' || key === 'fdw_mapping_status') return { label: metaLabel(key), value: <StatusPill status={String(value)} /> };
        return { label: metaLabel(key), value: metaValue(value), mono: key === 'file' || /_id$/.test(key) };
      }),
  ];

  return (
    <div key={result.source_id} className="animate-fade-in px-5 py-5 sm:px-6">
      <div className="flex items-start gap-3.5">
        <SystemLogo system={system || 'knowledge'} tile size="md" />
        <div className="min-w-0 flex-1">
          <h3 className="text-xl font-medium tracking-tight text-foreground">{docTitle(result)}</h3>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Rank <span className="num">{rank}</span> · {typeLabel(result.content_type)}{system ? ` from ${systemName(system)}` : ''}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <div className="num text-xl font-medium text-foreground">{score}%</div>
          <div className="text-xs text-muted-foreground">similarity</div>
        </div>
      </div>

      <div className="mt-6 grid gap-x-10 gap-y-7 xl:grid-cols-[minmax(0,1fr)_300px]">
        <section className="min-w-0">
          <SubHeading>Content</SubHeading>
          <p className="whitespace-pre-wrap break-words text-sm leading-6 text-foreground">{result.content}</p>
        </section>
        <section className="min-w-0">
          <SubHeading>Details</SubHeading>
          <KeyValues items={facts} />
        </section>
      </div>

      <div className="mt-7 border-t border-border pt-4">
        <button
          type="button"
          onClick={() => setShowRaw(v => !v)}
          aria-expanded={showRaw}
          className="inline-flex items-center gap-1.5 rounded text-sm font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Icon name="chevron-right" className={cn('h-3 w-3 transition-transform duration-200', showRaw && 'rotate-90')} />
          Technical details
        </button>
        {showRaw && (
          <div className="mt-3 animate-fade-in">
            <p className="mb-1.5 font-mono text-xs text-muted-foreground">{result.source_id}</p>
            <CodeBlock maxHeight={320}>{JSON.stringify(result, null, 2)}</CodeBlock>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Retrieval bundle: what a query brought back, ranked, with the selected
 * result open beside the list (master and detail).
 */
const RetrievalBundle: React.FC<RetrievalBundleProps> = ({ results, loading, error, onRetry }) => {
  const [category, setCategory] = React.useState('all');
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [browseOpen, setBrowseOpen] = React.useState(false);

  // A new result set starts on its best match with no category filter.
  React.useEffect(() => { setCategory('all'); setSelectedId(null); }, [results]);

  if (error) return <InlineError onRetry={onRetry}>The search did not finish. {error}</InlineError>;

  if (loading && !results) {
    return (
      <div className="grid overflow-hidden rounded-xl border border-border bg-card lg:h-[620px] lg:grid-cols-[340px_minmax(0,1fr)]" aria-busy="true">
        <div className="hidden space-y-4 border-r border-border p-4 lg:block">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="space-y-2"><Skeleton className="h-4 w-3/4" /><Skeleton className="h-3 w-full" /><Skeleton className="h-1 w-full" /></div>)}
        </div>
        <div className="space-y-4 p-6"><Skeleton className="h-7 w-64" /><Skeleton className="h-4 w-48" /><Skeleton className="h-40 w-full" /></div>
      </div>
    );
  }

  if (!results) {
    return <EmptyState icon="search" title="Run a query to see what comes back" description="Results are ranked by similarity. Select one to read its content and where it came from." />;
  }

  const all = results.results || [];
  if (all.length === 0) {
    return <EmptyState icon="search" title="Nothing matched this query" description="Try other words, remove the category filter or raise the graph hops." />;
  }

  const categories = Object.entries(results.by_category || {});
  const visible = category === 'all' ? all : all.filter(r => r.content_type === category);
  const selected = visible.find(r => r.source_id === selectedId) || visible[0] || all[0];
  const rankOf = (r: SearchResult) => all.indexOf(r) + 1;

  const list = (
    <>
      <div className="shrink-0 border-b border-border px-3 py-2">
        <Chips
          label="Filter results by type"
          value={category}
          onChange={setCategory}
          options={[
            { value: 'all', label: 'All', count: all.length },
            ...categories.map(([key, docs]) => ({ value: key, label: typeLabel(key), count: (docs as SearchResult[]).length })),
          ]}
        />
      </div>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {visible.map(r => (
          <ResultRow
            key={r.source_id}
            result={r}
            rank={rankOf(r)}
            selected={selected?.source_id === r.source_id}
            onSelect={() => { setSelectedId(r.source_id); setBrowseOpen(false); }}
          />
        ))}
      </div>
    </>
  );

  return (
    <div className={cn('transition-opacity duration-200', loading && 'opacity-60')}>
      <p className="mb-3 text-sm text-muted-foreground">
        <span className="num text-foreground">{results.total}</span> {results.total === 1 ? 'result' : 'results'}: <span className="num text-foreground">{results.vector_hits}</span> by vector search and <span className="num text-foreground">{results.graph_hits}</span> added by graph expansion.
      </p>

      <div className="grid overflow-hidden rounded-xl border border-border bg-card shadow-xs lg:h-[620px] lg:grid-cols-[340px_minmax(0,1fr)]">
        <div className="hidden min-h-0 flex-col border-r border-border bg-sidebar/40 lg:flex">{list}</div>

        <div className="flex min-h-0 min-w-0 flex-col">
          <div className="shrink-0 border-b border-border px-4 py-2 lg:hidden">
            <Button variant="outline" size="sm" className="w-full justify-between" onClick={() => setBrowseOpen(true)}>
              <span className="flex min-w-0 items-center gap-2">
                <Icon name="list" className="h-3.5 w-3.5" />
                <span className="truncate">{selected ? docTitle(selected) : 'Browse results'}</span>
              </span>
              <span className="flex items-center gap-1.5 font-normal text-muted-foreground">
                <span className="num">{selected ? rankOf(selected) : 0} of {all.length}</span>
                <Icon name="chevron-down" className="h-3.5 w-3.5" />
              </span>
            </Button>
          </div>
          <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
            {selected && <ResultDetail result={selected} rank={rankOf(selected)} />}
          </div>
        </div>
      </div>

      <Sheet open={browseOpen} onOpenChange={setBrowseOpen}>
        <SheetContent side="left" className="flex w-full flex-col gap-0 p-0 sm:max-w-sm">
          <div className="border-b border-border px-4 py-3.5 pr-12">
            <SheetTitle className="text-md font-medium">Results</SheetTitle>
            <SheetDescription className="sr-only">Choose a result to read</SheetDescription>
          </div>
          {list}
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default RetrievalBundle;
