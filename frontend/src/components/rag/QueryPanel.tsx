import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icon } from '@/components/ds/Icon';
import { Chips } from '@/components/ds/kit';
import { cn } from '@/lib/utils';

interface QueryPanelProps {
  onSearch: (query: string, contentType?: string, graphHops?: number) => void;
  loading: boolean;
}

// Chips need a non-empty value, so "all" stands for no category filter.
const CONTENT_TYPES = [
  { value: 'all', label: 'All' },
  { value: 'onto_schema', label: 'Schema' },
  { value: 'onto_policy', label: 'Policy' },
  { value: 'onto_workflow', label: 'Workflow' },
  { value: 'onto_integration', label: 'Integration' },
];

/**
 * Query bar of the planning playground: the question on top, its options in a
 * quiet row underneath, and a few example questions to start from.
 */
const QueryPanel: React.FC<QueryPanelProps> = ({ onSearch, loading }) => {
  const [query, setQuery] = useState('');
  const [contentType, setContentType] = useState('');
  const [graphHops, setGraphHops] = useState(2);
  const [showFilters, setShowFilters] = useState(true);

  const handleSearch = () => {
    if (query.trim()) {
      onSearch(query.trim(), contentType || undefined, graphHops);
    }
  };

  const sampleQueries = [
    'What is Material_Master and how is it mapped to a data source?',
    'What policies apply to inventory safety stock levels?',
    'How does the demand forecasting workflow use Salesforce and SAP data?',
    'What entities are needed for the Order-to-Cash use case?',
    'Which system is the source of truth for customer credit limit?',
    'What happens when AR_Invoice is disputed?',
  ];

  return (
    <div>
      <form
        onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
        className="flex items-center gap-2 rounded-xl border border-border-strong bg-card p-1.5 pl-3.5 shadow-xs transition-[border-color,box-shadow] duration-200 focus-within:border-brand focus-within:ring-2 focus-within:ring-ring/30"
      >
        <Icon name="search" className="shrink-0 text-subtle-foreground" />
        <Input
          placeholder="Ask about schemas, policies, workflows or integrations"
          aria-label="Retrieval query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="h-9 min-w-0 flex-1 border-0 bg-transparent px-0 text-base shadow-none hover:border-0 focus-visible:border-0 focus-visible:ring-0"
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => setShowFilters(!showFilters)}
          aria-label={showFilters ? 'Hide search options' : 'Show search options'}
          aria-expanded={showFilters}
          className={cn(showFilters && 'bg-accent text-foreground')}
        >
          <Icon name="sliders" />
        </Button>
        <Button type="submit" disabled={loading || !query.trim()}>
          <Icon name={loading ? 'spinner' : 'search'} className={cn(loading && 'animate-spin')} />
          <span className="hidden sm:inline">{loading ? 'Searching' : 'Search'}</span>
        </Button>
      </form>

      {showFilters && (
        <div className="mt-2.5 flex animate-fade-in flex-wrap items-center gap-x-5 gap-y-2 px-1 text-sm">
          <div className="flex min-w-0 items-center gap-2">
            <span className="shrink-0 text-xs text-muted-foreground">Category</span>
            <Chips
              label="Category"
              value={contentType || 'all'}
              onChange={(v) => setContentType(v === 'all' ? '' : v)}
              options={CONTENT_TYPES}
            />
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="graph-hops" className="shrink-0 text-xs text-muted-foreground">Graph hops</label>
            <Select value={String(graphHops)} onValueChange={(v) => setGraphHops(Number(v))}>
              <SelectTrigger id="graph-hops" className="h-8 w-[72px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                {[0, 1, 2, 3].map((h) => (
                  <SelectItem key={h} value={String(h)}>{h}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      <div className="mt-3 flex items-center gap-2 px-1">
        <span className="shrink-0 text-xs text-muted-foreground">Try</span>
        <div className="scrollbar-hide -mr-1 flex min-w-0 gap-1.5 overflow-x-auto pr-1">
          {sampleQueries.map((sq, i) => (
            <button
              key={i}
              type="button"
              title={sq}
              onClick={() => { setQuery(sq); onSearch(sq, contentType || undefined, graphHops); }}
              className="h-7 max-w-[280px] shrink-0 truncate rounded-full border border-border px-3 text-xs text-muted-foreground transition-colors duration-150 hover:border-brand/50 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default QueryPanel;
