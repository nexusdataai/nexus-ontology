import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, ShieldCheck, ShieldAlert, TrendingUp } from 'lucide-react';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

interface Scenario {
  Scenario_ID?: string;
  Event_ID?: string;
  Name?: string;
  Modeled_Savings?: number;
  Modeled_Risk_Score?: number;
  Concentration_Pct?: number;
}

const CONCENTRATION_CEILING = 60;

export function ScenarioComparisonWidget({ widget, data, loading }: Props) {
  const scenarios: Scenario[] = (data?.rows as Scenario[]) ?? [];

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center h-[260px]">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : scenarios.length === 0 ? (
          <div className="flex items-center justify-center h-[260px] text-sm text-muted-foreground">
            Run an award scenario to compare cost, risk, and concentration
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {scenarios.slice(0, 3).map((s, i) => {
              const savings = Number(s.Modeled_Savings ?? 0);
              const risk = Number(s.Modeled_Risk_Score ?? 0);
              const conc = Number(s.Concentration_Pct ?? 100);
              const violates = conc > CONCENTRATION_CEILING;
              return (
                <div key={s.Scenario_ID || i} className="border rounded-md p-3 bg-card">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-muted-foreground">{s.Scenario_ID}</span>
                    {violates ? (
                      <Badge className="text-xs bg-destructive/10 text-destructive">
                        <ShieldAlert className="h-3 w-3 mr-1" />Concentration breach
                      </Badge>
                    ) : (
                      <Badge className="text-xs bg-success/10 text-success">
                        <ShieldCheck className="h-3 w-3 mr-1" />Within ceiling
                      </Badge>
                    )}
                  </div>
                  <div className="text-sm font-medium mb-2">{s.Name || 'Unnamed scenario'}</div>
                  <div className="space-y-2 text-xs">
                    <Metric
                      label="Savings"
                      value={`${savings.toFixed(1)}%`}
                      bar={Math.max(0, Math.min(100, savings + 20))}
                      tint="bg-success"
                    />
                    <Metric
                      label="Risk"
                      value={`${risk.toFixed(1)}/100`}
                      bar={Math.max(0, Math.min(100, risk))}
                      tint="bg-warning"
                    />
                    <Metric
                      label="Concentration"
                      value={`${conc.toFixed(0)}%`}
                      bar={Math.max(0, Math.min(100, conc))}
                      tint={violates ? 'bg-destructive' : 'bg-primary'}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value, bar, tint }: { label: string; value: string; bar: number; tint: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs text-muted-foreground mb-1">
        <span className="flex items-center gap-1"><TrendingUp className="h-3 w-3" />{label}</span>
        <span>{value}</span>
      </div>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={`h-full ${tint}`} style={{ width: `${bar}%` }} />
      </div>
    </div>
  );
}
