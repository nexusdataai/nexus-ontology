/**
 * JourneyListView Component
 * 
 * Displays a list of journeys with filtering and search capabilities.
 * 
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.7
 */

import React, { useState, useMemo } from 'react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Plus, Search, RefreshCw, Loader2 } from 'lucide-react';
import { JourneyCard } from './JourneyCard';
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
}

const STATUS_OPTIONS: { value: JourneyStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Statuses' },
  { value: 'created', label: 'Created' },
  { value: 'running', label: 'Running' },
  { value: 'paused', label: 'Paused' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
];

const TYPE_OPTIONS: { value: JourneyType | 'all'; label: string }[] = [
  { value: 'all', label: 'All Types' },
  { value: 'call-processing', label: 'Call Processing' },
  { value: 'operation-management', label: 'Operation Management' },
  { value: 'demand-forecasting', label: 'Demand Forecasting' },
  { value: 'inventory-optimization', label: 'Inventory Optimization' },
  { value: 'procurement-analytics', label: 'Procurement Analytics' },
  { value: 'production-quality', label: 'Production & Quality' },
  { value: 'supply-chain-risk', label: 'Supply Chain Risk' },
  { value: 'customer-360', label: 'Customer 360' },
  { value: 'esg-sustainability', label: 'ESG & Sustainability' },
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

  return (
    <div className="h-full flex flex-col" data-testid="journey-list-view">
      {/* Header with filters */}
      <div className="p-4 border-b space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Journeys</h2>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
              data-testid="refresh-button"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
            <Button
              onClick={onCreateSemanticRag}
              size="sm"
              variant="outline"
              data-testid="create-semantic-rag-button"
            >
              <Plus className="h-4 w-4 mr-1" />
              New Semantic RAG Journey
            </Button>
            <Button
              onClick={onCreateO2C}
              size="sm"
              variant="outline"
            >
              <Plus className="h-4 w-4 mr-1" />
              New O2C Journey
            </Button>
            <Button
              onClick={onCreateDemandForecasting}
              size="sm"
              variant="outline"
              data-testid="create-demand-forecasting-button"
            >
              <Plus className="h-4 w-4 mr-1" />
              New Demand Forecasting Journey
            </Button>
            <Button
              onClick={onCreateInventoryOpt}
              size="sm"
              variant="outline"
              data-testid="create-inventory-opt-button"
            >
              <Plus className="h-4 w-4 mr-1" />
              New Inventory Optimization
            </Button>
            <Button
              onClick={onCreateProcurement}
              size="sm"
              variant="outline"
              data-testid="create-procurement-button"
            >
              <Plus className="h-4 w-4 mr-1" />
              New Procurement Journey
            </Button>
            <Button
              onClick={onCreateProductionQuality}
              size="sm"
              variant="outline"
              data-testid="create-production-quality-button"
            >
              <Plus className="h-4 w-4 mr-1" />
              New Production & Quality
            </Button>
            <Button
              onClick={onCreateSupplyChainRisk}
              size="sm"
              variant="outline"
              data-testid="create-supply-chain-risk-button"
            >
              <Plus className="h-4 w-4 mr-1" />
              New Supply Chain Risk
            </Button>
            <Button
              onClick={onCreateCustomer360}
              size="sm"
              variant="outline"
              data-testid="create-customer-360-button"
            >
              <Plus className="h-4 w-4 mr-1" />
              New Customer 360
            </Button>
            <Button
              onClick={onCreateESG}
              size="sm"
              variant="outline"
              data-testid="create-esg-button"
            >
              <Plus className="h-4 w-4 mr-1" />
              New ESG & Sustainability
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search journeys..."
              value={filter.searchQuery || ''}
              onChange={handleSearchChange}
              className="pl-9"
              data-testid="search-input"
            />
          </div>

          <Select
            value={filter.statusFilter || 'all'}
            onValueChange={handleStatusChange}
          >
            <SelectTrigger className="w-[160px]" data-testid="status-filter">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map(option => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={filter.typeFilter || 'all'}
            onValueChange={handleTypeChange}
          >
            <SelectTrigger className="w-[180px]" data-testid="type-filter">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              {TYPE_OPTIONS.map(option => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Journey List */}
      <div className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filteredJourneys.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center h-full text-muted-foreground"
            data-testid="empty-state"
          >
            <p className="text-lg">No journeys found</p>
            <p className="text-sm">
              {journeys.length === 0
                ? 'Create your first journey to get started'
                : 'Try adjusting your filters'}
            </p>
          </div>
        ) : (
          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            data-testid="journey-grid"
          >
            {filteredJourneys.map(journey => (
              <JourneyCard
                key={journey.id}
                journey={journey}
                onViewStudio={onSelectJourney}
                onDelete={onDelete}
                isActionLoading={actionLoadingId === journey.id}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer with count */}
      <div className="p-4 border-t text-sm text-muted-foreground">
        Showing {filteredJourneys.length} of {journeys.length} journeys
      </div>
    </div>
  );
}

export default JourneyListView;
