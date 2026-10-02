import { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable';
import {
  Plus, Trash2, Save, ArrowRight, Database,
  Loader2, Search, Zap, Eye, Wand2, ClipboardCheck, Layers,
} from 'lucide-react';
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
  draft: 'bg-yellow-500/20 text-yellow-300',
  active: 'bg-green-500/20 text-green-300',
  inactive: 'bg-gray-500/20 text-gray-400',
};

const TRANSFORM_OPTIONS = ['none', 'upper', 'lower', 'trim', 'string'];

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

function normalize(s: string): string {
  return s.toLowerCase().replace(/_/g, '');
}

function getSourceParam(schema: string): string | undefined {
  if (schema === 'oracle_erp') return 'oracle';
  if (schema === 'sap_s4hana') return 'sap';
  if (schema === 'sfdc_itxp2dev') return 'simulator';
  if (schema === 'external_sources') return 'external';
  return undefined;
}

export default function MappingRulesEditor() {
  const [rules, setRules] = useState<MappingRule[]>([]);
  const [selectedRule, setSelectedRule] = useState<MappingRule | null>(null);
  const [editState, setEditState] = useState<EditState | null>(null);
  const [schemaEntities, setSchemaEntities] = useState<any[]>([]);
  const [fdwTables, setFdwTables] = useState<ForeignTableInfo[]>([]);
  const [sourceColumns, setSourceColumns] = useState<ColumnInfo[]>([]);
  const [previewRows, setPreviewRows] = useState<any[]>([]);
  const [previewMeta, setPreviewMeta] = useState<{ durationMs: number; rowCount: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [autoMapping, setAutoMapping] = useState(false);
  const [autoMapResult, setAutoMapResult] = useState<AutoMapResponse | null>(null);
  const [auditOpen, setAuditOpen] = useState(false);

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const data = await mappingRuleService.list();
      setRules(data);
    } catch { setRules([]); }
    finally { setLoading(false); }
  }, []);

  const handleAutoMap = async () => {
    if (!confirm(
      'This will delete existing auto-mapped rules and re-create them by matching schema entities to actual FDW and simulator tables.\n\nManually created rules will not be affected.\n\nContinue?'
    )) return;
    setAutoMapping(true);
    setAutoMapResult(null);
    try {
      const result = await mappingRuleService.autoMap(true);
      setAutoMapResult(result);
      await loadRules();
    } catch (e) {
      console.error('Auto-map failed', e);
      setAutoMapResult({ created: 0, skipped: 0, errors: 1, details: [{ entity: 'all', status: 'error', reason: String(e) }] });
    } finally {
      setAutoMapping(false);
    }
  };

  useEffect(() => {
    loadRules();
    apiClient.get('/api/v1/control-plane/entities').then(setSchemaEntities).catch(() => {});
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
    setEditState(prev => prev ? { ...prev, [key]: value } : prev);
  };

  const updateFieldMap = (index: number, key: keyof FieldMap, value: string) => {
    setEditState(prev => {
      if (!prev) return prev;
      const maps = prev.fieldMaps.map((f, i) => i === index ? { ...f, [key]: value } : f);
      return { ...prev, fieldMaps: maps };
    });
  };

  const addFieldMap = () => {
    setEditState(prev => {
      if (!prev) return prev;
      return { ...prev, fieldMaps: [...prev.fieldMaps, { sourceField: '', targetField: '' }] };
    });
  };

  const removeFieldMap = (index: number) => {
    setEditState(prev => {
      if (!prev) return prev;
      return { ...prev, fieldMaps: prev.fieldMaps.filter((_, i) => i !== index) };
    });
  };

  const handleVirtualEntityChange = (entityName: string) => {
    const entity = schemaEntities.find((e: any) => e.name === entityName);
    if (!entity) return;
    const targetFields: FieldMap[] = (entity.fields || []).map((f: any) => ({
      sourceField: '',
      targetField: f.name,
    }));
    setEditState(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        virtualEntity: entityName,
        sourceSystem: entity.system || '',
        fieldMaps: targetFields.length > 0 ? targetFields : [{ sourceField: '', targetField: '' }],
      };
    });
  };

  const handleSourceTableChange = async (tableKey: string) => {
    if (!tableKey) { setSourceColumns([]); return; }
    const dotIdx = tableKey.indexOf('.');
    const schema = tableKey.substring(0, dotIdx);
    const table = tableKey.substring(dotIdx + 1);
    setEditState(prev => {
      if (!prev) return prev;
      return { ...prev, sourceSchema: schema, sourceTable: table, sourceType: 'FDW' };
    });
    try {
      const cols = await fdwService.getColumns(schema, table, getSourceParam(schema));
      setSourceColumns(cols);
    } catch { setSourceColumns([]); }
  };

  const handleAutoMatch = () => {
    if (!editState) return;
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
      await loadRules();
    } catch (e) { console.error('Save failed', e); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!editState?.id || !confirm('Delete this mapping rule?')) return;
    try {
      await mappingRuleService.delete(editState.id);
      setSelectedRule(null);
      setEditState(null);
      await loadRules();
    } catch (e) { console.error('Delete failed', e); }
  };

  const handlePreview = async () => {
    if (!editState?.virtualEntity) return;
    try {
      const targetFields = editState.fieldMaps.filter(fm => fm.targetField).map(fm => fm.targetField);
      const resp = await virtualQueryService.queryEntity({
        virtualEntity: editState.virtualEntity,
        fields: targetFields.length > 0 ? targetFields : undefined,
        limit: 5,
      });
      setPreviewRows(resp.rows || []);
      setPreviewMeta({ durationMs: resp.metadata?.durationMs || 0, rowCount: resp.metadata?.rowCount || resp.rows?.length || 0 });
      setShowPreview(true);
    } catch {
      setPreviewRows([]);
      setPreviewMeta(null);
      setShowPreview(true);
    }
  };

  const filteredRules = rules.filter(r =>
    !searchFilter || r.name.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const entityFields: any[] = editState?.virtualEntity
    ? (schemaEntities.find((e: any) => e.name === editState.virtualEntity)?.fields || [])
    : [];

  const sourceTableKey = editState?.sourceSchema && editState?.sourceTable
    ? `${editState.sourceSchema}.${editState.sourceTable}` : '';

  const fieldLookup = new Map<string, string>();
  if (editState) {
    editState.fieldMaps.forEach(fm => {
      if (fm.sourceField && fm.targetField) fieldLookup.set(fm.sourceField, fm.targetField);
    });
  }

  const SYSTEM_COLORS: Record<string, string> = {
    Salesforce: 'bg-blue-500', Oracle: 'bg-orange-500', SAP: 'bg-green-500',
  };

  const groupedRules = useMemo(() => {
    const groups: Record<string, MappingRule[]> = {};
    for (const r of filteredRules) {
      const sys = r.sourceSystem || 'Other';
      if (!groups[sys]) groups[sys] = [];
      groups[sys].push(r);
    }
    return groups;
  }, [filteredRules]);

  const mappedCount = editState?.fieldMaps.filter(fm => fm.sourceField && fm.targetField).length ?? 0;

  return (
    <div className="flex flex-col h-full min-h-0">
      <ResizablePanelGroup direction="horizontal" className="flex-1 min-h-0 px-2 pt-2 gap-0">
        {/* ===== LEFT: Rule List ===== */}
        <ResizablePanel defaultSize={22} minSize={14} maxSize={38} className="min-h-0 min-w-0">
          <Card className="h-full flex flex-col min-h-0 border rounded-md overflow-hidden">
            <CardHeader className="pb-2 shrink-0 py-3 px-3">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-sm">Mapping Rules</CardTitle>
                <Badge className="bg-muted text-muted-foreground text-[9px] shrink-0">{filteredRules.length}</Badge>
              </div>
              <div className="relative mt-2">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <Input value={searchFilter} onChange={e => setSearchFilter(e.target.value)} placeholder="Filter rules..." className="pl-7 h-7 text-xs" />
              </div>
              <div className="flex items-center gap-1 mt-2">
                <Button variant="ghost" size="sm" className="h-6 text-[10px] px-1.5" onClick={handleAutoMap} disabled={autoMapping} title="Auto-create mapping rules">
                  {autoMapping ? <Loader2 className="h-3 w-3 mr-0.5 animate-spin" /> : <Wand2 className="h-3 w-3 mr-0.5" />}Auto-Map
                </Button>
                <Button variant="ghost" size="sm" className="h-6 text-[10px] px-1.5" onClick={() => setAuditOpen(true)} title="Audit coverage">
                  <ClipboardCheck className="h-3 w-3 mr-0.5" />Audit
                </Button>
                <Button variant="ghost" size="sm" className="h-6 text-[10px] px-1.5" onClick={handleNew}>
                  <Plus className="h-3 w-3 mr-0.5" />New
                </Button>
              </div>
              {autoMapResult && (
                <div className={`p-2 rounded-md text-xs mt-2 ${autoMapResult.errors > 0 ? 'bg-red-500/10 text-red-300' : 'bg-green-500/10 text-green-300'}`}>
                  <div className="font-medium">Auto-Map: {autoMapResult.created} created, {autoMapResult.skipped} skipped{autoMapResult.errors > 0 && `, ${autoMapResult.errors} errors`}</div>
                  <button onClick={() => setAutoMapResult(null)} className="text-[10px] underline mt-0.5 opacity-70 hover:opacity-100">Dismiss</button>
                </div>
              )}
            </CardHeader>
            <CardContent className="flex-1 min-h-0 p-0 flex flex-col">
              <ScrollArea className="flex-1 min-h-0">
                {loading ? (
                  <div className="p-4 flex justify-center"><Loader2 className="h-4 w-4 animate-spin" /></div>
                ) : (
                  <div className="divide-y pr-2">
                    {Object.entries(groupedRules).map(([system, items]) => (
                      <div key={system}>
                        <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-muted/50">
                          <span className={`h-2 w-2 rounded-full shrink-0 ${SYSTEM_COLORS[system] || 'bg-gray-500'}`} />
                          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{system}</span>
                          <span className="text-[10px] text-muted-foreground ml-auto">{items.length}</span>
                        </div>
                        {items.map(rule => (
                          <button
                            key={rule.id}
                            onClick={() => selectRule(rule)}
                            className={`w-full text-left p-2.5 hover:bg-muted/50 transition-colors text-xs ${
                              selectedRule?.id === rule.id ? 'bg-blue-600/10 border-l-2 border-blue-500' : ''
                            }`}
                          >
                            <div className="flex items-center justify-between gap-1.5">
                              <span className="truncate font-medium">{rule.name}</span>
                              <Badge className={`text-[9px] shrink-0 ${STATUS_STYLES[rule.status]}`}>{rule.status}</Badge>
                            </div>
                            <div className="text-[10px] text-muted-foreground mt-0.5">{rule.virtualEntity}</div>
                            <div className="flex items-center gap-1 text-[10px] text-muted-foreground mt-0.5">
                              <Database className="h-2.5 w-2.5" />
                              <span>{rule.sourceTable}</span>
                            </div>
                          </button>
                        ))}
                      </div>
                    ))}
                    {filteredRules.length === 0 && (
                      <div className="p-4 text-center text-muted-foreground text-xs">
                        {rules.length === 0 ? 'No mapping rules yet' : 'No matches'}
                      </div>
                    )}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* ===== CENTER: Editor Form ===== */}
        <ResizablePanel defaultSize={50} minSize={30} className="min-h-0 min-w-0">
          {editState ? (
            <Card className="h-full flex flex-col min-h-0 border rounded-md overflow-hidden mx-1">
              <CardHeader className="pb-2 shrink-0 py-3 px-3">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-sm truncate">{editState.id ? editState.name : 'New Mapping Rule'}</CardTitle>
                  {editState.id && <Badge className={`text-[9px] ${STATUS_STYLES[editState.status]}`}>{editState.status}</Badge>}
                  <div className="flex-1" />
                  {editState.id && (
                    <Button variant="ghost" size="sm" className="h-7 text-destructive hover:text-destructive" onClick={handleDelete}>
                      <Trash2 className="h-3.5 w-3.5 mr-1" />Delete
                    </Button>
                  )}
                  <Button size="sm" className="h-7" onClick={handleSave} disabled={saving || !editState.name}>
                    {saving ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}Save
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="flex-1 min-h-0 p-0 flex flex-col">
                <ScrollArea className="flex-1 min-h-0 px-3 pb-3">
                  <div className="space-y-4 pt-1">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs text-muted-foreground mb-1 block">Name</label>
                        <Input value={editState.name} onChange={e => updateField('name', e.target.value)} className="h-8 text-xs" />
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground mb-1 block">Virtual Entity</label>
                        <select value={editState.virtualEntity} onChange={e => handleVirtualEntityChange(e.target.value)} className="w-full h-8 text-xs rounded-md border bg-card px-2" disabled={!!editState.id}>
                          <option value="">Select entity...</option>
                          {schemaEntities.map((ent: any) => <option key={ent.name} value={ent.name}>{ent.name}</option>)}
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">Source Table (FDW)</label>
                      <select value={sourceTableKey} onChange={e => handleSourceTableChange(e.target.value)} className="w-full h-8 text-xs rounded-md border bg-card px-2" disabled={!!editState.id}>
                        <option value="">Select table...</option>
                        {fdwTables.map(t => { const key = `${t.schemaName}.${t.tableName}`; return <option key={key} value={key}>{key}</option>; })}
                      </select>
                    </div>

                    <div className="border rounded-lg">
                      <div className="flex items-center gap-2 p-2.5 text-xs font-medium">
                        Field Mappings ({editState.fieldMaps.length})
                        <div className="flex-1" />
                        <button onClick={handleAutoMatch} className="flex items-center gap-1 text-[10px] text-blue-400 hover:text-blue-300"><Zap className="h-3 w-3" />Auto-Match</button>
                        <button onClick={addFieldMap} className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground"><Plus className="h-3 w-3" />Add</button>
                      </div>
                      <div className="border-t divide-y">
                        {editState.fieldMaps.map((fm, idx) => (
                          <div key={idx} className="flex items-center gap-2 px-2.5 py-1.5">
                            <select value={fm.sourceField} onChange={e => updateFieldMap(idx, 'sourceField', e.target.value)} className="h-7 text-xs rounded-md border bg-card px-1.5 flex-1 font-mono">
                              <option value="">source...</option>
                              {sourceColumns.map(c => <option key={c.columnName} value={c.columnName}>{c.columnName} ({c.dataType})</option>)}
                            </select>
                            <ArrowRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                            <select value={fm.targetField} onChange={e => updateFieldMap(idx, 'targetField', e.target.value)} className="h-7 text-xs rounded-md border bg-card px-1.5 flex-1 font-mono">
                              <option value="">target...</option>
                              {entityFields.map((f: any) => <option key={f.name} value={f.name}>{f.name} ({f.dataType})</option>)}
                            </select>
                            <select value={fm.transform || 'none'} onChange={e => updateFieldMap(idx, 'transform', e.target.value === 'none' ? '' : e.target.value)} className="h-7 text-xs rounded-md border bg-card px-1.5 w-20">
                              {TRANSFORM_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                            <Button variant="ghost" size="sm" onClick={() => removeFieldMap(idx)} className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive" disabled={editState.fieldMaps.length <= 1}>
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">Business Logic (SQL)</label>
                      <textarea value={editState.businessLogic} onChange={e => updateField('businessLogic', e.target.value)} className="w-full h-20 p-2 rounded-lg border bg-card font-mono text-xs resize-none focus:outline-none focus:ring-1 focus:ring-blue-500" placeholder="e.g. CASE WHEN status = 'A' THEN 'Active' ELSE 'Inactive' END" />
                    </div>

                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">Filter Expression (WHERE clause)</label>
                      <textarea value={editState.filterExpression} onChange={e => updateField('filterExpression', e.target.value)} className="w-full h-16 p-2 rounded-lg border bg-card font-mono text-xs resize-none focus:outline-none focus:ring-1 focus:ring-blue-500" placeholder="e.g. active = true AND deleted_at IS NULL" />
                    </div>

                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">Status</label>
                      <div className="flex items-center gap-1 rounded-lg border overflow-hidden w-fit">
                        {(['draft', 'active', 'inactive'] as const).map(s => (
                          <button key={s} onClick={() => updateField('status', s)} className={`px-3 py-1 text-xs capitalize transition-colors ${editState.status === s ? STATUS_STYLES[s] : 'text-muted-foreground hover:bg-muted'}`}>{s}</button>
                        ))}
                      </div>
                    </div>
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground text-sm border border-dashed rounded-lg mx-1">
              <div className="text-center">
                <Database className="h-8 w-8 mx-auto mb-2 opacity-40" />
                <p>Select a mapping rule or create a new one</p>
              </div>
            </div>
          )}
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* ===== RIGHT: Preview + Metadata ===== */}
        <ResizablePanel defaultSize={28} minSize={18} maxSize={42} className="min-h-0 min-w-0">
          {editState ? (
            <Card className="h-full flex flex-col min-h-0 border rounded-md overflow-hidden">
              <CardHeader className="pb-2 shrink-0 py-3 px-3">
                <CardTitle className="text-sm">{editState.id ? editState.name : 'New Rule'}</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 min-h-0 p-0 flex flex-col">
                <ScrollArea className="flex-1 min-h-0 px-3 pb-3">
                  {/* Mapping Summary */}
                  <div className="space-y-3 pt-1">
                    <div className="border rounded-lg p-3 space-y-2">
                      <div className="flex items-center gap-2 text-xs">
                        <Database className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="font-mono text-muted-foreground">{editState.sourceSchema}.{editState.sourceTable || '...'}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <ArrowRight className="h-3.5 w-3.5 text-blue-400" />
                        <span className="font-medium">{editState.virtualEntity || '...'}</span>
                      </div>
                      <div className="flex items-center gap-3 text-[10px] text-muted-foreground pt-1 border-t">
                        <span>{editState.fieldMaps.length} fields</span>
                        <span>{mappedCount} mapped</span>
                        <Badge className={`text-[9px] ${STATUS_STYLES[editState.status]}`}>{editState.status}</Badge>
                      </div>
                    </div>

                    {/* Field mapping summary */}
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Field Mapping Summary</p>
                      <div className="border rounded-lg divide-y">
                        {editState.fieldMaps.filter(fm => fm.sourceField || fm.targetField).map((fm, i) => (
                          <div key={i} className="flex items-center gap-1.5 px-2.5 py-1 text-[10px]">
                            <span className="font-mono text-muted-foreground truncate flex-1">{fm.sourceField || '—'}</span>
                            <ArrowRight className="h-2.5 w-2.5 text-muted-foreground shrink-0" />
                            <span className="font-mono font-medium truncate flex-1">{fm.targetField || '—'}</span>
                            {fm.transform && fm.transform !== 'none' && (
                              <Badge variant="outline" className="text-[8px] shrink-0">{fm.transform}</Badge>
                            )}
                          </div>
                        ))}
                        {editState.fieldMaps.filter(fm => fm.sourceField || fm.targetField).length === 0 && (
                          <div className="p-2.5 text-[10px] text-muted-foreground text-center">No field mappings configured</div>
                        )}
                      </div>
                    </div>

                    {/* Data Preview */}
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Preview Data</p>
                        <Button variant="outline" size="sm" className="h-6 text-[10px]" onClick={handlePreview} disabled={!editState.virtualEntity}>
                          <Eye className="h-3 w-3 mr-1" />Preview
                        </Button>
                      </div>
                      {showPreview ? (
                        <div className="border rounded-lg overflow-hidden">
                          {previewMeta && (
                            <div className="px-2.5 py-1.5 bg-muted/50 text-[10px] text-muted-foreground flex gap-3">
                              <span>{previewMeta.rowCount} rows</span>
                              <span>{previewMeta.durationMs}ms</span>
                            </div>
                          )}
                          {previewRows.length > 0 ? (
                            <div className="overflow-x-auto">
                              <table className="w-full text-xs">
                                <thead>
                                  <tr className="bg-muted/30">
                                    {Object.keys(previewRows[0]).map(col => (
                                      <th key={`src-${col}`} className="px-2 py-1 text-left text-muted-foreground font-normal">{col}</th>
                                    ))}
                                  </tr>
                                  <tr className="bg-muted/10">
                                    {Object.keys(previewRows[0]).map(col => (
                                      <th key={`tgt-${col}`} className="px-2 py-1 text-left font-medium">{fieldLookup.get(col) || '—'}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="divide-y">
                                  {previewRows.map((row, i) => (
                                    <tr key={i} className="hover:bg-muted/20">
                                      {Object.values(row).map((val, j) => (
                                        <td key={j} className="px-2 py-1 font-mono truncate max-w-[160px]">{String(val ?? '')}</td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <div className="p-3 text-center text-muted-foreground text-xs">No preview data</div>
                          )}
                        </div>
                      ) : (
                        <div className="border border-dashed rounded-lg p-4 text-center text-[10px] text-muted-foreground">
                          Click Preview to load sample data
                        </div>
                      )}
                    </div>
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          ) : (
            <Card className="h-full flex flex-col min-h-0 border rounded-md overflow-hidden">
              <CardHeader className="shrink-0 py-3 px-3">
                <CardTitle className="text-sm">Details</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 flex items-center justify-center">
                <div className="text-center text-muted-foreground">
                  <Layers className="h-6 w-6 mx-auto mb-2 opacity-40" />
                  <p className="text-xs">Select a rule to see details</p>
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
