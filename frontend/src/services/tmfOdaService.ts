// TMF ODA Service Layer
// Handles all data processing, filtering, and business logic for TMF ODA Viewer

export interface TmfField {
  name: string;
  type: string;
  description: string;
}

export interface TmfTable {
  name: string;
  type: string;
  category: string;
  apiReference: string;
  description: string;
  fields: TmfField[];
}

export interface TmfRelationship {
  source: string;
  target: string;
  type: string;
  relationship: string;
  foreignKey?: string | null;
  description: string;
  apiReference: string;
}

export interface ApiEndpoint {
  name: string;
  description: string;
  apiReference: string;
  method: string;
  endpoint: string;
  requestDetails: any;
  responseDetails: any;
}

export interface TmfConsolidatedData {
  metadata: {
    title: string;
    description: string;
    apiReference: string;
  };
  tables: TmfTable[];
  relationships: TmfRelationship[];
  apiEndpoints: ApiEndpoint[];
  statistics: {
    totalTables: number;
    regularTables: number;
    relationshipTables: number;
    totalRelationships: number;
    totalApiEndpoints: number;
    tablesByCategory: Record<string, number>;
    relationshipsByCategory: Record<string, number>;
  };
}

export interface FilteredDataset {
  tables: TmfTable[];
  relationships: TmfRelationship[];
  expandedTables: string[];
  entityMapping: Map<string, Set<string>>;
}

export interface FilterOptions {
  searchFilter: string;
  includedCategories: Set<string>; // Categories to include in the view
}

export interface EdgeVisibilityOptions {
  visibleEdges: Set<string>;
  mode: 'all' | 'filtered' | 'selective';
}

class TmfOdaService {
  private data: TmfConsolidatedData | null = null;
  private entityMapping: Map<string, Set<string>> = new Map();
  private isLoading = false;

