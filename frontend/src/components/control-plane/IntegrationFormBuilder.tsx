import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Field } from '@/components/ds/kit';
import { Icon } from '@/components/ds/Icon';
import { AddButton, Choice, FormBody, FormSection, NoRows, RemoveButton, SystemSelect } from './formKit';
import { parseIntegrationDoc } from './knowledgeParsers';

const SYSTEMS = ['Salesforce', 'Oracle', 'SAP', 'Google Drive'];
const SYNC_TYPES = ['unidirectional', 'bidirectional'];
const DIRECTIONS = ['source_to_target', 'target_to_source', 'bidirectional'];

const SYNC_TYPE_LABEL: Record<string, string> = { unidirectional: 'One way', bidirectional: 'Two way', one_way: 'One way', two_way: 'Two way' };
const DIRECTION_LABEL: Record<string, string> = { source_to_target: 'Source to target', target_to_source: 'Target to source', bidirectional: 'Both ways' };

interface FieldMapping { source: string; target: string; direction: string; transform: string; constraint: string }
interface MappingGroup { name: string; sourceObject: string; targetObject: string; direction: string; fields: FieldMapping[] }
interface IntDep { entity: string; system: string; relationship: string }

interface IntFormState {
  id: string; name: string; version: string;
  sourceSystem: string; targetSystem: string;
  syncType: string; frequency: string; description: string;
  mappings: MappingGroup[];
  retryCount: number; retryInterval: string; alertEmail: string; fallback: string;
  dependencies: IntDep[];
}

