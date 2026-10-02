import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Trash2, ChevronDown, ChevronRight, ArrowRight } from 'lucide-react';

const SYSTEMS = ['Salesforce', 'Oracle', 'SAP', 'Google Drive'];
const SYNC_TYPES = ['unidirectional', 'bidirectional'];
const DIRECTIONS = ['source_to_target', 'target_to_source', 'bidirectional'];
const SYSTEM_COLORS: Record<string, string> = {
  Salesforce: 'bg-blue-500', Oracle: 'bg-orange-500', SAP: 'bg-green-500', 'Google Drive': 'bg-red-500',
};

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

function Section({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card className="mb-3">
      <CardHeader className="pb-2 cursor-pointer" onClick={() => setOpen(!open)}>
        <CardTitle className="text-sm flex items-center gap-1.5">
          {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}{title}
        </CardTitle>
      </CardHeader>
      {open && <CardContent className="pt-0">{children}</CardContent>}
    </Card>
  );
}

function SystemBadge({ system }: { system: string }) {
  const color = SYSTEM_COLORS[system] || 'bg-gray-500';
  return <span className={`text-[9px] px-1.5 py-0.5 rounded text-white ${color}`}>{system}</span>;
}

export default function IntegrationFormBuilder({ content, onChange }: { content: string; onChange: (c: string) => void }) {
  const [state, setState] = useState<IntFormState>(() => parseIntegration(content));

  useEffect(() => { onChange(generateYaml(state)); }, [state]);
  const update = (p: Partial<IntFormState>) => setState(s => ({ ...s, ...p }));

  return (
    <div className="p-4 space-y-0">
      <Section title="Integration Header">
        <div className="grid grid-cols-2 gap-3">
          <div><label className="text-[10px] text-muted-foreground">Name</label>
            <Input value={state.name} onChange={e => update({ name: e.target.value })} placeholder="SF-Oracle Customer Sync" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">ID</label>
            <Input value={state.id} onChange={e => update({ id: e.target.value })} placeholder="INT_SF_ORACLE_V1" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Version</label>
            <Input value={state.version} onChange={e => update({ version: e.target.value })} placeholder="1.0" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Frequency</label>
            <Input value={state.frequency} onChange={e => update({ frequency: e.target.value })} placeholder="Every 15 minutes" className="text-xs" /></div>
        </div>
        <div className="mt-3 flex items-center gap-3">
          <div className="flex-1">
            <label className="text-[10px] text-muted-foreground">Source System</label>
            <select value={state.sourceSystem} onChange={e => update({ sourceSystem: e.target.value })}
              className="w-full rounded border bg-card px-2 py-1.5 text-xs">
              {SYSTEMS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground mt-4" />
          <div className="flex-1">
            <label className="text-[10px] text-muted-foreground">Target System</label>
            <select value={state.targetSystem} onChange={e => update({ targetSystem: e.target.value })}
              className="w-full rounded border bg-card px-2 py-1.5 text-xs">
              {SYSTEMS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
        <div className="mt-3">
          <label className="text-[10px] text-muted-foreground">Sync Type</label>
          <div className="flex gap-2 mt-1">
            {SYNC_TYPES.map(t => (
              <button key={t} onClick={() => update({ syncType: t })}
                className={`px-3 py-1 rounded text-xs ${state.syncType === t ? 'bg-blue-600/20 text-blue-300 border border-blue-500' : 'border text-muted-foreground'}`}>
                {t}
              </button>
            ))}
          </div>
        </div>
      </Section>

      <Section title="Description" defaultOpen={false}>
        <textarea value={state.description} onChange={e => update({ description: e.target.value })}
          className="w-full h-16 p-2 rounded border bg-card text-xs resize-none" placeholder="Describe this integration..." />
      </Section>

      <Section title={`Field Mappings (${state.mappings.length} groups)`}>
        {state.mappings.map((m, mi) => (
          <Card key={mi} className="mb-3 border-dashed">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <Input value={m.name} onChange={e => { const ms = [...state.mappings]; ms[mi] = { ...m, name: e.target.value }; update({ mappings: ms }); }}
                  placeholder="Mapping group name" className="text-xs flex-1" />
                <Button variant="ghost" size="sm" onClick={() => update({ mappings: state.mappings.filter((_, j) => j !== mi) })}><Trash2 className="h-3.5 w-3.5" /></Button>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div><label className="text-[10px] text-muted-foreground">Source Object</label>
                  <Input value={m.sourceObject} onChange={e => { const ms = [...state.mappings]; ms[mi] = { ...m, sourceObject: e.target.value }; update({ mappings: ms }); }}
                    placeholder="Account" className="text-xs" /></div>
                <div><label className="text-[10px] text-muted-foreground">Target Object</label>
                  <Input value={m.targetObject} onChange={e => { const ms = [...state.mappings]; ms[mi] = { ...m, targetObject: e.target.value }; update({ mappings: ms }); }}
                    placeholder="AR_Customer" className="text-xs" /></div>
              </div>

              <div className="text-[10px] text-muted-foreground mb-1">Fields</div>
              <div className="space-y-1.5">
                {m.fields.map((f, fi) => (
                  <div key={fi} className="grid grid-cols-6 gap-1.5 items-center">
                    <Input value={f.source} onChange={e => { const ms = [...state.mappings]; ms[mi].fields[fi] = { ...f, source: e.target.value }; update({ mappings: ms }); }}
                      placeholder="source.field" className="text-[10px] col-span-2" />
                    <select value={f.direction} onChange={e => { const ms = [...state.mappings]; ms[mi].fields[fi] = { ...f, direction: e.target.value }; update({ mappings: ms }); }}
                      className="rounded border bg-card px-1 py-1 text-[10px]">
                      {DIRECTIONS.map(d => <option key={d} value={d}>{d === 'source_to_target' ? '→' : d === 'target_to_source' ? '←' : '↔'}</option>)}
                    </select>
                    <Input value={f.target} onChange={e => { const ms = [...state.mappings]; ms[mi].fields[fi] = { ...f, target: e.target.value }; update({ mappings: ms }); }}
                      placeholder="target.field" className="text-[10px] col-span-2" />
                    <Button variant="ghost" size="sm" onClick={() => { const ms = [...state.mappings]; ms[mi].fields = ms[mi].fields.filter((_, j) => j !== fi); update({ mappings: ms }); }}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
              <Button variant="outline" size="sm" className="mt-2 text-[10px]" onClick={() => {
                const ms = [...state.mappings];
                ms[mi].fields = [...ms[mi].fields, { source: '', target: '', direction: 'source_to_target', transform: '', constraint: '' }];
                update({ mappings: ms });
              }}><Plus className="h-3 w-3 mr-1" />Add Field</Button>
            </CardContent>
          </Card>
        ))}
        <Button variant="outline" size="sm" onClick={() => update({ mappings: [...state.mappings, { name: '', sourceObject: '', targetObject: '', direction: '', fields: [] }] })}>
          <Plus className="h-3.5 w-3.5 mr-1" />Add Mapping Group
        </Button>
      </Section>

      <Section title="Failure Handling" defaultOpen={false}>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="text-[10px] text-muted-foreground">Retry Count</label>
            <Input type="number" value={state.retryCount} onChange={e => update({ retryCount: parseInt(e.target.value) || 0 })} className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Retry Interval</label>
            <Input value={state.retryInterval} onChange={e => update({ retryInterval: e.target.value })} placeholder="5 minutes" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Alert Email</label>
            <Input value={state.alertEmail} onChange={e => update({ alertEmail: e.target.value })} placeholder="team@company.com" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Fallback Strategy</label>
            <Input value={state.fallback} onChange={e => update({ fallback: e.target.value })} placeholder="Source system is authoritative" className="text-xs" /></div>
        </div>
      </Section>

      <Section title="Dependencies" defaultOpen={false}>
        {state.dependencies.map((d, i) => (
          <div key={i} className="grid grid-cols-4 gap-2 mb-2">
            <Input value={d.entity} onChange={e => { const ds = [...state.dependencies]; ds[i] = { ...d, entity: e.target.value }; update({ dependencies: ds }); }} placeholder="Entity" className="text-xs" />
            <select value={d.system} onChange={e => { const ds = [...state.dependencies]; ds[i] = { ...d, system: e.target.value }; update({ dependencies: ds }); }}
              className="rounded border bg-card px-2 py-1.5 text-xs"><option value="">System...</option>{SYSTEMS.map(s => <option key={s} value={s}>{s}</option>)}</select>
            <Input value={d.relationship} onChange={e => { const ds = [...state.dependencies]; ds[i] = { ...d, relationship: e.target.value }; update({ dependencies: ds }); }} placeholder="Relationship" className="text-xs" />
            <Button variant="ghost" size="sm" onClick={() => update({ dependencies: state.dependencies.filter((_, j) => j !== i) })}><Trash2 className="h-3.5 w-3.5" /></Button>
          </div>
        ))}
        <Button variant="outline" size="sm" onClick={() => update({ dependencies: [...state.dependencies, { entity: '', system: '', relationship: '' }] })}>
          <Plus className="h-3.5 w-3.5 mr-1" />Add Dependency
        </Button>
      </Section>
    </div>
  );
}
