/**
 * Tables tab of the runtime explorer (master–detail).
 *
 * Left: searchable list of the tables the source exposes (windowed, because a
 * source can expose well over a thousand tables), filtered by server and by
 * mapping status. Right: the selected table with its columns, a row preview
 * and the virtual entity it is mapped to.
 */

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '../ui/sheet';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { systemName } from '@/components/ds/SystemLogo';
import { Chips, CodeBlock, InlineError, KeyValues, SearchInput, StatusPill, SubHeading, TableShell } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { fdwService } from '@/services/fdwService';
import type { MappingRule } from '@/services/mappingRuleService';
import { ontosKeys } from './queryKeys';
import type { ForeignServerInfo, ForeignTableInfo, ColumnInfo, QueryResponse } from '@/types/fdwTypes';

// ============================================================================
// Pure helpers (exported for tests and for the workspace)
// ============================================================================

/**
 * Filters items by a search term against a name field (case-insensitive).
 * Returns all items when search is empty.
 */
export function filterBySearch<T>(items: T[], search: string, getName: (item: T) => string): T[] {
  const trimmed = search.trim();
  if (!trimmed) return items;
  const lower = trimmed.toLowerCase();
  return items.filter((item) => getName(item).toLowerCase().includes(lower));
}

export interface TableRef {
  schema: string;
  table: string;
}

export const tableKey = (schema: string, table: string) => `${schema}.${table}`.toLowerCase();

/** Mapping rules grouped by the source table they read (schema.table, lower case). */
export type MappingIndex = Map<string, MappingRule[]>;

export function buildMappingIndex(rules: MappingRule[]): MappingIndex {
  const index: MappingIndex = new Map();
  for (const rule of rules) {
    if (!rule?.sourceSchema || !rule?.sourceTable) continue;
    const key = tableKey(rule.sourceSchema, rule.sourceTable);
    const list = index.get(key);
    if (list) list.push(rule); else index.set(key, [rule]);
  }
  return index;
}

export interface MappingInfo {
  index: MappingIndex;
  state: 'loading' | 'ready' | 'error';
  retry?: () => void;
}

const NO_MAPPING: MappingInfo = { index: new Map(), state: 'ready' };
const MAPPING_RULES_PATH = '/ai-stack/data-plane?tab=mappingrules';

type MappingFilter = 'all' | 'mapped' | 'unmapped';
type DetailTab = 'columns' | 'rows' | 'mapping';

const errorText = (e: unknown, fallback: string) => (e as Error)?.message || fallback;

// ============================================================================
// Windowed list: only the rows in view are in the DOM
// ============================================================================

const ROW_H = 52;

