/** Display helpers shared by the retrieval views (bundle, graph, score). */
import type { SearchResult } from '@/services/ontoApi';

const TYPE_LABEL: Record<string, string> = {
  onto_schema: 'Schema', schema: 'Schema', fdw_table: 'Table',
  onto_policy: 'Policy', policy: 'Policy',
  onto_workflow: 'Workflow', workflow: 'Workflow',
  onto_integration: 'Integration', integration: 'Integration',
};

export const sentence = (s: string) => {
  const t = String(s || '').replace(/^onto_/, '').replace(/[_-]+/g, ' ').trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : '';
};

export const typeLabel = (contentType?: string) => TYPE_LABEL[String(contentType || '')] || sentence(String(contentType || 'Document'));

export const docTitle = (r: SearchResult) =>
  String(r.metadata?.object_name || r.metadata?.title || r.metadata?.name || '') || sentence(r.source_id.replace(/_V\d+_\d+$/i, '').toLowerCase());

export const docSystem = (r: SearchResult): string | null =>
  r.metadata?.source_system || r.metadata?.system || null;

export const pct = (similarity: number) => Math.round((similarity || 0) * 100);

/** Real labels for the metadata keys the index returns. */
const META_LABEL: Record<string, string> = {
  source_system: 'Source system', target_system: 'Target system', domain: 'Domain', scor_process: 'SCOR process',
  risk_level: 'Risk', fdw_mapping_status: 'Mapping', field_count: 'Fields', policy_id: 'Policy ID', workflow_id: 'Workflow ID',
  integration_id: 'Integration ID', owner: 'Owner', systems: 'Systems', step_count: 'Steps', sync_type: 'Sync type',
  frequency: 'Frequency', file: 'File', version: 'Version', category: 'Category', system: 'System',
};

export const metaLabel = (key: string) => META_LABEL[key] || sentence(key);

export function metaValue(value: unknown): string {
  if (value == null || value === '') return '';
  if (Array.isArray(value)) return value.map(v => (typeof v === 'object' ? JSON.stringify(v) : String(v).replace(/_/g, ' '))).join(', ');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
