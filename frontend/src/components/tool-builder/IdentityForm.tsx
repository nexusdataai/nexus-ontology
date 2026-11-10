import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icon } from '@/components/ds/Icon';
import { SystemLogo } from '@/components/ds/SystemLogo';
import { Field } from '@/components/ds/kit';
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

// Radix Select has no empty value, so this stands for "no connector API".
const NONE = '__none__';

function Section({ title, hint, children }: { title: string; hint: string; children: React.ReactNode }) {
  return (
    <section className="border-b border-border py-6 first:pt-0 last:border-b-0 last:pb-0">
      <h3 className="text-md font-medium text-foreground">{title}</h3>
      <p className="mt-0.5 text-sm text-muted-foreground">{hint}</p>
      <div className="mt-4 space-y-4">{children}</div>
    </section>
  );
}

function ToggleRow({ id, label, hint, checked, onChange }: { id: string; label: string; hint: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-start justify-between gap-6">
      <label htmlFor={id} className="min-w-0 cursor-pointer">
        <span className="block text-sm text-foreground">{label}</span>
        <span className="block text-xs text-muted-foreground">{hint}</span>
      </label>
      <Switch id={id} checked={checked} onCheckedChange={onChange} className="mt-0.5 shrink-0" />
    </div>
  );
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

  // Keep the current binding selectable even before (or without) the API list.
  const apiOptions = apis || [];
  const bindingMissing = !!values.connector_api && !apiOptions.some(a => a.api_id === values.connector_api);

  return (
    <div className="max-w-[720px]">
      <Section title="Identity" hint="How the agent and people recognise this tool.">
        <Field label="Name" htmlFor="tool-name" hint={isNew ? 'Lowercase letters, numbers and underscores. It cannot be changed later.' : 'The name cannot be changed after the tool is created.'}>
          <Input
            id="tool-name"
            value={values.name}
            onChange={(e) => set('name', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
            disabled={!isNew}
            className="font-mono"
            placeholder="my_tool_name"
          />
        </Field>
        <Field label="Description" htmlFor="tool-description" hint="The agent reads this to decide when to call the tool. Say what it returns.">
          <Textarea
            id="tool-description"
            value={values.description}
            onChange={(e) => set('description', e.target.value)}
            rows={3}
          />
        </Field>
        <Field label="Tags" htmlFor="tool-tag">
          {values.tags.length > 0 && (
            <div className="mb-2 flex flex-wrap items-center gap-1.5">
              {values.tags.map((t) => (
                <span key={t} className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-surface-2 pl-2 pr-1 text-xs text-foreground">
                  {t}
                  <button
                    type="button"
                    aria-label={`Remove tag ${t}`}
                    onClick={() => onChange({ ...values, tags: values.tags.filter((x) => x !== t) })}
                    className="flex h-5 w-5 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <Icon name="close" className="h-2.5 w-2.5" />
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <Input
              id="tool-tag"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addTag();
                }
              }}
              placeholder="Add a tag"
              className="max-w-xs"
            />
            <Button type="button" variant="outline" onClick={addTag} disabled={!tagInput.trim()}>Add</Button>
          </div>
        </Field>
      </Section>

      <Section title="Access and safety" hint="What the tool may touch and when a person must approve it.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Risk level" htmlFor="tool-risk">
            <Select value={values.risk_level} onValueChange={(v) => set('risk_level', v as RiskLevel)}>
              <SelectTrigger id="tool-risk"><SelectValue /></SelectTrigger>
              <SelectContent>
                {RISK_OPTIONS.map((r) => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Connector API" htmlFor="tool-api" hint="The source-system call this tool makes, if any.">
            <Select value={values.connector_api ?? NONE} onValueChange={(v) => set('connector_api', v === NONE ? null : v)}>
              <SelectTrigger id="tool-api"><SelectValue placeholder="None" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>None</SelectItem>
                {bindingMissing && <SelectItem value={values.connector_api!}><span className="font-mono text-xs">{values.connector_api}</span></SelectItem>}
                {apiOptions.map((a) => (
                  <SelectItem key={a.api_id} value={a.api_id}>
                    <span className="flex items-center gap-2">
                      <SystemLogo system={a.target_system} size="xs" />
                      <span className="font-mono text-xs">{a.api_id}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        </div>
        <ToggleRow
          id="tool-approval"
          label="Requires approval"
          hint="A person must approve each run before the tool changes anything."
          checked={values.requires_approval}
          onChange={(v) => set('requires_approval', v)}
        />
        <ToggleRow
          id="tool-cacheable"
          label="Cache results"
          hint="For read-only tools. The same inputs return the stored result for 120 seconds."
          checked={values.cacheable}
          onChange={(v) => set('cacheable', v)}
        />
      </Section>
    </div>
  );
}
