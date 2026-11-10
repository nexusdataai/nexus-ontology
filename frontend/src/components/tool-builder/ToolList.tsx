import { useMemo, useState } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { Chips, SearchInput } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { RiskPill, ToolSystem } from '@/components/reasoning/toolMeta';
import type { ToolSummary } from '@/services/toolBuilderService';

interface Props {
  tools: ToolSummary[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRefresh: () => void;
}

const RISK_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'read_only', label: 'Read' },
  { value: 'low_risk_write', label: 'Low risk' },
  { value: 'high_risk_write', label: 'High risk' },
];

/** List of the tools written in the builder, with search and a risk filter. */
export default function ToolList({
  tools, loading, selectedId, onSelect,
}: Props) {
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState<string>('');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return tools.filter(t => {
      if (riskFilter && t.risk_level !== riskFilter) return false;
      if (!q) return true;
      return t.name.toLowerCase().includes(q)
        || (t.description || '').toLowerCase().includes(q)
        || t.tags.some(tg => tg.toLowerCase().includes(q));
    });
  }, [tools, search, riskFilter]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 space-y-2 border-b border-border px-3 py-3">
        <SearchInput value={search} onChange={setSearch} placeholder="Search tools" className="sm:w-full" />
        <Chips
          label="Filter by risk"
          value={riskFilter || 'all'}
          onChange={(v) => setRiskFilter(v === 'all' ? '' : v)}
          options={RISK_FILTERS}
        />
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {loading && tools.length === 0 && (
          <div className="space-y-4 p-4" aria-busy="true">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="space-y-2"><Skeleton className="h-4 w-40" /><Skeleton className="h-3 w-full" /></div>
            ))}
          </div>
        )}
        {filtered.length === 0 && !loading && (
          <p className="px-4 py-8 text-center text-sm text-muted-foreground">
            {tools.length === 0 ? 'No tools yet. Use "New tool" to write the first one.' : 'No tools match the search.'}
          </p>
        )}
        {filtered.map((t, i) => {
          const selected = selectedId === t.tool_id;
          const seeded = t.tags.includes('playbook_seeded');
          return (
            <button
              key={t.tool_id}
              type="button"
              onClick={() => onSelect(t.tool_id)}
              aria-current={selected}
              style={{ ['--i' as any]: Math.min(i, 12) }}
              className={cn(
                'rise block w-full border-b border-border px-4 py-3 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
                selected ? 'bg-accent' : 'hover:bg-accent/60',
              )}
            >
              <span className="flex items-center justify-between gap-3">
                <span className={cn('min-w-0 truncate font-mono text-sm text-foreground', selected && 'font-medium')}>{t.name}</span>
                <span className="num shrink-0 text-xs text-muted-foreground">v{t.current_version}</span>
              </span>
              <span className="mt-0.5 line-clamp-2 text-xs leading-5 text-muted-foreground">{t.description || 'No description'}</span>
              <span className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                <RiskPill risk={t.risk_level} />
                {t.connector_api && <ToolSystem api={t.connector_api} className="text-xs text-muted-foreground" />}
                {seeded && <span className="text-xs text-muted-foreground" title="Created from the tool definitions in the knowledge repository">From a playbook</span>}
              </span>
            </button>
          );
        })}
      </div>

      <div className="shrink-0 border-t border-border px-4 py-2 text-xs text-muted-foreground">
        <span className="num">{filtered.length}</span> of <span className="num">{tools.length}</span> tools
      </div>
    </div>
  );
}
