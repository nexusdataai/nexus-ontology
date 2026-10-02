import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { DashboardWidget } from '@/config/dashboardWidgets';

const DEFAULT_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b', '#ec4899', '#14b8a6'];

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

export function PieChartWidget({ widget, data, loading }: Props) {
  const { config, query } = widget;
  const colorMap = (config.colors as Record<string, string>) || {};
  const groupBy = query.groupBy || query.columns?.[0] || 'name';
  const valueKey = query.columns?.[1] || 'value';
  const rows: { name: string; value: number }[] = (data?.rows ?? []).map((r: any) => ({
    name: r[groupBy] || r.name || 'unknown',
    value: Number(r[valueKey] ?? r.value ?? 0),
  }));

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center h-[240px]"><Loader2 className="h-5 w-5 animate-spin" /></div>
        ) : rows.length === 0 ? (
          <div className="flex items-center justify-center h-[240px] text-sm text-muted-foreground">No data available</div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={rows} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {rows.map((entry, i) => (
                  <Cell key={i} fill={colorMap[entry.name] || DEFAULT_COLORS[i % DEFAULT_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ fontSize: 11 }} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
