/**
 * FDW Query Mode Component
 *
 * Form-based query builder for executing raw FDW queries against foreign tables.
 * Includes schema/table selection, column picker, filter builder, order-by,
 * limit/offset, and results display with table + JSON views.
 *
 * Exports a pure `buildQueryRequest` function for property testing (task 9.4).
 *
 * Requirements: 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11, 7.12, 11.4, 11.5
 */

import { useState, useMemo } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Code,
  Loader2,
  Minus,
  Play,
  Plus,
  Table2,
  Rows3,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import { Skeleton } from '../ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
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

const FILTER_OPERATORS: FilterOperator[] = [
  'eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'like', 'in',
];

const INITIAL_FORM_STATE: FdwQueryFormState = {
  schemaName: '',
  table: '',
  columns: [],
  filters: [],
  orderBy: [],
  limit: undefined,
  offset: undefined,
};

// ============================================================================
// Pure function: buildQueryRequest (exported for property testing)
// ============================================================================

/**
 * Converts the form state into a QueryRequest object suitable for the FDW API.
 * This is a pure function with no side effects — tested by property tests in 9.4.
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

function QuerySkeleton() {
  return (
    <div className="space-y-3" data-testid="fdw-query-skeleton">
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-2/3" />
    </div>
  );
}

function ErrorCard({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Card className="border-destructive" data-testid="fdw-query-error">
      <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-2">
        <AlertCircle className="h-5 w-5 text-destructive" />
        <CardTitle className="text-base">Error</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{message}</p>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Filter Builder Row
// ============================================================================

function FilterRowItem({
  filter,
  index,
  availableColumns,
  onChange,
  onRemove,
}: {
  filter: FilterRow;
  index: number;
  availableColumns: string[];
  onChange: (index: number, updated: FilterRow) => void;
  onRemove: (index: number) => void;
}) {
  return (
    <div className="flex items-center gap-2" data-testid={`filter-row-${index}`}>
      <Select
        value={filter.column}
        onValueChange={(val) => onChange(index, { ...filter, column: val })}
      >
        <SelectTrigger className="w-40" data-testid={`filter-column-${index}`}>
          <SelectValue placeholder="Column" />
        </SelectTrigger>
        <SelectContent>
          {availableColumns.map((col) => (
            <SelectItem key={col} value={col}>{col}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filter.operator}
        onValueChange={(val) => onChange(index, { ...filter, operator: val as FilterOperator })}
      >
        <SelectTrigger className="w-24" data-testid={`filter-operator-${index}`}>
          <SelectValue placeholder="Op" />
        </SelectTrigger>
        <SelectContent>
          {FILTER_OPERATORS.map((op) => (
            <SelectItem key={op} value={op}>{op}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Input
        value={filter.value}
        onChange={(e) => onChange(index, { ...filter, value: e.target.value })}
        placeholder="Value"
        className="flex-1"
        data-testid={`filter-value-${index}`}
      />

      <Button
        variant="ghost"
        size="icon"
        onClick={() => onRemove(index)}
        data-testid={`filter-remove-${index}`}
      >
        <Minus className="h-4 w-4" />
      </Button>
    </div>
  );
}

// ============================================================================
// Order-By Row
// ============================================================================

function OrderByRowItem({
  orderBy,
  index,
  availableColumns,
  onChange,
  onRemove,
}: {
  orderBy: OrderByRow;
  index: number;
  availableColumns: string[];
  onChange: (index: number, updated: OrderByRow) => void;
  onRemove: (index: number) => void;
}) {
  return (
    <div className="flex items-center gap-2" data-testid={`orderby-row-${index}`}>
      <Select
        value={orderBy.column}
        onValueChange={(val) => onChange(index, { ...orderBy, column: val })}
      >
        <SelectTrigger className="w-40" data-testid={`orderby-column-${index}`}>
          <SelectValue placeholder="Column" />
        </SelectTrigger>
        <SelectContent>
          {availableColumns.map((col) => (
            <SelectItem key={col} value={col}>{col}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button
        variant="outline"
        size="sm"
        onClick={() =>
          onChange(index, {
            ...orderBy,
            direction: orderBy.direction === 'asc' ? 'desc' : 'asc',
          })
        }
        className="w-20 flex items-center gap-1"
        data-testid={`orderby-direction-${index}`}
      >
        {orderBy.direction === 'asc' ? (
          <>
            <ChevronUp className="h-3 w-3" /> ASC
          </>
        ) : (
          <>
            <ChevronDown className="h-3 w-3" /> DESC
          </>
        )}
      </Button>

      <Button
        variant="ghost"
        size="icon"
        onClick={() => onRemove(index)}
        data-testid={`orderby-remove-${index}`}
      >
        <Minus className="h-4 w-4" />
      </Button>
    </div>
  );
}

// ============================================================================
// Results Display
// ============================================================================

function ResultsMetadata({ metadata }: { metadata: QueryResponse['metadata'] }) {
  return (
    <div
      className="flex items-center gap-4 text-sm text-muted-foreground border rounded-md px-4 py-2"
      data-testid="query-metadata"
    >
      <span className="flex items-center gap-1">
        <Clock className="h-3.5 w-3.5" />
        {metadata.durationMs}ms
      </span>
      <span className="flex items-center gap-1">
        <Rows3 className="h-3.5 w-3.5" />
        {metadata.rowCount} rows
      </span>
      <span className="flex items-center gap-1">
        <Table2 className="h-3.5 w-3.5" />
        {metadata.tableQueried}
      </span>
    </div>
  );
}

function ResultsTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No rows returned</p>;
  }

  const columnKeys = Object.keys(rows[0]);

  return (
    <div className="border rounded-md overflow-auto max-h-96">
      <Table>
        <TableHeader>
          <TableRow>
            {columnKeys.map((key) => (
              <TableHead key={key}>{key}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i}>
              {columnKeys.map((key) => (
                <TableCell key={key} className="text-sm">
                  {row[key] === null ? (
                    <span className="text-muted-foreground italic">null</span>
                  ) : (
                    String(row[key])
                  )}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function ResultsJson({ data }: { data: QueryResponse }) {
  return (
    <pre
      className="border rounded-md p-4 overflow-auto max-h-96 text-xs bg-muted/30"
      data-testid="results-json"
    >
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function FdwQueryMode({ fdwSource }: { fdwSource?: string } = {}) {
  const [form, setForm] = useState<FdwQueryFormState>(INITIAL_FORM_STATE);
  const [resultView, setResultView] = useState<'table' | 'json'>('table');

  // Fetch all tables for schema/table dropdowns
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

  // Extract unique schemas from tables
  const schemas = useMemo(() => {
    if (!tables) return [];
    return [...new Set(tables.map((t) => t.schemaName))].sort();
  }, [tables]);

  // Filter tables by selected schema
  const filteredTables = useMemo(() => {
    if (!tables || !form.schemaName) return [];
    return tables.filter((t) => t.schemaName === form.schemaName);
  }, [tables, form.schemaName]);

  // Fetch columns when a table is selected
  const {
    data: columns,
    isLoading: columnsLoading,
  } = useQuery<ColumnInfo[]>({
    queryKey: [...ontosKeys.columns(form.schemaName, form.table), fdwSource],
    queryFn: () => fdwService.getColumns(form.schemaName, form.table, fdwSource),
    enabled: !!form.schemaName && !!form.table,
    staleTime: 300000,
  });

  const columnNames = useMemo(
    () => (columns ?? []).map((c) => c.columnName),
    [columns],
  );

  // Execute query mutation
  const mutation = useMutation<QueryResponse, Error, QueryRequest>({
    mutationFn: (request) => fdwService.executeQuery(request, fdwSource),
    onSuccess: (data) => {
      toast.success(`Query returned ${data.metadata.rowCount} rows in ${data.metadata.durationMs}ms`);
    },
    onError: (error) => {
      toast.error(`Query failed: ${error.message}`);
    },
  });

  // ---- Form handlers ----

  const handleSchemaChange = (schema: string) => {
    setForm({ ...INITIAL_FORM_STATE, schemaName: schema });
  };

  const handleTableChange = (table: string) => {
    setForm((prev) => ({
      ...prev,
      table,
      columns: [],
      filters: [],
      orderBy: [],
    }));
  };

  const handleColumnToggle = (col: string, checked: boolean) => {
    setForm((prev) => ({
      ...prev,
      columns: checked
        ? [...prev.columns, col]
        : prev.columns.filter((c) => c !== col),
    }));
  };

  const handleSelectAllColumns = (selectAll: boolean) => {
    setForm((prev) => ({
      ...prev,
      columns: selectAll ? [...columnNames] : [],
    }));
  };

  // Filters
  const addFilter = () => {
    setForm((prev) => ({
      ...prev,
      filters: [...prev.filters, { column: columnNames[0] ?? '', operator: 'eq', value: '' }],
    }));
  };

  const updateFilter = (index: number, updated: FilterRow) => {
    setForm((prev) => ({
      ...prev,
      filters: prev.filters.map((f, i) => (i === index ? updated : f)),
    }));
  };

  const removeFilter = (index: number) => {
    setForm((prev) => ({
      ...prev,
      filters: prev.filters.filter((_, i) => i !== index),
    }));
  };

  // Order-by
  const addOrderBy = () => {
    setForm((prev) => ({
      ...prev,
      orderBy: [...prev.orderBy, { column: columnNames[0] ?? '', direction: 'asc' }],
    }));
  };

  const updateOrderBy = (index: number, updated: OrderByRow) => {
    setForm((prev) => ({
      ...prev,
      orderBy: prev.orderBy.map((o, i) => (i === index ? updated : o)),
    }));
  };

  const removeOrderBy = (index: number) => {
    setForm((prev) => ({
      ...prev,
      orderBy: prev.orderBy.filter((_, i) => i !== index),
    }));
  };

  // Execute
  const handleExecute = () => {
    const request = buildQueryRequest(form);
    mutation.mutate(request);
  };

  const canExecute = !!form.schemaName && !!form.table && !mutation.isPending;

  // ---- Render ----

  if (tablesLoading) return <QuerySkeleton />;
  if (tablesError) {
    return (
      <ErrorCard
        message={tablesErrorObj?.message ?? 'Failed to fetch tables'}
        onRetry={() => refetchTables()}
      />
    );
  }

  return (
    <div className="space-y-6" data-testid="fdw-query-mode">
      {/* Schema & Table Selection */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Schema</Label>
          <Select value={form.schemaName} onValueChange={handleSchemaChange}>
            <SelectTrigger data-testid="schema-select">
              <SelectValue placeholder="Select schema" />
            </SelectTrigger>
            <SelectContent>
              {schemas.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Table</Label>
          <Select
            value={form.table}
            onValueChange={handleTableChange}
            disabled={!form.schemaName}
          >
            <SelectTrigger data-testid="table-select">
              <SelectValue placeholder="Select table" />
            </SelectTrigger>
            <SelectContent>
              {filteredTables.map((t) => (
                <SelectItem key={t.tableName} value={t.tableName}>
                  {t.tableName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Column Multi-Select */}
      {form.table && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Columns</Label>
            {columnNames.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  handleSelectAllColumns(form.columns.length !== columnNames.length)
                }
                data-testid="toggle-all-columns"
              >
                {form.columns.length === columnNames.length ? 'Deselect All' : 'Select All'}
              </Button>
            )}
          </div>
          {columnsLoading ? (
            <Skeleton className="h-10 w-full" />
          ) : (
            <div
              className="flex flex-wrap gap-3 border rounded-md p-3 max-h-40 overflow-auto"
              data-testid="column-picker"
            >
              {columnNames.length === 0 ? (
                <p className="text-sm text-muted-foreground">No columns available</p>
              ) : (
                columnNames.map((col) => (
                  <label
                    key={col}
                    className="flex items-center gap-1.5 text-sm cursor-pointer"
                  >
                    <Checkbox
                      checked={form.columns.includes(col)}
                      onCheckedChange={(checked) =>
                        handleColumnToggle(col, checked === true)
                      }
                      data-testid={`column-check-${col}`}
                    />
                    {col}
                  </label>
                ))
              )}
            </div>
          )}
          {form.columns.length === 0 && columnNames.length > 0 && (
            <p className="text-xs text-muted-foreground">
              No columns selected — all columns will be returned
            </p>
          )}
        </div>
      )}

      {/* Filter Builder */}
      {form.table && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Filters</Label>
            <Button
              variant="outline"
              size="sm"
              onClick={addFilter}
              disabled={columnNames.length === 0}
              data-testid="add-filter"
            >
              <Plus className="h-3.5 w-3.5 mr-1" /> Add Filter
            </Button>
          </div>
          {form.filters.length > 0 && (
            <div className="space-y-2">
              {form.filters.map((filter, i) => (
                <FilterRowItem
                  key={i}
                  filter={filter}
                  index={i}
                  availableColumns={columnNames}
                  onChange={updateFilter}
                  onRemove={removeFilter}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Order-By Controls */}
      {form.table && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Order By</Label>
            <Button
              variant="outline"
              size="sm"
              onClick={addOrderBy}
              disabled={columnNames.length === 0}
              data-testid="add-orderby"
            >
              <Plus className="h-3.5 w-3.5 mr-1" /> Add Order
            </Button>
          </div>
          {form.orderBy.length > 0 && (
            <div className="space-y-2">
              {form.orderBy.map((ob, i) => (
                <OrderByRowItem
                  key={i}
                  orderBy={ob}
                  index={i}
                  availableColumns={columnNames}
                  onChange={updateOrderBy}
                  onRemove={removeOrderBy}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Limit / Offset */}
      {form.table && (
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Limit</Label>
            <Input
              type="number"
              min={0}
              placeholder="No limit"
              value={form.limit ?? ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  limit: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
              data-testid="limit-input"
            />
          </div>
          <div className="space-y-2">
            <Label>Offset</Label>
            <Input
              type="number"
              min={0}
              placeholder="0"
              value={form.offset ?? ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  offset: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
              data-testid="offset-input"
            />
          </div>
        </div>
      )}

      {/* Execute Button */}
      <div className="flex items-center gap-3">
        <Button
          onClick={handleExecute}
          disabled={!canExecute}
          data-testid="execute-button"
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Executing...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Execute
            </>
          )}
        </Button>
      </div>

      {/* Results */}
      {mutation.isError && (
        <ErrorCard message={mutation.error?.message ?? 'Query execution failed'} />
      )}

      {mutation.isSuccess && mutation.data && (
        <div className="space-y-3" data-testid="query-results">
          <ResultsMetadata metadata={mutation.data.metadata} />

          <div className="flex items-center gap-2">
            <Button
              variant={resultView === 'table' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setResultView('table')}
              data-testid="view-table"
            >
              <Table2 className="h-3.5 w-3.5 mr-1" /> Table
            </Button>
            <Button
              variant={resultView === 'json' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setResultView('json')}
              data-testid="view-json"
            >
              <Code className="h-3.5 w-3.5 mr-1" /> JSON
            </Button>
          </div>

          {resultView === 'table' ? (
            <ResultsTable rows={mutation.data.rows} />
          ) : (
            <ResultsJson data={mutation.data} />
          )}
        </div>
      )}
    </div>
  );
}

export default FdwQueryMode;
