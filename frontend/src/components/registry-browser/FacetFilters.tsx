import { cn } from '@/lib/utils';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import type { FacetDescriptor, FacetState } from './types';

interface FacetFiltersProps {
  facets: FacetDescriptor[];
  state: FacetState;
  onChange: (next: FacetState) => void;
  className?: string;
}

/**
 * Left-rail multi-select checkboxes. Each facet is a group of options;
 * selections within a facet are OR-combined, and selections across
 * facets are AND-combined (the parent applies that logic when filtering
 * the row list).
 *
 * State is owned by the parent so the same descriptor list can drive
 * both the left rail and the URL search params for deep linking.
 */
export function FacetFilters({ facets, state, onChange, className }: FacetFiltersProps) {
  const toggle = (facetKey: string, optValue: string, checked: boolean) => {
    const next: FacetState = { ...state };
    const curr = new Set(state[facetKey] || []);
    if (checked) curr.add(optValue);
    else curr.delete(optValue);
    if (curr.size === 0) {
      delete next[facetKey];
    } else {
      next[facetKey] = curr;
    }
    onChange(next);
  };

  const clearFacet = (facetKey: string) => {
    const next = { ...state };
    delete next[facetKey];
    onChange(next);
  };

  const clearAll = () => onChange({});

  const totalSelected = Object.values(state).reduce((sum, s) => sum + s.size, 0);

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="font-medium">Filters {totalSelected > 0 ? `(${totalSelected})` : ''}</span>
        {totalSelected > 0 && (
          <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px]" onClick={clearAll}>
            <X className="h-3 w-3 mr-1" /> Clear
          </Button>
        )}
      </div>
      {facets.map((f) => {
        const selected = state[f.key] || new Set<string>();
        const hasSel = selected.size > 0;
        return (
          <div key={f.key} className="space-y-1.5">
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                {f.label}
              </div>
              {hasSel && (
                <button
                  className="text-[10px] text-muted-foreground hover:text-foreground"
                  onClick={() => clearFacet(f.key)}
                >
                  clear
                </button>
              )}
            </div>
            <div className="space-y-1 max-h-44 overflow-auto pr-1">
              {f.options.length === 0 && (
                <div className="text-[11px] text-muted-foreground italic">no options</div>
              )}
              {f.options.map((opt) => {
                const isChecked = selected.has(opt.value);
                return (
                  <label
                    key={opt.value}
                    className={cn(
                      'flex items-center gap-2 text-xs cursor-pointer rounded px-1 py-0.5',
                      'hover:bg-muted/40',
                      isChecked && 'bg-primary/10',
                    )}
                  >
                    <Checkbox
                      checked={isChecked}
                      onCheckedChange={(v) => toggle(f.key, opt.value, !!v)}
                      className="h-3.5 w-3.5"
                    />
                    <span className="flex-1 truncate" title={opt.label || opt.value}>
                      {opt.label || opt.value}
                    </span>
                    {opt.count != null && (
                      <span className="text-[10px] text-muted-foreground font-mono">{opt.count}</span>
                    )}
                  </label>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default FacetFilters;