function WindowedList<T>({ items, resetKey, getKey, renderRow, label }: {
  items: T[];
  resetKey: string;
  getKey: (item: T) => string;
  renderRow: (item: T) => React.ReactNode;
  label: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [height, setHeight] = useState(640);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setHeight(el.clientHeight || 640);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // A new search or filter starts at the top.
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = 0;
    setScrollTop(0);
  }, [resetKey]);

  const start = Math.max(0, Math.floor(scrollTop / ROW_H) - 6);
  const end = Math.min(items.length, Math.ceil((scrollTop + height) / ROW_H) + 6);

  return (
    <div ref={ref} onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)} className="scroll-thin min-h-0 flex-1 overflow-y-auto">
      <ul aria-label={label} className="relative" style={{ height: items.length * ROW_H }}>
        {items.slice(start, end).map((item, i) => (
          <li key={getKey(item)} className="absolute inset-x-0 px-2" style={{ top: (start + i) * ROW_H, height: ROW_H }}>
            {renderRow(item)}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ============================================================================
// Rows table (preview)
// ============================================================================

function RowsTable({ rows }: { rows: Record<string, any>[] }) {
  const cols = Object.keys(rows[0]);
  return (
    <TableShell className="scroll-thin max-h-[480px] overflow-y-auto">
      <Table>
        <TableHeader className="sticky top-0 z-10 bg-card">
          <TableRow className="hover:bg-transparent">
            {cols.map(col => <TableHead key={col} className="font-mono">{col}</TableHead>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i}>
              {cols.map(col => {
                const val = row[col];
                return (
                  <TableCell key={col} className="max-w-[240px] truncate whitespace-nowrap py-2 font-mono text-xs text-foreground" title={val == null ? undefined : String(val)}>
                    {val == null ? <span className="text-subtle-foreground">—</span> : String(val)}
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableShell>
  );
}

// ============================================================================
// Detail: one table
// ============================================================================

function TableDetail({ table, fdwSource, rules, mapping, onQueryTable }: {
  table: ForeignTableInfo;
  fdwSource?: string;
  rules: MappingRule[];
  /** Null when mapping status is not shown at all. */
  mapping: MappingInfo | null;
  onQueryTable?: (ref: TableRef) => void;
}) {
  const schema = table.schemaName;
  const tableName = table.tableName;
  const [tab, setTab] = useState<DetailTab>('columns');
  const [columnSearch, setColumnSearch] = useState('');

  const columnsQuery = useQuery<ColumnInfo[]>({
    queryKey: [...ontosKeys.columns(schema, tableName), fdwSource],
    queryFn: () => fdwService.getColumns(schema, tableName, fdwSource),
    staleTime: 300000,
  });
  const columns = columnsQuery.data ?? [];

  // Same read as before: first 10 columns, 20 rows. Runs when the Rows tab is opened.
  const previewQuery = useQuery<QueryResponse>({
    queryKey: ['fdw', 'preview', schema, tableName, fdwSource],
    queryFn: () => {
      const cols = columns.slice(0, 10).map(c => c.columnName);
      return fdwService.executeQuery(
        { table: tableName, schemaName: schema, columns: cols.length > 0 ? cols : undefined, limit: 20 },
        fdwSource,
      );
    },
    enabled: tab === 'rows' && !columnsQuery.isLoading,
    staleTime: 60000,
    retry: false,
  });

  // Source column → canonical field, from the rules bound to this table.
  const targetByColumn = useMemo(() => {
    const m = new Map<string, string>();
    for (const rule of rules) {
      for (const fm of rule.fieldMaps ?? []) {
        if (fm?.sourceField && !m.has(fm.sourceField)) m.set(fm.sourceField, fm.targetField);
      }
    }
    return m;
  }, [rules]);

  const shownColumns = filterBySearch(columns, columnSearch, c => c.columnName);
  const entityNames = [...new Set(rules.map(r => r.virtualEntity).filter(Boolean))];
  const columnCount = columnsQuery.data ? columns.length : table.columnCount;
  const preview = previewQuery.data;

  return (
    <Tabs value={tab} onValueChange={(v) => setTab(v as DetailTab)} className="flex min-h-0 flex-1 flex-col">
      <header className="shrink-0 px-4 pt-5 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <h2 className="min-w-0 break-all text-xl font-medium tracking-tight text-foreground">{tableName}</h2>
              {mapping?.state === 'ready' && (
                <StatusPill tone={rules.length > 0 ? 'success' : 'neutral'} variant="soft">
                  {rules.length > 0 ? 'Mapped' : 'Not mapped'}
                </StatusPill>
              )}
            </div>
            <p className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
              <span className="mono-id break-all">{schema}.{tableName}</span>
              <span aria-hidden="true">·</span>
              <span><span className="num">{columnCount}</span> {columnCount === 1 ? 'column' : 'columns'}</span>
              {table.serverName && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>Server <span className="mono-id">{table.serverName}</span></span>
                </>
              )}
            </p>
            {entityNames.length > 0 && (
              <p className="mt-1 text-sm text-muted-foreground">
                Feeds the virtual {entityNames.length === 1 ? 'entity' : 'entities'}{' '}
                <span className="font-medium text-foreground">{entityNames.join(', ')}</span>.
              </p>
            )}
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {onQueryTable && (
              <Button variant="outline" size="sm" onClick={() => onQueryTable({ schema, table: tableName })}>
                <Icon name="terminal" /> Query this table
              </Button>
            )}
            <Button size="sm" onClick={() => setTab('rows')} data-testid="preview-rows-button">
              <Icon name="eye" /> Preview rows
            </Button>
          </div>
        </div>

        <TabsList variant="line" className="mt-4">
          <TabsTrigger value="columns">Columns <span className="num text-xs font-normal text-subtle-foreground">{columnCount}</span></TabsTrigger>
          <TabsTrigger value="rows">Rows</TabsTrigger>
          {mapping && (
            <TabsTrigger value="mapping">
              Mapping {rules.length > 0 && <span className="num text-xs font-normal text-subtle-foreground">{rules.length}</span>}
            </TabsTrigger>
          )}
        </TabsList>
      </header>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
        {/* ---------------------------------------------------------- columns */}
        <TabsContent value="columns" className="mt-0">
          {columnsQuery.isLoading ? (
            <div className="space-y-2" data-testid="columns-skeleton" aria-busy="true">
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
            </div>
          ) : columnsQuery.isError ? (
            <InlineError onRetry={() => columnsQuery.refetch()}>
              {errorText(columnsQuery.error, 'Could not load the columns of this table.')}
            </InlineError>
          ) : columns.length === 0 ? (
            <EmptyState icon="table" title="No columns found" description="The source did not return any columns for this table." />
          ) : (
            <>
              {columns.length > 12 && (
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <SearchInput value={columnSearch} onChange={setColumnSearch} placeholder="Search columns" />
                  <p className="text-xs text-muted-foreground">
                    <span className="num">{shownColumns.length}</span> of <span className="num">{columns.length}</span> columns
                  </p>
                </div>
              )}
              {shownColumns.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">No columns match this search.</p>
              ) : (
                <TableShell>
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead>Column</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Required</TableHead>
                        {targetByColumn.size > 0 && <TableHead>Mapped to</TableHead>}
                        <TableHead className="text-right">Position</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {shownColumns.map(col => {
                        const target = targetByColumn.get(col.columnName);
                        return (
                          <TableRow key={col.columnName}>
                            <TableCell className="py-2 text-sm font-medium text-foreground">{col.columnName}</TableCell>
                            <TableCell className="py-2"><span className="mono-id">{col.dataType}</span></TableCell>
                            <TableCell className="py-2 text-sm text-muted-foreground">{col.isNullable ? 'Optional' : 'Required'}</TableCell>
                            {targetByColumn.size > 0 && (
                              <TableCell className="py-2 text-sm">
                                {target
                                  ? <span className="inline-flex items-center gap-1.5 text-foreground"><Icon name="arrow-right" className="h-3 w-3 text-subtle-foreground" />{target}</span>
                                  : <span className="text-subtle-foreground">—</span>}
                              </TableCell>
                            )}
                            <TableCell className="num py-2 text-right text-sm text-muted-foreground">{col.ordinalPosition}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TableShell>
              )}
            </>
          )}
        </TabsContent>

        {/* ------------------------------------------------------------- rows */}
        <TabsContent value="rows" className="mt-0">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              {previewQuery.isFetching || columnsQuery.isLoading ? 'Loading rows…' : preview ? (
                <>
                  <span className="num font-medium text-foreground">{preview.metadata?.rowCount ?? preview.rows.length}</span>{' '}
                  {(preview.metadata?.rowCount ?? preview.rows.length) === 1 ? 'row' : 'rows'}
                  {preview.metadata?.durationMs != null && <> · <span className="num">{preview.metadata.durationMs}</span> ms</>}
                  {' '}· limited to 20 rows{columns.length > 10 && <>, first 10 of <span className="num">{columns.length}</span> columns</>}
                </>
              ) : 'A sample of up to 20 rows.'}
            </p>
            <Button variant="outline" size="sm" onClick={() => previewQuery.refetch()} disabled={previewQuery.isFetching || columnsQuery.isLoading}>
              <Icon name="refresh" className={previewQuery.isFetching ? 'animate-spin' : undefined} /> Refresh
            </Button>
          </div>
          {previewQuery.isError && !previewQuery.isFetching ? (
            <InlineError onRetry={() => previewQuery.refetch()}>
              {errorText(previewQuery.error, 'Could not read rows from this table.')}
            </InlineError>
          ) : !preview ? (
            <div className="space-y-2" aria-busy="true">
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
            </div>
          ) : preview.rows.length > 0 ? (
            <RowsTable rows={preview.rows} />
          ) : (
            <EmptyState
              icon="table"
              title="No rows returned"
              description="The table exists but the source returned no rows for it."
            />
          )}
          {onQueryTable && preview && preview.rows.length > 0 && (
            <p className="mt-3 text-xs text-muted-foreground">
              Need other columns, filters or more rows?{' '}
              <button type="button" onClick={() => onQueryTable({ schema, table: tableName })} className="font-medium text-primary underline-offset-4 hover:underline dark:text-brand-hi">
                Query this table
              </button>
            </p>
          )}
        </TabsContent>

        {/* ---------------------------------------------------------- mapping */}
        <TabsContent value="mapping" className="mt-0">
          {!mapping ? null : mapping.state === 'loading' ? (
            <div className="space-y-2" aria-busy="true">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
            </div>
          ) : mapping.state === 'error' ? (
            <InlineError onRetry={mapping.retry}>Could not load the mapping rules, so the mapping of this table is unknown.</InlineError>
          ) : rules.length === 0 ? (
            <EmptyState
              icon="shuffle"
              title="Not mapped to a virtual entity"
              description="No mapping rule reads this table yet. Map it to make its data available as a canonical entity."
              action={<Button asChild variant="outline" size="sm"><Link to={MAPPING_RULES_PATH}>Open mapping rules</Link></Button>}
            />
          ) : (
            <div className="space-y-8">
              {rules.map(rule => (
                <section key={rule.id} className="max-w-3xl">
                  <SubHeading action={<StatusPill status={rule.status} />}>{rule.virtualEntity}</SubHeading>
                  <KeyValues
                    columns={2}
                    items={[
                      { label: 'Rule', value: rule.name },
                      { label: 'Access', value: rule.sourceType === 'FDW' ? 'Read in place (FDW)' : rule.sourceType },
                      { label: 'Source system', value: systemName(rule.sourceSystem) },
                      { label: 'Fields mapped', value: <span className="num">{rule.fieldMaps?.length ?? 0}</span> },
                    ]}
                  />
                  {rule.fieldMaps?.length > 0 && (
                    <TableShell className="mt-4">
                      <Table>
                        <TableHeader>
                          <TableRow className="hover:bg-transparent">
                            <TableHead>Source column</TableHead>
                            <TableHead className="w-8 px-0" aria-hidden="true" />
                            <TableHead>Entity field</TableHead>
                            <TableHead>Transform</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {rule.fieldMaps.map((fm, i) => (
                            <TableRow key={`${fm.sourceField}-${i}`}>
                              <TableCell className="py-2 text-sm text-foreground">{fm.sourceField}</TableCell>
                              <TableCell className="px-0 py-2"><Icon name="arrow-right" className="h-3 w-3 text-subtle-foreground" /></TableCell>
                              <TableCell className="py-2 text-sm font-medium text-foreground">{fm.targetField}</TableCell>
                              <TableCell className="py-2 text-sm text-muted-foreground">{fm.transform || '—'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableShell>
                  )}
                  {rule.filterExpression && (
                    <div className="mt-4">
                      <SubHeading>Filter</SubHeading>
                      <CodeBlock wrap>{rule.filterExpression}</CodeBlock>
                    </div>
                  )}
                </section>
              ))}
              <Button asChild variant="outline" size="sm"><Link to={MAPPING_RULES_PATH}>Open mapping rules</Link></Button>
            </div>
          )}
        </TabsContent>
      </div>
    </Tabs>
  );
}

// ============================================================================
// Main component
// ============================================================================

interface FdwExplorerProps {
  fdwSource?: string;
  /** Mapping rules by source table. Omit to hide mapping status. */
  mapping?: MappingInfo;
  /** Reports the table shown in the detail pane. */
  onCurrentChange?: (ref: TableRef | null) => void;
  /** "Query this table": opens the table in the query editor. */
  onQueryTable?: (ref: TableRef) => void;
}

const ALL_SERVERS = '__all__';

export function FdwExplorer({ fdwSource, mapping = NO_MAPPING, onCurrentChange, onQueryTable }: FdwExplorerProps = {}) {
  const [search, setSearch] = useState('');
  const [server, setServer] = useState<string>(ALL_SERVERS);
  const [mappingFilter, setMappingFilter] = useState<MappingFilter>('all');
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [browseOpen, setBrowseOpen] = useState(false);

  const serversQuery = useQuery<ForeignServerInfo[]>({
    queryKey: [...ontosKeys.servers, fdwSource],
    queryFn: () => fdwService.listServers(fdwSource),
    staleTime: 300000,
  });
  const servers = serversQuery.data ?? [];

  const serverParam = server === ALL_SERVERS ? undefined : server;
  const tablesQuery = useQuery<ForeignTableInfo[]>({
    queryKey: [...ontosKeys.tables(serverParam), fdwSource],
    queryFn: () => fdwService.listTables(serverParam, fdwSource),
    staleTime: 300000,
  });

  const showMapping = mapping !== NO_MAPPING;
  const isMapped = (t: ForeignTableInfo) => mapping.index.has(tableKey(t.schemaName, t.tableName));

  // Mapped tables first (they are the ones in use), then the source's own order.
  const tables = useMemo(() => {
    const all = tablesQuery.data ?? [];
    if (mapping.index.size === 0) return all;
    const mapped: ForeignTableInfo[] = [];
    const rest: ForeignTableInfo[] = [];
    for (const t of all) (mapping.index.has(tableKey(t.schemaName, t.tableName)) ? mapped : rest).push(t);
    return [...mapped, ...rest];
  }, [tablesQuery.data, mapping.index]);

  const mappedCount = useMemo(() => tables.filter(isMapped).length, [tables, mapping.index]);

  const filtered = useMemo(() => {
    const byStatus = mappingFilter === 'all' ? tables : tables.filter(t => isMapped(t) === (mappingFilter === 'mapped'));
    return filterBySearch(byStatus, search, t => t.tableName);
  }, [tables, mappingFilter, search, mapping.index]);

  // Wait for the mapping lookup before first paint so the order does not jump.
  const listLoading = tablesQuery.isLoading || (showMapping && mapping.state === 'loading');

  // First table is open by default; a search does not change the open table.
  const current = useMemo(() => {
    if (listLoading) return null;
    return tables.find(t => tableKey(t.schemaName, t.tableName) === selectedKey) ?? filtered[0] ?? null;
  }, [listLoading, tables, filtered, selectedKey]);
  const currentKey = current ? tableKey(current.schemaName, current.tableName) : null;

  useEffect(() => {
    onCurrentChange?.(current ? { schema: current.schemaName, table: current.tableName } : null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentKey]);

  const select = (t: ForeignTableInfo) => {
    setSelectedKey(tableKey(t.schemaName, t.tableName));
    setBrowseOpen(false);
  };

  const singleServer = servers.length === 1 ? servers[0] : null;

  /* ------------------------------------------------------------- the list */

  const list = (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 space-y-2.5 border-b border-border p-3">
        <SearchInput value={search} onChange={setSearch} placeholder="Search tables" className="sm:w-full" data-testid="search-input" />
        {servers.length > 1 && (
          <Select value={server} onValueChange={(v) => { setServer(v); setSelectedKey(null); }}>
            <SelectTrigger className="h-8 px-2.5 text-xs" aria-label="Filter by server"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_SERVERS}>All servers</SelectItem>
              {servers.map(s => (
                <SelectItem key={s.serverName} value={s.serverName} data-testid={`server-item-${s.serverName}`}>
                  {s.serverName}{s.wrapperType ? ` (${s.wrapperType})` : ''}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        {showMapping && mapping.state === 'ready' && tables.length > 0 && (
          <Chips<MappingFilter>
            label="Filter by mapping"
            value={mappingFilter}
            onChange={setMappingFilter}
            options={[
              { value: 'all', label: 'All', count: tables.length },
              { value: 'mapped', label: 'Mapped', count: mappedCount },
              { value: 'unmapped', label: 'Not mapped' },
            ]}
          />
        )}
      </div>

      {listLoading ? (
        <div className="min-h-0 flex-1 space-y-2 p-3" data-testid="explorer-skeleton" aria-busy="true">
          {Array.from({ length: 9 }).map((_, i) => <Skeleton key={i} className="h-11 w-full" />)}
        </div>
      ) : tablesQuery.isError ? (
        <div className="min-h-0 flex-1 p-3" data-testid="explorer-error">
          <InlineError onRetry={() => tablesQuery.refetch()}>{errorText(tablesQuery.error, 'Could not load the tables.')}</InlineError>
        </div>
      ) : filtered.length === 0 ? (
        <p className="min-h-0 flex-1 px-4 py-8 text-center text-sm text-muted-foreground" data-testid="explorer-empty">
          {tables.length === 0 ? 'This source exposes no tables yet.' : 'No tables match this search or filter.'}
        </p>
      ) : (
        <WindowedList
          items={filtered}
          resetKey={`${search}|${mappingFilter}|${server}`}
          label="Tables"
          getKey={t => `${t.schemaName}.${t.tableName}`}
          renderRow={(t) => {
            const key = tableKey(t.schemaName, t.tableName);
            const on = key === currentKey;
            const rules = mapping.index.get(key);
            return (
              <button
                type="button"
                onClick={() => select(t)}
                aria-current={on ? 'true' : undefined}
                data-testid={`table-item-${t.schemaName}.${t.tableName}`}
                className={cn(
                  'flex h-12 w-full flex-col justify-center overflow-hidden rounded-md px-2 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  on ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground',
                )}
              >
                <span className={cn('block w-full truncate text-sm text-foreground', on && 'font-medium')}>{t.tableName}</span>
                <span className="mt-0.5 flex w-full items-center gap-1.5 overflow-hidden text-xs text-muted-foreground">
                  <span className="num shrink-0">{t.columnCount} {t.columnCount === 1 ? 'column' : 'columns'}</span>
                  {rules && rules.length > 0 && (
                    <>
                      <span aria-hidden="true">·</span>
                      <StatusPill tone="success" className="min-w-0 shrink font-normal text-muted-foreground">
                        <span className="truncate">Mapped to {rules[0].virtualEntity}{rules.length > 1 ? ` +${rules.length - 1}` : ''}</span>
                      </StatusPill>
                    </>
                  )}
                </span>
              </button>
            );
          }}
        />
      )}

      {!listLoading && !tablesQuery.isError && tables.length > 0 && (
        <div className="shrink-0 space-y-0.5 border-t border-border px-4 py-2 text-xs text-muted-foreground">
          <p><span className="num">{filtered.length.toLocaleString()}</span> of <span className="num">{tables.length.toLocaleString()}</span> tables</p>
          {singleServer && (
            <p className="truncate" data-testid={`server-item-${singleServer.serverName}`}>
              Server <span className="mono-id">{singleServer.serverName}</span>
              {singleServer.wrapperType && singleServer.wrapperType !== singleServer.serverName ? ` · ${singleServer.wrapperType} wrapper` : ''}
            </p>
          )}
          {showMapping && mapping.state === 'error' && (
            <p>
              Mapping status unavailable.{' '}
              <button type="button" onClick={mapping.retry} className="font-medium underline underline-offset-4">Retry</button>
            </p>
          )}
        </div>
      )}
    </div>
  );

  /* ----------------------------------------------------------- the layout */

  return (
    <div className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)] lg:grid-cols-[300px_minmax(0,1fr)]" data-testid="fdw-explorer">
      <aside className="hidden min-h-0 border-r border-border bg-sidebar/40 lg:block" aria-label="Tables">{list}</aside>

      <Sheet open={browseOpen} onOpenChange={setBrowseOpen}>
        <SheetContent side="left" className="flex w-full flex-col gap-0 p-0 sm:max-w-sm">
          <div className="border-b border-border px-4 pb-3 pt-4 pr-12">
            <SheetTitle className="text-md font-medium">Tables</SheetTitle>
            <SheetDescription className="sr-only">Choose a table of this source</SheetDescription>
          </div>
          <div className="min-h-0 flex-1">{list}</div>
        </SheetContent>
      </Sheet>

      <div className="flex min-h-0 min-w-0 flex-col">
        <div className="shrink-0 border-b border-border px-4 py-2 lg:hidden">
          <Button variant="outline" size="sm" className="w-full justify-between" onClick={() => setBrowseOpen(true)}>
            <span className="flex min-w-0 items-center gap-2">
              <Icon name="list" className="h-3.5 w-3.5" />
              <span className="truncate">{current ? current.tableName : 'Browse tables'}</span>
            </span>
            <span className="flex items-center gap-1.5 font-normal text-muted-foreground">
              <span className="num">{filtered.length.toLocaleString()}</span>
              <Icon name="chevron-down" className="h-3.5 w-3.5" />
            </span>
          </Button>
        </div>

        {listLoading ? (
          <div className="space-y-4 p-5 sm:p-6" aria-busy="true">
            <Skeleton className="h-7 w-56" />
            <Skeleton className="h-4 w-80 max-w-full" />
            <Skeleton className="h-10 w-full" />
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
          </div>
        ) : tablesQuery.isError ? (
          <div className="p-5 sm:p-6">
            <InlineError onRetry={() => tablesQuery.refetch()}>{errorText(tablesQuery.error, 'Could not load the tables of this source.')}</InlineError>
          </div>
        ) : !current ? (
          <div className="p-5 sm:p-6">
            <EmptyState
              icon="table"
              title={tables.length === 0 ? 'No tables exposed yet' : 'No tables match this search or filter'}
              description={tables.length === 0
                ? (servers.length === 0 && !serversQuery.isLoading
                  ? 'No foreign server is set up for this source, so there is nothing to browse. Connect the source or switch it to simulator mode in Settings.'
                  : 'The source is connected but does not expose any tables.')
                : 'Clear the search or choose another filter to see tables again.'}
            />
          </div>
        ) : (
          <TableDetail
            key={currentKey}
            table={current}
            fdwSource={fdwSource}
            rules={mapping.index.get(currentKey!) ?? []}
            mapping={showMapping ? mapping : null}
            onQueryTable={onQueryTable}
          />
        )}
      </div>
    </div>
  );
}

export default FdwExplorer;
