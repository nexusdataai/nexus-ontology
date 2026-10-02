import { useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import type { PanelQuery } from '../types';
import { VDLQueryEditor } from '../query-editor/VDLQueryEditor';
import { NLQueryInput } from '../query-editor/NLQueryInput';
import type { NLQueryResponse } from '../datasources/vdl-datasource';

interface Props {
  targets: PanelQuery[];
  onChange: (targets: PanelQuery[]) => void;
  onRunQuery: () => void;
  onPanelTypeChange?: (type: string) => void;
  onTitleChange?: (title: string) => void;
}

const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

export function QueryTab({ targets, onChange, onRunQuery, onPanelTypeChange, onTitleChange }: Props) {
  const addQuery = () => {
    const nextRef = LETTERS[targets.length] || `Q${targets.length + 1}`;
    onChange([...targets, { refId: nextRef, entity: '' }]);
  };

  const updateQuery = (index: number, query: PanelQuery) => {
    const updated = targets.map((t, i) => (i === index ? query : t));
    onChange(updated);
  };

  const removeQuery = (index: number) => {
    if (targets.length <= 1) return;
    onChange(targets.filter((_, i) => i !== index));
  };

  const handleNLQuery = useCallback((response: NLQueryResponse) => {
    const pq = response.panel_query;
    if (!pq.entity) return;

    const newTarget: PanelQuery = {
      refId: targets[0]?.refId || 'A',
      entity: pq.entity,
      fields: pq.fields || undefined,
      filters: pq.filters?.map((f) => ({
        field: f.field,
        operator: f.operator as PanelQuery['filters'] extends Array<infer T> ? T extends { operator: infer O } ? O : string : string,
        value: f.value,
      })) as PanelQuery['filters'],
      aggregation: pq.aggregation ? { function: pq.aggregation.function as 'count' | 'sum' | 'avg' | 'min' | 'max', field: pq.aggregation.field } : undefined,
      groupBy: pq.groupBy || undefined,
      orderBy: pq.orderBy || undefined,
      limit: pq.limit || 100,
    };

    const updated = targets.length > 0
      ? targets.map((t, i) => (i === 0 ? newTarget : t))
      : [newTarget];
    onChange(updated);

    if (response.suggested_panel_type && onPanelTypeChange) {
      onPanelTypeChange(response.suggested_panel_type);
    }
    if (response.suggested_title && onTitleChange) {
      onTitleChange(response.suggested_title);
    }
  }, [targets, onChange, onPanelTypeChange, onTitleChange]);

  return (
    <div className="space-y-3">
      <NLQueryInput
        onQueryGenerated={handleNLQuery}
        currentEntity={targets[0]?.entity}
      />

      {targets.map((target, i) => (
        <div key={target.refId} className="relative">
          <VDLQueryEditor
            query={target}
            onChange={(q) => updateQuery(i, q)}
            onRunQuery={onRunQuery}
          />
          {targets.length > 1 && (
            <Button
              variant="ghost"
              size="sm"
              className="absolute top-2 right-14 h-6 text-[10px] text-destructive"
              onClick={() => removeQuery(i)}
              type="button"
            >
              Remove
            </Button>
          )}
        </div>
      ))}
      <Button variant="outline" size="sm" className="h-7 text-xs w-full" onClick={addQuery} type="button">
        <Plus className="h-3 w-3 mr-1" /> Add Query
      </Button>
    </div>
  );
}
