/**
 * Automation Registry panel (Workspace, Phase 5.3).
 *
 * Renders AUTOMATION# rows from `/api/v1/automation/registry` in a
 * searchable table with a YAML preview drawer. Provides basic upsert +
 * delete controls so playbooks can be authored without a filesystem
 * hop.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Loader2,
  RefreshCw,
  Search,
  X,
  Save,
  Trash2,
  Plus,
} from 'lucide-react';
import {
  automationRegistryService,
  AutomationRow,
} from '@/services/automationRegistryService';

function matches(row: AutomationRow, q: string): boolean {
  if (!q) return true;
  const n = q.toLowerCase();
  return (
    (row.useCaseId || '').toLowerCase().includes(n)
    || (row.solution || '').toLowerCase().includes(n)
    || (row.sourceFile || '').toLowerCase().includes(n)
    || (row.yamlText || '').toLowerCase().includes(n)
  );
}

export function AutomationRegistryPanel() {
  const [rows, setRows] = useState<AutomationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<AutomationRow | null>(null);
  const [editorText, setEditorText] = useState('');
  const [savingId, setSavingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await automationRegistryService.list();
      setRows(r.items || []);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => rows.filter((r) => matches(r, search)), [rows, search]);

  const openRow = async (row: AutomationRow) => {
    setSelected(row);
    if (row.yamlText) {
      setEditorText(row.yamlText);
    } else {
      try {
        const full = await automationRegistryService.get(row.useCaseId);
        setEditorText(full.yamlText || '');
      } catch {
        setEditorText('');
      }
    }
  };

  const closeDrawer = () => {
    setSelected(null);
    setEditorText('');
    setCreating(false);
  };

  const openCreate = () => {
    setCreating(true);
    setSelected({ useCaseId: '', solution: 'misc', sourceFile: '', yamlText: '' });
    setEditorText('');
  };

  const saveSelected = async () => {
    if (!selected) return;
    if (!selected.useCaseId || !selected.solution) {
      setError('useCaseId and solution are required');
      return;
    }
    setSavingId(selected.useCaseId);
    setError(null);
    try {
      await automationRegistryService.upsert({
        use_case_id: selected.useCaseId,
        solution: selected.solution,
        yaml_text: editorText,
        source_file: selected.sourceFile || `${selected.useCaseId}.yaml`,
      });
      await load();
      closeDrawer();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setSavingId(null);
    }
  };

  const deleteSelected = async () => {
    if (!selected || !selected.useCaseId) return;
    if (!confirm(`Delete playbook '${selected.useCaseId}'?`)) return;
    setSavingId(selected.useCaseId);
    try {
      await automationRegistryService.remove(selected.useCaseId);
      await load();
      closeDrawer();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Automation Registry</h2>
          <p className="text-xs text-muted-foreground mt-1">
            Playbook YAML definitions stored in DynamoDB (AUTOMATION#). Consumed by the automation indexer.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
            <Input
              className="pl-7 h-8 w-64 text-xs"
              placeholder="Search useCase / solution / yaml..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button size="sm" variant="outline" onClick={load} disabled={loading}>
            {loading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <RefreshCw className="h-3 w-3 mr-1" />}
            Refresh
          </Button>
          <Button size="sm" onClick={openCreate}>
            <Plus className="h-3 w-3 mr-1" /> New
          </Button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded p-2">
          {error}
        </div>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            Playbooks <Badge variant="outline" className="ml-2 text-[10px]">{filtered.length} / {rows.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-6 justify-center">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading...
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-sm text-muted-foreground italic py-6 text-center">
              {rows.length === 0 ? 'No AUTOMATION# rows in DDB yet.' : `No matches for "${search}".`}
            </div>
          ) : (
            <div className="divide-y">
              {filtered.map((row) => (
                <button
                  key={row.useCaseId}
                  onClick={() => openRow(row)}
                  className="w-full grid grid-cols-12 gap-2 py-2 px-1 items-center text-left hover:bg-muted/40 transition-colors"
                >
                  <div className="col-span-4 font-mono text-xs truncate">{row.useCaseId}</div>
                  <div className="col-span-3 text-xs">
                    <Badge variant="outline" className="text-[10px]">{row.solution}</Badge>
                  </div>
                  <div className="col-span-3 text-[10px] text-muted-foreground font-mono truncate">{row.sourceFile}</div>
                  <div className="col-span-2 text-[10px] text-muted-foreground text-right">
                    {row.sizeBytes ? `${(row.sizeBytes / 1024).toFixed(1)} KB` : ''}
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {selected && (
        <div
          className="fixed inset-0 z-40 bg-black/60 flex items-center justify-center p-4"
          onClick={closeDrawer}
        >
          <div
            className="bg-card border rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <div className="flex flex-col gap-1 min-w-0 mr-2">
                <div className="flex items-center gap-2">
                  <Input
                    className="w-56 h-7 text-xs font-mono"
                    placeholder="useCaseId"
                    value={selected.useCaseId}
                    onChange={(e) => setSelected({ ...selected, useCaseId: e.target.value })}
                    disabled={!creating && !!selected.useCaseId}
                  />
                  <Input
                    className="w-40 h-7 text-xs"
                    placeholder="solution"
                    value={selected.solution}
                    onChange={(e) => setSelected({ ...selected, solution: e.target.value })}
                  />
                </div>
                <div className="text-[10px] text-muted-foreground">{selected.sourceFile}</div>
              </div>
              <div className="flex items-center gap-2">
                {!creating && selected.useCaseId && (
                  <Button size="sm" variant="ghost" onClick={deleteSelected} disabled={savingId === selected.useCaseId}>
                    <Trash2 className="h-3 w-3 mr-1" /> Delete
                  </Button>
                )}
                <Button size="sm" onClick={saveSelected} disabled={savingId === selected.useCaseId}>
                  {savingId === selected.useCaseId ? (
                    <Loader2 className="h-3 w-3 animate-spin mr-1" />
                  ) : (
                    <Save className="h-3 w-3 mr-1" />
                  )}
                  Save
                </Button>
                <Button size="sm" variant="ghost" onClick={closeDrawer}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="flex-1 min-h-0 overflow-auto p-4">
              <textarea
                className="w-full min-h-[400px] text-[11px] font-mono bg-muted/30 border rounded p-3"
                value={editorText}
                onChange={(e) => setEditorText(e.target.value)}
                placeholder="# use_case_id: ...\n# solution: ...\n# stages: [...]\n"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
