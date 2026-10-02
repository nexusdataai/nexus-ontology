import React, { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { 
  Save, 
  X, 
  Plus, 
  Trash2, 
  Lightbulb, 
  Target,
  Tag,
  Hash
} from 'lucide-react';
import { 
  SecondBrainRule, 
  TransformationStage, 
  RuleType, 
  RulePriority,
  CreateRuleRequest,
  UpdateRuleRequest
} from '@/types/secondBrain';
import { secondBrainService } from '@/services/secondBrainService';

interface RuleEditorProps {
  rule?: SecondBrainRule | null;
  currentStage?: TransformationStage;
  contextData?: {
    table?: string;
    field?: string;
    pattern?: string;
  };
  onSave: () => void;
  onCancel: () => void;
}

export const RuleEditor: React.FC<RuleEditorProps> = ({
  rule,
  currentStage,
  contextData,
  onSave,
  onCancel
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [stage, setStage] = useState<TransformationStage>('raw-analysis');
  const [type, setType] = useState<RuleType>('field-mapping');
  const [priority, setPriority] = useState<RulePriority>('medium');
  const [content, setContent] = useState('');
  const [keywords, setKeywords] = useState<string[]>([]);
  const [newKeyword, setNewKeyword] = useState('');
  const [examples, setExamples] = useState<string[]>([]);
  const [newExample, setNewExample] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');
  const [contextTables, setContextTables] = useState<string[]>([]);
  const [contextFields, setContextFields] = useState<string[]>([]);
  const [contextPatterns, setContextPatterns] = useState<string[]>([]);
  const [newTable, setNewTable] = useState('');
  const [newField, setNewField] = useState('');
  const [newPattern, setNewPattern] = useState('');
  const [scope, setScope] = useState<'global' | 'project' | 'session'>('global');

  // Initialize form with existing rule data
  useEffect(() => {
    if (rule) {
      setTitle(rule.title);
      setDescription(rule.description);
      setStage(rule.stage);
      setType(rule.type);
      setPriority(rule.priority);
      setContent(rule.content);
      setKeywords(rule.keywords || []);
      setExamples(rule.examples || []);
      setTags(rule.metadata.tags || []);
      setContextTables(rule.context.tables || []);
      setContextFields(rule.context.fields || []);
      setContextPatterns(rule.context.patterns || []);
      setScope(rule.context.scope);
    } else {
      // Initialize with context data
      if (currentStage) setStage(currentStage);
      if (contextData?.table) setContextTables([contextData.table]);
      if (contextData?.field) setContextFields([contextData.field]);
      if (contextData?.pattern) setContextPatterns([contextData.pattern]);
    }
  }, [rule, currentStage, contextData]);

  const addKeyword = () => {
    if (newKeyword.trim() && !keywords.includes(newKeyword.trim())) {
      setKeywords([...keywords, newKeyword.trim()]);
      setNewKeyword('');
    }
  };

  const removeKeyword = (keyword: string) => {
    setKeywords(keywords.filter(k => k !== keyword));
  };

  const addExample = () => {
    if (newExample.trim()) {
      setExamples([...examples, newExample.trim()]);
      setNewExample('');
    }
  };

  const removeExample = (index: number) => {
    setExamples(examples.filter((_, i) => i !== index));
  };

  const addTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()]);
      setNewTag('');
    }
  };

  const removeTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag));
  };

  const addTable = () => {
    if (newTable.trim() && !contextTables.includes(newTable.trim())) {
      setContextTables([...contextTables, newTable.trim()]);
      setNewTable('');
    }
  };

  const removeTable = (table: string) => {
    setContextTables(contextTables.filter(t => t !== table));
  };

  const addField = () => {
    if (newField.trim() && !contextFields.includes(newField.trim())) {
      setContextFields([...contextFields, newField.trim()]);
      setNewField('');
    }
  };

  const removeField = (field: string) => {
    setContextFields(contextFields.filter(f => f !== field));
  };

  const addPattern = () => {
    if (newPattern.trim() && !contextPatterns.includes(newPattern.trim())) {
      setContextPatterns([...contextPatterns, newPattern.trim()]);
      setNewPattern('');
    }
  };

  const removePattern = (pattern: string) => {
    setContextPatterns(contextPatterns.filter(p => p !== pattern));
  };

  const handleSave = () => {
    if (!title.trim() || !content.trim()) {
      alert('Title and content are required');
      return;
    }

    const ruleData = {
      title: title.trim(),
      description: description.trim(),
      stage,
      type,
      priority,
      content: content.trim(),
      keywords,
      examples,
      tags,
      context: {
        tables: contextTables.length > 0 ? contextTables : undefined,
        fields: contextFields.length > 0 ? contextFields : undefined,
        patterns: contextPatterns.length > 0 ? contextPatterns : undefined,
        scope
      }
    };

    try {
      if (rule) {
        // Update existing rule
        const updateRequest: UpdateRuleRequest = {
          ...ruleData,
          id: rule.id,
          version: rule.metadata.version
        };
        secondBrainService.updateRule(updateRequest);
      } else {
        // Create new rule
        const createRequest: CreateRuleRequest = ruleData;
        secondBrainService.createRule(createRequest);
      }
      
      onSave();
    } catch (error) {
      console.error('Failed to save rule:', error);
      alert('Failed to save rule. Please try again.');
    }
  };

  const isFormValid = title.trim() && content.trim();

  return (
    <Dialog open={true} onOpenChange={onCancel}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-primary" />
            {rule ? 'Edit Rule' : 'Create New Rule'}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <div>
              <Label htmlFor="title">Rule Title *</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Customer table always maps to TMF Customer entity"
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of what this rule does"
                className="mt-1"
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="stage">Stage</Label>
                <select
                  id="stage"
                  value={stage}
                  onChange={(e) => setStage(e.target.value as TransformationStage)}
                  className="w-full mt-1 px-3 py-2 border border-input rounded-md bg-background"
                >
                  <option value="raw-analysis">Raw Analysis</option>
                  <option value="schema-mapping">Schema Mapping</option>
                  <option value="tmf-mapping">TMF Mapping</option>
                  <option value="validation">Validation</option>
                  <option value="output-generation">Output Generation</option>
                  <option value="quality-check">Quality Check</option>
                </select>
              </div>

              <div>
                <Label htmlFor="type">Type</Label>
                <select
                  id="type"
                  value={type}
                  onChange={(e) => setType(e.target.value as RuleType)}
                  className="w-full mt-1 px-3 py-2 border border-input rounded-md bg-background"
                >
                  <option value="field-mapping">Field Mapping</option>
                  <option value="data-interpretation">Data Interpretation</option>
                  <option value="validation-rule">Validation Rule</option>
                  <option value="transformation-logic">Transformation Logic</option>
                  <option value="quality-metric">Quality Metric</option>
                  <option value="documentation-note">Documentation Note</option>
                </select>
              </div>

              <div>
                <Label htmlFor="priority">Priority</Label>
                <select
                  id="priority"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as RulePriority)}
                  className="w-full mt-1 px-3 py-2 border border-input rounded-md bg-background"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>
          </div>

          {/* Rule Content */}
          <div>
            <Label htmlFor="content">Rule Content (Natural Language) *</Label>
            <Textarea
              id="content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Describe your rule in natural language. For example: 'When I see a table with customer information, it should be mapped to the TMF629 Customer entity. Look for fields like customer_id, customer_name, and customer_email as key indicators.'"
              rows={4}
              className="mt-1"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Describe your rule as if you're explaining it to a colleague. Be specific about conditions and actions.
            </p>
          </div>

          {/* Context */}
          <div className="space-y-4">
            <h4 className="font-medium flex items-center gap-2">
              <Target className="h-4 w-4" />
              Context (When to apply this rule)
            </h4>

            <div>
              <Label>Scope</Label>
              <select
                value={scope}
                onChange={(e) => setScope(e.target.value as 'global' | 'project' | 'session')}
                className="w-full mt-1 px-3 py-2 border border-input rounded-md bg-background"
              >
                <option value="global">Global (all projects)</option>
                <option value="project">Project-specific</option>
                <option value="session">Session-specific</option>
              </select>
            </div>

            {/* Tables */}
            <div>
              <Label>Applies to Tables</Label>
              <div className="flex gap-2 mt-1">
                <Input
                  value={newTable}
                  onChange={(e) => setNewTable(e.target.value)}
                  placeholder="Table name"
                  onKeyPress={(e) => e.key === 'Enter' && addTable()}
                />
                <Button onClick={addTable} size="sm">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {contextTables.map(table => (
                  <Badge key={table} variant="secondary" className="text-xs">
                    {table}
                    <Button
                      onClick={() => removeTable(table)}
                      variant="ghost"
                      size="sm"
                      className="h-auto p-0 ml-1"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
              </div>
            </div>

            {/* Fields */}
            <div>
              <Label>Applies to Fields</Label>
              <div className="flex gap-2 mt-1">
                <Input
                  value={newField}
                  onChange={(e) => setNewField(e.target.value)}
                  placeholder="Field name"
                  onKeyPress={(e) => e.key === 'Enter' && addField()}
                />
                <Button onClick={addField} size="sm">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {contextFields.map(field => (
                  <Badge key={field} variant="secondary" className="text-xs">
                    {field}
                    <Button
                      onClick={() => removeField(field)}
                      variant="ghost"
                      size="sm"
                      className="h-auto p-0 ml-1"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
              </div>
            </div>

            {/* Patterns */}
            <div>
              <Label>Data Patterns</Label>
              <div className="flex gap-2 mt-1">
                <Input
                  value={newPattern}
                  onChange={(e) => setNewPattern(e.target.value)}
                  placeholder="Pattern description"
                  onKeyPress={(e) => e.key === 'Enter' && addPattern()}
                />
                <Button onClick={addPattern} size="sm">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {contextPatterns.map(pattern => (
                  <Badge key={pattern} variant="secondary" className="text-xs">
                    {pattern}
                    <Button
                      onClick={() => removePattern(pattern)}
                      variant="ghost"
                      size="sm"
                      className="h-auto p-0 ml-1"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          {/* Keywords */}
          <div>
            <Label>Keywords</Label>
            <div className="flex gap-2 mt-1">
              <Input
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                placeholder="Add keyword"
                onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
              />
              <Button onClick={addKeyword} size="sm">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {keywords.map(keyword => (
                <Badge key={keyword} variant="outline" className="text-xs">
                  <Hash className="h-3 w-3 mr-1" />
                  {keyword}
                  <Button
                    onClick={() => removeKeyword(keyword)}
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 ml-1"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
          </div>

          {/* Examples */}
          <div>
            <Label>Examples (Optional)</Label>
            <div className="space-y-2 mt-1">
              <div className="flex gap-2">
                <Textarea
                  value={newExample}
                  onChange={(e) => setNewExample(e.target.value)}
                  placeholder="Provide an example of how this rule should be applied"
                  rows={2}
                />
                <Button onClick={addExample} size="sm" className="self-start">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              {examples.map((example, index) => (
                <div key={index} className="bg-muted p-3 rounded text-sm">
                  <div className="flex justify-between items-start">
                    <p>{example}</p>
                    <Button
                      onClick={() => removeExample(index)}
                      variant="ghost"
                      size="sm"
                      className="h-auto p-1"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Tags */}
          <div>
            <Label>Tags</Label>
            <div className="flex gap-2 mt-1">
              <Input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                placeholder="Add tag"
                onKeyPress={(e) => e.key === 'Enter' && addTag()}
              />
              <Button onClick={addTag} size="sm">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {tags.map(tag => (
                <Badge key={tag} variant="outline" className="text-xs">
                  <Tag className="h-3 w-3 mr-1" />
                  {tag}
                  <Button
                    onClick={() => removeTag(tag)}
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 ml-1"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button onClick={onCancel} variant="outline">
            Cancel
          </Button>
          <Button 
            onClick={handleSave} 
            disabled={!isFormValid}
            className="flex items-center gap-2"
          >
            <Save className="h-4 w-4" />
            {rule ? 'Update Rule' : 'Create Rule'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}; 