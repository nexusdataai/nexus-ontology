import { useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Plus, RefreshCw, Wrench } from 'lucide-react';
import type { RiskLevel, ToolSummary } from '@/services/toolBuilderService';

interface Props {
  tools: ToolSummary[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRefresh: () => void;
}

function riskColor(r: RiskLevel): string {
  if (r === 'high_risk_write') return 'text-red-300';
  if (r === 'low_risk_write') return 'text-amber-300';
  return 'text-green-300';
}

export default function ToolList({
  tools, loading, selectedId, onSelect, onNew, onRefresh,
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
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-border space-y-2">
        <div className="flex items-center gap-1">
          <Button size="sm" className="h-7 text-[11px] flex-1" onClick={onNew}>
            <Plus className="h-3 w-3 mr-1" /> New tool
          </Button>
          <Button size="sm" variant="outline" className="h-7" onClick={onRefresh}>
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
        <Input
          placeholder="Search..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-7 text-xs"
        />
        <div className="flex flex-wrap gap-1 text-[10px]">
          {['', 'read_only', 'low_risk_write', 'high_risk_write'].map((r) => (
            <Button
              key={r || 'all'}
              size="sm"
              variant={riskFilter === r ? 'default' : 'outline'}
              className="h-6 text-[10px] px-2"
              onClick={() => setRiskFilter(r)}
            >
              {r === '' ? 'all' : r.replace('_write', '')}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {filtered.length === 0 && !loading && (
          <div className="px-3 py-6 text-center text-xs text-muted-foreground italic">
            <Wrench className="h-5 w-5 mx-auto mb-2 opacity-40" />
            No tools yet. Click <span className="font-mono">+ New tool</span>.
          </div>
        )}
        {filtered.map(t => (
          <button
            key={t.tool_id}
            type="button"
            onClick={() => onSelect(t.tool_id)}
            className={`w-full text-left px-3 py-2 border-b border-border/40 hover:bg-muted/30 ${
              selectedId === t.tool_id ? 'bg-blue-600/10 border-l-2 border-l-blue-400' : ''
            }`}
          >
            <div className="flex items-center justify-between gap-2 mb-0.5">
              <span className="font-mono text-xs truncate">{t.name}</span>
              <div className="flex items-center gap-1 shrink-0">
                {t.tags.includes('playbook_seeded') && (
                  <Badge
                    variant="outline"
                    className="text-[9px] border-blue-400/40 text-blue-300"
                    title="Seeded from enterprise-knowledge/tools/ YAML catalogue"
                  >
                    playbook
                  </Badge>
                )}
                <Badge variant="outline" className={`text-[9px] ${riskColor(t.risk_level)}`}>
                  {t.risk_level.replace('_write', '')}
                </Badge>
              </div>
            </div>
            <div className="text-[10px] text-muted-foreground truncate">{t.description || '(no description)'}</div>
            <div className="flex items-center gap-1 flex-wrap mt-1">
              {t.tags.filter(tag => tag !== 'playbook_seeded').slice(0, 4).map(tag => (
                <span key={tag} className="px-1 py-0 rounded bg-muted/40 text-[9px]">{tag}</span>
              ))}
              {t.connector_api && (
                <span className="text-[9px] text-muted-foreground italic">{t.connector_api}</span>
              )}
            </div>
          </button>
        ))}
      </div>

      <div className="px-3 py-1 border-t border-border text-[10px] text-muted-foreground">
        {filtered.length} / {tools.length}
      </div>
    </div>
  );
}
