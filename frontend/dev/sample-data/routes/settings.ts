/**
 * Settings and user management: licence, users, roles and permissions,
 * system parameters, secrets, log level, Google Drive connector settings.
 * Secret values are never returned, only masked placeholders.
 */
import { type SampleRoute, SYSTEMS, PEOPLE, COMPANY, ADMIN_EMAIL, ago, ahead, asObj, pad, emailOf, HOUR, DAY } from '../fixtures';

// ---------------------------------------------------------------------------
// Licence
// ---------------------------------------------------------------------------

const LICENSE_ID = 'LIC-ENT-2026-004417';

const licenseStatus = () => ({
  license_status: 'active',
  license_id: LICENSE_ID,
  tier: 'enterprise',
  holder_name: COMPANY,
  activated_at: ago(DAY * 311),
  expires_at: ahead(DAY * 54),
  days_remaining: 54,
  is_expiring_soon: true,
  expiration_warning: 'This licence expires in 54 days. Renew it to avoid a grace period.',
  features: ['data_plane', 'control_plane', 'reasoning', 'ai_automation', 'ai_analytics', 'ai_ops', 'sso', 'audit_export', 'custom_tools'],
  grace_period: { is_in_grace_period: false, grace_period_ends_at: null, days_remaining: null, restrictions: [] },
  usage_stats: { users: 12, journeys: 6, data_sources: 6, dashboards: 6, agent_sessions_30d: 4812, tools: 47 },
  message: null,
  activation_instructions: null,
});

const licenseAudit = () => {
  const events: [string, 'success' | 'failure', Record<string, unknown>][] = [
    ['license_validated', 'success', { source: 'scheduled check' }],
    ['feature_access_granted', 'success', { feature_id: 'custom_tools' }],
    ['license_validated', 'success', { source: 'scheduled check' }],
    ['feature_access_denied', 'failure', { feature_id: 'multi_region', required_tier: 'enterprise_plus' }],
    ['license_validated', 'success', { source: 'sign-in' }],
    ['license_validation_failed', 'failure', { reason: 'Licence server did not respond; cached result used' }],
    ['license_validated', 'success', { source: 'scheduled check' }],
    ['feature_access_granted', 'success', { feature_id: 'audit_export' }],
    ['license_renewed', 'success', { previous_expiration: ago(DAY * 311).slice(0, 10), tier: 'enterprise' }],
    ['grace_period_ended', 'success', { reason: 'Licence renewed' }],
    ['grace_period_started', 'success', { days: 14 }],
    ['license_expired', 'failure', { tier: 'professional' }],
    ['license_activated', 'success', { tier: 'professional' }],
  ];
  const offsets = [22, HOUR * 3, HOUR * 24, HOUR * 31, HOUR * 48, HOUR * 71, HOUR * 72, DAY * 9, DAY * 311, DAY * 311, DAY * 318, DAY * 318, DAY * 683];
  return events.map(([event_type, result, details], i) => ({
    event_id: `lev-${pad(9412 - i, 6)}`,
    timestamp: ago(offsets[i]),
    event_type,
    license_id: LICENSE_ID,
    details,
    result,
    ip_address: i % 3 === 0 ? '10.24.8.17' : '10.24.8.41',
    user_agent: i % 2 === 0 ? 'nexus-backend/2.8.1' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/141.0',
  }));
};

// ---------------------------------------------------------------------------
// Users and roles
// ---------------------------------------------------------------------------

const USERS = PEOPLE.map((name, i) => ({
  sub: `c3a1f0e2-7b4d-4c1a-9e${pad(10 + i, 2)}-5d2f8a6b${pad(1000 + i * 37, 4)}`,
  email: emailOf(name),
  name,
  status: i === 7 ? 'FORCE_CHANGE_PASSWORD' : i === 9 ? 'UNCONFIRMED' : 'CONFIRMED',
  enabled: i !== 6,
  groups: [['Admin', 'Executive', 'SalesManager', 'Rep', 'SalesManager', 'Rep', 'Rep', 'Rep', 'Executive', 'Rep'][i]],
  role: ['Admin', 'Executive', 'SalesManager', 'Rep', 'SalesManager', 'Rep', 'Rep', 'Rep', 'Executive', 'Rep'][i],
  mfa_enabled: i < 5 || i === 8,
  created: ago(DAY * (320 - i * 29)),
  last_modified: ago(HOUR * (4 + i * 53)),
}));

