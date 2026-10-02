import { useEffect, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { connectorApiService, type ConnectorAPISpec } from '@/services/connectorApiService';
import { RISK_OPTIONS } from './typings';
import type { RiskLevel } from '@/services/toolBuilderService';

export interface IdentityValues {
  name: string;
  description: string;
  risk_level: RiskLevel;
  requires_approval: boolean;
  cacheable: boolean;
  connector_api: string | null;
  tags: string[];
}

interface Props {
  values: IdentityValues;
  onChange: (next: IdentityValues) => void;
  isNew: boolean;
}

export default function IdentityForm({ values, onChange, isNew }: Props) {
  const [apis, setApis] = useState<ConnectorAPISpec[] | null>(null);
  const [tagInput, setTagInput] = useState('');

  useEffect(() => {
    let cancelled = false;
    connectorApiService.list()
      .then((r) => { if (!cancelled) setApis(r.items || []); })
      .catch(() => { if (!cancelled) setApis([]); });
    return () => { cancelled = true; };
  }, []);

  const set = <K extends keyof IdentityValues>(k: K, v: IdentityValues[K]) =>
    onChange({ ...values, [k]: v });

  const addTag = () => {
    const t = tagInput.trim();
    if (!t) return;
    if (!values.tags.includes(t)) onChange({ ...values, tags: [...values.tags, t] });
    setTagInput('');
  };

  return (
    <div className="space-y-3 text-sm">
      <Field label="Name (lowercase, snake_case)">
        <Input
          value={values.name}
          onChange={(e) => set('name', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
          disabled={!isNew}
          className="h-7 text-[11px] font-mono"
          placeholder="my_tool_name"
        />
      </Field>
      <Field label="Description">
        <textarea
          value={values.description}
          onChange={(e) => set('description', e.target.value)}
          rows={3}
          className="w-full text-[11px] bg-background border rounded p-2"
        />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Risk level">
          <select
            value={values.risk_level}
            onChange={(e) => set('risk_level', e.target.value as RiskLevel)}
            className="h-7 text-[11px] bg-background border rounded px-1 w-full"
          >
            {RISK_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </Field>
        <Field label="Connector API binding">
          <select
            value={values.connector_api ?? ''}
            onChange={(e) => set('connector_api', e.target.value || null)}
            className="h-7 text-[11px] bg-background border rounded px-1 w-full"
          >
            <option value="">(none)</option>
            {(apis || []).map((a) => (
              <option key={a.api_id} value={a.api_id}>
                {a.api_id} ({a.target_system})
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="flex items-center gap-4 text-[11px]">
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="checkbox"
            checked={values.requires_approval}
            onChange={(e) => set('requires_approval', e.target.checked)}
          />
          requires approval
        </label>
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="checkbox"
            checked={values.cacheable}
            onChange={(e) => set('cacheable', e.target.checked)}
          />
          cacheable (read-only tools, 120s TTL)
        </label>
      </div>
      <Field label="Tags">
        <div className="flex items-center gap-1 flex-wrap mb-1">
          {values.tags.map((t) => (
            <Badge
              key={t}
              variant="outline"
              className="text-[10px] cursor-pointer"
              onClick={() => onChange({ ...values, tags: values.tags.filter((x) => x !== t) })}
            >
              {t} <span className="ml-1 text-muted-foreground">x</span>
            </Badge>
          ))}
        </div>
        <div className="flex gap-1">
          <Input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addTag();
              }
            }}
            placeholder="add tag..."
            className="h-7 text-[11px]"
          />
          <button
            type="button"
            onClick={addTag}
            className="h-7 px-2 text-[11px] border rounded"
          >
            Add
          </button>
        </div>
      </Field>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] uppercase text-muted-foreground mb-1">{label}</div>
      {children}
    </div>
  );
}
