import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2 } from 'lucide-react';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

// Vendor × line bid matrix. Each row is a Vendor_Quote_Line; columns
// show price, lead time, MOQ, payment terms, and compliance flags.
export function BidMatrixWidget({ widget, data, loading }: Props) {
  const rows: any[] = data?.rows ?? [];
  const columns = [
    'Vendor_Quote_ID', 'RFx_Line_ID', 'Unit_Price', 'Lead_Time_Days',
    'MOQ', 'Payment_Terms', 'Compliance_Flags',
  ];

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{widget.title} ({rows.length})</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="flex items-center justify-center h-[260px]">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : rows.length === 0 ? (
          <div className="flex items-center justify-center h-[260px] text-sm text-muted-foreground">
            No vendor bids submitted yet
          </div>
        ) : (
          <ScrollArea className="h-[340px]">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-muted/30 sticky top-0 z-10">
                  {columns.map(col => (
                    <th key={col} className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">
                      {col.replace(/_/g, ' ')}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {rows.map((row, i) => (
                  <tr key={i} className="hover:bg-muted/20">
                    {columns.map(col => {
                      const v = row[col];
                      if (col === 'Unit_Price') {
                        const num = Number(v);
                        return (
                          <td key={col} className="px-3 py-1.5 font-mono">
                            {isFinite(num) ? `$${num.toFixed(2)}` : String(v ?? '')}
                          </td>
                        );
                      }
                      if (col === 'Compliance_Flags') {
                        const flags = String(v ?? '').split(',').filter(Boolean);
                        return (
                          <td key={col} className="px-3 py-1.5">
                            <div className="flex gap-1 flex-wrap">
                              {flags.slice(0, 3).map((f) => (
                                <Badge key={f} className="text-xs bg-primary/10 text-primary">
                                  {f.trim()}
                                </Badge>
                              ))}
                            </div>
                          </td>
                        );
                      }
                      return (
                        <td key={col} className="px-3 py-1.5 font-mono max-w-[180px] truncate">
                          {String(v ?? '')}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