const ROLES = [
  { id: 'admin', name: 'Admin', displayName: 'Administrator', description: 'Full access, including users, licence and secrets.', level: 100, badgeColor: 'bg-destructive/20 text-destructive' },
  { id: 'executive', name: 'Executive', displayName: 'Executive', description: 'Reads every dashboard and report. Approves high-risk actions.', level: 80, badgeColor: 'bg-primary/20 text-primary' },
  { id: 'sales_manager', name: 'SalesManager', displayName: 'Manager', description: 'Runs journeys and approves actions for their team.', level: 60, badgeColor: 'bg-warning/20 text-warning' },
  { id: 'rep', name: 'Rep', displayName: 'Analyst', description: 'Reads data and dashboards, asks the Copilot.', level: 20, badgeColor: 'bg-success/20 text-success' },
];
const CATEGORIES = [
  { id: 'data', name: 'Data', description: 'Sources, virtual entities and mapping rules', icon: '🗄️', order: 1 },
  { id: 'knowledge', name: 'Knowledge', description: 'Policies, workflows and integrations', icon: '📚', order: 2 },
  { id: 'automation', name: 'Automation', description: 'Journeys, schedules and tools', icon: '⚙️', order: 3 },
  { id: 'analytics', name: 'Analytics', description: 'Dashboards, views and solutions', icon: '📊', order: 4 },
  { id: 'administration', name: 'Administration', description: 'Users, licence, settings and secrets', icon: '🔐', order: 5 },
];
type Perm = [id: string, displayName: string, description: string, category: string, risk: 'low' | 'medium' | 'high' | 'critical', scope: 'individual' | 'team' | 'organization', minLevel: number];
const PERMS: Perm[] = [
  ['data.read', 'Read data', 'Browse sources and query virtual entities', 'data', 'low', 'organization', 20],
  ['data.sources.manage', 'Manage data sources', 'Add, edit and remove data sources', 'data', 'high', 'organization', 100],
  ['data.mapping.edit', 'Edit mapping rules', 'Create and change mapping rules', 'data', 'medium', 'organization', 60],
  ['knowledge.read', 'Read knowledge', 'Browse the knowledge index and graph', 'knowledge', 'low', 'organization', 20],
  ['knowledge.edit', 'Edit knowledge', 'Edit policies, workflows and integrations', 'knowledge', 'medium', 'organization', 60],
  ['knowledge.reindex', 'Rebuild the index', 'Run the Knowledge Processor', 'knowledge', 'medium', 'organization', 80],
  ['automation.copilot', 'Use the Copilot', 'Ask questions and plan journeys', 'automation', 'low', 'individual', 20],
  ['automation.run', 'Run journeys', 'Start, pause and cancel journeys', 'automation', 'medium', 'team', 60],
  ['automation.schedule', 'Schedule journeys', 'Create and change schedules', 'automation', 'medium', 'team', 60],
  ['automation.approve', 'Approve high-risk steps', 'Approve writes to source systems', 'automation', 'critical', 'organization', 80],
  ['automation.tools.edit', 'Edit tools', 'Create and change tools in the tool builder', 'automation', 'high', 'organization', 100],
  ['analytics.read', 'Read dashboards', 'Open dashboards, views and solutions', 'analytics', 'low', 'organization', 20],
  ['analytics.edit', 'Edit dashboards', 'Create and change dashboards and views', 'analytics', 'low', 'team', 60],
  ['admin.users', 'Manage users', 'Invite, disable and remove users', 'administration', 'high', 'organization', 100],
  ['admin.roles', 'Manage roles', 'Change role permissions', 'administration', 'critical', 'organization', 100],
  ['admin.settings', 'Manage settings', 'Change system parameters and log level', 'administration', 'high', 'organization', 100],
  ['admin.secrets', 'Manage secrets', 'Rotate connector credentials', 'administration', 'critical', 'organization', 100],
  ['admin.diagnostics', 'Run diagnostics', 'Run diagnostics and read platform health', 'administration', 'low', 'organization', 60],
];

