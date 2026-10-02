import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Edit, 
  Trash2, 
  Zap, 
  Clock, 
  TrendingUp,
  Target,
  Tag
} from 'lucide-react';
import { SecondBrainRule } from '@/types/secondBrain';

interface RuleCardProps {
  rule: SecondBrainRule;
  onEdit: (rule: SecondBrainRule) => void;
  onDelete: (ruleId: string) => void;
  onApply: (rule: SecondBrainRule) => void;
  compact?: boolean;
}

const priorityColors = {
  low: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100',
  medium: 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-800 dark:text-orange-100',
  critical: 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
};

const stageColors = {
  'raw-analysis': 'bg-purple-100 text-purple-800 dark:bg-purple-800 dark:text-purple-100',
  'schema-mapping': 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100',
  'tmf-mapping': 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100',
  'validation': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100',
  'output-generation': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-800 dark:text-indigo-100',
  'quality-check': 'bg-pink-100 text-pink-800 dark:bg-pink-800 dark:text-pink-100'
};

export const RuleCard: React.FC<RuleCardProps> = ({
  rule,
  onEdit,
  onDelete,
  onApply,
  compact = false
}) => {
  const handleApply = (e: React.MouseEvent) => {
    e.stopPropagation();
    onApply(rule);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit(rule);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(rule.id);
  };

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 dark:text-green-400';
    if (confidence >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer">
      <CardContent className="p-3">
        <div className="space-y-2">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm truncate">{rule.title}</h4>
              <p className="text-xs text-muted-foreground line-clamp-2">{rule.description}</p>
            </div>
            <div className="flex items-center gap-1 ml-2">
              <Button
                onClick={handleApply}
                size="sm"
                variant="ghost"
                className="h-6 w-6 p-0"
                title="Apply Rule"
              >
                <Zap className="h-3 w-3" />
              </Button>
              <Button
                onClick={handleEdit}
                size="sm"
                variant="ghost"
                className="h-6 w-6 p-0"
                title="Edit Rule"
              >
                <Edit className="h-3 w-3" />
              </Button>
              <Button
                onClick={handleDelete}
                size="sm"
                variant="ghost"
                className="h-6 w-6 p-0 text-red-500 hover:text-red-700"
                title="Delete Rule"
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          </div>

          {/* Badges */}
          <div className="flex items-center gap-1 flex-wrap">
            <Badge 
              variant="secondary" 
              className={`text-xs ${stageColors[rule.stage]}`}
            >
              {rule.stage.replace('-', ' ')}
            </Badge>
            <Badge 
              variant="outline" 
              className={`text-xs ${priorityColors[rule.priority]}`}
            >
              {rule.priority}
            </Badge>
            <Badge variant="outline" className="text-xs">
              {rule.type.replace('-', ' ')}
            </Badge>
          </div>

          {/* Content Preview */}
          {!compact && (
            <div className="bg-muted/50 p-2 rounded text-xs">
              <p className="line-clamp-2">{rule.content}</p>
            </div>
          )}

          {/* Stats */}
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                <span className={getConfidenceColor(rule.confidence)}>
                  {Math.round(rule.confidence * 100)}%
                </span>
              </span>
              <span className="flex items-center gap-1">
                <Target className="h-3 w-3" />
                {rule.usage.timesApplied}
              </span>
              {rule.usage.lastUsed && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDate(rule.usage.lastUsed)}
                </span>
              )}
            </div>
            
            {rule.metadata.tags.length > 0 && (
              <div className="flex items-center gap-1">
                <Tag className="h-3 w-3" />
                <span>{rule.metadata.tags.length}</span>
              </div>
            )}
          </div>

          {/* Keywords */}
          {rule.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {rule.keywords.slice(0, 3).map(keyword => (
                <span 
                  key={keyword}
                  className="px-1 py-0.5 bg-muted text-xs rounded"
                >
                  {keyword}
                </span>
              ))}
              {rule.keywords.length > 3 && (
                <span className="px-1 py-0.5 bg-muted text-xs rounded">
                  +{rule.keywords.length - 3}
                </span>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}; 