import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, CheckCircle2, Clock, XCircle, AlertTriangle, User } from 'lucide-react';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

interface ApprovalStep {
  role?: string;
  approver_id?: string;
  status?: string;
  at?: string;
  due_at?: string;
}

const STATUS_ICON: Record<string, any> = {
  approved: CheckCircle2,
  pending: Clock,
  rejected: XCircle,
  escalated: AlertTriangle,
};

const STATUS_TINT: Record<string, string> = {
  approved: 'text-green-600 bg-green-500/10',
  pending: 'text-amber-600 bg-amber-500/10',
  rejected: 'text-red-600 bg-red-500/10',
  escalated: 'text-orange-600 bg-orange-500/10',
};

// Renders the approval chain JSON stored on Quote_Header /
// Sourcing_Award.Approval_Chain_JSON as a vertical timeline.
export function ApprovalTimelineWidget({ widget, data, loading }: Props) {
  const rows: any[] = data?.rows ?? [];
  // The first row's Approval_Chain_JSON column holds the chain. If
  // multiple quotes are returned we show the first one's chain.
  const chainRaw = rows[0]?.Approval_Chain_JSON || rows[0]?.approval_chain_json;
  let chain: ApprovalStep[] = [];
  try {
    if (typeof chainRaw === 'string' && chainRaw) {
      chain = JSON.parse(chainRaw);
    } else if (Array.isArray(chainRaw)) {
      chain = chainRaw;
    }
  } catch {
    chain = [];
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center h-[220px]">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : chain.length === 0 ? (
          <div className="flex items-center justify-center h-[220px] text-sm text-muted-foreground">
            Auto-approved or no approval chain on this quote
          </div>
        ) : (
          <ol className="relative border-l border-border ml-3 space-y-4 py-2">
            {chain.map((step, idx) => {
              const status = (step.status || 'pending').toLowerCase();
              const Icon = STATUS_ICON[status] || Clock;
              const tint = STATUS_TINT[status] || 'text-muted-foreground bg-muted';
              return (
                <li key={idx} className="ml-4">
                  <span className={`absolute -left-[11px] flex items-center justify-center w-5 h-5 rounded-full ${tint}`}>
                    <Icon className="h-3 w-3" />
                  </span>
                  <div className="flex items-center gap-2">
                    <User className="h-3 w-3 text-muted-foreground" />
                    <span className="text-sm font-medium">{step.role || 'Approver'}</span>
                    <Badge variant="outline" className="text-[9px]">{step.approver_id || '—'}</Badge>
                    <Badge className={`text-[9px] ${tint}`}>{status}</Badge>
                  </div>
                  {(step.at || step.due_at) && (
                    <div className="text-[10px] text-muted-foreground mt-1 font-mono">
                      {step.at ? `acted ${step.at}` : `due ${step.due_at}`}
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
