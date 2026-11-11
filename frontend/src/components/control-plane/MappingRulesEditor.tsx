/**
 * Data Plane → Mapping rules. Papu's original layout (rule list | editor |
 * summary and data), drawn in the product theme: Geist type, theme colours,
 * the shared icon set, in-app confirm dialogs and toasts.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { Icon } from '@/components/ds/Icon';
import { SearchInput } from '@/components/ds/kit';
import { confirmDialog } from '@/components/ds/confirm';
import { cn } from '@/lib/utils';
import { MappingAuditPanel } from './MappingAuditPanel';
import {
  mappingRuleService,
  type MappingRule,
  type FieldMap,
  type CreateMappingRuleRequest,
  type UpdateMappingRuleRequest,
  type AutoMapResponse,
} from '@/services/mappingRuleService';
import { fdwService } from '@/services/fdwService';
import { apiClient } from '@/services/apiClient';
import { virtualQueryService } from '@/services/virtualQueryService';
import type { ForeignTableInfo, ColumnInfo } from '@/types/fdwTypes';

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-warning/15 text-warning',
  active: 'bg-success/15 text-success',
  inactive: 'bg-muted text-muted-foreground',
};
const SYSTEM_COLOUR: Record<string, string> = {
  Salesforce: 'hsl(var(--chart-1))',
  Oracle: 'hsl(var(--chart-5))',
  SAP: 'hsl(var(--chart-4))',
};

const TRANSFORM_OPTIONS = ['none', 'upper', 'lower', 'trim', 'string'];
/** Rows loaded by Preview. */
const PREVIEW_LIMIT = 10;

const SELECT = 'h-9 w-full rounded-md border border-input bg-background px-2 text-sm text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60';
const TEXTAREA = 'w-full resize-none rounded-lg border border-input bg-background p-2.5 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring';

interface SchemaField { name: string; dataType?: string }
interface SchemaEntity { name: string; system?: string; fields?: SchemaField[] }
type PreviewRow = Record<string, unknown>;

interface EditState {
  id?: string;
  name: string;
  virtualEntity: string;
  sourceType: 'FDW' | 'ETL' | 'CDC';
  sourceSystem: string;
  sourceSchema: string;
  sourceTable: string;
  fieldMaps: FieldMap[];
  businessLogic: string;
  filterExpression: string;
  status: 'draft' | 'active' | 'inactive';
}

function makeEditState(rule?: MappingRule | null): EditState {
  if (!rule) {
    return {
      name: '', virtualEntity: '', sourceType: 'FDW', sourceSystem: '',
      sourceSchema: '', sourceTable: '',
      fieldMaps: [{ sourceField: '', targetField: '' }],
      businessLogic: '', filterExpression: '', status: 'draft',
    };
  }
  return {
    id: rule.id, name: rule.name, virtualEntity: rule.virtualEntity,
    sourceType: rule.sourceType, sourceSystem: rule.sourceSystem,
    sourceSchema: rule.sourceSchema, sourceTable: rule.sourceTable,
    fieldMaps: rule.fieldMaps.map(f => ({ ...f })),
    businessLogic: rule.businessLogic || '',
    filterExpression: rule.filterExpression || '',
    status: rule.status,
  };
}

const normalize = (s: string) => s.toLowerCase().replace(/_/g, '');
const errorText = (e: unknown, fallback: string): string => (e instanceof Error && e.message ? e.message : fallback);

function getSourceParam(schema: string): string | undefined {
  if (schema === 'oracle_erp') return 'oracle';
  if (schema === 'sap_s4hana') return 'sap';
  if (schema === 'sfdc_itxp2dev') return 'simulator';
  if (schema === 'external_sources') return 'external';
  return undefined;
}

