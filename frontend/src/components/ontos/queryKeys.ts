export const ontosKeys = {
  health: ['fdw', 'health'] as const,
  servers: ['fdw', 'servers'] as const,
  tables: (server?: string) => ['fdw', 'tables', server] as const,
  columns: (schema: string, table: string) => ['fdw', 'columns', schema, table] as const,
};