const rbacAudit = () => [
  { action: 'permission_granted', userId: ADMIN_EMAIL, roleId: 'sales_manager', permissionId: 'automation.schedule', changes: 'Managers can now schedule journeys', version: '1.4.0', min: HOUR * 26 },
  { action: 'permission_revoked', userId: ADMIN_EMAIL, roleId: 'rep', permissionId: 'analytics.edit', changes: 'Analysts can no longer edit shared dashboards', version: '1.3.2', min: DAY * 6 },
  { action: 'role_updated', userId: emailOf(PEOPLE[1]), roleId: 'executive', changes: 'Description updated', version: '1.3.1', min: DAY * 19 },
  { action: 'permission_granted', userId: ADMIN_EMAIL, roleId: 'executive', permissionId: 'automation.approve', changes: 'Executives can approve high-risk steps', version: '1.3.0', min: DAY * 41 },
  { action: 'config_initialised', userId: 'system', changes: 'Default roles and permissions created', version: '1.0.0', min: DAY * 320 },
].map(({ min, ...entry }) => ({ ...entry, timestamp: ago(min) }));

const rbacConfig = () => ({
  metadata: { version: '1.4.0', lastUpdated: ago(HOUR * 26), description: `Roles and permissions for ${COMPANY}`, updatedBy: ADMIN_EMAIL, environment: 'dev' },
  roles: ROLES,
  transactionCategories: CATEGORIES,
  permissions: PERMS.map(([id, displayName, description, category, riskLevel, dataScope]) => ({ id, name: id, displayName, description, category, riskLevel, dataScope })),
  rolePermissions: Object.fromEntries(ROLES.map(r => [r.id, PERMS.filter(p => r.level >= p[6]).map(p => p[0])])),
  auditLog: rbacAudit(),
});

// ---------------------------------------------------------------------------
// System parameters, secrets, environment
// ---------------------------------------------------------------------------

const param = (value: string, def: string, description: string, env_var: string, type: 'text' | 'number' | 'boolean' | 'select' = 'text', options?: string[]) =>
  ({ value, default: def, description, type, env_var, modified: value !== def, ...(options ? { options } : {}) });

