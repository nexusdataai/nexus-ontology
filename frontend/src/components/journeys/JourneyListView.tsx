/**
 * JourneyListView Component
 * 
 * The journeys collection: a toolbar (search, status chips, type, refresh,
 * new journey) and one row per journey. Rows open the Journey Studio.
 * 
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.7
 */

import React, { useState, useMemo } from 'react';
import { Button } from '../ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { Skeleton } from '../ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { Chips, InlineError, SearchInput, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { JourneyCard, JOURNEY_ROW_GRID } from './JourneyCard';
import {
  CallProcessingJourney,
  JourneyStatus,
  JourneyType,
  JourneyFilter,
} from '../../types/callProcessingJourney';
import { filterJourneys } from '../../utils/journeyUtils';

export interface JourneyListViewProps {
  journeys: CallProcessingJourney[];
  isLoading?: boolean;
  onSelectJourney: (journeyId: string) => void;
  onCreateSemanticRag?: () => void;
  onCreateO2C?: () => void;
  onCreateDemandForecasting?: () => void;
  onCreateInventoryOpt?: () => void;
  onCreateProcurement?: () => void;
  onCreateProductionQuality?: () => void;
  onCreateSupplyChainRisk?: () => void;
  onCreateCustomer360?: () => void;
  onCreateESG?: () => void;
  onDelete: (journeyId: string) => void;
  onRefresh: () => void;
  actionLoadingId?: string | null;
  /** The last load failed (the list shows an error with a retry). */
  error?: boolean;
}

const STATUS_OPTIONS: { value: JourneyStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'created', label: 'Not run yet' },
  { value: 'running', label: 'Running' },
  { value: 'paused', label: 'Paused' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
];

const TYPE_OPTIONS: { value: JourneyType | 'all'; label: string }[] = [
  { value: 'all', label: 'All types' },
  { value: 'call-processing', label: 'Call processing' },
  { value: 'operation-management', label: 'Operation management' },
  { value: 'demand-forecasting', label: 'Demand forecasting' },
  { value: 'inventory-optimization', label: 'Inventory optimization' },
  { value: 'procurement-analytics', label: 'Procurement analytics' },
  { value: 'production-quality', label: 'Production and quality' },
  { value: 'supply-chain-risk', label: 'Supply chain risk' },
  { value: 'customer-360', label: 'Customer 360' },
  { value: 'esg-sustainability', label: 'ESG and sustainability' },
];

export function JourneyListView({
  journeys,
  isLoading = false,
  onSelectJourney,
  onCreateSemanticRag,
  onCreateO2C,
  onCreateDemandForecasting,
  onCreateInventoryOpt,
  onCreateProcurement,
  onCreateProductionQuality,
  onCreateSupplyChainRisk,
  onCreateCustomer360,
  onCreateESG,
  onDelete,
  onRefresh,
  actionLoadingId,
  error = false,
}: JourneyListViewProps) {
  const [filter, setFilter] = useState<JourneyFilter>({});

  const filteredJourneys = useMemo(() => {
    return filterJourneys(journeys, filter);
  }, [journeys, filter]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilter(prev => ({
      ...prev,
      searchQuery: e.target.value || undefined,
    }));
  };

  const handleStatusChange = (value: string) => {
    setFilter(prev => ({
      ...prev,
      statusFilter: value === 'all' ? undefined : (value as JourneyStatus),
    }));
  };

  const handleTypeChange = (value: string) => {
    setFilter(prev => ({
      ...prev,
      typeFilter: value === 'all' ? undefined : (value as JourneyType),
    }));
  };

  // Presentation only: counts per status for the filter chips.
  const statusCounts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const j of journeys) c[j.status] = (c[j.status] || 0) + 1;
    return c;
  }, [journeys]);
  const activeStatus = (filter.statusFilter || 'all') as JourneyStatus | 'all';
  const statusChips = STATUS_OPTIONS
    .filter(o => o.value === 'all' || o.value === activeStatus || (statusCounts[o.value] || 0) > 0)
    .map(o => ({ value: o.value, label: o.label, count: o.value === 'all' ? journeys.length : statusCounts[o.value] || 0 }));
  const hasFilter = !!(filter.searchQuery || filter.statusFilter || filter.typeFilter);
  const runningCount = statusCounts.running || 0;
  const failedCount = statusCounts.failed || 0;

  return (
    <div className="page" data-testid="journey-list-view">
      <Toolbar>
        <div data-testid="search-input-wrap" className="w-full sm:w-auto">
          <SearchInput
            value={filter.searchQuery || ''}
            onChange={(v) => handleSearchChange({ target: { value: v } } as React.ChangeEvent<HTMLInputElement>)}
            placeholder="Search journeys"
            data-testid="search-input"
          />
        </div>
        <div data-testid="status-filter" className="min-w-0">
          <Chips label="Status" options={statusChips} value={activeStatus} onChange={handleStatusChange} />
        </div>
        <ToolbarSpacer />
        <Select value={filter.typeFilter || 'all'} onValueChange={handleTypeChange}>
          <SelectTrigger className="h-8 w-[180px]" data-testid="type-filter" aria-label="Type">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            {TYPE_OPTIONS.map(option => (
              <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading} data-testid="refresh-button">
          <Icon name="refresh" className={isLoading ? 'animate-spin' : undefined} /> Refresh
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button size="sm" data-testid="create-journey-button">
              <Icon name="plus" /> New journey <Icon name="chevron-down" className="-mr-1 h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">Choose a journey type</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onCreateSemanticRag} data-testid="create-semantic-rag-button">Knowledge pipeline (Semantic RAG)</DropdownMenuItem>
            <DropdownMenuItem onClick={onCreateO2C}>Order-to-Cash</DropdownMenuItem>
            <DropdownMenuItem onClick={onCreateDemandForecasting} data-testid="create-demand-forecasting-button">Demand forecasting</DropdownMenuItem>
            <DropdownMenuItem onClick={onCreateInventoryOpt} data-testid="create-inventory-opt-button">Inventory optimization</DropdownMenuItem>
            <DropdownMenuItem onClick={onCreateProcurement} data-testid="create-procurement-button">Procurement</DropdownMenuItem>
            <DropdownMenuItem onClick={onCreateProductionQuality} data-testid="create-production-quality-button">Production and quality</DropdownMenuItem>
            <DropdownMenuItem onClick={onCreateSupplyChainRisk} data-testid="create-supply-chain-risk-button">Supply chain risk</DropdownMenuItem>
            <DropdownMenuItem onClick={onCreateCustomer360} data-testid="create-customer-360-button">Customer 360</DropdownMenuItem>
            <DropdownMenuItem onClick={onCreateESG} data-testid="create-esg-button">ESG and sustainability</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </Toolbar>

      <p className="mt-3 text-sm text-muted-foreground" aria-live="polite">
        {isLoading && journeys.length === 0 ? 'Loading journeys' : (
          <>
            <span className="num text-foreground">{filteredJourneys.length}</span>
            {hasFilter ? <> of <span className="num">{journeys.length}</span></> : null} {journeys.length === 1 && !hasFilter ? 'journey' : 'journeys'}
            {!hasFilter && runningCount > 0 ? <>, <span className="num">{runningCount}</span> running now</> : null}
            {!hasFilter && failedCount > 0 ? <>, <span className="num text-destructive">{failedCount}</span> failed on the last run</> : null}
          </>
        )}
      </p>

      <div className="mt-4">
        {error ? (
          <InlineError onRetry={onRefresh}>The journeys could not be loaded.</InlineError>
        ) : isLoading && journeys.length === 0 ? (
          <div className="overflow-hidden rounded-xl border border-border bg-card">
            {[0, 1, 2, 3, 4].map(i => (
              <div key={i} className="flex items-center gap-6 border-b border-border px-5 py-4 last:border-b-0">
                <div className="min-w-0 flex-1 space-y-2"><Skeleton className="h-4 w-56 max-w-full" /><Skeleton className="h-3 w-80 max-w-full" /></div>
                <Skeleton className="hidden h-2 w-40 lg:block" />
                <Skeleton className="hidden h-4 w-24 lg:block" />
              </div>
            ))}
          </div>
        ) : filteredJourneys.length === 0 ? (
          <div data-testid="empty-state">
            <EmptyState
              icon="route"
              title={journeys.length === 0 ? 'No journeys yet' : 'No journeys match'}
              description={journeys.length === 0 ? 'Create your first journey to automate a business process.' : 'Try another search, or clear the filters.'}
              action={hasFilter ? <Button variant="outline" size="sm" onClick={() => setFilter({})}>Clear filters</Button> : undefined}
            />
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
            <div className={cn('hidden border-b border-border bg-surface-2 px-5 py-2 text-xs font-medium text-muted-foreground', JOURNEY_ROW_GRID)} aria-hidden="true">
              <span>Journey</span>
              <span>Progress</span>
              <span>Runs</span>
              <span>Status</span>
              <span />
            </div>
            <div className="divide-y divide-border" data-testid="journey-grid">
              {filteredJourneys.map((journey, i) => (
                <JourneyCard
                  key={journey.id}
                  journey={journey}
                  index={i}
                  onViewStudio={onSelectJourney}
                  onDelete={onDelete}
                  isActionLoading={actionLoadingId === journey.id}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default JourneyListView;
