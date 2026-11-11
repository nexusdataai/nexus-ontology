/**
 * Data Plane → Entities. Papu's original layout (entity list | schema |
 * relationships and data layer, with the data panel below), drawn in the
 * product theme: Geist type, theme colours and the shared icon set.
 */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import type { ImperativePanelHandle } from 'react-resizable-panels';
import { Icon } from '@/components/ds/Icon';
import { SearchInput } from '@/components/ds/kit';
import { CHART_COLORS } from '@/components/ds/charts';
import { cn } from '@/lib/utils';
import { apiClient } from '@/services/apiClient';
import { fdwService } from '@/services/fdwService';
import { virtualQueryService } from '@/services/virtualQueryService';
import { mappingRuleService, type MappingRule } from '@/services/mappingRuleService';
import type { QueryRequest } from '@/types/fdwTypes';

const FDW_SCHEMA = 'sfdc_itxp2dev';
/** Rows shown in the data panel. */
const ROW_LIMIT = 50;

interface SchemaEntity {
  name: string;
  system: string;
  domain: string;
  semantic: string;
  riskLevel: string;
  isVirtual: boolean;
  fdwMappingStatus: string;
  scorProcess: string;
  fields: { name: string; dataType: string; semantic: string; riskLevel: string; constraints: string[] }[];
  relationships: { type: string; targetEntity: string; targetCategory: string; description: string }[];
}
type PreviewRow = Record<string, unknown>;
interface Preview { rows: PreviewRow[]; metadata?: { rowCount?: number; durationMs?: number } | null }

// Grouping axis for the entity list. Canonical entities are source-agnostic
// (system field is typically empty), so business taxonomy is the useful
// partition: by `domain` or by `scorProcess` (Plan/Source/Make/…).
type GroupAxis = 'domain' | 'scor';
const GROUP_AXIS_LABEL: Record<GroupAxis, string> = { domain: 'Domain', scor: 'SCOR process' };
const GROUP_AXIS_PLURAL: Record<GroupAxis, string> = { domain: 'domains', scor: 'SCOR processes' };

const groupKeyOf = (e: SchemaEntity, axis: GroupAxis): string => {
  const raw = axis === 'domain' ? e.domain : e.scorProcess;
  const v = (raw || '').trim();
  return v || 'Uncategorized';
};

/** A theme colour at low opacity, for tinted badges. */
const tint = (colour: string, a = 0.16) => colour.replace('))', ` / ${a}))`);

const FDW_STATUS_STYLES: Record<string, string> = {
  mapped: 'bg-success/15 text-success',
  virtual: 'bg-warning/15 text-warning',
  unmapped: 'bg-muted text-muted-foreground',
};
const RISK_STYLES: Record<string, string> = {
  high: 'text-destructive',
  medium: 'text-warning',
  low: 'text-success',
};
/** Relationship colours, the same as the knowledge graph. */
const RELATIONSHIP_COLOUR: Record<string, string> = {
  triggers: 'hsl(var(--chart-6))',
  syncs_to: 'hsl(var(--chart-1))',
  depends_on: 'hsl(var(--success))',
  constrained_by: 'hsl(var(--chart-5))',
  owned_by: 'hsl(var(--chart-3))',
  validates: 'hsl(var(--chart-2))',
};
const words = (s: string) => String(s || '').replace(/_/g, ' ');

function Pill({ className, style, children }: { className?: string; style?: React.CSSProperties; children: React.ReactNode }) {
  return (
    <span className={cn('inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium', className)} style={style}>
      {children}
    </span>
  );
}

function Loading({ className }: { className?: string }) {
  return <Icon name="spinner" className={cn('h-4 w-4 animate-spin text-muted-foreground', className)} label="Loading" />;
}

type RightTab = 'relationships' | 'vdl';

