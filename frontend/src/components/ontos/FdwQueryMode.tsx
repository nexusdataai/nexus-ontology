/**
 * Query editor of the runtime explorer.
 *
 * Builds a read query against one table of the source: table, columns,
 * filters, sort order, limit and offset on the left; the rows (table or JSON)
 * with row count and time on the right.
 *
 * Exports the pure `buildQueryRequest` function for property testing.
 */

import { useEffect, useMemo, useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Checkbox } from '../ui/checkbox';
import { Skeleton } from '../ui/skeleton';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { CodeBlock, Field, InlineError, SearchInput, TableShell } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { fdwService } from '@/services/fdwService';
import { ontosKeys } from './queryKeys';
import type {
  ForeignTableInfo,
  ColumnInfo,
  FilterOperator,
  QueryRequest,
  QueryResponse,
} from '@/types/fdwTypes';

// ============================================================================
// Types
// ============================================================================

export interface FilterRow {
  column: string;
  operator: FilterOperator;
  value: string;
}

export interface OrderByRow {
  column: string;
  direction: 'asc' | 'desc';
}

export interface FdwQueryFormState {
  schemaName: string;
  table: string;
  columns: string[];
  filters: FilterRow[];
  orderBy: OrderByRow[];
  limit: number | undefined;
  offset: number | undefined;
}

export interface QueryTableRef {
  schema: string;
  table: string;
}

const FILTER_OPERATORS: FilterOperator[] = [
  'eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'like', 'in',
];

const OPERATOR_LABEL: Record<FilterOperator, string> = {
  eq: 'equals',
  neq: 'does not equal',
  gt: 'greater than',
  gte: 'at least',
  lt: 'less than',
  lte: 'at most',
  like: 'matches pattern',
  in: 'is one of',
};

const VALUE_PLACEHOLDER: Partial<Record<FilterOperator, string>> = {
  like: 'Pattern, % for any text',
  in: 'Values, comma separated',
};

const INITIAL_FORM_STATE: FdwQueryFormState = {
  schemaName: '',
  table: '',
  columns: [],
  filters: [],
  orderBy: [],
  limit: undefined,
  offset: undefined,
};

/** Tables shown at once in the table picker; the search narrows the rest. */
const PICKER_LIMIT = 60;

// ============================================================================
// Pure function: buildQueryRequest (exported for property testing)
// ============================================================================

/**
 * Converts the form state into a QueryRequest object suitable for the FDW API.
 * This is a pure function with no side effects.
 */
export function buildQueryRequest(state: FdwQueryFormState): QueryRequest {
  const request: QueryRequest = {
    table: state.table,
    schemaName: state.schemaName,
  };

  if (state.columns.length > 0) {
    request.columns = [...state.columns];
  }

  if (state.filters.length > 0) {
    request.filters = state.filters.map((f) => {
      // For 'in' operator, split comma-separated values into an array
      if (f.operator === 'in') {
        return {
          column: f.column,
          operator: f.operator,
          value: f.value.split(',').map((v) => v.trim()),
        };
      }
      return {
        column: f.column,
        operator: f.operator,
        value: f.value,
      };
    });
  }

  if (state.orderBy.length > 0) {
    request.orderBy = state.orderBy.map((o) => ({
      column: o.column,
      direction: o.direction,
    }));
  }

  if (state.limit !== undefined) {
    request.limit = state.limit;
  }

  if (state.offset !== undefined) {
    request.offset = state.offset;
  }

  return request;
}

// ============================================================================
// Sub-components
// ============================================================================

