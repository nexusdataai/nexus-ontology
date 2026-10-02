import { useEffect, useState } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Loader2 } from 'lucide-react';
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
    <div>
      <Label className="text-xs text-muted-foreground">Virtual Entity</Label>
      <Select value={value || undefined} onValueChange={onChange}>
        <SelectTrigger className="h-8 text-xs mt-1">
          {loading ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <SelectValue placeholder="Select entity..." />
          )}
        </SelectTrigger>
        <SelectContent>
          {entities.map((e) => (
            <SelectItem key={e.virtual_entity} value={e.virtual_entity} className="text-xs">
              <span>{e.virtual_entity}</span>
              <span className="text-muted-foreground ml-2">({e.active_rules} rules)</span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
