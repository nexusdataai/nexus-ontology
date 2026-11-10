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
  low: 'bg-surface-2 text-foreground dark:bg-surface-3 dark:text-foreground',
  medium: 'bg-primary/10 text-primary dark:bg-primary/15 dark:text-primary',
  high: 'bg-warning/10 text-warning dark:bg-warning/15 dark:text-warning',
  critical: 'bg-destructive/10 text-destructive dark:bg-destructive/15 dark:text-destructive'
};

const stageColors = {
  'raw-analysis': 'bg-primary/10 text-primary dark:bg-primary/15 dark:text-primary',
  'schema-mapping': 'bg-success/10 text-success dark:bg-success/15 dark:text-success',
  'tmf-mapping': 'bg-primary/10 text-primary dark:bg-primary/15 dark:text-primary',
  'validation': 'bg-warning/10 text-warning dark:bg-warning/15 dark:text-warning',
  'output-generation': 'bg-primary/10 text-primary dark:bg-primary/15 dark:text-primary',
  'quality-check': 'bg-primary/10 text-primary dark:bg-primary/15 dark:text-primary'
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
    if (confidence >= 0.8) return 'text-success dark:text-success';
    if (confidence >= 0.6) return 'text-warning dark:text-warning';
    return 'text-destructive dark:text-destructive';
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
                className="h-6 w-6 p-0 text-destructive hover:text-destructive"
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