/**
 * Runtime explorer workspace for one source.
 *
 * - A bar with two tabs and the source overview (status, schema, server,
 *   tables, mapped tables).
 * - Tables: browse the tables the source exposes, their columns, a row
 *   preview and the virtual entity each table is mapped to.
 * - Query: build and run a read query against one table.
 *
 * The active tab lives in the URL (?tab=); `mode` and `source` are untouched.
 */

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';
import { useUrlTab } from '@/components/ds/PageTabs';
import type { IconName } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';
import { fdwService } from '@/services/fdwService';
import { mappingRuleService, type MappingRule } from '@/services/mappingRuleService';
import type { ForeignTableInfo } from '@/types/fdwTypes';
import { ontosKeys } from './queryKeys';
import { OntosDashboard } from './OntosDashboard';
import { FdwExplorer, buildMappingIndex, tableKey, type MappingInfo, type TableRef } from './FdwExplorer';
import { QueryBuilder } from './QueryBuilder';

// ============================================================================
// Types
// ============================================================================

export type OntosTabId = 'tables' | 'query';

export interface OntosTabConfig {
  id: OntosTabId;
  label: string;
  icon: IconName;
}

export interface OntosWorkspaceProps {
  prefillStandard?: string;
  prefillResource?: string;
  fdwSource?: string;
}

// ============================================================================
// Constants
// ============================================================================

export const ONTOS_TAB_CONFIGS: OntosTabConfig[] = [
  { id: 'tables', label: 'Tables', icon: 'table' },
  { id: 'query', label: 'Query', icon: 'terminal' },
];

// ============================================================================
// Component
// ============================================================================

export function OntosWorkspace({ fdwSource }: OntosWorkspaceProps) {
  const [urlTab, setTab] = useUrlTab('tables');
  const activeTab: OntosTabId = urlTab === 'query' ? 'query' : 'tables';

  // Table open in the Tables tab: the Query tab starts on the same one.
  const [currentTable, setCurrentTable] = useState<TableRef | null>(null);
  // "Query this table" from the Tables tab.
  const [queryTarget, setQueryTarget] = useState<(TableRef & { nonce: number }) | null>(null);

  const tablesQuery = useQuery<ForeignTableInfo[]>({
    queryKey: [...ontosKeys.tables(), fdwSource],
    queryFn: () => fdwService.listTables(undefined, fdwSource),
    staleTime: 300000,
  });

  // Read-only: which tables are bound to a virtual entity.
  const rulesQuery = useQuery<MappingRule[]>({
    queryKey: ['mapping-rules', 'all'],
    queryFn: () => mappingRuleService.list(),
    staleTime: 300000,
    retry: false,
  });

  const mapping: MappingInfo = useMemo(() => ({
    index: buildMappingIndex(rulesQuery.data ?? []),
    state: rulesQuery.isLoading ? 'loading' : rulesQuery.isError ? 'error' : 'ready',
    retry: () => { rulesQuery.refetch(); },
  }), [rulesQuery.data, rulesQuery.isLoading, rulesQuery.isError, rulesQuery.refetch]);

  const mappedCount = useMemo(() => {
    if (mapping.state !== 'ready' || !tablesQuery.data) return undefined;
    return tablesQuery.data.filter(t => mapping.index.has(tableKey(t.schemaName, t.tableName))).length;
  }, [mapping, tablesQuery.data]);

  const openInQuery = (ref: TableRef) => {
    setQueryTarget({ ...ref, nonce: Date.now() });
    setTab('query');
  };

  return (
    // The whole workspace is the full-height pane: the bar takes what it needs, the view gets the rest.
    <div className="flex h-pane min-h-0 min-w-0 flex-col" data-testid="ontos-workspace">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-x-6 border-b border-border px-4 pt-1 sm:px-6 lg:px-8">
        <Tabs value={activeTab} onValueChange={setTab} className="order-2 -mb-px w-full xl:order-1 xl:w-auto">
          <TabsList variant="line" className="w-auto border-b-0">
            {ONTOS_TAB_CONFIGS.map(tab => (
              <TabsTrigger key={tab.id} value={tab.id} data-testid={`ontos-tab-${tab.id}`}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <OntosDashboard fdwSource={fdwSource} mappedCount={mappedCount} className="order-1 py-1.5 xl:order-2" />
      </div>

      {/* Both views stay mounted so a built query and its results survive a tab switch. */}
      <div className="min-h-0 flex-1">
        <div className={cn('h-full min-h-0', activeTab !== 'tables' && 'hidden')} role="tabpanel" aria-label="Tables">
          <FdwExplorer
            fdwSource={fdwSource}
            mapping={mapping}
            onCurrentChange={setCurrentTable}
            onQueryTable={openInQuery}
          />
        </div>
        <div className={cn('h-full min-h-0', activeTab !== 'query' && 'hidden')} role="tabpanel" aria-label="Query">
          <QueryBuilder fdwSource={fdwSource} defaultTable={currentTable} target={queryTarget} />
        </div>
      </div>
    </div>
  );
}

export default OntosWorkspace;
