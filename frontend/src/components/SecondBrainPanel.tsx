import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Brain, 
  Plus, 
  Search, 
  Filter, 
  BookOpen, 
  Lightbulb, 
  TrendingUp,
  Settings,
  ChevronDown,
  ChevronUp,
  Edit,
  Trash2,
  Eye,
  Clock,
  Target,
  Zap
} from 'lucide-react';
import { 
  SecondBrainRule, 
  TransformationStage, 
  RuleType, 
  RulePriority,
  SecondBrainQuery 
} from '@/types/secondBrain';
import { secondBrainService } from '@/services/secondBrainService';
import { RuleEditor } from './RuleEditor';
import { RuleCard } from './RuleCard';
import { createExampleRules } from '@/utils/createExampleRules';

interface SecondBrainPanelProps {
  currentStage?: TransformationStage;
  contextData?: {
    table?: string;
    field?: string;
    pattern?: string;
  };
  onRuleApplied?: (rule: SecondBrainRule) => void;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
}

export const SecondBrainPanel: React.FC<SecondBrainPanelProps> = ({
  currentStage,
  contextData,
  onRuleApplied,
  collapsed = false,
  onToggleCollapsed
}) => {
  const [rules, setRules] = useState<SecondBrainRule[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStage, setSelectedStage] = useState<TransformationStage | 'all'>('all');
  const [selectedType, setSelectedType] = useState<RuleType | 'all'>('all');
  const [showEditor, setShowEditor] = useState(false);
  const [editingRule, setEditingRule] = useState<SecondBrainRule | null>(null);
  const [activeTab, setActiveTab] = useState('rules');
  const [statistics, setStatistics] = useState<any>(null);

  // Load rules and statistics
  useEffect(() => {
    loadRules();
    loadStatistics();
  }, [currentStage, selectedStage, selectedType, searchQuery]);

  const loadRules = () => {
    const query: SecondBrainQuery = {
      stage: selectedStage !== 'all' ? selectedStage : (currentStage || undefined),
      type: selectedType !== 'all' ? selectedType : undefined,
      searchText: searchQuery.trim() || undefined,
      sortBy: 'confidence',
      limit: 50
    };

    const result = secondBrainService.queryRules(query);
    setRules(result.rules);
  };

  const loadStatistics = () => {
    const stats = secondBrainService.getStatistics();
    setStatistics(stats);
  };

  const handleCreateRule = () => {
    setEditingRule(null);
    setShowEditor(true);
  };

  const handleEditRule = (rule: SecondBrainRule) => {
    setEditingRule(rule);
    setShowEditor(true);
  };

  const handleDeleteRule = (ruleId: string) => {
    if (window.confirm('Are you sure you want to delete this rule?')) {
      secondBrainService.deleteRule(ruleId);
      loadRules();
      loadStatistics();
    }
  };

  const handleRuleApply = (rule: SecondBrainRule) => {
    if (onRuleApplied) {
      onRuleApplied(rule);
    }
    
    // Record the application
    secondBrainService.applyRule(rule.id, {
      stage: currentStage || 'raw-analysis',
      tableName: contextData?.table,
      fieldName: contextData?.field,
      timestamp: new Date()
    }, {
      success: true,
      confidence: 0.8,
      reasoning: 'Rule applied via UI'
    });
    
    loadRules();
    loadStatistics();
  };

  const handleSaveRule = () => {
    setShowEditor(false);
    setEditingRule(null);
    loadRules();
    loadStatistics();
  };

  // Get stage-specific rules count
  const getStageRulesCount = (stage: TransformationStage) => {
    return rules.filter(rule => rule.stage === stage).length;
  };

  // Get contextual recommendations
  const getContextualRules = () => {
    if (!contextData || !currentStage) return [];
    
    const query: SecondBrainQuery = {
      stage: currentStage,
      context: contextData,
      sortBy: 'confidence',
      limit: 3
    };
    
    return secondBrainService.queryRules(query).rules;
  };

  if (collapsed) {
    return null;
  }

  return (
    <div className="fixed right-4 top-4 bottom-4 w-96 z-50">
      <Card className="h-full bg-background/95 backdrop-blur-sm border-border shadow-xl">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Brain className="h-5 w-5 text-primary" />
              Second Brain
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                onClick={handleCreateRule}
                size="sm"
                className="h-8 px-2"
              >
                <Plus className="h-4 w-4" />
              </Button>
              <Button
                onClick={onToggleCollapsed}
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
              >
                <ChevronUp className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          {/* Current Stage Context */}
          {currentStage && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Target className="h-4 w-4" />
              <span className="capitalize">{currentStage.replace('-', ' ')}</span>
              <Badge variant="outline" className="text-xs">
                {getStageRulesCount(currentStage)} rules
              </Badge>
            </div>
          )}
          
          {/* Search and Filters */}
          <div className="space-y-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search rules..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 h-8"
              />
            </div>
            
            <div className="flex gap-2">
              <select
                value={selectedStage}
                onChange={(e) => setSelectedStage(e.target.value as TransformationStage | 'all')}
                className="flex-1 h-8 px-2 rounded border border-input bg-background text-sm"
              >
                <option value="all">All Stages</option>
                <option value="raw-analysis">Raw Analysis</option>
                <option value="schema-mapping">Schema Mapping</option>
                <option value="tmf-mapping">TMF Mapping</option>
                <option value="validation">Validation</option>
                <option value="output-generation">Output Generation</option>
                <option value="quality-check">Quality Check</option>
              </select>
              
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value as RuleType | 'all')}
                className="flex-1 h-8 px-2 rounded border border-input bg-background text-sm"
              >
                <option value="all">All Types</option>
                <option value="field-mapping">Field Mapping</option>
                <option value="data-interpretation">Data Interpretation</option>
                <option value="validation-rule">Validation Rule</option>
                <option value="transformation-logic">Transformation Logic</option>
                <option value="quality-metric">Quality Metric</option>
                <option value="documentation-note">Documentation Note</option>
              </select>
            </div>
          </div>
        </CardHeader>

        <CardContent className="h-full overflow-hidden p-0">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
            <TabsList className="grid w-full grid-cols-3 mx-4 mb-2">
              <TabsTrigger value="rules" className="text-xs">
                Rules ({rules.length})
              </TabsTrigger>
              <TabsTrigger value="insights" className="text-xs">
                Insights
              </TabsTrigger>
              <TabsTrigger value="stats" className="text-xs">
                Stats
              </TabsTrigger>
            </TabsList>

            <TabsContent value="rules" className="flex-1 overflow-y-auto px-4 pb-4">
              {/* Contextual Recommendations */}
              {contextData && currentStage && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                    <Lightbulb className="h-4 w-4 text-yellow-500" />
                    Contextual Recommendations
                  </h4>
                  <div className="space-y-2">
                    {getContextualRules().map(rule => (
                      <div
                        key={rule.id}
                        className="p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-700"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="text-sm font-medium">{rule.title}</div>
                            <div className="text-xs text-muted-foreground">{rule.description}</div>
                          </div>
                          <Button
                            onClick={() => handleRuleApply(rule)}
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2"
                          >
                            <Zap className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Rules List */}
              <div className="space-y-3">
                {rules.map(rule => (
                  <RuleCard
                    key={rule.id}
                    rule={rule}
                    onEdit={handleEditRule}
                    onDelete={handleDeleteRule}
                    onApply={handleRuleApply}
                    compact={true}
                  />
                ))}
                
                {rules.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-sm">No rules found</p>
                    <p className="text-xs mb-4">Create your first rule to get started</p>
                    <div className="space-y-2">
                      <Button
                        onClick={handleCreateRule}
                        size="sm"
                        className="mr-2"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Create Rule
                      </Button>
                      <Button
                        onClick={() => {
                          createExampleRules();
                          loadRules();
                          loadStatistics();
                        }}
                        size="sm"
                        variant="outline"
                      >
                        <Lightbulb className="h-4 w-4 mr-2" />
                        Load Examples
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="insights" className="flex-1 overflow-y-auto px-4 pb-4">
              <div className="space-y-4">
                <div className="text-center py-8 text-muted-foreground">
                  <TrendingUp className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="text-sm">Insights Coming Soon</p>
                  <p className="text-xs">AI-generated insights based on your rules</p>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="stats" className="flex-1 overflow-y-auto px-4 pb-4">
              {statistics && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-card rounded-lg border border-border">
                      <div className="text-2xl font-bold text-primary">{statistics.totalRules}</div>
                      <div className="text-xs text-muted-foreground">Total Rules</div>
                    </div>
                    <div className="p-3 bg-card rounded-lg border border-border">
                      <div className="text-2xl font-bold text-green-600">{statistics.activeRules}</div>
                      <div className="text-xs text-muted-foreground">Active Rules</div>
                    </div>
                    <div className="p-3 bg-card rounded-lg border border-border">
                      <div className="text-2xl font-bold text-blue-600">{statistics.totalApplications}</div>
                      <div className="text-xs text-muted-foreground">Applications</div>
                    </div>
                    <div className="p-3 bg-card rounded-lg border border-border">
                      <div className="text-2xl font-bold text-purple-600">
                        {Math.round(statistics.averageConfidence * 100)}%
                      </div>
                      <div className="text-xs text-muted-foreground">Avg Confidence</div>
                    </div>
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Rule Editor Modal */}
      {showEditor && (
        <RuleEditor
          rule={editingRule}
          currentStage={currentStage}
          contextData={contextData}
          onSave={handleSaveRule}
          onCancel={() => setShowEditor(false)}
        />
      )}
    </div>
  );
}; 