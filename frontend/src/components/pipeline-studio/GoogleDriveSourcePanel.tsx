import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { dataFlowService } from '@/services/dataFlowService';
import apiClient from '@/services/apiClient';

export default function GoogleDriveSourcePanel({
  onTestResult,
}: {
  onTestResult?: (msg: string, ok: boolean) => void;
}) {
  const [status, setStatus] = useState<{ connected?: boolean; folders_configured?: number } | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    apiClient.get('/api/v1/connectors/gdrive/status').then(setStatus).catch(() => setStatus(null));
  }, []);

  const runTest = async () => {
    setTesting(true);
    try {
      const r = await dataFlowService.testGoogleDriveSource();
      const ok = Boolean((r as { success?: boolean }).success ?? (r as { connected?: boolean }).connected);
      const msg = (r as { message?: string }).message || (ok ? 'Connection OK' : 'Connection failed');
      onTestResult?.(msg, ok);
      if (ok) toast.success('Google Drive', { description: msg });
      else toast.error('Google Drive', { description: msg });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      onTestResult?.(msg, false);
      toast.error('Google Drive test failed', { description: msg });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-2 rounded-lg border border-border bg-surface-1/50 p-3">
      <p className="text-xs font-medium text-foreground">Google Drive connector</p>
      <p className="text-[11px] text-muted-foreground">
        {status?.connected ? 'Connected' : 'Not connected'}
        {typeof status?.folders_configured === 'number' && ` · ${status.folders_configured} folder(s) configured`}
      </p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" variant="outline" onClick={runTest} disabled={testing}>
          {testing ? 'Testing…' : 'Test connection'}
        </Button>
        <a
          href="/ai-stack/data-plane?tab=connectors"
          className="inline-flex h-8 items-center text-xs text-primary underline-offset-4 hover:underline"
        >
          Connector settings
        </a>
      </div>
    </div>
  );
}