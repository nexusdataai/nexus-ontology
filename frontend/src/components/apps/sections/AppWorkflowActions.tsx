import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, ShieldAlert, FileWarning, Clock, Mail, Truck, CreditCard, ChevronDown, ChevronRight } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import type { AppConfig } from '@/config/appRegistry';

interface ActionEntry {
  action_id: string;
  action_type: string;
  entity_type: string;
  entity_id: string;
  status: string;
  policy_reference: string;
  details: any;
  job_id: string;
  processed_at: string;
}

const ACTION_CONFIG: Record<string, { label: string; icon: typeof ShieldAlert; color: string; badge: string }> = {
  credit_hold: { label: 'Credit Hold', icon: ShieldAlert, color: 'text-red-400', badge: 'bg-red-500/20 text-red-400' },
  dispute_case: { label: 'Dispute Case', icon: FileWarning, color: 'text-amber-400', badge: 'bg-amber-500/20 text-amber-400' },
  sla_breach: { label: 'SLA Escalation', icon: Clock, color: 'text-purple-400', badge: 'bg-purple-500/20 text-purple-400' },
  dunning_notice: { label: 'Dunning Notice', icon: Mail, color: 'text-blue-400', badge: 'bg-blue-500/20 text-blue-400' },
  expedited_fulfillment: { label: 'Expedited', icon: Truck, color: 'text-green-400', badge: 'bg-green-500/20 text-green-400' },
  credit_note: { label: 'Credit Note', icon: CreditCard, color: 'text-cyan-400', badge: 'bg-cyan-500/20 text-cyan-400' },
};

interface Props { app: AppConfig; }

export function AppWorkflowActions({ app }: Props) {
  const [actions, setActions] = useState<ActionEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchActions = (retries = 3) => {
    setLoading(true);
    setError(false);
    apiClient.post(`/api/v1/apps/${app.id}/query`, {
      entity: 'O2C_Action_Log', limit: 500,
    }).then(d => {
      setActions(d?.rows || []);
      setLoading(false);
    }).catch(() => {
      if (retries > 1) {
        setTimeout(() => fetchActions(retries - 1), 800);
      } else {
        setError(true);
        setLoading(false);
      }
    });
  };

  useEffect(() => { fetchActions(); }, [app.id]);

  if (loading) return <div className="flex items-center justify-center h-full"><Loader2 className="h-6 w-6 animate-spin" /></div>;

  if (error) return (
    <div className="p-6">
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground space-y-3">
          <p>Failed to load workflow actions. The server may be temporarily unavailable.</p>
          <button onClick={() => fetchActions()} className="text-sm text-blue-400 hover:underline">Retry</button>
        </CardContent>
      </Card>
    </div>
  );

  const byType: Record<string, number> = {};
  for (const a of actions) {
    const t = a.action_type || 'unknown';
    byType[t] = (byType[t] || 0) + 1;
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Workflow Actions</h2>
        <p className="text-sm text-muted-foreground">Automated actions executed by the O2C Monitor — credit holds, disputes, escalations, collections</p>
      </div>

      {actions.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No workflow actions recorded yet. Run the O2C journey to generate actions.
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {Object.entries(ACTION_CONFIG).map(([type, cfg]) => {
              const Icon = cfg.icon;
              const count = byType[type] || 0;
              return (
                <Card key={type}>
                  <CardContent className="pt-4 pb-3 text-center">
                    <Icon className={`h-5 w-5 mx-auto mb-1 ${cfg.color}`} />
                    <div className="text-2xl font-bold">{count}</div>
                    <div className="text-[10px] text-muted-foreground">{cfg.label}</div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Action Timeline */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Action Log ({actions.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[400px]">
                <div className="divide-y divide-border/50">
                  {actions.map((action, i) => {
                    const cfg = ACTION_CONFIG[action.action_type] || { label: action.action_type, icon: Clock, color: 'text-muted-foreground', badge: 'bg-muted text-muted-foreground' };
                    const Icon = cfg.icon;
                    const isExpanded = expanded === action.action_id;
                    return (
                      <button key={action.action_id || i} onClick={() => setExpanded(isExpanded ? null : action.action_id)}
                        className="w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors">
                        <div className="flex items-center gap-3">
                          <Icon className={`h-4 w-4 shrink-0 ${cfg.color}`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <Badge className={`text-[9px] ${cfg.badge}`}>{cfg.label}</Badge>
                              <span className="text-xs font-mono text-muted-foreground">{action.entity_type}: {action.entity_id}</span>
                              <Badge variant="outline" className="text-[8px]">{action.status}</Badge>
                            </div>
                          </div>
                          {isExpanded ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                        </div>
                        {isExpanded && (
                          <div className="mt-2 ml-7 p-2 rounded bg-muted/30 text-xs space-y-1">
                            {action.policy_reference && <div><span className="text-muted-foreground">Policy:</span> {action.policy_reference}</div>}
                            {action.details && typeof action.details === 'object' && (
                              <pre className="text-[10px] text-muted-foreground whitespace-pre-wrap">{JSON.stringify(action.details, null, 2)}</pre>
                            )}
                            {action.details && typeof action.details === 'string' && (
                              <pre className="text-[10px] text-muted-foreground whitespace-pre-wrap">{action.details}</pre>
                            )}
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
