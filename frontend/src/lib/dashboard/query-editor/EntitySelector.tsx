import { useEffect, useState } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Field } from '@/components/ds/kit';
import type { VirtualEntitySummary } from '../types';
import { getVDLDataSource } from '../datasources/vdl-datasource';

interface Props {
  value: string;
  onChange: (entity: string) => void;
}

export function EntitySelector({ value, onChange }: Props) {
  const [entities, setEntities] = useState<VirtualEntitySummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getVDLDataSource()
      .getEntities()
      .then(setEntities)
      .catch(() => setEntities([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Field
      label="Entity"
      hint={
        !loading && entities.length === 0
          ? 'No entities are available from the virtual data layer right now.'
          : 'The business object this panel reads from the virtual data layer.'
      }
    >
      {loading ? (
        <Skeleton className="h-9 w-full" />
      ) : (
        <Select value={value || undefined} onValueChange={onChange}>
          <SelectTrigger aria-label="Entity" className="h-9">
            <SelectValue placeholder="Choose an entity" />
          </SelectTrigger>
          <SelectContent>
            {/* Keep a saved entity selectable even if the list no longer has it. */}
            {value && !entities.some((e) => e.virtual_entity === value) && (
              <SelectItem value={value}>{value}</SelectItem>
            )}
            {entities.map((e) => (
              <SelectItem key={e.virtual_entity} value={e.virtual_entity}>
                <span>{e.virtual_entity}</span>
                <span className="num ml-2 text-xs text-muted-foreground">
                  {e.active_rules} {e.active_rules === 1 ? 'mapping rule' : 'mapping rules'}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </Field>
  );
}
