// Data service to dynamically load from local files in public folder
// Files are read fresh on each request to ensure latest data

export interface GraphNode {
  id: string;
  group: string;
  type: string;
  label: string;
  color: string;
  title: string;
  shape: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  color: string;
  title: string;
  confidence: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphEdge[];
}

export interface HierarchicalData {
  legacy_schema: {
    tables: { name: string; count: number; percentage: number }[];
    procedures: { name: string; count: number; percentage: number }[];
    components: { name: string; count: number; percentage: number }[];
  };
  tmf_oda: {
    components: { name: string; count: number; percentage: number }[];
  };
}

export interface MappingData {
  confidence_distribution: { confidence: string; count: number }[];
  api_coverage: { component: string; percentage: number; color: string }[];
  legacy_assets: { type: string; count: number }[];
  procedure_mapping: { procedure: string; confidence: number }[];
}

// Dynamic data loading functions - no caching, fresh data on each call

export const fetchGraphData = async (): Promise<GraphData> => {
  try {
    // Add timestamp to prevent browser caching
    const timestamp = new Date().getTime();
    const response = await fetch(`/graph_data.json?t=${timestamp}`);
    if (!response.ok) {
      throw new Error(`Failed to load graph data: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error loading graph data:', error);
    throw error;
  }
};

export const fetchAnalysisReport = async (): Promise<string> => {
  try {
    // Add timestamp to prevent browser caching
    const timestamp = new Date().getTime();
    const response = await fetch(`/tmf_oda_mapping_report.md?t=${timestamp}`);
    if (!response.ok) {
      throw new Error(`Failed to load analysis report: ${response.status}`);
    }
    const text = await response.text();
    return text;
  } catch (error) {
    console.error('Error loading analysis report:', error);
    throw error;
  }
};

// Mock data for other dashboards (to be replaced with dynamic loading later)
export const fetchHierarchicalData = (): Promise<HierarchicalData> => {
  return new Promise((resolve) => {
    setTimeout(() => resolve(mockHierarchicalData), 500);
  });
};

export const fetchMappingData = (): Promise<MappingData> => {
  return new Promise((resolve) => {
    setTimeout(() => resolve(mockMappingData), 500);
  });
};

// Mock data for other dashboards (to be replaced later)
const mockHierarchicalData: HierarchicalData = {
  legacy_schema: {
    tables: [
      { name: 'Tables', count: 335, percentage: 45 },
      { name: 'CUSTOMER', count: 18, percentage: 2 },
      { name: 'CUSTOMER_SERVICE', count: 17, percentage: 2 },
      { name: 'CUSTOMER_TRANSACTION', count: 15, percentage: 2 },
    ],
    procedures: [
      { name: 'Procedures', count: 35, percentage: 5 },
      { name: 'create_customer_complete', count: 1, percentage: 1 },
    ],
    components: [
      { name: 'CUSTOMER', count: 30, percentage: 4 },
      { name: 'CUSTOMER_WALLET', count: 20, percentage: 3 },
    ]
  },
  tmf_oda: {
    components: [
      { name: 'Party Management', count: 11, percentage: 24 },
      { name: 'Customer Management', count: 4, percentage: 4 },
      { name: 'Service Management', count: 4, percentage: 4 },
      { name: 'Revenue Management', count: 4, percentage: 4 },
    ]
  }
};

const mockMappingData: MappingData = {
  confidence_distribution: [
    { confidence: '90%', count: 4 },
    { confidence: '80%', count: 2 },
    { confidence: '70%', count: 1 },
  ],
  api_coverage: [
    { component: 'Party Management', percentage: 47.8, color: '#3b82f6' },
    { component: 'Customer Management', percentage: 13, color: '#ef4444' },
    { component: 'Service Management', percentage: 8.7, color: '#10b981' },
    { component: 'Revenue Management', percentage: 8.7, color: '#f59e0b' },
    { component: 'Others', percentage: 21.8, color: '#8b5cf6' },
  ],
  legacy_assets: [
    { type: 'Tables', count: 25 },
    { type: 'Procedures', count: 10 },
    { type: 'Mappings', count: 7 },
  ],
  procedure_mapping: [
    { procedure: 'create_customer_complete', confidence: 1 },
    { procedure: 'update_customer_profile', confidence: 1 },
    { procedure: 'manage_customer_journey', confidence: 1 },
    { procedure: 'handle_customer_preference', confidence: 0.8 },
  ]
};
