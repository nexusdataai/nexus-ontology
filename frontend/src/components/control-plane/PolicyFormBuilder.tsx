import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Field, StatusPill } from '@/components/ds/kit';
import { SystemLogo } from '@/components/ds/SystemLogo';
import { AddButton, Choice, FormBody, FormSection, NoRows, RemoveButton, SystemSelect } from './formKit';
import { parsePolicyDoc } from './knowledgeParsers';

const RISK_LEVELS = ['Low', 'Medium', 'High'];
const SYSTEMS = ['Salesforce', 'Oracle ERP', 'SAP', 'Google Drive'];
const CONSTRAINT_TYPES = [
  { value: 'limit', label: 'Limit' },
  { value: 'validation', label: 'Validation' },
  { value: 'dependency', label: 'Dependency' },
];
const NO_TYPE = '__none__';

interface Constraint { text: string; type: string }
interface ApprovalRow { magnitude: string; approval: string; role: string; sla: string }
interface Restriction { text: string; system: string; condition: string }

interface PolicyFormState {
  policyId: string;
  title: string;
  version: string;
  owner: string;
  riskLevel: string;
  systems: string[];
  sourceOfTruth: { system: string; field: string; description: string };
  constraints: Constraint[];
  approvalMatrix: ApprovalRow[];
  restrictions: Restriction[];
  auditLogChanges: boolean;
  auditJustification: boolean;
  auditNotifyTargets: string;
  additionalSections: { title: string; content: string }[];
}

const AUDIT_LOG = 'All changes must be logged with previous/new values';
const AUDIT_JUSTIFY = 'Written justification required for significant changes';
const AUDIT_NOTIFY = 'Notifications sent to: ';

function parsePolicy(content: string): PolicyFormState {
  const state: PolicyFormState = {
    policyId: '', title: '', version: '1.0', owner: '', riskLevel: 'Medium',
    systems: [], sourceOfTruth: { system: '', field: '', description: '' },
    constraints: [], approvalMatrix: [], restrictions: [],
    auditLogChanges: true, auditJustification: false, auditNotifyTargets: '',
    additionalSections: [],
  };
  const lines = content.split('\n');
  for (const line of lines) {
    if (line.startsWith('# ')) state.title = line.replace('# ', '').trim();
    const m = line.match(/^\*\*(.+?):\*\*\s*(.+)/);
    if (m) {
      const [, key, val] = m;
      if (key === 'Policy ID') state.policyId = val;
      if (key === 'Version') state.version = val;
      if (key === 'Owner') state.owner = val;
      if (key === 'Risk Level') state.riskLevel = val;
      if (key === 'Systems Affected') state.systems = val.split(',').map(s => s.trim());
    }
  }

  // Keep what is already written: every section of the file opens as an
  // editable section, so saving from the form does not drop it.
  const doc = parsePolicyDoc(content);
  if (doc.sections.length > 0) {
    state.auditLogChanges = false;
    for (const s of doc.sections) {
      const isOwnAudit = /audit requirements/i.test(s.title) && !s.table && s.paragraphs.length === 0
        && s.bullets.length > 0 && s.bullets.every(b => b === AUDIT_LOG || b === AUDIT_JUSTIFY || b.startsWith(AUDIT_NOTIFY));
      if (isOwnAudit) {
        state.auditLogChanges = s.bullets.includes(AUDIT_LOG);
        state.auditJustification = s.bullets.includes(AUDIT_JUSTIFY);
        state.auditNotifyTargets = (s.bullets.find(b => b.startsWith(AUDIT_NOTIFY)) || '').slice(AUDIT_NOTIFY.length);
      } else {
        state.additionalSections.push({ title: s.heading, content: s.raw });
      }
    }
  }
  return state;
}

