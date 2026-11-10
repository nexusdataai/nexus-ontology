import { useCallback, useEffect, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Field } from '@/components/ds/kit';
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

const NONE = '__none__';

/** One query on a virtual entity: entity, fields, filters, summary, sort, limit. */
export function VDLQueryEditor({ query, onChange }: Props) {
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

  const sortField = query.orderBy?.replace(/\s+(ASC|DESC)$/i, '').trim() || '';

  return (
    <div className="space-y-4">
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

          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_132px_96px]">
            <Field label="Sort by">
              {fieldNames.length > 0 ? (
                <Select
                  value={sortField || NONE}
                  onValueChange={(v) => {
                    if (v === NONE) {
                      onChange({ ...query, orderBy: undefined });
                      return;
                    }
                    const dir = query.orderBy?.match(/\s+(ASC|DESC)$/i)?.[1] || '';
                    onChange({ ...query, orderBy: `${v}${dir ? ' ' + dir : ''}` });
                  }}
                >
                  <SelectTrigger aria-label="Sort by" className="h-8">
                    <SelectValue placeholder="No sorting" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>No sorting</SelectItem>
                    {sortField && !fieldNames.includes(sortField) && (
                      <SelectItem value={sortField}>{sortField}</SelectItem>
                    )}
                    {fieldNames.map((f) => (
                      <SelectItem key={f} value={f}>{f}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  className="h-8"
                  value={query.orderBy || ''}
                  onChange={(e) => onChange({ ...query, orderBy: e.target.value || undefined })}
                  placeholder="Field name, then ASC or DESC"
                  aria-label="Sort by"
                />
              )}
            </Field>
            <Field label="Direction">
              <Select
                value={query.orderBy?.match(/\s+(ASC|DESC)$/i)?.[1]?.toUpperCase() || 'ASC'}
                onValueChange={(dir) => {
                  const field = query.orderBy?.replace(/\s+(ASC|DESC)$/i, '').trim();
                  if (field) onChange({ ...query, orderBy: `${field} ${dir}` });
                }}
              >
                <SelectTrigger aria-label="Sort direction" className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ASC">Ascending</SelectItem>
                  <SelectItem value="DESC">Descending</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="Row limit">
              <Input
                className="num h-8"
                type="number"
                value={query.limit ?? 100}
                onChange={(e) => onChange({ ...query, limit: Number(e.target.value) || 100 })}
                min={1}
                max={10000}
                aria-label="Row limit"
              />
            </Field>
          </div>
        </>
      )}
    </div>
  );
}
