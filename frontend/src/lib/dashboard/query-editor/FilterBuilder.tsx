import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icon } from '@/components/ds/Icon';
import type { QueryFilter } from '../types';

interface Props {
  value: QueryFilter[];
  onChange: (filters: QueryFilter[]) => void;
  availableFields?: string[];
}

const OPERATORS = [
  { value: 'eq', label: 'is' },
  { value: 'neq', label: 'is not' },
  { value: 'gt', label: 'greater than' },
  { value: 'gte', label: 'at least' },
  { value: 'lt', label: 'less than' },
  { value: 'lte', label: 'at most' },
  { value: 'contains', label: 'contains' },
  { value: 'in', label: 'is one of' },
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
    <div className="min-w-0">
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <span className="text-xs font-medium text-muted-foreground">Filters</span>
        <Button variant="ghost" size="sm" className="-mr-2 h-7 px-2" onClick={addFilter} type="button">
          <Icon name="plus" className="h-3 w-3" /> Add filter
        </Button>
      </div>
      {value.length === 0 ? (
        <p className="text-xs text-subtle-foreground">No filters: the panel uses every row.</p>
      ) : (
        <ul className="space-y-2">
          {value.map((filter, i) => (
            <li key={i} className="flex flex-wrap items-center gap-1.5">
              {availableFields?.length ? (
                <Select value={filter.field || undefined} onValueChange={(v) => updateFilter(i, { field: v })}>
                  <SelectTrigger aria-label="Filter field" className="h-8 min-w-[120px] flex-1 basis-32">
                    <SelectValue placeholder="Field" />
                  </SelectTrigger>
                  <SelectContent>
                    {/* Keep a saved field visible even if the entity no longer lists it. */}
                    {filter.field && !availableFields.includes(filter.field) && (
                      <SelectItem value={filter.field}>{filter.field}</SelectItem>
                    )}
                    {availableFields.map((f) => (
                      <SelectItem key={f} value={f}>{f}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  className="h-8 min-w-[120px] flex-1 basis-32"
                  value={filter.field}
                  onChange={(e) => updateFilter(i, { field: e.target.value })}
                  placeholder="Field"
                  aria-label="Filter field"
                />
              )}
              <Select
                value={filter.operator}
                onValueChange={(v) => updateFilter(i, { operator: v as QueryFilter['operator'] })}
              >
                <SelectTrigger aria-label="Condition" className="h-8 w-[128px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OPERATORS.map((op) => (
                    <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                className="h-8 min-w-[100px] flex-1 basis-28"
                value={String(filter.value)}
                onChange={(e) => updateFilter(i, { value: e.target.value })}
                placeholder="Value"
                aria-label="Filter value"
              />
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                onClick={() => removeFilter(i)}
                type="button"
                aria-label="Remove filter"
              >
                <Icon name="trash" className="h-3.5 w-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
