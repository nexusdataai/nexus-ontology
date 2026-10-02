export interface DiscoveryStage {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  startTime?: Date;
  endTime?: Date;
  duration?: string;
  subSteps: DiscoverySubStep[];
  report?: DiscoveryStageReport;
  canSkip?: boolean;
  requiresApproval?: boolean;
}

export interface DiscoverySubStep {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  startTime?: Date;
  endTime?: Date;
  duration?: string;
  logs: DiscoveryLog[];
  result?: any;
  errorMessage?: string;
}

export interface DiscoveryLog {
  id: string;
  timestamp: Date;
  level: 'info' | 'warn' | 'error' | 'success' | 'debug';
  message: string;
  details?: string;
  metadata?: Record<string, any>;
}

export interface DiscoveryStageReport {
  stageId: string;
  stageName: string;
  summary: string;
  keyFindings: string[];
  metrics: Record<string, any>;
  recommendations: string[];
  artifacts: DiscoveryArtifact[];
  issues: DiscoveryIssue[];
  nextStageReadiness: 'ready' | 'needs_review' | 'blocked';
}

export interface DiscoveryArtifact {
  id: string;
  name: string;
  type: 'schema' | 'mapping' | 'report' | 'data' | 'script';
  description: string;
  filePath?: string;
  downloadUrl?: string;
  metadata?: Record<string, any>;
}

export interface DiscoveryIssue {
  id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: 'schema' | 'mapping' | 'data' | 'validation' | 'performance';
  title: string;
  description: string;
  recommendation: string;
  affectedItems: string[];
}

export interface DiscoverySession {
  id: string;
  customerId: string;
  schemaId: string;
  schemaName: string;
  startTime: Date;
  endTime?: Date;
  status: 'running' | 'completed' | 'failed' | 'paused';
  currentStage: string;
  stages: DiscoveryStage[];
  configuration: DiscoveryConfiguration;
  metadata: Record<string, any>;
}

export interface DiscoveryConfiguration {
  timeout: number;
  maxDepth: number;
  includeDocumentation: boolean;
  includeExamples: boolean;
  validateEndpoints: boolean;
  generateMigrationScripts: boolean;
  performDataSampling: boolean;
  tmfSpecVersion: string;
  outputFormat: 'json' | 'xml' | 'yaml';
}

export const DISCOVERY_STAGES: Omit<DiscoveryStage, 'status' | 'subSteps' | 'report'>[] = [
  {
    id: 'raw_analysis',
    name: 'Raw Input Analysis',
    description: 'Analyze the raw customer database schema to understand structure and relationships',
    canSkip: false,
    requiresApproval: false
  },
  {
    id: 'stripped_schema',
    name: 'Create Stripped Down Schema',
    description: 'Extract and create a simplified schema based on TMF specifications',
    canSkip: false,
    requiresApproval: true
  },
  {
    id: 'tmf_mapping',
    name: 'TMF Schema Mapping',
    description: 'Map the stripped schema to TMF ODA standards and APIs',
    canSkip: false,
    requiresApproval: true
  },
  {
    id: 'data_migration_planning',
    name: 'Data Migration Planning',
    description: 'Plan and prepare data migration strategies and scripts',
    canSkip: true,
    requiresApproval: true
  },
  {
    id: 'data_migration_execution',
    name: 'Data Migration',
    description: 'Execute the actual data migration from legacy systems to TMF-compliant structure',
    canSkip: true,
    requiresApproval: true
  },
  {
    id: 'verification',
    name: 'Verification & Validation',
    description: 'Validate the mapping and migration results against TMF standards',
    canSkip: false,
    requiresApproval: false
  }
];

export const RAW_ANALYSIS_SUBSTEPS: Omit<DiscoverySubStep, 'status' | 'logs' | 'startTime' | 'endTime' | 'duration'>[] = [
  {
    id: 'schema_parsing',
    name: 'Schema File Parsing',
    description: 'Parse SQL schema files and extract table definitions'
  },
  {
    id: 'relationship_discovery',
    name: 'Relationship Discovery',
    description: 'Identify foreign key relationships and table dependencies'
  },
  {
    id: 'data_type_analysis',
    name: 'Data Type Analysis',
    description: 'Analyze column data types and constraints'
  },
  {
    id: 'business_rules_extraction',
    name: 'Business Rules Extraction',
    description: 'Extract business rules from stored procedures and constraints'
  },
  {
    id: 'complexity_assessment',
    name: 'Complexity Assessment',
    description: 'Assess schema complexity and identify potential challenges'
  }
];

