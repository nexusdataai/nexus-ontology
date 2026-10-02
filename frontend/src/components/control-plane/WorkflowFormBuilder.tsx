import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Trash2, ChevronDown, ChevronRight, ChevronUp, ArrowRight } from 'lucide-react';

const SYSTEMS = ['Salesforce', 'Oracle', 'SAP', 'Google Drive', 'Internal', 'External', 'Cross-System'];
const SYSTEM_COLORS: Record<string, string> = {
  Salesforce: 'bg-blue-500', Oracle: 'bg-orange-500', SAP: 'bg-green-500',
  'Google Drive': 'bg-red-500', Internal: 'bg-gray-500', External: 'bg-purple-500', 'Cross-System': 'bg-indigo-500',
};

interface WfStep { name: string; system: string; action: string; sla: string; failureAction: string }
interface WfDep { entity: string; system: string; relationship: string }

interface WfFormState {
  id: string; name: string; version: string; system: string;
  triggerObject: string; triggerField: string; triggerCondition: string;
  description: string;
  steps: WfStep[];
  dependencies: WfDep[];
}

function parseWorkflow(content: string): WfFormState {
  const s: WfFormState = {
    id: '', name: '', version: '1.0', system: '', triggerObject: '', triggerField: '', triggerCondition: '',
    description: '', steps: [], dependencies: [],
  };
  for (const line of content.split('\n')) {
    if (line.match(/^id:/)) s.id = line.split(':').slice(1).join(':').trim();
    if (line.match(/^name:/)) s.name = line.split(':').slice(1).join(':').trim();
    if (line.match(/^version:/)) s.version = line.split(':').slice(1).join(':').trim().replace(/"/g, '');
    if (line.match(/^system:/)) s.system = line.split(':').slice(1).join(':').trim();
  }
  return s;
}

function generateYaml(s: WfFormState): string {
  let y = `id: ${s.id || 'WF_UNTITLED_V1'}\n`;
  y += `name: ${s.name || 'Untitled Workflow'}\n`;
  y += `version: "${s.version}"\n`;
  y += `system: ${s.system || 'Internal'}\n`;
  if (s.triggerObject || s.triggerField) {
    y += `trigger:\n  object: ${s.triggerObject}\n  field: ${s.triggerField}\n`;
    if (s.triggerCondition) y += `  condition: "${s.triggerCondition}"\n`;
  }
  if (s.description) y += `description: >\n  ${s.description}\n`;
  y += '\nsteps:\n';
  s.steps.forEach((step, i) => {
    y += `  - order: ${i + 1}\n`;
    y += `    name: ${step.name || `Step ${i+1}`}\n`;
    y += `    system: ${step.system || 'Internal'}\n`;
    y += `    action: "${step.action}"\n`;
    if (step.sla) y += `    sla: "${step.sla}"\n`;
    if (step.failureAction) y += `    failure_action: "${step.failureAction}"\n`;
  });
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

export default function WorkflowFormBuilder({ content, onChange }: { content: string; onChange: (c: string) => void }) {
  const [state, setState] = useState<WfFormState>(() => parseWorkflow(content));

  useEffect(() => { onChange(generateYaml(state)); }, [state]);
  const update = (p: Partial<WfFormState>) => setState(s => ({ ...s, ...p }));

  const moveStep = (from: number, to: number) => {
    if (to < 0 || to >= state.steps.length) return;
    const steps = [...state.steps];
    const [moved] = steps.splice(from, 1);
    steps.splice(to, 0, moved);
    update({ steps });
  };

  return (
    <div className="p-4 space-y-0">
      <Section title="Workflow Header">
        <div className="grid grid-cols-2 gap-3">
          <div><label className="text-[10px] text-muted-foreground">Name</label>
            <Input value={state.name} onChange={e => update({ name: e.target.value })} placeholder="Order to Cash" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">ID</label>
            <Input value={state.id} onChange={e => update({ id: e.target.value })} placeholder="WF_ORDER_TO_CASH_V1" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Version</label>
            <Input value={state.version} onChange={e => update({ version: e.target.value })} placeholder="1.0" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Primary System</label>
            <select value={state.system} onChange={e => update({ system: e.target.value })}
              className="w-full rounded border bg-card px-2 py-1.5 text-xs">
              {SYSTEMS.map(s => <option key={s} value={s}>{s}</option>)}
            </select></div>
        </div>
      </Section>

      <Section title="Trigger">
        <div className="grid grid-cols-3 gap-3">
          <div><label className="text-[10px] text-muted-foreground">Object</label>
            <Input value={state.triggerObject} onChange={e => update({ triggerObject: e.target.value })} placeholder="Account" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Field</label>
            <Input value={state.triggerField} onChange={e => update({ triggerField: e.target.value })} placeholder="Credit_Limit__c" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Condition</label>
            <Input value={state.triggerCondition} onChange={e => update({ triggerCondition: e.target.value })} placeholder="Change exceeds threshold" className="text-xs" /></div>
        </div>
      </Section>

      <Section title="Description" defaultOpen={false}>
        <textarea value={state.description} onChange={e => update({ description: e.target.value })}
          className="w-full h-20 p-2 rounded border bg-card text-xs resize-none" placeholder="Describe this workflow..." />
      </Section>

      <Section title={`Steps (${state.steps.length})`}>
        <div className="space-y-2">
          {state.steps.map((step, i) => (
            <div key={i} className="flex items-start gap-2 p-3 rounded-lg border">
              <div className="flex flex-col items-center gap-1 pt-1">
                <span className="w-6 h-6 rounded-full bg-blue-500/20 text-blue-300 text-[10px] flex items-center justify-center font-bold">{i + 1}</span>
                <button onClick={() => moveStep(i, i - 1)} className="text-muted-foreground hover:text-foreground" disabled={i === 0}><ChevronUp className="h-3 w-3" /></button>
                <button onClick={() => moveStep(i, i + 1)} className="text-muted-foreground hover:text-foreground" disabled={i === state.steps.length - 1}><ChevronDown className="h-3 w-3" /></button>
              </div>
              <div className="flex-1 grid grid-cols-2 gap-2">
                <div><label className="text-[10px] text-muted-foreground">Step Name</label>
                  <Input value={step.name} onChange={e => { const ss = [...state.steps]; ss[i] = { ...step, name: e.target.value }; update({ steps: ss }); }} placeholder="Validate Pre-requisites" className="text-xs" /></div>
                <div><label className="text-[10px] text-muted-foreground">System</label>
                  <select value={step.system} onChange={e => { const ss = [...state.steps]; ss[i] = { ...step, system: e.target.value }; update({ steps: ss }); }}
                    className="w-full rounded border bg-card px-2 py-1.5 text-xs">
                    {SYSTEMS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select></div>
                <div className="col-span-2"><label className="text-[10px] text-muted-foreground">Action</label>
                  <Input value={step.action} onChange={e => { const ss = [...state.steps]; ss[i] = { ...step, action: e.target.value }; update({ steps: ss }); }} placeholder="Check risk tier, validate AR balance" className="text-xs" /></div>
                <div><label className="text-[10px] text-muted-foreground">SLA (optional)</label>
                  <Input value={step.sla} onChange={e => { const ss = [...state.steps]; ss[i] = { ...step, sla: e.target.value }; update({ steps: ss }); }} placeholder="48 hours" className="text-xs" /></div>
                <div><label className="text-[10px] text-muted-foreground">Failure Action (optional)</label>
                  <Input value={step.failureAction} onChange={e => { const ss = [...state.steps]; ss[i] = { ...step, failureAction: e.target.value }; update({ steps: ss }); }} placeholder="Reject with reason" className="text-xs" /></div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => update({ steps: state.steps.filter((_, j) => j !== i) })} className="mt-4"><Trash2 className="h-3.5 w-3.5" /></Button>
            </div>
          ))}
        </div>
        <Button variant="outline" size="sm" className="mt-2" onClick={() => update({ steps: [...state.steps, { name: '', system: 'Salesforce', action: '', sla: '', failureAction: '' }] })}>
          <Plus className="h-3.5 w-3.5 mr-1" />Add Step
        </Button>
      </Section>

      <Section title="Dependencies" defaultOpen={false}>
        {state.dependencies.map((d, i) => (
          <div key={i} className="grid grid-cols-4 gap-2 mb-2">
            <Input value={d.entity} onChange={e => { const ds = [...state.dependencies]; ds[i] = { ...d, entity: e.target.value }; update({ dependencies: ds }); }} placeholder="Account" className="text-xs" />
            <select value={d.system} onChange={e => { const ds = [...state.dependencies]; ds[i] = { ...d, system: e.target.value }; update({ dependencies: ds }); }}
              className="rounded border bg-card px-2 py-1.5 text-xs"><option value="">System...</option>{SYSTEMS.map(s => <option key={s} value={s}>{s}</option>)}</select>
            <Input value={d.relationship} onChange={e => { const ds = [...state.dependencies]; ds[i] = { ...d, relationship: e.target.value }; update({ dependencies: ds }); }} placeholder="Source object" className="text-xs" />
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
