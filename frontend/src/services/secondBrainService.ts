/**
 * Second Brain Service - Human in Loop Transformation Feature
 * 
 * This service manages the storage, retrieval, and application of
 * human-provided rules and insights for transformation stages.
 */

import {
  SecondBrainRule,
  SecondBrainStore,
  SecondBrainQuery,
  SecondBrainResult,
  SecondBrainSession,
  SecondBrainInsight,
  RuleApplication,
  CreateRuleRequest,
  UpdateRuleRequest,
  SecondBrainEvent,
  TransformationStage,
  RuleType,
  RulePriority
} from '@/types/secondBrain';

class SecondBrainService {
  private store: SecondBrainStore;
  private eventListeners: Map<string, (event: SecondBrainEvent) => void> = new Map();
  private currentSession: SecondBrainSession | null = null;
  private readonly STORAGE_KEY = 'second-brain-store';

  constructor() {
    this.store = this.initializeStore();
    this.loadFromStorage();
    
    // Auto-save every 30 seconds
    setInterval(() => {
      this.saveToStorage();
    }, 30000);
  }

  /**
   * Initialize empty store
   */
  private initializeStore(): SecondBrainStore {
    return {
      rules: new Map(),
      applications: new Map(),
      sessions: new Map(),
      insights: new Map(),
      metadata: {
        version: '1.0.0',
        lastSync: new Date(),
        totalRules: 0,
        totalApplications: 0
      }
    };
  }

  /**
   * Load store from localStorage
   */
  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const data = JSON.parse(stored);
        
        // Convert plain objects back to Maps
        this.store.rules = new Map(data.rules || []);
        this.store.applications = new Map(data.applications || []);
        this.store.sessions = new Map(data.sessions || []);
        this.store.insights = new Map(data.insights || []);
        this.store.metadata = data.metadata || this.store.metadata;
        
        // Convert date strings back to Date objects
        this.convertDatesFromStorage();
        
