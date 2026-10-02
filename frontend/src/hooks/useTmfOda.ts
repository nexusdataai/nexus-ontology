import { useState, useEffect, useCallback } from 'react';
import tmfOdaService, { 
  TmfTable, 
  TmfRelationship, 
  FilteredDataset, 
  FilterOptions,
  TmfConsolidatedData,
  ApiEndpoint
} from '@/services/tmfOdaService';

interface UseTmfOdaState {
  // Data state
  isLoading: boolean;
  error: string | null;
  isDataLoaded: boolean;
  
  // Current dataset
  currentDataset: FilteredDataset | null;
  filteredEndpoints: ApiEndpoint[];
  
  // Filter state
  filterOptions: FilterOptions;
  
  // Metadata
  statistics: TmfConsolidatedData['statistics'] | null;
  tableCategories: string[];
  relationshipCategories: string[];
}

interface UseTmfOdaActions {
  // Data loading
  loadData: () => Promise<void>;
  refreshData: () => Promise<void>;
  
  // Filtering
  updateFilter: (newFilter: Partial<FilterOptions>) => void;
  resetFilters: () => void;
  
  // Category management
  toggleCategory: (category: string) => void;
  isCategoryIncluded: (category: string) => boolean;
}

export interface UseTmfOdaReturn extends UseTmfOdaState, UseTmfOdaActions {}

// Start with all categories selected
const defaultFilterOptions: FilterOptions = {
  searchFilter: '',
  includedCategories: new Set(['Core Entities', 'Support Entities', 'Events', 'Characteristics', 'Contact Information'])
};

export function useTmfOda(): UseTmfOdaReturn {
  // State management
  const [state, setState] = useState<UseTmfOdaState>({
    isLoading: false,
    error: null,
    isDataLoaded: false,
    currentDataset: null,
    filteredEndpoints: [],
    filterOptions: defaultFilterOptions,
    statistics: null,
    tableCategories: ['all'],
    relationshipCategories: ['all']
  });

  // Load data action
  const loadData = useCallback(async () => {
    if (state.isDataLoaded && tmfOdaService.isDataLoaded()) {
      return; // Already loaded
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      await tmfOdaService.loadData();
      
      // Get initial dataset and metadata
      const dataset = tmfOdaService.getFilteredDataset(defaultFilterOptions);
      const stats = tmfOdaService.getStatistics();
      const tableCategories = tmfOdaService.getTableCategories();
      const relationshipCategories = tmfOdaService.getRelationshipCategories();
      const endpoints = tmfOdaService.getFilteredEndpoints('');
      
      console.log(`📊 Dataset loaded: ${dataset.tables.length} tables, ${dataset.relationships.length} relationships`);

      setState(prev => ({
        ...prev,
        isLoading: false,
        isDataLoaded: true,
        currentDataset: dataset,
        filteredEndpoints: endpoints,
        statistics: stats,
        tableCategories,
        relationshipCategories
      }));

      console.log('✅ useTmfOda: Data loaded successfully');
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load data'
      }));
      console.error('❌ useTmfOda: Failed to load data:', error);
    }
  }, [state.isDataLoaded]);

  // Refresh data action
  const refreshData = useCallback(async () => {
    setState(prev => ({ ...prev, isDataLoaded: false }));
    await loadData();
  }, [loadData]);

  // Update filter action (simplified)
  const updateFilter = useCallback((newFilter: Partial<FilterOptions>) => {
    const updatedFilterOptions = { 
      ...state.filterOptions, 
      ...newFilter,
      // Ensure includedCategories is properly merged
      includedCategories: newFilter.includedCategories || state.filterOptions.includedCategories
    };
    
    try {
      const dataset = tmfOdaService.getFilteredDataset(updatedFilterOptions);
      const endpoints = tmfOdaService.getFilteredEndpoints(updatedFilterOptions.searchFilter);
      
      console.log(`🔍 useTmfOda: Filter update - categories: [${Array.from(updatedFilterOptions.includedCategories).join(', ')}]`);
      console.log(`🔍 useTmfOda: Filtered to ${dataset.tables.length} tables, ${dataset.relationships.length} relationships`);

      setState(prev => ({
        ...prev,
        filterOptions: updatedFilterOptions,
        currentDataset: dataset,
        filteredEndpoints: endpoints
      }));

      console.log(`✅ useTmfOda: ${dataset.tables.length} tables, ${dataset.relationships.length} relationships visible`);
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to apply filter'
      }));
    }
  }, [state.filterOptions]);

  // Reset filters action
  const resetFilters = useCallback(() => {
    updateFilter(defaultFilterOptions);
  }, [updateFilter]);

  // Category management actions
  const toggleCategory = useCallback((category: string) => {
    const newCategories = new Set(state.filterOptions.includedCategories);
    if (newCategories.has(category)) {
      newCategories.delete(category);
    } else {
      newCategories.add(category);
    }
    updateFilter({ includedCategories: newCategories });
  }, [state.filterOptions.includedCategories, updateFilter]);

  const isCategoryIncluded = useCallback((category: string): boolean => {
    return state.filterOptions.includedCategories.has(category);
  }, [state.filterOptions.includedCategories]);

  // Auto-load data on mount
  useEffect(() => {
    loadData();
  }, [loadData]);

  return {
    // State
    ...state,
    
    // Actions
    loadData,
    refreshData,
    updateFilter,
    resetFilters,
    toggleCategory,
    isCategoryIncluded
  };
}

export default useTmfOda; 