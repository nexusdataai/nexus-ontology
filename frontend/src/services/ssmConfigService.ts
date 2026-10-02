/**
 * SSM Configuration Service
 * 
 * Provides API calls for managing SSM parameters and secrets through
 * the backend configuration API.
 */

import { apiClient } from './apiClient';

// =============================================================================
// Types and Interfaces
// =============================================================================

export interface ParameterValue {
  value: string;
  default: string;
  description: string;
  type: 'text' | 'number' | 'boolean' | 'select';
  env_var: string;
  modified: boolean;
  options?: string[];
  path?: string;
}

export interface ParameterCategory {
  label: string;
  description: string;
  icon: string;
  parameters: Record<string, ParameterValue>;
}

export interface ConfigParametersResponse {
  environment: string;
  categories: Record<string, ParameterCategory>;
}

export interface ConfigSchemaResponse {
  environment: string;
  capability: string;
  categories: Record<string, {
    label: string;
    description: string;
    icon: string;
    parameters: Record<string, {
      description: string;
      default: string;
      type: string;
      env_var: string;
      options?: string[];
    }>;
  }>;
  secrets: Record<string, {
    label: string;
    description: string;
    keys: string[];
    managed_by: string | null;
  }>;
}

export interface ParameterUpdateResponse {
  status: string;
  path: string;
  previous_value: string;
  new_value: string;
  timestamp: string;
}

export interface SecretInfo {
  name: string;
  label: string;
  description: string;
  keys: string[];
  managed_by: string | null;
  exists: boolean;
  last_modified: string | null;
}

export interface SecretsListResponse {
  secrets: SecretInfo[];
}

export interface SecretDetail {
  name: string;
  label: string;
  description: string;
  keys: string[];
  managed_by: string | null;
  exists: boolean;
  values: Record<string, string | null>;
}

export interface SecretUpdateResponse {
  status: string;
  name: string;
  updated_keys: string[];
  timestamp: string;
}

export interface CacheInvalidateResponse {
  status: string;
  message: string;
  timestamp: string;
}

export interface EnvironmentInfo {
  environment: string;
  region: string;
  is_aws: boolean;
  is_localstack: boolean;
  log_level: string;
  timestamp: string;
}

export interface LogLevelResponse {
  level: string;
  source: string;
  timestamp: string;
}

export interface LogLevelUpdateResponse {
  status: string;
  previous_level: string;
  new_level: string;
  ssm_updated: boolean;
  loggers_updated: number;
  timestamp: string;
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get the configuration schema with all parameter categories and metadata
 */
export async function getConfigSchema(): Promise<ConfigSchemaResponse> {
  const response = await apiClient.get<ConfigSchemaResponse>('/api/v1/config/schema');
  return response;
}

/**
 * Get all SSM parameters grouped by category
 */
export async function getAllParameters(category?: string): Promise<ConfigParametersResponse> {
  const url = category 
    ? `/api/v1/config/parameters?category=${encodeURIComponent(category)}`
    : '/api/v1/config/parameters';
  return apiClient.get<ConfigParametersResponse>(url);
}

/**
 * Get parameters for a specific category
 */
export async function getParametersByCategory(category: string): Promise<ParameterCategory> {
  return apiClient.get<ParameterCategory>(`/api/v1/config/parameters/${encodeURIComponent(category)}`);
}

/**
 * Get a single parameter by category and name
 */
export async function getParameter(category: string, name: string): Promise<ParameterValue> {
  return apiClient.get<ParameterValue>(
    `/api/v1/config/parameters/${encodeURIComponent(category)}/${encodeURIComponent(name)}`
  );
}

/**
 * Update a parameter value
 */
export async function updateParameter(
  category: string,
  name: string,
  value: string
): Promise<ParameterUpdateResponse> {
  return apiClient.put<ParameterUpdateResponse>(
    `/api/v1/config/parameters/${encodeURIComponent(category)}/${encodeURIComponent(name)}`,
    { value }
  );
}

/**
 * Get list of available secrets with metadata (no values)
 */
export async function getSecretsList(): Promise<SecretsListResponse> {
  return apiClient.get<SecretsListResponse>('/api/v1/config/secrets');
}

/**
 * Get a secret's metadata and masked values
 */
export async function getSecret(name: string): Promise<SecretDetail> {
  return apiClient.get<SecretDetail>(`/api/v1/config/secrets/${encodeURIComponent(name)}`);
}

/**
 * Update a secret's values
 */
export async function updateSecret(
  name: string,
  values: Record<string, string>
): Promise<SecretUpdateResponse> {
  return apiClient.put<SecretUpdateResponse>(
    `/api/v1/config/secrets/${encodeURIComponent(name)}`,
    { values }
  );
}

/**
 * Invalidate all SSM and Secrets Manager caches
 */
export async function invalidateCache(): Promise<CacheInvalidateResponse> {
  return apiClient.post<CacheInvalidateResponse>('/api/v1/config/cache/invalidate', {});
}

/**
 * Get current environment information
 */
export async function getEnvironmentInfo(): Promise<EnvironmentInfo> {
  return apiClient.get<EnvironmentInfo>('/api/v1/config/environment');
}

/**
 * Get current log level
 */
export async function getLogLevel(): Promise<LogLevelResponse> {
  return apiClient.get<LogLevelResponse>('/api/v1/config/log-level');
}

/**
 * Update log level
 */
export async function updateLogLevel(
  level: string,
  persistToSsm: boolean = true
): Promise<LogLevelUpdateResponse> {
  return apiClient.put<LogLevelUpdateResponse>('/api/v1/config/log-level', {
    level,
    persist_to_ssm: persistToSsm
  });
}

// =============================================================================
// Service Object Export
// =============================================================================

export const ssmConfigService = {
  // Schema
  getConfigSchema,
  
  // Parameters
  getAllParameters,
  getParametersByCategory,
  getParameter,
  updateParameter,
  
  // Secrets
  getSecretsList,
  getSecret,
  updateSecret,
  
  // Cache
  invalidateCache,
  
  // Environment
  getEnvironmentInfo,
  
  // Log Level
  getLogLevel,
  updateLogLevel,
};

export default ssmConfigService;
