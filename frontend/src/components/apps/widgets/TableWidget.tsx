import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  matched: 'bg-green-500/10 text-green-700',
  quantity_mismatch: 'bg-amber-500/10 text-amber-700',
  price_mismatch: 'bg-red-500/10 text-red-700',
  missing_delivery: 'bg-violet-500/10 text-violet-700',
  missing_invoice: 'bg-slate-500/10 text-slate-700',
};

export function TableWidget({ widget, data, loading }: Props) {
  const rows: any[] = data?.rows ?? [];
  const columns = widget.query.columns ?? (rows.length > 0 ? Object.keys(rows[0]).slice(0, 8) : []);

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{widget.title} ({rows.length})</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="flex items-center justify-center h-[200px]"><Loader2 className="h-5 w-5 animate-spin" /></div>
        ) : rows.length === 0 ? (
          <div className="flex items-center justify-center h-[200px] text-sm text-muted-foreground">No data available</div>
        ) : (
          <ScrollArea className="h-[300px]">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-muted/30 sticky top-0 z-10">
                  {columns.map(col => (
                    <th key={col} className="px-3 py-2 text-left font-medium text-muted-foreground">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {rows.map((row, i) => (
                  <tr key={i} className="hover:bg-muted/20">
                    {columns.map(col => {
                      const v = row[col];
                      const statusClass = col === 'match_status' ? STATUS_COLORS[v] : '';
                      return (
                        <td key={col} className="px-3 py-1.5 font-mono max-w-[180px] truncate">
                          {statusClass ? <Badge className={`${statusClass} text-[9px]`}>{v}</Badge> : String(v ?? '')}
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