const PARAMETER_CATEGORIES: Record<string, { label: string; description: string; icon: string; parameters: Record<string, ReturnType<typeof param>> }> = {
  data_source_mode: {
    label: 'Data source mode', description: 'Whether each source reads the simulator or the real system.', icon: 'layers',
    parameters: Object.fromEntries(SYSTEMS.map(s => [s.modeKey, param(s.mode, 'simulator', `${s.label}: simulator or real system`, `DATA_SOURCE_MODE_${s.modeKey.toUpperCase()}`, 'select', ['simulator', 'real'])])),
  },
  sfdc: {
    label: 'Salesforce', description: 'Connection settings for Salesforce CRM.', icon: 'database',
    parameters: {
      instance_url: param('https://kinetiq-beverages.my.salesforce.com', '', 'Salesforce instance URL', 'SFDC_INSTANCE_URL'),
      api_version: param('v61.0', 'v60.0', 'REST API version', 'SFDC_API_VERSION'),
      batch_size: param('2000', '2000', 'Rows fetched per request', 'SFDC_BATCH_SIZE', 'number'),
      sync_interval_minutes: param('15', '15', 'Minutes between incremental syncs', 'SFDC_SYNC_INTERVAL_MINUTES', 'number'),
    },
  },
  'oracle-erp': {
    label: 'Oracle ERP', description: 'Connection settings for Oracle receivables and payables.', icon: 'building',
    parameters: {
      host: param('ora-erp-prod.kinetiq.internal', '', 'Database host', 'ORACLE_HOST'),
      port: param('1521', '1521', 'Listener port', 'ORACLE_PORT', 'number'),
      service_name: param('ERPPRD', '', 'Service name', 'ORACLE_SERVICE_NAME'),
      query_timeout_seconds: param('45', '30', 'Query timeout in seconds', 'ORACLE_QUERY_TIMEOUT', 'number'),
    },
  },
  sap: {
    label: 'SAP S/4HANA', description: 'Connection settings for SAP.', icon: 'factory',
    parameters: {
      odata_base_url: param('https://s4.kinetiq.internal/sap/opu/odata/sap', '', 'OData base URL', 'SAP_ODATA_BASE_URL'),
      client: param('100', '100', 'SAP client', 'SAP_CLIENT'),
      language: param('EN', 'EN', 'Logon language', 'SAP_LANGUAGE', 'select', ['EN', 'DE', 'ES', 'NL']),
      fetch_size: param('1000', '1000', 'Rows fetched per request', 'SAP_FETCH_SIZE', 'number'),
    },
  },
  s3: {
    label: 'Storage', description: 'Buckets for results, knowledge files and simulator seeds.', icon: 'database',
    parameters: {
      results_bucket: param('kinetiq-nexus-results', '', 'Bucket for journey results', 'S3_RESULTS_BUCKET'),
      knowledge_bucket: param('kinetiq-nexus-knowledge', '', 'Bucket for policies, workflows and integrations', 'S3_KNOWLEDGE_BUCKET'),
      retention_days: param('180', '90', 'Days to keep job results', 'S3_RETENTION_DAYS', 'number'),
      versioning_enabled: param('true', 'true', 'Keep previous versions of knowledge files', 'S3_VERSIONING_ENABLED', 'boolean'),
    },
  },
  dynamodb: {
    label: 'Registry tables', description: 'Tables for journeys, tools and health snapshots.', icon: 'database',
    parameters: {
      workspace_table: param('nexus-dev-foundry-workspace', '', 'Journeys, tools and automations', 'DDB_WORKSPACE_TABLE'),
      health_table: param('nexus-dev-health', '', 'AI health snapshots', 'DDB_HEALTH_TABLE'),
      health_snapshot_ttl_days: param('30', '30', 'Days to keep health snapshots', 'DDB_HEALTH_TTL_DAYS', 'number'),
    },
  },
  cloudwatch: {
    label: 'Monitoring', description: 'Logs, metrics and alarms.', icon: 'activity',
    parameters: {
      log_group: param('/nexus/dev/backend', '', 'Log group for the backend', 'CW_LOG_GROUP'),
      metrics_enabled: param('true', 'true', 'Publish custom metrics', 'CW_METRICS_ENABLED', 'boolean'),
      alarm_email: param('platform-ops@kinetiq-beverages.example', '', 'Where alarms are sent', 'CW_ALARM_EMAIL'),
      agent_latency_alarm_ms: param('6000', '8000', 'Alarm when agent p95 latency exceeds this', 'CW_AGENT_LATENCY_ALARM_MS', 'number'),
    },
  },
};
const withPaths = () => Object.fromEntries(Object.entries(PARAMETER_CATEGORIES).map(([cat, c]) => [cat, {
  ...c,
  parameters: Object.fromEntries(Object.entries(c.parameters).map(([name, p]) => [name, { ...p, path: `/nexus/dev/${cat}/${name}` }])),
}]));

