import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Icon } from '@/components/ds/Icon';
import { InlineError } from '@/components/ds/kit';
import {
  toolBuilderService,
  type ToolDoc,
  type ToolSummary,
} from '@/services/toolBuilderService';
import { cn } from '@/lib/utils';
import { RiskPill } from '@/components/reasoning/toolMeta';
import ToolList from './ToolList';
import ToolEditor from './ToolEditor';
import ParametersEditor from './ParametersEditor';
import IdentityForm, { type IdentityValues } from './IdentityForm';
import TestRunner from './TestRunner';
import VersionHistory from './VersionHistory';
import { DEFAULT_TOOL_TEMPLATE } from './typings';
import { confirmDialog } from '@/components/ds/confirm';
import { toast } from 'sonner';

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

const iconBtn = 'flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50';

/**
 * Reusable Tool Builder component (no Layout wrapper). Used by the
 * Reasoning page's "Tool Builder" tab. Owns its own height; expects to
 * be mounted inside a `flex-1` / `h-full` container.
 *
 * Layout: the list of tools on the left (behind "Browse tools" on small
 * screens), the editor on the right with a fixed header (name, save state,
 * actions) and tabs for code, details, parameters, test and history.
 */
export default function ToolBuilder() {
  const [tools, setTools] = useState<ToolSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftState>(EMPTY_DRAFT);
  const [savedSnapshot, setSavedSnapshot] = useState<string>(JSON.stringify(EMPTY_DRAFT));
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState('code');
  // Local view state: the tool list sheet on small screens.
  const [browseOpen, setBrowseOpen] = useState(false);

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
    setBrowseOpen(false);
    try {
      const doc = await toolBuilderService.get(toolId);
      const d = docToDraft(doc);
      setDraft(d);
      setSavedSnapshot(JSON.stringify(d));
      setTab('code');
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  const handleNew = () => {
    setDraft(EMPTY_DRAFT);
    setSavedSnapshot(JSON.stringify(EMPTY_DRAFT));
    setTab('identity');
    setBrowseOpen(false);
  };

  const dirty = useMemo(
    () => JSON.stringify(draft) !== savedSnapshot,
    [draft, savedSnapshot],
  );

  // Open the first tool once the list arrives, unless a new tool is being written.
  const [autoOpened, setAutoOpened] = useState(false);
  useEffect(() => {
    if (autoOpened || tools.length === 0) return;
    setAutoOpened(true);
    if (draft.isNew && !dirty) loadTool(tools[0].tool_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tools]);

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
    if (!(await confirmDialog({ title: `Delete tool ${draft.identity.name}?`, description: 'This cannot be undone.', destructive: true }))) return;
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
        toast.success('Import finished', { description: `${r.imported} imported, ${r.updated} updated, ${r.skipped} skipped, ${r.errors.length} errors` });
        loadList();
      } catch (e: any) {
        setError(e?.message || String(e));
      }
    };
    input.click();
  };

  const currentVersion = tools.find(t => t.tool_id === draft.tool_id)?.current_version;
  const paramCount = Object.keys((draft.parameters?.properties as Record<string, unknown>) || {}).length;
  // Remount editors that keep their own copy of the draft when another tool loads.
  const draftKey = `${draft.tool_id ?? 'new'}:${draft.baselineUpdatedAt ?? ''}`;

  const listPane = (
    <>
      <div className="flex shrink-0 items-center gap-1 px-3 pt-3">
        <Button variant="outline" size="sm" className="mr-auto" onClick={handleNew}>
          <Icon name="plus" /> New tool
        </Button>
        <button type="button" className={iconBtn} onClick={loadList} disabled={loading} aria-label="Refresh the list" title="Refresh the list">
          <Icon name={loading ? 'spinner' : 'refresh'} className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
        </button>
        <button type="button" className={iconBtn} onClick={handleImport} aria-label="Import tools from a file" title="Import tools from a file">
          <Icon name="upload" className="h-3.5 w-3.5" />
        </button>
        <button type="button" className={iconBtn} onClick={handleExport} aria-label="Export all tools to a file" title="Export all tools to a file">
          <Icon name="download" className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="min-h-0 flex-1">
        <ToolList
          tools={tools}
          loading={loading}
          selectedId={draft.tool_id}
          onSelect={loadTool}
          onNew={handleNew}
          onRefresh={loadList}
        />
      </div>
    </>
  );

  return (
    <div className="grid h-full min-h-0 lg:grid-cols-[300px_minmax(0,1fr)]">
      <aside className="hidden min-h-0 flex-col border-r border-border bg-sidebar/40 lg:flex" aria-label="Tools">
        {listPane}
      </aside>

      <div className="flex min-h-0 min-w-0 flex-col">
        <div className="shrink-0 border-b border-border px-4 py-2 lg:hidden">
          <Button variant="outline" size="sm" className="w-full justify-between" onClick={() => setBrowseOpen(true)}>
            <span className="flex min-w-0 items-center gap-2">
              <Icon name="list" className="h-3.5 w-3.5" />
              <span className="truncate">Browse tools</span>
            </span>
            <span className="flex items-center gap-1.5 font-normal text-muted-foreground">
              <span className="num">{tools.length}</span>
              <Icon name="chevron-down" className="h-3.5 w-3.5" />
            </span>
          </Button>
        </div>

        {/* Editor header: the object, its save state and its actions */}
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-3 px-4 pb-3 pt-4 sm:px-6">
          <div className="min-w-0">
            <h2 className={cn('truncate text-xl font-medium tracking-tight text-foreground', draft.identity.name && 'font-mono')}>
              {draft.identity.name || 'New tool'}
            </h2>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <RiskPill risk={draft.identity.risk_level} />
              {!draft.isNew && currentVersion != null && <span className="num">Version {currentVersion}</span>}
              <span aria-live="polite">{draft.isNew ? 'Not saved yet' : dirty ? 'Unsaved changes' : 'All changes saved'}</span>
            </p>
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            {!draft.isNew && dirty && (
              <Input
                value={draft.changelog}
                onChange={(e) => setDraft({ ...draft, changelog: e.target.value })}
                placeholder="What changed (optional)"
                aria-label="Change note for this version"
                className="h-9 w-56 max-w-full animate-fade-in"
              />
            )}
            {!draft.isNew && draft.tool_id && (
              <>
                <button type="button" className={cn(iconBtn, 'h-9 w-9')} onClick={() => draft.tool_id && loadTool(draft.tool_id)} aria-label="Reload the saved version" title="Reload the saved version">
                  <Icon name="refresh" />
                </button>
                <Button variant="outline" onClick={handleDelete}>
                  <Icon name="trash" /> Delete
                </Button>
              </>
            )}
            <Button onClick={handleSave} disabled={saving || !draft.identity.name || !draft.source_code}>
              {saving && <Icon name="spinner" className="animate-spin" />}
              {draft.isNew ? 'Create tool' : 'Save'}
            </Button>
          </div>
        </div>

        {error && (
          <div className="shrink-0 px-4 pb-3 sm:px-6">
            <InlineError>{error}</InlineError>
          </div>
        )}

        <Tabs value={tab} onValueChange={setTab} className="flex min-h-0 flex-1 flex-col">
          <TabsList variant="line" className="shrink-0 px-4 sm:px-6">
            <TabsTrigger value="code">Code</TabsTrigger>
            <TabsTrigger value="identity">Details</TabsTrigger>
            <TabsTrigger value="parameters">
              Parameters {paramCount > 0 && <span className="num text-xs font-normal text-muted-foreground">{paramCount}</span>}
            </TabsTrigger>
            <TabsTrigger value="test">Test</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          <TabsContent value="code" className="relative mt-0 min-h-0 flex-1">
            <div className="scroll-thin absolute inset-0 overflow-auto p-4 sm:px-6">
              <ToolEditor
                value={draft.source_code}
                onChange={(v) => setDraft({ ...draft, source_code: v })}
                height="100%"
              />
            </div>
          </TabsContent>
          <TabsContent value="identity" className="scroll-thin mt-0 min-h-0 flex-1 overflow-y-auto px-4 pb-24 pt-6 sm:px-6">
            <IdentityForm
              values={draft.identity}
              onChange={(v) => setDraft({ ...draft, identity: v })}
              isNew={draft.isNew}
            />
          </TabsContent>
          <TabsContent value="parameters" className="scroll-thin mt-0 min-h-0 flex-1 overflow-y-auto px-4 pb-24 pt-6 sm:px-6">
            <ParametersEditor
              key={draftKey}
              schema={draft.parameters}
              onChange={(v) => setDraft({ ...draft, parameters: v })}
            />
          </TabsContent>
          <TabsContent value="test" className="scroll-thin mt-0 min-h-0 flex-1 overflow-y-auto px-4 pb-24 pt-6 sm:px-6">
            <TestRunner
              key={draft.tool_id ?? 'new'}
              toolId={draft.tool_id}
              parameters={draft.parameters}
              unsaved={dirty}
            />
          </TabsContent>
          <TabsContent value="history" className="scroll-thin mt-0 min-h-0 flex-1 overflow-y-auto px-4 pb-24 pt-6 sm:px-6">
            <VersionHistory
              toolId={draft.tool_id}
              onRestored={() => draft.tool_id && loadTool(draft.tool_id)}
            />
          </TabsContent>
        </Tabs>
      </div>

      <Sheet open={browseOpen} onOpenChange={setBrowseOpen}>
        <SheetContent side="left" className="flex w-full flex-col gap-0 p-0 sm:max-w-sm">
          <div className="border-b border-border px-4 py-3.5 pr-12">
            <SheetTitle className="text-md font-medium">Tools</SheetTitle>
            <SheetDescription className="sr-only">Choose a tool to edit, or start a new one</SheetDescription>
          </div>
          {listPane}
        </SheetContent>
      </Sheet>
    </div>
  );
}
