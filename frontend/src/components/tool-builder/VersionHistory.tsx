import { useEffect, useState } from 'react';
import { Loader2, RotateCcw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { toolBuilderService, type ToolVersion } from '@/services/toolBuilderService';

interface Props {
  toolId: string | null;
  onRestored: () => void;
}

export default function VersionHistory({ toolId, onRestored }: Props) {
  const [versions, setVersions] = useState<ToolVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState<number | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!toolId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    toolBuilderService.listVersions(toolId)
      .then((vs) => { if (!cancelled) setVersions(vs); })
      .catch((e) => { if (!cancelled) setError(e?.message || String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [toolId]);

  const handleRestore = async (version: number) => {
    if (!toolId) return;
    setRestoring(version);
    try {
      await toolBuilderService.restoreVersion(toolId, version);
      onRestored();
      const vs = await toolBuilderService.listVersions(toolId);
      setVersions(vs);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setRestoring(null);
    }
  };

  if (!toolId) {
    return (
      <div className="text-xs text-muted-foreground italic">
        Save the tool first to start a version history.
      </div>
    );
  }
  if (loading) {
    return (
      <div className="text-xs text-muted-foreground flex items-center gap-2">
        <Loader2 className="h-3 w-3 animate-spin" /> loading versions...
      </div>
    );
  }
  if (error) {
    return <div className="text-xs text-red-300">{error}</div>;
  }
  if (versions.length === 0) {
    return <div className="text-xs text-muted-foreground italic">No versions recorded.</div>;
  }

  const selected = versions.find((v) => v.version === selectedVersion) || null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-3 text-sm">
      <div className="border rounded-md max-h-96 overflow-auto">
        {versions.map((v) => (
          <button
            key={v.version}
            type="button"
            onClick={() => setSelectedVersion(v.version)}
            className={`w-full text-left px-3 py-2 border-b border-border/40 hover:bg-muted/30 ${
              selectedVersion === v.version ? 'bg-blue-600/10' : ''
            }`}
          >
            <div className="flex items-center justify-between">
              <Badge variant="outline" className="text-[10px]">v{v.version}</Badge>
              <span className="text-[9px] text-muted-foreground truncate ml-2">{v.createdAt}</span>
            </div>
            <div className="text-[10px] text-muted-foreground truncate mt-0.5">
              {v.changelog || '(no changelog)'}
            </div>
            <div className="text-[9px] text-muted-foreground/70 truncate">{v.createdBy || ''}</div>
          </button>
        ))}
      </div>
      <div>
        {!selected && (
          <div className="text-xs text-muted-foreground italic">
            Pick a version on the left to inspect or restore.
          </div>
        )}
        {selected && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-[11px] text-muted-foreground">
                v{selected.version} | sha {String(selected.source_sha256 || '').slice(0, 10)} | {selected.createdAt}
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleRestore(selected.version)}
                disabled={restoring === selected.version}
              >
                {restoring === selected.version
                  ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                  : <RotateCcw className="h-3.5 w-3.5 mr-1" />}
                Restore as current
              </Button>
            </div>
            <pre className="text-[10px] font-mono bg-muted/20 border rounded p-2 max-h-80 overflow-auto whitespace-pre-wrap">
              {selected.source_code}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
