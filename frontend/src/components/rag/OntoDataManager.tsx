import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { InlineError, Toolbar, ToolbarSpacer } from '@/components/ds/kit';
import { ontoDataApi, type OntoFile } from '@/services/ontoDataApi';
import { confirmDialog } from '@/components/ds/confirm';

const CATEGORIES = [
  { id: 'policies', label: 'Policies', hint: 'Markdown, text or PDF', accept: '.md,.txt,.pdf' },
  { id: 'workflows', label: 'Workflows', hint: 'YAML or JSON', accept: '.yaml,.yml,.json' },
  { id: 'integrations', label: 'Integration rules', hint: 'YAML or JSON', accept: '.json,.yaml,.yml' },
];

const OntoDataManager: React.FC = () => {
  const [files, setFiles] = useState<OntoFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});
  // Presentation only.
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const loadFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await ontoDataApi.listFiles();
      setFiles(res.files || []);
    } catch (e: any) {
      console.error('Failed to load files:', e);
      setError(e?.message || 'The knowledge files could not be loaded.');
    } finally {
      setLoading(false);
      setLoaded(true);
    }
  };

  useEffect(() => { loadFiles(); }, []);

  const handleUpload = async (category: string, file: File) => {
    setUploading(category);
    try {
      await ontoDataApi.uploadFile(category, file);
      toast.success('File uploaded', { description: file.name });
      await loadFiles();
    } catch (e: any) {
      console.error('Upload failed:', e);
      toast.error('Upload failed', { description: e?.message });
    } finally {
      setUploading(null);
    }
  };

  const handleDelete = async (key: string) => {
    if (!(await confirmDialog({ title: `Delete ${key.split('/').pop()}?`, description: 'The file is removed from the knowledge store.', destructive: true }))) return;
    try {
      await ontoDataApi.deleteFile(key);
      toast.success('File deleted', { description: key.split('/').pop() });
      await loadFiles();
    } catch (e: any) {
      console.error('Delete failed:', e);
      toast.error('Delete failed', { description: e?.message });
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const res = await ontoDataApi.seedDefaults();
      if (res.success) {
        const n = Object.values(res.counts || {}).reduce((a, b) => a + (Number(b) || 0), 0);
        toast.success('Sample files loaded', { description: n ? `${n} files are in the knowledge store.` : undefined });
        await loadFiles();
      } else {
        toast.error('The sample files could not be loaded');
      }
    } catch (e: any) {
      console.error('Seed failed:', e);
      toast.error('The sample files could not be loaded', { description: e?.message });
    } finally {
      setSeeding(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDay = (iso?: string) => {
    if (!iso) return '';
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const firstLoad = loading && !loaded;

  return (
    <div className="space-y-6">
      <Toolbar>
        <p className="text-sm text-muted-foreground">
          {firstLoad ? 'Loading files' : <><span className="num font-medium text-foreground">{files.length}</span> {files.length === 1 ? 'file' : 'files'} in the knowledge store</>}
        </p>
        <ToolbarSpacer />
        <Button variant="ghost" size="sm" onClick={loadFiles} disabled={loading}>
          <Icon name="refresh" className={loading ? 'animate-spin' : undefined} /> Refresh
        </Button>
        <Button variant="outline" size="sm" onClick={handleSeed} disabled={seeding}>
          <Icon name={seeding ? 'spinner' : 'download'} className={seeding ? 'animate-spin' : undefined} /> Load sample files
        </Button>
      </Toolbar>

      {error && <InlineError onRetry={loadFiles}>{error}</InlineError>}

      {CATEGORIES.map((cat) => {
        const catFiles = files.filter((f) => f.category === cat.id);

        return (
          <section key={cat.id}>
            <div className="flex items-end justify-between gap-3 pb-2">
              <div className="min-w-0">
                <h3 className="text-sm font-medium text-foreground">
                  {cat.label} {!firstLoad && <span className="num font-normal text-muted-foreground">{catFiles.length}</span>}
                </h3>
                <p className="text-xs text-muted-foreground">{cat.hint}</p>
              </div>
              <div className="shrink-0">
                <input
                  type="file"
                  accept={cat.accept}
                  className="hidden"
                  ref={(el) => { fileInputRefs.current[cat.id] = el; }}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUpload(cat.id, file);
                    e.target.value = '';
                  }}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRefs.current[cat.id]?.click()}
                  disabled={uploading === cat.id}
                >
                  <Icon name={uploading === cat.id ? 'spinner' : 'upload'} className={uploading === cat.id ? 'animate-spin' : undefined} />
                  {uploading === cat.id ? 'Uploading' : 'Upload'}
                </Button>
              </div>
            </div>

            {firstLoad ? (
              <div className="space-y-2 border-t border-border pt-3" aria-busy="true">
                {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
              </div>
            ) : catFiles.length === 0 ? (
              <p className="border-y border-border py-3 text-sm text-muted-foreground">
                No {cat.label.toLowerCase()} here yet. Upload a file, or load the sample files.
              </p>
            ) : (
              <ul className="border-t border-border">
                {catFiles.map((f) => (
                  <li key={f.key} className="group flex items-center gap-3 border-b border-border py-2 text-sm">
                    <span className="min-w-0 flex-1 truncate text-foreground">{f.filename}</span>
                    <span className="hidden shrink-0 text-xs text-muted-foreground sm:inline">{formatDay(f.last_modified)}</span>
                    <span className="num w-16 shrink-0 text-right text-xs text-muted-foreground">{formatSize(f.size)}</span>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="h-7 w-7 shrink-0 text-subtle-foreground hover:text-destructive sm:opacity-0 sm:focus-visible:opacity-100 sm:group-hover:opacity-100"
                      onClick={() => handleDelete(f.key)}
                      aria-label={`Delete ${f.filename}`}
                    >
                      <Icon name="trash" className="h-3.5 w-3.5" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
};

export default OntoDataManager;
