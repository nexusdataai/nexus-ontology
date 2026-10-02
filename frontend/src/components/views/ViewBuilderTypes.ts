import type { SimulatorRef, ViewTab } from '@/lib/foundry/model';

export interface DraftTab {
  tabId: string;
  label: string;
  icon?: string;
  dashboardId: string;
  simulatorRefs: SimulatorRef[];
  timeOverride?: { from?: string; to?: string } | null;
  /** marks tabs that have not been persisted to the backend yet */
  isNew?: boolean;
  /** marks tabs whose label/dashboard/simulatorRefs differ from the server */
  isDirty?: boolean;
}

export function tabsFromServer(serverTabs: ViewTab[]): DraftTab[] {
  return serverTabs.map((t) => ({
    tabId: t.tabId,
    label: t.label,
    icon: t.icon,
    dashboardId: t.dashboardId,
    simulatorRefs: t.simulatorRefs ? [...t.simulatorRefs] : [],
    timeOverride: t.timeOverride || null,
    isNew: false,
    isDirty: false,
  }));
}