export default function EntityExplorer() {
  const [entities, setEntities] = useState<SchemaEntity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<SchemaEntity | null>(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [previewData, setPreviewData] = useState<Preview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [rightTab, setRightTab] = useState<RightTab>('relationships');
  const [entityMappingRules, setEntityMappingRules] = useState<MappingRule[]>([]);
  const [vdlLoading, setVdlLoading] = useState(false);

  const previewGen = useRef(0);
  const bottomPanelRef = useRef<ImperativePanelHandle>(null);
  const [bottomPanelExpanded, setBottomPanelExpanded] = useState(true);

  const [groupAxis, setGroupAxis] = useState<GroupAxis>('domain');
  // The group filter is folded away by default so the entity list is visible straight away.
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set());

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await apiClient.get('/api/v1/control-plane/entities');
        const list = (data as SchemaEntity[]) || [];
        setEntities(list);
        setSelectedGroups(new Set(list.map(e => groupKeyOf(e, 'domain'))));
      } catch {
        setEntities([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Switching the grouping axis selects every group again, so the list is never unexpectedly empty.
  useEffect(() => {
    if (entities.length === 0) return;
    setSelectedGroups(new Set(entities.map(e => groupKeyOf(e, groupAxis))));
  }, [groupAxis, entities]);

  const loadPreview = useCallback(async (entity: SchemaEntity) => {
    const gen = ++previewGen.current;
    setPreviewLoading(true);
    setPreviewData(null);
    try {
      const data = await virtualQueryService.previewEntity(entity.name, ROW_LIMIT);
      if (previewGen.current !== gen) return;
      if (data.rows && data.rows.length > 0) {
        setPreviewData({ rows: data.rows as PreviewRow[], metadata: data.metadata });
        setPreviewLoading(false);
        return;
      }
    } catch {
      // The virtual data layer could not answer; try the FDW table below.
    }

    if (entity.isVirtual) {
      if (previewGen.current === gen) { setPreviewData(null); setPreviewLoading(false); }
      return;
    }

    try {
      const fdwColumns = await fdwService.getColumns(FDW_SCHEMA, entity.name);
      if (previewGen.current !== gen) return;
      const fdwColNames = new Set(fdwColumns.map(c => c.columnName));
      const validCols = entity.fields.map(f => f.name).filter(f => fdwColNames.has(f));
      const queryCols = validCols.length > 0 ? validCols.slice(0, 8) : fdwColumns.slice(0, 8).map(c => c.columnName);
      if (queryCols.length === 0) { setPreviewData(null); return; }
      const req: QueryRequest = { table: entity.name, schemaName: FDW_SCHEMA, columns: queryCols, limit: ROW_LIMIT };
      const result = await fdwService.executeQuery(req);
      if (previewGen.current !== gen) return;
      setPreviewData({ rows: result.rows as PreviewRow[], metadata: result.metadata });
    } catch {
      if (previewGen.current === gen) setPreviewData(null);
    } finally {
      if (previewGen.current === gen) setPreviewLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedEntity) {
      previewGen.current += 1;
      setPreviewData(null);
      setPreviewLoading(false);
      setEntityMappingRules([]);
      setRightTab('relationships');
      return;
    }
    loadPreview(selectedEntity);
  }, [selectedEntity, loadPreview]);

  useEffect(() => {
    if (!selectedEntity || rightTab !== 'vdl') return;
    setVdlLoading(true);
    mappingRuleService
      .list(selectedEntity.name)
      .then(setEntityMappingRules)
      .catch(() => setEntityMappingRules([]))
      .finally(() => setVdlLoading(false));
  }, [selectedEntity, rightTab]);

  const filteredEntities = useMemo(() => entities.filter(e => {
    if (!selectedGroups.has(groupKeyOf(e, groupAxis))) return false;
    if (!searchFilter) return true;
    return e.name.toLowerCase().includes(searchFilter.toLowerCase());
  }), [entities, searchFilter, selectedGroups, groupAxis]);

  const grouped = useMemo(() => filteredEntities.reduce<Record<string, SchemaEntity[]>>((acc, e) => {
    const k = groupKeyOf(e, groupAxis);
    (acc[k] ??= []).push(e);
    return acc;
  }, {}), [filteredEntities, groupAxis]);

  // All groups on the current axis, sorted, so each keeps the same colour.
  const allGroups = useMemo(() => [...new Set(entities.map(e => groupKeyOf(e, groupAxis)))].sort(), [entities, groupAxis]);

  const groupColour = (key: string): string => {
    const idx = allGroups.indexOf(key);
    return CHART_COLORS[(idx >= 0 ? idx : 0) % CHART_COLORS.length];
  };

  const toggleGroup = (key: string) => {
    setSelectedGroups(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const activeRule = entityMappingRules.find(r => r.status === 'active');

  const toggleBottomPanel = () => {
    const p = bottomPanelRef.current;
    if (!p) return;
    if (p.isCollapsed()) p.expand(16);
    else p.collapse();
  };

  const domainPill = (e: SchemaEntity) => e.domain && (
    <Pill style={{ background: tint(groupColour(groupKeyOf(e, 'domain'))), color: groupColour(groupKeyOf(e, 'domain')) }}>{e.domain}</Pill>
  );
  const kindPill = (e: SchemaEntity) => (
    <Pill className={e.isVirtual ? FDW_STATUS_STYLES.virtual : FDW_STATUS_STYLES.mapped}>{e.isVirtual ? 'virtual' : 'mapped'}</Pill>
  );
  const riskPill = (e: SchemaEntity) => (
    <Pill className={cn('border border-border bg-transparent', RISK_STYLES[e.riskLevel] || 'text-muted-foreground')}>
      <Icon name="shield-check" className="h-3 w-3" />
      {e.riskLevel}
    </Pill>
  );

  const tabClass = (on: boolean) => cn(
    'flex flex-1 items-center justify-center gap-1.5 border-b-2 py-2 text-sm transition-colors',
    on ? 'border-brand font-medium text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground',
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ResizablePanelGroup direction="vertical" className="min-h-0 flex-1">
        <ResizablePanel defaultSize={70} minSize={40} className="min-h-0">
          <ResizablePanelGroup direction="horizontal" className="h-full min-h-0 gap-0 px-2 pt-2">
            {/* Left: entity list */}
            <ResizablePanel defaultSize={26} minSize={16} maxSize={40} className="min-h-0 min-w-0">
              <Card className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border">
                <CardHeader className="shrink-0 space-y-0 px-3 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-md font-medium">Entities</CardTitle>
                    <Pill className="num bg-muted text-muted-foreground">{filteredEntities.length}</Pill>
                  </div>
                  <SearchInput value={searchFilter} onChange={setSearchFilter} placeholder="Search entities" className="mt-2.5 sm:w-full" aria-label="Search entities" />
                  {/* Group-by axis */}
                  <div className="mt-2.5 flex flex-wrap items-center gap-1 text-xs">
                    <span className="text-muted-foreground">Group by</span>
                    {(['domain', 'scor'] as GroupAxis[]).map(axis => (
                      <button
                        key={axis}
                        type="button"
                        onClick={() => setGroupAxis(axis)}
                        aria-pressed={groupAxis === axis}
                        className={cn(
                          'rounded-md border px-2 py-0.5 transition-colors',
                          groupAxis === axis ? 'border-brand/60 bg-brand/10 text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground',
                        )}
                      >
                        {GROUP_AXIS_LABEL[axis]}
                      </button>
                    ))}
                  </div>
                  {allGroups.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setFiltersOpen(o => !o)}
                      aria-expanded={filtersOpen}
                      className="mt-2 flex w-full items-center gap-1.5 rounded-md px-1 py-1 text-left text-xs text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
                    >
                      <Icon name="filter" className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">Show {GROUP_AXIS_PLURAL[groupAxis]}</span>
                      <span className={cn('num ml-auto shrink-0', selectedGroups.size < allGroups.length && 'font-medium text-warning')}>
                        {selectedGroups.size < allGroups.length ? `${selectedGroups.size} of ${allGroups.length}` : 'All'}
                      </span>
                      <Icon name={filtersOpen ? 'chevron-up' : 'chevron-down'} className="h-3.5 w-3.5 shrink-0" />
                    </button>
                  )}
                  {allGroups.length > 0 && filtersOpen && (
                    <div className="mt-1 flex max-h-32 flex-wrap gap-1 overflow-y-auto pb-0.5">
                      <button
                        type="button"
                        onClick={() => setSelectedGroups(new Set(selectedGroups.size === allGroups.length ? [] : allGroups))}
                        className="rounded-md border border-dashed border-border px-1.5 py-0.5 text-xs text-muted-foreground hover:text-foreground"
                      >
                        {selectedGroups.size === allGroups.length ? 'None' : 'All'}
                      </button>
                      {allGroups.map(key => (
                        <button
                          key={key}
                          type="button"
                          onClick={() => toggleGroup(key)}
                          aria-pressed={selectedGroups.has(key)}
                          className={cn(
                            'flex items-center gap-1.5 whitespace-nowrap rounded-md border px-1.5 py-0.5 text-xs transition-colors',
                            selectedGroups.has(key) ? 'border-border text-foreground' : 'border-transparent text-muted-foreground/50 hover:text-muted-foreground',
                          )}
                        >
                          <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: groupColour(key) }} />
                          {key}
                        </button>
                      ))}
                    </div>
                  )}
                </CardHeader>
                <CardContent className="flex min-h-0 flex-1 flex-col p-0">
                  <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
                    {loading ? (
                      <div className="flex justify-center p-4"><Loading /></div>
                    ) : (
                      <div className="divide-y divide-border">
                        {Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([groupKey, items]) => (
                          <div key={groupKey}>
                            <div className="flex items-center gap-2 bg-muted/50 px-3 py-1.5">
                              <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: groupColour(groupKey) }} />
                              <span className="truncate text-xs font-medium uppercase tracking-wider text-muted-foreground">{groupKey}</span>
                              <span className="num ml-auto text-xs text-muted-foreground">{items.length}</span>
                            </div>
                            {items.map(entity => {
                              const on = selectedEntity?.name === entity.name;
                              return (
                                <button
                                  key={entity.name}
                                  type="button"
                                  onClick={() => { setSelectedEntity(entity); setRightTab('relationships'); }}
                                  aria-pressed={on}
                                  className={cn(
                                    'w-full border-l-2 px-3 py-2.5 text-left transition-colors hover:bg-muted/50',
                                    on ? 'border-brand bg-brand/10' : 'border-transparent',
                                  )}
                                >
                                  <div className="flex items-center justify-between gap-1.5">
                                    <span className="truncate text-sm font-medium text-foreground">{entity.name}</span>
                                    <Pill className={FDW_STATUS_STYLES[entity.fdwMappingStatus] || FDW_STATUS_STYLES.unmapped}>{entity.fdwMappingStatus}</Pill>
                                  </div>
                                  <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                    <span className="flex items-center gap-1"><Icon name="table" className="h-3 w-3" /><span className="num">{entity.fields.length}</span> fields</span>
                                    <span className={RISK_STYLES[entity.riskLevel] || 'text-muted-foreground'}>{entity.riskLevel}</span>
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        ))}
                        {filteredEntities.length === 0 && (
                          <div className="p-4 text-center text-sm text-muted-foreground">
                            {entities.length === 0 ? 'No entities loaded' : 'No matches'}
                            {entities.length > 0 && selectedGroups.size < allGroups.length && (
                              <button type="button" onClick={() => setSelectedGroups(new Set(allGroups))} className="mt-1 block w-full text-xs text-primary underline dark:text-brand-hi">Show all {GROUP_AXIS_PLURAL[groupAxis]}</button>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </ResizablePanel>

            <ResizableHandle withHandle className="mx-1" />

            {/* Centre: schema */}
            <ResizablePanel defaultSize={46} minSize={28} className="min-h-0 min-w-0">
              <Card className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border">
                {selectedEntity ? (
                  <>
                    <CardHeader className="shrink-0 space-y-0 border-b bg-muted/20 px-4 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-md font-semibold text-foreground">{selectedEntity.name}</h2>
                        {domainPill(selectedEntity)}
                        {selectedEntity.scorProcess && <Pill className="bg-info/15 text-info">SCOR: {selectedEntity.scorProcess}</Pill>}
                        {riskPill(selectedEntity)}
                        {kindPill(selectedEntity)}
                      </div>
                      {selectedEntity.semantic && <p className="mt-1.5 line-clamp-2 text-sm text-muted-foreground">{selectedEntity.semantic}</p>}
                    </CardHeader>
                    <CardContent className="flex min-h-0 flex-1 flex-col p-0">
                      <div className="flex shrink-0 items-center gap-2 border-b bg-muted/30 px-4 py-2 text-sm font-medium text-foreground">
                        <Icon name="table" className="h-4 w-4 text-muted-foreground" />
                        Schema fields <span className="num text-muted-foreground">({selectedEntity.fields.length})</span>
                      </div>
                      <div className="min-h-0 flex-1 overflow-auto">
                        <div className="p-2">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b text-xs text-muted-foreground">
                                <th className="px-2 py-2 text-left font-medium">Field name</th>
                                <th className="px-2 py-2 text-left font-medium">Data type</th>
                                <th className="px-2 py-2 text-left font-medium">Meaning</th>
                                <th className="px-2 py-2 text-left font-medium">Risk</th>
                                <th className="px-2 py-2 text-left font-medium">Constraints</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                              {selectedEntity.fields.map(field => (
                                <tr key={field.name} className="transition-colors hover:bg-muted/30">
                                  <td className="px-2 py-2 font-mono text-foreground">{field.name}</td>
                                  <td className="px-2 py-2"><Pill className="bg-muted font-mono text-muted-foreground">{field.dataType}</Pill></td>
                                  <td className="px-2 py-2 text-muted-foreground">{field.semantic}</td>
                                  <td className="px-2 py-2"><span className={RISK_STYLES[field.riskLevel] || 'text-muted-foreground'}>{field.riskLevel}</span></td>
                                  <td className="px-2 py-2 text-xs text-muted-foreground">{field.constraints.length > 0 ? field.constraints.join(', ') : <span className="text-muted-foreground/50">—</span>}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </CardContent>
                  </>
                ) : (
                  <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
                    <div className="text-center">
                      <Icon name="database" className="mx-auto mb-2 h-8 w-8 opacity-40" />
                      <p>Select an entity to view its schema</p>
                    </div>
                  </div>
                )}
              </Card>
            </ResizablePanel>

            <ResizableHandle withHandle className="mx-1" />

            {/* Right: Relationships | Data layer */}
            <ResizablePanel defaultSize={28} minSize={18} maxSize={42} className="min-h-0 min-w-0">
              {selectedEntity ? (
                <Card className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border">
                  <div className="flex shrink-0 items-center gap-2 border-b bg-card px-3 py-2">
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: selectedEntity.domain ? groupColour(groupKeyOf(selectedEntity, groupAxis)) : 'hsl(var(--muted-foreground))' }} />
                    <span className="flex-1 truncate text-sm font-medium text-foreground">{selectedEntity.name}</span>
                    <Button variant="ghost" size="sm" className="h-7 w-7 shrink-0 p-0" onClick={() => setSelectedEntity(null)} aria-label="Clear selection">
                      <Icon name="close" className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                  <div className="flex shrink-0 border-b" role="tablist">
                    <button type="button" role="tab" aria-selected={rightTab === 'relationships'} onClick={() => setRightTab('relationships')} className={tabClass(rightTab === 'relationships')}>
                      <Icon name="link" className="h-3.5 w-3.5" /> Relationships
                    </button>
                    <button type="button" role="tab" aria-selected={rightTab === 'vdl'} onClick={() => setRightTab('vdl')} className={tabClass(rightTab === 'vdl')}>
                      <Icon name="layers" className="h-3.5 w-3.5" /> Data layer
                    </button>
                  </div>
                  <CardContent className="flex min-h-0 flex-1 flex-col p-0">
                    <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
                      <div className="space-y-3 px-3 py-3 pb-4">
                        <div className="flex flex-wrap gap-1">
                          {domainPill(selectedEntity)}
                          {kindPill(selectedEntity)}
                          {riskPill(selectedEntity)}
                        </div>

                        {rightTab === 'relationships' && (
                          <>
                            <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                              <Icon name="table" className="h-3.5 w-3.5" /> <span className="num">{selectedEntity.fields.length}</span> fields
                            </div>
                            {selectedEntity.relationships.length > 0 ? (
                              <div className="space-y-1.5">
                                <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                                  <Icon name="link" className="h-3.5 w-3.5" /> <span className="num">{selectedEntity.relationships.length}</span> relationships
                                </div>
                                {selectedEntity.relationships.map((rel, i) => {
                                  const c = RELATIONSHIP_COLOUR[rel.type] || 'hsl(var(--muted-foreground))';
                                  return (
                                    <div key={i} className="flex flex-col gap-1 rounded-lg border border-border bg-muted/30 p-2.5 text-sm">
                                      <div className="flex flex-wrap items-center gap-1.5">
                                        <Pill style={{ background: tint(c), color: c }}>{words(rel.type)}</Pill>
                                        <Icon name="chevron-right" className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                                        <span className="truncate font-medium text-foreground">{rel.targetEntity}</span>
                                      </div>
                                      {rel.targetCategory && <Pill className="w-fit bg-muted text-muted-foreground">{rel.targetCategory}</Pill>}
                                      {rel.description && <p className="text-xs leading-snug text-muted-foreground">{rel.description}</p>}
                                    </div>
                                  );
                                })}
                              </div>
                            ) : (
                              <p className="text-sm text-muted-foreground">No relationships defined.</p>
                            )}
                          </>
                        )}

                        {rightTab === 'vdl' && (
                          vdlLoading ? (
                            <div className="flex justify-center py-4"><Loading /></div>
                          ) : (
                            <>
                              <div>
                                <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                                  <Icon name="database" className="h-3.5 w-3.5" /> Mapping rule
                                </div>
                                {activeRule ? (
                                  <div className="space-y-1 rounded-lg bg-muted/30 p-2.5 text-sm">
                                    <div className="flex items-center gap-1.5">
                                      <Pill className="bg-success/15 text-success">active</Pill>
                                      <span className="truncate font-medium text-foreground">{activeRule.name}</span>
                                    </div>
                                    <div className="font-mono text-xs text-muted-foreground">{activeRule.sourceSchema}.{activeRule.sourceTable}</div>
                                    <div className="text-xs text-muted-foreground"><span className="num">{activeRule.fieldMaps.length}</span> field mappings · {activeRule.sourceType}</div>
                                  </div>
                                ) : (
                                  <div className="rounded-lg bg-muted/20 p-2.5 text-sm text-muted-foreground">No active mapping rule for this entity.</div>
                                )}
                              </div>

                              {selectedEntity.scorProcess && (
                                <div>
                                  <div className="mb-1.5 text-xs font-medium text-muted-foreground">SCOR process</div>
                                  <Pill className="bg-info/15 text-info">{selectedEntity.scorProcess}</Pill>
                                </div>
                              )}

                              <div>
                                <div className="mb-1.5 text-xs font-medium text-muted-foreground">FDW mapping</div>
                                {selectedEntity.isVirtual ? (
                                  <div className="flex items-start gap-2 rounded-lg bg-warning/10 px-2.5 py-2 text-sm">
                                    <Icon name="alert-triangle" className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                                    <span className="text-foreground">Virtual entity, no direct FDW table. Its data comes through the virtual data layer.</span>
                                  </div>
                                ) : (
                                  <div className="flex flex-col gap-1 text-sm">
                                    <span className="text-xs text-muted-foreground">FDW table</span>
                                    <span className="break-all font-mono text-foreground">{FDW_SCHEMA}.{selectedEntity.name}</span>
                                    <Pill className={cn('w-fit', FDW_STATUS_STYLES[selectedEntity.fdwMappingStatus] || FDW_STATUS_STYLES.unmapped)}>{selectedEntity.fdwMappingStatus}</Pill>
                                  </div>
                                )}
                              </div>

                              <Button variant="outline" size="sm" className="w-full" onClick={() => loadPreview(selectedEntity)} disabled={previewLoading}>
                                <Icon name={previewLoading ? 'spinner' : 'refresh'} className={cn('h-3.5 w-3.5', previewLoading && 'animate-spin')} />
                                Refresh data
                              </Button>
                            </>
                          )
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card className="flex h-full min-h-0 items-center justify-center rounded-xl border border-dashed bg-muted/10">
                  <p className="px-3 text-center text-sm text-muted-foreground">Select an entity for relationships and data layer</p>
                </Card>
              )}
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Bottom: data */}
        <ResizablePanel
          ref={bottomPanelRef}
          defaultSize={30}
          minSize={10}
          maxSize={60}
          collapsible
          collapsedSize={5}
          className="min-h-0"
          onCollapse={() => setBottomPanelExpanded(false)}
          onExpand={() => setBottomPanelExpanded(true)}
        >
          <div className="mx-2 mb-2 flex h-[calc(100%-0.5rem)] min-h-0 flex-col overflow-hidden rounded-xl border bg-card">
            <div className="flex w-full shrink-0 items-center gap-2 border-b bg-muted/30 px-3 py-2">
              <button type="button" onClick={toggleBottomPanel} className="flex min-w-0 flex-1 items-center gap-2 text-left" aria-expanded={bottomPanelExpanded}>
                <Icon name="eye" className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate text-sm font-medium text-foreground">{selectedEntity ? `Data: ${selectedEntity.name}` : 'Data'}</span>
                {previewLoading && <Loading className="h-3.5 w-3.5 text-brand" />}
                {!previewLoading && previewData && selectedEntity && (
                  <span className="hidden truncate text-xs text-muted-foreground sm:inline">
                    <span className="num">{previewData.metadata?.rowCount ?? previewData.rows.length}</span> rows
                    {previewData.metadata?.durationMs != null && <> · <span className="num">{previewData.metadata.durationMs}</span> ms</>}
                  </span>
                )}
                <span className="flex-1" />
                <Icon name={bottomPanelExpanded ? 'chevron-down' : 'chevron-up'} className="h-4 w-4 shrink-0 text-muted-foreground" />
              </button>
              <Button variant="ghost" size="sm" className="h-7 w-7 shrink-0 p-0" onClick={() => selectedEntity && loadPreview(selectedEntity)} disabled={!selectedEntity || previewLoading} aria-label="Refresh data">
                <Icon name="refresh" className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="min-h-0 flex-1 overflow-auto">
              {!selectedEntity ? (
                <div className="flex h-full items-center justify-center px-3 py-4 text-sm text-muted-foreground">Select an entity to see its rows here.</div>
              ) : previewLoading && !previewData ? (
                <div className="flex h-full min-h-[80px] items-center justify-center"><Loading /></div>
              ) : previewData && previewData.rows.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="sticky top-0 z-10 bg-card">
                      {Object.keys(previewData.rows[0]).map(col => (
                        <th key={col} className="whitespace-nowrap border-b px-3 py-2 text-left text-xs font-medium text-muted-foreground">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {previewData.rows.map((row, i) => (
                      <tr key={i} className="hover:bg-muted/30">
                        {Object.values(row).map((val, j) => (
                          <td key={j} className="max-w-[240px] truncate whitespace-nowrap px-3 py-1.5 font-mono text-foreground">{val == null ? '' : String(val)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex h-full min-h-[80px] flex-col items-center justify-center gap-1 px-4 py-3 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Icon name="alert-triangle" className="h-4 w-4 shrink-0 text-warning" />
                    <span>{selectedEntity.isVirtual ? 'No rows returned for this virtual entity.' : 'The FDW query returned no rows, or its columns could not be resolved.'}</span>
                  </div>
                  <p className="max-w-md text-center text-xs">Check the Data Plane connection, the mapping rules, and that the FDW table exists for mapped entities.</p>
                </div>
              )}
            </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
