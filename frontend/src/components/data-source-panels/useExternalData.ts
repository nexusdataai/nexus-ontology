import { useState, useEffect, useCallback } from 'react';
import { fdwService } from '@/services/fdwService';

const SCHEMA = 'external_sources';

export function useExternalData(tableName: string, limit = 200) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fdwService.executeQuery(
        { table: tableName, schemaName: SCHEMA, limit, offset: 0 },
        'external',
      );
      setRows(result.rows || []);
      setTotal(result.metadata?.rowCount ?? (result.rows || []).length);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
      setRows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [tableName, limit]);

  useEffect(() => { refresh(); }, [refresh]);

  return { data: { rows, total }, loading, error, refresh, rows, total };
}
