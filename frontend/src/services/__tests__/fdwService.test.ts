/**
 * FDW Service Unit Tests
 *
 * Tests that each fdwService function calls apiClient with the correct endpoint
 * and that errors propagate correctly.
 *
 * Requirements: 9.1, 9.2, 9.3, 9.4
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fdwService } from '../fdwService';
import apiClient from '../apiClient';

vi.mock('../apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('fdwService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getHealth', () => {
    it('calls apiClient.get with /health/fdw', async () => {
      const mockResponse = { status: 'healthy', latencyMs: 12, foreignServersCount: 2, foreignTablesCount: 5 };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await fdwService.getHealth();

      expect(apiClient.get).toHaveBeenCalledWith('/health/fdw');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('listServers', () => {
    it('calls apiClient.get with /api/fdw/servers', async () => {
      const mockServers = [{ serverName: 'pg_remote', wrapperType: 'postgres_fdw', serverOptions: {} }];
      vi.mocked(apiClient.get).mockResolvedValue(mockServers);

      const result = await fdwService.listServers();

      expect(apiClient.get).toHaveBeenCalledWith('/api/fdw/servers');
      expect(result).toEqual(mockServers);
    });
  });

  describe('listTables', () => {
    it('calls apiClient.get with /api/fdw/tables when no server filter', async () => {
      const mockTables = [{ schemaName: 'public', tableName: 'users', serverName: 'pg_remote', columnCount: 4 }];
      vi.mocked(apiClient.get).mockResolvedValue(mockTables);

      const result = await fdwService.listTables();

      expect(apiClient.get).toHaveBeenCalledWith('/api/fdw/tables');
      expect(result).toEqual(mockTables);
    });

    it('calls apiClient.get with server query param when server is provided', async () => {
      vi.mocked(apiClient.get).mockResolvedValue([]);

      await fdwService.listTables('pg_remote');

      expect(apiClient.get).toHaveBeenCalledWith('/api/fdw/tables?server=pg_remote');
    });

    it('encodes special characters in server name', async () => {
      vi.mocked(apiClient.get).mockResolvedValue([]);

      await fdwService.listTables('server with spaces');

      expect(apiClient.get).toHaveBeenCalledWith('/api/fdw/tables?server=server%20with%20spaces');
    });
  });

  describe('getColumns', () => {
    it('calls apiClient.get with correct schema/table path', async () => {
      const mockColumns = [{ columnName: 'id', dataType: 'integer', isNullable: false, ordinalPosition: 1 }];
      vi.mocked(apiClient.get).mockResolvedValue(mockColumns);

      const result = await fdwService.getColumns('public', 'users');

      expect(apiClient.get).toHaveBeenCalledWith('/api/fdw/tables/public/users/columns');
      expect(result).toEqual(mockColumns);
    });

    it('encodes special characters in schema and table names', async () => {
      vi.mocked(apiClient.get).mockResolvedValue([]);

      await fdwService.getColumns('my schema', 'my table');

      expect(apiClient.get).toHaveBeenCalledWith('/api/fdw/tables/my%20schema/my%20table/columns');
    });
  });

  describe('executeQuery', () => {
    it('calls apiClient.post with /api/fdw/query and request body', async () => {
      const request = { table: 'users', schemaName: 'public', columns: ['id', 'name'], limit: 10 };
      const mockResponse = { rows: [{ id: 1, name: 'Alice' }], metadata: { durationMs: 42, tableQueried: 'users', rowCount: 1 } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await fdwService.executeQuery(request);

      expect(apiClient.post).toHaveBeenCalledWith('/api/fdw/query', request);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('error propagation', () => {
    it('propagates errors from apiClient', async () => {
      const error = new Error('Network error');
      vi.mocked(apiClient.get).mockRejectedValue(error);

      await expect(fdwService.getHealth()).rejects.toThrow('Network error');
    });

    it('propagates ApiError with status from apiClient', async () => {
      const apiError = Object.assign(new Error('Not Found'), { status: 404, statusText: 'Not Found' });
      vi.mocked(apiClient.get).mockRejectedValue(apiError);

      await expect(fdwService.listServers()).rejects.toThrow('Not Found');
    });
  });
});
