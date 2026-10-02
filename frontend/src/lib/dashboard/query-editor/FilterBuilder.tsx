import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Plus, Trash2 } from 'lucide-react';
import type { QueryFilter } from '../types';

interface Props {
  value: QueryFilter[];
  onChange: (filters: QueryFilter[]) => void;
  availableFields?: string[];
}

const OPERATORS = [
  { value: 'eq', label: '=' },
  { value: 'neq', label: '!=' },
  { value: 'gt', label: '>' },
  { value: 'gte', label: '>=' },
  { value: 'lt', label: '<' },
  { value: 'lte', label: '<=' },
  { value: 'contains', label: 'contains' },
  { value: 'in', label: 'in' },
] as const;

export function FilterBuilder({ value, onChange, availableFields }: Props) {
  const addFilter = () => {
    onChange([...value, { field: '', operator: 'eq', value: '' }]);
  };

  const updateFilter = (index: number, patch: Partial<QueryFilter>) => {
    const updated = value.map((f, i) => (i === index ? { ...f, ...patch } : f));
    onChange(updated);
  };

  const removeFilter = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <Label className="text-xs text-muted-foreground">Filters</Label>
        <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={addFilter} type="button">
          <Plus className="h-3 w-3 mr-1" /> Add Filter
        </Button>
      </div>
      {value.length === 0 && (
        <p className="text-[10px] text-muted-foreground mt-1">No filters applied</p>
      )}
      <div className="space-y-1.5 mt-1">
        {value.map((filter, i) => (
          <div key={i} className="flex items-center gap-1.5">
            {availableFields?.length ? (
              <Select value={filter.field || undefined} onValueChange={(v) => updateFilter(i, { field: v })}>
                <SelectTrigger className="h-7 text-[10px] w-[120px]">
                  <SelectValue placeholder="Field" />
                </SelectTrigger>
                <SelectContent>
                  {availableFields.map((f) => (
                    <SelectItem key={f} value={f} className="text-[10px]">{f}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input
                className="h-7 text-[10px] w-[120px]"
                value={filter.field}
                onChange={(e) => updateFilter(i, { field: e.target.value })}
                placeholder="Field"
              />
            )}
            <Select
              value={filter.operator}
              onValueChange={(v) => updateFilter(i, { operator: v as QueryFilter['operator'] })}
            >
              <SelectTrigger className="h-7 text-[10px] w-[80px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {OPERATORS.map((op) => (
                  <SelectItem key={op.value} value={op.value} className="text-[10px]">{op.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              className="h-7 text-[10px] flex-1"
              value={String(filter.value)}
              onChange={(e) => updateFilter(i, { value: e.target.value })}
              placeholder="Value"
            />
            <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => removeFilter(i)} type="button">
              <Trash2 className="h-3 w-3 text-destructive" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
