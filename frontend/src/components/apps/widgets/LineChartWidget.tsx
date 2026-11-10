import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { DashboardWidget } from '@/config/dashboardWidgets';
import { ChartTooltip, CHART_MARGIN, AreaFill, axisProps, gridProps, lineProps, cursorLine, seriesColor } from '@/components/ds/charts';
import { WidgetFrame, labelOf, compact } from './WidgetFrame';

interface Props {
  widget: DashboardWidget;
  data: any;
  loading: boolean;
}

export function LineChartWidget({ widget, data, loading }: Props) {
  const { config } = widget;
  const xKey = (config.xKey as string) || 'name';
  const yKey = (config.yKey as string) || 'value';
  const rows = (data?.rows ?? []).map((r: any) => ({ ...r, [yKey]: Number(r[yKey] ?? 0) }));
  const last = rows.length ? rows[rows.length - 1][yKey] : null;
  const gid = `area-${widget.id}`;

  return (
    <WidgetFrame
      title={widget.title}
      description={`${labelOf(yKey)} over ${labelOf(xKey).toLowerCase()}`}
      aside={last !== null ? <span className="num text-lg font-medium text-foreground">{compact(last)}</span> : null}
      loading={loading}
      empty={rows.length === 0}
    >
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={rows} margin={CHART_MARGIN}>
          <defs><AreaFill id={gid} color={seriesColor(0)} /></defs>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey={xKey} {...axisProps} />
          <YAxis {...axisProps} width={44} tickFormatter={(v) => compact(Number(v), 0)} />
          <Tooltip content={<ChartTooltip valueFormatter={(v) => compact(Number(v))} />} cursor={cursorLine} />
          <Area dataKey={yKey} name={labelOf(yKey)} stroke={seriesColor(0)} fill={`url(#${gid})`} {...lineProps} />
        </AreaChart>
      </ResponsiveContainer>
    </WidgetFrame>
  );
}
