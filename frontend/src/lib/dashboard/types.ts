export type FieldType = 'number' | 'string' | 'time' | 'boolean';

export interface FieldConfig {
  unit?: string;
  decimals?: number;
  min?: number;
  max?: number;
  thresholds?: Threshold[];
  color?: string;
  displayName?: string;
}

export interface Threshold {
  value: number;
  color: string;
}

export interface DataField {
  name: string;
  type: FieldType;
  values: unknown[];
  config?: FieldConfig;
}

export interface DataFrame {
  name: string;
  fields: DataField[];
  length: number;
}

export interface TimeRange {
  from: string;
  to: string;
  raw?: { from: string; to: string };
}

export interface ScopedVar {
  text: string;
  value: string | number;
}

export interface QueryFilter {
  field: string;
  operator: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains' | 'in';
  value: unknown;
}

export interface AggregationConfig {
  function: 'count' | 'sum' | 'avg' | 'min' | 'max';
  field?: string;
}

export interface PanelQuery {
  refId: string;
  entity: string;
  fields?: string[];
  filters?: QueryFilter[];
  aggregation?: AggregationConfig;
  groupBy?: string[];
  orderBy?: string;
  limit?: number;
  hide?: boolean;
}

export interface DashboardQueryRequest {
  queries: PanelQuery[];
  timeRange?: TimeRange;
  scopedVars?: Record<string, ScopedVar>;
}

export interface QueryResult {
  frames: DataFrame[];
  error?: string;
}

export interface DashboardQueryResponse {
  results: Record<string, QueryResult>;
}

export interface FieldDescriptor {
  name: string;
  type: FieldType;
  sampleValues?: unknown[];
}

export interface VirtualEntitySummary {
  virtual_entity: string;
  source_count: number;
  active_rules: number;
  sources: {
    source_system: string;
    source_table: string;
    source_type: string;
    status: string;
  }[];
}

export type LoadingState = 'idle' | 'loading' | 'done' | 'error' | 'streaming';

export interface PanelData {
  state: LoadingState;
  frames: DataFrame[];
  error?: string;
  timeRange?: TimeRange;
}

export function rowsToDataFrame(
  name: string,
  rows: Record<string, unknown>[],
): DataFrame {
  if (rows.length === 0) {
    return { name, fields: [], length: 0 };
  }

  const keys = Object.keys(rows[0]);
  const fields: DataField[] = keys.map((key) => {
    const values = rows.map((r) => r[key]);
    const type = inferFieldType(values);
    return { name: key, type, values };
  });

  return { name, fields, length: rows.length };
}

export function dataFrameToRows(frame: DataFrame): Record<string, unknown>[] {
  const rows: Record<string, unknown>[] = [];
  for (let i = 0; i < frame.length; i++) {
    const row: Record<string, unknown> = {};
    for (const field of frame.fields) {
      row[field.name] = field.values[i];
    }
    rows.push(row);
  }
  return rows;
}

export function getFieldByName(frame: DataFrame, name: string): DataField | undefined {
  return frame.fields.find((f) => f.name === name);
}

function inferFieldType(values: unknown[]): FieldType {
  for (const v of values) {
    if (v == null) continue;
    if (typeof v === 'number') return 'number';
    if (typeof v === 'boolean') return 'boolean';
    if (typeof v === 'string') {
      if (/^\d{4}-\d{2}-\d{2}/.test(v)) return 'time';
      const num = Number(v);
      if (!isNaN(num) && v.trim() !== '') return 'number';
    }
    return 'string';
  }
  return 'string';
}
