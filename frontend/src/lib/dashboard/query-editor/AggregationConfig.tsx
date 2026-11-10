import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import type { AggregationConfig as AggConfig } from '../types';

interface Props {
  aggregation?: AggConfig;
  groupBy: string[];
  onAggregationChange: (agg: AggConfig | undefined) => void;
  onGroupByChange: (groupBy: string[]) => void;
  availableFields?: string[];
}

const NONE = '__none__';

const AGG_FUNCTIONS = [
  { value: NONE, label: 'None' },
  { value: 'count', label: 'Count' },
  { value: 'sum', label: 'Sum' },
  { value: 'avg', label: 'Average' },
  { value: 'min', label: 'Min' },
  { value: 'max', label: 'Max' },
] as const;

export function AggregationConfig({
  aggregation,
  groupBy,
  onAggregationChange,
  onGroupByChange,
  availableFields,
}: Props) {
  const handleFunctionChange = (fn: string) => {
    if (!fn || fn === NONE) {
      onAggregationChange(undefined);
      return;
    }
    onAggregationChange({
      function: fn as AggConfig['function'],
      field: aggregation?.field,
    });
  };

  const handleFieldChange = (field: string) => {
    if (!aggregation) return;
    onAggregationChange({ ...aggregation, field: (field && field !== NONE) ? field : undefined });
  };

  const handleGroupByChange = (field: string) => {
    if (groupBy.includes(field)) {
      onGroupByChange(groupBy.filter((g) => g !== field));
    } else {
      onGroupByChange([...groupBy, field]);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <div className="flex-1">
          <Label className="text-xs text-muted-foreground">Aggregation</Label>
          <Select value={aggregation?.function || NONE} onValueChange={handleFunctionChange}>
            <SelectTrigger className="h-7 text-xs mt-1">
              <SelectValue placeholder="None" />
            </SelectTrigger>
            <SelectContent>
              {AGG_FUNCTIONS.map((fn) => (
                <SelectItem key={fn.value} value={fn.value} className="text-xs">{fn.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {aggregation && aggregation.function !== 'count' && (
          <div className="flex-1">
            <Label className="text-xs text-muted-foreground">Agg. Field</Label>
            <Select value={aggregation.field || NONE} onValueChange={handleFieldChange}>
              <SelectTrigger className="h-7 text-xs mt-1">
                <SelectValue placeholder="Select field" />
              </SelectTrigger>
              <SelectContent>
                {(availableFields || []).map((f) => (
                  <SelectItem key={f} value={f} className="text-xs">{f}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>
      {aggregation && (
        <div>
          <Label className="text-xs text-muted-foreground">Group By</Label>
          <div className="flex flex-wrap gap-1 mt-1">
            {(availableFields || []).map((f) => {
              const selected = groupBy.includes(f);
              return (
                <button
                  key={f}
                  type="button"
                  onClick={() => handleGroupByChange(f)}
                  className={`px-2 py-0.5 rounded text-xs border transition-colors ${
                    selected
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-background text-muted-foreground border-border hover:border-primary/50'
                  }`}
                >
                  {f}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
