import { useEffect, useMemo, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { dashboardService, type DashboardListItem } from '@/services/dashboardService';
import type { DraftTab } from './ViewBuilderTypes';
import type { SimulatorRef } from '@/lib/foundry/model';

interface TabInspectorProps {
  tab: DraftTab | null;
  onChange: (next: DraftTab) => void;
  onRemove: () => void;
}

export function TabInspector({ tab, onChange, onRemove }: TabInspectorProps) {
  const [dashboards, setDashboards] = useState<DashboardListItem[]>([]);

  useEffect(() => {
    dashboardService
      .list()
      .then(setDashboards)
      .catch(() => undefined);
  }, []);

  const dashboardOptions = useMemo(() => dashboards, [dashboards]);

  if (!tab) {
    return (
      <div className="h-full flex items-center justify-center p-4 text-xs text-muted-foreground border-l">
        Select a tab to edit, or drag a dashboard from the palette to add one.
      </div>
    );
  }

  const update = (patch: Partial<DraftTab>) => {
    onChange({ ...tab, ...patch, isDirty: true });
  };

  const updateSimRef = (idx: number, patch: Partial<SimulatorRef>) => {
    const next = tab.simulatorRefs.map((r, i) => (i === idx ? { ...r, ...patch } : r));
    update({ simulatorRefs: next });
  };

  const removeSimRef = (idx: number) => {
    const next = tab.simulatorRefs.filter((_, i) => i !== idx);
    update({ simulatorRefs: next });
  };

  const addSimRef = () => {
    update({ simulatorRefs: [...tab.simulatorRefs, { service: '' }] });
  };

  return (
    <div className="h-full flex flex-col border-l bg-background overflow-auto">
      <div className="px-3 pt-3 pb-2 border-b flex items-center justify-between">
        <div className="text-xs font-semibold text-muted-foreground">
          Tab settings
        </div>
        <Button variant="ghost" size="sm" className="h-6 px-2 text-destructive" onClick={onRemove}>
          <Trash2 className="h-3 w-3 mr-1" /> Remove
        </Button>
      </div>

      <div className="p-3 space-y-3 text-xs">
        <div>
          <label className="block text-xs text-muted-foreground mb-1">
            Label
          </label>
          <Input
            value={tab.label}
            onChange={(e) => update({ label: e.target.value })}
            className="h-7 text-xs"
          />
        </div>

        <div>
          <label className="block text-xs text-muted-foreground mb-1">
            Dashboard
          </label>
          <select
            value={tab.dashboardId}
            onChange={(e) => update({ dashboardId: e.target.value })}
            className="w-full h-7 rounded-md border border-input bg-background px-2 text-xs"
          >
            <option value="">Select a dashboard...</option>
            {dashboardOptions.map((d) => (
              <option key={d.uid} value={d.uid}>
                {d.title}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-muted-foreground mb-1">
            Time override
          </label>
          <div className="grid grid-cols-2 gap-2">
            <Input
              placeholder="from (e.g. now-24h)"
              value={tab.timeOverride?.from || ''}
              onChange={(e) =>
                update({
                  timeOverride: { ...(tab.timeOverride || {}), from: e.target.value || undefined },
                })
              }
              className="h-7 text-xs"
            />
            <Input
              placeholder="to (e.g. now)"
              value={tab.timeOverride?.to || ''}
              onChange={(e) =>
                update({
                  timeOverride: { ...(tab.timeOverride || {}), to: e.target.value || undefined },
                })
              }
              className="h-7 text-xs"
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs text-muted-foreground">
              Simulator data refs
            </label>
            <Button variant="ghost" size="sm" className="h-6 px-2" onClick={addSimRef}>
              <Plus className="h-3 w-3 mr-1" /> Add
            </Button>
          </div>
          {tab.simulatorRefs.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Optional. Reference simulator datasets stored in S3 to scope the dashboard's data.
            </p>
          ) : (
            <div className="space-y-2">
              {tab.simulatorRefs.map((ref, idx) => (
                <div key={idx} className="border rounded-md p-2 space-y-1.5">
                  <div className="flex items-center gap-1">
                    <Input
                      placeholder="service (sfdc, oracle, sap, external...)"
                      value={ref.service}
                      onChange={(e) => updateSimRef(idx, { service: e.target.value })}
                      className="h-6 text-xs"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 text-destructive shrink-0"
                      onClick={() => removeSimRef(idx)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                  <Input
                    placeholder="scenario (optional)"
                    value={ref.scenario || ''}
                    onChange={(e) => updateSimRef(idx, { scenario: e.target.value })}
                    className="h-6 text-xs"
                  />
                  <Input
                    placeholder="s3 key / manifest path"
                    value={ref.s3Key || ''}
                    onChange={(e) => updateSimRef(idx, { s3Key: e.target.value })}
                    className="h-6 text-xs"
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TabInspector;
