import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Code2, Download, Loader2, RefreshCw, Save, Trash2, Upload, Wrench,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  toolBuilderService,
  type ToolDoc,
  type ToolSummary,
} from '@/services/toolBuilderService';
import ToolList from './ToolList';
import ToolEditor from './ToolEditor';
import ParametersEditor from './ParametersEditor';
import IdentityForm, { type IdentityValues } from './IdentityForm';
import TestRunner from './TestRunner';
import VersionHistory from './VersionHistory';
import { DEFAULT_TOOL_TEMPLATE } from './typings';

interface DraftState {
  isNew: boolean;
  tool_id: string | null;
  identity: IdentityValues;
  parameters: Record<string, unknown>;
  source_code: string;
  baselineUpdatedAt?: string | null;
  changelog: string;
}

const EMPTY_DRAFT: DraftState = {
  isNew: true,
  tool_id: null,
  identity: {
    name: '',
    description: '',
    risk_level: 'read_only',
    requires_approval: false,
    cacheable: false,
    connector_api: null,
    tags: [],
  },
  parameters: { type: 'object', properties: {}, required: [] },
  source_code: DEFAULT_TOOL_TEMPLATE,
  baselineUpdatedAt: null,
  changelog: '',
};

function docToDraft(doc: ToolDoc): DraftState {
  return {
    isNew: false,
    tool_id: doc.tool_id,
    identity: {
      name: doc.name,
      description: doc.description || '',
      risk_level: doc.risk_level,
      requires_approval: !!doc.requires_approval,
      cacheable: !!doc.cacheable,
      connector_api: doc.connector_api ?? null,
      tags: [...(doc.tags || [])],
    },
    parameters: doc.parameters || { type: 'object', properties: {}, required: [] },
    source_code: doc.source_code || '',
    baselineUpdatedAt: doc.updatedAt ?? null,
    changelog: '',
  };
}

/**
 * Reusable Tool Builder component (no Layout wrapper). Used by the
 * Reasoning page's "Tool Builder" tab. Owns its own height; expects to
 * be mounted inside a `flex-1` / `h-full` container.
 */