const SECRETS = [
  { name: 'sfdc-oauth', label: 'Salesforce OAuth', description: 'Connected app credentials for Salesforce.', keys: ['client_id', 'client_secret', 'refresh_token'], managed_by: null, exists: true, modifiedMin: DAY * 21 },
  { name: 'oracle-erp-db', label: 'Oracle ERP database', description: 'Read-only database user for Oracle ERP.', keys: ['username', 'password'], managed_by: null, exists: true, modifiedMin: DAY * 64 },
  { name: 'sap-odata', label: 'SAP OData', description: 'Technical user for SAP OData services.', keys: ['username', 'password'], managed_by: null, exists: true, modifiedMin: DAY * 64 },
  { name: 'gdrive-oauth', label: 'Google Drive OAuth', description: 'OAuth client for the Google Drive connector.', keys: ['client_id', 'client_secret', 'refresh_token'], managed_by: 'google-drive-connector', exists: true, modifiedMin: DAY * 9 },
  { name: 'llm-provider', label: 'Model provider', description: 'API key for the language model used by the Copilot.', keys: ['api_key'], managed_by: null, exists: true, modifiedMin: DAY * 3 },
  { name: 'social-listening-api', label: 'Social listening API', description: 'API key for the social listening provider.', keys: ['api_key', 'workspace_id'], managed_by: null, exists: false, modifiedMin: 0 },
  { name: 'smtp-relay', label: 'Email relay', description: 'Credentials for sending notifications.', keys: ['host', 'username', 'password'], managed_by: null, exists: true, modifiedMin: DAY * 120 },
].map(({ modifiedMin, ...s }) => ({ ...s, last_modified: s.exists ? ago(modifiedMin) : null }));

const environment = () => ({ environment: 'dev', region: 'eu-west-1', is_aws: true, is_localstack: false, log_level: 'INFO', timestamp: ago(0) });

// ---------------------------------------------------------------------------
// Google Drive connector
// ---------------------------------------------------------------------------

const gdriveSettings = () => ({
  auth_type: 'oauth2',
  // The client secret is masked; the form only needs to know one is stored.
  oauth2_config: { client_id: '418207736551-k1netiqdrive.apps.googleusercontent.com', client_secret: '', redirect_uri: 'https://nexus.kinetiq-beverages.example/gdrive/callback', scopes: ['https://www.googleapis.com/auth/drive.readonly'] },
  scan_config: { folder_ids: ['1Zx8Qw_ProcurementContracts2026', '1Rt5Lm_SustainabilityReports', '1Hk2Np_SupplierCertificates'], mime_type_filters: ['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/csv'], max_files_per_scan: 200, include_subfolders: true },
  enable_auto_scan: true,
  enable_ocr_extraction: true,
  scan_schedule: '0 */6 * * *',
  last_updated: ago(DAY * 9),
});

const gdriveDiagnostics = () => ({
  connection_health: 'degraded',
  token_status: 'valid',
  token_expires_at: ahead(47),
  api_quota_used: 14280,
  api_quota_daily_limit: 20000,
  api_quota_remaining: 5720,
  folders_configured: 3,
  total_files_discovered: 1846,
  files_by_type: { pdf: 1312, xlsx: 388, csv: 146 },
  recent_syncs: [
    { timestamp: ago(95), files_processed: 22, duration_ms: 131000, errors: 3 },
    { timestamp: ago(95 + 360), files_processed: 9, duration_ms: 48200, errors: 0 },
    { timestamp: ago(95 + 720), files_processed: 14, duration_ms: 71900, errors: 0 },
    { timestamp: ago(95 + 1080), files_processed: 31, duration_ms: 164300, errors: 1 },
    { timestamp: ago(95 + 1440), files_processed: 6, duration_ms: 30100, errors: 0 },
  ],
  recent_errors: [
    { timestamp: ago(96), message: 'Expiry_Date could not be read in 3 contracts (scanned image, low OCR confidence).' },
    { timestamp: ago(97), message: 'Rate limit reached for files.export; retried after 30 s.' },
    { timestamp: ago(95 + 1081), message: 'Permission denied on /Procurement/Contracts/Archive (shared drive membership missing).' },
  ],
  last_sync_at: ago(95),
  last_sync_duration_ms: 131000,
  last_sync_files_processed: 22,
});

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

