/**
 * Shared types for the registry-browser building blocks.
 *
 * Two new tabs under the Reasoning page browse:
 *   - the ReAct tool catalogue (code-defined + DynamoDB-authored)
 *   - the Connector API catalogue (oracle / sap / sfdc / external)
 *
 * Both panels are thin compositions over RegistryTable / StatsTiles /
 * FacetFilters / DetailDrawer / ExecuteDrawer. The types here describe
 * the generic descriptor shape each panel hands in -- the components
 * themselves stay agnostic to the underlying row type.
 */

import type { ReactNode } from 'react';

// ---------------------------------------------------------------------------
// RegistryTable
// ---------------------------------------------------------------------------

export interface RegistryColumn<T> {
  key: string;
  label: string;
  /** Narrow column on the right (mono / numeric / chip etc.) */
  className?: string;
  /** Header cell tailwind classes (rarely needed). */
  headerClassName?: string;
  /** Body cell renderer */
  render: (row: T) => ReactNode;
  /** Optional sort accessor; when omitted the column is not sortable. */
  sortBy?: (row: T) => string | number | boolean | null | undefined;
}

// ---------------------------------------------------------------------------
// StatsTiles
// ---------------------------------------------------------------------------

export type StatTone = 'ok' | 'warn' | 'err' | 'muted';

export interface StatBreakdown {
  label: string;
  value: number | string;
  tone?: StatTone;
}

export interface StatTile {
  title: string;
  value: number | string;
  tone?: StatTone;
  hint?: string;
  /** Optional inline mini-breakdown chips (count + label). */
  breakdown?: StatBreakdown[];
}

// ---------------------------------------------------------------------------
// FacetFilters
// ---------------------------------------------------------------------------

export interface FacetOption {
  value: string;
  label?: string;
  count?: number;
}

export interface FacetDescriptor {
  key: string;
  label: string;
  options: FacetOption[];
}

/** Map of facet key -> set of selected option values. */
export type FacetState = Record<string, Set<string>>;

// ---------------------------------------------------------------------------
// DetailDrawer
// ---------------------------------------------------------------------------

export interface DetailDrawerTab<T> {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
}

export interface DetailBadge {
  label: string;
  tone?: StatTone | 'info';
  title?: string;
}

// ---------------------------------------------------------------------------
// ExecuteDrawer
// ---------------------------------------------------------------------------

export interface ExecuteResultEnvelope {
  status: 'pass' | 'fail' | 'skip' | string;
  duration_ms?: number;
  result?: unknown;
  result_preview?: string;
  error?: string;
  /** Extra blocks the per-kind adapter wants to surface (audit / verification etc.) */
  extras?: Record<string, unknown>;
}

export interface ExecuteAdapter {
  kind: 'tool' | 'connector_api';
  id: string;
  displayName: string;
  /** JSON-Schema-shaped object for hint rendering above the payload editor. */
  paramsSchema?: Record<string, any> | null;
  /** Pre-filled payload (canary). */
  defaultParams?: Record<string, any>;
  /** Optional risk pill */
  riskLevel?: string;
  /** Optional connector_api id for tool kind. */
  connectorApi?: string | null;
  /** Run the action; must return an envelope. */
  run: (params: Record<string, any>) => Promise<ExecuteResultEnvelope>;
}
