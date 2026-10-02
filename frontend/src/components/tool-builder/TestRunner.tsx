import { useMemo, useState } from 'react';
import { CheckCircle2, Loader2, Play, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { toolBuilderService, type ToolTestResponse } from '@/services/toolBuilderService';

interface Props {
  toolId: string | null;
  parameters: Record<string, unknown>;
  unsaved: boolean;
}

function defaultPayload(parameters: Record<string, unknown>): string {
  const props = (parameters?.properties as Record<string, any>) || {};
  const out: Record<string, unknown> = {};
  for (const [k, p] of Object.entries(props)) {
    const t = p?.type;
    if (t === 'integer') out[k] = 0;
    else if (t === 'number') out[k] = 0;
    else if (t === 'boolean') out[k] = false;
    else if (t === 'array') out[k] = [];
    else if (t === 'object') out[k] = {};
    else out[k] = '';
  }
  return JSON.stringify(out, null, 2);
}

export default function TestRunner({ toolId, parameters, unsaved }: Props) {
  const initial = useMemo(() => defaultPayload(parameters), [parameters]);
  const [paramsJson, setParamsJson] = useState<string>(initial);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ToolTestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    if (!toolId) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const payload = paramsJson.trim() ? JSON.parse(paramsJson) : {};
      const r = await toolBuilderService.test(toolId, payload);
      setResult(r);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setRunning(false);
    }
  };

  if (!toolId) {
    return (
      <div className="text-xs text-muted-foreground italic">
        Save the tool first; testing dispatches the persisted version.
      </div>
    );
  }

  return (
    <div className="space-y-3 text-sm">
      {unsaved && (
        <div className="text-[11px] text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-1.5">
          You have unsaved changes. The Test endpoint dispatches the LAST SAVED version.
        </div>
      )}

      <div>
        <div className="text-[10px] uppercase text-muted-foreground mb-1">Params (JSON)</div>
        <textarea
          value={paramsJson}
          onChange={(e) => setParamsJson(e.target.value)}
          spellCheck={false}
          className="w-full h-32 text-[11px] font-mono bg-background/50 border rounded p-2"
        />
      </div>

      <div className="flex items-center gap-2">
        <Button onClick={handleRun} disabled={running} size="sm">
          {running ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-1" />}
          Run
        </Button>
        {result && (
          <Badge variant="outline" className={`text-[10px] ${
            result.status === 'pass'
              ? 'text-green-300 border-green-500/30 bg-green-500/10'
              : 'text-red-300 border-red-500/30 bg-red-500/10'
          }`}>
            {result.status === 'pass'
              ? <CheckCircle2 className="h-3 w-3 mr-1 inline" />
              : <XCircle className="h-3 w-3 mr-1 inline" />}
            {result.status} | {result.duration_ms}ms
          </Badge>
        )}
      </div>

      {error && (
        <div className="text-[11px] text-red-300 bg-red-500/10 border border-red-500/20 rounded px-2 py-1.5">
          {error}
        </div>
      )}

      {result && result.status === 'fail' && result.error && (
        <div className="text-[11px] text-red-300 bg-red-500/10 border border-red-500/20 rounded px-2 py-1.5 font-mono whitespace-pre-wrap">
          {result.error}
        </div>
      )}

      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div>
            <div className="text-[10px] uppercase text-muted-foreground mb-1">Result</div>
            <pre className="text-[10px] font-mono bg-muted/20 border rounded p-2 max-h-72 overflow-auto">
              {result.result === undefined || result.result === null
                ? '(none)'
                : JSON.stringify(result.result, null, 2)}
            </pre>
          </div>
          <div>
            <div className="text-[10px] uppercase text-muted-foreground mb-1">
              Logs ({result.logs?.length ?? 0})
            </div>
            <div className="text-[10px] font-mono bg-muted/20 border rounded p-2 max-h-72 overflow-auto space-y-0.5">
              {(result.logs || []).length === 0 && (
                <div className="text-muted-foreground italic">no log entries</div>
              )}
              {(result.logs || []).map((l, i) => (
                <div key={i} className="leading-tight">
                  <span className={`mr-2 font-semibold ${
                    l.level === 'error' ? 'text-red-300'
                    : l.level === 'warning' ? 'text-amber-300'
                    : 'text-muted-foreground'
                  }`}>
                    {l.level.toUpperCase()}
                  </span>
                  <span>{l.msg}</span>
                  {l.kw && Object.keys(l.kw).length > 0 && (
                    <span className="text-muted-foreground"> {JSON.stringify(l.kw)}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