function generateMarkdown(s: PolicyFormState): string {
  let md = `# ${s.title || 'Untitled Policy'}\n\n`;
  md += `**Policy ID:** ${s.policyId}\n`;
  md += `**Version:** ${s.version}\n`;
  md += `**Owner:** ${s.owner}\n`;
  md += `**Risk Level:** ${s.riskLevel}\n`;
  md += `**Systems Affected:** ${s.systems.join(', ')}\n\n`;

  if (s.sourceOfTruth.system || s.sourceOfTruth.field) {
    md += `## 1. Source of Truth\n\n`;
    md += `${s.sourceOfTruth.system} \`${s.sourceOfTruth.field}\` is the authoritative source.\n`;
    if (s.sourceOfTruth.description) md += `${s.sourceOfTruth.description}\n`;
    md += '\n';
  }

  if (s.constraints.length > 0) {
    md += `## 2. Constraints\n\n`;
    for (const c of s.constraints) md += `- ${c.text}${c.type ? ` (${c.type})` : ''}\n`;
    md += '\n';
  }

  if (s.approvalMatrix.length > 0) {
    md += `## 3. Approval Thresholds\n\n`;
    md += `| Change Magnitude | Approval Required | Approver Role | SLA |\n`;
    md += `|---|---|---|---|\n`;
    for (const r of s.approvalMatrix) md += `| ${r.magnitude} | ${r.approval} | ${r.role} | ${r.sla} |\n`;
    md += '\n';
  }

  if (s.restrictions.length > 0) {
    md += `## 4. Restrictions\n\n`;
    for (const r of s.restrictions) md += `- ${r.text}${r.system ? ` (${r.system})` : ''}${r.condition ? ` — ${r.condition}` : ''}\n`;
    md += '\n';
  }

  if (s.auditLogChanges || s.auditJustification) {
    md += `## 5. Audit Requirements\n\n`;
    if (s.auditLogChanges) md += `- All changes must be logged with previous/new values\n`;
    if (s.auditJustification) md += `- Written justification required for significant changes\n`;
    if (s.auditNotifyTargets) md += `- Notifications sent to: ${s.auditNotifyTargets}\n`;
    md += '\n';
  }

  for (const sec of s.additionalSections) {
    md += `## ${sec.title}\n\n${sec.content}\n\n`;
  }

  return md;
}

