/**
 * Data Plane → VDL workspace (catalog entities + composition editor + lineage).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { Icon } from '@/components/ds/Icon';
import { SearchInput } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { apiClient } from '@/services/apiClient';
import { fdwService } from '@/services/fdwService';
import {
  vdlCompositionService,
  type CompositionJoin,
  type CompositionProjection,
  type CompositionSourceRef,
  type VdlComposition,
  type VdlCompositionUpsert,
} from '@/services/vdlCompositionService';
import { virtualQueryService } from '@/services/virtualQueryService';
import type { ColumnInfo, ForeignTableInfo } from '@/types/fdwTypes';

interface SchemaEntity {
  name: string;
  domain: string;
  fields?: { name: string; dataType?: string }[];
  relationships?: { type: string; targetEntity: string; description?: string }[];
}

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-warning/15 text-warning',
  active: 'bg-success/15 text-success',
  inactive: 'bg-muted text-muted-foreground',
};

function tableLabel(s: CompositionSourceRef) {
  return `${s.schema}.${s.table}`;
}

const PREFERRED_SCHEMAS = ['oracle_erp', 'sfdc_itxp2dev', 'sfdc_schema', 'simulator'];

function normName(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function scoreFdwTable(entityName: string, table: ForeignTableInfo): number {
  const e = normName(entityName);
  const t = normName(table.tableName);
  let score = 0;
  if (t === e) score = 100;
  else if (t.endsWith(e) || t.includes(e)) score = 75;
  else if (e.includes(t) && t.length > 3) score = 50;
  const schema = table.schemaName.toLowerCase();
  if (schema.includes('oracle') && entityName.toLowerCase().includes('ap_')) score += 8;
  if ((schema.includes('sfdc') || schema.includes('salesforce')) && !entityName.toLowerCase().startsWith('oracle')) score += 4;
  const pref = PREFERRED_SCHEMAS.findIndex((p) => schema.includes(p.replace(/_/g, '')) || schema === p);
  if (pref >= 0) score += 6 - pref;
  return score;
}

function inferSourceSystem(schema: string): string {
  const s = schema.toLowerCase();
  if (s.includes('oracle')) return 'Oracle';
  if (s.includes('sfdc') || s.includes('salesforce')) return 'Salesforce';
  if (s.includes('sap')) return 'SAP';
  return schema.split('_')[0] || 'FDW';
}

export default function VdlWorkspace() {
  const [entities, setEntities] = useState<SchemaEntity[]>([]);
  const [compositions, setCompositions] = useState<VdlComposition[]>([]);
  const [selected, setSelected] = useState<SchemaEntity | null>(null);
  const [edit, setEdit] = useState<VdlCompositionUpsert | null>(null);
  const [fdwTables, setFdwTables] = useState<ForeignTableInfo[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[]>([]);
  const [centerTab, setCenterTab] = useState<'schema' | 'composition' | 'relationships'>('composition');
  const [quickMapping, setQuickMapping] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    let catalog: SchemaEntity[] = [];
    try {
      const data = await apiClient.get<SchemaEntity[]>('/api/v1/control-plane/entities', {
        requireAuth: false,
      });
      if (Array.isArray(data)) catalog = data;
    } catch (e) {
      console.warn('VDL workspace: entity catalog load failed, trying virtual entity list', e);
    }
    if (catalog.length === 0) {
      try {
        const summaries = await virtualQueryService.listEntities();
        catalog = summaries.map((s) => ({
          name: s.virtual_entity,
          domain: s.active_rules > 0 ? 'Mapped' : 'Unmapped',
        }));
      } catch (e) {
        console.error('VDL workspace: fallback entity list failed', e);
        toast.error('Could not load VDL entities');
      }
    }
    const byName = new Map(catalog.map((e) => [e.name, e]));
    let comps: VdlComposition[] = [];
    try {
      comps = await vdlCompositionService.list();
      for (const c of comps) {
        if (!byName.has(c.virtualEntity)) {
          byName.set(c.virtualEntity, {
            name: c.virtualEntity,
            domain: 'Composed (catalog pending)',
          });
        }
      }
    } catch (e) {
      console.warn('VDL workspace: compositions load failed', e);
    }
    setEntities([...byName.values()].sort((a, b) => a.name.localeCompare(b.name)));
    setCompositions(comps);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    Promise.all([
      fdwService.listTables().catch(() => [] as ForeignTableInfo[]),
      fdwService.listTables(undefined, 'simulator').catch(() => [] as ForeignTableInfo[]),
      fdwService.listTables(undefined, 'oracle').catch(() => [] as ForeignTableInfo[]),
      fdwService.listTables(undefined, 'sap').catch(() => [] as ForeignTableInfo[]),
      fdwService.listTables(undefined, 'external').catch(() => [] as ForeignTableInfo[]),
    ]).then(([a, b, c, d, e]) => {
      const seen = new Set<string>();
      const all: ForeignTableInfo[] = [];
      for (const t of [...a, ...b, ...c, ...d, ...e]) {
        const key = `${t.schemaName}.${t.tableName}`;
        if (!seen.has(key)) { seen.add(key); all.push(t); }
      }
      setFdwTables(all);
    });
  }, [load]);

  const compByEntity = useMemo(() => {
    const m = new Map<string, VdlComposition>();
    for (const c of compositions) m.set(c.virtualEntity, c);
    return m;
  }, [compositions]);

  const entityRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    const catalogByName = new Map<string, SchemaEntity>();
    for (const e of entities) catalogByName.set(e.name, e);
    for (const c of compositions) {
      if (!catalogByName.has(c.virtualEntity)) {
        catalogByName.set(c.virtualEntity, {
          name: c.virtualEntity,
          domain: 'Composed (catalog pending)',
        });
      }
    }
    return [...catalogByName.values()]
      .map((e) => {
        const comp = compByEntity.get(e.name);
        const sourceCount = comp?.from?.length ?? 0;
        const status = comp?.status ?? 'unmapped';
        const tables = (comp?.from || []).map(tableLabel).join(' ');
        return { e, sourceCount, status, tables };
      })
      .filter(({ e, tables }) => {
        if (!q) return true;
        return (
          e.name.toLowerCase().includes(q)
          || (e.domain || '').toLowerCase().includes(q)
          || tables.toLowerCase().includes(q)
        );
      })
      .sort((a, b) => a.e.name.localeCompare(b.e.name));
  }, [entities, compositions, compByEntity, search]);

  const hydrateCatalog = async (
    entity: SchemaEntity,
    comp?: VdlComposition,
  ): Promise<SchemaEntity> => {
    try {
      return await apiClient.get<SchemaEntity>(
        `/api/v1/control-plane/entities/${encodeURIComponent(entity.name)}`,
        { requireAuth: false },
      );
    } catch {
      // Composition-only entity: infer schema from the primary FDW table.
      const primary = comp?.from?.[0];
      if (!primary) return entity;
      try {
        const cols = await fdwService.getColumns(primary.schema, primary.table);
        return {
          ...entity,
          fields: cols.map((c) => ({ name: c.columnName, dataType: c.dataType })),
        };
      } catch {
        return entity;
      }
    }
  };

  const selectEntity = async (entity: SchemaEntity) => {
    setCenterTab('composition');
    setPreviewRows([]);
    let comp = compByEntity.get(entity.name);
    if (!comp) {
      try {
        comp = await vdlCompositionService.get(entity.name);
      } catch {
        comp = undefined;
      }
    }
    const enriched = await hydrateCatalog(entity, comp);
    setSelected(enriched);
    const next: VdlCompositionUpsert = {
      virtualEntity: entity.name,
      name: comp?.name || entity.name,
      status: comp?.status || 'draft',
      strategy: comp?.strategy || 'runtime_sql',
      from: comp?.from?.length ? comp.from : [],
      joins: comp?.joins || [],
      select: comp?.select?.length
        ? comp.select
        : (enriched.fields || []).map((f) => ({ targetField: f.name, expr: '' })),
      fieldMaps: comp?.fieldMaps || [],
      filterExpression: comp?.filterExpression || '',
      businessLogic: comp?.businessLogic || '',
    };
    if (!next.from.length) {
      next.from = [];
    }
    setEdit(next);
  };

  const schemaRows = useMemo(() => {
    if (!selected || !edit) return [];
    const projByField = new Map((edit.select || []).map((p) => [p.targetField, p.expr]));
    const fields = selected.fields?.length
      ? selected.fields
      : (edit.select || []).map((p) => ({ name: p.targetField, dataType: undefined as string | undefined }));
    return fields.map((f) => ({
      name: f.name,
      type: f.dataType || '—',
      sourceExpr: projByField.get(f.name) || '—',
    }));
  }, [selected, edit]);

  const quickMapFromSources = async () => {
    if (!selected || !edit) return;
    setQuickMapping(true);
    try {
      const ranked = fdwTables
        .map((t) => ({ t, score: scoreFdwTable(selected.name, t) }))
        .filter((x) => x.score >= 50)
        .sort((a, b) => b.score - a.score);
      if (ranked.length === 0) {
        toast.error('No matching Oracle/SFDC table', {
          description: 'Pick a source table manually, or run Auto-map on the Mapper tab.',
        });
        return;
      }
      const best = ranked[0].t;
      let columns: ColumnInfo[] = [];
      try {
        columns = await fdwService.getColumns(best.schemaName, best.tableName);
      } catch {
        toast.error('Could not read columns for the matched table');
        return;
      }
      const from: CompositionSourceRef = {
        alias: 'src',
        sourceSystem: inferSourceSystem(best.schemaName),
        schema: best.schemaName,
        table: best.tableName,
      };
      const catalogFields =
        selected.fields?.map((f) => f.name) || (edit.select || []).map((p) => p.targetField);
      const select: CompositionProjection[] =
        catalogFields.length > 0
          ? catalogFields.map((tf) => {
              const col = columns.find(
                (c) =>
                  normName(c.columnName) === normName(tf)
                  || c.columnName.toLowerCase() === tf.toLowerCase(),
              );
              return { targetField: tf, expr: col ? `src."${col.columnName}"` : '' };
            })
          : columns.slice(0, 40).map((c) => ({
              targetField: c.columnName,
              expr: `src."${c.columnName}"`,
            }));
      const next: VdlCompositionUpsert = {
        ...edit,
        from: [from],
        joins: [],
        select,
        status: edit.status === 'inactive' ? 'draft' : edit.status,
      };
      setEdit(next);
      const hydrated = await hydrateCatalog(selected, {
        virtualEntity: selected.name,
        status: next.status,
        strategy: next.strategy || 'runtime_sql',
        from: next.from,
        joins: [],
        select: next.select,
        fieldMaps: [],
        createdAt: '',
        updatedAt: '',
      });
      setSelected(hydrated);
      toast.success(`Linked ${selected.name} → ${best.schemaName}.${best.tableName}`);
    } finally {
      setQuickMapping(false);
    }
  };

  const addSourceTable = (tableKey: string) => {
    if (!edit || !tableKey) return;
    const dot = tableKey.indexOf('.');
    const schema = tableKey.slice(0, dot);
    const table = tableKey.slice(dot + 1);
    const alias = `t${edit.from.length + 1}`;
    const src: CompositionSourceRef = {
      alias,
      sourceSystem: schema === 'external_sources' ? 'External' : schema.split('_')[0],
      schema,
      table,
    };
    setEdit({ ...edit, from: [...edit.from, src] });
  };

  const updateProjection = (idx: number, key: keyof CompositionProjection, val: string) => {
    if (!edit) return;
    const select = [...(edit.select || [])];
    select[idx] = { ...select[idx], [key]: val };
    setEdit({ ...edit, select });
  };

  const updateJoin = (idx: number, key: keyof CompositionJoin, val: string) => {
    if (!edit) return;
    const joins = [...(edit.joins || [])];
    joins[idx] = { ...joins[idx], [key]: val };
    setEdit({ ...edit, joins });
  };

  const addJoin = () => {
    if (!edit || edit.from.length < 2) return;
    setEdit({
      ...edit,
      joins: [...(edit.joins || []), { left: edit.from[0].alias, right: edit.from[1].alias, type: 'left', on: '' }],
    });
  };

  const handleSave = async () => {
    if (!edit || !selected) return;
    setSaving(true);
    try {
      const saved = await vdlCompositionService.upsert(edit.virtualEntity, edit);
      toast.success('Composition saved');
      setCompositions((prev) => {
        const rest = prev.filter((c) => c.virtualEntity !== saved.virtualEntity);
        return [...rest, saved];
      });
    } catch (e) {
      toast.error('Save failed', { description: (e as Error)?.message });
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = async () => {
    if (!selected) return;
    try {
      const res = await virtualQueryService.queryEntity({ virtualEntity: selected.name, limit: 10 });
      setPreviewRows(res.rows || []);
    } catch (e) {
      toast.error('Preview failed', { description: (e as Error)?.message });
      setPreviewRows([]);
    }
  };

  const lineageSources = edit?.from || [];

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
    <ResizablePanelGroup direction="horizontal" className="h-full min-h-0 flex-1 gap-0 px-2 py-2">
      <ResizablePanel defaultSize={26} minSize={16} maxSize={40} className="min-h-0 min-w-0">
        <Card className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border">
          <CardHeader className="shrink-0 space-y-0 px-3 py-3">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-md font-medium">VDL entities</CardTitle>
              <span className="num rounded-md bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">{entityRows.length}</span>
            </div>
            <SearchInput value={search} onChange={setSearch} placeholder="Search entity or source table" className="mt-2.5 sm:w-full" aria-label="Search VDL entities" />
          </CardHeader>
          <CardContent className="min-h-0 flex-1 overflow-y-auto p-0">
            <EntityList loading={loading} rows={entityRows} onSelect={selectEntity} selected={selected?.name} />
          </CardContent>
        </Card>
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={48} minSize={36} className="flex min-h-0 flex-col">
        {!selected || !edit ? (
          <p className="m-auto px-6 text-sm text-muted-foreground">Select a VDL entity to edit how it is composed from source tables.</p>
        ) : (
          <>
            <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2">
              {([
                { id: 'composition' as const, label: 'Mapper' },
                { id: 'schema' as const, label: 'Schema' },
                { id: 'relationships' as const, label: 'Relationships' },
              ]).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setCenterTab(tab.id)}
                  className={cn(
                    'rounded-md px-2.5 py-1 text-xs font-medium',
                    centerTab === tab.id ? 'bg-accent text-foreground' : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  {tab.label}
                </button>
              ))}
              <div className="ml-auto flex flex-wrap justify-end gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={quickMapFromSources}
                  disabled={quickMapping}
                  title="Match this VDL entity to an Oracle or Salesforce FDW table and fill column expressions"
                >
                  {quickMapping ? <Icon name="spinner" className="h-4 w-4 animate-spin" /> : <Icon name="sparkles" className="h-4 w-4" />}
                  Quick map
                </Button>
                <Button size="sm" variant="outline" onClick={handlePreview}>Preview</Button>
                <Button size="sm" onClick={handleSave} disabled={saving}>
                  {saving ? <Icon name="spinner" className="h-4 w-4 animate-spin" /> : 'Save'}
                </Button>
              </div>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              {centerTab === 'schema' && (
                schemaRows.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
                    <p>No schema fields yet for <span className="font-medium text-foreground">{selected.name}</span>.</p>
                    <p className="mt-2 text-xs">
                      Use <span className="font-medium">Quick map</span> on the Mapper tab to bind an Oracle or Salesforce table, or edit projections below.
                    </p>
                  </div>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-muted-foreground">
                        <th className="py-1 pr-2">VDL field</th>
                        <th className="py-1 pr-2">Type</th>
                        <th className="py-1">Source expression</th>
                      </tr>
                    </thead>
                    <tbody>
                      {schemaRows.map((row) => (
                        <tr key={row.name} className="border-t border-border">
                          <td className="py-1.5 pr-2 font-mono text-xs">{row.name}</td>
                          <td className="py-1.5 pr-2 text-muted-foreground">{row.type}</td>
                          <td className="py-1.5 font-mono text-xs text-muted-foreground">{row.sourceExpr}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )
              )}
              {centerTab === 'relationships' && (
                (selected.relationships || []).length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
                    <p>No ontology relationships are defined for this entity in the catalog.</p>
                    <p className="mt-2 text-xs">
                      Lineage on the right shows physical source tables. Cross-entity links come from enterprise-knowledge YAML when the entity is in the canonical catalog.
                    </p>
                  </div>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {(selected.relationships || []).map((r, i) => (
                      <li key={i} className="rounded-md border border-border p-2">
                        <span className="font-medium">{r.type}</span> → {r.targetEntity}
                        {r.description && <p className="mt-1 text-xs text-muted-foreground">{r.description}</p>}
                      </li>
                    ))}
                  </ul>
                )
              )}
              {centerTab === 'composition' && (
                <div className="space-y-5">
                  <p className="text-xs text-muted-foreground">
                    Simple path: one VDL entity ← one Oracle or Salesforce table via <span className="font-medium text-foreground">Quick map</span>, optional SQL join for a second source, then Save and Preview. Bulk rule creation: Mapper tab → Auto-map.
                  </p>
                  <section>
                    <p className="mb-2 text-xs font-medium text-muted-foreground">① Source tables</p>
                    <div className="mb-2 flex flex-wrap gap-1.5">
                      {edit.from.map((s) => (
                        <span key={s.alias} className="rounded-md bg-muted px-2 py-1 text-xs font-mono">{s.alias}: {tableLabel(s)}</span>
                      ))}
                    </div>
                    <select
                      className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
                      defaultValue=""
                      onChange={(e) => { addSourceTable(e.target.value); e.target.value = ''; }}
                    >
                      <option value="">Add source table…</option>
                      {fdwTables.map((t) => (
                        <option key={`${t.schemaName}.${t.tableName}`} value={`${t.schemaName}.${t.tableName}`}>
                          {t.schemaName}.{t.tableName}
                        </option>
                      ))}
                    </select>
                  </section>
                  <section>
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-xs font-medium text-muted-foreground">Joins</p>
                      <Button size="sm" variant="ghost" onClick={addJoin} disabled={edit.from.length < 2}>Add join</Button>
                    </div>
                    {(edit.joins || []).map((j, i) => (
                      <div key={i} className="mb-2 grid grid-cols-4 gap-2">
                        <Input value={j.left} onChange={(e) => updateJoin(i, 'left', e.target.value)} placeholder="left alias" className="h-8 text-xs" />
                        <Input value={j.right} onChange={(e) => updateJoin(i, 'right', e.target.value)} placeholder="right alias" className="h-8 text-xs" />
                        <Input value={j.type} onChange={(e) => updateJoin(i, 'type', e.target.value)} placeholder="inner/left" className="h-8 text-xs" />
                        <Input value={j.on} onChange={(e) => updateJoin(i, 'on', e.target.value)} placeholder="on clause" className="h-8 text-xs font-mono" />
                      </div>
                    ))}
                  </section>
                  <section>
                    <p className="mb-2 text-xs font-medium text-muted-foreground">② Projections (VDL field ← expression)</p>
                    <div className="space-y-1.5">
                      {(edit.select || []).map((p, i) => (
                        <div key={p.targetField} className="grid grid-cols-2 gap-2">
                          <Input value={p.targetField} readOnly className="h-8 text-xs font-mono bg-muted/40" />
                          <Input
                            value={p.expr}
                            onChange={(e) => updateProjection(i, 'expr', e.target.value)}
                            placeholder={edit.from[0] ? `${edit.from[0].alias}.column` : 'expression'}
                            className="h-8 text-xs font-mono"
                          />
                        </div>
                      ))}
                    </div>
                  </section>
                  <section>
                    <p className="mb-2 text-xs font-medium text-muted-foreground">③ Filter (WHERE)</p>
                    <textarea
                      className="min-h-[72px] w-full rounded-md border border-input bg-background p-2 font-mono text-xs"
                      value={edit.filterExpression || ''}
                      onChange={(e) => setEdit({ ...edit, filterExpression: e.target.value })}
                    />
                  </section>
                  <section className="flex gap-2">
                    {(['draft', 'active', 'inactive'] as const).map((st) => (
                      <button
                        key={st}
                        type="button"
                        onClick={() => setEdit({ ...edit, status: st })}
                        className={cn('rounded-md px-2 py-1 text-xs capitalize', edit.status === st ? STATUS_STYLES[st] : 'text-muted-foreground')}
                      >
                        {st}
                      </button>
                    ))}
                  </section>
                </div>
              )}
            </div>
          </>
        )}
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={30} minSize={24} className="flex min-h-0 flex-col border-l border-border p-4">
        <p className="text-xs font-medium text-muted-foreground">Lineage</p>
        {selected && edit ? (
          <div className="mt-3 space-y-3 text-sm">
            <p className="font-medium text-foreground">{selected.name}</p>
            <p className="text-xs text-muted-foreground">Composed from</p>
            <ul className="space-y-1 font-mono text-xs">
              {lineageSources.map((s) => (
                <li key={s.alias} className="rounded bg-muted/50 px-2 py-1">{tableLabel(s)}</li>
              ))}
              {lineageSources.length === 0 && <li className="text-muted-foreground">No sources linked yet</li>}
            </ul>
            <Button size="sm" variant="outline" className="w-full" onClick={async () => {
              try {
                const v = await vdlCompositionService.validate(selected.name);
                if (v.valid) toast.success('SQL valid');
                else toast.error(v.errors.join('; '));
              } catch (e) {
                toast.error((e as Error).message);
              }
            }}>
              Validate SQL
            </Button>
            {previewRows.length > 0 && (
              <motionPreview rows={previewRows} />
            )}
          </div>
        ) : (
          <p className="mt-4 text-xs text-muted-foreground">Sources fan in to the VDL entity here.</p>
        )}
      </ResizablePanel>
    </ResizablePanelGroup>
    </div>
  );
}

function EntityList({
  loading,
  rows,
  onSelect,
  selected,
}: {
  loading: boolean;
  rows: { e: SchemaEntity; sourceCount: number; status: string }[];
  onSelect: (e: SchemaEntity) => void;
  selected?: string;
}) {
  if (loading) {
    return (
      <div className="flex justify-center p-6">
        <Icon name="spinner" className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <p className="px-4 py-6 text-center text-xs text-muted-foreground">
        No VDL entities loaded. Open the Mapper tab for rule-based mapping, or refresh after the API is reachable.
      </p>
    );
  }
  return (
    <ul className="divide-y divide-border px-2 pb-2">
      {rows.map(({ e, sourceCount, status }) => {
        const on = selected === e.name;
        return (
          <li key={e.name}>
            <button
              type="button"
              onClick={() => onSelect(e)}
              aria-pressed={on}
              className={cn(
                'w-full border-l-2 px-2 py-2.5 text-left transition-colors',
                on ? 'border-brand bg-brand/10' : 'border-transparent hover:bg-muted/50',
              )}
            >
              <div className="truncate text-sm font-medium text-foreground">{e.name}</div>
              <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                <span className="truncate">{e.domain || 'Uncategorized'}</span>
                <span aria-hidden="true">·</span>
                <span className="num">{sourceCount} sources</span>
                <span className={cn('rounded-md px-1.5 py-0.5 text-[10px] font-medium capitalize', STATUS_STYLES[status] || STATUS_STYLES.inactive)}>
                  {status}
                </span>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function motionPreview({ rows }: { rows: Record<string, unknown>[] }) {
  const keys = Object.keys(rows[0] || {});
  return (
    <div className="mt-2 overflow-x-auto rounded border border-border text-xs">
      <table className="w-full">
        <thead><tr>{keys.map((k) => <th key={k} className="border-b px-2 py-1 text-left font-mono">{k}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{keys.map((k) => <td key={k} className="border-t px-2 py-1 font-mono">{String(r[k] ?? '')}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}