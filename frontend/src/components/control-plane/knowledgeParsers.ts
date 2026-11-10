/**
 * Read-only parsers for knowledge files (policy markdown, workflow and
 * integration YAML). They turn the stored text into plain objects so the
 * screens can show a policy as rules, a workflow as steps and an integration
 * as source to target, and so the form builders open with the file's values.
 *
 * Tolerant by design: anything that cannot be read is left empty. They never
 * write and never call the API.
 */

/* ------------------------------------------------------------------ policy */

export interface PolicySection {
  /** Heading without its leading number ("3. Approval thresholds"). */
  title: string;
  /** Heading exactly as written, number included. */
  heading: string;
  paragraphs: string[];
  bullets: string[];
  /** First row is the header. */
  table: string[][] | null;
  /** The section body exactly as written. */
  raw: string;
}

export interface PolicyDoc {
  title: string;
  policyId: string;
  version: string;
  owner: string;
  riskLevel: string;
  systems: string[];
  /** Any other `**Key:** value` line. */
  extra: { label: string; value: string }[];
  sections: PolicySection[];
}

const KNOWN_META = ['Policy ID', 'Version', 'Owner', 'Risk Level', 'Systems Affected'];

function buildSection(title: string, body: string[]): PolicySection {
  const paragraphs: string[] = [];
  const bullets: string[] = [];
  const rows: string[][] = [];
  let para: string[] = [];
  const flush = () => { if (para.length) { paragraphs.push(para.join(' ')); para = []; } };
  for (const line of body) {
    const t = line.trim();
    if (!t) { flush(); continue; }
    if (/^[-*]\s+/.test(t)) { flush(); bullets.push(t.replace(/^[-*]\s+/, '')); continue; }
    if (t.startsWith('|')) {
      flush();
      const cells = t.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
      if (!cells.every(c => /^:?-{2,}:?$/.test(c) || c === '')) rows.push(cells);
      continue;
    }
    para.push(t.replace(/^#{3,}\s+/, ''));
  }
  flush();
  return {
    heading: title,
    title: title.replace(/^\d+[.)]\s*/, ''),
    paragraphs,
    bullets,
    table: rows.length > 1 ? rows : null,
    raw: body.join('\n').trim(),
  };
}

export function parsePolicyDoc(content: string): PolicyDoc {
  const doc: PolicyDoc = { title: '', policyId: '', version: '', owner: '', riskLevel: '', systems: [], extra: [], sections: [] };
  let current: string | null = null;
  let body: string[] = [];
  for (const line of String(content || '').split('\n')) {
    if (line.startsWith('## ')) {
      if (current !== null) doc.sections.push(buildSection(current, body));
      current = line.slice(3).trim();
      body = [];
      continue;
    }
    if (current === null) {
      if (line.startsWith('# ')) { doc.title = line.slice(2).trim(); continue; }
      const m = line.match(/^\*\*(.+?):\*\*\s*(.+)/);
      if (m) {
        const key = m[1].trim();
        const val = m[2].trim();
        if (key === 'Policy ID') doc.policyId = val;
        else if (key === 'Version') doc.version = val;
        else if (key === 'Owner') doc.owner = val;
        else if (key === 'Risk Level') doc.riskLevel = val;
        else if (key === 'Systems Affected') doc.systems = val.split(',').map(s => s.trim()).filter(Boolean);
        if (!KNOWN_META.includes(key)) doc.extra.push({ label: key, value: val });
      }
      continue;
    }
    body.push(line);
  }
  if (current !== null) doc.sections.push(buildSection(current, body));
  return doc;
}

/* -------------------------------------------------------------- yaml lines */

interface YamlLine { indent: number; dash: boolean; key: string; value: string; text: string }

const unquote = (v: string): string => {
  const t = v.trim();
  if (t.length >= 2 && ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'")))) return t.slice(1, -1);
  return t;
};

function yamlLines(content: string): YamlLine[] {
  return String(content || '').split('\n').map((raw) => {
    const m = raw.match(/^(\s*)(-\s+)?([A-Za-z_][\w-]*):(?:\s+(.*))?\s*$/);
    if (m) return { indent: m[1].length, dash: !!m[2], key: m[3], value: unquote(m[4] || ''), text: raw.trim() };
    return { indent: raw.length - raw.trimStart().length, dash: false, key: '', value: '', text: raw.trim() };
  });
}

/** Reads `description: >` style folded text starting at line `i`. */
function foldedText(lines: YamlLine[], i: number): string {
  const first = lines[i].value;
  if (first && first !== '>' && first !== '|' && first !== '>-' && first !== '|-') return first;
  const parts: string[] = [];
  for (let j = i + 1; j < lines.length; j++) {
    const l = lines[j];
    if (!l.text) { if (parts.length) break; continue; }
    if (l.indent === 0) break;
    parts.push(l.text);
  }
  return parts.join(' ');
}

export interface DependencyDoc { entity: string; system: string; relationship: string }

/* ---------------------------------------------------------------- workflow */

export interface WorkflowStepDoc { order: number; name: string; system: string; action: string; sla: string; failureAction: string }

export interface WorkflowDoc {
  id: string;
  name: string;
  version: string;
  system: string;
  trigger: { object: string; field: string; condition: string };
  description: string;
  steps: WorkflowStepDoc[];
  dependencies: DependencyDoc[];
}

const emptyWorkflow = (): WorkflowDoc => ({
  id: '', name: '', version: '', system: '', trigger: { object: '', field: '', condition: '' }, description: '', steps: [], dependencies: [],
});

const str = (v: unknown): string => (v == null ? '' : String(v));

export function parseWorkflowDoc(content: string): WorkflowDoc {
  const doc = emptyWorkflow();
  const text = String(content || '').trim();
  if (text.startsWith('{')) {
    try {
      const j = JSON.parse(text);
      doc.id = str(j.id); doc.name = str(j.name); doc.version = str(j.version); doc.system = str(j.system); doc.description = str(j.description);
      doc.trigger = { object: str(j.trigger?.object), field: str(j.trigger?.field), condition: str(j.trigger?.condition) };
      doc.steps = (Array.isArray(j.steps) ? j.steps : []).map((s: any, i: number) => ({
        order: Number(s.order) || i + 1, name: str(s.name), system: str(s.system), action: str(s.action), sla: str(s.sla), failureAction: str(s.failure_action ?? s.failureAction),
      }));
      doc.dependencies = (Array.isArray(j.dependencies) ? j.dependencies : []).map((d: any) => ({ entity: str(d.entity), system: str(d.system), relationship: str(d.relationship) }));
    } catch { /* leave empty */ }
    return doc;
  }

  const lines = yamlLines(content);
  let section = '';
  let step: WorkflowStepDoc | null = null;
  let dep: DependencyDoc | null = null;
  const closeStep = () => { if (step) { doc.steps.push(step); step = null; } };
  const closeDep = () => { if (dep) { doc.dependencies.push(dep); dep = null; } };

  lines.forEach((l, i) => {
    if (!l.key) return;
    if (l.indent === 0 && !l.dash) {
      closeStep(); closeDep();
      section = l.key;
      if (l.key === 'id') doc.id = l.value;
      else if (l.key === 'name') doc.name = l.value;
      else if (l.key === 'version') doc.version = l.value;
      else if (l.key === 'system') doc.system = l.value;
      else if (l.key === 'description') doc.description = foldedText(lines, i);
      return;
    }
    if (section === 'trigger') {
      if (l.key === 'object') doc.trigger.object = l.value;
      else if (l.key === 'field') doc.trigger.field = l.value;
      else if (l.key === 'condition') doc.trigger.condition = l.value;
    } else if (section === 'steps') {
      if (l.dash) { closeStep(); step = { order: doc.steps.length + 1, name: '', system: '', action: '', sla: '', failureAction: '' }; }
      if (!step) return;
      if (l.key === 'order') step.order = parseInt(l.value, 10) || step.order;
      else if (l.key === 'name') step.name = l.value;
      else if (l.key === 'system') step.system = l.value;
      else if (l.key === 'action') step.action = l.value;
      else if (l.key === 'sla') step.sla = l.value;
      else if (l.key === 'failure_action') step.failureAction = l.value;
    } else if (section === 'dependencies') {
      if (l.dash) { closeDep(); dep = { entity: '', system: '', relationship: '' }; }
      if (!dep) return;
      if (l.key === 'entity') dep.entity = l.value;
      else if (l.key === 'system') dep.system = l.value;
      else if (l.key === 'relationship') dep.relationship = l.value;
    }
  });
  closeStep(); closeDep();
  return doc;
}

/* ------------------------------------------------------------- integration */

export interface IntegrationFieldDoc { source: string; target: string; direction: string; transform: string; constraint: string }
export interface IntegrationMappingDoc { name: string; sourceObject: string; targetObject: string; direction: string; fields: IntegrationFieldDoc[] }

export interface IntegrationDoc {
  id: string;
  name: string;
  version: string;
  sourceSystem: string;
  targetSystem: string;
  syncType: string;
  frequency: string;
  description: string;
  mappings: IntegrationMappingDoc[];
  retryCount: number | null;
  retryInterval: string;
  alertEmail: string;
  fallback: string;
  dependencies: DependencyDoc[];
}

export function parseIntegrationDoc(content: string): IntegrationDoc {
  const doc: IntegrationDoc = {
    id: '', name: '', version: '', sourceSystem: '', targetSystem: '', syncType: '', frequency: '', description: '',
    mappings: [], retryCount: null, retryInterval: '', alertEmail: '', fallback: '', dependencies: [],
  };
  const lines = yamlLines(content);
  let section = '';
  let mapping: IntegrationMappingDoc | null = null;
  let field: IntegrationFieldDoc | null = null;
  let inFields = false;
  let dep: DependencyDoc | null = null;
  const closeField = () => { if (field && mapping) mapping.fields.push(field); field = null; };
  const closeMapping = () => { closeField(); if (mapping) doc.mappings.push(mapping); mapping = null; inFields = false; };
  const closeDep = () => { if (dep) { doc.dependencies.push(dep); dep = null; } };

  lines.forEach((l, i) => {
    if (!l.key) return;
    if (l.indent === 0 && !l.dash) {
      closeMapping(); closeDep();
      section = l.key;
      if (l.key === 'id') doc.id = l.value;
      else if (l.key === 'name') doc.name = l.value;
      else if (l.key === 'version') doc.version = l.value;
      else if (l.key === 'source_system') doc.sourceSystem = l.value;
      else if (l.key === 'target_system') doc.targetSystem = l.value;
      else if (l.key === 'sync_type') doc.syncType = l.value;
      else if (l.key === 'frequency') doc.frequency = l.value;
      else if (l.key === 'description') doc.description = foldedText(lines, i);
      return;
    }
    if (section === 'mappings') {
      if (l.dash && l.key === 'name') { closeMapping(); mapping = { name: l.value, sourceObject: '', targetObject: '', direction: '', fields: [] }; return; }
      if (!mapping) return;
      if (l.key === 'fields') { inFields = true; return; }
      if (inFields) {
        if (l.dash) { closeField(); field = { source: '', target: '', direction: 'source_to_target', transform: '', constraint: '' }; }
        if (!field) return;
        if (l.key === 'source') field.source = l.value;
        else if (l.key === 'target') field.target = l.value;
        else if (l.key === 'direction') field.direction = l.value;
        else if (l.key === 'transformation' || l.key === 'transform') field.transform = l.value;
        else if (l.key === 'constraint') field.constraint = l.value;
        return;
      }
      if (l.key === 'source_object') mapping.sourceObject = l.value;
      else if (l.key === 'target_object') mapping.targetObject = l.value;
      else if (l.key === 'direction') mapping.direction = l.value;
    } else if (section === 'failure_handling') {
      if (l.key === 'retry_count') { const n = parseInt(l.value, 10); doc.retryCount = Number.isNaN(n) ? null : n; }
      else if (l.key === 'retry_interval') doc.retryInterval = l.value;
      else if (l.key === 'alert_on_failure') doc.alertEmail = l.value;
      else if (l.key === 'fallback') doc.fallback = l.value;
    } else if (section === 'dependencies') {
      if (l.dash) { closeDep(); dep = { entity: '', system: '', relationship: '' }; }
      if (!dep) return;
      if (l.key === 'entity') dep.entity = l.value;
      else if (l.key === 'system') dep.system = l.value;
      else if (l.key === 'relationship') dep.relationship = l.value;
    }
  });
  closeMapping(); closeDep();
  return doc;
}

/* ----------------------------------------------------------------- helpers */

/** "credit-approval.yaml" becomes "Credit approval". */
export function prettyFileName(filename: string): string {
  const ACRONYM: Record<string, string> = { sf: 'Salesforce', sap: 'SAP', rbac: 'RBAC', po: 'PO', rfx: 'RFx', esg: 'ESG', ap: 'AP', ar: 'AR', gdrive: 'Google Drive', sla: 'SLA', cpq: 'CPQ', o2c: 'O2C', kpi: 'KPI', gl: 'GL', erp: 'ERP', crm: 'CRM', tpm: 'TPM', ai: 'AI', api: 'API', sku: 'SKU', dso: 'DSO' };
  const base = String(filename || '').replace(/\.[^.]+$/, '');
  const words = base.split(/[-_\s]+/).filter(Boolean).map(w => ACRONYM[w.toLowerCase()] || w.toLowerCase());
  const out = words.join(' ');
  return out ? out.charAt(0).toUpperCase() + out.slice(1) : filename;
}

/** True when a step reads as an approval gate. */
export const isApprovalStep = (s: { name: string; action: string }): boolean => /approv|sign[s]? off|sign-off/i.test(`${s.name} ${s.action}`);