function Section({ title, hint, action, children }: { title: string; hint?: React.ReactNode; action?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <section className="border-b border-border px-4 py-5 last:border-b-0 sm:px-6">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-medium text-foreground">{title}</h3>
          {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {children && <div className="mt-3">{children}</div>}
    </section>
  );
}

/** Searchable table picker. A source can expose well over a thousand tables. */
function TablePicker({ tables, value, onChange, disabled }: {
  tables: ForeignTableInfo[];
  value: string;
  onChange: (table: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const matches = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? tables.filter(t => t.tableName.toLowerCase().includes(q)) : tables;
  }, [tables, search]);
  const shown = matches.slice(0, PICKER_LIMIT);

  return (
    <Popover open={open} onOpenChange={(o) => { setOpen(o); if (!o) setSearch(''); }}>
      <PopoverTrigger asChild>
        <Button
          id="query-table"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className="w-full justify-between px-3 font-normal"
          data-testid="table-select"
        >
          <span className={cn('truncate', !value && 'text-muted-foreground')}>{value || 'Choose a table'}</span>
          <Icon name="chevron-down" className="h-3.5 w-3.5 text-subtle-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[var(--radix-popover-trigger-width)] min-w-[260px] p-0">
        <div className="border-b border-border p-2">
          <SearchInput value={search} onChange={setSearch} placeholder="Search tables" className="sm:w-full" autoFocus />
        </div>
        {shown.length === 0 ? (
          <p className="px-3 py-6 text-center text-sm text-muted-foreground">No tables match this search.</p>
        ) : (
          <ul className="scroll-thin max-h-64 overflow-y-auto p-1">
            {shown.map(t => {
              const on = t.tableName === value;
              return (
                <li key={t.tableName}>
                  <button
                    type="button"
                    onClick={() => { onChange(t.tableName); setOpen(false); setSearch(''); }}
                    className={cn(
                      'flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      on ? 'bg-accent font-medium text-foreground' : 'text-foreground hover:bg-accent/60',
                    )}
                  >
                    <span className="truncate">{t.tableName}</span>
                    <span className="num shrink-0 text-xs font-normal text-muted-foreground">{t.columnCount} cols</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {matches.length > shown.length && (
          <p className="border-t border-border px-3 py-2 text-xs text-muted-foreground">
            Showing <span className="num">{shown.length}</span> of <span className="num">{matches.length.toLocaleString()}</span>. Search to narrow the list.
          </p>
        )}
      </PopoverContent>
    </Popover>
  );
}

function ColumnSelect({ value, columns, onChange, testId, label }: { value: string; columns: string[]; onChange: (v: string) => void; testId: string; label: string }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="min-w-0 flex-1 basis-40" data-testid={testId} aria-label={label}>
        <SelectValue placeholder="Column" />
      </SelectTrigger>
      <SelectContent>
        {columns.map((col) => <SelectItem key={col} value={col}>{col}</SelectItem>)}
      </SelectContent>
    </Select>
  );
}

function FilterRowItem({ filter, index, availableColumns, onChange, onRemove }: {
  filter: FilterRow;
  index: number;
  availableColumns: string[];
  onChange: (index: number, updated: FilterRow) => void;
  onRemove: (index: number) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2" data-testid={`filter-row-${index}`}>
      <ColumnSelect
        value={filter.column}
        columns={availableColumns}
        onChange={(val) => onChange(index, { ...filter, column: val })}
        testId={`filter-column-${index}`}
        label="Filter column"
      />
      <Select value={filter.operator} onValueChange={(val) => onChange(index, { ...filter, operator: val as FilterOperator })}>
        <SelectTrigger className="min-w-0 flex-1 basis-36" data-testid={`filter-operator-${index}`} aria-label="Condition">
          <SelectValue placeholder="Condition" />
        </SelectTrigger>
        <SelectContent>
          {FILTER_OPERATORS.map((op) => <SelectItem key={op} value={op}>{OPERATOR_LABEL[op]}</SelectItem>)}
        </SelectContent>
      </Select>
      <Input
        value={filter.value}
        onChange={(e) => onChange(index, { ...filter, value: e.target.value })}
        placeholder={VALUE_PLACEHOLDER[filter.operator] || 'Value'}
        aria-label="Filter value"
        className="min-w-0 flex-1 basis-40"
        data-testid={`filter-value-${index}`}
      />
      <Button variant="ghost" size="icon" onClick={() => onRemove(index)} aria-label="Remove filter" data-testid={`filter-remove-${index}`}>
        <Icon name="close" />
      </Button>
    </div>
  );
}

function OrderByRowItem({ orderBy, index, availableColumns, onChange, onRemove }: {
  orderBy: OrderByRow;
  index: number;
  availableColumns: string[];
  onChange: (index: number, updated: OrderByRow) => void;
  onRemove: (index: number) => void;
}) {
  const asc = orderBy.direction === 'asc';
  return (
    <div className="flex flex-wrap items-center gap-2" data-testid={`orderby-row-${index}`}>
      <ColumnSelect
        value={orderBy.column}
        columns={availableColumns}
        onChange={(val) => onChange(index, { ...orderBy, column: val })}
        testId={`orderby-column-${index}`}
        label="Sort column"
      />
      <Button
        variant="outline"
        onClick={() => onChange(index, { ...orderBy, direction: asc ? 'desc' : 'asc' })}
        className="w-36 justify-between px-3 font-normal"
        aria-label={`Sort direction: ${asc ? 'ascending' : 'descending'}. Click to switch.`}
        data-testid={`orderby-direction-${index}`}
      >
        {asc ? 'Ascending' : 'Descending'}
        <Icon name={asc ? 'chevron-up' : 'chevron-down'} className="h-3.5 w-3.5 text-subtle-foreground" />
      </Button>
      <Button variant="ghost" size="icon" onClick={() => onRemove(index)} aria-label="Remove sort" data-testid={`orderby-remove-${index}`}>
        <Icon name="close" />
      </Button>
    </div>
  );
}

function ResultsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const columnKeys = Object.keys(rows[0]);
  return (
    <TableShell className="scroll-thin max-h-[560px] overflow-y-auto">
      <Table>
        <TableHeader className="sticky top-0 z-10 bg-card">
          <TableRow className="hover:bg-transparent">
            {columnKeys.map((key) => <TableHead key={key} className="font-mono">{key}</TableHead>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i}>
              {columnKeys.map((key) => {
                const val = row[key];
                return (
                  <TableCell key={key} className="max-w-[260px] truncate whitespace-nowrap py-2 font-mono text-xs text-foreground" title={val == null ? undefined : String(val)}>
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
// Main Component
// ============================================================================

interface FdwQueryModeProps {
  fdwSource?: string;
  /** Table to start on when nothing has been chosen yet. */
  defaultTable?: QueryTableRef | null;
  /** Explicit "query this table" request; a new nonce re-applies it. */
  target?: (QueryTableRef & { nonce: number }) | null;
}

export function FdwQueryMode({ fdwSource, defaultTable, target }: FdwQueryModeProps = {}) {
  const [form, setForm] = useState<FdwQueryFormState>(INITIAL_FORM_STATE);
  const [resultView, setResultView] = useState<'table' | 'json'>('table');
  const [columnSearch, setColumnSearch] = useState('');
  const [showRequest, setShowRequest] = useState(false);

  // All tables of the source, for the schema and table pickers
  const {
    data: tables,
    isLoading: tablesLoading,
    isError: tablesError,
    error: tablesErrorObj,
    refetch: refetchTables,
  } = useQuery<ForeignTableInfo[]>({
    queryKey: [...ontosKeys.tables(), fdwSource],
    queryFn: () => fdwService.listTables(undefined, fdwSource),
    staleTime: 300000,
  });

  const schemas = useMemo(() => {
    if (!tables) return [];
    return [...new Set(tables.map((t) => t.schemaName))].sort();
  }, [tables]);

  const filteredTables = useMemo(() => {
    if (!tables || !form.schemaName) return [];
    return tables.filter((t) => t.schemaName === form.schemaName);
  }, [tables, form.schemaName]);

  // Columns of the chosen table
  const {
    data: columns,
    isLoading: columnsLoading,
    isError: columnsError,
    refetch: refetchColumns,
  } = useQuery<ColumnInfo[]>({
    queryKey: [...ontosKeys.columns(form.schemaName, form.table), fdwSource],
    queryFn: () => fdwService.getColumns(form.schemaName, form.table, fdwSource),
    enabled: !!form.schemaName && !!form.table,
    staleTime: 300000,
  });

  const columnNames = useMemo(() => (columns ?? []).map((c) => c.columnName), [columns]);

  const mutation = useMutation<QueryResponse, Error, QueryRequest>({
    mutationFn: (request) => fdwService.executeQuery(request, fdwSource),
    onSuccess: (data) => {
      toast.success(`Query returned ${data.metadata.rowCount} rows in ${data.metadata.durationMs}ms`);
    },
    onError: (error) => {
      toast.error(`Query failed: ${error.message}`);
    },
  });

  // ---- Starting point: never an empty editor ----

  // Nothing chosen yet: start on the table open in the Tables tab, else the first table.
  useEffect(() => {
    if (!tables || tables.length === 0 || form.table) return;
    const wanted = defaultTable && (!form.schemaName || form.schemaName === defaultTable.schema)
      ? tables.find(t => t.schemaName === defaultTable.schema && t.tableName === defaultTable.table)
      : undefined;
    const start = wanted || (form.schemaName ? tables.find(t => t.schemaName === form.schemaName) : undefined) || tables[0];
    if (start) setForm({ ...INITIAL_FORM_STATE, schemaName: start.schemaName, table: start.tableName });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tables, defaultTable?.schema, defaultTable?.table, form.table, form.schemaName]);

  // "Query this table" from the Tables tab.
  useEffect(() => {
    if (!target) return;
    setForm({ ...INITIAL_FORM_STATE, schemaName: target.schema, table: target.table });
    setColumnSearch('');
    mutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target?.nonce]);

  // ---- Form handlers ----

  const handleSchemaChange = (schema: string) => {
    setForm({ ...INITIAL_FORM_STATE, schemaName: schema });
    setColumnSearch('');
  };

  const handleTableChange = (table: string) => {
    setForm((prev) => ({ ...prev, table, columns: [], filters: [], orderBy: [] }));
    setColumnSearch('');
  };

  const handleColumnToggle = (col: string, checked: boolean) => {
    setForm((prev) => ({
      ...prev,
      columns: checked ? [...prev.columns, col] : prev.columns.filter((c) => c !== col),
    }));
  };

  const handleSelectAllColumns = (selectAll: boolean) => {
    setForm((prev) => ({ ...prev, columns: selectAll ? [...columnNames] : [] }));
  };

  const addFilter = () => {
    setForm((prev) => ({
      ...prev,
      filters: [...prev.filters, { column: columnNames[0] ?? '', operator: 'eq', value: '' }],
    }));
  };
  const updateFilter = (index: number, updated: FilterRow) => {
    setForm((prev) => ({ ...prev, filters: prev.filters.map((f, i) => (i === index ? updated : f)) }));
  };
  const removeFilter = (index: number) => {
    setForm((prev) => ({ ...prev, filters: prev.filters.filter((_, i) => i !== index) }));
  };

  const addOrderBy = () => {
    setForm((prev) => ({
      ...prev,
      orderBy: [...prev.orderBy, { column: columnNames[0] ?? '', direction: 'asc' }],
    }));
  };
  const updateOrderBy = (index: number, updated: OrderByRow) => {
    setForm((prev) => ({ ...prev, orderBy: prev.orderBy.map((o, i) => (i === index ? updated : o)) }));
  };
  const removeOrderBy = (index: number) => {
    setForm((prev) => ({ ...prev, orderBy: prev.orderBy.filter((_, i) => i !== index) }));
  };

  const request = useMemo(() => buildQueryRequest(form), [form]);
  const handleExecute = () => mutation.mutate(request);
  const handleReset = () => {
    setForm((prev) => ({ ...INITIAL_FORM_STATE, schemaName: prev.schemaName, table: prev.table }));
    setColumnSearch('');
    mutation.reset();
  };

  const canExecute = !!form.schemaName && !!form.table && !mutation.isPending;
  const isEdited = form.columns.length > 0 || form.filters.length > 0 || form.orderBy.length > 0 || form.limit !== undefined || form.offset !== undefined;

  // ---- Render ----

  if (tablesLoading) {
    return (
      <div className="space-y-3 p-5 sm:p-6" data-testid="fdw-query-skeleton" aria-busy="true">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-10 w-full max-w-md" />
        <Skeleton className="h-10 w-full max-w-md" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (tablesError) {
    return (
      <div className="p-5 sm:p-6" data-testid="fdw-query-error">
        <InlineError onRetry={() => refetchTables()}>
          {tablesErrorObj?.message ?? 'Could not load the tables of this source.'}
        </InlineError>
      </div>
    );
  }

  if (!tables || tables.length === 0) {
    return (
      <div className="p-5 sm:p-6">
        <EmptyState icon="terminal" title="Nothing to query yet" description="This source does not expose any tables, so there is nothing to run a query against." />
      </div>
    );
  }

  const shownColumns = columnSearch.trim()
    ? columnNames.filter(c => c.toLowerCase().includes(columnSearch.trim().toLowerCase()))
    : columnNames;
  const allSelected = columnNames.length > 0 && form.columns.length === columnNames.length;
  const result = mutation.data;
  const rowCount = result ? result.metadata?.rowCount ?? result.rows.length : 0;

  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="fdw-query-mode">
      {/* Editor header */}
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border px-4 py-3 sm:px-6">
        <div className="min-w-0">
          <h2 className="text-md font-medium text-foreground">Read rows from a table</h2>
          <p className="truncate text-xs text-muted-foreground">
            {form.table
              ? <>Reading <span className="mono-id">{form.schemaName}.{form.table}</span> in place. Nothing is copied or changed.</>
              : 'Choose a table to start. Nothing is copied or changed.'}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button variant="ghost" size="sm" onClick={handleReset} disabled={!isEdited && !mutation.data && !mutation.isError}>
            Reset
          </Button>
          <Button size="sm" onClick={handleExecute} disabled={!canExecute} data-testid="execute-button">
            <Icon name={mutation.isPending ? 'spinner' : 'play'} className={mutation.isPending ? 'animate-spin' : undefined} />
            {mutation.isPending ? 'Running…' : 'Run query'}
          </Button>
        </div>
      </header>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto xl:grid xl:grid-cols-[440px_minmax(0,1fr)] xl:overflow-hidden">
        {/* ------------------------------------------------------ the builder */}
        <div className="scroll-thin min-h-0 border-b border-border xl:overflow-y-auto xl:border-b-0 xl:border-r">
          <Section title="Table" hint="The table to read from.">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              {schemas.length > 1 && (
                <Field label="Schema" htmlFor="query-schema">
                  <Select value={form.schemaName} onValueChange={handleSchemaChange}>
                    <SelectTrigger id="query-schema" data-testid="schema-select">
                      <SelectValue placeholder="Choose a schema" />
                    </SelectTrigger>
                    <SelectContent>
                      {schemas.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </Field>
              )}
              <Field
                label="Table"
                htmlFor="query-table"
                hint={schemas.length === 1 ? <>Schema <span className="font-mono">{schemas[0]}</span> · <span className="num">{filteredTables.length.toLocaleString()}</span> tables</> : undefined}
              >
                <TablePicker tables={filteredTables} value={form.table} onChange={handleTableChange} disabled={!form.schemaName} />
              </Field>
            </div>
          </Section>

          {form.table && (
            <>
              <Section
                title="Columns"
                hint={form.columns.length === 0
                  ? 'None chosen: every column is returned.'
                  : <><span className="num">{form.columns.length}</span> of <span className="num">{columnNames.length}</span> chosen.</>}
                action={columnNames.length > 0 && (
                  <Button variant="ghost" size="sm" onClick={() => handleSelectAllColumns(!allSelected)} data-testid="toggle-all-columns">
                    {allSelected ? 'Clear all' : 'Select all'}
                  </Button>
                )}
              >
                {columnsLoading ? (
                  <Skeleton className="h-24 w-full" />
                ) : columnsError ? (
                  <InlineError onRetry={() => refetchColumns()}>Could not load the columns of this table.</InlineError>
                ) : columnNames.length === 0 ? (
                  <p className="text-sm text-muted-foreground">This table has no columns.</p>
                ) : (
                  <>
                    {columnNames.length > 12 && (
                      <SearchInput value={columnSearch} onChange={setColumnSearch} placeholder="Search columns" className="mb-2 sm:w-full" />
                    )}
                    <div className="scroll-thin max-h-52 overflow-y-auto rounded-lg border border-border" data-testid="column-picker">
                      {shownColumns.length === 0 ? (
                        <p className="px-3 py-4 text-center text-sm text-muted-foreground">No columns match this search.</p>
                      ) : (
                        <ul className="grid gap-x-3 p-1.5 sm:grid-cols-2">
                          {shownColumns.map((col) => (
                            <li key={col} className="min-w-0">
                              <label className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1.5 text-sm text-foreground hover:bg-accent/60">
                                <Checkbox
                                  checked={form.columns.includes(col)}
                                  onCheckedChange={(checked) => handleColumnToggle(col, checked === true)}
                                  data-testid={`column-check-${col}`}
                                />
                                <span className="truncate" title={col}>{col}</span>
                              </label>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </>
                )}
              </Section>

              <Section
                title="Filters"
                hint={form.filters.length === 0 ? 'No filter: all rows qualify.' : 'Rows must meet every filter.'}
                action={
                  <Button variant="outline" size="sm" onClick={addFilter} disabled={columnNames.length === 0} data-testid="add-filter">
                    <Icon name="plus" /> Add filter
                  </Button>
                }
              >
                {form.filters.length > 0 && (
                  <div className="space-y-2">
                    {form.filters.map((filter, i) => (
                      <FilterRowItem key={i} filter={filter} index={i} availableColumns={columnNames} onChange={updateFilter} onRemove={removeFilter} />
                    ))}
                  </div>
                )}
              </Section>

              <Section
                title="Sort"
                hint={form.orderBy.length === 0 ? 'No sort: rows come in the source order.' : 'Applied in the order listed.'}
                action={
                  <Button variant="outline" size="sm" onClick={addOrderBy} disabled={columnNames.length === 0} data-testid="add-orderby">
                    <Icon name="plus" /> Add sort
                  </Button>
                }
              >
                {form.orderBy.length > 0 && (
                  <div className="space-y-2">
                    {form.orderBy.map((ob, i) => (
                      <OrderByRowItem key={i} orderBy={ob} index={i} availableColumns={columnNames} onChange={updateOrderBy} onRemove={removeOrderBy} />
                    ))}
                  </div>
                )}
              </Section>

              <Section title="Rows" hint="How many rows to return and where to start.">
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Limit" htmlFor="query-limit" hint="Empty for no limit">
                    <Input
                      id="query-limit"
                      type="number"
                      min={0}
                      placeholder="No limit"
                      value={form.limit ?? ''}
                      onChange={(e) => setForm((prev) => ({ ...prev, limit: e.target.value ? Number(e.target.value) : undefined }))}
                      data-testid="limit-input"
                    />
                  </Field>
                  <Field label="Skip rows" htmlFor="query-offset" hint="Offset from the first row">
                    <Input
                      id="query-offset"
                      type="number"
                      min={0}
                      placeholder="0"
                      value={form.offset ?? ''}
                      onChange={(e) => setForm((prev) => ({ ...prev, offset: e.target.value ? Number(e.target.value) : undefined }))}
                      data-testid="offset-input"
                    />
                  </Field>
                </div>
              </Section>

              <Section
                title="Technical details"
                hint="The request sent to the source when you run the query."
                action={
                  <Button variant="ghost" size="sm" onClick={() => setShowRequest(v => !v)} aria-expanded={showRequest}>
                    {showRequest ? 'Hide' : 'Show'}
                  </Button>
                }
              >
                {showRequest && <CodeBlock maxHeight={220}>{JSON.stringify(request, null, 2)}</CodeBlock>}
              </Section>
            </>
          )}
        </div>

        {/* ------------------------------------------------------ the results */}
        <div className="scroll-thin min-h-0 min-w-0 px-4 py-5 sm:px-6 xl:overflow-y-auto" aria-live="polite">
          {mutation.isPending ? (
            <div className="space-y-2" aria-busy="true">
              <Skeleton className="mb-4 h-5 w-48" />
              {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
            </div>
          ) : mutation.isError ? (
            <div data-testid="fdw-query-error">
              <h3 className="mb-2 text-sm font-medium text-foreground">The query did not run</h3>
              <InlineError onRetry={canExecute ? handleExecute : undefined}>
                {mutation.error?.message ?? 'Query execution failed'}
              </InlineError>
            </div>
          ) : result ? (
            <div data-testid="query-results">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-muted-foreground" data-testid="query-metadata">
                  <span className="num font-medium text-foreground">{rowCount.toLocaleString()}</span> {rowCount === 1 ? 'row' : 'rows'}
                  {result.metadata?.durationMs != null && <> · <span className="num">{result.metadata.durationMs}</span> ms</>}
                  {result.metadata?.tableQueried && <> · <span className="mono-id">{result.metadata.tableQueried}</span></>}
                </p>
                <Tabs value={resultView} onValueChange={(v) => setResultView(v as 'table' | 'json')}>
                  <TabsList className="h-8">
                    <TabsTrigger value="table" className="px-2.5 text-xs" data-testid="view-table">Table</TabsTrigger>
                    <TabsTrigger value="json" className="px-2.5 text-xs" data-testid="view-json">JSON</TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
              {resultView === 'json' ? (
                <div data-testid="results-json">
                  <CodeBlock maxHeight={560}>{JSON.stringify(result, null, 2)}</CodeBlock>
                </div>
              ) : result.rows.length === 0 ? (
                <EmptyState icon="table" title="No rows returned" description="The query ran but no rows matched. Loosen the filters or check that the table holds data." />
              ) : (
                <ResultsTable rows={result.rows} />
              )}
            </div>
          ) : (
            <EmptyState
              icon="play"
              title="Run the query to see rows"
              description={form.table
                ? `Rows from ${form.table} appear here, with the row count and the time the source took.`
                : 'Choose a table, then run the query.'}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default FdwQueryMode;
