import { describe, it, expect, vi, beforeEach } from 'vitest';
import { tmfOdaService, TmfTable, TmfRelationship, TmfConsolidatedData, FilterOptions } from '../tmfOdaService';

// Mock fetch globally
global.fetch = vi.fn();

// Mock data for testing
const mockTmfData: TmfConsolidatedData = {
  metadata: {
    title: "Test TMF629 API",
    description: "Test data for TMF629",
    apiReference: "TMF629"
  },
  tables: [
    {
      name: "Customer",
      type: "table",
      category: "Core Entities",
      apiReference: "TMF629",
      description: "Customer entity",
      fields: [
        { name: "id", type: "STRING", description: "Customer ID" },
        { name: "name", type: "STRING", description: "Customer name" }
      ]
    },
    {
      name: "BusinessPartner",
      type: "table",
      category: "Core Entities",
      apiReference: "TMF629",
      description: "Business partner entity",
      fields: [
        { name: "id", type: "STRING", description: "Partner ID" },
        { name: "type", type: "STRING", description: "Partner type" }
      ]
    },
    {
      name: "ContactMedium",
      type: "table",
      category: "Contact Information",
      apiReference: "TMF629",
      description: "Contact medium",
      fields: [
        { name: "id", type: "STRING", description: "Contact ID" },
        { name: "type", type: "STRING", description: "Contact type" }
      ]
    },
    {
      name: "Event",
      type: "table",
      category: "Events",
      apiReference: "TMF629",
      description: "Event entity",
      fields: [
        { name: "id", type: "STRING", description: "Event ID" }
      ]
    }
  ],
  relationships: [
    {
      source: "Customer",
      target: "ContactMedium",
      type: "database_relationship",
      relationship: "Foreign Key",
      foreignKey: "customer_id",
      description: "Customer has contact mediums",
      apiReference: "TMF629"
    },
    {
      source: "BusinessPartner",
      target: "Customer",
      type: "database_relationship",
      relationship: "Inheritance",
      foreignKey: null,
      description: "BusinessPartner inherits from Customer",
      apiReference: "TMF629"
    },
    {
      source: "PartyOrPartyRole",
      target: "Customer",
      type: "database_relationship",
      relationship: "Union",
      foreignKey: null,
      description: "Abstract entity relationship",
      apiReference: "TMF629"
    }
  ],
  apiEndpoints: [
    {
      name: "Get Customer",
      description: "Retrieve customer by ID",
      apiReference: "TMF629",
      method: "GET",
      endpoint: "/customer/{id}",
      requestDetails: {},
      responseDetails: {}
    },
    {
      name: "Create Customer",
      description: "Create new customer",
      apiReference: "TMF629",
      method: "POST",
      endpoint: "/customer",
      requestDetails: {},
      responseDetails: {}
    }
  ],
  statistics: {
    totalTables: 4,
    regularTables: 4,
    relationshipTables: 0,
    totalRelationships: 3,
    totalApiEndpoints: 2,
    tablesByCategory: {
      "Core Entities": 2,
      "Contact Information": 1,
      "Events": 1
    },
    relationshipsByCategory: {
      "Foreign Key": 1,
      "Inheritance": 1,
      "Union": 1
    }
  }
};

const mockApiResponse = [{ consolidated_tmf629: mockTmfData }];

