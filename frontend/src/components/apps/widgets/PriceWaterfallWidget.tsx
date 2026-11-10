import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, TrendingDown, TrendingUp } from 'lucide-react';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

interface WaterfallRow {
  Line_ID?: string;
  Offering_ID?: string;
  List_Price?: number;
  Tier_Max_Discount_Pct?: number;
  Applied_Discount_Pct?: number;
  Unit_Net?: number;
  Floor_Price?: number;
  Margin_Pct_Line?: number;
  Below_Floor?: boolean;
  Line_Net?: number;
  Qty?: number;
}

const MARGIN_FLOOR = 15;

// Pricing waterfall — list → tier discount → applied discount →
// unit net → fees → line net → margin. Surfaces floor breaches and
// margin floor breaches inline.
export function PriceWaterfallWidget({ widget, data, loading }: Props) {
  const rows: WaterfallRow[] = (data?.rows as WaterfallRow[]) ?? [];

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
        ) : rows.length === 0 ? (
          <div className="flex items-center justify-center h-[220px] text-sm text-muted-foreground">
            Configure quote lines to see the pricing waterfall
          </div>
        ) : (
          <div className="space-y-3">
            {rows.map((r, i) => {
              const margin = Number(r.Margin_Pct_Line ?? 0);
              const belowFloor = Boolean(r.Below_Floor);
              const marginBreach = margin < MARGIN_FLOOR;
              const list = Number(r.List_Price ?? 0);
              const unit = Number(r.Unit_Net ?? 0);
              const widthPct = list > 0 ? Math.max(8, Math.min(100, (unit / list) * 100)) : 0;
              return (
                <div key={r.Line_ID || i} className="border rounded-md p-3 bg-card">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-muted-foreground">
                        {r.Line_ID}
                      </span>
                      <Badge variant="outline" className="text-xs">{r.Offering_ID}</Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      {marginBreach ? (
                        <Badge className="bg-destructive/10 text-destructive text-xs">
                          <TrendingDown className="h-3 w-3 mr-1" />Below floor
                        </Badge>
                      ) : (
                        <Badge className="bg-success/10 text-success text-xs">
                          <TrendingUp className="h-3 w-3 mr-1" />Healthy
                        </Badge>
                      )}
                      {belowFloor && (
                        <Badge className="bg-warning/10 text-warning text-xs">
                          Below price floor
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="h-3 bg-muted rounded-full overflow-hidden mb-2">
                    <div
                      className={`h-full ${marginBreach ? 'bg-destructive' : 'bg-success'}`}
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>
                  <div className="grid grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
                    <Step label="Qty" value={String(r.Qty ?? 0)} />
                    <Step label="List" value={`$${list.toFixed(2)}`} />
                    <Step label="Tier Max" value={`${(r.Tier_Max_Discount_Pct ?? 0).toFixed(1)}%`} />
                    <Step label="Applied" value={`${(r.Applied_Discount_Pct ?? 0).toFixed(1)}%`} />
                    <Step label="Unit Net" value={`$${unit.toFixed(2)}`} />
                    <Step label="Margin" value={`${margin.toFixed(1)}%`} highlight={marginBreach} />
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

function Step({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={`font-mono font-medium ${highlight ? 'text-destructive' : ''}`}>{value}</span>
    </div>
  );
}
