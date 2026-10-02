/**
 * Query Builder Component
 *
 * FDW query interface for building and executing raw queries against foreign tables.
 */

import { Database } from 'lucide-react';
import { FdwQueryMode } from './FdwQueryMode';

export function QueryBuilder({ fdwSource }: { fdwSource?: string }) {
  return (
    <div className="h-full flex flex-col p-6" data-testid="query-builder">
      <div className="flex items-center gap-2 mb-4">
        <Database className="h-4 w-4" />
        <h3 className="text-sm font-medium">FDW Query Builder</h3>
      </div>
      <div className="flex-1">
        <FdwQueryMode fdwSource={fdwSource} />
      </div>
    </div>
  );
}

export default QueryBuilder;
