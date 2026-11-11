import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { EmptyState } from '@/components/ds/primitives';
import { CodeBlock, InlineError, Panel, StatusPill } from '@/components/ds/kit';
import { SystemLogo, systemName } from '@/components/ds/SystemLogo';
import { cn } from '@/lib/utils';
import { connectorApiService, type ConnectorAPISpec, type RiskLevel, type TargetSystem } from '@/services/connectorApiService';
import ConnectorApiTestDrawer from '@/components/diagnostics/ConnectorApiTestDrawer';

interface Props {
  connectorId: string;
  connectorName: string;
  description: string;
  /** Legacy decoration, no longer drawn. Kept so older callers still compile. */
  color?: string;
  icon?: React.ReactNode;
  /** Availability word shown in the header (defaults to "Available"). */
  status?: string;
  targetSystem?: TargetSystem;
  onBack: () => void;
}

const RISK_LABEL: Record<RiskLevel, string> = {
  read_only: 'Read only',
  low_risk_write: 'Low-risk write',
  high_risk_write: 'High-risk write',
};

const HTTP_VERB = /^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(.+)$/i;

export function ConnectorDetailView({
  connectorId,
  connectorName,
  description,
  status = 'Available',
  targetSystem,
  onBack,
}: Props) {
  const [apis, setApis] = useState<ConnectorAPISpec[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [testApiId, setTestApiId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    if (!targetSystem) {
      setApis([]);
      return;
    }
    setApis(null);
    setError(null);
    connectorApiService
      .list(targetSystem)
      .then((resp) => {
        if (!cancelled) setApis(resp.items ?? []);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setApis([]);
          setError(e instanceof Error ? e.message : 'Failed to load connector APIs');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [targetSystem, reloadKey]);

  const toggle = (apiId: string) =>
    setExpanded((prev) => ({ ...prev, [apiId]: !prev[apiId] }));

  const loadingApis = !!targetSystem && apis === null && !error;
  const readCount = apis?.filter(a => a.risk_level === 'read_only').length ?? 0;
  const writeCount = (apis?.length ?? 0) - readCount;

  return (
    <div className="page">
      <button
        type="button"
        onClick={onBack}
        className="-ml-1 inline-flex items-center gap-1 rounded-sm px-1 text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Icon name="chevron-left" className="h-3.5 w-3.5" /> All connectors
      </button>

      <header className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start">
        <SystemLogo system={connectorId} tile size="lg" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <h1 className="text-lg font-medium tracking-tight text-foreground">{connectorName}</h1>
            <StatusPill status={status} variant="soft" />
          </div>
          <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">{description}</p>
          {targetSystem && apis !== null && !error && (
            <p className="mt-2 text-sm text-muted-foreground">
              Reaches {systemName(targetSystem)} through{' '}
              <span className="num font-medium text-foreground">{apis.length}</span> {apis.length === 1 ? 'API' : 'APIs'}
              {apis.length > 0 && <> · <span className="num">{readCount}</span> read only · <span className="num">{writeCount}</span> write</>}
            </p>
          )}
        </div>
      </header>

      <Panel
        className="mt-7"
        flush
        title="Connector APIs"
        description="Operations that agents and journeys can call through this connector."
        actions={apis !== null && apis.length > 0 ? <span className="num text-sm text-muted-foreground">{apis.length}</span> : undefined}
        footer={
          <span>
            Connector ID <span className="font-mono text-foreground">{connectorId}</span>
            {targetSystem && <> · target system <span className="font-mono text-foreground">{targetSystem}</span></>}
          </span>
        }
      >
        {!targetSystem ? (
          <div className="p-4 sm:p-5">
            <EmptyState
              icon="download"
              className="border-0 py-8"
              title="Ingestion source only"
              description="This connector brings data in. It has no outbound APIs registered."
            />
          </div>
        ) : loadingApis ? (
          <div className="divide-y divide-border" aria-busy="true">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-2 px-5 py-4">
                <Skeleton className="h-4 w-56 max-w-full" />
                <Skeleton className="h-3 w-80 max-w-full" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="p-4 sm:p-5">
            <InlineError onRetry={() => setReloadKey(k => k + 1)}>{error}</InlineError>
          </div>
        ) : apis && apis.length === 0 ? (
          <div className="p-4 sm:p-5">
            <EmptyState
              icon="plug"
              className="border-0 py-8"
              title="No APIs registered"
              description={`Nothing is registered for ${systemName(targetSystem)} yet.`}
            />
          </div>
        ) : (
          <ul>
            {(apis || []).map((api, i) => {
              const isOpen = !!expanded[api.api_id];
              const m = HTTP_VERB.exec(api.operation || '');
              const panelId = `api-${api.api_id}`;
              return (
                <li key={api.api_id} className="rise border-b border-border last:border-b-0" style={{ '--i': Math.min(i, 8) } as React.CSSProperties}>
                  <button
                    type="button"
                    onClick={() => toggle(api.api_id)}
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    className={cn(
                      'flex w-full items-start gap-3 px-4 py-3.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:px-5',
                      isOpen ? 'bg-surface-2/50' : 'hover:bg-surface-2/40',
                    )}
                  >
                    <Icon name="chevron-right" className={cn('mt-1 h-3.5 w-3.5 shrink-0 text-subtle-foreground transition-transform duration-200 ease-brand', isOpen && 'rotate-90')} />
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                        <span className="break-all font-mono text-sm font-medium text-foreground">{api.api_id}</span>
                        <span className="flex shrink-0 items-center gap-3">
                          {api.simulator_writeback && <span className="text-xs text-muted-foreground">Simulator writeback</span>}
                          <StatusPill status={api.risk_level}>{RISK_LABEL[api.risk_level] || api.risk_level}</StatusPill>
                        </span>
                      </span>
                      <span className="mt-1 block break-all font-mono text-xs text-muted-foreground">
                        {m ? <><span className="font-medium text-foreground">{m[1].toUpperCase()}</span> {m[2]}</> : api.operation}
                      </span>
                      {api.description && <span className={cn('mt-1 block text-sm text-muted-foreground', !isOpen && 'line-clamp-2')}>{api.description}</span>}
                    </span>
                  </button>

                  {isOpen && (
                    <div id={panelId} className="space-y-4 border-t border-border bg-surface-2/30 px-4 py-4 sm:px-5 sm:pl-[46px]">
                      {api.tags.length > 0 && (
                        <p className="text-xs text-muted-foreground">Tags: <span className="text-foreground">{api.tags.join(', ')}</span></p>
                      )}
                      <div className="grid gap-4 md:grid-cols-2">
                        <SchemaBlock title="Request schema" data={api.request_schema} />
                        <SchemaBlock title="Response schema" data={api.response_schema} />
                      </div>
                      <div className="flex justify-end">
                        <Button size="sm" variant="outline" onClick={() => setTestApiId(api.api_id)}>
                          <Icon name="play" className="h-3.5 w-3.5" /> Test in Workbench
                        </Button>
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Panel>

      {testApiId && (
        <ConnectorApiTestDrawer
          apiId={testApiId}
          onClose={() => setTestApiId(null)}
        />
      )}
    </div>
  );
}

function SchemaBlock({ title, data }: { title: string; data: Record<string, unknown> }) {
  const isEmpty = !data || Object.keys(data).length === 0;
  return (
    <div className="min-w-0">
      <p className="mb-1.5 text-xs font-medium text-muted-foreground">{title}</p>
      {isEmpty
        ? <p className="rounded-lg border border-dashed border-border-strong px-3 py-2.5 text-xs text-muted-foreground">No schema defined.</p>
        : <CodeBlock maxHeight={280}>{JSON.stringify(data, null, 2)}</CodeBlock>}
    </div>
  );
}
