import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/services/apiClient';
import type { DashboardWidget } from '@/config/dashboardWidgets';
import { KPICardWidget } from './widgets/KPICardWidget';
import { BarChartWidget } from './widgets/BarChartWidget';
import { PieChartWidget } from './widgets/PieChartWidget';
import { LineChartWidget } from './widgets/LineChartWidget';
import { TableWidget } from './widgets/TableWidget';
import { AlertListWidget } from './widgets/AlertListWidget';
import { ConfigurationCanvasWidget } from './widgets/ConfigurationCanvasWidget';
import { PriceWaterfallWidget } from './widgets/PriceWaterfallWidget';
import { ApprovalTimelineWidget } from './widgets/ApprovalTimelineWidget';
import { DocumentPreviewWidget } from './widgets/DocumentPreviewWidget';
import { BidMatrixWidget } from './widgets/BidMatrixWidget';
import { ScenarioComparisonWidget } from './widgets/ScenarioComparisonWidget';
import { ContractDiffWidget } from './widgets/ContractDiffWidget';
import { ShouldCostWidget } from './widgets/ShouldCostWidget';

interface Props {
  appId: string;
  widgets: DashboardWidget[];
}

export function DashboardRenderer({ appId, widgets }: Props) {
  const [widgetData, setWidgetData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const kpiWidgetIds = new Set(widgets.filter(w => w.type === 'kpi_card').map(w => w.id));
    const alertWidgetIds = new Set(widgets.filter(w => w.type === 'alert_list').map(w => w.id));

    widgets.forEach(w => {
      if (!w.query.entity || (w.config as any).placeholder) return;
      setLoading(prev => ({ ...prev, [w.id]: true }));
    });

    apiClient.get(`/api/v1/apps/${appId}/dashboard`).then(dash => {
      const kpis = dash?.kpis || {};
      widgets.forEach(w => {
        if (kpiWidgetIds.has(w.id) && w.query.columns?.[0]) {
          const col = w.query.columns[0];
          const val = kpis[col];
          if (val !== undefined && val !== null) {
            setWidgetData(prev => ({ ...prev, [w.id]: { rows: [{ [col]: val }], total: 1, source: 's3' } }));
            setLoading(prev => ({ ...prev, [w.id]: false }));
          }
        }
      });
    }).catch(() => {});

    apiClient.get(`/api/v1/apps/${appId}/alerts`).then(alertData => {
      const alerts = alertData?.alerts || [];
      widgets.forEach(w => {
        if (alertWidgetIds.has(w.id) && alerts.length > 0) {
          setWidgetData(prev => ({
            ...prev,
            [w.id]: { rows: [{ alerts: JSON.stringify(alerts), total_alerts: alerts.length }], total: 1, source: 's3' },
          }));
          setLoading(prev => ({ ...prev, [w.id]: false }));
        }
      });
    }).catch(() => {});

    widgets.forEach(w => {
      if (!w.query.entity || (w.config as any).placeholder) return;
      fetchVdlWidget(w).then(resp => {
        setWidgetData(prev => {
          const existing = prev[w.id];
          if (existing?.source === 's3' && existing.total > 0) return prev;
          return { ...prev, [w.id]: resp };
        });
      }).catch(() => {
        setWidgetData(prev => {
          if (prev[w.id]?.total > 0) return prev;
          return { ...prev, [w.id]: { rows: [], total: 0, error: 'Query failed' } };
        });
      }).finally(() => {
        setLoading(prev => ({ ...prev, [w.id]: false }));
      });
    });
  }, [appId, widgets]);

  const fetchVdlWidget = async (w: DashboardWidget) => {
    return apiClient.post(`/api/v1/apps/${appId}/query`, {
      entity: w.query.entity,
      columns: w.query.columns,
      aggregation: w.query.aggregation,
      groupBy: w.query.groupBy,
      orderBy: w.query.orderBy,
      filters: w.query.filters,
      limit: w.query.limit ?? 100,
    });
  };

  const renderWidget = (w: DashboardWidget) => {
    const d = widgetData[w.id];
    const isLoading = loading[w.id] ?? true;

    switch (w.type) {
      case 'kpi_card':
        return <KPICardWidget widget={w} data={d} loading={isLoading} />;
      case 'bar_chart':
        return <BarChartWidget widget={w} data={d} loading={isLoading} />;
      case 'pie_chart':
        return <PieChartWidget widget={w} data={d} loading={isLoading} />;
      case 'line_chart':
        return <LineChartWidget widget={w} data={d} loading={isLoading} />;
      case 'table':
        return <TableWidget widget={w} data={d} loading={isLoading} />;
      case 'alert_list':
        return <AlertListWidget widget={w} data={d} loading={isLoading} />;
      case 'configuration_canvas':
        return <ConfigurationCanvasWidget widget={w} data={d} loading={isLoading} />;
      case 'price_waterfall':
        return <PriceWaterfallWidget widget={w} data={d} loading={isLoading} />;
      case 'approval_timeline':
        return <ApprovalTimelineWidget widget={w} data={d} loading={isLoading} />;
      case 'document_preview':
        return <DocumentPreviewWidget widget={w} data={d} loading={isLoading} />;
      case 'bid_matrix':
        return <BidMatrixWidget widget={w} data={d} loading={isLoading} />;
      case 'scenario_comparison':
        return <ScenarioComparisonWidget widget={w} data={d} loading={isLoading} />;
      case 'contract_diff':
        return <ContractDiffWidget widget={w} data={d} loading={isLoading} />;
      case 'should_cost':
        return <ShouldCostWidget widget={w} data={d} loading={isLoading} />;
      default:
        return null;
    }
  };

  const kpiWidgets = widgets.filter(w => w.type === 'kpi_card');
  const chartWidgets = widgets.filter(w => w.type !== 'kpi_card');

  return (
    <div className="space-y-6">
      {kpiWidgets.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {kpiWidgets.map(w => (
            <div key={w.id}>{renderWidget(w)}</div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-4 gap-4">
        {chartWidgets.map(w => (
          <div key={w.id} className={`col-span-${w.span || 2}`} style={{ gridColumn: `span ${w.span || 2}` }}>
            {renderWidget(w)}
          </div>
        ))}
      </div>
    </div>
  );
}
