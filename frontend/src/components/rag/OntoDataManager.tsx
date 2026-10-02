import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Upload, Trash2, RefreshCw, Loader2, FileText, GitBranch, Link2,
  Sparkles, Download, FolderOpen,
} from 'lucide-react';
import { ontoDataApi, type OntoFile } from '@/services/ontoDataApi';

const CATEGORIES = [
  { id: 'policies', label: 'Policies', icon: FileText, accept: '.md,.txt,.pdf', color: 'text-amber-400' },
  { id: 'workflows', label: 'Workflows', icon: GitBranch, accept: '.yaml,.yml,.json', color: 'text-green-400' },
  { id: 'integrations', label: 'Integrations', icon: Link2, accept: '.json,.yaml,.yml', color: 'text-purple-400' },
];

const OntoDataManager: React.FC = () => {
  const [files, setFiles] = useState<OntoFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const loadFiles = async () => {
    setLoading(true);
    try {
      const res = await ontoDataApi.listFiles();
      setFiles(res.files || []);
    } catch (e) {
      console.error('Failed to load files:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadFiles(); }, []);

  const handleUpload = async (category: string, file: File) => {
    setUploading(category);
    try {
      await ontoDataApi.uploadFile(category, file);
      await loadFiles();
    } catch (e) {
      console.error('Upload failed:', e);
    } finally {
      setUploading(null);
    }
  };

  const handleDelete = async (key: string) => {
    if (!confirm(`Delete ${key.split('/').pop()}?`)) return;
    try {
      await ontoDataApi.deleteFile(key);
      await loadFiles();
    } catch (e) {
      console.error('Delete failed:', e);
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const res = await ontoDataApi.seedDefaults();
      if (res.success) {
        await loadFiles();
      }
    } catch (e) {
      console.error('Seed failed:', e);
    } finally {
      setSeeding(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FolderOpen className="h-5 w-5" />
          <span className="font-medium">Knowledge Data Store</span>
          <Badge variant="secondary">{files.length} files</Badge>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadFiles} disabled={loading}>
            {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
          </Button>
          <Button size="sm" onClick={handleSeed} disabled={seeding}>
            {seeding ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Sparkles className="h-3 w-3 mr-1" />}
            Seed Defaults
          </Button>
        </div>
      </div>

      <ScrollArea className="h-[450px]">
        <div className="space-y-4 pr-3">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const catFiles = files.filter((f) => f.category === cat.id);

            return (
              <Card key={cat.id} className="border-border/50">
                <CardHeader className="py-3 px-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className={`h-4 w-4 ${cat.color}`} />
                      <CardTitle className="text-sm">{cat.label}</CardTitle>
                      <Badge variant="outline" className="text-xs">{catFiles.length}</Badge>
                    </div>
                    <div>
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
                        {uploading === cat.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <><Upload className="h-3 w-3 mr-1" /> Upload</>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0 px-4 pb-3">
                  {catFiles.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No {cat.label.toLowerCase()} uploaded yet. Click "Seed Defaults" to load sample data.</p>
                  ) : (
                    <div className="space-y-1">
                      {catFiles.map((f) => (
                        <div key={f.key} className="flex items-center justify-between py-1 px-2 rounded hover:bg-muted/30 text-sm">
                          <div className="flex items-center gap-2 min-w-0 flex-1">
                            <Icon className="h-3 w-3 shrink-0 opacity-50" />
                            <span className="truncate">{f.filename}</span>
                            <span className="text-xs text-muted-foreground shrink-0">{formatSize(f.size)}</span>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 shrink-0"
                            onClick={() => handleDelete(f.key)}
                          >
                            <Trash2 className="h-3 w-3 text-destructive" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
};

export default OntoDataManager;
