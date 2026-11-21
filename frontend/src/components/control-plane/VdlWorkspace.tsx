/**
 * Data Plane → VDL workspace (catalog entities + composition editor + lineage).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
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
import type { ForeignTableInfo } from '@/types/fdwTypes';

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

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.get<SchemaEntity[]>('/api/v1/control-plane/entities');
      setEntities(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('VDL workspace: entity catalog load failed', e);
      toast.error('Could not load the VDL entity catalog');
      setEntities([]);
    }
    try {
      setCompositions(await vdlCompositionService.list());
    } catch (e) {
      console.warn('VDL workspace: compositions load failed', e);
      setCompositions([]);
    } finally {
      setLoading(false);
    }
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

  const selectEntity = async (entity: SchemaEntity) => {
    setSelected(entity);
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
    const next: VdlCompositionUpsert = {
      virtualEntity: entity.name,
      name: comp?.name || entity.name,
      status: comp?.status || 'draft',
      strategy: comp?.strategy || 'runtime_sql',
      from: comp?.from?.length ? comp.from : [],
      joins: comp?.joins || [],
      select: comp?.select?.length
        ? comp.select
        : (entity.fields || []).map((f) => ({ targetField: f.name, expr: '' })),
      fieldMaps: comp?.fieldMaps || [],
      filterExpression: comp?.filterExpression || '',
      businessLogic: comp?.businessLogic || '',
    };
  if (!next.from.length) {
      next.from = [];
    }
    setEdit(next);
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
    <div className="flex h-full min-h-0 flex-col">
    <ResizablePanelGroup direction="horizontal" className="min-h-0 flex-1 rounded-lg border border-border bg-background">
      <ResizablePanel defaultSize={22} minSize={18} className="flex min-h-0 flex-col border-r border-border">
        <div className="shrink-0 space-y-2 border-b border-border p-3">
          <p className="text-xs font-medium text-muted-foreground">VDL entities</p>
          <SearchInput value={search} onChange={setSearch} placeholder="Search entity or source table" className="w-full" />
        </div>
        <motionList loading={loading} rows={entityRows} onSelect={selectEntity} selected={selected?.name} />
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={48} minSize={36} className="flex min-h-0 flex-col">
        {!selected || !edit ? (
          <p className="m-auto px-6 text-sm text-muted-foreground">Select a VDL entity to edit how it is composed from source tables.</p>
        ) : (
          <>
            <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2">
              {(['schema', 'composition', 'relationships'] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setCenterTab(tab)}
                  className={cn(
                    'rounded-md px-2.5 py-1 text-xs font-medium capitalize',
                    centerTab === tab ? 'bg-accent text-foreground' : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  {tab}
                </button>
              ))}
              <div className="ml-auto flex gap-2">
                <Button size="sm" variant="outline" onClick={handlePreview}>Preview</Button>
                <Button size="sm" onClick={handleSave} disabled={saving}>
                  {saving ? <Icon name="spinner" className="h-4 w-4 animate-spin" /> : 'Save'}
                </Button>
              </div>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              {centerTab === 'schema' && (
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-xs text-muted-foreground"><th className="py-1">Field</th><th>Type</th></tr></thead>
                  <tbody>
                    {(selected.fields || []).map((f) => (
                      <tr key={f.name} className="border-t border-border"><td className="py-1.5 font-mono text-xs">{f.name}</td><td className="text-muted-foreground">{f.dataType || '—'}</td></tr>
                    ))}
                  </tbody>
                </table>
              )}
              {centerTab === 'relationships' && (
                <ul className="space-y-2 text-sm">
                  {(selected.relationships || []).map((r, i) => (
                    <li key={i} className="rounded-md border border-border p-2">
                      <span className="font-medium">{r.type}</span> → {r.targetEntity}
                      {r.description && <p className="mt-1 text-xs text-muted-foreground">{r.description}</p>}
                    </li>
                  ))}
                </ul>
              )}
              {centerTab === 'composition' && (
                <div className="space-y-5">
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

function motionList({
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
  if (loading) return <div className="p-4"><Icon name="spinner" className="h-4 w-4 animate-spin" /></div>;
  if (rows.length === 0) {
    return (
      <p className="p-4 text-xs text-muted-foreground">
        No VDL entities loaded. Check that the API is reachable and try refreshing the page.
      </p>
    );
  }
  return (
    <ul className="min-h-0 flex-1 overflow-y-auto p-2">
      {rows.map(({ e, sourceCount, status }) => (
        <li key={e.name}>
          <button
            type="button"
            onClick={() => onSelect(e)}
            className={cn(
              'mb-1 w-full rounded-md px-2 py-2 text-left text-sm',
              selected === e.name ? 'bg-accent' : 'hover:bg-accent/50',
            )}
          >
            <span className="font-medium">{e.name}</span>
            <span className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
              <span>{e.domain || 'Uncategorized'}</span>
              <span>·</span>
              <span>{sourceCount} sources</span>
              <span className={cn('rounded-md px-1.5 py-0.5 text-[10px] font-medium capitalize', STATUS_STYLES[status] || STATUS_STYLES.inactive)}>{status}</span>
            </span>
          </button>
        </li>
      ))}
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