function parseIntegration(content: string): IntFormState {
  const s: IntFormState = {
    id: '', name: '', version: '1.0', sourceSystem: 'Salesforce', targetSystem: 'Oracle',
    syncType: 'bidirectional', frequency: '', description: '',
    mappings: [], retryCount: 3, retryInterval: '5 minutes', alertEmail: '', fallback: '',
    dependencies: [],
  };
  for (const line of content.split('\n')) {
    if (line.match(/^id:/)) s.id = line.split(':').slice(1).join(':').trim();
    if (line.match(/^name:/)) s.name = line.split(':').slice(1).join(':').trim();
    if (line.match(/^version:/)) s.version = line.split(':').slice(1).join(':').trim().replace(/"/g, '');
    if (line.match(/^source_system:/)) s.sourceSystem = line.split(':').slice(1).join(':').trim();
    if (line.match(/^target_system:/)) s.targetSystem = line.split(':').slice(1).join(':').trim();
    if (line.match(/^sync_type:/)) s.syncType = line.split(':').slice(1).join(':').trim();
    if (line.match(/^frequency:/)) s.frequency = line.split(':').slice(1).join(':').trim().replace(/"/g, '');
  }
  // Open with what the file already holds, so saving from the form keeps
  // its mappings, failure handling and dependencies.
  const doc = parseIntegrationDoc(content);
  s.description = doc.description;
  s.mappings = doc.mappings.map(m => ({ ...m, fields: m.fields.map(f => ({ ...f })) }));
  if (doc.retryCount != null) s.retryCount = doc.retryCount;
  if (doc.retryInterval) s.retryInterval = doc.retryInterval;
  s.alertEmail = doc.alertEmail;
  s.fallback = doc.fallback;
  s.dependencies = doc.dependencies.map(d => ({ ...d }));
  return s;
}

function generateYaml(s: IntFormState): string {
  let y = `id: ${s.id || 'INT_UNTITLED_V1'}\n`;
  y += `name: ${s.name || 'Untitled Integration'}\n`;
  y += `version: "${s.version}"\n`;
  y += `source_system: ${s.sourceSystem}\n`;
  y += `target_system: ${s.targetSystem}\n`;
  y += `sync_type: ${s.syncType}\n`;
  y += `frequency: "${s.frequency}"\n`;
  if (s.description) y += `description: >\n  ${s.description}\n`;

  if (s.mappings.length > 0) {
    y += '\nmappings:\n';
    for (const m of s.mappings) {
      y += `  - name: ${m.name}\n`;
      y += `    source_object: ${m.sourceObject}\n`;
      y += `    target_object: ${m.targetObject}\n`;
      y += `    direction: ${m.direction || `${s.sourceSystem} → ${s.targetSystem}`}\n`;
      if (m.fields.length > 0) {
        y += `    fields:\n`;
        for (const f of m.fields) {
          y += `      - source: ${f.source}\n`;
          y += `        target: ${f.target}\n`;
          y += `        direction: "${f.direction}"\n`;
          if (f.transform) y += `        transformation: "${f.transform}"\n`;
          if (f.constraint) y += `        constraint: "${f.constraint}"\n`;
        }
      }
    }
  }

  y += `\nfailure_handling:\n`;
  y += `  retry_count: ${s.retryCount}\n`;
  y += `  retry_interval: "${s.retryInterval}"\n`;
  if (s.alertEmail) y += `  alert_on_failure: "${s.alertEmail}"\n`;
  if (s.fallback) y += `  fallback: "${s.fallback}"\n`;

  if (s.dependencies.length > 0) {
    y += '\ndependencies:\n';
    for (const d of s.dependencies) {
      y += `  - entity: ${d.entity}\n`;
      if (d.system) y += `    system: ${d.system}\n`;
      y += `    relationship: "${d.relationship}"\n`;
    }
  }
  return y;
}

function DirectionIcon({ direction }: { direction: string }) {
  if (direction === 'target_to_source') return <Icon name="arrow-right" className="h-3.5 w-3.5 rotate-180" />;
  if (direction === 'bidirectional') return <Icon name="shuffle" className="h-3.5 w-3.5" />;
  return <Icon name="arrow-right" className="h-3.5 w-3.5" />;
}

export default function IntegrationFormBuilder({ content, onChange }: { content: string; onChange: (c: string) => void }) {
  const [state, setState] = useState<IntFormState>(() => parseIntegration(content));

  useEffect(() => { onChange(generateYaml(state)); }, [state]);
  const update = (p: Partial<IntFormState>) => setState(s => ({ ...s, ...p }));

  const setMapping = (mi: number, patch: Partial<MappingGroup>) => update({ mappings: state.mappings.map((m, j) => (j === mi ? { ...m, ...patch } : m)) });
  const setMappingField = (mi: number, fi: number, patch: Partial<FieldMapping>) =>
    setMapping(mi, { fields: state.mappings[mi].fields.map((f, j) => (j === fi ? { ...f, ...patch } : f)) });
  const setDep = (i: number, patch: Partial<IntDep>) => update({ dependencies: state.dependencies.map((d, j) => (j === i ? { ...d, ...patch } : d)) });

  const syncTypes = SYNC_TYPES.includes(state.syncType) || !state.syncType ? SYNC_TYPES : [state.syncType, ...SYNC_TYPES];

  return (
    <FormBody>
      <FormSection title="Integration details" hint="Which two systems are connected, in which direction and how often.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" htmlFor="int-name" className="sm:col-span-2">
            <Input id="int-name" value={state.name} onChange={e => update({ name: e.target.value })} placeholder="Salesforce to Oracle customer sync" />
          </Field>
          <div className="grid items-end gap-3 sm:col-span-2 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
            <Field label="Source system">
              <SystemSelect label="Source system" systems={SYSTEMS} value={state.sourceSystem} onChange={(v) => update({ sourceSystem: v })} />
            </Field>
            <Icon name="arrow-right" className="mb-2.5 hidden text-subtle-foreground sm:block" />
            <Field label="Target system">
              <SystemSelect label="Target system" systems={SYSTEMS} value={state.targetSystem} onChange={(v) => update({ targetSystem: v })} />
            </Field>
          </div>
          <Field label="Direction">
            <Choice
              label="Sync direction"
              value={state.syncType}
              onChange={(t) => update({ syncType: t })}
              options={syncTypes.map(t => ({ value: t, label: SYNC_TYPE_LABEL[t] || t }))}
            />
          </Field>
          <Field label="Trigger or frequency" htmlFor="int-freq">
            <Input id="int-freq" value={state.frequency} onChange={e => update({ frequency: e.target.value })} placeholder="Every 15 minutes" />
          </Field>
          <Field label="Integration ID" htmlFor="int-id">
            <Input id="int-id" value={state.id} onChange={e => update({ id: e.target.value })} placeholder="INT_SF_ORACLE_V1" className="font-mono" />
          </Field>
          <Field label="Version" htmlFor="int-version">
            <Input id="int-version" value={state.version} onChange={e => update({ version: e.target.value })} placeholder="1.0" />
          </Field>
          <Field label="Description" htmlFor="int-desc" className="sm:col-span-2">
            <Textarea id="int-desc" value={state.description} onChange={e => update({ description: e.target.value })} rows={3} placeholder="What this integration keeps in step, in a sentence or two" />
          </Field>
        </div>
      </FormSection>

      <FormSection title="Field mappings" count={state.mappings.length} hint="Group fields by the pair of objects they move between.">
        {state.mappings.length === 0 && <NoRows>No mapping groups yet.</NoRows>}
        <div className="border-t border-border">
          {state.mappings.map((m, mi) => (
            <div key={mi} className="border-b border-border py-5">
              <div className="flex items-start gap-2">
                <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_auto_minmax(0,1fr)] sm:items-end">
                  <Field label="Group name" htmlFor={`int-map-name-${mi}`}>
                    <Input id={`int-map-name-${mi}`} value={m.name} onChange={e => setMapping(mi, { name: e.target.value })} placeholder="Customer master" />
                  </Field>
                  <Field label="Source object" htmlFor={`int-map-src-${mi}`}>
                    <Input id={`int-map-src-${mi}`} value={m.sourceObject} onChange={e => setMapping(mi, { sourceObject: e.target.value })} placeholder="Account" className="font-mono" />
                  </Field>
                  <Icon name="arrow-right" className="mb-2.5 hidden text-subtle-foreground sm:block" />
                  <Field label="Target object" htmlFor={`int-map-tgt-${mi}`}>
                    <Input id={`int-map-tgt-${mi}`} value={m.targetObject} onChange={e => setMapping(mi, { targetObject: e.target.value })} placeholder="AR_Customer" className="font-mono" />
                  </Field>
                </div>
                <div className="pt-6"><RemoveButton label={`Remove mapping group ${m.name || mi + 1}`} onClick={() => update({ mappings: state.mappings.filter((_, j) => j !== mi) })} /></div>
              </div>

              <div className="mt-4 space-y-2 sm:pl-4">
                {m.fields.length === 0 && <NoRows>No fields in this group yet.</NoRows>}
                {m.fields.map((f, fi) => (
                  <div key={fi} className="flex items-center gap-2">
                    <div className="grid min-w-0 flex-1 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2">
                      <Input value={f.source} onChange={e => setMappingField(mi, fi, { source: e.target.value })} placeholder="Account.Name" aria-label={`Source field ${fi + 1}`} className="font-mono text-xs" />
                      <Select value={DIRECTIONS.includes(f.direction) ? f.direction : 'source_to_target'} onValueChange={(v) => setMappingField(mi, fi, { direction: v })}>
                        <SelectTrigger className="h-9 w-14 px-2" aria-label={`Direction of field ${fi + 1}: ${DIRECTION_LABEL[f.direction] || 'Source to target'}`}>
                          <SelectValue><DirectionIcon direction={f.direction} /></SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {DIRECTIONS.map(d => (
                            <SelectItem key={d} value={d}>
                              <span className="inline-flex items-center gap-2"><DirectionIcon direction={d} />{DIRECTION_LABEL[d]}</span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Input value={f.target} onChange={e => setMappingField(mi, fi, { target: e.target.value })} placeholder="AR_Customer.customer_name" aria-label={`Target field ${fi + 1}`} className="font-mono text-xs" />
                    </div>
                    <RemoveButton label={`Remove field ${fi + 1}`} onClick={() => setMapping(mi, { fields: m.fields.filter((_, j) => j !== fi) })} />
                  </div>
                ))}
                <div className="pt-1">
                  <AddButton onClick={() => setMapping(mi, { fields: [...m.fields, { source: '', target: '', direction: 'source_to_target', transform: '', constraint: '' }] })}>Add field</AddButton>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3">
          <AddButton onClick={() => update({ mappings: [...state.mappings, { name: '', sourceObject: '', targetObject: '', direction: '', fields: [] }] })}>Add mapping group</AddButton>
        </div>
      </FormSection>

      <FormSection title="If a sync fails" hint="How often to retry, who to tell and which side wins.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Retries" htmlFor="int-retry">
            <Input id="int-retry" type="number" min={0} value={state.retryCount} onChange={e => update({ retryCount: parseInt(e.target.value) || 0 })} />
          </Field>
          <Field label="Wait between retries" htmlFor="int-retry-int">
            <Input id="int-retry-int" value={state.retryInterval} onChange={e => update({ retryInterval: e.target.value })} placeholder="5 minutes" />
          </Field>
          <Field label="Alert email" htmlFor="int-alert">
            <Input id="int-alert" value={state.alertEmail} onChange={e => update({ alertEmail: e.target.value })} placeholder="team@company.com" />
          </Field>
          <Field label="Fallback" htmlFor="int-fallback">
            <Input id="int-fallback" value={state.fallback} onChange={e => update({ fallback: e.target.value })} placeholder="Source system is authoritative" />
          </Field>
        </div>
      </FormSection>

      <FormSection title="Dependencies" count={state.dependencies.length} hint="Entities this integration relies on.">
        {state.dependencies.length === 0 && <NoRows>No dependencies added.</NoRows>}
        <div className="space-y-3">
          {state.dependencies.map((d, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className="grid min-w-0 flex-1 gap-2 sm:grid-cols-3">
                <Input value={d.entity} onChange={e => setDep(i, { entity: e.target.value })} placeholder="Account" aria-label={`Dependency ${i + 1}: entity`} className="font-mono" />
                <SystemSelect label={`Dependency ${i + 1}: system`} systems={SYSTEMS} emptyLabel="Any system" value={d.system} onChange={(v) => setDep(i, { system: v })} />
                <Input value={d.relationship} onChange={e => setDep(i, { relationship: e.target.value })} placeholder="Source entity" aria-label={`Dependency ${i + 1}: relationship`} />
              </div>
              <RemoveButton label={`Remove dependency ${i + 1}`} onClick={() => update({ dependencies: state.dependencies.filter((_, j) => j !== i) })} />
            </div>
          ))}
        </div>
        <div className="mt-3">
          <AddButton onClick={() => update({ dependencies: [...state.dependencies, { entity: '', system: '', relationship: '' }] })}>Add dependency</AddButton>
        </div>
      </FormSection>
    </FormBody>
  );
}
