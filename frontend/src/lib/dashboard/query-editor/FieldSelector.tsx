import { useEffect, useState } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';
import type { FieldDescriptor } from '../types';
import { getVDLDataSource } from '../datasources/vdl-datasource';

interface Props {
  entity: string;
  value: string[];
  onChange: (fields: string[]) => void;
}

/** Toggle chip used for fields and group-by. */
export function ToggleChip({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cn(
        'inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        selected
          ? 'border-brand/50 bg-brand/10 font-medium text-foreground'
          : 'border-border text-muted-foreground hover:border-border-strong hover:text-foreground',
      )}
    >
      {selected && <Icon name="check" className="h-3 w-3 text-primary dark:text-brand-hi" />}
      {children}
    </button>
  );
}

export function FieldSelector({ entity, value, onChange }: Props) {
  const [available, setAvailable] = useState<FieldDescriptor[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!entity) {
      setAvailable([]);
      return;
    }
    setLoading(true);
    getVDLDataSource()
      .getEntityFields(entity)
      .then(setAvailable)
      .catch(() => setAvailable([]))
      .finally(() => setLoading(false));
  }, [entity]);

  const toggle = (field: string) => {
    if (value.includes(field)) {
      onChange(value.filter((f) => f !== field));
    } else {
      onChange([...value, field]);
    }
  };

  const selectAll = () => onChange(available.map((f) => f.name));
  const clearAll = () => onChange([]);

  if (!entity) return null;

  return (
    <div className="min-w-0">
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span className="text-xs font-medium text-muted-foreground">
          Fields
          {available.length > 0 && (
            <span className="num ml-1.5 font-normal text-subtle-foreground">
              {value.length === 0 ? 'all' : value.length} of {available.length}
            </span>
          )}
        </span>
        {available.length > 0 && (
          <span className="flex items-center gap-3 text-xs">
            <button onClick={selectAll} className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline" type="button">Select all</button>
            <button onClick={clearAll} className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline" type="button">Clear</button>
          </span>
        )}
      </div>
      {loading ? (
        <div className="flex flex-wrap gap-1.5" aria-busy="true">
          {[72, 96, 64, 88, 80].map((w, i) => <Skeleton key={i} className="h-7" style={{ width: w }} />)}
        </div>
      ) : available.length === 0 ? (
        <p className="text-xs text-muted-foreground">No fields were found for this entity. Leave this empty to use every field.</p>
      ) : (
        <>
          <div className="scroll-thin flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
            {available.map((f) => (
              <ToggleChip key={f.name} selected={value.includes(f.name)} onClick={() => toggle(f.name)}>
                {f.name}
                <span className="font-normal text-subtle-foreground">{f.type}</span>
              </ToggleChip>
            ))}
          </div>
          {value.length === 0 && <p className="mt-1 text-xs text-subtle-foreground">Nothing selected: the panel uses every field.</p>}
        </>
      )}
    </div>
  );
}
