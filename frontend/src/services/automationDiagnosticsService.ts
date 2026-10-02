import { apiClient } from './apiClient';

export type AutomationOverall = 'healthy' | 'degraded' | 'unhealthy';
export type UseCaseStatus = 'pass' | 'warn' | 'fail';

export interface AutomationUseCaseRow {
  use_case_id: string;
  title: string;
  solution_id: string;
  status: UseCaseStatus;
  yaml_file: string;
  stage_count: number;
  step_count: number;
  binding_count: number;
  tool_refs: string[];
  connector_api_refs: string[];
  missing_tools: string[];
  missing_connector_apis: string[];
  high_risk_steps: number;
  tags: string[];
  kpi_impact: string[];
}

export interface AutomationDryRunReport {
  yaml_root: string;
  files_seen: number;
  validated: number;
  validation_errors: number;
  use_cases: AutomationUseCaseRow[];
  errors: { file: string; error: string }[];
  totals: {
    use_cases: number;
    stages: number;
    steps: number;
    tool_bindings: number;
    connector_apis: number;
    high_risk_steps: number;
    missing_tools: number;
    missing_connector_apis: number;
  };
  overall: AutomationOverall;
  registry: {
    known_tools: string[];
    known_connector_apis: string[];
  };
}

// ---------------------------------------------------------------------------
// Phase 2 - Tool Catalogue, Saved Journeys, Copilot Runtime, Smoke Test
// ---------------------------------------------------------------------------

export interface ToolCatalogueRow {
  tool_id: string;
  display_name: string;
  group: string;
  risk_level: string;
  requires_approval: boolean;
  connector_api: string | null;
  consumes_count: number;
  produces_count: number;
  tags: string[];
  registered: boolean;
  yaml_present: boolean;
  example_invocation: boolean;
}

export interface ToolCatalogueReport {
  totals: {
    yaml_tools: number;
    registered_tools: number;
    yaml_only_orphans: number;
    registry_only_orphans: number;
    groups: Record<string, number>;
  };
  metadata_quality: {
    with_consumes_entities: number;
    with_produces_entities: number;
    with_connector_api: number;
    with_example_invocation: number;
    with_tags: number;
  };
  risk_distribution: {
    read_only: number;
    low_risk_write: number;
    high_risk_write: number;
  };
  yaml_only_orphans: string[];
  registry_only_orphans: string[];
  tools: ToolCatalogueRow[];
  errors: { file?: string; phase?: string; error: string }[];
  tools_yaml_root: string;
  overall: AutomationOverall;
}

export interface SavedJourneyRecent {
  journey_id: string;
  title: string | null;
  kind: string;
  solution_id: string | null;
  createdBy: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  step_count: number;
  validation_ok: boolean;
}

export interface SavedJourneyBroken {
  journey_id: string;
  title: string | null;
  kind: string;
  solution_id: string;
  missing_tools: string[];
  missing_connector_apis: string[];
}

export interface SavedJourneysReport {
  total: number;
  by_kind: Record<string, number>;
  by_solution: Record<string, number>;
  broken_journeys: SavedJourneyBroken[];
  recent: SavedJourneyRecent[];
  overall: AutomationOverall | 'unknown';
  source?: string;
  error?: string;
}

export interface CopilotRuntimeReport {
  session_store: {
    mode: 'pg' | 'memory' | 'unknown';
    recent_count: number;
    by_status: Record<string, number>;
    stuck_awaiting_approval_24h: number;
  };
  vector_index: Record<string, number>;
  knowledge_graph: {
    age_available: boolean;
    uses_metadata_fallback: boolean;
  };
  tool_registry_size: number;
  connector_api_registry_size: number;
  overall: AutomationOverall;
}

export interface SmokeStage {
  name: string;
  status: 'pass' | 'fail' | 'skip';
  duration_ms: number;
  detail?: Record<string, any>;
}

export interface SmokeTestReport {
  overall: AutomationOverall;
  goal: string;
  stages: SmokeStage[];
  session_id: string | null;
  journey_id: string | null;
}

export interface GraphIntegrityReport {
  use_cases_checked: number;
  missing_tools: number;
  missing_connector_apis: number;
  broken_edges: { use_case_id: string; type: string; missing_target: string }[];
  orphan_registry_tools: string[];
  overall: string;
  source?: string;
}

export const automationDiagnosticsService = {
  status: () =>
    apiClient.get<AutomationDryRunReport>('/api/v1/diagnostics/automation'),

  dryRun: () =>
    apiClient.post<AutomationDryRunReport>('/api/v1/diagnostics/automation/dry-run', {}),

  toolCatalogue: () =>
    apiClient.get<ToolCatalogueReport>('/api/v1/diagnostics/automation/tool-catalogue'),

  savedJourneys: () =>
    apiClient.get<SavedJourneysReport>('/api/v1/diagnostics/automation/saved-journeys'),

  copilotRuntime: () =>
    apiClient.get<CopilotRuntimeReport>('/api/v1/diagnostics/automation/copilot-runtime'),

  graphIntegrity: () =>
    apiClient.get<GraphIntegrityReport>('/api/v1/diagnostics/automation/graph-integrity'),

  smokeTest: (goal?: string, name?: string) =>
    apiClient.post<SmokeTestReport>(
      '/api/v1/diagnostics/automation/smoke-test',
      { goal, name },
      { timeout: 600000 },
    ),
};
