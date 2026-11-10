import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { CodeBlock, InlineError } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { formatWhen } from '@/components/reasoning/toolMeta';
import { toolBuilderService, type ToolVersion } from '@/services/toolBuilderService';

interface Props {
  toolId: string | null;
  onRestored: () => void;
}

/** Saved versions of a tool: pick one to read its code or restore it. */
export default function VersionHistory({ toolId, onRestored }: Props) {
  const [versions, setVersions] = useState<ToolVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState<number | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Bumped by "Retry" to load the list again.
  const [reload, setReload] = useState(0);

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
  }, [toolId, reload]);

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
    return <EmptyState icon="history" title="No history yet" description="Save the tool to start its version history." />;
  }
  if (loading) {
    return (
      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]" aria-busy="true">
        <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="space-y-2"><Skeleton className="h-4 w-24" /><Skeleton className="h-3 w-full" /></div>)}</div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (error) {
    return <InlineError onRetry={() => setReload(n => n + 1)}>{error}</InlineError>;
  }
  if (versions.length === 0) {
    return <EmptyState icon="history" title="No versions recorded" description="Each save adds a version here." />;
  }

  // The newest version is open by default.
  const selected = versions.find((v) => v.version === selectedVersion) || versions[0];
  const latest = Math.max(...versions.map(v => v.version));

  return (
    <div className="grid gap-x-8 gap-y-6 lg:grid-cols-[280px_minmax(0,1fr)]">
      <div className="min-w-0">
        <h3 className="mb-2 text-md font-medium text-foreground">Versions</h3>
        <ol className="scroll-thin max-h-[420px] overflow-auto rounded-xl border border-border">
          {versions.map((v, i) => {
            const on = selected.version === v.version;
            return (
              <li key={v.version} className="border-b border-border last:border-b-0">
                <button
                  type="button"
                  onClick={() => setSelectedVersion(v.version)}
                  aria-current={on}
                  style={{ ['--i' as any]: Math.min(i, 10) }}
                  className={cn(
                    'rise block w-full px-3.5 py-2.5 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
                    on ? 'bg-accent' : 'hover:bg-accent/60',
                  )}
                >
                  <span className="flex items-baseline justify-between gap-3">
                    <span className={cn('num text-sm text-foreground', on && 'font-medium')}>
                      Version {v.version}{v.version === latest && <span className="font-normal text-muted-foreground"> · current</span>}
                    </span>
                    <span className="num shrink-0 text-xs text-muted-foreground">{formatWhen(v.createdAt)}</span>
                  </span>
                  <span className="mt-0.5 block truncate text-xs text-muted-foreground">{v.changelog || 'No change note'}</span>
                  {v.createdBy && <span className="block truncate text-xs text-subtle-foreground">{v.createdBy}</span>}
                </button>
              </li>
            );
          })}
        </ol>
      </div>

      <div key={selected.version} className="min-w-0 animate-fade-in">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-md font-medium text-foreground">Version {selected.version}</h3>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {selected.changelog || 'No change note'}
              {selected.createdBy && <> · {selected.createdBy}</>}
              {selected.createdAt && <> · {formatWhen(selected.createdAt)}</>}
            </p>
            {selected.source_sha256 && <p className="mono-id mt-1" title={selected.source_sha256}>Checksum {String(selected.source_sha256).replace(/^sha256:/, '').slice(0, 12)}</p>}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleRestore(selected.version)}
            disabled={restoring === selected.version}
          >
            <Icon name={restoring === selected.version ? 'spinner' : 'history'} className={cn(restoring === selected.version && 'animate-spin')} />
            Restore this version
          </Button>
        </div>
        <CodeBlock className="mt-4" maxHeight={420}>{selected.source_code || ''}</CodeBlock>
      </div>
    </div>
  );
}
