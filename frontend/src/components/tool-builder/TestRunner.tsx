import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { CodeBlock, InlineError, StatusPill, SubHeading } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
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

const LEVEL_TONE: Record<string, string> = {
  error: 'text-destructive',
  warning: 'text-warning',
};

/** Run the saved version of a tool with a JSON payload and read its result and logs. */
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
    return <EmptyState icon="flask" title="Save the tool to test it" description="A test runs the saved version of the tool, so it needs to be created first." />;
  }

  const logs = result?.logs || [];

  return (
    <div className="grid gap-x-8 gap-y-6 xl:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
      <div className="min-w-0">
        <h3 className="text-md font-medium text-foreground">Test run</h3>
        <p className="mt-0.5 text-sm text-muted-foreground">Runs the saved version against live data with the payload below.</p>

        {unsaved && (
          <p className="mt-3 flex items-start gap-2 rounded-lg border border-warning/25 bg-warning/10 px-3 py-2.5 text-sm text-foreground">
            <Icon name="alert-triangle" className="mt-0.5 shrink-0 text-warning" />
            You have unsaved changes. The test runs the last saved version.
          </p>
        )}

        <label htmlFor="tool-test-payload" className="mb-1.5 mt-4 block text-xs font-medium text-muted-foreground">Payload (JSON)</label>
        <Textarea
          id="tool-test-payload"
          value={paramsJson}
          onChange={(e) => setParamsJson(e.target.value)}
          spellCheck={false}
          className="min-h-[180px] resize-y font-mono text-xs leading-5"
        />

        <Button onClick={handleRun} disabled={running} className="mt-3">
          <Icon name={running ? 'spinner' : 'play'} className={cn(running && 'animate-spin')} />
          {running ? 'Running' : 'Run test'}
        </Button>
      </div>

      <div className="min-w-0 space-y-5">
        {error && <InlineError>{error}</InlineError>}

        {running && (
          <div className="space-y-3" aria-busy="true"><Skeleton className="h-5 w-40" /><Skeleton className="h-36 w-full" /></div>
        )}

        {!running && !result && !error && (
          <p className="rounded-xl border border-dashed border-border-strong px-5 py-10 text-center text-sm text-muted-foreground">The result and the log lines the tool writes appear here.</p>
        )}

        {result && (
          <div className="animate-fade-up space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <StatusPill status={result.status} variant="soft">{result.status === 'pass' ? 'Passed' : 'Failed'}</StatusPill>
              <span className="num text-sm text-muted-foreground">{result.duration_ms} ms</span>
            </div>

            {result.status === 'fail' && result.error && (
              <InlineError><span className="whitespace-pre-wrap break-words font-mono text-xs">{result.error}</span></InlineError>
            )}

            <section>
              <SubHeading>Result</SubHeading>
              <CodeBlock maxHeight={300}>
                {result.result === undefined || result.result === null
                  ? 'No result returned'
                  : JSON.stringify(result.result, null, 2)}
              </CodeBlock>
            </section>

            <section>
              <SubHeading action={<span className="num text-xs text-muted-foreground">{logs.length}</span>}>Logs</SubHeading>
              {logs.length === 0 ? (
                <p className="text-sm text-muted-foreground">The tool wrote no log lines.</p>
              ) : (
                <ol className="scroll-thin max-h-72 divide-y divide-border overflow-auto rounded-lg border border-border">
                  {logs.map((l, i) => (
                    <li key={i} className="grid grid-cols-[64px_minmax(0,1fr)] gap-x-3 px-3 py-2 text-xs">
                      <span className={cn('font-medium first-letter:uppercase', LEVEL_TONE[l.level] || 'text-muted-foreground')}>{l.level}</span>
                      <span className="min-w-0 break-words text-foreground">
                        {l.msg}
                        {l.kw && Object.keys(l.kw).length > 0 && (
                          <span className="mt-0.5 block font-mono text-muted-foreground">{JSON.stringify(l.kw)}</span>
                        )}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