export const settingsRoutes: SampleRoute[] = [
  // Licence
  { method: 'GET', path: '/api/v1/license/status', handle: () => ({ status: 'success', data: licenseStatus() }) },
  {
    path: '/api/v1/license/validate',
    handle: () => ({ status: 'success', data: { is_valid: true, license_status: 'active', license_id: LICENSE_ID, tier: 'enterprise', error_code: null, message: null, is_in_grace_period: false, can_write: true } }),
  },
  {
    method: 'GET', path: '/api/v1/license/audit',
    handle: ({ query }) => {
      const offset = Number(query.get('offset')) || 0;
      const limit = Number(query.get('limit')) || 50;
      return { status: 'success', data: licenseAudit().slice(offset, offset + limit) };
    },
  },
  {
    method: 'GET', path: /^\/api\/v1\/license\/features\/([^/]+)$/,
    handle: ({ match }) => {
      const allowed = licenseStatus().features.includes(match[1]);
      return { status: 'success', data: { feature_id: match[1], is_allowed: allowed, required_tier: 'enterprise', current_tier: 'enterprise', upgrade_message: allowed ? null : 'This feature is not part of your licence.' } };
    },
  },
  {
    method: 'POST', path: '/api/v1/license/activate',
    handle: () => ({ status: 'success', message: 'Licence activated (sample data: nothing is stored)', data: { license_id: LICENSE_ID, tier: 'enterprise', holder_name: COMPANY, holder_id: 'CUST-004417', activated_at: ago(0), expires_at: ahead(DAY * 365), days_remaining: 365, features: licenseStatus().features, is_active: true } }),
  },
  {
    method: 'POST', path: '/api/v1/license/renew',
    handle: () => ({ status: 'success', message: 'Licence renewed (sample data: nothing is stored)', data: { license_id: LICENSE_ID, previous_expiration: ahead(DAY * 54), new_expiration: ahead(DAY * 419), tier: 'enterprise', tier_changed: false, features: licenseStatus().features } }),
  },
  {
    method: 'POST', path: '/api/v1/license/deactivate',
    handle: () => ({ status: 'success', message: 'Licence deactivated (sample data: nothing is stored)', data: { deactivated_at: ago(0), previous_license_id: LICENSE_ID, can_reactivate: true } }),
  },

  // Users
  { method: 'GET', path: /^\/api\/v1\/users\/?$/, handle: () => ({ users: USERS, total: USERS.length }) },

  // Roles and permissions
  { method: 'GET', path: '/api/v1/rbac/config', handle: () => ({ status: 'success', data: rbacConfig() }) },
  { method: 'GET', path: '/api/v1/rbac/audit', handle: ({ query }) => ({ status: 'success', data: rbacAudit().slice(0, Number(query.get('limit')) || 50) }) },
  {
    method: 'PUT', path: /^\/api\/v1\/rbac\/roles\/([^/]+)\/permissions$/,
    handle: ({ match, body }) => ({ status: 'success', message: 'Permissions updated (sample data: nothing is stored)', data: { roleId: match[1], permissions: asObj(body).permissions || [], version: '1.4.1' } }),
  },

  // System parameters
  {
    method: 'GET', path: '/api/v1/config/schema',
    handle: () => ({
      environment: 'dev', capability: 'nexus',
      categories: Object.fromEntries(Object.entries(PARAMETER_CATEGORIES).map(([cat, c]) => [cat, { label: c.label, description: c.description, icon: c.icon, parameters: Object.fromEntries(Object.entries(c.parameters).map(([n, p]) => [n, { description: p.description, default: p.default, type: p.type, env_var: p.env_var, ...(p.options ? { options: p.options } : {}) }])) }])),
      secrets: Object.fromEntries(SECRETS.map(s => [s.name, { label: s.label, description: s.description, keys: s.keys, managed_by: s.managed_by }])),
    }),
  },
  {
    method: 'GET', path: '/api/v1/config/parameters',
    handle: ({ query }) => {
      const all = withPaths();
      const cat = query.get('category');
      return { environment: 'dev', categories: cat && all[cat] ? { [cat]: all[cat] } : all };
    },
  },
  {
    method: 'GET', path: /^\/api\/v1\/config\/parameters\/([^/]+)\/([^/]+)$/,
    handle: ({ match }) => withPaths()[decodeURIComponent(match[1])]?.parameters[decodeURIComponent(match[2])] || param('', '', 'Unknown parameter', ''),
  },
  {
    method: 'PUT', path: /^\/api\/v1\/config\/parameters\/([^/]+)\/([^/]+)$/,
    handle: ({ match, body }) => {
      const cat = decodeURIComponent(match[1]);
      const name = decodeURIComponent(match[2]);
      return { status: 'updated', path: `/nexus/dev/${cat}/${name}`, previous_value: PARAMETER_CATEGORIES[cat]?.parameters[name]?.value ?? '', new_value: String(asObj(body).value ?? ''), timestamp: ago(0) };
    },
  },
  { method: 'GET', path: /^\/api\/v1\/config\/parameters\/([^/]+)$/, handle: ({ match }) => withPaths()[decodeURIComponent(match[1])] || { label: decodeURIComponent(match[1]), description: '', icon: 'settings', parameters: {} } },
  { method: 'POST', path: '/api/v1/config/cache/invalidate', handle: () => ({ status: 'success', message: 'Configuration cache cleared. New values are read on the next request.', timestamp: ago(0) }) },
  { method: 'GET', path: '/api/v1/config/environment', handle: () => environment() },
  { method: 'GET', path: '/api/v1/config/log-level', handle: () => ({ level: 'INFO', source: 'ssm', timestamp: ago(DAY * 2) }) },
  {
    method: 'PUT', path: '/api/v1/config/log-level',
    handle: ({ body }) => ({ status: 'updated', previous_level: 'INFO', new_level: String(asObj(body).level || 'INFO'), ssm_updated: asObj(body).persist_to_ssm !== false, loggers_updated: 14, timestamp: ago(0) }),
  },

  // Secrets (masked)
  { method: 'GET', path: '/api/v1/config/secrets', handle: () => ({ secrets: SECRETS }) },
  {
    method: 'GET', path: /^\/api\/v1\/config\/secrets\/([^/]+)$/,
    handle: ({ match }) => {
      const s = SECRETS.find(x => x.name === decodeURIComponent(match[1])) || SECRETS[0];
      return { name: s.name, label: s.label, description: s.description, keys: s.keys, managed_by: s.managed_by, exists: s.exists, values: Object.fromEntries(s.keys.map(k => [k, s.exists ? '********' : null])) };
    },
  },
  {
    method: 'PUT', path: /^\/api\/v1\/config\/secrets\/([^/]+)$/,
    handle: ({ match, body }) => ({ status: 'updated', name: decodeURIComponent(match[1]), updated_keys: Object.keys(asObj(asObj(body).values)), timestamp: ago(0) }),
  },

  // Google Drive connector
  { method: 'GET', path: '/api/v1/connectors/gdrive/settings', handle: () => ({ success: true, data: gdriveSettings() }) },
  { method: 'GET', path: '/api/v1/connectors/gdrive/diagnostics', handle: () => gdriveDiagnostics() },
  { method: 'POST', path: '/api/v1/connectors/gdrive/test', handle: () => ({ success: true, message: 'Connected. 1,846 files visible in 3 folders.', files_found: 1846, latency_ms: 412 }) },
  { method: 'POST', path: '/api/v1/connectors/gdrive/auth/start', handle: () => ({ success: false, message: 'Sign-in with Google is not available with sample data.' }) },
];
