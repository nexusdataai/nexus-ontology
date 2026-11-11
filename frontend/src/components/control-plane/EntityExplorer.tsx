import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import {
  DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { InlineError, KeyValues, SearchInput, StatusPill, SubHeading, TableShell } from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
import { apiClient } from '@/services/apiClient';
import { fdwService } from '@/services/fdwService';
import { virtualQueryService } from '@/services/virtualQueryService';
import { mappingRuleService, type MappingRule } from '@/services/mappingRuleService';
import type { QueryRequest } from '@/types/fdwTypes';

const FDW_SCHEMA = 'sfdc_itxp2dev';
/** Rows read for the Data tab. */
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

// Grouping axis for the entity list. Canonical entities are source-agnostic
// (system field is typically empty), so business taxonomy is the useful
// partition: by `domain` (15+ today) or by `scorProcess` (Plan/Source/Make/…).
type GroupAxis = 'domain' | 'scor';

const GROUP_AXIS_LABEL: Record<GroupAxis, string> = {
  domain: 'Domain',
  scor: 'SCOR process',
};
const GROUP_AXIS_PLURAL: Record<GroupAxis, string> = {
  domain: 'domains',
  scor: 'processes',
};

const groupKeyOf = (e: SchemaEntity, axis: GroupAxis): string => {
  const raw = axis === 'domain' ? e.domain : e.scorProcess;
  const v = (raw || '').trim();
  return v || 'Uncategorized';
};

const RELATION_LABEL: Record<string, string> = {
  triggers: 'Triggers',
  syncs_to: 'Syncs to',
  depends_on: 'Depends on',
  constrained_by: 'Constrained by',
};

const humanize = (s: string): string => {
  const t = String(s || '').replace(/[_-]+/g, ' ').trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : '';
};

const mappingStatusOf = (e: SchemaEntity): string =>
  e.fdwMappingStatus || (e.isVirtual ? 'virtual' : 'unmapped');

// Data first: the entity's real rows are what people come here to see.
type RightTab = 'data' | 'fields' | 'relationships' | 'source';
type MappingFilter = 'all' | 'mapped' | 'virtual' | 'unmapped';

export default function EntityExplorer() {
  const [entities, setEntities] = useState<SchemaEntity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<SchemaEntity | null>(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<{ rows: any[]; metadata: any } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [rightTab, setRightTab] = useState<RightTab>('data');
  // Domain filter for the list (one control instead of group / domain / mapping).
  const [domainFilter, setDomainFilter] = useState<string>('all');
  // Quick filter over the rows on screen.
  const [rowFilter, setRowFilter] = useState('');
  const [entityMappingRules, setEntityMappingRules] = useState<MappingRule[]>([]);
  const [vdlLoading, setVdlLoading] = useState(false);
  const [vdlError, setVdlError] = useState<string | null>(null);

  const previewGen = useRef(0);

  const [groupAxis, setGroupAxis] = useState<GroupAxis>('domain');
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set());
  // Presentation only: mapping-status filter and the small-screen list sheet.
  const [mappingFilter, setMappingFilter] = useState<MappingFilter>('all');
  const [browseOpen, setBrowseOpen] = useState(false);

  const loadEntities = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await apiClient.get('/api/v1/control-plane/entities');
      const list = (data as SchemaEntity[]) || [];
      setEntities(list);
      // Default: all groups on the current axis are selected. Re-seed when
      // the axis changes below.
      setSelectedGroups(new Set(list.map(e => groupKeyOf(e, 'domain'))));
    } catch (e) {
      setEntities([]);
      setLoadError(e instanceof Error && e.message ? e.message : 'The entity catalogue could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadEntities(); }, [loadEntities]);

  // When the user switches grouping axis, reset the filter to "all groups
  // selected" so they don't end up with an unexpected empty list.
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
        setPreviewData({ rows: data.rows, metadata: data.metadata });
        // Without this the header kept saying "Loading rows" next to the rows.
        setPreviewLoading(false);
        return;
      }
    } catch {
      // VDL preview failed, fall through to FDW if not virtual
    }

    if (entity.isVirtual) {
      if (previewGen.current === gen) setPreviewData(null);
      if (previewGen.current === gen) setPreviewLoading(false);
      return;
    }

    try {
      const fdwColumns = await fdwService.getColumns(FDW_SCHEMA, entity.name);
      if (previewGen.current !== gen) return;
      const fdwColNames = new Set(fdwColumns.map(c => c.columnName));
      const schemaFieldNames = entity.fields.map(f => f.name);
      const validCols = schemaFieldNames.filter(f => fdwColNames.has(f));
      const queryCols =
        validCols.length > 0
          ? validCols.slice(0, 8)
          : fdwColumns.slice(0, 8).map(c => c.columnName);
      if (queryCols.length === 0) {
        if (previewGen.current !== gen) return;
        setPreviewData(null);
        return;
      }
      const req: QueryRequest = {
        table: entity.name,
        schemaName: FDW_SCHEMA,
        columns: queryCols,
        limit: ROW_LIMIT,
      };
      const result = await fdwService.executeQuery(req);
      if (previewGen.current !== gen) return;
      setPreviewData({ rows: result.rows, metadata: result.metadata });
    } catch {
      if (previewGen.current !== gen) return;
      setPreviewData(null);
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
      return;
    }
    setRowFilter('');
    loadPreview(selectedEntity);
  }, [selectedEntity, loadPreview]);

  useEffect(() => {
    if (!selectedEntity) return;
    setVdlLoading(true);
    setVdlError(null);
    mappingRuleService
      .list(selectedEntity.name)
      .then(setEntityMappingRules)
      .catch((e) => {
        setEntityMappingRules([]);
        setVdlError(e instanceof Error && e.message ? e.message : 'Mapping rules could not be loaded.');
      })
      .finally(() => setVdlLoading(false));
  }, [selectedEntity?.name]);

  const filteredEntities = useMemo(() => {
    const q = searchFilter.trim().toLowerCase();
    return entities.filter(e => {
      if (domainFilter !== 'all' && groupKeyOf(e, 'domain') !== domainFilter) return false;
      if (!q) return true;
      return e.name.toLowerCase().includes(q) || (e.semantic || '').toLowerCase().includes(q);
    });
  }, [entities, searchFilter, domainFilter]);

  const grouped = useMemo(() => {
    return filteredEntities.reduce<Record<string, SchemaEntity[]>>((acc, e) => {
      const k = groupKeyOf(e, 'domain');
      (acc[k] ??= []).push(e);
      return acc;
    }, {});
  }, [filteredEntities]);

  const sortedGroups = useMemo(
    () => Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)),
    [grouped],
  );

  // Stable, sorted list of all groups on the current axis (the filter menu).
  const allGroups = useMemo(() => {
    const s = new Set(entities.map(e => groupKeyOf(e, 'domain')));
    return [...s].sort();
  }, [entities]);

  const toggleGroup = (key: string) => {
    setSelectedGroups(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // The detail is never blank: show the first entity of the list after load.
  useEffect(() => {
    if (selectedEntity || sortedGroups.length === 0) return;
    setSelectedEntity(sortedGroups[0][1][0]);
  }, [selectedEntity, sortedGroups]);

  const activeRule = entityMappingRules.find(r => r.status === 'active');

  const selectEntity = (entity: SchemaEntity) => {
    setSelectedEntity(entity);
    setBrowseOpen(false);
  };

  const selectedGroupCount = allGroups.filter(g => selectedGroups.has(g)).length;
  const allGroupsOn = selectedGroupCount === allGroups.length;

  /* ------------------------------------------------------------- the list */

  const list = (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 space-y-2.5 border-b border-border p-3">
        <SearchInput value={searchFilter} onChange={setSearchFilter} placeholder="Search entities" className="sm:w-full" />
        <Select value={domainFilter} onValueChange={setDomainFilter}>
          <SelectTrigger className="h-9" aria-label="Business domain"><SelectValue /></SelectTrigger>
          <SelectContent className="max-h-80">
            <SelectItem value="all">All domains</SelectItem>
            {allGroups.map(g => <SelectItem key={g} value={g}>{g}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <div className="space-y-3 p-3" aria-busy="true">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-4 w-3/5" />
                <Skeleton className="h-3 w-2/5" />
              </div>
            ))}
          </div>
        ) : loadError ? (
          <div className="p-3"><InlineError onRetry={loadEntities}>{loadError}</InlineError></div>
        ) : filteredEntities.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-muted-foreground">
            {entities.length === 0 ? 'No entities in the catalogue yet.' : 'No entities match these filters.'}
          </p>
        ) : (
          <div className="pb-3">
            {sortedGroups.map(([groupKey, items], gi) => (
              <section key={groupKey} className="rise" style={{ '--i': Math.min(gi, 8) } as React.CSSProperties}>
                <h3 className="eyebrow flex items-center justify-between gap-2 px-4 pb-1.5 pt-4">
                  <span className="truncate">{groupKey}</span>
                  <span className="num font-normal text-subtle-foreground">{items.length}</span>
                </h3>
                <ul className="px-2">
                  {items.map(entity => {
                    const on = selectedEntity?.name === entity.name;
                    return (
                      <li key={entity.name}>
                        <button
                          type="button"
                          onClick={() => selectEntity(entity)}
                          aria-current={on ? 'true' : undefined}
                          className={cn(
                            'flex w-full items-start gap-2.5 rounded-md px-2 py-2 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                            on ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground',
                          )}
                        >
                          {entity.system && <SystemLogo system={entity.system} size="xs" className="mt-0.5" />}
                          <span className="min-w-0 flex-1">
                            <span className={cn('block truncate text-sm text-foreground', on && 'font-medium')}>{entity.name}</span>
                            <span className="mt-0.5 block text-xs text-muted-foreground">
                              <span className="num">{entity.fields.length}</span> fields
                            </span>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </div>
        )}
      </div>

      {!loading && !loadError && entities.length > 0 && (
        <div className="shrink-0 border-t border-border px-4 py-2 text-xs text-muted-foreground">
          <span className="num">{filteredEntities.length}</span> of <span className="num">{entities.length}</span> entities
        </div>
      )}
    </div>
  );

  /* ----------------------------------------------------------- the detail */

  const entity = selectedEntity;
  const relationGroups = entity
    ? entity.relationships.reduce<Record<string, SchemaEntity['relationships']>>((acc, r) => {
        (acc[r.type || 'related'] ??= []).push(r);
        return acc;
      }, {})
    : {};
  const previewCols = previewData && previewData.rows.length > 0 ? Object.keys(previewData.rows[0]) : [];
  const rowQuery = rowFilter.trim().toLowerCase();
  const visibleRows = (previewData?.rows || [])
    .map((row, index) => ({ row, index }))
    .filter(({ row }) => !rowQuery || Object.values(row).some(v => v != null && String(typeof v === 'object' ? JSON.stringify(v) : v).toLowerCase().includes(rowQuery)));

  return (
    <div className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)] lg:grid-cols-[300px_minmax(0,1fr)]">
      <aside className="hidden min-h-0 border-r border-border bg-sidebar/40 lg:block" aria-label="Entities">{list}</aside>

      <Sheet open={browseOpen} onOpenChange={setBrowseOpen}>
        <SheetContent side="left" className="flex w-full flex-col gap-0 p-0 sm:max-w-sm">
          <div className="border-b border-border px-4 pb-3 pt-4 pr-12">
            <SheetTitle className="text-md font-medium">Entities</SheetTitle>
            <SheetDescription className="sr-only">Choose a virtual entity</SheetDescription>
          </div>
          <div className="min-h-0 flex-1">{list}</div>
        </SheetContent>
      </Sheet>

      <div className="flex min-h-0 min-w-0 flex-col">
        <div className="shrink-0 border-b border-border px-4 py-2 lg:hidden">
          <Button variant="outline" size="sm" className="w-full justify-between" onClick={() => setBrowseOpen(true)}>
            <span className="flex min-w-0 items-center gap-2">
              <Icon name="list" className="h-3.5 w-3.5" />
              <span className="truncate">{entity ? entity.name : 'Browse entities'}</span>
            </span>
            <span className="flex items-center gap-1.5 font-normal text-muted-foreground">
              <span className="num">{filteredEntities.length}</span>
              <Icon name="chevron-down" className="h-3.5 w-3.5" />
            </span>
          </Button>
        </div>

        {loading ? (
          <div className="space-y-4 p-5 sm:p-6" aria-busy="true">
            <Skeleton className="h-7 w-56" />
            <Skeleton className="h-4 w-80 max-w-full" />
            <Skeleton className="h-10 w-full" />
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
          </div>
        ) : loadError ? (
          <div className="p-5 sm:p-6"><InlineError onRetry={loadEntities}>{loadError}</InlineError></div>
        ) : !entity ? (
          <div className="p-5 sm:p-6">
            <EmptyState
              icon="cube"
              title={entities.length === 0 ? 'No virtual entities yet' : 'No entities match these filters'}
              description={entities.length === 0
                ? 'Entities appear here once source systems are modelled in the virtual data layer.'
                : 'Change the search or the domain to see entities again.'}
            />
          </div>
        ) : (
          <Tabs value={rightTab} onValueChange={(v) => setRightTab(v as RightTab)} className="flex min-h-0 flex-1 flex-col">
            <header className="shrink-0 px-4 pt-5 sm:px-6">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <h2 className="min-w-0 break-words text-xl font-medium tracking-tight text-foreground sm:text-2xl">{entity.name}</h2>
                <span className="text-sm text-muted-foreground">{entity.domain || 'No domain'}</span>
              </div>
              {entity.semantic && <p className="mt-1 line-clamp-2 max-w-3xl text-sm text-muted-foreground">{entity.semantic}</p>}
              <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
                {activeRule ? (
                  <span className="inline-flex min-w-0 items-center gap-1.5">
                    <SystemLogo system={activeRule.sourceSystem} size="sm" />
                    <span>From <span className="text-foreground">{systemName(activeRule.sourceSystem)}</span></span>
                    <span className="truncate font-mono text-xs text-subtle-foreground">{activeRule.sourceSchema}.{activeRule.sourceTable}</span>
                  </span>
                ) : vdlLoading ? (
                  <Skeleton className="h-4 w-48" />
                ) : (
                  <span>{entity.isVirtual ? 'Virtual entity' : 'No active source table'}</span>
                )}
                <span aria-hidden="true">·</span>
                <span><span className="num">{entity.fields.length}</span> fields</span>
                {entity.riskLevel && (
                  <>
                    <span aria-hidden="true">·</span>
                    <StatusPill status={entity.riskLevel}>{humanize(entity.riskLevel)} risk</StatusPill>
                  </>
                )}
              </p>

              <TabsList variant="line" className="mt-4">
                <TabsTrigger value="data">Data</TabsTrigger>
                <TabsTrigger value="fields">Fields <span className="num text-xs font-normal text-subtle-foreground">{entity.fields.length}</span></TabsTrigger>
                <TabsTrigger value="relationships">Relationships <span className="num text-xs font-normal text-subtle-foreground">{entity.relationships.length}</span></TabsTrigger>
                <TabsTrigger value="source">Source</TabsTrigger>
              </TabsList>
            </header>

            <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
              {/* Fields */}
              <TabsContent value="fields" className="mt-0">
                {entity.fields.length === 0 ? (
                  <EmptyState icon="table" title="No fields defined" description="This entity has no schema fields yet." />
                ) : (
                  <TableShell>
                    <Table className="min-w-[640px]">
                      <TableHeader>
                        <TableRow className="hover:bg-transparent">
                          <TableHead>Field</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Meaning</TableHead>
                          <TableHead>Risk</TableHead>
                          <TableHead>Constraints</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {entity.fields.map(field => (
                          <TableRow key={field.name}>
                            <TableCell className="py-2.5 font-mono text-xs text-foreground">{field.name}</TableCell>
                            <TableCell className="py-2.5 font-mono text-xs text-muted-foreground">{field.dataType}</TableCell>
                            <TableCell className="py-2.5 text-sm text-muted-foreground">{field.semantic || '—'}</TableCell>
                            <TableCell className="py-2.5">
                              {field.riskLevel ? <StatusPill status={field.riskLevel} className="font-normal" /> : <span className="text-subtle-foreground">—</span>}
                            </TableCell>
                            <TableCell className="py-2.5 text-xs text-muted-foreground">
                              {field.constraints && field.constraints.length > 0
                                ? field.constraints.map((c, i) => <div key={i}>{c}</div>)
                                : <span className="text-subtle-foreground">—</span>}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableShell>
                )}
              </TabsContent>

              {/* Relationships */}
              <TabsContent value="relationships" className="mt-0">
                {entity.relationships.length === 0 ? (
                  <EmptyState icon="network" title="No relationships defined" description="This entity is not linked to other entities yet." />
                ) : (
                  <div className="max-w-3xl space-y-7">
                    {Object.entries(relationGroups).map(([type, rels]) => (
                      <section key={type}>
                        <SubHeading action={<span className="num text-xs text-muted-foreground">{rels.length}</span>}>
                          {RELATION_LABEL[type] || humanize(type)}
                        </SubHeading>
                        <ul className="border-t border-border">
                          {rels.map((rel, i) => {
                            const target = entities.find(e => e.name === rel.targetEntity);
                            return (
                              <li key={`${rel.targetEntity}-${i}`} className="flex items-start gap-3 border-b border-border py-2.5">
                                <Icon name="arrow-right" className="mt-1 h-3.5 w-3.5 shrink-0 text-subtle-foreground" />
                                <div className="min-w-0 flex-1">
                                  <div className="flex flex-wrap items-baseline gap-x-2">
                                    {target ? (
                                      <button
                                        type="button"
                                        onClick={() => selectEntity(target)}
                                        className="rounded-sm text-sm font-medium text-foreground underline-offset-4 hover:text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:hover:text-brand-hi"
                                      >
                                        {rel.targetEntity}
                                      </button>
                                    ) : (
                                      <span className="text-sm font-medium text-foreground">{rel.targetEntity}</span>
                                    )}
                                    {rel.targetCategory && <span className="text-xs text-muted-foreground">{humanize(rel.targetCategory)}</span>}
                                  </div>
                                  {rel.description && <p className="mt-0.5 text-sm text-muted-foreground">{rel.description}</p>}
                                </div>
                              </li>
                            );
                          })}
                        </ul>
                      </section>
                    ))}
                  </div>
                )}
              </TabsContent>

              {/* Data layer */}
              <TabsContent value="source" className="mt-0">
                {vdlLoading ? (
                  <div className="max-w-3xl space-y-2.5" aria-busy="true">
                    {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
                  </div>
                ) : (
                  <div className="max-w-3xl space-y-7">
                    {vdlError && <InlineError>{vdlError}</InlineError>}
                    <section>
                      <SubHeading>Mapping</SubHeading>
                      <KeyValues
                        className="border-t border-border"
                        items={[
                          { label: 'Active mapping rule', value: activeRule ? activeRule.name : 'None' },
                          ...(activeRule ? [
                            { label: 'Source table', value: `${activeRule.sourceSchema}.${activeRule.sourceTable}`, mono: true },
                            { label: 'Source type', value: activeRule.sourceType },
                            { label: 'Field mappings', value: <span className="num">{activeRule.fieldMaps.length}</span> },
                          ] : []),
                          entity.isVirtual
                            ? { label: 'FDW table', value: 'None (virtual entity)' }
                            : { label: 'FDW table', value: `${FDW_SCHEMA}.${entity.name}`, mono: true },
                          { label: 'Mapping status', value: <StatusPill status={mappingStatusOf(entity)} /> },
                          ...(entity.scorProcess ? [{ label: 'SCOR process', value: entity.scorProcess }] : []),
                        ]}
                      />
                      {entity.isVirtual && (
                        <p className="mt-3 text-sm text-muted-foreground">
                          This is a virtual entity with no direct FDW table. Its data is read through the virtual query path.
                        </p>
                      )}
                      {!activeRule && !vdlError && (
                        <p className="mt-3 text-sm text-muted-foreground">No active mapping rule for this entity.</p>
                      )}
                    </section>

                    {activeRule && activeRule.fieldMaps.length > 0 && (
                      <section>
                        <SubHeading>Field map</SubHeading>
                        <TableShell>
                          <Table>
                            <TableHeader>
                              <TableRow className="hover:bg-transparent">
                                <TableHead>Source field</TableHead>
                                <TableHead className="w-8 px-0" />
                                <TableHead>Entity field</TableHead>
                                <TableHead>Transform</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {activeRule.fieldMaps.map((fm, i) => (
                                <TableRow key={i}>
                                  <TableCell className="py-2 font-mono text-xs text-muted-foreground">{fm.sourceField || '—'}</TableCell>
                                  <TableCell className="px-0 py-2"><Icon name="arrow-right" className="h-3.5 w-3.5 text-subtle-foreground" /></TableCell>
                                  <TableCell className="py-2 font-mono text-xs text-foreground">{fm.targetField || '—'}</TableCell>
                                  <TableCell className="py-2 text-xs text-muted-foreground">{fm.transform && fm.transform !== 'none' ? fm.transform : '—'}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableShell>
                      </section>
                    )}
                  </div>
                )}
              </TabsContent>

              {/* Data: the entity's rows, read live from its source */}
              <TabsContent value="data" className="mt-0">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-muted-foreground" aria-live="polite">
                    {previewLoading && !previewData ? 'Reading rows…' : previewData && previewData.rows.length > 0 ? (
                      <>
                        {visibleRows.length !== previewData.rows.length && <><span className="num font-medium text-foreground">{visibleRows.length}</span> of </>}
                        <span className="num font-medium text-foreground">{previewData.rows.length}</span> rows
                        {previewData.rows.length >= ROW_LIMIT && <> (first {ROW_LIMIT})</>}
                        {previewData.metadata?.durationMs != null && <> · read in <span className="num">{previewData.metadata.durationMs}</span> ms</>}
                      </>
                    ) : 'No rows'}
                  </p>
                  <div className="flex items-center gap-2">
                    {previewData && previewData.rows.length > 0 && (
                      <SearchInput value={rowFilter} onChange={setRowFilter} placeholder="Find in these rows" className="w-52 sm:w-64" />
                    )}
                    <Button variant="outline" size="sm" onClick={() => loadPreview(entity)} disabled={previewLoading}>
                      <Icon name="refresh" className={previewLoading ? 'animate-spin' : undefined} /> Refresh
                    </Button>
                  </div>
                </div>
                {previewLoading && !previewData ? (
                  <div className="space-y-2" aria-busy="true">
                    {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
                  </div>
                ) : previewData && previewData.rows.length > 0 ? (
                  <TableShell className="max-h-[calc(100vh-330px)] min-h-[320px] overflow-auto">
                    {/* Plain table: the shared Table wraps itself in a scroll box, which stops the header from sticking. */}
                    <table className="w-full caption-bottom text-sm">
                      <TableHeader className="sticky top-0 z-10 bg-card">
                        <TableRow className="hover:bg-transparent">
                          <TableHead className="w-12 text-right text-subtle-foreground">#</TableHead>
                          {previewCols.map(col => (
                            <TableHead key={col} className={cn('whitespace-nowrap', typeof previewData.rows[0][col] === 'number' && 'text-right')}>
                              {humanize(col)}
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {visibleRows.map(({ row, index }) => (
                          <TableRow key={index}>
                            <TableCell className="num py-3 text-right text-xs text-subtle-foreground">{index + 1}</TableCell>
                            {previewCols.map(col => {
                              const val = row[col];
                              const text = val == null ? '' : typeof val === 'object' ? JSON.stringify(val) : String(val);
                              return (
                                <TableCell key={col} className={cn('max-w-[280px] truncate whitespace-nowrap py-3 text-sm text-foreground', typeof val === 'number' && 'num text-right')} title={text || undefined}>
                                  {val == null || text === '' ? <span className="text-subtle-foreground">—</span> : text}
                                </TableCell>
                              );
                            })}
                          </TableRow>
                        ))}
                        {visibleRows.length === 0 && (
                          <TableRow className="hover:bg-transparent">
                            <TableCell colSpan={previewCols.length + 1} className="py-8 text-center text-sm text-muted-foreground">No row contains “{rowFilter}”.</TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </table>
                  </TableShell>
                ) : (
                  <EmptyState
                    icon="table"
                    title={entity.isVirtual ? 'No rows returned for this virtual entity' : 'No rows returned'}
                    description={entity.isVirtual
                      ? 'Check the mapping rules that feed this entity, in the Source tab.'
                      : 'The source returned no rows, or its columns could not be resolved. The Source tab shows the mapping rule and table behind this entity.'}
                  />
                )}
              </TabsContent>
            </div>
          </Tabs>
        )}
      </div>
    </div>
  );
}
