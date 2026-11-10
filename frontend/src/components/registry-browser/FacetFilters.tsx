import { cn } from '@/lib/utils';
import { Checkbox } from '@/components/ui/checkbox';
import type { FacetDescriptor, FacetState } from './types';

interface FacetFiltersProps {
  facets: FacetDescriptor[];
  state: FacetState;
  onChange: (next: FacetState) => void;
  className?: string;
}

const linkBtn = 'rounded text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

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
    <div className={cn('flex flex-col gap-5', className)}>
      <div className="flex h-5 items-center justify-between">
        <span className="text-sm font-medium text-foreground">
          Filters {totalSelected > 0 ? <span className="num font-normal text-muted-foreground">{`(${totalSelected})`}</span> : ''}
        </span>
        {totalSelected > 0 && (
          <button type="button" className={linkBtn} onClick={clearAll}>Clear</button>
        )}
      </div>
      {facets.map((f) => {
        const selected = state[f.key] || new Set<string>();
        const hasSel = selected.size > 0;
        return (
          <div key={f.key}>
            <div className="mb-1 flex items-center justify-between">
              <div className="text-xs font-medium text-muted-foreground">{f.label}</div>
              {hasSel && (
                <button type="button" className={linkBtn} aria-label={`Reset ${f.label}`} onClick={() => clearFacet(f.key)}>
                  Reset
                </button>
              )}
            </div>
            <div className="scroll-thin -mx-1.5 max-h-48 overflow-auto">
              {f.options.length === 0 && (
                <div className="px-1.5 text-xs text-subtle-foreground">No options</div>
              )}
              {f.options.map((opt) => {
                const isChecked = selected.has(opt.value);
                return (
                  <label
                    key={opt.value}
                    className={cn(
                      'flex min-h-8 cursor-pointer items-center gap-2.5 rounded-md px-1.5 text-sm transition-colors duration-150 hover:bg-accent/70',
                      isChecked ? 'text-foreground' : 'text-muted-foreground',
                    )}
                  >
                    <Checkbox
                      checked={isChecked}
                      onCheckedChange={(v) => toggle(f.key, opt.value, !!v)}
                    />
                    <span className="flex-1 truncate" title={opt.label || opt.value}>
                      {opt.label || opt.value}
                    </span>
                    {opt.count != null && (
                      <span className="num text-xs text-subtle-foreground">{opt.count}</span>
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