  /**
   * Load TMF629 consolidated data
   */
  async loadData(): Promise<TmfConsolidatedData> {
    if (this.data) {
      return this.data;
    }

    if (this.isLoading) {
      // Wait for existing load to complete
      while (this.isLoading) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      return this.data!;
    }

    try {
      this.isLoading = true;
      console.log('🔄 TmfOdaService: Loading data...');
      
      // Load main data and cleaned relationships
      const [mainResponse, cleanedRelResponse] = await Promise.all([
        fetch('/TMF629_entities.json'),
        fetch('/TMF629_relationships.json')
      ]);
      
      if (!mainResponse.ok) {
        throw new Error(`HTTP error loading TMF629_entities.json! status: ${mainResponse.status}`);
      }
      if (!cleanedRelResponse.ok) {
        throw new Error(`HTTP error loading TMF629_relationships.json! status: ${cleanedRelResponse.status}`);
      }
      
      const [mainDataArray, cleanedRelArray] = await Promise.all([
        mainResponse.json(),
        cleanedRelResponse.json()
      ]);
      
      if (mainDataArray && Array.isArray(mainDataArray) && mainDataArray.length > 0) {
        const mainData = mainDataArray[0];
        
        if (mainData.consolidated_tmf629) {
          // Use main data structure but replace relationships with cleaned ones
          this.data = {
            ...mainData.consolidated_tmf629,
            relationships: cleanedRelArray[0].consolidated_tmf629.relationships
          };
          
          this.entityMapping = this.createEntityMapping(this.data.tables);
          
          // Validate that all relationships reference existing tables
          this.validateRelationships();
          
          console.log('✅ TmfOdaService: Data loaded successfully from TMF629_entities.json + TMF629_relationships.json');
          console.log(`📊 Loaded: ${this.data.tables.length} tables, ${this.data.relationships.length} relationships`);
          console.log('🧹 Using cleaned relationships - no abstract entities!');
          console.log(`🔍 First 3 relationships: ${this.data.relationships.slice(0, 3).map(r => `${r.source}->${r.target}(${r.relationship})`).join(', ')}`);
          console.log(`🔍 Sample table names: [${this.data.tables.slice(0, 10).map(t => t.name).join(', ')}]`);
          
          return this.data;
        } else {
          throw new Error('consolidated_tmf629 property not found');
        }
      } else {
        throw new Error('Invalid data structure');
      }
    } catch (error) {
      console.error('❌ TmfOdaService: Failed to load data:', error);
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * Validate that all relationships reference existing tables
   */
  private validateRelationships(): void {
    if (!this.data) return;
    
    const tableNames = new Set(this.data.tables.map(t => t.name));
    const invalidRelationships: string[] = [];
    
    this.data.relationships.forEach((rel, index) => {
      const sourceExists = tableNames.has(rel.source);
      const targetExists = tableNames.has(rel.target);
      
      if (!sourceExists || !targetExists) {
        invalidRelationships.push(`${rel.source} -> ${rel.target} (source: ${sourceExists}, target: ${targetExists})`);
      }
    });
    
    if (invalidRelationships.length > 0) {
      console.warn(`⚠️  Found ${invalidRelationships.length} invalid relationships:`);
      invalidRelationships.slice(0, 10).forEach(rel => console.warn(`   ${rel}`));
      
      // Filter out invalid relationships
      this.data.relationships = this.data.relationships.filter(rel => {
        const sourceExists = tableNames.has(rel.source);
        const targetExists = tableNames.has(rel.target);
        return sourceExists && targetExists;
      });
      
      console.log(`🧹 Filtered out invalid relationships. Remaining: ${this.data.relationships.length} relationships`);
    } else {
      console.log('✅ All relationships reference valid tables');
    }
  }

  /**
   * Create entity mapping - simplified for cleaned relationships
   */
  private createEntityMapping(tables: TmfTable[]): Map<string, Set<string>> {
    const mapping = new Map<string, Set<string>>();
    
    // Create direct mapping for existing tables (1:1 mapping)
    tables.forEach(table => {
      mapping.set(table.name, new Set([table.name]));
    });
    
    console.log('🗺️  Simple entity mapping created with', mapping.size, 'direct mappings');
    
    return mapping;
  }

  /**
   * Resolve abstract entity names to actual table names
   */
  private resolveEntityName(entityName: string): string[] {
    if (this.entityMapping.has(entityName)) {
      return Array.from(this.entityMapping.get(entityName)!);
    }
    return [entityName]; // Return as-is if no mapping found
  }

  /**
   * Get filtered dataset - simplified for cleaned relationships
   */
  getFilteredDataset(filterOptions: FilterOptions): FilteredDataset {
    if (!this.data) {
      throw new Error('Data not loaded. Call loadData() first.');
    }

    const { searchFilter, includedCategories } = filterOptions;
    
    console.log(`🔍 TmfOdaService: Filtering for categories: [${Array.from(includedCategories).join(', ')}], search: "${searchFilter}"`);
    
    // Step 1: Filter tables by included categories
    let filteredTables = this.data.tables.filter(t => includedCategories.has(t.category));
    
    console.log(`🎯 Tables from categories: ${filteredTables.length} tables`);
    
    // Step 2: Apply search filter if provided
    if (searchFilter.trim()) {
      const filterLower = searchFilter.trim().toLowerCase();
      filteredTables = filteredTables.filter(t => 
        t.name.toLowerCase().includes(filterLower) ||
        t.description.toLowerCase().includes(filterLower) ||
        t.fields.some(f => f.name.toLowerCase().includes(filterLower) || f.description.toLowerCase().includes(filterLower))
      );
      console.log(`🔍 After search filter: ${filteredTables.length} tables`);
    }
    
    // Step 3: Get table names for relationship filtering
    const visibleTableNames = new Set(filteredTables.map(t => t.name));
    
    // Step 4: Simple relationship filtering (no abstract entities to resolve!)
    console.log(`🔍 Debug filtering - Total relationships loaded: ${this.data.relationships.length}`);
    console.log(`🔍 Debug filtering - Visible table names: [${Array.from(visibleTableNames).slice(0, 10).join(', ')}...]`);
    console.log(`🔍 Sample relationships: ${this.data.relationships.slice(0, 5).map(r => `${r.source}->${r.target}(${r.relationship})`).join(', ')}`);
    console.log(`🔍 Relationship types: ${this.data.relationships.slice(0, 3).map(r => `source: ${typeof r.source}, target: ${typeof r.target}`).join(', ')}`);
    
    const relationships = this.data.relationships.filter(rel => {
      // Since we're using cleaned relationships, source and target should be concrete table names
      // But D3.js may have mutated them to object references, so we need to extract the original strings
      const sourceString = typeof rel.source === 'string' ? rel.source : (rel.source as any).name || String(rel.source);
      const targetString = typeof rel.target === 'string' ? rel.target : (rel.target as any).name || String(rel.target);
      
      const sourceExists = visibleTableNames.has(sourceString);
      const targetExists = visibleTableNames.has(targetString);
      
      if (!sourceExists || !targetExists) {
        console.log(`❌ Filtering out: ${sourceString} -> ${targetString} (source: ${sourceExists}, target: ${targetExists})`);
      }
      
      return sourceExists && targetExists;
    });
    
    console.log(`✅ TmfOdaService: ${relationships.length} relationships between ${filteredTables.length} tables`);
    console.log(`🔍 Filtered relationships: ${relationships.slice(0, 3).map(r => `${typeof r.source === 'string' ? r.source : (r.source as any).name}->${typeof r.target === 'string' ? r.target : (r.target as any).name}`).join(', ')}`);
    
    // Debug output
    if (relationships.length === 0 && filteredTables.length > 1) {
      console.warn(`⚠️  No relationships found between ${filteredTables.length} tables`);
      console.log(`📋 Available tables: ${filteredTables.map(t => t.name).slice(0, 5).join(', ')}...`);
    } else if (relationships.length > 0) {
      console.log(`✅ Sample relationships: ${relationships.slice(0, 3).map(r => `${r.source}->${r.target}(${r.relationship})`).join(', ')}`);
    }
    
    return {
      tables: filteredTables,
      relationships,
      expandedTables: [], // No expansion needed with cleaned relationships
      entityMapping: this.entityMapping
    };
  }

  /**
   * Get all relationships for a specific entity
   */
  getEntityRelationships(entityName: string): TmfRelationship[] {
    if (!this.data) {
      throw new Error('Data not loaded. Call loadData() first.');
    }

    return this.data.relationships.filter(r => {
      const sourceTableNames = this.resolveEntityName(r.source);
      const targetTableNames = this.resolveEntityName(r.target);
      
      return sourceTableNames.includes(entityName) || targetTableNames.includes(entityName);
    });
  }

  /**
   * Generate edge visibility set for relationships
   */
  generateEdgeVisibility(relationships: TmfRelationship[], mode: 'all' | 'none' = 'all'): Set<string> {
    const edges = new Set<string>();
    
    if (mode === 'all') {
      relationships.forEach(rel => {
        const relId = `${rel.source}-${rel.target}-${rel.relationship}`;
        edges.add(relId);
      });
    }
    
    return edges;
  }

  /**
   * Get all edge IDs for specific entity relationships
   */
  getEntityEdgeIds(entityName: string): Set<string> {
    const entityRelationships = this.getEntityRelationships(entityName);
    return this.generateEdgeVisibility(entityRelationships);
  }

  /**
   * Get filtered API endpoints
   */
  getFilteredEndpoints(searchFilter: string): ApiEndpoint[] {
    if (!this.data) {
      throw new Error('Data not loaded. Call loadData() first.');
    }

    if (!searchFilter.trim()) {
      return this.data.apiEndpoints;
    }

    const filterLower = searchFilter.trim().toLowerCase();
    return this.data.apiEndpoints.filter(e =>
      e.name.toLowerCase().includes(filterLower) ||
      e.description.toLowerCase().includes(filterLower) ||
      e.endpoint.toLowerCase().includes(filterLower)
    );
  }

  /**
   * Get data statistics
   */
  getStatistics(): TmfConsolidatedData['statistics'] | null {
    return this.data?.statistics || null;
  }

  /**
   * Get unique table categories
   */
  getTableCategories(): string[] {
    if (!this.data) return ['all'];
    return ['all', ...Object.keys(this.data.statistics.tablesByCategory)];
  }

  /**
   * Get unique relationship categories
   */
  getRelationshipCategories(): string[] {
    if (!this.data) return ['all'];
    return ['all', ...Object.keys(this.data.statistics.relationshipsByCategory)];
  }

  /**
   * Check if data is loaded
   */
  isDataLoaded(): boolean {
    return this.data !== null;
  }

  /**
   * Get raw data (use sparingly)
   */
  getRawData(): TmfConsolidatedData | null {
    return this.data;
  }

  /**
   * Get metadata information
   */
  getMetadata(): TmfConsolidatedData['metadata'] | null {
    return this.data?.metadata || null;
  }

  /**
   * Search tables by name or description
   */
  searchTables(searchTerm: string): TmfTable[] {
    if (!this.data || !searchTerm.trim()) {
      return this.data?.tables || [];
    }

    const term = searchTerm.toLowerCase();
    return this.data.tables.filter(table =>
      table.name.toLowerCase().includes(term) ||
      table.description.toLowerCase().includes(term) ||
      table.fields.some(field => 
        field.name.toLowerCase().includes(term) || 
        field.description.toLowerCase().includes(term)
      )
    );
  }

  /**
   * Get table by name
   */
  getTableByName(tableName: string): TmfTable | null {
    if (!this.data) return null;
    return this.data.tables.find(table => table.name === tableName) || null;
  }

  /**
   * Get tables by category
   */
  getTablesByCategory(category: string): TmfTable[] {
    if (!this.data) return [];
    if (category === 'all') return this.data.tables;
    return this.data.tables.filter(table => table.category === category);
  }

  /**
   * Get relationships by type
   */
  getRelationshipsByType(relationshipType: string): TmfRelationship[] {
    if (!this.data) return [];
    if (relationshipType === 'all') return this.data.relationships;
    return this.data.relationships.filter(rel => rel.relationship === relationshipType);
  }

  /**
   * Find connected entities (1-level) for a given entity
   */
  getConnectedEntities(entityName: string): TmfTable[] {
    if (!this.data) return [];

    const connectedNames = new Set<string>();
    const entityRelationships = this.getEntityRelationships(entityName);

    entityRelationships.forEach(rel => {
      const sourceNames = this.resolveEntityName(rel.source);
      const targetNames = this.resolveEntityName(rel.target);
      
      sourceNames.forEach(name => connectedNames.add(name));
      targetNames.forEach(name => connectedNames.add(name));
    });

    // Remove the original entity from connected set
    connectedNames.delete(entityName);

    return this.data.tables.filter(table => connectedNames.has(table.name));
  }

  /**
   * Get relationship path between two entities
   */
  getRelationshipPath(sourceEntity: string, targetEntity: string): TmfRelationship[] {
    if (!this.data) return [];

    // Simple direct relationship check
    return this.data.relationships.filter(rel => {
      const sourceNames = this.resolveEntityName(rel.source);
      const targetNames = this.resolveEntityName(rel.target);
      
      const isDirectPath = (
        sourceNames.includes(sourceEntity) && targetNames.includes(targetEntity)
      ) || (
        sourceNames.includes(targetEntity) && targetNames.includes(sourceEntity)
      );
      
      return isDirectPath;
    });
  }

  /**
   * Validate entity mapping integrity - enhanced version
   */
  validateEntityMapping(): { valid: boolean; issues: string[] } {
    if (!this.data) {
      return { valid: false, issues: ['No data loaded'] };
    }

    const issues: string[] = [];
    const tableNames = new Set(this.data.tables.map(t => t.name));

    // Check all relationships reference valid entities
    this.data.relationships.forEach((rel, index) => {
      const sourceNames = this.resolveEntityName(rel.source);
      const targetNames = this.resolveEntityName(rel.target);

      const hasValidSource = sourceNames.some(name => tableNames.has(name));
      const hasValidTarget = targetNames.some(name => tableNames.has(name));

      if (!hasValidSource) {
        issues.push(`Relationship ${index}: Source "${rel.source}" resolves to invalid entities: [${sourceNames.join(', ')}]`);
      }
      if (!hasValidTarget) {
        issues.push(`Relationship ${index}: Target "${rel.target}" resolves to invalid entities: [${targetNames.join(', ')}]`);
      }
    });

    return {
      valid: issues.length === 0,
      issues
    };
  }

  /**
   * Get entity statistics
   */
  getEntityStatistics(entityName: string): {
    relationshipCount: number;
    connectedEntities: number;
    incomingRelationships: number;
    outgoingRelationships: number;
    relationshipTypes: string[];
  } | null {
    if (!this.data) return null;

    const entityRelationships = this.getEntityRelationships(entityName);
    const connectedEntities = this.getConnectedEntities(entityName);
    
    const incoming = entityRelationships.filter(rel => {
      const targetNames = this.resolveEntityName(rel.target);
      return targetNames.includes(entityName);
    });
    
    const outgoing = entityRelationships.filter(rel => {
      const sourceNames = this.resolveEntityName(rel.source);
      return sourceNames.includes(entityName);
    });

    const relationshipTypes = [...new Set(entityRelationships.map(rel => rel.relationship))];

    return {
      relationshipCount: entityRelationships.length,
      connectedEntities: connectedEntities.length,
      incomingRelationships: incoming.length,
      outgoingRelationships: outgoing.length,
      relationshipTypes
    };
  }

  /**
   * Clear cached data (force reload)
   */
  clearCache(): void {
    this.data = null;
    this.entityMapping.clear();
    this.isLoading = false;
    console.log('🗑️ TmfOdaService: Cache cleared');
  }
}

// Export singleton instance
export const tmfOdaService = new TmfOdaService();
export default tmfOdaService; 