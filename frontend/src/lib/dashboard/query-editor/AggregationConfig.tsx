import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Field } from '@/components/ds/kit';
import type { AggregationConfig as AggConfig } from '../types';
import { ToggleChip } from './FieldSelector';

interface Props {
  aggregation?: AggConfig;
  groupBy: string[];
  onAggregationChange: (agg: AggConfig | undefined) => void;
  onGroupByChange: (groupBy: string[]) => void;
  availableFields?: string[];
}

const NONE = '__none__';

const AGG_FUNCTIONS = [
  { value: NONE, label: 'No summary (show rows)' },
  { value: 'count', label: 'Count of rows' },
  { value: 'sum', label: 'Sum' },
  { value: 'avg', label: 'Average' },
  { value: 'min', label: 'Minimum' },
  { value: 'max', label: 'Maximum' },
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

  const fields = availableFields || [];

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Summarise">
          <Select value={aggregation?.function || NONE} onValueChange={handleFunctionChange}>
            <SelectTrigger aria-label="Summarise" className="h-8">
              <SelectValue placeholder="No summary" />
            </SelectTrigger>
            <SelectContent>
              {AGG_FUNCTIONS.map((fn) => (
                <SelectItem key={fn.value} value={fn.value}>{fn.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        {aggregation && aggregation.function !== 'count' && (
          <Field label="Of field">
            <Select value={aggregation.field || NONE} onValueChange={handleFieldChange}>
              <SelectTrigger aria-label="Field to summarise" className="h-8">
                <SelectValue placeholder="Choose a field" />
              </SelectTrigger>
              <SelectContent>
                {aggregation.field && !fields.includes(aggregation.field) && (
                  <SelectItem value={aggregation.field}>{aggregation.field}</SelectItem>
                )}
                {fields.map((f) => (
                  <SelectItem key={f} value={f}>{f}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        )}
      </div>
      {aggregation && (
        <div>
          <span className="mb-1.5 block text-xs font-medium text-muted-foreground">Group by</span>
          {fields.length === 0 ? (
            <p className="text-xs text-subtle-foreground">No fields to group by.</p>
          ) : (
            <div className="scroll-thin flex max-h-32 flex-wrap gap-1.5 overflow-y-auto">
              {fields.map((f) => (
                <ToggleChip key={f} selected={groupBy.includes(f)} onClick={() => handleGroupByChange(f)}>
                  {f}
                </ToggleChip>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
