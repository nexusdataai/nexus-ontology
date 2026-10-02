/**
 * Journey KPI Catalog (frontend)
 *
 * Mirror of `nexus-backend/src/services/journey_kpi_catalog.py`. The backend is
 * the source of truth and also returns `kpi_definition` on `GET /journeys/{id}`,
 * but having the catalog here lets the JSX render lucide icons by string name
 * without an extra round-trip and keeps the Studio header rendering consistent
 * even when an older backend doesn't yet send `kpi_definition`.
 */

import {
  Activity,
  AlertTriangle,
  Boxes,
  Factory,
  FileBarChart,
  Leaf,
  Phone,
  ShoppingCart,
  TrendingUp,
  Users,
  type LucideIcon,
} from 'lucide-react';

export interface KpiPrimary {
  label: string;
  icon: string;
  color: string;
}

export interface KpiDefinition {
  primary: KpiPrimary;
}

export const KPI_CATALOG: Record<string, KpiDefinition> = {
  'order-to-cash':            { primary: { label: 'Orders Processed',       icon: 'ShoppingCart',  color: 'green'   } },
  'demand-forecasting':       { primary: { label: 'Forecasts Generated',    icon: 'TrendingUp',    color: 'blue'    } },
  'inventory-optimization':   { primary: { label: 'SKUs Optimized',         icon: 'Boxes',         color: 'purple'  } },
  'procurement-analytics':    { primary: { label: 'POs Analyzed',           icon: 'FileBarChart',  color: 'amber'   } },
  'production-quality':       { primary: { label: 'Production Runs Scored', icon: 'Factory',       color: 'indigo'  } },
  'supply-chain-risk':        { primary: { label: 'Vendors Risk-Scored',    icon: 'AlertTriangle', color: 'red'     } },
  'customer-360':             { primary: { label: 'Accounts Analyzed',      icon: 'Users',         color: 'cyan'    } },
  'esg-sustainability':       { primary: { label: 'ESG Plants Analyzed',    icon: 'Leaf',          color: 'emerald' } },
  'call-processing':          { primary: { label: 'Calls Processed',        icon: 'Phone',         color: 'sky'     } },
  '_default':                 { primary: { label: 'Items Processed',        icon: 'Activity',      color: 'slate'   } },
};

export const ICON_MAP: Record<string, LucideIcon> = {
  Activity,
  AlertTriangle,
  Boxes,
  Factory,
  FileBarChart,
  Leaf,
  Phone,
  ShoppingCart,
  TrendingUp,
  Users,
};

/**
 * Resolve a KPI definition for a journey's solution_id, falling back to the
 * `_default` row when the id is empty or unknown.
 */
export function getKpiDefinition(solutionId?: string | null): KpiDefinition {
  if (!solutionId) return KPI_CATALOG._default;
  return KPI_CATALOG[solutionId] ?? KPI_CATALOG._default;
}

/**
 * Resolve the lucide icon component for a KPI primary by its string name.
 */
export function getKpiIcon(iconName?: string | null): LucideIcon {
  if (!iconName) return Activity;
  return ICON_MAP[iconName] ?? Activity;
}
