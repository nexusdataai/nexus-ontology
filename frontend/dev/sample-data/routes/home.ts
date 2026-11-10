/**
 * Home page and calls every page shares.
 * (The journey list the home page also reads lives in automation.ts.)
 */
import { type SampleRoute, ENTITIES, MAPPING_RULES, TOOLS, ago } from '../fixtures';

const mapped = ENTITIES.filter(e => e.fdwMappingStatus === 'mapped').length;
const virtualOnly = ENTITIES.filter(e => e.fdwMappingStatus === 'virtual').length;
const unmapped = ENTITIES.filter(e => e.fdwMappingStatus === 'unmapped').length;

/** Platform-wide counters. Read by Home and by Control Plane > Semantic layer. */
export const controlPlaneStats = () => ({
  onto_schema: 86,
  onto_policy: 14,
  onto_workflow: 23,
  onto_integration: 9,
  graph_nodes: 412,
  graph_edges: 1287,
  total_embeddings: 5630,
  embedding_service: 'healthy',
  embedding_available: true,
  fdw_tables: 71,
  tools_count: 47,
  virtual_entities: 86,
  mapped_entities: 71,
  virtual_only_entities: 9,
  unmapped_entities: 6,
  mapping_rules_total: 131,
  mapping_rules_active: 118,
  // Keys are the system names the backend uses; Home turns them into labels.
  entities_by_system: { SAP: 31, Salesforce: 22, Oracle: 18, Google_Drive: 6, Social_Listening: 5, File_Uploads: 4 },
  simulator_status: {
    sfdc: { loaded: true, tables: 22, rows: 48210 },
    oracle: { loaded: true, tables: 18, rows: 131540 },
    sap: { loaded: true, tables: 31, rows: 96875 },
  },
  // Counts of the sample catalogue itself, for reference.
  sample_catalogue: { entities: ENTITIES.length, mapped, virtual_only: virtualOnly, unmapped, mapping_rules: MAPPING_RULES.length, tools: TOOLS.length },
  last_indexed_at: ago(380),
});

export const homeRoutes: SampleRoute[] = [
  {
    method: 'GET',
    path: '/api/v1/config/simulator',
    handle: () => ({ enabled: true, baseUrl: '', uiUrl: 'http://localhost:8082' }),
  },
  {
    method: 'GET',
    path: '/api/v1/control-plane/stats',
    handle: () => controlPlaneStats(),
  },
  { method: 'GET', path: '/api/v1/health', handle: () => ({ status: 'healthy', version: '2.8.1', timestamp: ago(0) }) },
  { method: 'GET', path: '/health', handle: () => ({ status: 'healthy' }) },
];
