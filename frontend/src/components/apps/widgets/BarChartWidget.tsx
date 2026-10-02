import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { DashboardWidget } from '@/config/dashboardWidgets';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

export function BarChartWidget({ widget, data, loading }: Props) {
  const { config } = widget;
  const xKey = (config.xKey as string) || 'name';
  const yKey = (config.yKey as string) || 'value';
  const color = (config.color as string) || '#3b82f6';

  const rows = data?.rows ?? [];

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center h-[220px]"><Loader2 className="h-5 w-5 animate-spin" /></div>
        ) : rows.length === 0 ? (
          <div className="flex items-center justify-center h-[220px] text-sm text-muted-foreground">No data available</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={rows} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey={xKey} tick={{ fontSize: 9 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10 }} width={45} />
              <Tooltip contentStyle={{ fontSize: 11 }} />
              <Bar dataKey={yKey} fill={color} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