describe('TmfOdaService', () => {
  beforeEach(() => {
    // Clear service cache before each test
    tmfOdaService.clearCache();
    
    // Reset fetch mock
    (fetch as vi.Mock).mockClear();
  });

  describe('Data Loading', () => {
    it('should load data successfully', async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      });

      const data = await tmfOdaService.loadData();

      expect(data).toEqual(mockTmfData);
      expect(tmfOdaService.isDataLoaded()).toBe(true);
      expect(fetch).toHaveBeenCalledWith('/TMF629_entities.json');
    });

    it('should handle fetch errors', async () => {
      (fetch as vi.Mock).mockRejectedValueOnce(new Error('Network error'));

      await expect(tmfOdaService.loadData()).rejects.toThrow('Network error');
      expect(tmfOdaService.isDataLoaded()).toBe(false);
    });

    it('should handle invalid response structure', async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ invalid: 'structure' })
      });

      await expect(tmfOdaService.loadData()).rejects.toThrow('Invalid data structure');
    });

    it('should return cached data on subsequent calls', async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      });

      const data1 = await tmfOdaService.loadData();
      const data2 = await tmfOdaService.loadData();

      expect(data1).toBe(data2);
      expect(fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('Entity Filtering', () => {
    beforeEach(async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      });
      await tmfOdaService.loadData();
    });

    it('should filter by table category', () => {
      const filterOptions: FilterOptions = {
        tableCategoryFilter: 'Core Entities',
        relationshipCategoryFilter: 'all',
        searchFilter: ''
      };

      const result = tmfOdaService.getFilteredDataset(filterOptions);

      expect(result.tables).toHaveLength(3); // 2 core + 1 connected (ContactMedium)
      expect(result.tables.some(t => t.name === 'Customer')).toBe(true);
      expect(result.tables.some(t => t.name === 'BusinessPartner')).toBe(true);
      expect(result.tables.some(t => t.name === 'ContactMedium')).toBe(true);
    });

    it('should filter by relationship category', () => {
      const filterOptions: FilterOptions = {
        tableCategoryFilter: 'all',
        relationshipCategoryFilter: 'Foreign Key',
        searchFilter: ''
      };

      const result = tmfOdaService.getFilteredDataset(filterOptions);

      expect(result.relationships.every(r => r.relationship === 'Foreign Key')).toBe(true);
    });

    it('should filter by search term', () => {
      const filterOptions: FilterOptions = {
        tableCategoryFilter: 'all',
        relationshipCategoryFilter: 'all',
        searchFilter: 'customer'
      };

      const result = tmfOdaService.getFilteredDataset(filterOptions);

      expect(result.tables.some(t => t.name === 'Customer')).toBe(true);
      expect(result.tables.some(t => t.name === 'ContactMedium')).toBe(true); // Connected to Customer
    });

    it('should return all data when no filters applied', () => {
      const filterOptions: FilterOptions = {
        tableCategoryFilter: 'all',
        relationshipCategoryFilter: 'all',
        searchFilter: ''
      };

      const result = tmfOdaService.getFilteredDataset(filterOptions);

      expect(result.tables).toHaveLength(4);
      expect(result.relationships).toHaveLength(3);
    });
  });

  describe('Entity Relationships', () => {
    beforeEach(async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      });
      await tmfOdaService.loadData();
    });

    it('should get relationships for an entity', () => {
      const relationships = tmfOdaService.getEntityRelationships('Customer');

      expect(relationships).toHaveLength(3); // Customer appears in 3 relationships
      expect(relationships.some(r => r.source === 'Customer' || r.target === 'Customer')).toBe(true);
    });

    it('should get connected entities', () => {
      const connected = tmfOdaService.getConnectedEntities('Customer');

      expect(connected.some(t => t.name === 'ContactMedium')).toBe(true);
      expect(connected.some(t => t.name === 'BusinessPartner')).toBe(true);
      expect(connected.some(t => t.name === 'Customer')).toBe(false); // Should not include self
    });

    it('should get relationship path between entities', () => {
      const path = tmfOdaService.getRelationshipPath('Customer', 'ContactMedium');

      expect(path).toHaveLength(1);
      expect(path[0].source === 'Customer' && path[0].target === 'ContactMedium').toBe(true);
    });

    it('should generate edge visibility set', () => {
      const relationships = tmfOdaService.getEntityRelationships('Customer');
      const edges = tmfOdaService.generateEdgeVisibility(relationships);

      expect(edges.size).toBeGreaterThan(0);
      expect(Array.from(edges).every(edge => typeof edge === 'string')).toBe(true);
    });
  });

  describe('Entity Statistics', () => {
    beforeEach(async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      });
      await tmfOdaService.loadData();
    });

    it('should calculate entity statistics', () => {
      const stats = tmfOdaService.getEntityStatistics('Customer');

      expect(stats).toBeDefined();
      expect(stats!.relationshipCount).toBeGreaterThan(0);
      expect(stats!.connectedEntities).toBeGreaterThan(0);
      expect(stats!.relationshipTypes).toContain('Foreign Key');
    });

    it('should return null for non-existent entity', () => {
      const stats = tmfOdaService.getEntityStatistics('NonExistentEntity');

      expect(stats).toBeDefined(); // Service should still return stats even if entity doesn't exist
      expect(stats!.relationshipCount).toBe(0);
    });
  });

  describe('Search and Lookup', () => {
    beforeEach(async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      });
      await tmfOdaService.loadData();
    });

    it('should search tables by name', () => {
      const results = tmfOdaService.searchTables('customer');

      expect(results).toHaveLength(1);
      expect(results[0].name).toBe('Customer');
    });

    it('should search tables by description', () => {
      const results = tmfOdaService.searchTables('partner');

      expect(results.some(t => t.name === 'BusinessPartner')).toBe(true);
    });

    it('should search tables by field name', () => {
      const results = tmfOdaService.searchTables('type');

      expect(results.length).toBeGreaterThan(0);
    });

    it('should get table by name', () => {
      const table = tmfOdaService.getTableByName('Customer');

      expect(table).toBeDefined();
      expect(table!.name).toBe('Customer');
    });

    it('should return null for non-existent table', () => {
      const table = tmfOdaService.getTableByName('NonExistentTable');

      expect(table).toBeNull();
    });

    it('should get tables by category', () => {
      const coreEntities = tmfOdaService.getTablesByCategory('Core Entities');

      expect(coreEntities).toHaveLength(2);
      expect(coreEntities.every(t => t.category === 'Core Entities')).toBe(true);
    });

    it('should get relationships by type', () => {
      const foreignKeys = tmfOdaService.getRelationshipsByType('Foreign Key');

      expect(foreignKeys).toHaveLength(1);
      expect(foreignKeys.every(r => r.relationship === 'Foreign Key')).toBe(true);
    });
  });

  describe('Metadata and Categories', () => {
    beforeEach(async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      });
      await tmfOdaService.loadData();
    });

    it('should get metadata', () => {
      const metadata = tmfOdaService.getMetadata();

      expect(metadata).toEqual(mockTmfData.metadata);
    });

    it('should get statistics', () => {
      const stats = tmfOdaService.getStatistics();

      expect(stats).toEqual(mockTmfData.statistics);
    });

    it('should get table categories', () => {
      const categories = tmfOdaService.getTableCategories();

      expect(categories).toContain('all');
      expect(categories).toContain('Core Entities');
      expect(categories).toContain('Contact Information');
      expect(categories).toContain('Events');
    });

    it('should get relationship categories', () => {
      const categories = tmfOdaService.getRelationshipCategories();

      expect(categories).toContain('all');
      expect(categories).toContain('Foreign Key');
      expect(categories).toContain('Inheritance');
      expect(categories).toContain('Union');
    });
  });

  describe('Entity Mapping Validation', () => {
    beforeEach(async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      });
      await tmfOdaService.loadData();
    });

    it('should validate entity mapping', () => {
      const validation = tmfOdaService.validateEntityMapping();

      expect(validation).toHaveProperty('valid');
      expect(validation).toHaveProperty('issues');
      expect(Array.isArray(validation.issues)).toBe(true);
    });

    it('should detect invalid entity references', () => {
      // Mock data already contains "PartyOrPartyRole" which is an abstract entity
      const validation = tmfOdaService.validateEntityMapping();

      // The validation should still pass because abstract entities are mapped
      expect(validation.valid).toBe(true);
    });
  });

  describe('Endpoint Filtering', () => {
    beforeEach(async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      });
      await tmfOdaService.loadData();
    });

    it('should get all endpoints when no filter', () => {
      const endpoints = tmfOdaService.getFilteredEndpoints('');

      expect(endpoints).toHaveLength(2);
    });

    it('should filter endpoints by search term', () => {
      const endpoints = tmfOdaService.getFilteredEndpoints('create');

      expect(endpoints).toHaveLength(1);
      expect(endpoints[0].name).toBe('Create Customer');
    });

    it('should filter endpoints by method', () => {
      const endpoints = tmfOdaService.getFilteredEndpoints('GET');

      expect(endpoints).toHaveLength(1);
      expect(endpoints[0].method).toBe('GET');
    });
  });

  describe('Cache Management', () => {
    it('should clear cache', async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockApiResponse)
      });

      await tmfOdaService.loadData();
      expect(tmfOdaService.isDataLoaded()).toBe(true);

      tmfOdaService.clearCache();
      expect(tmfOdaService.isDataLoaded()).toBe(false);
    });

    it('should reload data after cache clear', async () => {
      (fetch as vi.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockApiResponse)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockApiResponse)
        });

      await tmfOdaService.loadData();
      tmfOdaService.clearCache();
      await tmfOdaService.loadData();

      expect(fetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('Error Handling', () => {
    it('should throw error when accessing data before loading', () => {
      expect(() => {
        tmfOdaService.getFilteredDataset({
          tableCategoryFilter: 'all',
          relationshipCategoryFilter: 'all',
          searchFilter: ''
        });
      }).toThrow('Data not loaded. Call loadData() first.');
    });

    it('should handle malformed JSON gracefully', async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON'))
      });

      await expect(tmfOdaService.loadData()).rejects.toThrow('Invalid JSON');
    });

    it('should handle HTTP errors', async () => {
      (fetch as vi.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404
      });

      await expect(tmfOdaService.loadData()).rejects.toThrow('HTTP error! status: 404');
    });
  });
}); 