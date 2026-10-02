import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Loader2, Play, X, XCircle, MinusCircle } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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

function statusBadge(status: string) {
  if (status === 'pass') {
    return (
      <Badge variant="outline" className="bg-green-500/15 text-green-300 border-green-500/30 gap-1">
        <CheckCircle2 className="h-3 w-3" /> pass
      </Badge>
    );
  }
  if (status === 'fail') {
    return (
      <Badge variant="outline" className="bg-red-500/15 text-red-300 border-red-500/30 gap-1">
        <XCircle className="h-3 w-3" /> fail
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="bg-amber-500/15 text-amber-300 border-amber-500/30 gap-1">
      <MinusCircle className="h-3 w-3" /> {status}
    </Badge>
  );
}

const RISK_BADGE: Record<string, string> = {
  read_only: 'bg-green-500/15 text-green-300 border-green-500/30',
  low_risk_write: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  high_risk_write: 'bg-red-500/15 text-red-300 border-red-500/30',
};

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
      setError(`payload JSON parse error: ${e.message || e}`);
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

  return (
    <Sheet open={!!adapter} onOpenChange={(o) => { if (!o) onClose(); }}>
      <SheetContent side="right" className="p-0 w-full sm:max-w-2xl flex flex-col">
        <SheetHeader className="p-4 pb-3 border-b">
          <SheetTitle className="text-base flex items-center gap-2 flex-wrap">
            <Play className="h-4 w-4 text-primary" />
            <span className="font-mono">{adapter?.id}</span>
            {adapter?.riskLevel && (
              <Badge variant="outline" className={cn('text-[10px]', RISK_BADGE[adapter.riskLevel] || RISK_BADGE.low_risk_write)}>
                {adapter.riskLevel.replace(/_/g, ' ')}
              </Badge>
            )}
            <Badge variant="outline" className="text-[10px] bg-muted/40">
              {adapter?.kind === 'tool' ? 'tool' : 'connector api'}
            </Badge>
          </SheetTitle>
          <SheetDescription className="text-xs text-muted-foreground">
            {adapter?.kind === 'tool'
              ? 'Dispatch through /api/v1/diagnostics/react-tools/{tool}/execute'
              : 'Dispatch through /api/v1/connector-apis/{api_id}/invoke'}
            {adapter?.connectorApi ? ` -> ${adapter.connectorApi}` : ''}
          </SheetDescription>
        </SheetHeader>

        <div className="p-4 space-y-3 flex-1 overflow-auto">
          {requiredKeys.length > 0 && (
            <div className="text-[11px] text-muted-foreground">
              Required:{' '}
              {requiredKeys.map((k) => (
                <code key={k} className="bg-muted/40 px-1 rounded mr-1">{k}</code>
              ))}
            </div>
          )}

          <div>
            <div className="text-[11px] font-medium text-muted-foreground mb-1">Payload (JSON)</div>
            <textarea
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              spellCheck={false}
              className={cn(
                'w-full font-mono text-[12px] p-2 rounded border bg-card/30',
                'min-h-[140px] resize-y',
              )}
            />
          </div>

          {error && (
            <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded p-2">
              {error}
            </div>
          )}

          {envelope && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {statusBadge(envelope.status)}
                {envelope.duration_ms != null && (
                  <span>{envelope.duration_ms} ms</span>
                )}
                {envelope.result_preview && (
                  <span className="font-mono text-[11px] text-muted-foreground/80">
                    {envelope.result_preview}
                  </span>
                )}
              </div>

              <Tabs value={resultTab} onValueChange={setResultTab}>
                <TabsList className="h-8">
                  <TabsTrigger value="result" className="text-xs h-7 px-2">Result</TabsTrigger>
                  {isConnector && hasVerification && (
                    <TabsTrigger value="verification" className="text-xs h-7 px-2">Verification</TabsTrigger>
                  )}
                  {isConnector && hasRequestBlock && (
                    <TabsTrigger value="request" className="text-xs h-7 px-2">Request</TabsTrigger>
                  )}
                </TabsList>
                <TabsContent value="result" className="mt-2">
                  <pre className="text-[11px] font-mono bg-muted/30 border rounded p-2 max-h-72 overflow-auto whitespace-pre-wrap">
{JSON.stringify(envelope.result ?? envelope.error ?? null, null, 2)}
                  </pre>
                </TabsContent>
                {isConnector && hasVerification && (
                  <TabsContent value="verification" className="mt-2">
                    <pre className="text-[11px] font-mono bg-muted/30 border rounded p-2 max-h-72 overflow-auto whitespace-pre-wrap">
{JSON.stringify(extras!.verification, null, 2)}
                    </pre>
                  </TabsContent>
                )}
                {isConnector && hasRequestBlock && (
                  <TabsContent value="request" className="mt-2">
                    <pre className="text-[11px] font-mono bg-muted/30 border rounded p-2 max-h-72 overflow-auto whitespace-pre-wrap">
{JSON.stringify(extras!.request, null, 2)}
                    </pre>
                  </TabsContent>
                )}
              </Tabs>
            </div>
          )}
        </div>

        <div className="border-t p-3 flex items-center justify-between bg-card/40">
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-3.5 w-3.5 mr-1" /> Close
          </Button>
          <Button size="sm" onClick={handleRun} disabled={running || !adapter}>
            {running ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-1" />}
            Run
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export default ExecuteDrawer;