function Pill({ className, children }: { className?: string; children: React.ReactNode }) {
  return <span className={cn('inline-flex shrink-0 items-center rounded-md px-1.5 py-0.5 text-xs font-medium', className)}>{children}</span>;
}
function Label({ htmlFor, children }: { htmlFor?: string; children: React.ReactNode }) {
  return <label htmlFor={htmlFor} className="mb-1.5 block text-xs font-medium text-muted-foreground">{children}</label>;
}
function Spinner({ className }: { className?: string }) {
  return <Icon name="spinner" className={cn('h-4 w-4 animate-spin', className)} />;
}

export default function MappingRulesEditor() {
  const [rules, setRules] = useState<MappingRule[]>([]);
  const [selectedRule, setSelectedRule] = useState<MappingRule | null>(null);
  const [editState, setEditState] = useState<EditState | null>(null);
  const [schemaEntities, setSchemaEntities] = useState<SchemaEntity[]>([]);
  const [fdwTables, setFdwTables] = useState<ForeignTableInfo[]>([]);
  const [sourceColumns, setSourceColumns] = useState<ColumnInfo[]>([]);
  const [previewRows, setPreviewRows] = useState<PreviewRow[]>([]);
  const [previewMeta, setPreviewMeta] = useState<{ durationMs: number; rowCount: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [autoMapping, setAutoMapping] = useState(false);
  const [autoMapResult, setAutoMapResult] = useState<AutoMapResponse | null>(null);
  const [auditOpen, setAuditOpen] = useState(false);

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      setRules(await mappingRuleService.list());
    } catch { setRules([]); }
    finally { setLoading(false); }
  }, []);

  const handleAutoMap = async () => {
    if (!(await confirmDialog({
      title: 'Re-create the automatic mapping rules?',
      description: 'Existing auto-mapped rules are deleted and created again by matching schema entities to the FDW and simulator tables. Rules created by hand are not affected.',
      confirmLabel: 'Auto-map',
    }))) return;
    setAutoMapping(true);
    setAutoMapResult(null);
    try {
      const result = await mappingRuleService.autoMap(true);
      setAutoMapResult(result);
      await loadRules();
    } catch (e) {
      setAutoMapResult({ created: 0, skipped: 0, errors: 1, details: [{ entity: 'all', status: 'error', reason: String(e) }] });
      toast.error('Auto-map failed', { description: errorText(e, 'The request did not complete.') });
    } finally {
      setAutoMapping(false);
    }
  };

  useEffect(() => {
    loadRules();
    apiClient.get<SchemaEntity[]>('/api/v1/control-plane/entities').then(list => setSchemaEntities(list || [])).catch(() => {});
    Promise.all([
      fdwService.listTables().catch(() => [] as ForeignTableInfo[]),
      fdwService.listTables(undefined, 'simulator').catch(() => [] as ForeignTableInfo[]),
      fdwService.listTables(undefined, 'oracle').catch(() => [] as ForeignTableInfo[]),
      fdwService.listTables(undefined, 'sap').catch(() => [] as ForeignTableInfo[]),
    ]).then(([fdw, sfdc, oracle, sap]) => {
      const seen = new Set<string>();
      const all: ForeignTableInfo[] = [];
      for (const t of [...fdw, ...sfdc, ...oracle, ...sap]) {
        const key = `${t.schemaName}.${t.tableName}`;
        if (!seen.has(key)) { seen.add(key); all.push(t); }
      }
      setFdwTables(all);
    }).catch(() => {});
  }, [loadRules]);

  const selectRule = (rule: MappingRule) => {
    setSelectedRule(rule);
    setEditState(makeEditState(rule));
    setSourceColumns([]);
    setPreviewRows([]);
    setShowPreview(false);
    if (rule.sourceSchema && rule.sourceTable) {
      fdwService.getColumns(rule.sourceSchema, rule.sourceTable, getSourceParam(rule.sourceSchema))
        .then(setSourceColumns).catch(() => {});
    }
  };

  const handleNew = () => {
    setSelectedRule(null);
    setEditState(makeEditState());
    setSourceColumns([]);
    setPreviewRows([]);
    setShowPreview(false);
  };

  const updateField = <K extends keyof EditState>(key: K, value: EditState[K]) => {
    setEditState(prev => (prev ? { ...prev, [key]: value } : prev));
  };

  const updateFieldMap = (index: number, key: keyof FieldMap, value: string) => {
    setEditState(prev => (prev ? { ...prev, fieldMaps: prev.fieldMaps.map((f, i) => (i === index ? { ...f, [key]: value } : f)) } : prev));
  };
  const addFieldMap = () => {
    setEditState(prev => (prev ? { ...prev, fieldMaps: [...prev.fieldMaps, { sourceField: '', targetField: '' }] } : prev));
  };
  const removeFieldMap = (index: number) => {
    setEditState(prev => (prev ? { ...prev, fieldMaps: prev.fieldMaps.filter((_, i) => i !== index) } : prev));
  };

  const handleVirtualEntityChange = (entityName: string) => {
    const entity = schemaEntities.find(e => e.name === entityName);
    if (!entity) return;
    const targetFields: FieldMap[] = (entity.fields || []).map(f => ({ sourceField: '', targetField: f.name }));
    setEditState(prev => (prev ? {
      ...prev,
      virtualEntity: entityName,
      sourceSystem: entity.system || '',
      fieldMaps: targetFields.length > 0 ? targetFields : [{ sourceField: '', targetField: '' }],
    } : prev));
  };

  const handleSourceTableChange = async (tableKey: string) => {
    if (!tableKey) { setSourceColumns([]); return; }
    const dotIdx = tableKey.indexOf('.');
    const schema = tableKey.substring(0, dotIdx);
    const table = tableKey.substring(dotIdx + 1);
    setEditState(prev => (prev ? { ...prev, sourceSchema: schema, sourceTable: table, sourceType: 'FDW' } : prev));
    try {
      setSourceColumns(await fdwService.getColumns(schema, table, getSourceParam(schema)));
    } catch { setSourceColumns([]); }
  };

  const handleAutoMatch = () => {
    setEditState(prev => {
      if (!prev) return prev;
      const maps = prev.fieldMaps.map(fm => {
        if (fm.sourceField) return fm;
        const match = sourceColumns.find(c => normalize(c.columnName) === normalize(fm.targetField));
        return match ? { ...fm, sourceField: match.columnName } : fm;
      });
      return { ...prev, fieldMaps: maps };
    });
  };

  const handleSave = async () => {
    if (!editState) return;
    setSaving(true);
    try {
      if (editState.id) {
        const payload: UpdateMappingRuleRequest = {
          name: editState.name, fieldMaps: editState.fieldMaps,
          businessLogic: editState.businessLogic || undefined,
          filterExpression: editState.filterExpression || undefined,
          status: editState.status,
        };
        const updated = await mappingRuleService.update(editState.id, payload);
        setSelectedRule(updated);
        setEditState(makeEditState(updated));
      } else {
        const payload: CreateMappingRuleRequest = {
          name: editState.name, virtualEntity: editState.virtualEntity,
          sourceType: editState.sourceType, sourceSystem: editState.sourceSystem,
          sourceTable: editState.sourceTable, sourceSchema: editState.sourceSchema,
          fieldMaps: editState.fieldMaps,
          businessLogic: editState.businessLogic || undefined,
          filterExpression: editState.filterExpression || undefined,
        };
        const created = await mappingRuleService.create(payload);
        setSelectedRule(created);
        setEditState(makeEditState(created));
      }
      toast.success('Mapping rule saved');
      await loadRules();
    } catch (e) {
      toast.error('The rule was not saved', { description: errorText(e, 'The request did not complete.') });
    } finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!editState?.id || !(await confirmDialog({ title: 'Delete this mapping rule?', description: 'This cannot be undone.', destructive: true }))) return;
    try {
      await mappingRuleService.delete(editState.id);
      setSelectedRule(null);
      setEditState(null);
      toast.success('Mapping rule deleted');
      await loadRules();
    } catch (e) {
      toast.error('The rule was not deleted', { description: errorText(e, 'The request did not complete.') });
    }
  };

  const handlePreview = async () => {
    if (!editState?.virtualEntity) return;
    setPreviewing(true);
    try {
      const targetFields = editState.fieldMaps.filter(fm => fm.targetField).map(fm => fm.targetField);
      const resp = await virtualQueryService.queryEntity({
        virtualEntity: editState.virtualEntity,
        fields: targetFields.length > 0 ? targetFields : undefined,
        limit: PREVIEW_LIMIT,
      });
      setPreviewRows((resp.rows || []) as PreviewRow[]);
      setPreviewMeta({ durationMs: resp.metadata?.durationMs || 0, rowCount: resp.metadata?.rowCount || resp.rows?.length || 0 });
    } catch {
      setPreviewRows([]);
      setPreviewMeta(null);
    } finally {
      setShowPreview(true);
      setPreviewing(false);
    }
  };

  const filteredRules = useMemo(
    () => rules.filter(r => !searchFilter || r.name.toLowerCase().includes(searchFilter.toLowerCase()) || (r.virtualEntity || '').toLowerCase().includes(searchFilter.toLowerCase())),
    [rules, searchFilter],
  );

  const entityFields: SchemaField[] = editState?.virtualEntity
    ? (schemaEntities.find(e => e.name === editState.virtualEntity)?.fields || [])
    : [];

  const sourceTableKey = editState?.sourceSchema && editState?.sourceTable ? `${editState.sourceSchema}.${editState.sourceTable}` : '';

  const fieldLookup = new Map<string, string>();
  editState?.fieldMaps.forEach(fm => { if (fm.sourceField && fm.targetField) fieldLookup.set(fm.sourceField, fm.targetField); });

  const groupedRules = useMemo(() => {
    const groups: Record<string, MappingRule[]> = {};
    for (const r of filteredRules) (groups[r.sourceSystem || 'Other'] ??= []).push(r);
    return groups;
  }, [filteredRules]);

  const mappedCount = editState?.fieldMaps.filter(fm => fm.sourceField && fm.targetField).length ?? 0;
  const noFieldMaps = !!editState && editState.fieldMaps.length === 0;
  const summaryMaps = editState?.fieldMaps.filter(fm => fm.sourceField || fm.targetField) || [];

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ResizablePanelGroup direction="horizontal" className="min-h-0 flex-1 gap-0 px-2 py-2">
        {/* ===== Left: rule list ===== */}
        <ResizablePanel defaultSize={22} minSize={14} maxSize={38} className="min-h-0 min-w-0">
          <Card className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border">
            <CardHeader className="shrink-0 space-y-0 px-3 py-3">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-md font-medium">Mapping rules</CardTitle>
                <Pill className="num bg-muted text-muted-foreground">{filteredRules.length}</Pill>
              </div>
              <SearchInput value={searchFilter} onChange={setSearchFilter} placeholder="Filter rules" className="mt-2.5 sm:w-full" aria-label="Filter rules" />
              <div className="mt-2 flex items-center gap-1">
                <Button variant="ghost" size="sm" className="h-8 px-2" onClick={handleAutoMap} disabled={autoMapping} title="Create mapping rules automatically">
                  {autoMapping ? <Spinner className="h-3.5 w-3.5" /> : <Icon name="sparkles" className="h-3.5 w-3.5" />}Auto-map
                </Button>
                <Button variant="ghost" size="sm" className="h-8 px-2" onClick={() => setAuditOpen(true)} title="Check mapping coverage">
                  <Icon name="clipboard" className="h-3.5 w-3.5" />Audit
                </Button>
                <Button variant="ghost" size="sm" className="h-8 px-2" onClick={handleNew}>
                  <Icon name="plus" className="h-3.5 w-3.5" />New
                </Button>
              </div>
              {autoMapResult && (
                <div className={cn('mt-2 rounded-lg p-2.5 text-sm', autoMapResult.errors > 0 ? 'bg-destructive/10 text-destructive' : 'bg-success/10 text-success')} role="status">
                  <div className="font-medium">Auto-map: {autoMapResult.created} created, {autoMapResult.skipped} skipped{autoMapResult.errors > 0 && `, ${autoMapResult.errors} errors`}</div>
                  <button type="button" onClick={() => setAutoMapResult(null)} className="mt-0.5 text-xs underline opacity-80 hover:opacity-100">Dismiss</button>
                </div>
              )}
            </CardHeader>
            <CardContent className="flex min-h-0 flex-1 flex-col p-0">
              <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
                {loading ? (
                  <div className="flex justify-center p-4"><Spinner className="text-muted-foreground" /></div>
                ) : (
                  <div className="divide-y divide-border">
                    {Object.entries(groupedRules).map(([system, items]) => (
                      <div key={system}>
                        <div className="flex items-center gap-2 bg-muted/50 px-3 py-1.5">
                          <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: SYSTEM_COLOUR[system] || 'hsl(var(--muted-foreground))' }} />
                          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{system}</span>
                          <span className="num ml-auto text-xs text-muted-foreground">{items.length}</span>
                        </div>
                        {items.map(rule => {
                          const on = selectedRule?.id === rule.id;
                          return (
                            <button
                              key={rule.id}
                              type="button"
                              onClick={() => selectRule(rule)}
                              aria-pressed={on}
                              className={cn('w-full border-l-2 px-3 py-2.5 text-left transition-colors hover:bg-muted/50', on ? 'border-brand bg-brand/10' : 'border-transparent')}
                            >
                              <div className="flex items-center justify-between gap-1.5">
                                <span className="truncate text-sm font-medium text-foreground">{rule.name}</span>
                                <Pill className={STATUS_STYLES[rule.status]}>{rule.status}</Pill>
                              </div>
                              <div className="mt-0.5 text-xs text-muted-foreground">{rule.virtualEntity}</div>
                              <div className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                                <Icon name="database" className="h-3 w-3" />
                                <span className="truncate font-mono">{rule.sourceTable}</span>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    ))}
                    {filteredRules.length === 0 && (
                      <div className="p-4 text-center text-sm text-muted-foreground">{rules.length === 0 ? 'No mapping rules yet' : 'No matches'}</div>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </ResizablePanel>

        <ResizableHandle withHandle className="mx-1" />

        {/* ===== Centre: editor ===== */}
        <ResizablePanel defaultSize={50} minSize={30} className="min-h-0 min-w-0">
          {editState ? (
            <Card className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border">
              <CardHeader className="shrink-0 space-y-0 px-4 py-3">
                <div className="flex items-center gap-2">
                  <CardTitle className="truncate text-md font-medium">{editState.id ? editState.name : 'New mapping rule'}</CardTitle>
                  {editState.id && <Pill className={STATUS_STYLES[editState.status]}>{editState.status}</Pill>}
                  <div className="flex-1" />
                  {editState.id && (
                    <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={handleDelete}>
                      <Icon name="trash" className="h-3.5 w-3.5" />Delete
                    </Button>
                  )}
                  <Button size="sm" onClick={handleSave} disabled={saving || !editState.name}>
                    {saving ? <Spinner className="h-3.5 w-3.5" /> : <Icon name="check" className="h-3.5 w-3.5" />}Save
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="flex min-h-0 flex-1 flex-col p-0">
                <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4">
                  <div className="space-y-4 pt-1">
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <div>
                        <Label htmlFor="mr-name">Name</Label>
                        <Input id="mr-name" value={editState.name} onChange={e => updateField('name', e.target.value)} className="h-9 text-sm" />
                      </div>
                      <div>
                        <Label htmlFor="mr-entity">Virtual entity</Label>
                        <select id="mr-entity" value={editState.virtualEntity} onChange={e => handleVirtualEntityChange(e.target.value)} className={SELECT} disabled={!!editState.id}>
                          <option value="">Select entity…</option>
                          {editState.virtualEntity && !schemaEntities.some(e => e.name === editState.virtualEntity) && <option value={editState.virtualEntity}>{editState.virtualEntity}</option>}
                          {schemaEntities.map(ent => <option key={ent.name} value={ent.name}>{ent.name}</option>)}
                        </select>
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="mr-source">Source table (FDW)</Label>
                      <select id="mr-source" value={sourceTableKey} onChange={e => handleSourceTableChange(e.target.value)} className={cn(SELECT, 'font-mono')} disabled={!!editState.id}>
                        <option value="">Select table…</option>
                        {sourceTableKey && !fdwTables.some(t => `${t.schemaName}.${t.tableName}` === sourceTableKey) && <option value={sourceTableKey}>{sourceTableKey}</option>}
                        {fdwTables.map(t => { const key = `${t.schemaName}.${t.tableName}`; return <option key={key} value={key}>{key}</option>; })}
                      </select>
                    </div>

                    <div className="rounded-xl border border-border">
                      <div className="flex items-center gap-2 px-3 py-2.5 text-sm font-medium text-foreground">
                        Field mappings <span className="num font-normal text-muted-foreground">({editState.fieldMaps.length})</span>
                        <div className="flex-1" />
                        <button type="button" onClick={handleAutoMatch} disabled={sourceColumns.length === 0} title="Fill empty source fields where the names match"
                          className="flex items-center gap-1 text-xs font-medium text-primary hover:underline disabled:opacity-50 disabled:hover:no-underline dark:text-brand-hi">
                          <Icon name="bolt" className="h-3.5 w-3.5" />Auto-match
                        </button>
                        <button type="button" onClick={addFieldMap} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
                          <Icon name="plus" className="h-3.5 w-3.5" />Add
                        </button>
                      </div>
                      <div className="divide-y divide-border border-t border-border">
                        {noFieldMaps && (
                          <p className="px-3 py-2.5 text-sm text-muted-foreground">No field mapping is set, so every source column is read under its own name. Add fields only where a column must be renamed or transformed.</p>
                        )}
                        {editState.fieldMaps.map((fm, idx) => (
                          <div key={idx} className="flex items-center gap-2 px-3 py-2">
                            <select aria-label={`Source field ${idx + 1}`} value={fm.sourceField} onChange={e => updateFieldMap(idx, 'sourceField', e.target.value)} className={cn(SELECT, 'h-8 flex-1 font-mono')}>
                              <option value="">source…</option>
                              {fm.sourceField && !sourceColumns.some(c => c.columnName === fm.sourceField) && <option value={fm.sourceField}>{fm.sourceField}</option>}
                              {sourceColumns.map(c => <option key={c.columnName} value={c.columnName}>{c.columnName} ({c.dataType})</option>)}
                            </select>
                            <Icon name="arrow-right" className="h-4 w-4 shrink-0 text-muted-foreground" />
                            <select aria-label={`Entity field ${idx + 1}`} value={fm.targetField} onChange={e => updateFieldMap(idx, 'targetField', e.target.value)} className={cn(SELECT, 'h-8 flex-1 font-mono')}>
                              <option value="">target…</option>
                              {fm.targetField && !entityFields.some(f => f.name === fm.targetField) && <option value={fm.targetField}>{fm.targetField}</option>}
                              {entityFields.map(f => <option key={f.name} value={f.name}>{f.name}{f.dataType ? ` (${f.dataType})` : ''}</option>)}
                            </select>
                            <select aria-label={`Transform ${idx + 1}`} value={fm.transform || 'none'} onChange={e => updateFieldMap(idx, 'transform', e.target.value === 'none' ? '' : e.target.value)} className={cn(SELECT, 'h-8 w-24')}>
                              {TRANSFORM_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                            <Button variant="ghost" size="sm" onClick={() => removeFieldMap(idx)} className="h-8 w-8 shrink-0 p-0 text-muted-foreground hover:text-destructive" disabled={editState.fieldMaps.length <= 1} aria-label={`Remove field mapping ${idx + 1}`}>
                              <Icon name="trash" className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="mr-logic">Business logic (SQL)</Label>
                      <textarea id="mr-logic" value={editState.businessLogic} onChange={e => updateField('businessLogic', e.target.value)} className={cn(TEXTAREA, 'h-20')} placeholder="e.g. CASE WHEN status = 'A' THEN 'Active' ELSE 'Inactive' END" />
                    </div>

                    <div>
                      <Label htmlFor="mr-filter">Filter expression (WHERE clause)</Label>
                      <textarea id="mr-filter" value={editState.filterExpression} onChange={e => updateField('filterExpression', e.target.value)} className={cn(TEXTAREA, 'h-16')} placeholder="e.g. active = true AND deleted_at IS NULL" />
                    </div>

                    <div>
                      <Label>Status</Label>
                      <div className="flex w-fit items-center gap-0.5 overflow-hidden rounded-lg border border-border p-0.5" role="radiogroup" aria-label="Status">
                        {(['draft', 'active', 'inactive'] as const).map(s => (
                          <button key={s} type="button" role="radio" aria-checked={editState.status === s} onClick={() => updateField('status', s)}
                            className={cn('rounded-md px-3 py-1 text-sm capitalize transition-colors', editState.status === s ? STATUS_STYLES[s] : 'text-muted-foreground hover:bg-muted')}>
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="flex h-full items-center justify-center rounded-xl border border-dashed text-sm text-muted-foreground">
              <div className="text-center">
                <Icon name="database" className="mx-auto mb-2 h-8 w-8 opacity-40" />
                <p>Select a mapping rule or create a new one</p>
              </div>
            </div>
          )}
        </ResizablePanel>

        <ResizableHandle withHandle className="mx-1" />

        {/* ===== Right: summary and data ===== */}
        <ResizablePanel defaultSize={28} minSize={18} maxSize={42} className="min-h-0 min-w-0">
          {editState ? (
            <Card className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border">
              <CardHeader className="shrink-0 space-y-0 px-3 py-3">
                <CardTitle className="truncate text-md font-medium">{editState.id ? editState.name : 'New rule'}</CardTitle>
              </CardHeader>
              <CardContent className="flex min-h-0 flex-1 flex-col p-0">
                <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-3 pb-3">
                  <div className="space-y-4 pt-1">
                    {/* Mapping summary */}
                    <div className="space-y-2 rounded-xl border border-border p-3">
                      <div className="flex items-center gap-2 text-sm">
                        <Icon name="database" className="h-4 w-4 text-muted-foreground" />
                        <span className="truncate font-mono text-muted-foreground">{editState.sourceSchema ? `${editState.sourceSchema}.` : ''}{editState.sourceTable || '…'}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Icon name="arrow-right" className="h-4 w-4 text-primary dark:text-brand-hi" />
                        <span className="truncate font-medium text-foreground">{editState.virtualEntity || '…'}</span>
                      </div>
                      <div className="flex flex-wrap items-center gap-3 border-t border-border pt-2 text-xs text-muted-foreground">
                        {noFieldMaps ? <span>All columns, as they are</span> : <>
                          <span><span className="num text-foreground">{editState.fieldMaps.length}</span> fields</span>
                          <span><span className="num text-foreground">{mappedCount}</span> mapped</span>
                        </>}
                        <Pill className={STATUS_STYLES[editState.status]}>{editState.status}</Pill>
                      </div>
                    </div>

                    {/* Field mapping summary */}
                    <div>
                      <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">Field mapping summary</p>
                      <div className="divide-y divide-border rounded-xl border border-border">
                        {summaryMaps.map((fm, i) => (
                          <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 text-sm">
                            <span className="flex-1 truncate font-mono text-muted-foreground">{fm.sourceField || '—'}</span>
                            <Icon name="arrow-right" className="h-3 w-3 shrink-0 text-muted-foreground" />
                            <span className="flex-1 truncate font-mono font-medium text-foreground">{fm.targetField || '—'}</span>
                            {fm.transform && fm.transform !== 'none' && <Pill className="border border-border text-muted-foreground">{fm.transform}</Pill>}
                          </div>
                        ))}
                        {summaryMaps.length === 0 && (
                          <div className="p-3 text-center text-sm text-muted-foreground">{noFieldMaps ? 'Every source column is read as it is' : 'No field mappings configured'}</div>
                        )}
                      </div>
                    </div>

                    {/* Data */}
                    <div>
                      <div className="mb-1.5 flex items-center justify-between">
                        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Data</p>
                        <Button variant="outline" size="sm" className="h-8" onClick={handlePreview} disabled={!editState.virtualEntity || previewing}>
                          {previewing ? <Spinner className="h-3.5 w-3.5" /> : <Icon name="eye" className="h-3.5 w-3.5" />}Preview
                        </Button>
                      </div>
                      {showPreview ? (
                        <div className="overflow-hidden rounded-xl border border-border">
                          {previewMeta && (
                            <div className="flex gap-3 bg-muted/50 px-3 py-1.5 text-xs text-muted-foreground">
                              <span><span className="num">{previewMeta.rowCount}</span> rows</span>
                              <span><span className="num">{previewMeta.durationMs}</span> ms</span>
                            </div>
                          )}
                          {previewRows.length > 0 ? (
                            <div className="overflow-x-auto">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="bg-muted/30">
                                    {Object.keys(previewRows[0]).map(col => (
                                      <th key={`src-${col}`} className="whitespace-nowrap px-2.5 py-1.5 text-left text-xs font-normal text-muted-foreground">{col}</th>
                                    ))}
                                  </tr>
                                  <tr className="bg-muted/10">
                                    {Object.keys(previewRows[0]).map(col => (
                                      <th key={`tgt-${col}`} className="whitespace-nowrap px-2.5 py-1.5 text-left text-xs font-medium text-foreground">{fieldLookup.get(col) || '—'}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                  {previewRows.map((row, i) => (
                                    <tr key={i} className="hover:bg-muted/20">
                                      {Object.values(row).map((val, j) => (
                                        <td key={j} className="max-w-[180px] truncate whitespace-nowrap px-2.5 py-1.5 font-mono text-foreground">{String(val ?? '')}</td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <div className="p-3 text-center text-sm text-muted-foreground">No rows returned</div>
                          )}
                        </div>
                      ) : (
                        <div className="rounded-xl border border-dashed p-4 text-center text-sm text-muted-foreground">Click Preview to load the data</div>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border">
              <CardHeader className="shrink-0 space-y-0 px-3 py-3">
                <CardTitle className="text-md font-medium">Details</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-1 items-center justify-center">
                <div className="text-center text-muted-foreground">
                  <Icon name="layers" className="mx-auto mb-2 h-6 w-6 opacity-40" />
                  <p className="text-sm">Select a rule to see details</p>
                </div>
              </CardContent>
            </Card>
          )}
        </ResizablePanel>
      </ResizablePanelGroup>

      <MappingAuditPanel
        open={auditOpen}
        onClose={() => setAuditOpen(false)}
        onSelectRule={(ruleId) => {
          setAuditOpen(false);
          const rule = rules.find(r => r.id === ruleId);
          if (rule) selectRule(rule);
        }}
      />
    </div>
  );
}
