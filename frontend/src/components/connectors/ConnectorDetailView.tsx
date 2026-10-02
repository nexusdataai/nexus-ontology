import { useEffect, useState } from 'react';
import { ArrowLeft, ChevronDown, ChevronRight, Loader2, Play, Plug, ShieldAlert, Tag } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { connectorApiService, type ConnectorAPISpec, type RiskLevel, type TargetSystem } from '@/services/connectorApiService';
import ConnectorApiTestDrawer from '@/components/diagnostics/ConnectorApiTestDrawer';

interface Props {
  connectorId: string;
  connectorName: string;
  description: string;
  color: string;
  icon: React.ReactNode;
  targetSystem?: TargetSystem;
  onBack: () => void;
}

const RISK_BADGE: Record<RiskLevel, string> = {
  read_only: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  low_risk_write: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  high_risk_write: 'bg-red-500/20 text-red-300 border-red-500/30',
};

const RISK_LABEL: Record<RiskLevel, string> = {
  read_only: 'Read',
  low_risk_write: 'Low-risk write',
  high_risk_write: 'High-risk write',
};

export function ConnectorDetailView({
  connectorId,
  connectorName,
  description,
  color,
  icon,
  targetSystem,
  onBack,
}: Props) {
  const [apis, setApis] = useState<ConnectorAPISpec[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [testApiId, setTestApiId] = useState<string | null>(null);

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
  }, [targetSystem]);

  const toggle = (apiId: string) =>
    setExpanded((prev) => ({ ...prev, [apiId]: !prev[apiId] }));

  return (
    <div className="p-6 space-y-4">
      <Button variant="ghost" size="sm" onClick={onBack} className="text-xs">
        <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Back to Connectors
      </Button>

      <Card className="overflow-hidden">
        <div className={`h-1.5 bg-gradient-to-r ${color}`} />
        <CardContent className="pt-4 pb-4 flex items-start gap-4">
          <div className={`p-3 rounded-xl bg-gradient-to-br ${color}`}>{icon}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold">{connectorName}</h1>
              {targetSystem && (
                <Badge variant="outline" className="text-[10px]">
                  target_system = {targetSystem}
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{description}</p>
            <p className="text-[10px] text-muted-foreground/80 mt-1">id: {connectorId}</p>
          </div>
        </CardContent>
      </Card>

      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold flex items-center gap-1.5">
            <Plug className="h-4 w-4 text-purple-400" /> Connector APIs
          </h2>
          {apis !== null && (
            <Badge variant="outline" className="text-[10px]">
              {apis.length} {apis.length === 1 ? 'API' : 'APIs'}
            </Badge>
          )}
        </div>

        {!targetSystem && (
          <Card>
            <CardContent className="pt-4 pb-4 text-xs text-muted-foreground">
              This connector is an ingestion source and has no outbound mutation APIs registered.
            </CardContent>
          </Card>
        )}

        {targetSystem && apis === null && !error && (
          <Card>
            <CardContent className="pt-4 pb-4 flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading APIs...
            </CardContent>
          </Card>
        )}

        {targetSystem && error && (
          <Card>
            <CardContent className="pt-4 pb-4 text-xs text-red-400">{error}</CardContent>
          </Card>
        )}

        {targetSystem && apis !== null && apis.length === 0 && !error && (
          <Card>
            <CardContent className="pt-4 pb-4 text-xs text-muted-foreground">
              No APIs registered for target_system &quot;{targetSystem}&quot;.
            </CardContent>
          </Card>
        )}

        {apis && apis.length > 0 && (
          <div className="space-y-2">
            {apis.map((api) => {
              const isOpen = !!expanded[api.api_id];
              return (
                <Card key={api.api_id} className="overflow-hidden">
                  <button
                    type="button"
                    className="w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors"
                    onClick={() => toggle(api.api_id)}
                  >
                    <div className="flex items-start gap-2">
                      {isOpen ? (
                        <ChevronDown className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                      ) : (
                        <ChevronRight className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <code className="text-xs font-mono font-semibold">{api.api_id}</code>
                          <Badge
                            variant="outline"
                            className={`text-[9px] ${RISK_BADGE[api.risk_level]}`}
                          >
                            {api.risk_level === 'high_risk_write' && (
                              <ShieldAlert className="h-2.5 w-2.5 mr-1" />
                            )}
                            {RISK_LABEL[api.risk_level]}
                          </Badge>
                          {api.simulator_writeback && (
                            <Badge variant="outline" className="text-[9px]">
                              simulator-writeback
                            </Badge>
                          )}
                        </div>
                        <code className="block text-[10px] font-mono text-muted-foreground mt-1">
                          {api.operation}
                        </code>
                        <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">
                          {api.description}
                        </p>
                      </div>
                    </div>
                  </button>

                  {isOpen && (
                    <div className="border-t px-4 py-3 space-y-3 bg-muted/10">
                      {api.tags.length > 0 && (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <Tag className="h-3 w-3 text-muted-foreground" />
                          {api.tags.map((t) => (
                            <Badge key={t} variant="outline" className="text-[9px]">
                              {t}
                            </Badge>
                          ))}
                        </div>
                      )}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <SchemaBlock title="Request schema" data={api.request_schema} />
                        <SchemaBlock title="Response schema" data={api.response_schema} />
                      </div>
                      <div className="flex justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-[10px]"
                          onClick={(e) => { e.stopPropagation(); setTestApiId(api.api_id); }}
                        >
                          <Play className="h-3 w-3 mr-1" /> Test in Workbench
                        </Button>
                      </div>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </div>

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
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
        {title}
      </p>
      <pre className="text-[10px] font-mono bg-background/50 border rounded p-2 overflow-x-auto">
        {isEmpty ? '(none)' : JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
