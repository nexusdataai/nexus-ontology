import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Play } from 'lucide-react';
import type { PanelQuery, FieldDescriptor } from '../types';
import { EntitySelector } from './EntitySelector';
import { FieldSelector } from './FieldSelector';
import { FilterBuilder } from './FilterBuilder';
import { AggregationConfig } from './AggregationConfig';
import { getVDLDataSource } from '../datasources/vdl-datasource';

interface Props {
  query: PanelQuery;
  onChange: (query: PanelQuery) => void;
  onRunQuery: () => void;
}

export function VDLQueryEditor({ query, onChange, onRunQuery }: Props) {
  const [availableFields, setAvailableFields] = useState<FieldDescriptor[]>([]);

  useEffect(() => {
    if (!query.entity) {
      setAvailableFields([]);
      return;
    }
    getVDLDataSource()
      .getEntityFields(query.entity)
      .then(setAvailableFields)
      .catch(() => setAvailableFields([]));
  }, [query.entity]);

  const fieldNames = availableFields.map((f) => f.name);

  const handleEntityChange = useCallback(
    (entity: string) => {
      onChange({ ...query, entity, fields: [], filters: [], aggregation: undefined, groupBy: undefined });
    },
    [query, onChange],
  );

  const handleFieldsChange = useCallback(
    (fields: string[]) => onChange({ ...query, fields }),
    [query, onChange],
  );

  return (
    <div className="space-y-3 p-3 border rounded-lg bg-card">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">Query {query.refId}</span>
        <Button variant="outline" size="sm" className="h-7 text-xs" onClick={onRunQuery} type="button">
          <Play className="h-3 w-3 mr-1" /> Run
        </Button>
      </div>

      <EntitySelector value={query.entity} onChange={handleEntityChange} />

      {query.entity && (
        <>
          <FieldSelector entity={query.entity} value={query.fields || []} onChange={handleFieldsChange} />

          <FilterBuilder
            value={query.filters || []}
            onChange={(filters) => onChange({ ...query, filters })}
            availableFields={fieldNames}
          />

          <AggregationConfig
            aggregation={query.aggregation}
            groupBy={query.groupBy || []}
            onAggregationChange={(agg) => onChange({ ...query, aggregation: agg })}
            onGroupByChange={(groupBy) => onChange({ ...query, groupBy })}
            availableFields={fieldNames}
          />

          <div className="flex gap-2">
            <div className="flex-1">
              <Label className="text-xs text-muted-foreground">Order By</Label>
              <div className="flex gap-1 mt-1">
                {fieldNames.length > 0 ? (
                  <Select
                    value={query.orderBy?.replace(/\s+(ASC|DESC)$/i, '').trim() || '__none__'}
                    onValueChange={(v) => {
                      if (v === '__none__') {
                        onChange({ ...query, orderBy: undefined });
                        return;
                      }
                      const dir = query.orderBy?.match(/\s+(ASC|DESC)$/i)?.[1] || '';
                      onChange({ ...query, orderBy: `${v}${dir ? ' ' + dir : ''}` });
                    }}
                  >
                    <SelectTrigger className="h-7 text-[10px] flex-1">
                      <SelectValue placeholder="None" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__" className="text-[10px]">None</SelectItem>
                      {fieldNames.map((f) => (
                        <SelectItem key={f} value={f} className="text-[10px]">{f}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    className="h-7 text-[10px] flex-1"
                    value={query.orderBy || ''}
                    onChange={(e) => onChange({ ...query, orderBy: e.target.value || undefined })}
                    placeholder="field ASC/DESC"
                  />
                )}
                <Select
                  value={query.orderBy?.match(/\s+(ASC|DESC)$/i)?.[1]?.toUpperCase() || 'ASC'}
                  onValueChange={(dir) => {
                    const field = query.orderBy?.replace(/\s+(ASC|DESC)$/i, '').trim();
                    if (field) onChange({ ...query, orderBy: `${field} ${dir}` });
                  }}
                >
                  <SelectTrigger className="h-7 text-[10px] w-[70px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ASC" className="text-[10px]">ASC</SelectItem>
                    <SelectItem value="DESC" className="text-[10px]">DESC</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="w-[80px]">
              <Label className="text-xs text-muted-foreground">Limit</Label>
              <Input
                className="h-7 text-[10px] mt-1"
                type="number"
                value={query.limit ?? 100}
                onChange={(e) => onChange({ ...query, limit: Number(e.target.value) || 100 })}
                min={1}
                max={10000}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
