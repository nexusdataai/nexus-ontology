import { useState, useEffect, useCallback, useMemo } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { Field, InlineError, KeyValues, SearchInput, StatusPill } from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
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
import { confirmDialog } from '@/components/ds/confirm';

const TRANSFORM_OPTIONS = ['none', 'upper', 'lower', 'trim', 'string'];
const TRANSFORM_LABEL: Record<string, string> = {
  none: 'No transform', upper: 'Upper case', lower: 'Lower case', trim: 'Trim spaces', string: 'To text',
};
const STATUS_OPTIONS = ['draft', 'active', 'inactive'] as const;

/** Radix Select cannot hold an empty value; this stands for "not chosen". */
const NONE = '__none__';

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

const errorText = (e: unknown, fallback: string): string =>
  e instanceof Error && e.message ? e.message : fallback;

/** One mono select cell of the field-mapping table. */
function FieldSelect({ value, onChange, options, placeholder, label }: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; hint?: string }[];
  placeholder: string;
  label: string;
}) {
  // Keep the saved value visible even while (or if) the option list is missing.
  const items = value && !options.some(o => o.value === value) ? [{ value }, ...options] : options;
  return (
    <Select value={value || undefined} onValueChange={(v) => onChange(v === NONE ? '' : v)}>
      <SelectTrigger aria-label={label} className="h-8 w-full min-w-0 px-2.5 font-mono text-xs">
        <SelectValue placeholder={<span className="font-sans text-subtle-foreground">{placeholder}</span>} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={NONE} className="text-muted-foreground">Not set</SelectItem>
        {items.map(o => (
          <SelectItem key={o.value} value={o.value} className="font-mono text-xs">
            {o.value}{o.hint && <span className="ml-2 font-sans text-muted-foreground">{o.hint}</span>}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function SectionTitle({ title, hint, action }: { title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-3 flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
      <div className="min-w-0">
        <h3 className="text-md font-medium text-foreground">{title}</h3>
        {hint && <p className="mt-0.5 text-sm text-muted-foreground">{hint}</p>}
      </div>
      {action}
    </div>
  );
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
  // Presentation only.
  const [loadError, setLoadError] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [browseOpen, setBrowseOpen] = useState(false);

  const loadRules = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await mappingRuleService.list();
      setRules(data);
    } catch (e) {
      setRules([]);
      setLoadError(errorText(e, 'Mapping rules could not be loaded.'));
    }
    finally { setLoading(false); }
  }, []);

  const handleAutoMap = async () => {
    if (!(await confirmDialog({
      title: 'Re-run auto-mapping?',
      description: 'This deletes the existing auto-mapped rules and re-creates them by matching schema entities to the actual FDW and simulator tables. Manually created rules are not affected.',
      confirmLabel: 'Auto-map',
    }))) return;
    setAutoMapping(true);
    setAutoMapResult(null);
    try {
      const result = await mappingRuleService.autoMap(true);
      setAutoMapResult(result);
      if (result.errors > 0) toast.warning(`Auto-map finished with ${result.errors} ${result.errors === 1 ? 'error' : 'errors'}`, { description: `${result.created} created, ${result.skipped} skipped.` });
      else toast.success('Auto-map finished', { description: `${result.created} created, ${result.skipped} skipped.` });
      await loadRules();
    } catch (e) {
      console.error('Auto-map failed', e);
      setAutoMapResult({ created: 0, skipped: 0, errors: 1, details: [{ entity: 'all', status: 'error', reason: String(e) }] });
      toast.error('Auto-map failed', { description: errorText(e, 'The request did not complete.') });
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
    setPreviewError(null);
    setBrowseOpen(false);
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
    setPreviewError(null);
    setBrowseOpen(false);
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
      toast.success('Mapping rule saved');
      await loadRules();
    } catch (e) {
      console.error('Save failed', e);
      toast.error('The rule was not saved', { description: errorText(e, 'The request did not complete.') });
    }
    finally { setSaving(false); }
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
      console.error('Delete failed', e);
      toast.error('The rule was not deleted', { description: errorText(e, 'The request did not complete.') });
    }
  };

  const handlePreview = async () => {
    if (!editState?.virtualEntity) return;
    setPreviewing(true);
    setPreviewError(null);
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
    } catch (e) {
      setPreviewRows([]);
      setPreviewMeta(null);
      setShowPreview(true);
      setPreviewError(errorText(e, 'The preview query failed.'));
    } finally {
      setPreviewing(false);
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

  // The editor is never blank: open the first rule of the list after load.
  useEffect(() => {
    if (loading || editState) return;
    const first = Object.values(groupedRules)[0]?.[0];
    if (first) selectRule(first);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, editState, groupedRules]);

  const entityOptions: string[] = schemaEntities.map((e: any) => e.name);
  if (editState?.virtualEntity && !entityOptions.includes(editState.virtualEntity)) entityOptions.unshift(editState.virtualEntity);
  const tableOptions: string[] = fdwTables.map(t => `${t.schemaName}.${t.tableName}`);
  if (sourceTableKey && !tableOptions.includes(sourceTableKey)) tableOptions.unshift(sourceTableKey);

  const sourceOptions = sourceColumns.map(c => ({ value: c.columnName, hint: c.dataType }));
  const targetOptions = entityFields.map((f: any) => ({ value: f.name as string, hint: f.dataType as string }));

  /* ------------------------------------------------------------- the list */

  const list = (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 space-y-2.5 border-b border-border p-3">
        <SearchInput value={searchFilter} onChange={setSearchFilter} placeholder="Search rules" className="sm:w-full" />
        <div className="flex items-center gap-1">
          <Button variant="outline" size="sm" onClick={handleNew} className="border-brand/40 text-primary hover:border-brand/70 hover:bg-brand/10 dark:text-brand-hi">
            <Icon name="plus" /> New rule
          </Button>
          <div className="flex-1" />
          <Button variant="ghost" size="sm" className="px-2" onClick={handleAutoMap} disabled={autoMapping} title="Create mapping rules automatically from the source tables">
            <Icon name={autoMapping ? 'spinner' : 'sparkles'} className={autoMapping ? 'animate-spin' : undefined} /> Auto-map
          </Button>
          <Button variant="ghost" size="sm" className="px-2" onClick={() => setAuditOpen(true)} title="Check mapping coverage">
            <Icon name="clipboard" /> Audit
          </Button>
        </div>
        {autoMapResult && (
          autoMapResult.errors > 0 ? (
            <InlineError className="text-xs">
              <p className="font-medium">Auto-map: {autoMapResult.created} created, {autoMapResult.skipped} skipped, {autoMapResult.errors} {autoMapResult.errors === 1 ? 'error' : 'errors'}</p>
              {autoMapResult.details.filter(d => d.status === 'error').slice(0, 3).map((d, i) => (
                <p key={i} className="mt-0.5 break-words">{d.entity}{d.reason ? `: ${d.reason}` : ''}</p>
              ))}
              <button type="button" onClick={() => setAutoMapResult(null)} className="mt-1 underline underline-offset-4">Dismiss</button>
            </InlineError>
          ) : (
            <div className="flex items-start justify-between gap-2 rounded-lg border border-border bg-surface-2/70 px-3 py-2 text-xs text-muted-foreground">
              <span><StatusPill tone="success" className="mr-1.5">Auto-map finished</StatusPill>{autoMapResult.created} created, {autoMapResult.skipped} skipped</span>
              <button type="button" onClick={() => setAutoMapResult(null)} aria-label="Dismiss" className="mt-0.5 text-subtle-foreground hover:text-foreground">
                <Icon name="close" className="h-3 w-3" />
              </button>
            </div>
          )
        )}
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <div className="space-y-3 p-3" aria-busy="true">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-4 w-3/5" />
                <Skeleton className="h-3 w-4/5" />
              </div>
            ))}
          </div>
        ) : loadError ? (
          <div className="p-3"><InlineError onRetry={loadRules}>{loadError}</InlineError></div>
        ) : filteredRules.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-muted-foreground">
            {rules.length === 0 ? 'No mapping rules yet.' : 'No rules match this search.'}
          </p>
        ) : (
          <div className="pb-3">
            {Object.entries(groupedRules).map(([system, items], gi) => (
              <section key={system} className="rise" style={{ '--i': Math.min(gi, 8) } as React.CSSProperties}>
                <h3 className="flex items-center gap-2 px-4 pb-1.5 pt-4 text-xs font-medium text-muted-foreground">
                  <SystemLogo system={system} size="xs" />
                  <span className="truncate">{systemName(system)}</span>
                  <span className="num ml-auto font-normal text-subtle-foreground">{items.length}</span>
                </h3>
                <ul className="px-2">
                  {items.map(rule => {
                    const on = selectedRule?.id === rule.id;
                    return (
                      <li key={rule.id}>
                        <button
                          type="button"
                          onClick={() => selectRule(rule)}
                          aria-current={on ? 'true' : undefined}
                          className={cn(
                            'block w-full rounded-md px-2 py-2 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                            on ? 'bg-accent' : 'hover:bg-accent/60',
                          )}
                        >
                          <span className="flex items-center justify-between gap-2">
                            <span className={cn('truncate text-sm text-foreground', on && 'font-medium')}>{rule.name}</span>
                            <StatusPill status={rule.status} className="font-normal text-muted-foreground" />
                          </span>
                          <span className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                            <span className="truncate font-mono">{rule.sourceTable || 'No table'}</span>
                            <Icon name="arrow-right" className="h-3 w-3 shrink-0 text-subtle-foreground" />
                            <span className="truncate">{rule.virtualEntity}</span>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </div>
        )}
      </div>

      {!loading && !loadError && rules.length > 0 && (
        <div className="shrink-0 border-t border-border px-4 py-2 text-xs text-muted-foreground">
          <span className="num">{filteredRules.length}</span> of <span className="num">{rules.length}</span> rules
        </div>
      )}
    </div>
  );

  /* ----------------------------------------------------------- the editor */

  return (
    <div className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)] lg:grid-cols-[300px_minmax(0,1fr)]">
      <aside className="hidden min-h-0 border-r border-border bg-sidebar/40 lg:block" aria-label="Mapping rules">{list}</aside>

      <Sheet open={browseOpen} onOpenChange={setBrowseOpen}>
        <SheetContent side="left" className="flex w-full flex-col gap-0 p-0 sm:max-w-sm">
          <div className="border-b border-border px-4 pb-3 pt-4 pr-12">
            <SheetTitle className="text-md font-medium">Mapping rules</SheetTitle>
            <SheetDescription className="sr-only">Choose a mapping rule to edit</SheetDescription>
          </div>
          <div className="min-h-0 flex-1">{list}</div>
        </SheetContent>
      </Sheet>

      <div className="flex min-h-0 min-w-0 flex-col">
        <div className="shrink-0 border-b border-border px-4 py-2 lg:hidden">
          <Button variant="outline" size="sm" className="w-full justify-between" onClick={() => setBrowseOpen(true)}>
            <span className="flex min-w-0 items-center gap-2">
              <Icon name="list" className="h-3.5 w-3.5" />
              <span className="truncate">{editState ? (editState.name || 'New rule') : 'Browse rules'}</span>
            </span>
            <span className="flex items-center gap-1.5 font-normal text-muted-foreground">
              <span className="num">{rules.length}</span>
              <Icon name="chevron-down" className="h-3.5 w-3.5" />
            </span>
          </Button>
        </div>

        {!editState ? (
          loading ? (
            <div className="space-y-4 p-5 sm:p-6" aria-busy="true">
              <Skeleton className="h-8 w-72 max-w-full" />
              <Skeleton className="h-9 w-full max-w-2xl" />
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
            </div>
          ) : (
            <div className="space-y-4 p-5 sm:p-6">
              {loadError && <InlineError onRetry={loadRules}>{loadError}</InlineError>}
              <EmptyState
                icon="shuffle"
                title="No mapping rules yet"
                description="A mapping rule connects a source table to a virtual entity, field by field. Create one by hand or let auto-map propose them."
                action={
                  <div className="flex flex-wrap justify-center gap-2">
                    <Button size="sm" onClick={handleNew}><Icon name="plus" /> New rule</Button>
                    <Button size="sm" variant="outline" onClick={handleAutoMap} disabled={autoMapping}>
                      <Icon name={autoMapping ? 'spinner' : 'sparkles'} className={autoMapping ? 'animate-spin' : undefined} /> Auto-map
                    </Button>
                  </div>
                }
              />
            </div>
          )
        ) : (
          <>
            {/* Sticky editor header */}
            <header className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-2 border-b border-border px-4 py-3 sm:px-6">
              <div className="min-w-0 flex-1 basis-64">
                <Input
                  value={editState.name}
                  onChange={e => updateField('name', e.target.value)}
                  placeholder="Rule name"
                  aria-label="Rule name"
                  className="-ml-2 h-9 border-transparent bg-transparent px-2 text-lg font-medium tracking-tight shadow-none hover:border-border focus-visible:border-ring"
                />
                <p className="mt-0.5 flex items-center gap-1.5 truncate text-xs text-muted-foreground">
                  {editState.sourceSystem && <SystemLogo system={editState.sourceSystem} size="xs" />}
                  <span className="truncate font-mono">{sourceTableKey || 'No source table'}</span>
                  <Icon name="arrow-right" className="h-3 w-3 shrink-0 text-subtle-foreground" />
                  <span className="truncate">{editState.virtualEntity || 'No entity'}</span>
                  {!editState.id && <span className="shrink-0 text-subtle-foreground">· Not saved yet</span>}
                </p>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                <Select value={editState.status} onValueChange={(v) => updateField('status', v as EditState['status'])}>
                  <SelectTrigger className="h-8 w-[124px] px-2.5 text-xs" aria-label="Rule status"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {STATUS_OPTIONS.map(s => <SelectItem key={s} value={s}><StatusPill status={s} /></SelectItem>)}
                  </SelectContent>
                </Select>
                {editState.id && (
                  <Button variant="ghost" size="sm" onClick={handleDelete} className="hover:bg-destructive/10 hover:text-destructive">
                    <Icon name="trash" /> Delete
                  </Button>
                )}
                <Button size="sm" onClick={handleSave} disabled={saving || !editState.name}>
                  <Icon name={saving ? 'spinner' : 'check'} className={saving ? 'animate-spin' : undefined} /> Save rule
                </Button>
              </div>
            </header>

            <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
              <div className="grid xl:grid-cols-[minmax(0,1fr)_340px]">
                {/* Form */}
                <div className="min-w-0 space-y-9 px-4 py-6 sm:px-6">
                  <section>
                    <SectionTitle
                      title="Source and target"
                      hint={editState.id ? 'The entity and source table are fixed once a rule is created.' : 'Choose the virtual entity to fill and the source table it reads from.'}
                    />
                    <div className="grid max-w-3xl gap-4 sm:grid-cols-2">
                      <Field label="Virtual entity">
                        <Select value={editState.virtualEntity || undefined} onValueChange={handleVirtualEntityChange} disabled={!!editState.id}>
                          <SelectTrigger aria-label="Virtual entity"><SelectValue placeholder="Select an entity" /></SelectTrigger>
                          <SelectContent>
                            {entityOptions.map(name => <SelectItem key={name} value={name}>{name}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </Field>
                      <Field label="Source table">
                        <Select value={sourceTableKey || undefined} onValueChange={handleSourceTableChange} disabled={!!editState.id}>
                          <SelectTrigger aria-label="Source table" className="font-mono text-xs"><SelectValue placeholder={<span className="font-sans text-sm">Select a table</span>} /></SelectTrigger>
                          <SelectContent>
                            {tableOptions.map(key => <SelectItem key={key} value={key} className="font-mono text-xs">{key}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </Field>
                    </div>
                  </section>

                  <section>
                    <SectionTitle
                      title="Field mapping"
                      hint={editState.fieldMaps.length === 0 ? 'No field mapping is set, so every source column is read under its own name. Add fields only where a column must be renamed or transformed.' : `${mappedCount} of ${editState.fieldMaps.length} fields mapped. Each source column fills one entity field.`}
                      action={
                        <Button variant="ghost" size="sm" onClick={handleAutoMatch} disabled={sourceColumns.length === 0} title="Fill empty source fields where the names match">
                          <Icon name="bolt" /> Auto-match
                        </Button>
                      }
                    />
                    <div className="scroll-thin overflow-x-auto rounded-xl border border-border bg-card shadow-xs">
                      <div className="min-w-[620px]">
                        <div className="grid grid-cols-[minmax(0,1fr)_20px_minmax(0,1fr)_150px_32px] items-center gap-2 border-b border-border bg-surface-2/60 px-3 py-2 text-xs font-medium text-muted-foreground">
                          <span>Source field</span>
                          <span />
                          <span>Entity field</span>
                          <span>Transform</span>
                          <span />
                        </div>
                        {editState.fieldMaps.map((fm, idx) => (
                          <div key={idx} className="grid grid-cols-[minmax(0,1fr)_20px_minmax(0,1fr)_150px_32px] items-center gap-2 border-b border-border px-3 py-1.5">
                            <FieldSelect
                              label={`Source field, row ${idx + 1}`}
                              value={fm.sourceField}
                              onChange={v => updateFieldMap(idx, 'sourceField', v)}
                              options={sourceOptions}
                              placeholder="Source column"
                            />
                            <Icon name="arrow-right" className={cn('h-3.5 w-3.5 justify-self-center', fm.sourceField && fm.targetField ? 'text-primary dark:text-brand-hi' : 'text-subtle-foreground')} />
                            <FieldSelect
                              label={`Entity field, row ${idx + 1}`}
                              value={fm.targetField}
                              onChange={v => updateFieldMap(idx, 'targetField', v)}
                              options={targetOptions}
                              placeholder="Entity field"
                            />
                            <Select value={fm.transform || 'none'} onValueChange={v => updateFieldMap(idx, 'transform', v === 'none' ? '' : v)}>
                              <SelectTrigger aria-label={`Transform, row ${idx + 1}`} className="h-8 px-2.5 text-xs"><SelectValue /></SelectTrigger>
                              <SelectContent>
                                {TRANSFORM_OPTIONS.map(t => <SelectItem key={t} value={t}>{TRANSFORM_LABEL[t] || t}</SelectItem>)}
                              </SelectContent>
                            </Select>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => removeFieldMap(idx)}
                              disabled={editState.fieldMaps.length <= 1}
                              aria-label={`Remove row ${idx + 1}`}
                              className="hover:bg-destructive/10 hover:text-destructive"
                            >
                              <Icon name="trash" className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        ))}
                        <button
                          type="button"
                          onClick={addFieldMap}
                          className="flex w-full items-center gap-2 px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                        >
                          <Icon name="plus" className="h-3.5 w-3.5" /> Add field
                        </button>
                      </div>
                    </div>
                  </section>

                  <section>
                    <SectionTitle title="Logic" hint="Optional SQL applied when the rule runs." />
                    <div className="max-w-3xl space-y-4">
                      <Field label="Business logic (SQL)" hint="An expression evaluated per row, for example to derive a status.">
                        <Textarea
                          value={editState.businessLogic}
                          onChange={e => updateField('businessLogic', e.target.value)}
                          rows={4}
                          spellCheck={false}
                          className="resize-y font-mono text-xs"
                          placeholder="CASE WHEN status = 'A' THEN 'Active' ELSE 'Inactive' END"
                        />
                      </Field>
                      <Field label="Row filter (WHERE clause)" hint="Only rows that match are read from the source table.">
                        <Textarea
                          value={editState.filterExpression}
                          onChange={e => updateField('filterExpression', e.target.value)}
                          rows={3}
                          spellCheck={false}
                          className="resize-y font-mono text-xs"
                          placeholder="active = true AND deleted_at IS NULL"
                        />
                      </Field>
                    </div>
                  </section>
                </div>

                {/* Aside: preview + summary */}
                <aside className="min-w-0 space-y-7 border-t border-border px-4 py-6 sm:px-6 xl:border-l xl:border-t-0 xl:px-5">
                  <section>
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <h3 className="text-md font-medium text-foreground">Preview</h3>
                      <Button variant="outline" size="sm" onClick={handlePreview} disabled={!editState.virtualEntity || previewing}>
                        <Icon name={previewing ? 'spinner' : 'eye'} className={previewing ? 'animate-spin' : undefined} /> Preview
                      </Button>
                    </div>
                    {previewing ? (
                      <div className="space-y-2" aria-busy="true">
                        {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-7 w-full" />)}
                      </div>
                    ) : !showPreview ? (
                      <p className="text-sm text-muted-foreground">
                        {editState.virtualEntity ? 'Load five sample rows to check the mapping.' : 'Choose a virtual entity to preview its rows.'}
                      </p>
                    ) : previewError ? (
                      <InlineError onRetry={handlePreview}>{previewError}</InlineError>
                    ) : previewRows.length === 0 ? (
                      <p className="text-sm text-muted-foreground">The query returned no rows.</p>
                    ) : (
                      <>
                        {previewMeta && (
                          <p className="mb-2 text-xs text-muted-foreground">
                            <span className="num">{previewMeta.rowCount}</span> rows · <span className="num">{previewMeta.durationMs}</span> ms
                          </p>
                        )}
                        <div className="scroll-thin overflow-x-auto rounded-lg border border-border">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="border-b border-border bg-surface-2/60">
                                {Object.keys(previewRows[0]).map(col => (
                                  <th key={col} className="whitespace-nowrap px-2.5 py-1.5 text-left font-medium text-muted-foreground">
                                    <span className="font-mono">{col}</span>
                                    {fieldLookup.get(col) && <span className="block font-normal text-subtle-foreground">to {fieldLookup.get(col)}</span>}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {previewRows.map((row, i) => (
                                <tr key={i} className="border-b border-border last:border-b-0">
                                  {Object.values(row).map((val, j) => (
                                    <td key={j} className="max-w-[160px] truncate whitespace-nowrap px-2.5 py-1.5 font-mono text-foreground">{String(val ?? '')}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    )}
                  </section>

                  <section>
                    <h3 className="mb-1 text-md font-medium text-foreground">Summary</h3>
                    <KeyValues
                      items={[
                        { label: 'Source system', value: editState.sourceSystem ? systemName(editState.sourceSystem) : '—' },
                        { label: 'Source table', value: sourceTableKey || '—', mono: !!sourceTableKey },
                        { label: 'Source type', value: editState.sourceType },
                        { label: 'Virtual entity', value: editState.virtualEntity || '—' },
                        { label: 'Fields mapped', value: editState.fieldMaps.length === 0 ? 'All columns, as they are' : <span className="num">{mappedCount} of {editState.fieldMaps.length}</span> },
                        { label: 'Status', value: <StatusPill status={editState.status} /> },
                      ]}
                    />
                  </section>
                </aside>
              </div>
            </div>
          </>
        )}
      </div>

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
