import { useEffect, useMemo, useRef, useState } from 'react';
import { Icon, type IconName } from '@/components/ds/Icon';
import { Input } from '@/components/ui/input';
import type { CatalogNodeType } from '@/services/dataFlowService';
import type { DataPlane } from '@/services/dataPlaneService';
import { cn } from '@/lib/utils';

const CATEGORY_LABEL: Record<string, string> = {
  sources: 'Sources',
  transform: 'Transform',
  ai: 'AI steps',
  sinks: 'Sinks',
  control: 'Control',
  nexus: 'Nexus processors',
  route: 'Routing',
};

const CATEGORY_ORDER = ['sources', 'transform', 'nexus', 'ai', 'route', 'sinks', 'control'] as const;

const CONNECTED_SOURCES_KEY = 'connected-sources';

function sortCategoryKeys(keys: string[]): string[] {
  return [...keys].sort((a, b) => {
    const ia = CATEGORY_ORDER.indexOf(a as (typeof CATEGORY_ORDER)[number]);
    const ib = CATEGORY_ORDER.indexOf(b as (typeof CATEGORY_ORDER)[number]);
    const ra = ia === -1 ? 999 : ia;
    const rb = ib === -1 ? 999 : ib;
    if (ra !== rb) return ra - rb;
    return a.localeCompare(b);
  });
}

const ICON_MAP: Record<string, IconName> = {
  database: 'database',
  shuffle: 'shuffle',
  'file-json': 'file',
  'check-circle': 'check-circle',
  filter: 'filter',
  cube: 'cube',
  layers: 'layers',
  'alert-triangle': 'alert-triangle',
  upload: 'upload',
  folder: 'folder',
  refresh: 'refresh',
  sparkles: 'sparkles',
  'megaphone-or-rss': 'megaphone-or-rss',
};

export default function PipelineStepPalette({
  catalog,
  sourceType,
  dataPlanes,
  onAdd,
}: {
  catalog: CatalogNodeType[];
  sourceType?: string;
  dataPlanes?: DataPlane[];
  onAdd: (type: string, extra?: Record<string, unknown>, label?: string) => void;
}) {
  const [q, setQ] = useState('');
  const query = q.trim().toLowerCase();
  const [expandedCats, setExpandedCats] = useState<Set<string>>(() => new Set());
  const paletteExpandInitialized = useRef(false);

  const byCat = useMemo(() => {
    const acc: Record<string, CatalogNodeType[]> = {};
    for (const item of catalog) {
      if (query && !`${item.label} ${item.description} ${item.type}`.toLowerCase().includes(query)) continue;
      const cat = item.category || 'transform';
      (acc[cat] ??= []).push(item);
    }
    return acc;
  }, [catalog, query]);

  const categoryKeys = useMemo(() => sortCategoryKeys(Object.keys(byCat)), [byCat]);

  useEffect(() => {
    if (paletteExpandInitialized.current) return;
    if (categoryKeys.length === 0 && !(dataPlanes && dataPlanes.length > 0)) return;
    paletteExpandInitialized.current = true;
    const initial = new Set<string>();
    if (categoryKeys[0]) initial.add(categoryKeys[0]);
    if (dataPlanes && dataPlanes.length > 0) initial.add(CONNECTED_SOURCES_KEY);
    setExpandedCats(initial);
  }, [categoryKeys, dataPlanes]);

  const toggleCat = (key: string) => {
    setExpandedCats(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const searchForcesOpen = !!query;

  const renderCategoryHeader = (key: string, label: string, count: number) => {
    const isOpen = searchForcesOpen || expandedCats.has(key);
    return (
      <button
        type="button"
        aria-expanded={isOpen}
        className="flex w-full items-center gap-1.5 rounded-md px-1 py-1.5 text-left text-[11px] font-medium uppercase tracking-wide text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
        onClick={() => toggleCat(key)}
      >
        <Icon name={isOpen ? 'chevron-down' : 'chevron-right'} className="h-3 w-3 shrink-0" />
        <span className="min-w-0 flex-1 truncate">{label}</span>
        <span className="text-[10px] font-normal tabular-nums text-subtle-foreground">{count}</span>
      </button>
    );
  };

  return (
    <aside className="flex h-full min-h-0 flex-col border-r border-border bg-surface-1/80">
      <div className="border-b border-border px-3 py-3">
        <h3 className="text-sm font-medium text-foreground">Add a step</h3>
        <Input
          className="mt-2 h-8"
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Search or describe…"
        />
      </div>
      <div className="scroll-thin flex-1 space-y-3 overflow-y-auto p-3">
        {dataPlanes && dataPlanes.length > 0 && (
          <div>
            {renderCategoryHeader(CONNECTED_SOURCES_KEY, 'Connected sources', dataPlanes.length)}
            {(searchForcesOpen || expandedCats.has(CONNECTED_SOURCES_KEY)) && (
            <ul className="mt-1 space-y-1">
              {dataPlanes.map(dp => (
                <li key={dp.id}>
                  <button
                    type="button"
                    onClick={() => onAdd('source.fdw', { dataPlaneId: dp.id, sourceType: 'generic' }, dp.name)}
                    className="flex w-full items-start gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-surface-2"
                  >
                    <Icon name="database" className="mt-0.5 h-3.5 w-3.5 text-primary" />
                    <span>
                      <span className="block font-medium text-foreground">{dp.name}</span>
                      <span className="block text-xs text-muted-foreground">{dp.type}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            )}
          </div>
        )}
        {categoryKeys.map(cat => {
          const items = byCat[cat] ?? [];
          const isOpen = searchForcesOpen || expandedCats.has(cat);
          return (
          <div key={cat}>
            {renderCategoryHeader(cat, CATEGORY_LABEL[cat] ?? cat, items.length)}
            {isOpen && (
            <ul className="mt-1 space-y-1">
              {items.map(item => {
                const disabled =
                  item.requiresSourceTypes &&
                  sourceType &&
                  !item.requiresSourceTypes.includes(sourceType);
                const stub = item.runtime === 'stub';
                return (
                  <li key={item.type}>
                    <button
                      type="button"
                      disabled={disabled}
                      draggable={!disabled}
                      onDragStart={e => {
                        e.dataTransfer.setData('application/pipeline-node', item.type);
                        e.dataTransfer.effectAllowed = 'move';
                      }}
                      onClick={() => onAdd(item.type)}
                      className={cn(
                        'flex w-full items-start gap-2 rounded-md border border-transparent px-2 py-2 text-left text-sm transition-colors',
                        'hover:border-border hover:bg-surface-2',
                        disabled && 'cursor-not-allowed opacity-40',
                      )}
                    >
                      <Icon name={(ICON_MAP[item.icon] ?? 'database') as IconName} className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                      <span>
                        <span className="block font-medium text-foreground">
                          {item.label}
                          {stub && <span className="ml-1 text-[10px] uppercase text-muted-foreground">Stub</span>}
                        </span>
                        <span className="block text-xs text-muted-foreground line-clamp-2">{item.description}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
            )}
          </div>
        );
        })}
      </div>
    </aside>
  );
}