export default function ToolBuilder() {
  const [tools, setTools] = useState<ToolSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftState>(EMPTY_DRAFT);
  const [savedSnapshot, setSavedSnapshot] = useState<string>(JSON.stringify(EMPTY_DRAFT));
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState('identity');

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const r = await toolBuilderService.list();
      setTools(r);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadList(); }, [loadList]);

  const loadTool = useCallback(async (toolId: string) => {
    setError(null);
    try {
      const doc = await toolBuilderService.get(toolId);
      const d = docToDraft(doc);
      setDraft(d);
      setSavedSnapshot(JSON.stringify(d));
      setTab('identity');
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  const handleNew = () => {
    setDraft(EMPTY_DRAFT);
    setSavedSnapshot(JSON.stringify(EMPTY_DRAFT));
    setTab('identity');
  };

  const dirty = useMemo(
    () => JSON.stringify(draft) !== savedSnapshot,
    [draft, savedSnapshot],
  );

  const handleSave = async () => {
    setError(null);
    setSaving(true);
    try {
      if (draft.isNew) {
        const created = await toolBuilderService.create({
          name: draft.identity.name,
          description: draft.identity.description,
          parameters: draft.parameters,
          risk_level: draft.identity.risk_level,
          requires_approval: draft.identity.requires_approval,
          cacheable: draft.identity.cacheable,
          connector_api: draft.identity.connector_api,
          tags: draft.identity.tags,
          source_code: draft.source_code,
        });
        const d = docToDraft(created);
        setDraft(d);
        setSavedSnapshot(JSON.stringify(d));
      } else if (draft.tool_id) {
        const updated = await toolBuilderService.update(draft.tool_id, {
          description: draft.identity.description,
          parameters: draft.parameters,
          risk_level: draft.identity.risk_level,
          requires_approval: draft.identity.requires_approval,
          cacheable: draft.identity.cacheable,
          connector_api: draft.identity.connector_api,
          tags: draft.identity.tags,
          source_code: draft.source_code,
          changelog: draft.changelog || undefined,
          if_unchanged_updated_at: draft.baselineUpdatedAt ?? undefined,
        });
        const d = docToDraft(updated);
        setDraft(d);
        setSavedSnapshot(JSON.stringify(d));
      }
      loadList();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!draft.tool_id) return;
    if (!confirm(`Delete tool ${draft.identity.name}?`)) return;
    try {
      await toolBuilderService.remove(draft.tool_id);
      handleNew();
      loadList();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  };

  const handleExport = async () => {
    const r = await toolBuilderService.exportBundle();
    const blob = new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `react-tools-bundle-${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const handleImport = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        const tools = Array.isArray(data?.tools) ? data.tools : [];
        const r = await toolBuilderService.importBundle({ tools, mode: 'merge' });
        alert(`Import: imported=${r.imported} updated=${r.updated} skipped=${r.skipped} errors=${r.errors.length}`);
        loadList();
      } catch (e: any) {
        setError(e?.message || String(e));
      }
    };
    input.click();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border px-6 py-3 flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <Wrench className="h-5 w-5 text-blue-300" />
            ReAct Tool Builder
          </h1>
          <p className="text-xs text-muted-foreground">
            Author async Python tools that query the Virtual Data Layer and call Connector APIs. Persisted in DynamoDB; usable by the Copilot agent and as journey steps.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleImport}>
            <Upload className="h-3.5 w-3.5 mr-1" /> Import
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-3.5 w-3.5 mr-1" /> Export
          </Button>
        </div>
      </div>

      {error && (
        <div className="mx-6 mt-3 text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          {error}
        </div>
      )}

      <div className="flex-1 grid grid-cols-[260px_1fr] overflow-hidden">
        <div className="border-r border-border overflow-hidden">
          <ToolList
            tools={tools}
            loading={loading}
            selectedId={draft.tool_id}
            onSelect={loadTool}
            onNew={handleNew}
            onRefresh={loadList}
          />
        </div>

        <div className="flex flex-col overflow-hidden">
          <div className="px-6 py-2 border-b border-border flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-2 text-sm">
              <Code2 className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono">{draft.identity.name || '(unsaved)'}</span>
              {dirty && <span className="text-amber-300 text-[11px]">| unsaved changes</span>}
            </div>
            <div className="flex items-center gap-2">
              {!draft.isNew && draft.tool_id && (
                <Button variant="outline" size="sm" onClick={handleDelete}>
                  <Trash2 className="h-3.5 w-3.5 mr-1" /> Delete
                </Button>
              )}
              <Button size="sm" onClick={handleSave} disabled={saving || !draft.identity.name || !draft.source_code}>
                {saving
                  ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                  : <Save className="h-3.5 w-3.5 mr-1" />}
                {draft.isNew ? 'Create' : 'Save'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => draft.tool_id && loadTool(draft.tool_id)}>
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <div className="flex-1 grid grid-rows-[1fr_auto] overflow-hidden">
            <div className="p-4 overflow-auto">
              <ToolEditor
                value={draft.source_code}
                onChange={(v) => setDraft({ ...draft, source_code: v })}
                height="55vh"
              />
            </div>

            <div className="border-t border-border bg-card overflow-hidden">
              <Tabs value={tab} onValueChange={setTab} className="flex flex-col h-72">
                <TabsList className="bg-transparent gap-1 h-auto p-2 border-b border-border/40">
                  {[
                    { value: 'identity', label: 'Identity' },
                    { value: 'parameters', label: 'Parameters' },
                    { value: 'test', label: 'Test' },
                    { value: 'history', label: 'History' },
                  ].map((t) => (
                    <TabsTrigger
                      key={t.value}
                      value={t.value}
                      className="data-[state=active]:bg-blue-600/20 data-[state=active]:text-blue-300 text-xs px-3 py-1"
                    >
                      {t.label}
                    </TabsTrigger>
                  ))}
                </TabsList>
                <div className="flex-1 overflow-auto p-3">
                  <TabsContent value="identity" className="mt-0">
                    <IdentityForm
                      values={draft.identity}
                      onChange={(v) => setDraft({ ...draft, identity: v })}
                      isNew={draft.isNew}
                    />
                  </TabsContent>
                  <TabsContent value="parameters" className="mt-0">
                    <ParametersEditor
                      schema={draft.parameters}
                      onChange={(v) => setDraft({ ...draft, parameters: v })}
                    />
                  </TabsContent>
                  <TabsContent value="test" className="mt-0">
                    <TestRunner
                      toolId={draft.tool_id}
                      parameters={draft.parameters}
                      unsaved={dirty}
                    />
                  </TabsContent>
                  <TabsContent value="history" className="mt-0">
                    <VersionHistory
                      toolId={draft.tool_id}
                      onRestored={() => draft.tool_id && loadTool(draft.tool_id)}
                    />
                  </TabsContent>
                </div>
              </Tabs>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
