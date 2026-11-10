import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Calculator } from 'lucide-react';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

interface Model {
  Model_ID?: string;
  Material_ID?: string;
  Modeled_Cost?: number;
  Confidence?: number;
  Generated_At?: string;
}

export function ShouldCostWidget({ widget, data, loading }: Props) {
  const rows: Model[] = (data?.rows as Model[]) ?? [];

  return (
    <Card className="h-full">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2">
          <Calculator className="h-4 w-4 text-primary" />
          {widget.title} ({rows.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center h-[220px]">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : rows.length === 0 ? (
          <div className="flex items-center justify-center h-[220px] text-sm text-muted-foreground">
            No should-cost models yet. Use should_cost_model in the chat.
          </div>
        ) : (
          <div className="space-y-2 max-h-[360px] overflow-auto">
            {rows.map((m, i) => {
              const conf = Number(m.Confidence ?? 0);
              const cost = Number(m.Modeled_Cost ?? 0);
              const confColor = conf > 0.75 ? 'text-success' : conf > 0.5 ? 'text-warning' : 'text-destructive';
              return (
                <div key={m.Model_ID || i} className="border rounded-md p-3 bg-card flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-muted-foreground">{m.Model_ID}</span>
                    <Badge variant="outline" className="text-xs">{m.Material_ID}</Badge>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-sm font-mono">
                      ${cost.toFixed(2)}
                      <span className="text-xs text-muted-foreground ml-1">/unit</span>
                    </div>
                    <Badge className={`text-xs bg-muted ${confColor}`}>
                      {(conf * 100).toFixed(0)}% conf
                    </Badge>
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
