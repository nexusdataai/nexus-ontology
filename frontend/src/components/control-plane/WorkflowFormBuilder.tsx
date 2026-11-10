import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Field, StatusPill } from '@/components/ds/kit';
import { Icon } from '@/components/ds/Icon';
import { AddButton, FormBody, FormSection, NoRows, RemoveButton, SystemSelect } from './formKit';
import { isApprovalStep, parseWorkflowDoc } from './knowledgeParsers';

const SYSTEMS = ['Salesforce', 'Oracle', 'SAP', 'Google Drive', 'Internal', 'External', 'Cross-System'];

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
  // Open with what the file already holds, so saving from the form keeps
  // its trigger, steps and dependencies.
  const doc = parseWorkflowDoc(content);
  s.triggerObject = doc.trigger.object;
  s.triggerField = doc.trigger.field;
  s.triggerCondition = doc.trigger.condition;
  s.description = doc.description;
  s.steps = doc.steps.map(st => ({ name: st.name, system: st.system, action: st.action, sla: st.sla, failureAction: st.failureAction }));
  s.dependencies = doc.dependencies.map(d => ({ ...d }));
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

  const setStep = (i: number, patch: Partial<WfStep>) => update({ steps: state.steps.map((s, j) => (j === i ? { ...s, ...patch } : s)) });
  const setDep = (i: number, patch: Partial<WfDep>) => update({ dependencies: state.dependencies.map((d, j) => (j === i ? { ...d, ...patch } : d)) });

  return (
    <FormBody>
      <FormSection title="Workflow details" hint="The name the agent uses for this process and the system that owns it.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" htmlFor="wf-name" className="sm:col-span-2">
            <Input id="wf-name" value={state.name} onChange={e => update({ name: e.target.value })} placeholder="Order to cash" />
          </Field>
          <Field label="Workflow ID" htmlFor="wf-id">
            <Input id="wf-id" value={state.id} onChange={e => update({ id: e.target.value })} placeholder="WF_ORDER_TO_CASH_V1" className="font-mono" />
          </Field>
          <Field label="Version" htmlFor="wf-version">
            <Input id="wf-version" value={state.version} onChange={e => update({ version: e.target.value })} placeholder="1.0" />
          </Field>
          <Field label="Primary system">
            <SystemSelect label="Primary system" systems={SYSTEMS} value={state.system} onChange={(v) => update({ system: v })} />
          </Field>
          <Field label="Description" htmlFor="wf-desc" className="sm:col-span-2">
            <Textarea id="wf-desc" value={state.description} onChange={e => update({ description: e.target.value })} rows={3} placeholder="What this workflow achieves, in a sentence or two" />
          </Field>
        </div>
      </FormSection>

      <FormSection title="Trigger" hint="The change that starts the workflow.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Object" htmlFor="wf-trig-obj">
            <Input id="wf-trig-obj" value={state.triggerObject} onChange={e => update({ triggerObject: e.target.value })} placeholder="Account" className="font-mono" />
          </Field>
          <Field label="Field" htmlFor="wf-trig-field">
            <Input id="wf-trig-field" value={state.triggerField} onChange={e => update({ triggerField: e.target.value })} placeholder="Credit_Limit__c" className="font-mono" />
          </Field>
          <Field label="Condition" htmlFor="wf-trig-cond" className="sm:col-span-2">
            <Input id="wf-trig-cond" value={state.triggerCondition} onChange={e => update({ triggerCondition: e.target.value })} placeholder="Change exceeds the auto-approval threshold" />
          </Field>
        </div>
      </FormSection>

      <FormSection title="Steps" count={state.steps.length} hint="In the order they run. Use the arrows to reorder.">
        {state.steps.length === 0 && <NoRows>No steps yet.</NoRows>}
        <ol className="border-t border-border">
          {state.steps.map((step, i) => (
            <li key={i} className="flex items-start gap-3 border-b border-border py-4">
              <div className="flex shrink-0 flex-col items-center gap-0.5">
                <span className="num flex h-7 w-7 items-center justify-center rounded-full border border-border-strong bg-card text-xs font-medium text-muted-foreground">{i + 1}</span>
                <Button type="button" variant="ghost" size="icon-sm" className="h-6 w-7 text-subtle-foreground" onClick={() => moveStep(i, i - 1)} disabled={i === 0} aria-label={`Move step ${i + 1} up`}>
                  <Icon name="chevron-up" className="h-3.5 w-3.5" />
                </Button>
                <Button type="button" variant="ghost" size="icon-sm" className="h-6 w-7 text-subtle-foreground" onClick={() => moveStep(i, i + 1)} disabled={i === state.steps.length - 1} aria-label={`Move step ${i + 1} down`}>
                  <Icon name="chevron-down" className="h-3.5 w-3.5" />
                </Button>
              </div>
              <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2">
                <Field label="Step name" htmlFor={`wf-step-name-${i}`}>
                  <Input id={`wf-step-name-${i}`} value={step.name} onChange={e => setStep(i, { name: e.target.value })} placeholder="Validate pre-requisites" />
                </Field>
                <Field label="System">
                  <SystemSelect label={`System of step ${i + 1}`} systems={SYSTEMS} value={step.system} onChange={(v) => setStep(i, { system: v })} />
                </Field>
                <Field label="What happens" htmlFor={`wf-step-action-${i}`} className="sm:col-span-2">
                  <Input id={`wf-step-action-${i}`} value={step.action} onChange={e => setStep(i, { action: e.target.value })} placeholder="Check the risk tier and the open balance" />
                </Field>
                <Field label="Time allowed (optional)" htmlFor={`wf-step-sla-${i}`}>
                  <Input id={`wf-step-sla-${i}`} value={step.sla} onChange={e => setStep(i, { sla: e.target.value })} placeholder="48 hours" />
                </Field>
                <Field label="If it fails (optional)" htmlFor={`wf-step-fail-${i}`}>
                  <Input id={`wf-step-fail-${i}`} value={step.failureAction} onChange={e => setStep(i, { failureAction: e.target.value })} placeholder="Reject with a reason" />
                </Field>
                {isApprovalStep(step) && (
                  <div className="sm:col-span-2"><StatusPill tone="warning">Shown as an approval gate</StatusPill></div>
                )}
              </div>
              <RemoveButton label={`Remove step ${i + 1}`} onClick={() => update({ steps: state.steps.filter((_, j) => j !== i) })} />
            </li>
          ))}
        </ol>
        <div className="mt-3">
          <AddButton onClick={() => update({ steps: [...state.steps, { name: '', system: 'Salesforce', action: '', sla: '', failureAction: '' }] })}>Add step</AddButton>
        </div>
      </FormSection>

      <FormSection title="Dependencies" count={state.dependencies.length} hint="Entities this workflow reads or writes.">
        {state.dependencies.length === 0 && <NoRows>No dependencies added.</NoRows>}
        <div className="space-y-3">
          {state.dependencies.map((d, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className="grid min-w-0 flex-1 gap-2 sm:grid-cols-3">
                <Input value={d.entity} onChange={e => setDep(i, { entity: e.target.value })} placeholder="Account" aria-label={`Dependency ${i + 1}: entity`} className="font-mono" />
                <SystemSelect label={`Dependency ${i + 1}: system`} systems={SYSTEMS} emptyLabel="Any system" value={d.system} onChange={(v) => setDep(i, { system: v })} />
                <Input value={d.relationship} onChange={e => setDep(i, { relationship: e.target.value })} placeholder="Source object" aria-label={`Dependency ${i + 1}: relationship`} />
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
