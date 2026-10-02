/**
 * Second Brain - Human in Loop Transformation Feature
 * 
 * This module defines the data structures for storing and managing
 * human-provided rules and insights for transformation stages.
 */

export type TransformationStage = 
  | 'raw-analysis'
  | 'schema-mapping'
  | 'tmf-mapping'
  | 'validation'
  | 'output-generation'
  | 'quality-check';

export type RuleType = 
  | 'field-mapping'
  | 'data-interpretation'
  | 'validation-rule'
  | 'transformation-logic'
  | 'quality-metric'
  | 'documentation-note';

export type RulePriority = 'low' | 'medium' | 'high' | 'critical';

export type RuleStatus = 'active' | 'inactive' | 'deprecated' | 'testing';

export interface RuleContext {
  /** Specific table names this rule applies to */
  tables?: string[];
  /** Specific field names this rule applies to */
  fields?: string[];
  /** Data patterns this rule matches */
  patterns?: string[];
  /** Conditions when this rule should be applied */
  conditions?: string[];
  /** Scope of application (global, project-specific, etc.) */
  scope: 'global' | 'project' | 'session';
}

export interface SecondBrainRule {
  /** Unique identifier for the rule */
  id: string;
  
  /** Human-readable title for the rule */
  title: string;
  
  /** Natural language description of the rule */
  description: string;
  
  /** The transformation stage this rule applies to */
  stage: TransformationStage;
  
  /** Type of rule */
  type: RuleType;
  
  /** Priority level of the rule */
  priority: RulePriority;
  
  /** Current status of the rule */
  status: RuleStatus;
  
  /** Context where this rule applies */
  context: RuleContext;
  
  /** Natural language rule content */
  content: string;
  
  /** Examples of how this rule should be applied */
  examples?: string[];
  
  /** Keywords for quick searching */
  keywords: string[];
  
  /** Confidence score (0-1) based on past success */
  confidence: number;
  
  /** Usage statistics */
  usage: {
    timesApplied: number;
    successRate: number;
    lastUsed?: Date;
    averageImpact: number; // 0-1 scale
  };
  
  /** Metadata */
  metadata: {
    createdAt: Date;
    updatedAt: Date;
    createdBy: string;
    version: number;
    tags: string[];
  };
  
  /** Feedback from applications */
  feedback?: {
    helpful: number;
    notHelpful: number;
    comments: string[];
  };
}

export interface RuleApplication {
  /** Reference to the rule that was applied */
  ruleId: string;
  
  /** Context where the rule was applied */
  context: {
    stage: TransformationStage;
    tableName?: string;
    fieldName?: string;
    inputData?: any;
    timestamp: Date;
  };
  
  /** Result of applying the rule */
  result: {
    success: boolean;
    confidence: number;
    output?: any;
    reasoning?: string;
    suggestions?: string[];
  };
  
  /** Human feedback on the application */
  feedback?: {
    accurate: boolean;
    helpful: boolean;
    comment?: string;
  };
}

export interface SecondBrainSession {
  /** Session identifier */
  id: string;
  
  /** Session name/title */
  title: string;
  
  /** Current transformation stage */
  currentStage: TransformationStage;
  
  /** Rules active in this session */
  activeRules: string[];
  
  /** Session context */
  context: {
    projectName?: string;
    sourceSchema?: string;
    targetSchema?: string;
    transformationGoal?: string;
  };
  
  /** Session statistics */
  statistics: {
    rulesApplied: number;
    successfulApplications: number;
    averageConfidence: number;
    processingTime: number;
  };
  
  /** Session metadata */
  metadata: {
    createdAt: Date;
    updatedAt: Date;
    lastActivity: Date;
  };
}

export interface SecondBrainInsight {
  /** Insight ID */
  id: string;
  
  /** Type of insight */
  type: 'pattern' | 'improvement' | 'warning' | 'suggestion';
  
  /** Insight title */
  title: string;
  
  /** Detailed description */
  description: string;
  
  /** Confidence in this insight */
  confidence: number;
  
  /** Stage where this insight was generated */
  stage: TransformationStage;
  
  /** Data that led to this insight */
  evidence: {
    ruleApplications: string[];
    dataPatterns: string[];
    userFeedback: string[];
  };
  
  /** Suggested actions */
  recommendations: string[];
  
  /** Metadata */
  metadata: {
    generatedAt: Date;
    relevanceScore: number;
    category: string;
  };
}

export interface SecondBrainStore {
  /** All rules in the second brain */
  rules: Map<string, SecondBrainRule>;
  
  /** Rule applications history */
  applications: Map<string, RuleApplication[]>;
  
  /** Active sessions */
  sessions: Map<string, SecondBrainSession>;
  
  /** Generated insights */
  insights: Map<string, SecondBrainInsight>;
  
  /** Store metadata */
  metadata: {
    version: string;
    lastSync: Date;
    totalRules: number;
    totalApplications: number;
  };
}

export interface SecondBrainQuery {
  /** Stage to query rules for */
  stage?: TransformationStage;
  
  /** Rule type to filter by */
  type?: RuleType;
  
  /** Context to match against */
  context?: {
    table?: string;
    field?: string;
    pattern?: string;
  };
  
  /** Text search query */
  searchText?: string;
  
  /** Minimum confidence threshold */
  minConfidence?: number;
  
  /** Maximum number of results */
  limit?: number;
  
  /** Sort criteria */
  sortBy?: 'confidence' | 'usage' | 'recent' | 'priority';
}

export interface SecondBrainResult {
  /** Matching rules */
  rules: SecondBrainRule[];
  
  /** Total count before limiting */
  totalCount: number;
  
  /** Query execution time */
  executionTime: number;
  
  /** Additional insights */
  insights?: SecondBrainInsight[];
  
  /** Suggestions for new rules */
  suggestions?: string[];
}

// Utility types for rule creation
export interface CreateRuleRequest {
  title: string;
  description: string;
  stage: TransformationStage;
  type: RuleType;
  priority: RulePriority;
  context: RuleContext;
  content: string;
  examples?: string[];
  keywords: string[];
  tags?: string[];
}

export interface UpdateRuleRequest extends Partial<CreateRuleRequest> {
  id: string;
  version: number;
}

// Event types for Second Brain operations
export type SecondBrainEvent = 
  | { type: 'rule-created'; rule: SecondBrainRule }
  | { type: 'rule-updated'; rule: SecondBrainRule }
  | { type: 'rule-deleted'; ruleId: string }
  | { type: 'rule-applied'; application: RuleApplication }
  | { type: 'insight-generated'; insight: SecondBrainInsight }
  | { type: 'session-started'; session: SecondBrainSession }
  | { type: 'session-ended'; sessionId: string }; 