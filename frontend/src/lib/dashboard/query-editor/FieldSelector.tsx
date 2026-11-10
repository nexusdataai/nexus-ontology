import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Loader2, X } from 'lucide-react';
import type { FieldDescriptor } from '../types';
import { getVDLDataSource } from '../datasources/vdl-datasource';

interface Props {
  entity: string;
  value: string[];
  onChange: (fields: string[]) => void;
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
    <div>
      <div className="flex items-center justify-between">
        <Label className="text-xs text-muted-foreground">Fields</Label>
        <div className="flex gap-1">
          <button onClick={selectAll} className="text-xs text-primary hover:underline" type="button">All</button>
          <span className="text-xs text-muted-foreground">|</span>
          <button onClick={clearAll} className="text-xs text-primary hover:underline" type="button">None</button>
        </div>
      </div>
      {loading ? (
        <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" /> Loading fields...
        </div>
      ) : (
        <div className="flex flex-wrap gap-1 mt-1">
          {available.map((f) => {
            const selected = value.includes(f.name);
            return (
              <Badge
                key={f.name}
                variant={selected ? 'default' : 'outline'}
                className="text-xs cursor-pointer select-none"
                onClick={() => toggle(f.name)}
              >
                {f.name}
                <span className="text-muted-foreground ml-1">({f.type})</span>
                {selected && <X className="h-2.5 w-2.5 ml-0.5" />}
              </Badge>
            );
          })}
          {available.length === 0 && !loading && (
            <span className="text-xs text-muted-foreground">No fields found. Leave empty to select all.</span>
          )}
        </div>
      )}
    </div>
  );
}
