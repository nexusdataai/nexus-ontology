// --- FDW Discovery Types ---

export interface ForeignServerInfo {
  serverName: string;
  wrapperType: string;
  serverOptions: Record<string, string>;
}

export interface ForeignTableInfo {
  schemaName: string;
  tableName: string;
  serverName: string;
  columnCount: number;
}

export interface ColumnInfo {
  columnName: string;
  dataType: string;
  isNullable: boolean;
  ordinalPosition: number;
}

// --- FDW Query Types ---

export type FilterOperator = 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'like' | 'in';

export interface QueryFilter {
  column: string;
  operator: FilterOperator;
  value: string | number | boolean | Array<string | number>;
}

export interface OrderByItem {
  column: string;
  direction: 'asc' | 'desc';
}

export interface QueryRequest {
  table: string;
  schemaName: string;
  filters?: QueryFilter[];
  columns?: string[];
  limit?: number;
  offset?: number;
  orderBy?: OrderByItem[];
}

export interface QueryMetadata {
  durationMs: number;
  tableQueried: string;
  rowCount: number;
}

export interface QueryResponse {
  rows: Record<string, any>[];
  metadata: QueryMetadata;
}

// --- Health Types ---

export interface FdwHealthResponse {
  status: string;
  latencyMs?: number;
  foreignServersCount?: number;
  foreignTablesCount?: number;
  error?: string;
}
