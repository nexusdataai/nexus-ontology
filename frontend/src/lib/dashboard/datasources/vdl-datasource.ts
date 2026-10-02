import { apiClient } from '@/services/apiClient';
import type { DataSourceApi } from './datasource-api';
import type {
  DashboardQueryRequest,
  DashboardQueryResponse,
  FieldDescriptor,
  FieldType,
  VirtualEntitySummary,
  DataFrame,
  PanelQuery,
} from '../types';
import { rowsToDataFrame } from '../types';

interface BackendQueryResult {
  ref_id: string;
  rows: Record<string, unknown>[];
  total: number;
  source?: string;
  error?: string;
}

interface BackendBatchResponse {
  results: Record<string, BackendQueryResult>;
}

export class VDLDataSource implements DataSourceApi {
  uid = 'vdl-default';
  type = 'vdl';
  name = 'Virtual Data Layer';

  async query(request: DashboardQueryRequest): Promise<DashboardQueryResponse> {
    const activeQueries = request.queries.filter((q) => !q.hide && q.entity);

    if (activeQueries.length === 0) {
      return { results: {} };
    }

    const payload = {
      queries: activeQueries.map((q) => ({
        ref_id: q.refId,
        entity: q.entity,
        fields: q.fields?.length ? q.fields : undefined,
        filters: q.filters?.map((f) => ({
          field: f.field,
          operator: f.operator,
          value: f.value,
        })),
        aggregation: q.aggregation
          ? { function: q.aggregation.function, field: q.aggregation.field }
          : undefined,
        group_by: q.groupBy?.length ? q.groupBy : undefined,
        order_by: q.orderBy || undefined,
        limit: q.limit ?? 100,
      })),
      time_range: request.timeRange
        ? { from: request.timeRange.from, to: request.timeRange.to }
        : undefined,
    };

    try {
      const resp = await apiClient.post<BackendBatchResponse>(
        '/api/v1/dashboard/query',
        payload,
      );

      const results: DashboardQueryResponse['results'] = {};
      for (const [refId, result] of Object.entries(resp.results)) {
        if (result.error) {
          results[refId] = { frames: [], error: result.error };
        } else {
          const frame = rowsToDataFrame(result.ref_id || refId, result.rows || []);
          results[refId] = { frames: [frame] };
        }
      }
      return { results };
    } catch (err) {
      return this.fallbackSingleQueries(activeQueries);
    }
  }

  private async fallbackSingleQueries(
    queries: PanelQuery[],
  ): Promise<DashboardQueryResponse> {
    const results: DashboardQueryResponse['results'] = {};

    await Promise.all(
      queries.map(async (q) => {
        try {
          const resp = await apiClient.post<{
            rows: Record<string, unknown>[];
            total: number;
            error?: string;
          }>('/api/v1/control-plane/virtual/query', {
            virtualEntity: q.entity,
            fields: q.fields?.length ? q.fields : undefined,
            filters: q.filters?.map((f) => ({
              field: f.field,
              operator: f.operator,
              value: f.value,
            })),
            limit: q.limit ?? 100,
          });

          if (resp.error) {
            results[q.refId] = { frames: [], error: resp.error };
          } else {
            let rows = resp.rows || [];

            if (q.aggregation && q.groupBy?.length) {
              rows = aggregateRows(rows, q.aggregation, q.groupBy);
            }
            if (q.orderBy) {
              rows = sortRows(rows, q.orderBy);
            }
            if (q.limit && rows.length > q.limit) {
              rows = rows.slice(0, q.limit);
            }

            const frame = rowsToDataFrame(q.refId, rows);
            results[q.refId] = { frames: [frame] };
          }
        } catch (e) {
          results[q.refId] = {
            frames: [],
            error: e instanceof Error ? e.message : 'Query failed',
          };
        }
      }),
    );

    return { results };
  }

  async testConnection(): Promise<{ status: 'success' | 'error'; message: string }> {
    try {
      const entities = await this.getEntities();
      return {
        status: 'success',
        message: `Connected. ${entities.length} virtual entities available.`,
      };
    } catch (e) {
      return {
        status: 'error',
        message: e instanceof Error ? e.message : 'Connection failed',
      };
    }
  }

