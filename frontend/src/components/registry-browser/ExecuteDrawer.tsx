import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Icon } from '@/components/ds/Icon';
import { CodeBlock, DetailSheet, InlineError, StatusPill, SubHeading } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { reactToolsDiagnosticsService, type ExecuteResult } from '@/services/reactToolsDiagnosticsService';
import {
  connectorApiWorkbenchService,
  type InvokeResponse,
} from '@/services/connectorApiWorkbenchService';
import type { ExecuteAdapter, ExecuteResultEnvelope } from './types';

interface ExecuteDrawerProps {
  adapter: ExecuteAdapter | null;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Adapter factories
// ---------------------------------------------------------------------------

/**
 * Build an ``ExecuteAdapter`` for a registered ReAct tool. Dispatches
 * through the existing ``reactToolsDiagnosticsService.executeOne``
 * endpoint which already covers code-defined + DDB-defined tools.
 */
export function adapterFromTool(args: {
  toolName: string;
  displayName?: string;
  paramsSchema?: Record<string, any> | null;
  defaultParams?: Record<string, any>;
  riskLevel?: string;
  connectorApi?: string | null;
}): ExecuteAdapter {
  return {
    kind: 'tool',
    id: args.toolName,
    displayName: args.displayName || args.toolName,
    paramsSchema: args.paramsSchema,
    defaultParams: args.defaultParams,
    riskLevel: args.riskLevel,
    connectorApi: args.connectorApi,
    run: async (params) => {
      const r: ExecuteResult = await reactToolsDiagnosticsService.executeOne(args.toolName, params);
      return {
        status: r.status,
        duration_ms: r.duration_ms,
        result: r.result ?? null,
        result_preview: r.result_preview,
        error: r.error,
        extras: {
          marker: r.marker,
          tool_id: r.tool_id,
          risk_level: r.risk_level,
        },
      };
    },
  };
}

/**
 * Build an ``ExecuteAdapter`` for a Connector API id. Dispatches
 * through ``connectorApiWorkbenchService.invoke`` and surfaces the
 * verification / audit block under ``extras`` so the drawer can render
 * them in dedicated tabs.
 */
export function adapterFromConnectorApi(args: {
  apiId: string;
  displayName?: string;
  paramsSchema?: Record<string, any> | null;
  defaultParams?: Record<string, any>;
  riskLevel?: string;
}): ExecuteAdapter {
  return {
    kind: 'connector_api',
    id: args.apiId,
    displayName: args.displayName || args.apiId,
    paramsSchema: args.paramsSchema,
    defaultParams: args.defaultParams,
    riskLevel: args.riskLevel,
    run: async (payload) => {
      const r: InvokeResponse = await connectorApiWorkbenchService.invoke(args.apiId, payload);
      const status =
        r.verdict === 'verified' || r.verdict === 'no_change' ? 'pass'
        : r.verdict === 'http_error' ? 'fail'
        : 'skip';
      return {
        status,
        duration_ms: r.duration_ms,
        result: r.response,
        result_preview: r.verdict,
        error: r.http_error || undefined,
        extras: {
          request: r.request,
          verification: r.verification,
          http_status: r.http_status,
          verdict: r.verdict,
        },
      };
    },
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Unified execute drawer for both tools and connector APIs.
 *
 * Renders a single payload-editor + Run button; the underlying adapter
 * decides which endpoint to call. The result panel uses tabs so the
 * tool path (Result / Logs) and the connector-api path (Result /
 * Verification / Request) can both surface their respective extras.
 */
export function ExecuteDrawer({ adapter, onClose }: ExecuteDrawerProps) {
  const [payload, setPayload] = useState<string>('{}');
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [envelope, setEnvelope] = useState<ExecuteResultEnvelope | null>(null);
  const [resultTab, setResultTab] = useState<string>('result');

  // Re-seed the payload editor whenever the adapter changes identity.
  useEffect(() => {
    if (!adapter) return;
    setPayload(JSON.stringify(adapter.defaultParams ?? {}, null, 2));
    setEnvelope(null);
    setError(null);
    setResultTab('result');
  }, [adapter]);

  const requiredKeys = useMemo<string[]>(() => {
    const r = adapter?.paramsSchema?.required;
    return Array.isArray(r) ? r : [];
  }, [adapter]);

  const handleRun = async () => {
    if (!adapter) return;
    let parsed: Record<string, any> = {};
    try {
      parsed = payload.trim() ? JSON.parse(payload) : {};
    } catch (e: any) {
      setError(`The payload is not valid JSON. Parse error: ${e.message || e}`);
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const env = await adapter.run(parsed);
      setEnvelope(env);
      setResultTab('result');
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setRunning(false);
    }
  };

  const extras = envelope?.extras as Record<string, any> | undefined;
  const hasVerification = !!extras?.verification;
  const hasRequestBlock = !!extras?.request;
  const isConnector = adapter?.kind === 'connector_api';
  const json = (v: unknown) => JSON.stringify(v, null, 2) ?? 'null';

  return (
    <DetailSheet
      open={!!adapter}
      onOpenChange={(o) => { if (!o) onClose(); }}
      wide
      title={<span className="font-mono text-md">{adapter?.id}</span>}
      description={`${adapter?.kind === 'tool' ? 'Runs this tool' : 'Calls this connector API'} with the payload below${adapter?.connectorApi ? `, through ${adapter.connectorApi}` : ''}.`}
      meta={(
        <>
          {adapter?.riskLevel && <StatusPill status={adapter.riskLevel} variant="soft" />}
          <span className="text-xs text-muted-foreground">{adapter?.kind === 'tool' ? 'Tool' : 'Connector API'}</span>
        </>
      )}
      footer={(
        <>
          <Button variant="ghost" onClick={onClose}>Close</Button>
          <Button onClick={handleRun} disabled={running || !adapter}>
            <Icon name={running ? 'spinner' : 'play'} className={cn(running && 'animate-spin')} />
            Run
          </Button>
        </>
      )}
    >
      <div className="space-y-6">
        <section>
          <SubHeading>Payload</SubHeading>
          <Textarea
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            spellCheck={false}
            aria-label="Payload as JSON"
            className="min-h-[160px] resize-y font-mono text-xs leading-5"
          />
          {requiredKeys.length > 0 && (
            <p className="mt-1.5 text-xs text-muted-foreground">
              Required:{' '}
              {requiredKeys.map((k, i) => (
                <span key={k}>{i > 0 && ', '}<code className="font-mono text-foreground">{k}</code></span>
              ))}
            </p>
          )}
        </section>

        {error && <InlineError>{error}</InlineError>}

        {running && !envelope && <Skeleton className="h-32 w-full" aria-busy="true" />}

        {envelope && (
          <section className="animate-fade-up">
            <SubHeading action={envelope.duration_ms != null ? <span className="num text-xs text-muted-foreground">{envelope.duration_ms} ms</span> : undefined}>
              <span className="flex flex-wrap items-center gap-3">
                Result
                <StatusPill status={envelope.status} tone={envelope.status === 'pass' || envelope.status === 'fail' ? undefined : 'warning'} />
              </span>
            </SubHeading>
            {envelope.result_preview && (
              <p className="mb-2 line-clamp-2 break-all font-mono text-xs text-muted-foreground">{envelope.result_preview}</p>
            )}

            <Tabs value={resultTab} onValueChange={setResultTab}>
              {(isConnector && (hasVerification || hasRequestBlock)) && (
                <TabsList variant="line" className="mb-3">
                  <TabsTrigger value="result">Response</TabsTrigger>
                  {hasVerification && <TabsTrigger value="verification">Verification</TabsTrigger>}
                  {hasRequestBlock && <TabsTrigger value="request">Request</TabsTrigger>}
                </TabsList>
              )}
              <TabsContent value="result" className="mt-0">
                <CodeBlock maxHeight={320} wrap>{json(envelope.result ?? envelope.error ?? null)}</CodeBlock>
              </TabsContent>
              {isConnector && hasVerification && (
                <TabsContent value="verification" className="mt-0">
                  <CodeBlock maxHeight={320} wrap>{json(extras!.verification)}</CodeBlock>
                </TabsContent>
              )}
              {isConnector && hasRequestBlock && (
                <TabsContent value="request" className="mt-0">
                  <CodeBlock maxHeight={320} wrap>{json(extras!.request)}</CodeBlock>
                </TabsContent>
              )}
            </Tabs>
          </section>
        )}
      </div>
    </DetailSheet>
  );
}

export default ExecuteDrawer;