export default function PolicyFormBuilder({ content, onChange }: { content: string; onChange: (c: string) => void }) {
  const [state, setState] = useState<PolicyFormState>(() => parsePolicy(content));

  useEffect(() => { onChange(generateMarkdown(state)); }, [state]);

  const update = (patch: Partial<PolicyFormState>) => setState(s => ({ ...s, ...patch }));

  const setSection = (i: number, patch: Partial<{ title: string; content: string }>) =>
    update({ additionalSections: state.additionalSections.map((s, j) => (j === i ? { ...s, ...patch } : s)) });

  return (
    <FormBody>
      <FormSection title="Policy details" hint="Who owns this policy, how risky it is and which systems it governs.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Title" htmlFor="pol-title" className="sm:col-span-2">
            <Input id="pol-title" value={state.title} onChange={e => update({ title: e.target.value })} placeholder="Credit limit policy" />
          </Field>
          <Field label="Policy ID" htmlFor="pol-id">
            <Input id="pol-id" value={state.policyId} onChange={e => update({ policyId: e.target.value })} placeholder="POL-CREDIT-001" className="font-mono" />
          </Field>
          <Field label="Version" htmlFor="pol-version">
            <Input id="pol-version" value={state.version} onChange={e => update({ version: e.target.value })} placeholder="1.0" />
          </Field>
          <Field label="Owner" htmlFor="pol-owner" className="sm:col-span-2">
            <Input id="pol-owner" value={state.owner} onChange={e => update({ owner: e.target.value })} placeholder="Finance Department" />
          </Field>
          <Field label="Risk level">
            <Choice
              label="Risk level"
              value={state.riskLevel}
              onChange={(r) => update({ riskLevel: r })}
              options={RISK_LEVELS.map(r => ({ value: r, label: <StatusPill status={r} className="font-normal">{r}</StatusPill> }))}
            />
          </Field>
          <Field label="Systems affected" className="sm:col-span-2">
            <Choice
              multiple
              label="Systems affected"
              value={state.systems}
              onChange={(s) => update({ systems: state.systems.includes(s) ? state.systems.filter(x => x !== s) : [...state.systems, s] })}
              options={[...SYSTEMS, ...state.systems.filter(s => s && !SYSTEMS.includes(s))].map(s => ({
                value: s,
                label: <span className="inline-flex items-center gap-1.5"><SystemLogo system={s} size="xs" /> {s}</span>,
              }))}
            />
          </Field>
        </div>
      </FormSection>

      <FormSection title="Written sections" count={state.additionalSections.length} hint="The body of the policy as it is stored. Bullets, tables and plain text are kept as written.">
        {state.additionalSections.length === 0 && <NoRows>No written sections yet.</NoRows>}
        <div className="space-y-5">
          {state.additionalSections.map((sec, i) => (
            <div key={i} className="space-y-2">
              <div className="flex items-center gap-2">
                <Input value={sec.title} onChange={e => setSection(i, { title: e.target.value })} placeholder="Section heading" aria-label={`Heading of section ${i + 1}`} className="font-medium" />
                <RemoveButton label={`Remove section ${sec.title || i + 1}`} onClick={() => update({ additionalSections: state.additionalSections.filter((_, j) => j !== i) })} />
              </div>
              <Textarea
                value={sec.content}
                onChange={e => setSection(i, { content: e.target.value })}
                aria-label={`Text of section ${sec.title || i + 1}`}
                placeholder={'- One rule per line\n- Use a table for thresholds'}
                rows={Math.min(12, Math.max(3, sec.content.split('\n').length + 1))}
                className="scroll-thin font-mono text-xs leading-5"
                spellCheck={false}
              />
            </div>
          ))}
        </div>
        <div className="mt-3"><AddButton onClick={() => update({ additionalSections: [...state.additionalSections, { title: '', content: '' }] })}>Add section</AddButton></div>
      </FormSection>

      <FormSection title="Source of truth" hint="The system and field that hold the authoritative value.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="System">
            <SystemSelect label="Source of truth system" systems={SYSTEMS} emptyLabel="No system" value={state.sourceOfTruth.system} onChange={(v) => update({ sourceOfTruth: { ...state.sourceOfTruth, system: v } })} />
          </Field>
          <Field label="Object and field" htmlFor="pol-sot-field">
            <Input id="pol-sot-field" value={state.sourceOfTruth.field} onChange={e => update({ sourceOfTruth: { ...state.sourceOfTruth, field: e.target.value } })} placeholder="Account.Credit_Limit__c" className="font-mono" />
          </Field>
          <Field label="Note" htmlFor="pol-sot-note" className="sm:col-span-2">
            <Input id="pol-sot-note" value={state.sourceOfTruth.description} onChange={e => update({ sourceOfTruth: { ...state.sourceOfTruth, description: e.target.value } })} placeholder="Other systems receive the value by sync and cannot override it" />
          </Field>
        </div>
      </FormSection>

      <FormSection title="Constraints" count={state.constraints.length} hint="Limits and checks the agent must respect.">
        {state.constraints.length === 0 && <NoRows>No constraints added.</NoRows>}
        <div className="space-y-2">
          {state.constraints.map((c, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
              <Input value={c.text} onChange={e => { const cs = [...state.constraints]; cs[i] = { ...c, text: e.target.value }; update({ constraints: cs }); }} placeholder="Maximum credit limit is 5,000,000 USD" aria-label={`Constraint ${i + 1}`} className="min-w-0 flex-1 basis-full sm:basis-auto" />
              <Select value={c.type || NO_TYPE} onValueChange={(v) => { const cs = [...state.constraints]; cs[i] = { ...c, type: v === NO_TYPE ? '' : v }; update({ constraints: cs }); }}>
                <SelectTrigger className="h-9 w-36" aria-label={`Type of constraint ${i + 1}`}><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_TYPE}>No type</SelectItem>
                  {CONSTRAINT_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                </SelectContent>
              </Select>
              <RemoveButton label={`Remove constraint ${i + 1}`} onClick={() => update({ constraints: state.constraints.filter((_, j) => j !== i) })} />
            </div>
          ))}
        </div>
        <div className="mt-3"><AddButton onClick={() => update({ constraints: [...state.constraints, { text: '', type: '' }] })}>Add constraint</AddButton></div>
      </FormSection>

      <FormSection title="Approval thresholds" count={state.approvalMatrix.length} hint="When a change needs approval, who approves it and how fast.">
        {state.approvalMatrix.length === 0 && <NoRows>No thresholds added.</NoRows>}
        <div className="space-y-3">
          {state.approvalMatrix.map((r, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className="grid min-w-0 flex-1 grid-cols-2 gap-2 lg:grid-cols-4">
                <Input value={r.magnitude} onChange={e => { const m = [...state.approvalMatrix]; m[i] = { ...r, magnitude: e.target.value }; update({ approvalMatrix: m }); }} placeholder="Over 10% increase" aria-label={`Threshold ${i + 1}: size of change`} />
                <Input value={r.approval} onChange={e => { const m = [...state.approvalMatrix]; m[i] = { ...r, approval: e.target.value }; update({ approvalMatrix: m }); }} placeholder="Approval needed" aria-label={`Threshold ${i + 1}: approval needed`} />
                <Input value={r.role} onChange={e => { const m = [...state.approvalMatrix]; m[i] = { ...r, role: e.target.value }; update({ approvalMatrix: m }); }} placeholder="Approver role" aria-label={`Threshold ${i + 1}: approver role`} />
                <Input value={r.sla} onChange={e => { const m = [...state.approvalMatrix]; m[i] = { ...r, sla: e.target.value }; update({ approvalMatrix: m }); }} placeholder="Within 48 hours" aria-label={`Threshold ${i + 1}: time allowed`} />
              </div>
              <RemoveButton label={`Remove threshold ${i + 1}`} onClick={() => update({ approvalMatrix: state.approvalMatrix.filter((_, j) => j !== i) })} />
            </div>
          ))}
        </div>
        <div className="mt-3"><AddButton onClick={() => update({ approvalMatrix: [...state.approvalMatrix, { magnitude: '', approval: '', role: '', sla: '' }] })}>Add threshold</AddButton></div>
      </FormSection>

      <FormSection title="Restrictions" count={state.restrictions.length} hint="Things that are not allowed, where and under which condition.">
        {state.restrictions.length === 0 && <NoRows>No restrictions added.</NoRows>}
        <div className="space-y-3">
          {state.restrictions.map((r, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className="grid min-w-0 flex-1 grid-cols-2 gap-2 lg:grid-cols-4">
                <Input value={r.text} onChange={e => { const rs = [...state.restrictions]; rs[i] = { ...r, text: e.target.value }; update({ restrictions: rs }); }} placeholder="No limit changes during close" aria-label={`Restriction ${i + 1}`} className="col-span-2" />
                <Input value={r.system} onChange={e => { const rs = [...state.restrictions]; rs[i] = { ...r, system: e.target.value }; update({ restrictions: rs }); }} placeholder="System" aria-label={`Restriction ${i + 1}: system`} />
                <Input value={r.condition} onChange={e => { const rs = [...state.restrictions]; rs[i] = { ...r, condition: e.target.value }; update({ restrictions: rs }); }} placeholder="Condition" aria-label={`Restriction ${i + 1}: condition`} />
              </div>
              <RemoveButton label={`Remove restriction ${i + 1}`} onClick={() => update({ restrictions: state.restrictions.filter((_, j) => j !== i) })} />
            </div>
          ))}
        </div>
        <div className="mt-3"><AddButton onClick={() => update({ restrictions: [...state.restrictions, { text: '', system: '', condition: '' }] })}>Add restriction</AddButton></div>
      </FormSection>

      <FormSection title="Audit" hint="What is recorded when this policy is applied.">
        <div className="space-y-3">
          <label className="flex items-center gap-2.5 text-sm text-foreground">
            <Checkbox checked={state.auditLogChanges} onCheckedChange={(v) => update({ auditLogChanges: v === true })} />
            Log every change with the previous and new value
          </label>
          <label className="flex items-center gap-2.5 text-sm text-foreground">
            <Checkbox checked={state.auditJustification} onCheckedChange={(v) => update({ auditJustification: v === true })} />
            Require a written justification
          </label>
          <Field label="Send notifications to" htmlFor="pol-notify" hint="Written into the policy only when one of the options above is on." className="max-w-md pt-1">
            <Input id="pol-notify" value={state.auditNotifyTargets} onChange={e => update({ auditNotifyTargets: e.target.value })} placeholder="finance-ops@company.com" />
          </Field>
        </div>
      </FormSection>
    </FormBody>
  );
}