export const STRIPPED_SCHEMA_SUBSTEPS: Omit<DiscoverySubStep, 'status' | 'logs' | 'startTime' | 'endTime' | 'duration'>[] = [
  {
    id: 'tmf_relevance_filtering',
    name: 'TMF Relevance Filtering',
    description: 'Filter tables and columns relevant to TMF specifications'
  },
  {
    id: 'core_entity_identification',
    name: 'Core Entity Identification',
    description: 'Identify core business entities (Customer, Product, Order, etc.)'
  },
  {
    id: 'simplified_schema_creation',
    name: 'Simplified Schema Creation',
    description: 'Create a simplified schema focusing on TMF-relevant structures'
  },
  {
    id: 'metadata_preservation',
    name: 'Metadata Preservation',
    description: 'Preserve important metadata and business context'
  }
];

export const TMF_MAPPING_SUBSTEPS: Omit<DiscoverySubStep, 'status' | 'logs' | 'startTime' | 'endTime' | 'duration'>[] = [
  {
    id: 'api_matching',
    name: 'TMF API Matching',
    description: 'Match entities to appropriate TMF API specifications'
  },
  {
    id: 'attribute_mapping',
    name: 'Attribute Mapping',
    description: 'Map database columns to TMF API attributes'
  },
  {
    id: 'relationship_mapping',
    name: 'Relationship Mapping',
    description: 'Map database relationships to TMF API relationships'
  },
  {
    id: 'api_coverage_analysis',
    name: 'API Coverage Analysis',
    description: 'Analyze coverage of TMF API specifications'
  },
  {
    id: 'gap_identification',
    name: 'Gap Identification',
    description: 'Identify gaps and missing mappings'
  }
];

export const DATA_MIGRATION_PLANNING_SUBSTEPS: Omit<DiscoverySubStep, 'status' | 'logs' | 'startTime' | 'endTime' | 'duration'>[] = [
  {
    id: 'migration_strategy',
    name: 'Migration Strategy Planning',
    description: 'Plan the overall data migration approach'
  },
  {
    id: 'etl_script_generation',
    name: 'ETL Script Generation',
    description: 'Generate Extract, Transform, Load scripts'
  },
  {
    id: 'data_validation_rules',
    name: 'Data Validation Rules',
    description: 'Create validation rules for data integrity'
  },
  {
    id: 'rollback_procedures',
    name: 'Rollback Procedures',
    description: 'Prepare rollback and recovery procedures'
  }
];

export const DATA_MIGRATION_EXECUTION_SUBSTEPS: Omit<DiscoverySubStep, 'status' | 'logs' | 'startTime' | 'endTime' | 'duration'>[] = [
  {
    id: 'candidate_dataset_selection',
    name: 'Candidate Dataset Selection',
    description: 'Select and prepare candidate datasets for migration'
  },
  {
    id: 'data_transfer',
    name: 'Data Transfer',
    description: 'Execute the actual data transfer from legacy to TMF systems'
  },
  {
    id: 'tmf_api_compliance_test',
    name: 'TMF API Compliance Test',
    description: 'Test migrated data against TMF API compliance requirements'
  },
  {
    id: 'mark_completion',
    name: 'Mark Completion',
    description: 'Mark migration tasks as completed and update status'
  }
];

export const VERIFICATION_SUBSTEPS: Omit<DiscoverySubStep, 'status' | 'logs' | 'startTime' | 'endTime' | 'duration'>[] = [
  {
    id: 'mapping_validation',
    name: 'Mapping Validation',
    description: 'Validate the accuracy of schema mappings'
  },
  {
    id: 'api_compliance_check',
    name: 'API Compliance Check',
    description: 'Check compliance with TMF API standards'
  },
  {
    id: 'data_integrity_verification',
    name: 'Data Integrity Verification',
    description: 'Verify data integrity and consistency'
  },
  {
    id: 'performance_assessment',
    name: 'Performance Assessment',
    description: 'Assess performance implications of the mapping'
  },
  {
    id: 'final_report_generation',
    name: 'Final Report Generation',
    description: 'Generate comprehensive final report'
  }
]; 