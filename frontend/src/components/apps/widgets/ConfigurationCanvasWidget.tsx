import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Boxes, Package } from 'lucide-react';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

// Configuration canvas visualizes the offerings and components on a quote
// (or candidate set) as a draggable card grid. v1 renders a compact grid;
// drag handlers are wired in a follow-up sprint.
export function ConfigurationCanvasWidget({ widget, data, loading }: Props) {
  const rows: any[] = data?.rows ?? [];

  return (
    <Card className="h-full">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2">
          <Boxes className="h-4 w-4 text-primary" />
          {widget.title} ({rows.length})
        </CardTitle>
        <Badge variant="outline" className="text-xs">Drag-ready</Badge>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center h-[220px]">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : rows.length === 0 ? (
          <div className="flex items-center justify-center h-[220px] text-sm text-muted-foreground">
            No offerings configured
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            {rows.slice(0, 12).map((row, i) => (
              <div
                key={row.Offering_ID || row.offering_id || i}
                className="border rounded-md p-3 hover:shadow-sm transition-shadow cursor-grab bg-card"
                draggable
              >
                <div className="flex items-center gap-2 mb-2">
                  <Package className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs font-mono">{row.Offering_ID || row.offering_id}</span>
                </div>
                <div className="text-sm font-medium truncate" title={row.Name || row.name}>
                  {row.Name || row.name}
                </div>
                <div className="flex gap-1 mt-2 flex-wrap">
                  {row.Type && (
                    <Badge variant="secondary" className="text-xs">{row.Type}</Badge>
                  )}
                  {(row.Channel_Eligibility || '')
                    .split(',')
                    .filter(Boolean)
                    .slice(0, 2)
                    .map((c: string) => (
                      <Badge key={c} className="text-xs bg-primary/10 text-primary">
                        {c.trim()}
                      </Badge>
                    ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