        console.log('🧠 Second Brain: Loaded from storage -', this.store.rules.size, 'rules');
      }
    } catch (error) {
      console.error('❌ Second Brain: Failed to load from storage:', error);
      this.store = this.initializeStore();
    }
  }

  /**
   * Save store to localStorage
   */
  private saveToStorage(): void {
    try {
      const data = {
        rules: Array.from(this.store.rules.entries()),
        applications: Array.from(this.store.applications.entries()),
        sessions: Array.from(this.store.sessions.entries()),
        insights: Array.from(this.store.insights.entries()),
        metadata: this.store.metadata
      };
      
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
      console.log('🧠 Second Brain: Saved to storage -', this.store.rules.size, 'rules');
    } catch (error) {
      console.error('❌ Second Brain: Failed to save to storage:', error);
    }
  }

  /**
   * Convert date strings from storage back to Date objects
   */
  private convertDatesFromStorage(): void {
    // Convert rule dates
    for (const [id, rule] of this.store.rules) {
      rule.metadata.createdAt = new Date(rule.metadata.createdAt);
      rule.metadata.updatedAt = new Date(rule.metadata.updatedAt);
      if (rule.usage.lastUsed) {
        rule.usage.lastUsed = new Date(rule.usage.lastUsed);
      }
    }
    
    // Convert session dates
    for (const [id, session] of this.store.sessions) {
      session.metadata.createdAt = new Date(session.metadata.createdAt);
      session.metadata.updatedAt = new Date(session.metadata.updatedAt);
      session.metadata.lastActivity = new Date(session.metadata.lastActivity);
    }
    
    // Convert application dates
    for (const [id, applications] of this.store.applications) {
      applications.forEach(app => {
        app.context.timestamp = new Date(app.context.timestamp);
      });
    }
    
    // Convert insight dates
    for (const [id, insight] of this.store.insights) {
      insight.metadata.generatedAt = new Date(insight.metadata.generatedAt);
    }
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  /**
   * Emit event to listeners
   */
  private emit(event: SecondBrainEvent): void {
    this.eventListeners.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error('❌ Second Brain: Event listener error:', error);
      }
    });
  }

  /**
   * Add event listener
   */
  on(eventType: string, listener: (event: SecondBrainEvent) => void): void {
    this.eventListeners.set(eventType, listener);
  }

  /**
   * Remove event listener
   */
  off(eventType: string): void {
    this.eventListeners.delete(eventType);
  }

  /**
   * Create a new rule
   */
  createRule(request: CreateRuleRequest): SecondBrainRule {
    const rule: SecondBrainRule = {
      id: this.generateId(),
      title: request.title,
      description: request.description,
      stage: request.stage,
      type: request.type,
      priority: request.priority,
      status: 'active',
      context: request.context,
      content: request.content,
      examples: request.examples,
      keywords: request.keywords,
      confidence: 0.5, // Start with neutral confidence
      usage: {
        timesApplied: 0,
        successRate: 0,
        averageImpact: 0
      },
      metadata: {
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: 'user', // TODO: Add user management
        version: 1,
        tags: request.tags || []
      }
    };

    this.store.rules.set(rule.id, rule);
    this.store.metadata.totalRules = this.store.rules.size;
    this.saveToStorage();

    this.emit({ type: 'rule-created', rule });
    
    console.log('🧠 Second Brain: Created rule -', rule.title);
    return rule;
  }

  /**
   * Update an existing rule
   */
  updateRule(request: UpdateRuleRequest): SecondBrainRule | null {
    const existingRule = this.store.rules.get(request.id);
    if (!existingRule) {
      console.warn('⚠️ Second Brain: Rule not found for update -', request.id);
      return null;
    }

    // Check version for optimistic locking
    if (existingRule.metadata.version !== request.version) {
      console.warn('⚠️ Second Brain: Version mismatch for rule update -', request.id);
      return null;
    }

    const updatedRule: SecondBrainRule = {
      ...existingRule,
      ...request,
      metadata: {
        ...existingRule.metadata,
        updatedAt: new Date(),
        version: existingRule.metadata.version + 1
      }
    };

    this.store.rules.set(request.id, updatedRule);
    this.saveToStorage();

    this.emit({ type: 'rule-updated', rule: updatedRule });
    
    console.log('🧠 Second Brain: Updated rule -', updatedRule.title);
    return updatedRule;
  }

  /**
   * Delete a rule
   */
  deleteRule(ruleId: string): boolean {
    const rule = this.store.rules.get(ruleId);
    if (!rule) {
      console.warn('⚠️ Second Brain: Rule not found for deletion -', ruleId);
      return false;
    }

    this.store.rules.delete(ruleId);
    this.store.applications.delete(ruleId);
    this.store.metadata.totalRules = this.store.rules.size;
    this.saveToStorage();

    this.emit({ type: 'rule-deleted', ruleId });
    
    console.log('🧠 Second Brain: Deleted rule -', rule.title);
    return true;
  }

  /**
   * Query rules based on criteria
   */
  queryRules(query: SecondBrainQuery): SecondBrainResult {
    const startTime = performance.now();
    let rules = Array.from(this.store.rules.values());

    // Filter by stage
    if (query.stage) {
      rules = rules.filter(rule => rule.stage === query.stage);
    }

    // Filter by type
    if (query.type) {
      rules = rules.filter(rule => rule.type === query.type);
    }

    // Filter by context
    if (query.context) {
      rules = rules.filter(rule => {
        if (query.context!.table && rule.context.tables) {
          return rule.context.tables.includes(query.context!.table);
        }
        if (query.context!.field && rule.context.fields) {
          return rule.context.fields.includes(query.context!.field);
        }
        if (query.context!.pattern && rule.context.patterns) {
          return rule.context.patterns.some(pattern => 
            pattern.includes(query.context!.pattern!) || 
            query.context!.pattern!.includes(pattern)
          );
        }
        return true;
      });
    }

    // Text search
    if (query.searchText) {
      const searchLower = query.searchText.toLowerCase();
      rules = rules.filter(rule => 
        rule.title.toLowerCase().includes(searchLower) ||
        rule.description.toLowerCase().includes(searchLower) ||
        rule.content.toLowerCase().includes(searchLower) ||
        rule.keywords.some(keyword => keyword.toLowerCase().includes(searchLower))
      );
    }

    // Filter by confidence
    if (query.minConfidence !== undefined) {
      rules = rules.filter(rule => rule.confidence >= query.minConfidence!);
    }

    // Filter active rules only
    rules = rules.filter(rule => rule.status === 'active');

    const totalCount = rules.length;

    // Sort results
    const sortBy = query.sortBy || 'confidence';
    rules.sort((a, b) => {
      switch (sortBy) {
        case 'confidence':
          return b.confidence - a.confidence;
        case 'usage':
          return b.usage.timesApplied - a.usage.timesApplied;
        case 'recent':
          return b.metadata.updatedAt.getTime() - a.metadata.updatedAt.getTime();
        case 'priority':
          const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
          return priorityOrder[b.priority] - priorityOrder[a.priority];
        default:
          return 0;
      }
    });

    // Apply limit
    if (query.limit) {
      rules = rules.slice(0, query.limit);
    }

    const executionTime = performance.now() - startTime;

    return {
      rules,
      totalCount,
      executionTime,
      insights: [], // TODO: Add relevant insights
      suggestions: [] // TODO: Add suggestions for new rules
    };
  }

  /**
   * Get rule by ID
   */
  getRule(ruleId: string): SecondBrainRule | null {
    return this.store.rules.get(ruleId) || null;
  }

  /**
   * Get all rules for a specific stage
   */
  getRulesForStage(stage: TransformationStage): SecondBrainRule[] {
    return this.queryRules({ stage }).rules;
  }

  /**
   * Apply a rule and record the application
   */
  applyRule(ruleId: string, context: RuleApplication['context'], result: RuleApplication['result']): void {
    const rule = this.store.rules.get(ruleId);
    if (!rule) {
      console.warn('⚠️ Second Brain: Rule not found for application -', ruleId);
      return;
    }

    const application: RuleApplication = {
      ruleId,
      context,
      result
    };

    // Update rule usage statistics
    rule.usage.timesApplied++;
    rule.usage.lastUsed = new Date();
    
    if (result.success) {
      rule.usage.successRate = (rule.usage.successRate * (rule.usage.timesApplied - 1) + 1) / rule.usage.timesApplied;
    } else {
      rule.usage.successRate = (rule.usage.successRate * (rule.usage.timesApplied - 1)) / rule.usage.timesApplied;
    }

    // Update confidence based on success
    if (result.success) {
      rule.confidence = Math.min(1, rule.confidence + 0.1 * result.confidence);
    } else {
      rule.confidence = Math.max(0, rule.confidence - 0.05);
    }

    // Store application
    if (!this.store.applications.has(ruleId)) {
      this.store.applications.set(ruleId, []);
    }
    this.store.applications.get(ruleId)!.push(application);

    this.store.metadata.totalApplications++;
    this.saveToStorage();

    this.emit({ type: 'rule-applied', application });
    
    console.log('🧠 Second Brain: Applied rule -', rule.title, '- Success:', result.success);
  }

  /**
   * Start a new transformation session
   */
  startSession(title: string, context: SecondBrainSession['context']): SecondBrainSession {
    const session: SecondBrainSession = {
      id: this.generateId(),
      title,
      currentStage: 'raw-analysis',
      activeRules: [],
      context,
      statistics: {
        rulesApplied: 0,
        successfulApplications: 0,
        averageConfidence: 0,
        processingTime: 0
      },
      metadata: {
        createdAt: new Date(),
        updatedAt: new Date(),
        lastActivity: new Date()
      }
    };

    this.store.sessions.set(session.id, session);
    this.currentSession = session;
    this.saveToStorage();

    this.emit({ type: 'session-started', session });
    
    console.log('🧠 Second Brain: Started session -', session.title);
    return session;
  }

  /**
   * Get current session
   */
  getCurrentSession(): SecondBrainSession | null {
    return this.currentSession;
  }

  /**
   * Update current session stage
   */
  updateSessionStage(stage: TransformationStage): void {
    if (this.currentSession) {
      this.currentSession.currentStage = stage;
      this.currentSession.metadata.lastActivity = new Date();
      this.saveToStorage();
    }
  }

  /**
   * End current session
   */
  endSession(): void {
    if (this.currentSession) {
      const sessionId = this.currentSession.id;
      this.currentSession = null;
      this.saveToStorage();
      
      this.emit({ type: 'session-ended', sessionId });
      console.log('🧠 Second Brain: Ended session -', sessionId);
    }
  }

  /**
   * Get statistics
   */
  getStatistics() {
    const rules = Array.from(this.store.rules.values());
    const activeRules = rules.filter(r => r.status === 'active');
    
    return {
      totalRules: rules.length,
      activeRules: activeRules.length,
      totalApplications: this.store.metadata.totalApplications,
      averageConfidence: activeRules.reduce((sum, rule) => sum + rule.confidence, 0) / activeRules.length || 0,
      stageBreakdown: this.getStageBreakdown(),
      typeBreakdown: this.getTypeBreakdown(),
      recentActivity: this.getRecentActivity()
    };
  }

  /**
   * Get rules breakdown by stage
   */
  private getStageBreakdown() {
    const breakdown: Record<TransformationStage, number> = {
      'raw-analysis': 0,
      'schema-mapping': 0,
      'tmf-mapping': 0,
      'validation': 0,
      'output-generation': 0,
      'quality-check': 0
    };

    for (const rule of this.store.rules.values()) {
      if (rule.status === 'active') {
        breakdown[rule.stage]++;
      }
    }

    return breakdown;
  }

  /**
   * Get rules breakdown by type
   */
  private getTypeBreakdown() {
    const breakdown: Record<RuleType, number> = {
      'field-mapping': 0,
      'data-interpretation': 0,
      'validation-rule': 0,
      'transformation-logic': 0,
      'quality-metric': 0,
      'documentation-note': 0
    };

    for (const rule of this.store.rules.values()) {
      if (rule.status === 'active') {
        breakdown[rule.type]++;
      }
    }

    return breakdown;
  }

  /**
   * Get recent activity
   */
  private getRecentActivity() {
    const now = new Date();
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    
    const recentRules = Array.from(this.store.rules.values())
      .filter(rule => rule.metadata.updatedAt >= oneDayAgo)
      .length;

    const recentApplications = Array.from(this.store.applications.values())
      .flat()
      .filter(app => app.context.timestamp >= oneDayAgo)
      .length;

    return {
      rulesCreated: recentRules,
      rulesApplied: recentApplications,
      period: '24h'
    };
  }

  /**
   * Export rules as JSON
   */
  exportRules(): string {
    const exportData = {
      rules: Array.from(this.store.rules.entries()),
      metadata: {
        exportedAt: new Date(),
        version: this.store.metadata.version,
        totalRules: this.store.rules.size
      }
    };

    return JSON.stringify(exportData, null, 2);
  }

  /**
   * Import rules from JSON
   */
  importRules(jsonData: string): { success: boolean; imported: number; errors: string[] } {
    try {
      const data = JSON.parse(jsonData);
      const errors: string[] = [];
      let imported = 0;

      if (data.rules && Array.isArray(data.rules)) {
        for (const [id, rule] of data.rules) {
          try {
            // Validate rule structure
            if (this.validateRule(rule)) {
              this.store.rules.set(id, rule);
              imported++;
            } else {
              errors.push(`Invalid rule structure: ${rule.title || id}`);
            }
          } catch (error) {
            errors.push(`Error importing rule ${id}: ${error}`);
          }
        }
      }

      this.store.metadata.totalRules = this.store.rules.size;
      this.saveToStorage();

      return { success: true, imported, errors };
    } catch (error) {
      return { success: false, imported: 0, errors: [String(error)] };
    }
  }

  /**
   * Validate rule structure
   */
  private validateRule(rule: any): boolean {
    const required = ['id', 'title', 'stage', 'type', 'priority', 'context', 'content'];
    return required.every(field => rule.hasOwnProperty(field));
  }

  /**
   * Clear all data (for testing/reset)
   */
  clear(): void {
    this.store = this.initializeStore();
    this.currentSession = null;
    localStorage.removeItem(this.STORAGE_KEY);
    console.log('🧠 Second Brain: Cleared all data');
  }
}

// Export singleton instance
export const secondBrainService = new SecondBrainService();
export default secondBrainService; 