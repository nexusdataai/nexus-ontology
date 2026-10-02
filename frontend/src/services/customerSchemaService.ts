export interface CustomerSchema {
  id: string;
  name: string;
  description: string;
  version: string;
  status: 'active' | 'inactive' | 'processing';
  lastDiscovery: string;
  endpoints: number;
  totalTables: number;
  regularTables: number;
  relationshipTables: number;
  totalRelationships: number;
  apiCoverage: string;
  schemaFiles: string[];
  folderPath: string;
  hasSecondBrain: boolean;
}

export interface CustomerMetadata {
  metadata: {
    title: string;
    description: string;
    version?: string;
    status?: string;
  };
  statistics: {
    totalTables: number;
    regularTables: number;
    relationshipTables: number;
    totalRelationships: number;
    apiCoverage: string;
  };
}

class CustomerSchemaService {
  private customerSchemas: CustomerSchema[] = [];

  async loadCustomerSchemas(): Promise<CustomerSchema[]> {
    try {
      // In a real application, this would be an API call
      // For now, we'll simulate the data structure based on what we know
      const schemas: CustomerSchema[] = [
        {
          id: 'mtn-sa',
          name: 'MTN SA Customer Management',
          description: 'MTN SA Customer Management Database Schema - 30+ Years Old Informix database',
          version: 'v1.0.0',
          status: 'active',
          lastDiscovery: '3 days ago',
          endpoints: 0,
          totalTables: 90000,
          regularTables: 14,
          relationshipTables: 2,
          totalRelationships: 14,
          apiCoverage: 'TMF 629 Customer Management - Complete Schema',
          schemaFiles: ['Eppix_Schema_202050317.sql', 'Eppix_Procedure_20250317.sql'],
          folderPath: 'public/customer-input/MTN-SA',
          hasSecondBrain: true
        },
        {
          id: 'jain-jordan',
          name: 'JAIN JORDAN Database Schema',
          description: 'JAIN JORDAN telecommunications database schema for billing and customer management',
          version: 'v1.0.0',
          status: 'active',
          lastDiscovery: '5 days ago',
          endpoints: 0,
          totalTables: 85000,
          regularTables: 12,
          relationshipTables: 3,
          totalRelationships: 16,
          apiCoverage: 'TMF 629 Customer Management - Partial Schema',
          schemaFiles: ['Schema_jordan.sql'],
          folderPath: 'public/customer-input/JAIN-JORDAN',
          hasSecondBrain: true
        }
      ];

      this.customerSchemas = schemas;
      return schemas;
    } catch (error) {
      console.error('Error loading customer schemas:', error);
      return [];
    }
  }

  getSchemaById(id: string): CustomerSchema | undefined {
    return this.customerSchemas.find(schema => schema.id === id);
  }

  getAllSchemas(): CustomerSchema[] {
    return this.customerSchemas;
  }

  // This would be used in a real implementation to dynamically scan folders
  async scanCustomerFolders(): Promise<string[]> {
    // In a real implementation, this would scan the public/customer-input directory
    return ['MTN-SA', 'JAIN-JORDAN'];
  }

  // This would parse actual metadata.json files in a real implementation
  async parseMetadata(folderPath: string): Promise<CustomerMetadata | null> {
    // In a real implementation, this would read and parse the metadata.json file
    // For now, returning null to indicate it should use default values
    return null;
  }
}

export const customerSchemaService = new CustomerSchemaService(); 