import { Fragment, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { Chips, CodeBlock, InlineError, KeyValues, SearchInput, StatusPill, SubHeading, TableShell, Timeline } from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { confirmDialog } from '@/components/ds/confirm';
import { cn } from '@/lib/utils';
import { ontoDataApi, type OntoFile } from '@/services/ontoDataApi';
import {
  parsePolicyDoc, parseWorkflowDoc, parseIntegrationDoc, prettyFileName, isApprovalStep,
  type PolicyDoc, type PolicySection, type WorkflowDoc, type IntegrationDoc, type DependencyDoc,
} from './knowledgeParsers';

// ============================================================================
// Shared KnowledgeEditor: one master-detail pattern for policies, workflows
// and integration rules. List on the left, the selected item on the right,
// read as a person reads it; the form builders open from "Edit".
// ============================================================================

interface Template { name: string; filename: string; content: string }
interface KnowledgeEditorProps {
  category: string;
  fileExtension: string;
  templates: Template[];
  renderPreview?: (content: string) => React.ReactNode;
  formBuilder?: (props: { content: string; onChange: (c: string) => void }) => React.ReactNode;
  title: string;
  description: string;
}

type Kind = 'policy' | 'workflow' | 'integration';
type DetailTab = 'overview' | 'content' | 'definition';
type ListFilter = 'all' | 'recent';

const KIND_OF: Record<string, Kind> = { policies: 'policy', workflows: 'workflow', integrations: 'integration' };

const KIND_COPY: Record<Kind, { noun: string; plural: string; contentTab: string; emptyIcon: 'shield-check' | 'workflow' | 'plug' }> = {
  policy: { noun: 'Policy', plural: 'policies', contentTab: 'Rules', emptyIcon: 'shield-check' },
  workflow: { noun: 'Workflow', plural: 'workflows', contentTab: 'Steps', emptyIcon: 'workflow' },
  integration: { noun: 'Integration rule', plural: 'integration rules', contentTab: 'Mappings', emptyIcon: 'plug' },
};

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

const formatSize = (bytes?: number): string => {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDay = (iso?: string): string => {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
};

/** Systems named in a file name such as "sf-oracle-customer-sync.yaml". */
function systemsInFilename(filename: string): string[] {
  const MAP: Record<string, string> = { sf: 'Salesforce', salesforce: 'Salesforce', oracle: 'Oracle', sap: 'SAP', gdrive: 'Google Drive', drive: 'Google Drive', social: 'Social Listening', upload: 'File Uploads' };
  const found: string[] = [];
  for (const token of filename.replace(/\.[^.]+$/, '').toLowerCase().split(/[-_]+/)) {
    const s = MAP[token];
    if (s && !found.includes(s)) found.push(s);
  }
  return found.slice(0, 2);
}

/** One-line summary of a template for the picker. */
function templateSummary(kind: Kind, content: string): { line: string; systems: string[] } {
  if (kind === 'policy') {
    const d = parsePolicyDoc(content);
    return { line: [d.riskLevel && `${d.riskLevel} risk`, d.owner, `${d.sections.length} sections`].filter(Boolean).join(' · '), systems: d.systems };
  }
  if (kind === 'workflow') {
    const d = parseWorkflowDoc(content);
    const systems = [...new Set(d.steps.map(s => s.system).filter(Boolean))];
    return { line: [`${d.steps.length} steps`, d.trigger.condition].filter(Boolean).join(' · '), systems };
  }
  const d = parseIntegrationDoc(content);
  return { line: [d.frequency, `${d.mappings.reduce((n, m) => n + m.fields.length, 0)} fields`].filter(Boolean).join(' · '), systems: [d.sourceSystem, d.targetSystem].filter(Boolean) };
}

export function KnowledgeEditor({ category, fileExtension, templates, renderPreview, formBuilder, title, description }: KnowledgeEditorProps) {
  const [files, setFiles] = useState<OntoFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<OntoFile | null>(null);
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const [showTemplates, setShowTemplates] = useState(false);
  const [loadingContent, setLoadingContent] = useState(false);
  const [editorMode, setEditorMode] = useState<'form' | 'raw'>(formBuilder ? 'form' : 'raw');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Presentation only.
  const [listError, setListError] = useState<string | null>(null);
  const [contentError, setContentError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<ListFilter>('all');
  const [detailTab, setDetailTab] = useState<DetailTab>('overview');
  const [editing, setEditing] = useState(false);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [busy, setBusy] = useState<'duplicate' | 'delete' | null>(null);
  // The form builders rewrite the text when they open. Their first output is
  // the baseline, so "Unsaved changes" only shows after a real edit.
  const formBaseline = useRef<string | null>(null);
  const pendingSelect = useRef<string | null>(null);

  const kind: Kind = KIND_OF[category] || 'policy';
  const copy = KIND_COPY[kind];

  const loadFiles = useCallback(async () => {
    setLoading(true);
    setListError(null);
    try {
      const data = await ontoDataApi.listFiles(category);
      setFiles(data.files || []);
    } catch (e: any) {
      setFiles([]);
      setListError(e?.message || `The ${KIND_COPY[KIND_OF[category] || 'policy'].plural} could not be loaded.`);
    }
    finally { setLoading(false); }
  }, [category]);

  useEffect(() => { loadFiles(); }, [loadFiles]);

  const loadContent = async (file: OntoFile) => {
    setSelectedFile(file);
    setLoadingContent(true);
    setContentError(null);
    setEditing(false);
    setDetailTab('overview');
    formBaseline.current = null;
    try {
      const config = await (async () => { try { const r = await fetch('/config.json'); const c = await r.json(); return c?.api?.baseUrl || ''; } catch { return ''; } })();
      const res = await fetch(`${config}/api/v1/control-plane/onto-data/files/${file.key}`, { credentials: 'include' });
      if (res.ok) {
        const text = await res.text();
        setContent(text);
        setOriginalContent(text);
      } else {
        setContentError(`This file could not be opened (error ${res.status}).`);
      }
    } catch (e) {
      console.error('Load failed:', e);
      setContentError('This file could not be opened.');
    }
    finally { setLoadingContent(false); }
  };

  const handleSave = async () => {
    if (!selectedFile && !content) return;
    setSaving(true);
    setMessage(null);
    try {
      const filename = selectedFile?.filename || `new-${Date.now()}${fileExtension}`;
      const blob = new Blob([content], { type: 'text/plain' });
      const file = new File([blob], filename, { type: 'text/plain' });
      await ontoDataApi.uploadFile(category, file);
      setOriginalContent(content);
      setMessage({ type: 'success', text: 'Saved successfully' });
      toast.success(`${copy.noun} saved`, { description: filename });
      setEditing(false);
      formBaseline.current = null;
      if (!selectedFile) pendingSelect.current = filename;
      await loadFiles();
      setTimeout(() => setMessage(null), 3000);
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message || 'Save failed' });
      toast.error('Save failed', { description: e.message });
    }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!selectedFile) return;
    try {
      await ontoDataApi.deleteFile(selectedFile.key);
      toast.success(`${copy.noun} deleted`, { description: selectedFile.filename });
      setSelectedFile(null);
      setContent('');
      setOriginalContent('');
      setEditing(false);
      await loadFiles();
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message || 'Delete failed' });
      toast.error('Delete failed', { description: e.message });
    }
  };

  const handleNewFromTemplate = (template: Template) => {
    setSelectedFile(null);
    setContent(template.content);
    setOriginalContent('');
    setShowTemplates(false);
    setEditing(false);
    setContentError(null);
    setDetailTab('overview');
    formBaseline.current = null;
    const blob = new Blob([template.content], { type: 'text/plain' });
    const file = new File([blob], template.filename, { type: 'text/plain' });
    setSaving(true);
    pendingSelect.current = template.filename;
    ontoDataApi.uploadFile(category, file).then(() => {
      loadFiles();
      setMessage({ type: 'success', text: `Created ${template.filename}` });
      toast.success(`${copy.noun} created from template`, { description: template.filename });
      setTimeout(() => setMessage(null), 3000);
    }).catch((e: any) => {
      pendingSelect.current = null;
      toast.error('The template could not be saved', { description: e?.message });
    }).finally(() => setSaving(false));
  };

  const isDirty = content !== originalContent;
  // In form mode compare with what the form first produced, not the stored text.
  const hasChanges = editing && editorMode === 'form' && formBuilder
    ? formBaseline.current != null && content !== formBaseline.current
    : isDirty;

  /* ------------------------------------------------------ local behaviour */

  // After a create or duplicate, open the new file once the list has it.
  useEffect(() => {
    if (loading || !pendingSelect.current) return;
    const match = files.find(f => f.filename === pendingSelect.current);
    pendingSelect.current = null;
    if (match) loadContent(match);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files, loading]);

  // The detail is never blank: open the first item after load.
  useEffect(() => {
    if (loading || saving || selectedFile || content || files.length === 0 || pendingSelect.current) return;
    loadContent(files[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files, loading, saving, selectedFile, content]);

  const confirmDiscard = async (): Promise<boolean> => {
    if (!editing || !hasChanges) return true;
    return confirmDialog({ title: 'Discard unsaved changes?', description: 'Your edits to this item have not been saved.', confirmLabel: 'Discard', destructive: true });
  };

  const selectFile = async (file: OntoFile) => {
    setBrowseOpen(false);
    if (file.key === selectedFile?.key && !contentError) return;
    if (!(await confirmDiscard())) return;
    loadContent(file);
  };

  const startEdit = () => {
    formBaseline.current = null;
    setEditorMode(formBuilder ? 'form' : 'raw');
    setEditing(true);
  };

  const cancelEdit = async () => {
    if (!(await confirmDiscard())) return;
    if (selectedFile) setContent(originalContent);
    formBaseline.current = null;
    setEditing(false);
  };

  const switchMode = (mode: 'form' | 'raw') => {
    formBaseline.current = null;
    setEditorMode(mode);
  };

  const onFormChange = useCallback((c: string) => {
    if (formBaseline.current == null) formBaseline.current = c;
    setContent(c);
  }, []);

  const requestDelete = async () => {
    if (!selectedFile) return;
    const ok = await confirmDialog({
      title: `Delete ${selectedFile.filename}?`,
      description: `The ${copy.noun.toLowerCase()} is removed from the knowledge store. The agent stops using it after the next index build.`,
      confirmLabel: 'Delete',
      destructive: true,
    });
    if (!ok) return;
    setBusy('delete');
    await handleDelete();
    setBusy(null);
  };

  const handleDuplicate = async () => {
    if (!content) return;
    const source = selectedFile?.filename || `new${fileExtension}`;
    const dot = source.lastIndexOf('.');
    const base = dot > 0 ? source.slice(0, dot) : source;
    const ext = dot > 0 ? source.slice(dot) : fileExtension;
    let name = `${base}-copy${ext}`;
    for (let n = 2; files.some(f => f.filename === name); n++) name = `${base}-copy-${n}${ext}`;
    setBusy('duplicate');
    try {
      await ontoDataApi.uploadFile(category, new File([new Blob([originalContent || content], { type: 'text/plain' })], name, { type: 'text/plain' }));
      toast.success(`${copy.noun} duplicated`, { description: name });
      pendingSelect.current = name;
      await loadFiles();
    } catch (e: any) {
      toast.error('Duplicate failed', { description: e?.message });
    } finally {
      setBusy(null);
    }
  };

  /* --------------------------------------------------------------- derived */

  const recentCount = useMemo(() => files.filter(f => f.last_modified && Date.now() - new Date(f.last_modified).getTime() < WEEK_MS).length, [files]);

  const visibleFiles = useMemo(() => {
    const q = search.trim().toLowerCase();
    return files.filter(f => {
      if (filter === 'recent' && !(f.last_modified && Date.now() - new Date(f.last_modified).getTime() < WEEK_MS)) return false;
      if (!q) return true;
      return f.filename.toLowerCase().includes(q) || prettyFileName(f.filename).toLowerCase().includes(q);
    });
  }, [files, search, filter]);

  const policy = useMemo(() => (kind === 'policy' && content ? parsePolicyDoc(content) : null), [kind, content]);
  const workflow = useMemo(() => (kind === 'workflow' && content ? parseWorkflowDoc(content) : null), [kind, content]);
  const integration = useMemo(() => (kind === 'integration' && content ? parseIntegrationDoc(content) : null), [kind, content]);

  const displayName = (policy?.title || workflow?.name || integration?.name || '').trim()
    || (selectedFile ? prettyFileName(selectedFile.filename) : `New ${copy.noun.toLowerCase()}`);

  const headerSystems: string[] = policy ? policy.systems
    : workflow ? [...new Set([workflow.system, ...workflow.steps.map(s => s.system)].filter(Boolean))]
    : integration ? [integration.sourceSystem, integration.targetSystem].filter(Boolean)
    : [];

  const contentCount = policy ? policy.sections.length : workflow ? workflow.steps.length : integration ? integration.mappings.reduce((n, m) => n + m.fields.length, 0) : 0;

  /* -------------------------------------------------------------- the list */

  const list = (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 space-y-2.5 border-b border-border p-3">
        <div className="flex items-center justify-between gap-2 pl-1">
          <h2 className="min-w-0 truncate text-md font-medium text-foreground">
            {title} {!loading && <span className="num text-sm font-normal text-muted-foreground">{files.length}</span>}
          </h2>
          <Button size="sm" onClick={() => { setBrowseOpen(false); setShowTemplates(true); }} disabled={saving}>
            <Icon name="plus" /> New
          </Button>
        </div>
        <SearchInput value={search} onChange={setSearch} placeholder={`Search ${copy.plural}`} className="sm:w-full" />
        <Chips<ListFilter>
          label="Filter"
          value={filter}
          onChange={setFilter}
          options={[
            { value: 'all', label: 'All', count: files.length },
            { value: 'recent', label: 'Updated this week', count: recentCount },
          ]}
        />
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {loading && files.length === 0 ? (
          <div className="space-y-3 p-4" aria-busy="true">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-4 w-3/5" />
                <Skeleton className="h-3 w-2/5" />
              </div>
            ))}
          </div>
        ) : listError ? (
          <div className="p-3"><InlineError onRetry={loadFiles}>{listError}</InlineError></div>
        ) : visibleFiles.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-muted-foreground">
            {files.length === 0 ? `No ${copy.plural} yet. Start one from a template.` : `No ${copy.plural} match this search.`}
          </p>
        ) : (
          <ul className="p-2">
            {visibleFiles.map((f, i) => {
              const on = selectedFile?.key === f.key;
              const logos = kind === 'integration' ? systemsInFilename(f.filename) : [];
              return (
                <li key={f.key} className="rise" style={{ '--i': Math.min(i, 10) } as React.CSSProperties}>
                  <button
                    type="button"
                    onClick={() => selectFile(f)}
                    aria-current={on ? 'true' : undefined}
                    className={cn(
                      'flex w-full items-start gap-2.5 rounded-md px-2 py-2 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      on ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground',
                    )}
                  >
                    <span className="min-w-0 flex-1">
                      <span className={cn('block truncate text-sm text-foreground', on && 'font-medium')}>{prettyFileName(f.filename)}</span>
                      <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                        {[formatDay(f.last_modified) && `Updated ${formatDay(f.last_modified)}`, formatSize(f.size)].filter(Boolean).join(' · ') || f.filename}
                      </span>
                    </span>
                    {logos.length > 0 && (
                      <span className="mt-0.5 flex shrink-0 items-center gap-1">
                        {logos.map((s, j) => (
                          <Fragment key={s}>
                            {j > 0 && <Icon name="arrow-right" className="h-3 w-3 text-subtle-foreground" />}
                            <SystemLogo system={s} size="xs" />
                          </Fragment>
                        ))}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {!loading && !listError && files.length > 0 && (
        <div className="shrink-0 border-t border-border px-4 py-2 text-xs text-muted-foreground">
          <span className="num">{visibleFiles.length}</span> of <span className="num">{files.length}</span> {copy.plural}
        </div>
      )}
    </div>
  );

  /* ------------------------------------------------------------ the detail */

  const hasItem = !!content || !!selectedFile;

  const readView = (
    <Tabs value={detailTab} onValueChange={(v) => setDetailTab(v as DetailTab)} className="flex min-h-0 flex-1 flex-col">
      <header className="shrink-0 px-4 pt-5 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">{copy.noun}</p>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <h2 className="min-w-0 break-words text-xl font-medium tracking-tight text-foreground sm:text-2xl">{displayName}</h2>
              {selectedFile
                ? <StatusPill tone="success" variant="soft">Saved</StatusPill>
                : <StatusPill tone="warning" variant="soft" live={saving}>{saving ? 'Saving' : 'Draft'}</StatusPill>}
              {policy?.riskLevel && <StatusPill status={policy.riskLevel} variant="soft">{policy.riskLevel} risk</StatusPill>}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="ghost" size="sm" onClick={requestDelete} disabled={!selectedFile || busy !== null} className="text-muted-foreground hover:text-destructive">
              <Icon name={busy === 'delete' ? 'spinner' : 'trash'} className={busy === 'delete' ? 'animate-spin' : undefined} /> Delete
            </Button>
            <Button variant="outline" size="sm" onClick={handleDuplicate} disabled={!content || busy !== null}>
              <Icon name={busy === 'duplicate' ? 'spinner' : 'copy'} className={busy === 'duplicate' ? 'animate-spin' : undefined} /> Duplicate
            </Button>
            <Button size="sm" onClick={startEdit} disabled={!content}>
              <Icon name="edit" /> Edit
            </Button>
          </div>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
          {kind === 'integration' && integration && headerSystems.length === 2 ? (
            <span className="inline-flex items-center gap-1.5 text-foreground">
              <SystemLogo system={integration.sourceSystem} size="sm" /> {systemName(integration.sourceSystem)}
              <Icon name="arrow-right" className="h-3.5 w-3.5 text-subtle-foreground" />
              <SystemLogo system={integration.targetSystem} size="sm" /> {systemName(integration.targetSystem)}
            </span>
          ) : headerSystems.length > 0 && (
            <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1 text-foreground">
              {headerSystems.map(s => (
                <span key={s} className="inline-flex items-center gap-1.5"><SystemLogo system={s} size="sm" /> {systemName(s)}</span>
              ))}
            </span>
          )}
          {headerSystems.length > 0 && <span aria-hidden="true">·</span>}
          {policy?.owner && <><span>Owned by {policy.owner}</span><span aria-hidden="true">·</span></>}
          {integration?.frequency && <><span>{integration.frequency}</span><span aria-hidden="true">·</span></>}
          {workflow && workflow.steps.length > 0 && <><span><span className="num">{workflow.steps.length}</span> steps</span><span aria-hidden="true">·</span></>}
          <span>{selectedFile?.last_modified ? `Updated ${formatDay(selectedFile.last_modified)}` : 'Not in the knowledge store yet'}</span>
        </div>

        <TabsList variant="line" className="mt-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="content">{copy.contentTab} <span className="num text-xs font-normal text-subtle-foreground">{contentCount}</span></TabsTrigger>
          <TabsTrigger value="definition">Definition</TabsTrigger>
        </TabsList>
      </header>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
        {message?.type === 'error' && <InlineError className="mb-4">{message.text}</InlineError>}
        <TabsContent value="overview" className="mt-0">
          {policy && <PolicyOverview doc={policy} onOpenRules={() => setDetailTab('content')} />}
          {workflow && <WorkflowOverview doc={workflow} onOpenSteps={() => setDetailTab('content')} />}
          {integration && <IntegrationOverview doc={integration} onOpenMappings={() => setDetailTab('content')} />}
        </TabsContent>
        <TabsContent value="content" className="mt-0">
          {policy && <PolicyRules doc={policy} />}
          {workflow && <WorkflowSteps doc={workflow} />}
          {integration && <IntegrationMappings doc={integration} />}
        </TabsContent>
        <TabsContent value="definition" className="mt-0">
          <div className="max-w-4xl">
            <p className="mb-3 text-sm text-muted-foreground">
              The stored {fileExtension === '.md' ? 'Markdown' : 'YAML'} the knowledge pipeline reads
              {selectedFile && <> from <span className="mono-id">{selectedFile.key}</span></>}.
            </p>
            <CodeBlock maxHeight={640}>{content}</CodeBlock>
          </div>
        </TabsContent>
      </div>
    </Tabs>
  );

  const editView = (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-3 border-b border-border px-4 py-3 sm:px-6">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">Editing {copy.noun.toLowerCase()}</p>
          <div className="flex flex-wrap items-baseline gap-x-3">
            <h2 className="min-w-0 truncate text-lg font-medium text-foreground">{displayName}</h2>
            <span className="text-xs text-muted-foreground">{hasChanges ? 'Unsaved changes' : 'No changes yet'}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {formBuilder && (
            <Tabs value={editorMode} onValueChange={(v) => switchMode(v as 'form' | 'raw')}>
              <TabsList className="h-8">
                <TabsTrigger value="form" className="px-3 text-xs">Form</TabsTrigger>
                <TabsTrigger value="raw" className="px-3 text-xs">{fileExtension === '.md' ? 'Markdown' : 'YAML'}</TabsTrigger>
              </TabsList>
            </Tabs>
          )}
          {editorMode === 'raw' && renderPreview && (
            <Button variant="ghost" size="sm" onClick={() => setShowPreview(!showPreview)} className="hidden lg:inline-flex">
              <Icon name="eye" /> {showPreview ? 'Hide preview' : 'Show preview'}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={cancelEdit} disabled={saving}>Cancel</Button>
          <Button size="sm" onClick={handleSave} disabled={saving || !content}>
            <Icon name={saving ? 'spinner' : 'check'} className={saving ? 'animate-spin' : undefined} /> Save
          </Button>
        </div>
      </header>

      {message?.type === 'error' && <div className="shrink-0 px-4 pt-4 sm:px-6"><InlineError>{message.text}</InlineError></div>}

      {editorMode === 'form' && formBuilder ? (
        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto" key={`form-${selectedFile?.key || 'draft'}`}>
          {formBuilder({ content, onChange: onFormChange })}
        </div>
      ) : (
        <div className={cn('grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)]', showPreview && renderPreview && 'lg:grid-cols-2')}>
          <div className="flex min-h-0 flex-col p-4 sm:p-6">
            <Textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              aria-label={`${copy.noun} definition`}
              className="scroll-thin min-h-0 flex-1 resize-none font-mono text-xs leading-5"
              spellCheck={false}
            />
          </div>
          {showPreview && renderPreview && (
            <div className="scroll-thin hidden min-h-0 overflow-y-auto border-l border-border p-6 lg:block">
              <SubHeading>Preview</SubHeading>
              {renderPreview(content)}
            </div>
          )}
        </div>
      )}
    </div>
  );

  return (
    <div className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)] lg:grid-cols-[300px_minmax(0,1fr)]">
      <aside className="hidden min-h-0 border-r border-border bg-sidebar/40 lg:block" aria-label={title}>{list}</aside>

      <Sheet open={browseOpen} onOpenChange={setBrowseOpen}>
        <SheetContent side="left" className="flex w-full flex-col gap-0 p-0 sm:max-w-sm">
          <div className="border-b border-border px-4 pb-3 pt-4 pr-12">
            <SheetTitle className="text-md font-medium">{title}</SheetTitle>
            <SheetDescription className="mt-0.5 text-xs text-muted-foreground">{description}</SheetDescription>
          </div>
          <div className="min-h-0 flex-1">{list}</div>
        </SheetContent>
      </Sheet>

      <div className="flex min-h-0 min-w-0 flex-col">
        <div className="shrink-0 border-b border-border px-4 py-2 lg:hidden">
          <Button variant="outline" size="sm" className="w-full justify-between" onClick={() => setBrowseOpen(true)}>
            <span className="flex min-w-0 items-center gap-2">
              <Icon name="list" className="h-3.5 w-3.5" />
              <span className="truncate">{hasItem ? displayName : `Browse ${copy.plural}`}</span>
            </span>
            <span className="flex items-center gap-1.5 font-normal text-muted-foreground">
              <span className="num">{files.length}</span>
              <Icon name="chevron-down" className="h-3.5 w-3.5" />
            </span>
          </Button>
        </div>

        {loadingContent || (loading && !hasItem) ? (
          <div className="space-y-4 p-5 sm:p-6" aria-busy="true">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-7 w-72 max-w-full" />
            <Skeleton className="h-4 w-96 max-w-full" />
            <Skeleton className="h-9 w-64" />
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-9 w-full max-w-3xl" />)}
          </div>
        ) : listError && !hasItem ? (
          <div className="p-5 sm:p-6"><InlineError onRetry={loadFiles}>{listError}</InlineError></div>
        ) : contentError && selectedFile ? (
          <div className="p-5 sm:p-6">
            <h2 className="mb-3 text-xl font-medium text-foreground">{prettyFileName(selectedFile.filename)}</h2>
            <InlineError onRetry={() => loadContent(selectedFile)}>{contentError}</InlineError>
          </div>
        ) : !content ? (
          <div className="p-5 sm:p-6">
            <EmptyState
              icon={copy.emptyIcon}
              title={selectedFile ? 'This file is empty' : `No ${copy.plural} yet`}
              description={selectedFile ? 'Delete it, or start a new one from a template.' : description}
              action={<Button onClick={() => setShowTemplates(true)}><Icon name="plus" /> New from template</Button>}
            />
          </div>
        ) : editing ? editView : readView}
      </div>

      <Dialog open={showTemplates} onOpenChange={setShowTemplates}>
        <DialogContent className="max-w-xl gap-0 p-0">
          <DialogHeader className="border-b border-border px-5 py-4 text-left">
            <DialogTitle>New {copy.noun.toLowerCase()}</DialogTitle>
            <DialogDescription>Start from a template. It is saved to the knowledge store and you can edit it straight away.</DialogDescription>
          </DialogHeader>
          <ul className="scroll-thin max-h-[60vh] overflow-y-auto p-2">
            {templates.map((t) => {
              const s = templateSummary(kind, t.content);
              const exists = files.some(f => f.filename === t.filename);
              return (
                <li key={t.filename}>
                  <button
                    type="button"
                    onClick={() => handleNewFromTemplate(t)}
                    className="group flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors duration-150 hover:bg-accent/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-foreground">{t.name}</span>
                      <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                        {s.line || t.filename}{exists && ' · replaces the saved file of the same name'}
                      </span>
                    </span>
                    {s.systems.length > 0 && (
                      <span className="flex shrink-0 items-center gap-1.5">
                        {s.systems.slice(0, 4).map(sys => <SystemLogo key={sys} system={sys} size="xs" />)}
                      </span>
                    )}
                    <Icon name="chevron-right" className="h-3.5 w-3.5 shrink-0 text-subtle-foreground transition-transform duration-150 group-hover:translate-x-0.5" />
                  </button>
                </li>
              );
            })}
          </ul>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================================
// Reading views
// ============================================================================

/** Inline `code` and **bold** inside policy text. */
function RichText({ children }: { children: string }) {
  const parts = String(children).split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith('`') && p.endsWith('`') && p.length > 2) return <code key={i} className="mono-id">{p.slice(1, -1)}</code>;
        if (p.startsWith('**') && p.endsWith('**') && p.length > 4) return <span key={i} className="font-medium text-foreground">{p.slice(2, -2)}</span>;
        return <Fragment key={i}>{p}</Fragment>;
      })}
    </>
  );
}

function SystemName({ system, className }: { system: string; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <SystemLogo system={system} size="xs" /> {systemName(system)}
    </span>
  );
}

function Dependencies({ items }: { items: DependencyDoc[] }) {
  if (items.length === 0) return null;
  return (
    <section>
      <SubHeading>Depends on</SubHeading>
      <ul className="border-t border-border">
        {items.map((d, i) => (
          <li key={`${d.entity}-${i}`} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-border py-2.5 text-sm">
            <span className="flex min-w-0 items-center gap-2">
              {d.system && <SystemLogo system={d.system} size="xs" />}
              <span className="mono-id truncate">{d.entity}</span>
            </span>
            <span className="text-muted-foreground">{d.relationship}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

const sectionSummary = (s: PolicySection): string => {
  const bits: string[] = [];
  if (s.table) bits.push(`${s.table.length - 1} ${s.table.length - 1 === 1 ? 'threshold' : 'thresholds'}`);
  if (s.bullets.length) bits.push(`${s.bullets.length} ${s.bullets.length === 1 ? 'rule' : 'rules'}`);
  if (!bits.length && s.paragraphs.length) bits.push('Statement');
  return bits.join(' · ');
};

const isSourceOfTruth = (s: PolicySection) => /source of truth/i.test(s.title);

/* ------------------------------------------------------------------ policy */

function PolicyOverview({ doc, onOpenRules }: { doc: PolicyDoc; onOpenRules?: () => void }) {
  const truth = doc.sections.find(isSourceOfTruth);
  const others = doc.sections.filter(s => !isSourceOfTruth(s));
  return (
    <div className="grid gap-x-10 gap-y-8 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0 max-w-3xl space-y-8">
        {truth && (
          <section>
            <SubHeading>Source of truth</SubHeading>
            {truth.paragraphs.map((p, i) => <p key={i} className="text-base leading-6 text-foreground"><RichText>{p}</RichText></p>)}
            {truth.bullets.length > 0 && (
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                {truth.bullets.map((b, i) => <li key={i}><RichText>{b}</RichText></li>)}
              </ul>
            )}
          </section>
        )}
        {others.length > 0 && (
          <section>
            <SubHeading>What this policy sets</SubHeading>
            <ul className="border-t border-border">
              {others.map((s, i) => {
                const first = s.bullets[0] || s.paragraphs[0] || '';
                const row = (
                  <>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-foreground">{s.title}</span>
                      {first && <span className="mt-0.5 line-clamp-1 block text-sm text-muted-foreground"><RichText>{first}</RichText></span>}
                    </span>
                    <span className="shrink-0 text-xs text-muted-foreground">{sectionSummary(s)}</span>
                  </>
                );
                return (
                  <li key={`${s.title}-${i}`} className="rise border-b border-border" style={{ '--i': i } as React.CSSProperties}>
                    {onOpenRules ? (
                      <button type="button" onClick={onOpenRules} className="flex w-full items-start gap-4 py-2.5 text-left transition-colors duration-150 hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                        {row}
                      </button>
                    ) : <div className="flex items-start gap-4 py-2.5">{row}</div>}
                  </li>
                );
              })}
            </ul>
          </section>
        )}
        {doc.sections.length === 0 && (
          <EmptyState icon="shield-check" title="No rules written yet" description="Add sections to this policy with Edit." />
        )}
      </div>
      <aside className="min-w-0">
        <SubHeading>Details</SubHeading>
        <KeyValues
          className="border-t border-border"
          items={[
            { label: 'Policy ID', value: doc.policyId || 'Not set', mono: !!doc.policyId },
            { label: 'Version', value: doc.version || 'Not set' },
            { label: 'Owner', value: doc.owner || 'Not set' },
            { label: 'Risk', value: doc.riskLevel ? <StatusPill status={doc.riskLevel} /> : 'Not set' },
            ...doc.extra.map(e => ({ label: e.label, value: e.value })),
          ]}
        />
        {doc.systems.length > 0 && (
          <div className="mt-6">
            <SubHeading>Applies to</SubHeading>
            <ul className="border-t border-border">
              {doc.systems.map(s => (
                <li key={s} className="flex items-center gap-2.5 border-b border-border py-2 text-sm text-foreground">
                  <SystemLogo system={s} size="sm" /> {s}
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}

/** A rule line. "condition → effect" is split around the arrow. */
function RuleLine({ text }: { text: string }) {
  const parts = text.split(/\s*(?:→|->|=>)\s*/);
  if (parts.length === 2 && parts[0] && parts[1]) {
    return (
      <span className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="text-foreground"><RichText>{parts[0]}</RichText></span>
        <Icon name="arrow-right" className="h-3 w-3 shrink-0 self-center text-subtle-foreground" />
        <span className="text-muted-foreground"><RichText>{parts[1]}</RichText></span>
      </span>
    );
  }
  return <span className="text-foreground"><RichText>{text}</RichText></span>;
}

const isBlankCell = (c: string) => /^[-—–]?$/.test(c.trim());

function PolicyTable({ rows }: { rows: string[][] }) {
  const [head, ...body] = rows;
  const riskCol = head.findIndex(h => /risk/i.test(h));
  return (
    <TableShell>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {head.map((h, i) => <TableHead key={i}>{h}</TableHead>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {body.map((r, i) => (
            <TableRow key={i}>
              {head.map((_, j) => {
                const cell = r[j] ?? '';
                return (
                  <TableCell key={j} className={cn('py-2.5 text-sm', j === 0 ? 'font-medium text-foreground' : 'text-muted-foreground')}>
                    {isBlankCell(cell)
                      ? <span className="text-subtle-foreground">None</span>
                      : j === riskCol ? <StatusPill status={cell} className="font-normal" /> : <RichText>{cell}</RichText>}
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableShell>
  );
}

function PolicyRules({ doc }: { doc: PolicyDoc }) {
  if (doc.sections.length === 0) {
    return <EmptyState icon="shield-check" title="No rules written yet" description="Add sections to this policy with Edit." />;
  }
  return (
    <div className="max-w-4xl space-y-9">
      {doc.sections.map((s, i) => (
        <section key={`${s.title}-${i}`} className="rise" style={{ '--i': Math.min(i, 8) } as React.CSSProperties}>
          <h3 className="flex items-baseline gap-2.5 text-md font-medium text-foreground">
            <span className="num text-sm font-normal text-subtle-foreground">{i + 1}</span>{s.title}
          </h3>
          {s.paragraphs.map((p, j) => <p key={j} className="mt-2 text-sm leading-6 text-muted-foreground"><RichText>{p}</RichText></p>)}
          {s.bullets.length > 0 && (
            <ul className="mt-3 border-t border-border">
              {s.bullets.map((b, j) => (
                <li key={j} className="border-b border-border py-2.5 text-sm"><RuleLine text={b} /></li>
              ))}
            </ul>
          )}
          {s.table && <div className="mt-3"><PolicyTable rows={s.table} /></div>}
        </section>
      ))}
    </div>
  );
}

export function PolicyPreview({ content }: { content: string }) {
  const doc = useMemo(() => parsePolicyDoc(content), [content]);
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-md font-medium text-foreground">{doc.title || 'Untitled policy'}</h3>
        <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
          {doc.riskLevel && <StatusPill status={doc.riskLevel}>{doc.riskLevel} risk</StatusPill>}
          {[doc.policyId, doc.owner, doc.systems.join(', ')].filter(Boolean).map((v, i) => <span key={i}>· {v}</span>)}
        </p>
      </div>
      <PolicyRules doc={doc} />
    </div>
  );
}

/* ---------------------------------------------------------------- workflow */

function WorkflowOverview({ doc, onOpenSteps }: { doc: WorkflowDoc; onOpenSteps?: () => void }) {
  const gates = doc.steps.filter(isApprovalStep).length;
  const bySystem = doc.steps.reduce<Record<string, number>>((acc, s) => { if (s.system) acc[s.system] = (acc[s.system] || 0) + 1; return acc; }, {});
  const hasTrigger = doc.trigger.object || doc.trigger.field || doc.trigger.condition;
  return (
    <div className="grid gap-x-10 gap-y-8 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0 max-w-3xl space-y-8">
        {doc.description && <p className="text-base leading-6 text-foreground">{doc.description}</p>}

        {hasTrigger && (
          <section>
            <SubHeading>Starts when</SubHeading>
            <div className="flex items-start gap-3 border-y border-border py-3">
              {doc.system && <SystemLogo system={doc.system} tile size="sm" />}
              <div className="min-w-0 text-sm">
                <p className="text-foreground">{doc.trigger.condition || 'The watched field changes'}</p>
                {(doc.trigger.object || doc.trigger.field) && (
                  <p className="mt-0.5 text-muted-foreground">
                    Watches <span className="mono-id">{[doc.trigger.object, doc.trigger.field].filter(Boolean).join('.')}</span>
                    {doc.system && <> in {systemName(doc.system)}</>}
                  </p>
                )}
              </div>
            </div>
          </section>
        )}

        {doc.steps.length > 0 ? (
          <section>
            <SubHeading action={onOpenSteps && (
              <button type="button" onClick={onOpenSteps} className="text-xs text-primary underline-offset-4 hover:underline dark:text-brand-hi">See every step</button>
            )}>
              The path
            </SubHeading>
            <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-2 border-t border-border pt-3">
              {doc.steps.map((s, i) => (
                <li key={i} className="rise flex items-center gap-1.5" style={{ '--i': i } as React.CSSProperties}>
                  {i > 0 && <Icon name="chevron-right" className="h-3 w-3 text-subtle-foreground" />}
                  <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground">
                    {s.system && <SystemLogo system={s.system} size="xs" />}
                    {s.name || `Step ${i + 1}`}
                  </span>
                </li>
              ))}
            </ol>
          </section>
        ) : (
          <EmptyState icon="workflow" title="No steps yet" description="Add the steps of this workflow with Edit." />
        )}

        <Dependencies items={doc.dependencies} />
      </div>

      <aside className="min-w-0">
        <SubHeading>Details</SubHeading>
        <KeyValues
          className="border-t border-border"
          items={[
            { label: 'Workflow ID', value: doc.id || 'Not set', mono: !!doc.id },
            { label: 'Version', value: doc.version || 'Not set' },
            { label: 'Primary system', value: doc.system ? <SystemName system={doc.system} /> : 'Not set' },
            { label: 'Steps', value: <span className="num">{doc.steps.length}</span> },
            { label: 'Approval gates', value: <span className="num">{gates}</span> },
          ]}
        />
        {Object.keys(bySystem).length > 0 && (
          <div className="mt-6">
            <SubHeading>Systems involved</SubHeading>
            <ul className="border-t border-border">
              {Object.entries(bySystem).map(([s, n]) => (
                <li key={s} className="flex items-center justify-between gap-3 border-b border-border py-2 text-sm">
                  <span className="flex items-center gap-2.5 text-foreground"><SystemLogo system={s} size="sm" /> {systemName(s)}</span>
                  <span className="text-muted-foreground"><span className="num">{n}</span> {n === 1 ? 'step' : 'steps'}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}

function WorkflowSteps({ doc }: { doc: WorkflowDoc }) {
  if (doc.steps.length === 0) {
    return <EmptyState icon="workflow" title="No steps yet" description="Add the steps of this workflow with Edit." />;
  }
  return (
    <div className="max-w-3xl">
      <Timeline
        items={doc.steps.map((s, i) => ({
          id: i,
          title: s.name || `Step ${i + 1}`,
          meta: s.system ? <SystemName system={s.system} /> : undefined,
          action: isApprovalStep(s) ? <StatusPill tone="warning">Approval gate</StatusPill> : undefined,
          description: (
            <>
              {s.action}
              {(s.sla || s.failureAction) && (
                <span className="mt-1 block text-xs">
                  {s.sla && <>Due within {s.sla}</>}
                  {s.sla && s.failureAction && ' · '}
                  {s.failureAction && <>If it fails: {s.failureAction}</>}
                </span>
              )}
            </>
          ),
        }))}
      />
    </div>
  );
}

export function WorkflowPreview({ content }: { content: string }) {
  const doc = useMemo(() => parseWorkflowDoc(content), [content]);
  if (!doc.name && doc.steps.length === 0) {
    return <p className="text-sm text-muted-foreground">Nothing to preview yet. The definition needs a name and steps.</p>;
  }
  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-md font-medium text-foreground">{doc.name || 'Untitled workflow'}</h3>
        {doc.description && <p className="mt-1 text-sm text-muted-foreground">{doc.description}</p>}
        {doc.trigger.condition && <p className="mt-1 text-xs text-muted-foreground">Starts when: {doc.trigger.condition}</p>}
      </div>
      <WorkflowSteps doc={doc} />
    </div>
  );
}

/* ------------------------------------------------------------- integration */

const SYNC_LABEL: Record<string, string> = {
  bidirectional: 'Two-way sync',
  unidirectional: 'One-way sync',
  one_way: 'One-way sync',
  two_way: 'Two-way sync',
};

const syncLabel = (t: string): string => SYNC_LABEL[t.toLowerCase().replace(/[\s-]+/g, '_')] || (t ? t.charAt(0).toUpperCase() + t.slice(1).replace(/_/g, ' ') : 'Sync');
const isTwoWay = (t: string): boolean => /bidirectional|two/i.test(t);

function DirectionGlyph({ direction }: { direction: string }) {
  if (direction === 'target_to_source') return <Icon name="arrow-right" className="h-3.5 w-3.5 rotate-180 text-subtle-foreground" label="Target to source" />;
  if (direction === 'bidirectional') return <Icon name="shuffle" className="h-3.5 w-3.5 text-subtle-foreground" label="Both ways" />;
  return <Icon name="arrow-right" className="h-3.5 w-3.5 text-subtle-foreground" label="Source to target" />;
}

function SystemEnd({ system, role, align = 'left' }: { system: string; role: string; align?: 'left' | 'right' }) {
  return (
    <div className={cn('flex min-w-0 items-center gap-3', align === 'right' && 'flex-row-reverse text-right')}>
      <SystemLogo system={system} tile size="lg" />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{role}</p>
        <p className="truncate text-md font-medium text-foreground">{system ? systemName(system) : 'Not set'}</p>
      </div>
    </div>
  );
}

function IntegrationOverview({ doc, onOpenMappings }: { doc: IntegrationDoc; onOpenMappings?: () => void }) {
  const twoWay = isTwoWay(doc.syncType);
  return (
    <div className="grid gap-x-10 gap-y-8 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0 max-w-3xl space-y-8">
        <section aria-label="Source and target" className="rounded-xl border border-border bg-card p-4 shadow-xs sm:p-5">
          <div className="grid items-center gap-x-4 gap-y-4 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
            <SystemEnd system={doc.sourceSystem} role="Source" />
            <div className="flex items-center gap-2 text-xs text-muted-foreground sm:flex-col sm:gap-1">
              <span className="flex items-center gap-1 text-subtle-foreground" aria-hidden="true">
                {twoWay && <Icon name="arrow-right" className="h-3.5 w-3.5 rotate-180" />}
                <span className="hidden h-px w-10 bg-border-strong sm:block" />
                <Icon name="arrow-right" className="h-3.5 w-3.5 text-primary dark:text-brand-hi" />
              </span>
              <span className="whitespace-nowrap">{syncLabel(doc.syncType)}</span>
            </div>
            <div className="sm:justify-self-end"><SystemEnd system={doc.targetSystem} role="Target" /></div>
          </div>
          {doc.frequency && (
            <p className="mt-4 flex items-center gap-2 border-t border-border pt-3 text-sm text-muted-foreground">
              <Icon name="clock" className="h-3.5 w-3.5 text-subtle-foreground" /> Runs: <span className="text-foreground">{doc.frequency}</span>
            </p>
          )}
        </section>

        {doc.description && <p className="text-base leading-6 text-foreground">{doc.description}</p>}

        {doc.mappings.length > 0 ? (
          <section>
            <SubHeading>What moves</SubHeading>
            <ul className="border-t border-border">
              {doc.mappings.map((m, i) => {
                const row = (
                  <>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-foreground">{m.name || `Mapping ${i + 1}`}</span>
                      <span className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                        <span className="mono-id">{m.sourceObject || 'source'}</span>
                        <Icon name="arrow-right" className="h-3 w-3 text-subtle-foreground" />
                        <span className="mono-id">{m.targetObject || 'target'}</span>
                      </span>
                    </span>
                    <span className="shrink-0 text-xs text-muted-foreground"><span className="num">{m.fields.length}</span> {m.fields.length === 1 ? 'field' : 'fields'}</span>
                  </>
                );
                return (
                  <li key={`${m.name}-${i}`} className="rise border-b border-border" style={{ '--i': i } as React.CSSProperties}>
                    {onOpenMappings ? (
                      <button type="button" onClick={onOpenMappings} className="flex w-full items-center gap-4 py-2.5 text-left transition-colors duration-150 hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                        {row}
                      </button>
                    ) : <div className="flex items-center gap-4 py-2.5">{row}</div>}
                  </li>
                );
              })}
            </ul>
          </section>
        ) : (
          <EmptyState icon="plug" title="No field mappings yet" description="Add mapping groups to this integration with Edit." />
        )}

        <Dependencies items={doc.dependencies} />
      </div>

      <aside className="min-w-0">
        <SubHeading>Details</SubHeading>
        <KeyValues
          className="border-t border-border"
          items={[
            { label: 'Integration ID', value: doc.id || 'Not set', mono: !!doc.id },
            { label: 'Version', value: doc.version || 'Not set' },
            { label: 'Direction', value: syncLabel(doc.syncType) },
            { label: 'Trigger', value: doc.frequency || 'Not set' },
          ]}
        />
        <div className="mt-6">
          <SubHeading>If a sync fails</SubHeading>
          <KeyValues
            className="border-t border-border"
            items={[
              { label: 'Retries', value: doc.retryCount != null ? <><span className="num">{doc.retryCount}</span>{doc.retryInterval && `, every ${doc.retryInterval}`}</> : 'Not set' },
              { label: 'Alert', value: doc.alertEmail || 'Nobody' },
              { label: 'Fallback', value: doc.fallback || 'None' },
            ]}
          />
        </div>
      </aside>
    </div>
  );
}

/** "Google Drive → SAP" on a mapping group names its own two systems. */
const mappingEnds = (direction: string): [string, string] => {
  const parts = /→|->/.test(direction) ? direction.split(/→|->/).map(p => p.trim()) : [];
  return [parts[0] || '', parts[1] || ''];
};

function IntegrationMappings({ doc }: { doc: IntegrationDoc }) {
  if (doc.mappings.length === 0) {
    return <EmptyState icon="plug" title="No field mappings yet" description="Add mapping groups to this integration with Edit." />;
  }
  const hasTransform = doc.mappings.some(m => m.fields.some(f => f.transform || f.constraint));
  return (
    <div className="max-w-4xl space-y-9">
      {doc.mappings.map((m, i) => (
        <section key={`${m.name}-${i}`} className="rise" style={{ '--i': Math.min(i, 8) } as React.CSSProperties}>
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h3 className="text-md font-medium text-foreground">{m.name || `Mapping ${i + 1}`}</h3>
            <span className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
              {(mappingEnds(m.direction)[0] || doc.sourceSystem) && <SystemLogo system={mappingEnds(m.direction)[0] || doc.sourceSystem} size="xs" />}
              <span className="mono-id">{m.sourceObject}</span>
              <Icon name="arrow-right" className="h-3 w-3 text-subtle-foreground" />
              {(mappingEnds(m.direction)[1] || doc.targetSystem) && <SystemLogo system={mappingEnds(m.direction)[1] || doc.targetSystem} size="xs" />}
              <span className="mono-id">{m.targetObject}</span>
            </span>
          </div>
          {m.fields.length === 0 ? (
            <p className="border-y border-border py-3 text-sm text-muted-foreground">No fields in this group yet.</p>
          ) : (
            <TableShell>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Source field</TableHead>
                    <TableHead className="w-8 px-0" />
                    <TableHead>Target field</TableHead>
                    {hasTransform && <TableHead>Transform or rule</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {m.fields.map((f, j) => (
                    <TableRow key={j}>
                      <TableCell className="py-2 font-mono text-xs text-foreground">{f.source || <span className="text-subtle-foreground">Not set</span>}</TableCell>
                      <TableCell className="px-0 py-2"><DirectionGlyph direction={f.direction} /></TableCell>
                      <TableCell className="py-2 font-mono text-xs text-foreground">{f.target || <span className="text-subtle-foreground">Not set</span>}</TableCell>
                      {hasTransform && <TableCell className="py-2 text-xs text-muted-foreground">{[f.transform, f.constraint].filter(Boolean).join(' · ') || 'None'}</TableCell>}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableShell>
          )}
        </section>
      ))}
    </div>
  );
}

export function IntegrationPreview({ content }: { content: string }) {
  const doc = useMemo(() => parseIntegrationDoc(content), [content]);
  if (!doc.name && doc.mappings.length === 0) {
    return <p className="text-sm text-muted-foreground">Nothing to preview yet. The definition needs a name and mappings.</p>;
  }
  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-md font-medium text-foreground">{doc.name || 'Untitled integration'}</h3>
        <p className="mt-1 flex flex-wrap items-center gap-1.5 text-sm text-muted-foreground">
          {doc.sourceSystem && <SystemName system={doc.sourceSystem} className="text-foreground" />}
          {doc.sourceSystem && doc.targetSystem && <Icon name="arrow-right" className="h-3.5 w-3.5 text-subtle-foreground" />}
          {doc.targetSystem && <SystemName system={doc.targetSystem} className="text-foreground" />}
          {doc.frequency && <span>· {doc.frequency}</span>}
        </p>
        {doc.description && <p className="mt-1 text-sm text-muted-foreground">{doc.description}</p>}
      </div>
      <IntegrationMappings doc={doc} />
    </div>
  );
}
