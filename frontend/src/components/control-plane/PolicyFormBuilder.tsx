import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react';

const RISK_LEVELS = ['Low', 'Medium', 'High'];
const SYSTEMS = ['Salesforce', 'Oracle ERP', 'SAP', 'Google Drive'];

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

function Section({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card className="mb-3">
      <CardHeader className="pb-2 cursor-pointer" onClick={() => setOpen(!open)}>
        <CardTitle className="text-sm flex items-center gap-1.5">
          {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          {title}
        </CardTitle>
      </CardHeader>
      {open && <CardContent className="pt-0">{children}</CardContent>}
    </Card>
  );
}

export default function PolicyFormBuilder({ content, onChange }: { content: string; onChange: (c: string) => void }) {
  const [state, setState] = useState<PolicyFormState>(() => parsePolicy(content));

  useEffect(() => { onChange(generateMarkdown(state)); }, [state]);

  const update = (patch: Partial<PolicyFormState>) => setState(s => ({ ...s, ...patch }));

  return (
    <div className="p-4 space-y-0">
      <Section title="Policy Header">
        <div className="grid grid-cols-2 gap-3">
          <div><label className="text-[10px] text-muted-foreground">Title</label>
            <Input value={state.title} onChange={e => update({ title: e.target.value })} placeholder="Credit Limit Policy" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Policy ID</label>
            <Input value={state.policyId} onChange={e => update({ policyId: e.target.value })} placeholder="POL-CREDIT-001" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Version</label>
            <Input value={state.version} onChange={e => update({ version: e.target.value })} placeholder="1.0" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Owner</label>
            <Input value={state.owner} onChange={e => update({ owner: e.target.value })} placeholder="Finance Department" className="text-xs" /></div>
        </div>
        <div className="mt-3">
          <label className="text-[10px] text-muted-foreground">Risk Level</label>
          <div className="flex gap-2 mt-1">
            {RISK_LEVELS.map(r => (
              <button key={r} onClick={() => update({ riskLevel: r })}
                className={`px-3 py-1 rounded text-xs ${state.riskLevel === r ? 'bg-blue-600/20 text-blue-300 border border-blue-500' : 'border text-muted-foreground'}`}>
                {r}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-3">
          <label className="text-[10px] text-muted-foreground">Systems Affected</label>
          <div className="flex flex-wrap gap-2 mt-1">
            {SYSTEMS.map(s => (
              <button key={s} onClick={() => update({ systems: state.systems.includes(s) ? state.systems.filter(x => x !== s) : [...state.systems, s] })}
                className={`px-2.5 py-1 rounded text-xs ${state.systems.includes(s) ? 'bg-blue-600/20 text-blue-300 border border-blue-500' : 'border text-muted-foreground'}`}>
                {s}
              </button>
            ))}
          </div>
        </div>
      </Section>

      <Section title="Source of Truth">
        <div className="grid grid-cols-3 gap-3">
          <div><label className="text-[10px] text-muted-foreground">System</label>
            <select value={state.sourceOfTruth.system} onChange={e => update({ sourceOfTruth: { ...state.sourceOfTruth, system: e.target.value } })}
              className="w-full rounded border bg-card px-2 py-1.5 text-xs">
              <option value="">Select...</option>{SYSTEMS.map(s => <option key={s} value={s}>{s}</option>)}
            </select></div>
          <div><label className="text-[10px] text-muted-foreground">Object.Field</label>
            <Input value={state.sourceOfTruth.field} onChange={e => update({ sourceOfTruth: { ...state.sourceOfTruth, field: e.target.value } })} placeholder="Account.Credit_Limit__c" className="text-xs" /></div>
          <div><label className="text-[10px] text-muted-foreground">Description</label>
            <Input value={state.sourceOfTruth.description} onChange={e => update({ sourceOfTruth: { ...state.sourceOfTruth, description: e.target.value } })} className="text-xs" /></div>
        </div>
      </Section>

      <Section title="Constraints">
        {state.constraints.map((c, i) => (
          <div key={i} className="flex gap-2 mb-2">
            <Input value={c.text} onChange={e => { const cs = [...state.constraints]; cs[i] = { ...c, text: e.target.value }; update({ constraints: cs }); }} placeholder="Constraint description" className="flex-1 text-xs" />
            <select value={c.type} onChange={e => { const cs = [...state.constraints]; cs[i] = { ...c, type: e.target.value }; update({ constraints: cs }); }}
              className="w-32 rounded border bg-card px-2 py-1.5 text-xs">
              <option value="">Type...</option><option value="limit">Limit</option><option value="validation">Validation</option><option value="dependency">Dependency</option>
            </select>
            <Button variant="ghost" size="sm" onClick={() => update({ constraints: state.constraints.filter((_, j) => j !== i) })}><Trash2 className="h-3.5 w-3.5" /></Button>
          </div>
        ))}
        <Button variant="outline" size="sm" onClick={() => update({ constraints: [...state.constraints, { text: '', type: '' }] })}><Plus className="h-3.5 w-3.5 mr-1" />Add Constraint</Button>
      </Section>

      <Section title="Approval Matrix">
        {state.approvalMatrix.map((r, i) => (
          <div key={i} className="grid grid-cols-5 gap-2 mb-2">
            <Input value={r.magnitude} onChange={e => { const m = [...state.approvalMatrix]; m[i] = { ...r, magnitude: e.target.value }; update({ approvalMatrix: m }); }} placeholder="e.g. > 10%" className="text-xs" />
            <Input value={r.approval} onChange={e => { const m = [...state.approvalMatrix]; m[i] = { ...r, approval: e.target.value }; update({ approvalMatrix: m }); }} placeholder="Required?" className="text-xs" />
            <Input value={r.role} onChange={e => { const m = [...state.approvalMatrix]; m[i] = { ...r, role: e.target.value }; update({ approvalMatrix: m }); }} placeholder="Approver role" className="text-xs" />
            <Input value={r.sla} onChange={e => { const m = [...state.approvalMatrix]; m[i] = { ...r, sla: e.target.value }; update({ approvalMatrix: m }); }} placeholder="SLA" className="text-xs" />
            <Button variant="ghost" size="sm" onClick={() => update({ approvalMatrix: state.approvalMatrix.filter((_, j) => j !== i) })}><Trash2 className="h-3.5 w-3.5" /></Button>
          </div>
        ))}
        <Button variant="outline" size="sm" onClick={() => update({ approvalMatrix: [...state.approvalMatrix, { magnitude: '', approval: '', role: '', sla: '' }] })}><Plus className="h-3.5 w-3.5 mr-1" />Add Row</Button>
      </Section>

      <Section title="Restrictions">
        {state.restrictions.map((r, i) => (
          <div key={i} className="grid grid-cols-4 gap-2 mb-2">
            <Input value={r.text} onChange={e => { const rs = [...state.restrictions]; rs[i] = { ...r, text: e.target.value }; update({ restrictions: rs }); }} placeholder="Restriction" className="col-span-2 text-xs" />
            <Input value={r.system} onChange={e => { const rs = [...state.restrictions]; rs[i] = { ...r, system: e.target.value }; update({ restrictions: rs }); }} placeholder="System" className="text-xs" />
            <div className="flex gap-1">
              <Input value={r.condition} onChange={e => { const rs = [...state.restrictions]; rs[i] = { ...r, condition: e.target.value }; update({ restrictions: rs }); }} placeholder="Condition" className="text-xs" />
              <Button variant="ghost" size="sm" onClick={() => update({ restrictions: state.restrictions.filter((_, j) => j !== i) })}><Trash2 className="h-3.5 w-3.5" /></Button>
            </div>
          </div>
        ))}
        <Button variant="outline" size="sm" onClick={() => update({ restrictions: [...state.restrictions, { text: '', system: '', condition: '' }] })}><Plus className="h-3.5 w-3.5 mr-1" />Add Restriction</Button>
      </Section>

      <Section title="Audit Requirements" defaultOpen={false}>
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs">
            <input type="checkbox" checked={state.auditLogChanges} onChange={e => update({ auditLogChanges: e.target.checked })} />Log all changes with previous/new values
          </label>
          <label className="flex items-center gap-2 text-xs">
            <input type="checkbox" checked={state.auditJustification} onChange={e => update({ auditJustification: e.target.checked })} />Require written justification
          </label>
          <div><label className="text-[10px] text-muted-foreground">Notification targets</label>
            <Input value={state.auditNotifyTargets} onChange={e => update({ auditNotifyTargets: e.target.value })} placeholder="email@company.com" className="text-xs" /></div>
        </div>
      </Section>
    </div>
  );
}
