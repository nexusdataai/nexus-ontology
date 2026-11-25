import { useEffect, useState } from 'react';
import { etlPipelineService } from '@/services/etlPipelineService';

export default function PipelineRunConsole({
  journeyId,
  jobId,
}: {
  journeyId?: string;
  jobId?: string | null;
}) {
  const [status, setStatus] = useState<string>('—');
  const [detail, setDetail] = useState<string>('');

  useEffect(() => {
    if (!journeyId || !jobId) {
      setStatus('—');
      setDetail('');
      return;
    }
    let cancelled = false;
    const tick = async () => {
      try {
        const j = await etlPipelineService.getPipelineStatus(journeyId, jobId);
        if (cancelled) return;
        const st = (j as { status?: string }).status || (j as { jobStatus?: string }).jobStatus || 'unknown';
        setStatus(st);
        setDetail(JSON.stringify(j).slice(0, 240));
      } catch {
        if (!cancelled) setStatus('poll failed');
      }
    };
    tick();
    const t = window.setInterval(tick, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [journeyId, jobId]);

  if (!journeyId || !jobId) return null;

  return (
    <div className="border-t border-border bg-surface-1/60 px-4 py-2 text-xs">
      <p className="font-medium text-foreground">Sample run</p>
      <p className="text-muted-foreground">Job <span className="font-mono">{jobId}</span> · {status}</p>
      {detail && <p className="mt-1 truncate font-mono text-[10px] text-subtle-foreground">{detail}</p>}
    </div>
  );
}