  async getEntities(): Promise<VirtualEntitySummary[]> {
    return apiClient.get<VirtualEntitySummary[]>(
      '/api/v1/control-plane/virtual/entities',
    );
  }

  async getEntityFields(entity: string): Promise<FieldDescriptor[]> {
    try {
      const resp = await apiClient.get<{ fields: FieldDescriptor[] }>(
        `/api/v1/dashboard/datasource/vdl/entities/${encodeURIComponent(entity)}/fields`,
      );
      return resp.fields;
    } catch {
      return this.inferFieldsFromPreview(entity);
    }
  }

  private async inferFieldsFromPreview(entity: string): Promise<FieldDescriptor[]> {
    try {
      const resp = await apiClient.get<{
        rows: Record<string, unknown>[];
      }>(
        `/api/v1/control-plane/virtual/entities/${encodeURIComponent(entity)}/preview?limit=5`,
      );

      if (!resp.rows?.length) return [];

      const keys = Object.keys(resp.rows[0]);
      return keys.map((key) => {
        const samples = resp.rows.map((r) => r[key]).filter((v) => v != null);
        const type = inferTypeFromSamples(samples);
        return { name: key, type, sampleValues: samples.slice(0, 3) };
      });
    } catch {
      return [];
    }
  }
}

function inferTypeFromSamples(samples: unknown[]): FieldType {
  for (const v of samples) {
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

function aggregateRows(
  rows: Record<string, unknown>[],
  agg: { function: string; field?: string },
  groupBy: string[],
): Record<string, unknown>[] {
  const groups: Record<string, Record<string, unknown>[]> = {};
  for (const row of rows) {
    const key = groupBy.map((g) => String(row[g] ?? 'unknown')).join('|');
    if (!groups[key]) groups[key] = [];
    groups[key].push(row);
  }

  const result: Record<string, unknown>[] = [];
  for (const [, groupRows] of Object.entries(groups)) {
    const out: Record<string, unknown> = {};
    for (const g of groupBy) {
      out[g] = groupRows[0][g];
    }

    const fn = agg.function.toLowerCase();
    if (fn === 'count') {
      out['value'] = groupRows.length;
    } else if (agg.field && (fn === 'sum' || fn === 'avg' || fn === 'min' || fn === 'max')) {
      const nums = groupRows
        .map((r) => Number(r[agg.field!]))
        .filter((n) => !isNaN(n));
      if (fn === 'sum') out['value'] = nums.reduce((a, b) => a + b, 0);
      else if (fn === 'avg') out['value'] = nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : 0;
      else if (fn === 'min') out['value'] = nums.length ? Math.min(...nums) : 0;
      else if (fn === 'max') out['value'] = nums.length ? Math.max(...nums) : 0;
    } else {
      out['value'] = groupRows.length;
    }

    result.push(out);
  }
  return result;
}

function sortRows(rows: Record<string, unknown>[], orderBy: string): Record<string, unknown>[] {
  const desc = /\s+desc$/i.test(orderBy);
  const field = orderBy.replace(/\s+(asc|desc)$/i, '').trim();
  return [...rows].sort((a, b) => {
    const av = a[field];
    const bv = b[field];
    const an = Number(av);
    const bn = Number(bv);
    if (!isNaN(an) && !isNaN(bn)) {
      return desc ? bn - an : an - bn;
    }
    const cmp = String(av ?? '').localeCompare(String(bv ?? ''));
    return desc ? -cmp : cmp;
  });
}

export interface NLQueryRequest {
  query: string;
  available_entities?: string[];
  current_entity?: string;
}

export interface NLQueryResponse {
  panel_query: {
    entity?: string;
    fields?: string[];
    filters?: Array<{ field: string; operator: string; value: unknown }>;
    aggregation?: { function: string; field?: string };
    groupBy?: string[];
    orderBy?: string;
    limit?: number;
  };
  suggested_panel_type: string;
  suggested_title: string;
  explanation: string;
  error?: string;
}

let _instance: VDLDataSource | null = null;

export function getVDLDataSource(): VDLDataSource {
  if (!_instance) {
    _instance = new VDLDataSource();
  }
  return _instance;
}

export async function nlQueryTranslate(request: NLQueryRequest): Promise<NLQueryResponse> {
  return apiClient.post<NLQueryResponse>('/api/v1/dashboard/nl-query', request);
}
