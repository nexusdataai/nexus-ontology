/**
 * FDW Explorer Component
 *
 * Two-panel layout for browsing foreign servers, tables, and column schemas:
 * - Left panel: server list + table list with search filtering
 * - Right panel: column details table
 *
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
 */

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  Database,
  Eye,
  Loader2,
  RefreshCw,
  Search,
  Server,
  Table2,
  X,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
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
import type { ForeignServerInfo, ForeignTableInfo, ColumnInfo, QueryResponse } from '@/types/fdwTypes';

// ============================================================================
// Pure filtering function (exported for property testing)
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

// ============================================================================
// Sub-components
// ============================================================================

function ExplorerSkeleton() {
  return (
    <div className="space-y-2" data-testid="explorer-skeleton">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Card className="border-destructive" data-testid="explorer-error">
      <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-2">
        <AlertCircle className="h-5 w-5 text-destructive" />
        <CardTitle className="text-base">Error</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{message}</p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="h-4 w-4 mr-1" />
          Retry
        </Button>
      </CardContent>
    </Card>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground" data-testid="explorer-empty">
      <Database className="h-10 w-10 mb-3 opacity-50" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ============================================================================
// Server List Item
// ============================================================================

function ServerItem({
  server,
  isSelected,
  onSelect,
}: {
  server: ForeignServerInfo;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left px-3 py-2.5 rounded-md transition-colors ${
        isSelected
          ? 'bg-primary/10 border border-primary/30'
          : 'hover:bg-muted/50 border border-transparent'
      }`}
      data-testid={`server-item-${server.serverName}`}
    >
      <div className="flex items-center gap-2">
        <Server className="h-4 w-4 text-muted-foreground shrink-0" />
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{server.serverName}</p>
          <p className="text-xs text-muted-foreground">{server.wrapperType}</p>
        </div>
      </div>
    </button>
  );
}

// ============================================================================
// Table List Item
// ============================================================================

function TableItem({
  table,
  isSelected,
  onSelect,
  rowCount,
}: {
  table: ForeignTableInfo;
  isSelected: boolean;
  onSelect: () => void;
  rowCount?: number;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
        isSelected
          ? 'bg-primary/10 border border-primary/30'
          : 'hover:bg-muted/50 border border-transparent'
      }`}
      data-testid={`table-item-${table.schemaName}.${table.tableName}`}
    >
      <div className="flex items-center gap-2">
        <Table2 className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-sm truncate">{table.tableName}</p>
          <p className="text-xs text-muted-foreground">
            {table.schemaName} · {rowCount != null ? `${rowCount.toLocaleString()} rows` : `${table.columnCount} cols`}
          </p>
        </div>
      </div>
    </button>
  );
}

// ============================================================================
// Column Details Panel
// ============================================================================

function ColumnPanel({
  schema,
  tableName,
  fdwSource,
}: {
  schema: string;
  tableName: string;
  fdwSource?: string;
}) {
  const [showData, setShowData] = useState(false);
  const [dataRows, setDataRows] = useState<Record<string, any>[]>([]);
  const [dataMeta, setDataMeta] = useState<{ rowCount: number; durationMs: number } | null>(null);
  const [dataLoading, setDataLoading] = useState(false);

  const {
    data: columns,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<ColumnInfo[]>({
    queryKey: [...ontosKeys.columns(schema, tableName), fdwSource],
    queryFn: () => fdwService.getColumns(schema, tableName, fdwSource),
    staleTime: 300000,
  });

  const handleViewData = async () => {
    if (showData) { setShowData(false); return; }
    setDataLoading(true);
    setShowData(true);
    try {
      const cols = columns?.slice(0, 10).map(c => c.columnName) || [];
      const result = await fdwService.executeQuery(
        { table: tableName, schemaName: schema, columns: cols.length > 0 ? cols : undefined, limit: 20 },
        fdwSource,
      );
      setDataRows(result.rows);
      setDataMeta(result.metadata);
    } catch {
      setDataRows([]);
      setDataMeta(null);
    } finally { setDataLoading(false); }
  };

  if (isLoading) {
    return (
      <div data-testid="columns-skeleton">
        <Skeleton className="h-8 w-48 mb-4" />
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorCard
        message={error?.message ?? 'Failed to fetch column details'}
        onRetry={() => refetch()}
      />
    );
  }

  if (!columns || columns.length === 0) {
    return <EmptyState message="No columns found for this table" />;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">
          {schema}.{tableName}
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            {columns.length} columns
          </span>
        </h3>
        <Button variant="outline" size="sm" onClick={handleViewData}>
          {showData ? <X className="h-3.5 w-3.5 mr-1" /> : <Eye className="h-3.5 w-3.5 mr-1" />}
          {showData ? 'Hide Data' : 'View Data'}
        </Button>
      </div>

      {showData && (
        <div className="border rounded-lg overflow-hidden">
          <div className="px-3 py-2 bg-muted/30 flex items-center gap-2 text-xs text-muted-foreground border-b">
            <Eye className="h-3.5 w-3.5" />
            <span>Data Preview — {tableName}</span>
            {dataMeta && (
              <span className="ml-auto">{dataMeta.rowCount} rows · {dataMeta.durationMs}ms</span>
            )}
          </div>
          {dataLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : dataRows.length > 0 ? (
            <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b">
                    {Object.keys(dataRows[0]).map(col => (
                      <th key={col} className="text-left px-2.5 py-1.5 font-medium text-muted-foreground whitespace-nowrap">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {dataRows.map((row, i) => (
                    <tr key={i} className="hover:bg-muted/30">
                      {Object.values(row).map((val, j) => (
                        <td key={j} className="px-2.5 py-1.5 font-mono truncate max-w-[200px] whitespace-nowrap">
                          {val == null ? <span className="text-muted-foreground/50 italic">null</span> : String(val)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-6 text-center text-xs text-muted-foreground">No data rows available for this table</div>
          )}
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Column</TableHead>
            <TableHead>Data Type</TableHead>
            <TableHead>Nullable</TableHead>
            <TableHead className="text-right">Position</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {columns.map((col) => (
            <TableRow key={col.columnName}>
              <TableCell className="font-medium">{col.columnName}</TableCell>
              <TableCell>
                <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{col.dataType}</code>
              </TableCell>
              <TableCell>
                <span className={col.isNullable ? 'text-muted-foreground' : 'text-foreground font-medium'}>
                  {col.isNullable ? 'Yes' : 'No'}
                </span>
              </TableCell>
              <TableCell className="text-right">{col.ordinalPosition}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function FdwExplorer({ fdwSource }: { fdwSource?: string } = {}) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [selectedServer, setSelectedServer] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<{ schema: string; table: string } | null>(null);

  // Fetch servers
  const {
    data: servers,
    isLoading: serversLoading,
    isError: serversError,
    error: serversErrorObj,
    refetch: refetchServers,
  } = useQuery<ForeignServerInfo[]>({
    queryKey: [...ontosKeys.servers, fdwSource],
    queryFn: () => fdwService.listServers(fdwSource),
    staleTime: 300000,
  });

  // Fetch tables for selected server
  const {
    data: tables,
    isLoading: tablesLoading,
    isError: tablesError,
    error: tablesErrorObj,
    refetch: refetchTables,
  } = useQuery<ForeignTableInfo[]>({
    queryKey: [...ontosKeys.tables(selectedServer ?? undefined), fdwSource],
    queryFn: () => fdwService.listTables(selectedServer ?? undefined, fdwSource),
    enabled: !!selectedServer,
    staleTime: 300000,
  });

  // Filter servers and tables by search
  const filteredServers = filterBySearch(servers ?? [], search, (s) => s.serverName);
  const filteredTables = filterBySearch(tables ?? [], search, (t) => t.tableName);

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ontosKeys.servers });
    if (selectedServer) {
      queryClient.invalidateQueries({ queryKey: ontosKeys.tables(selectedServer) });
    }
  };

  const handleServerSelect = (serverName: string) => {
    setSelectedServer(serverName);
    setSelectedTable(null);
  };

  const handleTableSelect = (schema: string, table: string) => {
    setSelectedTable({ schema, table });
  };

  return (
    <div className="h-full flex flex-col p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">FDW Explorer</h2>
        <Button variant="outline" size="sm" onClick={handleRefresh} data-testid="refresh-button">
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>

      {/* Two-panel layout */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Left panel: servers + tables */}
        <div className="w-80 shrink-0 flex flex-col border rounded-lg overflow-hidden">
          {/* Search */}
          <div className="p-3 border-b">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search servers and tables..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 h-9"
                data-testid="search-input"
              />
            </div>
          </div>

          {/* Server + table list */}
          <div className="flex-1 overflow-auto p-2 space-y-1">
            {serversLoading && <ExplorerSkeleton />}

            {serversError && (
              <ErrorCard
                message={serversErrorObj?.message ?? 'Failed to fetch servers'}
                onRetry={() => refetchServers()}
              />
            )}

            {!serversLoading && !serversError && filteredServers.length === 0 && (
              <EmptyState message="No foreign servers configured" />
            )}

            {!serversLoading &&
              !serversError &&
              filteredServers.map((server) => (
                <div key={server.serverName}>
                  <ServerItem
                    server={server}
                    isSelected={selectedServer === server.serverName}
                    onSelect={() => handleServerSelect(server.serverName)}
                  />

                  {/* Tables for selected server */}
                  {selectedServer === server.serverName && (
                    <div className="ml-4 mt-1 space-y-0.5">
                      {tablesLoading && (
                        <div className="space-y-1 py-1" data-testid="tables-skeleton">
                          {Array.from({ length: 3 }).map((_, i) => (
                            <Skeleton key={i} className="h-10 w-full" />
                          ))}
                        </div>
                      )}

                      {tablesError && (
                        <ErrorCard
                          message={tablesErrorObj?.message ?? 'Failed to fetch tables'}
                          onRetry={() => refetchTables()}
                        />
                      )}

                      {!tablesLoading && !tablesError && filteredTables.length === 0 && (
                        <p className="text-xs text-muted-foreground py-2 px-3">
                          No tables found
                        </p>
                      )}

                      {!tablesLoading &&
                        !tablesError &&
                        filteredTables.map((table) => (
                          <TableItem
                            key={`${table.schemaName}.${table.tableName}`}
                            table={table}
                            isSelected={
                              selectedTable?.schema === table.schemaName &&
                              selectedTable?.table === table.tableName
                            }
                            onSelect={() =>
                              handleTableSelect(table.schemaName, table.tableName)
                            }
                          />
                        ))}
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>

        {/* Right panel: column details */}
        <div className="flex-1 border rounded-lg p-4 overflow-auto">
          {selectedTable ? (
            <ColumnPanel schema={selectedTable.schema} tableName={selectedTable.table} fdwSource={fdwSource} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <Table2 className="h-10 w-10 mb-3 opacity-50" />
              <p className="text-sm">Select a table to view column details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default FdwExplorer;
