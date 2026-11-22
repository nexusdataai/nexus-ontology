import { useCallback, useEffect, useState } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { SubHeading } from '@/components/ds/kit';
import { nifiProcessorService, type NiFiAsset } from '@/services/nifiProcessorService';

export default function NiFiAssetsRegistryBrowser() {
  const [rows, setRows] = useState<NiFiAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<NiFiAsset | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await nifiProcessorService.listAssets();
      setRows(r.items || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <Skeleton className="h-32 w-full" />;
  }

  return (
    <div className="space-y-4">
      <SubHeading>Harvested Nexus flow assets</SubHeading>
      <div className="grid gap-2">
        {rows.map(a => (
          <button
            key={a.assetId}
            type="button"
            className="text-left rounded-md border p-3 hover:bg-muted/40"
            onClick={() => setSelected(a)}
          >
            <motionlessRowTitle
              id={String((a as { title?: string }).title || a.assetId)}
              kind={a.kind}
            />
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {(a.processorIds || []).join(', ')}
            </p>
          </button>
        ))}
      </div>
      {selected && (
        <pre className="text-xs rounded-md border p-3 max-h-64 overflow-auto whitespace-pre-wrap">
          {selected.contentText}
        </pre>
      )}
    </div>
  );
}

function motionlessRowTitle({ id, kind }: { id: string; kind: string }) {
  return (
    <span className="font-medium flex items-center gap-2">
      {id}
      <Badge variant="outline">{kind}</Badge>
    </span>
  );
}