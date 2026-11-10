/**
 * Source overview strip
 *
 * One quiet line of facts about the source shown above the Tables / Query
 * tabs: connection state, schema, server, table count and how many tables are
 * mapped to a virtual entity. It replaces the former dashboard tab.
 *
 * Simulator sources read the table list; a real source reads the FDW health
 * endpoint (same calls as before, now shared through the query cache).
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { InlineError, StatusPill } from '@/components/ds/kit';
import { fdwService } from '@/services/fdwService';
import { ontosKeys } from './queryKeys';
import type { FdwHealthResponse, ForeignServerInfo, ForeignTableInfo } from '@/types/fdwTypes';

interface OntosDashboardProps {
  fdwSource?: string;
  /** Tables of this source bound to a virtual entity. Omit while unknown. */
  mappedCount?: number;
  className?: string;
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex min-w-0 items-baseline gap-1.5 whitespace-nowrap">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 truncate text-foreground">{children}</dd>
    </div>
  );
}

export function OntosDashboard({ fdwSource, mappedCount, className }: OntosDashboardProps) {
  const queryClient = useQueryClient();
  const isSimulated = !!fdwSource && fdwSource !== 'real';

  const tablesQuery = useQuery<ForeignTableInfo[]>({
    queryKey: [...ontosKeys.tables(), fdwSource],
    queryFn: () => fdwService.listTables(undefined, fdwSource),
    enabled: isSimulated,
    staleTime: 300000,
  });

  const healthQuery = useQuery<FdwHealthResponse>({
    queryKey: [...ontosKeys.health],
    queryFn: () => fdwService.getHealth(),
    enabled: !isSimulated,
    staleTime: 60000,
  });

  const serversQuery = useQuery<ForeignServerInfo[]>({
    queryKey: [...ontosKeys.servers, fdwSource],
    queryFn: () => fdwService.listServers(fdwSource),
    staleTime: 300000,
  });

  const main = isSimulated ? tablesQuery : healthQuery;
  const refreshing = tablesQuery.isFetching || healthQuery.isFetching || serversQuery.isFetching;
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['fdw'] });

  if (main.isLoading) {
    return (
      <div className={className} data-testid="dashboard-skeleton" aria-busy="true">
        <Skeleton className="h-5 w-72 max-w-full" />
      </div>
    );
  }

  if (main.isError) {
    return (
      <InlineError className={className} onRetry={() => main.refetch()}>
        {(main.error as Error)?.message || 'Could not load the status of this source.'}
      </InlineError>
    );
  }

  const tables = tablesQuery.data ?? [];
  const servers = serversQuery.data ?? [];
  const schemas = [...new Set(tables.map(t => t.schemaName))];
  const health = healthQuery.data;
  const healthy = health?.status === 'healthy';

  const tableCount = isSimulated ? tables.length : health?.foreignTablesCount;
  const serverCount = isSimulated ? servers.length : health?.foreignServersCount ?? servers.length;

  return (
    <dl className={`flex flex-wrap items-center gap-x-5 gap-y-1.5 text-sm ${className ?? ''}`} data-testid="source-overview">
      <div className="flex items-center">
        <dt className="sr-only">Status</dt>
        <dd>
          {isSimulated ? (
            <StatusPill tone={tables.length > 0 ? 'success' : 'warning'}>
              {tables.length > 0 ? 'Connected' : 'No tables loaded'}
            </StatusPill>
          ) : (
            <StatusPill tone={!healthy ? 'danger' : serverCount === 0 ? 'warning' : 'success'}>
              {!healthy ? health?.error || 'Connection problem' : serverCount === 0 ? 'No server set up' : 'Connected'}
            </StatusPill>
          )}
        </dd>
      </div>

      {schemas.length === 1 && <Fact label="Schema"><span className="font-mono text-xs">{schemas[0]}</span></Fact>}
      {schemas.length > 1 && <Fact label="Schemas"><span className="num">{schemas.length}</span></Fact>}

      {servers.length === 1
        ? <Fact label="Server"><span className="font-mono text-xs">{servers[0].serverName}</span></Fact>
        : serverCount != null && <Fact label="Servers"><span className="num">{serverCount.toLocaleString()}</span></Fact>}

      {tableCount != null && <Fact label="Tables"><span className="num">{tableCount.toLocaleString()}</span></Fact>}

      {mappedCount != null && !!tableCount && (
        <Fact label="Mapped to entities"><span className="num">{mappedCount.toLocaleString()}</span></Fact>
      )}

      {!isSimulated && health?.latencyMs != null && (
        <Fact label="Response time"><span className="num">{health.latencyMs}</span> ms</Fact>
      )}

      <Button variant="ghost" size="icon-sm" onClick={refresh} aria-label="Refresh source details" title="Refresh" data-testid="refresh-button" className="-my-1">
        <Icon name="refresh" className={refreshing ? 'animate-spin' : undefined} />
      </Button>
    </dl>
  );
}

export default OntosDashboard;
