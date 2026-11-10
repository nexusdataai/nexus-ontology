import { useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ds/Icon';
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

/** The "Data" section of the panel editor: one or more queries on virtual entities. */
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

  const many = targets.length > 1;

  return (
    <div className="space-y-5">
      <NLQueryInput
        onQueryGenerated={handleNLQuery}
        currentEntity={targets[0]?.entity}
      />

      {targets.map((target, i) => (
        <div key={target.refId} className={many ? 'border-t border-border pt-4' : undefined}>
          {many && (
            <div className="mb-3 flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-foreground">Query {target.refId}</span>
              <Button
                variant="ghost"
                size="sm"
                className="-mr-2 h-7 px-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                onClick={() => removeQuery(i)}
                type="button"
              >
                <Icon name="trash" className="h-3 w-3" /> Remove query
              </Button>
            </div>
          )}
          <VDLQueryEditor
            query={target}
            onChange={(q) => updateQuery(i, q)}
            onRunQuery={onRunQuery}
          />
        </div>
      ))}

      <Button variant="ghost" size="sm" className="-ml-2 px-2" onClick={addQuery} type="button">
        <Icon name="plus" className="h-3 w-3" /> Add another query
      </Button>
    </div>
  );
}
