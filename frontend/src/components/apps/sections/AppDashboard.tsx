import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import type { AppConfig } from '@/config/appRegistry';
import { getWidgetsForApp } from '@/config/dashboardWidgets';
import { DashboardRenderer } from '../DashboardRenderer';

interface Props {
  app: AppConfig;
}

export function AppDashboard({ app }: Props) {
  const [liveData, setLiveData] = useState<Record<string, any>>({});
  const [liveLoading, setLiveLoading] = useState(true);

  const widgets = getWidgetsForApp(app.id);
  const hasRealWidgets = widgets.some(w => w.query.entity && !(w.config as any).placeholder);

  useEffect(() => {
    setLiveLoading(true);
    Promise.all(
      app.entities.slice(0, 4).map(e =>
        apiClient.get(`/api/v1/apps/${app.id}/live/${e}?limit=5`)
          .then(d => ({ entity: e, data: d }))
          .catch(() => ({ entity: e, data: null }))
      )
    ).then(results => {
      const map: Record<string, any> = {};
      for (const r of results) if (r.data) map[r.entity] = r.data;
      setLiveData(map);
    }).finally(() => setLiveLoading(false));
  }, [app.id]);

  return (
    <div className="p-6 space-y-6">
      {hasRealWidgets ? (
        <DashboardRenderer appId={app.id} widgets={widgets} />
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {app.kpis.map(kpi => (
            <Card key={kpi.label}>
              <CardContent className="pt-4">
                <p className="text-[10px] text-muted-foreground uppercase">{kpi.label}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-2xl font-bold">--</span>
                  <Badge variant="outline" className="text-[9px]">Target: {kpi.target}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
          <div className="col-span-full text-center py-10 text-sm text-muted-foreground">
            Dashboard widgets will be available once AI automation journeys produce result data.
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {app.entities.slice(0, 4).map(entity => {
          const live = liveData[entity];
          const count = live?.total || live?.rows?.length || 0;
          return (
            <Card key={entity}>
              <CardContent className="pt-3 pb-3">
                <p className="text-[10px] text-muted-foreground">{entity}</p>
                <p className="text-lg font-bold">
                  {liveLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin inline" />
                  ) : (
                    <>{count.toLocaleString()} <span className="text-xs font-normal text-muted-foreground">records</span></>
                  )}
                </p>
                <Badge variant="outline" className="text-[8px] mt-1">Live from VDL</Badge>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
