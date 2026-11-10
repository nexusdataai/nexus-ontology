/**
 * Query tab of the runtime explorer: a read-query editor over one table.
 */

import { FdwQueryMode, type QueryTableRef } from './FdwQueryMode';

interface QueryBuilderProps {
  fdwSource?: string;
  /** Table to start on when nothing has been chosen yet. */
  defaultTable?: QueryTableRef | null;
  /** Explicit "query this table" request; a new nonce re-applies it. */
  target?: (QueryTableRef & { nonce: number }) | null;
}

export function QueryBuilder({ fdwSource, defaultTable, target }: QueryBuilderProps) {
  return (
    <div className="h-full min-h-0" data-testid="query-builder">
      <FdwQueryMode fdwSource={fdwSource} defaultTable={defaultTable} target={target} />
    </div>
  );
}

export default QueryBuilder;
