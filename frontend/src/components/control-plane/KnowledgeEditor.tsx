import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Loader2, Save, Trash2, Plus, FileText, ChevronDown, Eye, EyeOff,
  ArrowRight, AlertCircle, CheckCircle,
} from 'lucide-react';
import { ontoDataApi, type OntoFile } from '@/services/ontoDataApi';

const SYSTEM_COLORS: Record<string, string> = {
  Salesforce: 'bg-blue-500',
  Oracle: 'bg-orange-500',
  SAP: 'bg-green-500',
  'Google Drive': 'bg-red-500',
  Internal: 'bg-gray-500',
  External: 'bg-purple-500',
  'Cross-System': 'bg-indigo-500',
};

function SystemBadge({ system }: { system: string }) {
  const color = SYSTEM_COLORS[system] || 'bg-gray-500';
  return <span className={`text-[9px] px-1.5 py-0.5 rounded text-white ${color}`}>{system}</span>;
}

// ============================================================================
// Shared KnowledgeEditor Component
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

  const loadFiles = useCallback(async () => {
    setLoading(true);
    try {
      const data = await ontoDataApi.listFiles(category);
      setFiles(data.files || []);
    } catch { setFiles([]); }
    finally { setLoading(false); }
  }, [category]);

  useEffect(() => { loadFiles(); }, [loadFiles]);

  const loadContent = async (file: OntoFile) => {
    setSelectedFile(file);
    setLoadingContent(true);
    try {
      const config = await (async () => { try { const r = await fetch('/config.json'); const c = await r.json(); return c?.api?.baseUrl || ''; } catch { return ''; } })();
      const res = await fetch(`${config}/api/v1/control-plane/onto-data/files/${file.key}`, { credentials: 'include' });
      if (res.ok) {
        const text = await res.text();
        setContent(text);
        setOriginalContent(text);
      }
    } catch (e) { console.error('Load failed:', e); }
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
      await loadFiles();
      setTimeout(() => setMessage(null), 3000);
    } catch (e: any) { setMessage({ type: 'error', text: e.message || 'Save failed' }); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!selectedFile) return;
    try {
      await ontoDataApi.deleteFile(selectedFile.key);
      setSelectedFile(null);
      setContent('');
      setOriginalContent('');
      await loadFiles();
    } catch (e: any) { setMessage({ type: 'error', text: e.message || 'Delete failed' }); }
  };

  const handleNewFromTemplate = (template: Template) => {
    setSelectedFile(null);
    setContent(template.content);
    setOriginalContent('');
    setShowTemplates(false);
    const blob = new Blob([template.content], { type: 'text/plain' });
    const file = new File([blob], template.filename, { type: 'text/plain' });
    setSaving(true);
    ontoDataApi.uploadFile(category, file).then(() => {
      loadFiles();
      setMessage({ type: 'success', text: `Created ${template.filename}` });
      setTimeout(() => setMessage(null), 3000);
    }).catch(() => {}).finally(() => setSaving(false));
  };

  const isDirty = content !== originalContent;

  return (
    <div className="p-6 flex flex-col h-full gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold mb-1">{title}</h2>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        {message && (
          <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded ${message.type === 'success' ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>
            {message.type === 'success' ? <CheckCircle className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
            {message.text}
          </div>
        )}
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-0">
        {/* Sidebar */}
        <Card className="flex flex-col min-h-0">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Files ({files.length})</CardTitle>
              <div className="relative">
                <Button variant="ghost" size="sm" onClick={() => setShowTemplates(!showTemplates)}>
                  <Plus className="h-3.5 w-3.5 mr-1" />New
                  <ChevronDown className="h-3 w-3 ml-1" />
                </Button>
                {showTemplates && (
                  <div className="absolute right-0 top-full z-50 mt-1 w-64 rounded-lg border bg-popover p-1 shadow-lg">
                    <div className="text-[10px] text-muted-foreground px-2 py-1 font-medium">New from Template</div>
                    {templates.map((t, i) => (
                      <button key={i} onClick={() => handleNewFromTemplate(t)}
                        className="w-full text-left px-2 py-1.5 rounded text-xs hover:bg-muted transition-colors">
                        {t.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex-1 min-h-0 p-0">
            <ScrollArea className="h-[500px]">
              {loading ? (
                <div className="p-4 flex justify-center"><Loader2 className="h-4 w-4 animate-spin" /></div>
              ) : (
                <div className="divide-y">
                  {files.map((f, i) => (
                    <button key={i} onClick={() => loadContent(f)}
                      className={`w-full text-left p-2.5 hover:bg-muted/50 transition-colors text-xs ${selectedFile?.key === f.key ? 'bg-blue-600/10 border-l-2 border-blue-500' : ''}`}>
                      <div className="flex items-center gap-1.5">
                        <FileText className="h-3 w-3 text-muted-foreground shrink-0" />
                        <span className="truncate font-medium">{f.filename}</span>
                      </div>
                      <div className="text-[10px] text-muted-foreground mt-0.5 ml-4.5">
                        {f.size ? `${(f.size / 1024).toFixed(1)}KB` : ''} {f.last_modified ? new Date(f.last_modified).toLocaleDateString() : ''}
                      </div>
                    </button>
                  ))}
                  {files.length === 0 && (
                    <div className="p-4 text-center text-muted-foreground text-xs">
                      No files yet. Create one from a template.
                    </div>
                  )}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Editor + Preview */}
        <div className="lg:col-span-3 flex flex-col gap-3 min-h-0">
          {/* Toolbar */}
          <div className="flex items-center gap-2">
            {selectedFile && <Badge variant="outline" className="text-xs">{selectedFile.filename}</Badge>}
            {isDirty && <Badge className="text-[9px] bg-amber-500/20 text-amber-300">Unsaved changes</Badge>}
            <div className="flex-1" />
            {formBuilder && (
              <div className="flex items-center rounded-lg border overflow-hidden text-xs">
                <button onClick={() => setEditorMode('form')}
                  className={`px-3 py-1 ${editorMode === 'form' ? 'bg-blue-600/20 text-blue-300' : 'text-muted-foreground hover:bg-muted'}`}>
                  Form
                </button>
                <button onClick={() => setEditorMode('raw')}
                  className={`px-3 py-1 ${editorMode === 'raw' ? 'bg-blue-600/20 text-blue-300' : 'text-muted-foreground hover:bg-muted'}`}>
                  Raw
                </button>
              </div>
            )}
            {editorMode === 'raw' && renderPreview && (
              <Button variant="ghost" size="sm" onClick={() => setShowPreview(!showPreview)}>
                {showPreview ? <EyeOff className="h-3.5 w-3.5 mr-1" /> : <Eye className="h-3.5 w-3.5 mr-1" />}
                {showPreview ? 'Hide Preview' : 'Show Preview'}
              </Button>
            )}
            {selectedFile && (
              <Button variant="ghost" size="sm" onClick={handleDelete} className="text-destructive hover:text-destructive">
                <Trash2 className="h-3.5 w-3.5 mr-1" />Delete
              </Button>
            )}
            <Button size="sm" onClick={handleSave} disabled={saving || !content}>
              {saving ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}
              Save
            </Button>
          </div>

          {/* Content area */}
          {loadingContent ? (
            <div className="flex-1 flex items-center justify-center"><Loader2 className="h-5 w-5 animate-spin" /></div>
          ) : content ? (
            editorMode === 'form' && formBuilder ? (
              <ScrollArea className="flex-1 h-[500px]">
                {formBuilder({ content, onChange: setContent })}
              </ScrollArea>
            ) : (
            <div className={`flex-1 grid ${showPreview && renderPreview ? 'grid-cols-2' : 'grid-cols-1'} gap-3 min-h-0`}>
              <textarea
                value={content}
                onChange={e => setContent(e.target.value)}
                className="w-full h-[500px] p-3 rounded-lg border bg-card font-mono text-xs resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
                spellCheck={false}
              />
              {showPreview && renderPreview && (
                <Card className="overflow-hidden">
                  <CardHeader className="pb-1 pt-2 px-3">
                    <CardTitle className="text-[10px] text-muted-foreground">Live Preview</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <ScrollArea className="h-[480px] px-3 pb-3">
                      {renderPreview(content)}
                    </ScrollArea>
                  </CardContent>
                </Card>
              )}
            </div>
            )
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm border border-dashed rounded-lg">
              Select a file to edit, or create one from a template
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Preview Renderers
// ============================================================================

export function PolicyPreview({ content }: { content: string }) {
  const lines = content.split('\n');
  const meta: Record<string, string> = {};
  const sections: { title: string; body: string }[] = [];
  let currentSection = '';
  let currentBody: string[] = [];

  for (const line of lines) {
    const metaMatch = line.match(/^\*\*(.+?):\*\*\s*(.+)/);
    if (metaMatch) { meta[metaMatch[1]] = metaMatch[2]; continue; }
    if (line.startsWith('## ')) {
      if (currentSection) sections.push({ title: currentSection, body: currentBody.join('\n').trim() });
      currentSection = line.replace('## ', '').trim();
      currentBody = [];
    } else if (line.startsWith('# ')) {
      meta['Title'] = line.replace('# ', '').trim();
    } else {
      currentBody.push(line);
    }
  }
  if (currentSection) sections.push({ title: currentSection, body: currentBody.join('\n').trim() });

  return (
    <div className="space-y-3 text-xs">
      {meta['Title'] && <h3 className="font-bold text-sm">{meta['Title']}</h3>}
      {Object.keys(meta).length > 1 && (
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(meta).filter(([k]) => k !== 'Title').map(([k, v]) => (
            <Badge key={k} variant="outline" className="text-[9px]">{k}: {v}</Badge>
          ))}
        </div>
      )}
      {sections.map((s, i) => (
        <div key={i} className="border rounded-lg p-2">
          <div className="font-medium text-xs mb-1">{s.title}</div>
          <div className="text-[10px] text-muted-foreground whitespace-pre-wrap">{s.body.slice(0, 300)}{s.body.length > 300 ? '...' : ''}</div>
        </div>
      ))}
    </div>
  );
}

export function WorkflowPreview({ content }: { content: string }) {
  try {
    let data: any = {};
    if (content.trim().startsWith('{')) {
      data = JSON.parse(content);
    } else {
      const lines = content.split('\n');
      const yamlObj: any = {};
      let currentKey = '';
      let steps: any[] = [];
      let inSteps = false;
      let currentStep: any = {};

      for (const line of lines) {
        if (line.match(/^name:/)) yamlObj.name = line.split(':').slice(1).join(':').trim();
        if (line.match(/^system:/)) yamlObj.system = line.split(':').slice(1).join(':').trim();
        if (line.match(/^description:/)) yamlObj.description = line.split(':').slice(1).join(':').trim().replace(/^>$/, '');
        if (line.match(/^steps:/)) { inSteps = true; continue; }
        if (inSteps && line.match(/^\s+- order:/)) {
          if (currentStep.order) steps.push(currentStep);
          currentStep = { order: parseInt(line.split(':')[1]) };
        }
        if (inSteps && line.match(/^\s+name:/)) currentStep.name = line.split(':').slice(1).join(':').trim();
        if (inSteps && line.match(/^\s+system:/)) currentStep.system = line.split(':').slice(1).join(':').trim();
        if (inSteps && line.match(/^\s+action:/)) currentStep.action = line.split(':').slice(1).join(':').trim().replace(/^"(.+)"$/, '$1');
        if (line.match(/^dependencies:/) || line.match(/^sequence_constraints:/)) { inSteps = false; if (currentStep.order) { steps.push(currentStep); currentStep = {}; } }
      }
      if (currentStep.order) steps.push(currentStep);
      data = { ...yamlObj, steps };
    }

    return (
      <div className="space-y-3 text-xs">
        {data.name && <h3 className="font-bold text-sm">{data.name}</h3>}
        {data.system && <SystemBadge system={data.system} />}
        {data.description && <p className="text-[10px] text-muted-foreground">{data.description}</p>}
        {data.steps?.length > 0 && (
          <div className="space-y-1.5">
            {data.steps.map((s: any, i: number) => (
              <div key={i} className="flex items-start gap-2 p-2 rounded-lg border">
                <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-300 text-[10px] flex items-center justify-center shrink-0 font-bold">{s.order || i + 1}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium text-[11px]">{s.name || `Step ${i+1}`}</span>
                    {s.system && <SystemBadge system={s.system} />}
                  </div>
                  {s.action && <p className="text-[10px] text-muted-foreground mt-0.5">{s.action}</p>}
                </div>
                {i < data.steps.length - 1 && <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0 mt-1" />}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  } catch {
    return <div className="text-xs text-muted-foreground">Unable to parse YAML</div>;
  }
}

export function IntegrationPreview({ content }: { content: string }) {
  try {
    const lines = content.split('\n');
    let name = '', sourceSys = '', targetSys = '', description = '';
    const mappings: { name: string; sourceObj: string; targetObj: string; fields: { source: string; target: string; direction: string }[] }[] = [];
    let currentMapping: any = null;
    let currentField: any = null;
    let inMappings = false, inFields = false;

    for (const line of lines) {
      if (line.match(/^name:/)) name = line.split(':').slice(1).join(':').trim();
      if (line.match(/^source_system:/)) sourceSys = line.split(':').slice(1).join(':').trim();
      if (line.match(/^target_system:/)) targetSys = line.split(':').slice(1).join(':').trim();
      if (line.match(/^description:/)) description = line.split(':').slice(1).join(':').trim().replace(/^>$/, '');
      if (line.match(/^mappings:/)) { inMappings = true; continue; }
      if (inMappings && line.match(/^\s+- name:/)) {
        if (currentMapping) mappings.push(currentMapping);
        currentMapping = { name: line.split(':').slice(1).join(':').trim(), sourceObj: '', targetObj: '', fields: [] };
        inFields = false;
      }
      if (currentMapping && line.match(/^\s+source_object:/)) currentMapping.sourceObj = line.split(':').slice(1).join(':').trim();
      if (currentMapping && line.match(/^\s+target_object:/)) currentMapping.targetObj = line.split(':').slice(1).join(':').trim();
      if (line.match(/^\s+fields:/)) { inFields = true; continue; }
      if (inFields && line.match(/^\s+- source:/)) {
        if (currentField) currentMapping.fields.push(currentField);
        currentField = { source: line.split(':').slice(1).join(':').trim(), target: '', direction: '' };
      }
      if (currentField && line.match(/^\s+target:/)) currentField.target = line.split(':').slice(1).join(':').trim();
      if (currentField && line.match(/^\s+direction:/)) currentField.direction = line.split(':').slice(1).join(':').trim().replace(/^"(.+)"$/, '$1');
      if (line.match(/^failure_handling:/) || line.match(/^dependencies:/)) {
        if (currentField) { currentMapping?.fields.push(currentField); currentField = null; }
        if (currentMapping) { mappings.push(currentMapping); currentMapping = null; }
        inMappings = false; inFields = false;
      }
    }
    if (currentField && currentMapping) currentMapping.fields.push(currentField);
    if (currentMapping) mappings.push(currentMapping);

    return (
      <div className="space-y-3 text-xs">
        {name && <h3 className="font-bold text-sm">{name}</h3>}
        <div className="flex items-center gap-2">
          {sourceSys && <SystemBadge system={sourceSys} />}
          {sourceSys && targetSys && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
          {targetSys && <SystemBadge system={targetSys} />}
        </div>
        {description && <p className="text-[10px] text-muted-foreground">{description}</p>}
        {mappings.map((m, i) => (
          <div key={i} className="border rounded-lg p-2">
            <div className="font-medium text-[11px] mb-1.5">{m.name}</div>
            {(m.sourceObj || m.targetObj) && (
              <div className="text-[10px] text-muted-foreground mb-1">{m.sourceObj} → {m.targetObj}</div>
            )}
            {m.fields.length > 0 && (
              <table className="w-full text-[10px]">
                <thead><tr className="text-muted-foreground"><th className="text-left py-0.5">Source</th><th className="text-center">→</th><th className="text-left py-0.5">Target</th></tr></thead>
                <tbody>
                  {m.fields.map((f, j) => (
                    <tr key={j}><td className="py-0.5 font-mono">{f.source}</td><td className="text-center text-muted-foreground">→</td><td className="py-0.5 font-mono">{f.target}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}
      </div>
    );
  } catch {
    return <div className="text-xs text-muted-foreground">Unable to parse YAML</div>;
  }
}
