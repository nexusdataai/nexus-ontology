/**
 * Configuration Service
 * 
 * Provides a unified interface for loading application configuration from
 * multiple sources with proper priority handling:
 * - Runtime config.json (production deployments)
 * - Environment variables (local development)
 * - Default values (fallback)
 */

type DataSource = 'api' | 'json';

// ============================================================================
// Types and Interfaces
// ============================================================================

export interface ApiConfig {
  baseUrl: string;
  timeout: number;
}

// Deployment mode determines how the UI connects to the backend
// - 'eks': Frontend + backend in same EKS cluster, nginx proxies /api/* and /health,/stats,/tools
// - 's3-ecs': Frontend on S3/CloudFront, backend on ECS behind ALB (cross-origin)
// - 'local': Local development
export type DeploymentMode = 'eks' | 's3-ecs' | 'local';

export interface GatewayConfig {
  apiKey: string;
  serverUrl?: string;
}

// AWS Cognito sign-in settings (config.json "cognito" block)
export interface CognitoConfig {
  region: string;
  userPoolId: string;
  clientId: string;
  domain: string;
  redirectSignIn: string;
  redirectSignOut: string;
}

export interface AppConfig {
  api: ApiConfig;
  deploymentMode: DeploymentMode;
  gateway?: GatewayConfig;
  cognito?: CognitoConfig;
  bypassAuth: boolean;
  environment: 'development' | 'staging' | 'production';
  dataSource: DataSource;
  enableFallback: boolean;
}

export interface ConfigService {
  getConfig(): Promise<AppConfig>;
  isConfigured(): Promise<boolean>;
  clearCache(): void;
}

export type ConfigSource = 'config.json' | 'environment' | 'defaults';

export interface ConfigLoadResult {
  config: AppConfig;
  source: ConfigSource;
}

// ============================================================================
// Environment Detection
// ============================================================================

export const detectEnvironment = (): 'development' | 'staging' | 'production' => {
  if (typeof window === 'undefined') {
    return 'development';
  }
  
  const hostname = window.location.hostname;
  
  if (hostname.includes('localhost') || hostname.includes('127.0.0.1')) {
    return 'development';
  } else if (hostname.includes('staging') || hostname.includes('dev')) {
    return 'staging';
  }
  
  return 'production';
};

export const isLocalDevelopment = (): boolean => {
  return detectEnvironment() === 'development';
};

const getWindowOrigin = (): string => {
  try {
    return typeof window !== 'undefined' ? window.location.origin : '';
  } catch {
    return '';
  }
};

// ============================================================================
// Configuration Validation
// ============================================================================

export interface ValidationResult {
  valid: boolean;
  missingFields: string[];
  errors: string[];
}

export const validateConfig = (config: Partial<AppConfig>): ValidationResult => {
  const missingFields: string[] = [];
  const errors: string[] = [];
  
  // API baseUrl is optional (empty means use nginx proxy)
  // No required fields for backend auth mode
  
  return {
    valid: true,  // Config is always valid now
    missingFields,
    errors
  };
};

// ============================================================================
// Default Configuration
// ============================================================================

const getDefaultConfig = (): Partial<AppConfig> => {
  const origin = getWindowOrigin();
  
  return {
    api: {
      baseUrl: '',
      timeout: 30000
    },
    deploymentMode: isLocalDevelopment() ? 'local' : 'eks',
    gateway: {
      apiKey: '',
    },
    cognito: {
      userPoolId: '',
      clientId: '',
      domain: '',
      region: 'us-east-1',
      redirectSignIn: `${origin}/auth/callback`,
      redirectSignOut: `${origin}/login`
    },
    bypassAuth: false,
    environment: detectEnvironment(),
    dataSource: 'api',
    enableFallback: true
  };
};

// ============================================================================
// Configuration Loading
// ============================================================================

let cachedConfig: AppConfig | null = null;
let cachedSource: ConfigSource | null = null;
let configLoadPromise: Promise<ConfigLoadResult> | null = null;

/**
 * Load configuration from environment variables
 */
const loadFromEnvironment = (): Partial<AppConfig> => {
  // Parse dataSource from environment
  const envDataSource = import.meta.env.VITE_DATA_SOURCE;
  const dataSource: DataSource = (envDataSource === 'json' || envDataSource === 'api') 
    ? envDataSource 
    : 'api';
  
  return {
    api: {
      baseUrl: import.meta.env.VITE_API_BASE_URL || '',
      timeout: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000', 10)
    },
    deploymentMode: 'local' as DeploymentMode,
    bypassAuth: import.meta.env.VITE_BYPASS_AUTH === 'true',
    environment: detectEnvironment(),
    dataSource,
    enableFallback: import.meta.env.VITE_ENABLE_FALLBACK !== 'false'
  };
};

/**
 * Fetch configuration from config.json
 */
const fetchConfigJson = async (): Promise<Partial<AppConfig> | null> => {
  try {
    console.log('📥 Fetching runtime config from /config.json...');
    
    const response = await fetch('/config.json', {
      cache: 'no-store',
      headers: { 'Accept': 'application/json' }
    });
    
    if (!response.ok) {
      console.warn(`⚠️ Failed to fetch config.json: ${response.status} ${response.statusText}`);
      return null;
    }
    
    const data = await response.json();
    const origin = getWindowOrigin();
    
    // Map config.json structure to AppConfig
    // Detect deployment mode: if baseUrl is empty, it's EKS (nginx proxy)
    const detectedMode: DeploymentMode = data.deploymentMode || 
      (data.api?.baseUrl ? 's3-ecs' : 'eks');
    
    const config: Partial<AppConfig> = {
      api: {
        baseUrl: data.api?.baseUrl || '',
        timeout: data.api?.timeout || 30000
      },
      deploymentMode: detectedMode,
      gateway: {
        apiKey: data.gateway?.apiKey || '',
        serverUrl: data.gateway?.serverUrl || '',
      },
      cognito: {
        userPoolId: data.cognito?.userPoolId || '',
        clientId: data.cognito?.clientId || '',
        domain: data.cognito?.domain || '',
        region: data.cognito?.region || 'us-east-1',
        redirectSignIn: data.cognito?.redirectSignIn || `${origin}/auth/callback`,
        redirectSignOut: data.cognito?.redirectSignOut || `${origin}/login`
      },
      bypassAuth: data.bypassAuth === true,
      environment: data.environment || detectEnvironment(),
      dataSource: (data.dataSource === 'json' || data.dataSource === 'api') ? data.dataSource : 'api',
      enableFallback: data.enableFallback !== false
    };
    
    console.log('✅ Runtime config loaded from config.json');
    return config;
    
  } catch (error) {
    console.warn('⚠️ Error fetching config.json:', error);
    return null;
  }
};

/**
 * Merge configurations with proper priority
 */
const mergeConfigs = (...configs: Partial<AppConfig>[]): AppConfig => {
  const defaults = getDefaultConfig();
  const merged = { ...defaults } as AppConfig;
  
  for (const config of configs) {
    if (config.api) {
      merged.api = { ...merged.api, ...config.api };
    }
    if (config.deploymentMode) {
      merged.deploymentMode = config.deploymentMode;
    }
    if (config.gateway) {
      merged.gateway = { ...merged.gateway, ...config.gateway };
    }
    if (config.bypassAuth !== undefined) {
      merged.bypassAuth = config.bypassAuth;
    }
    if (config.environment) {
      merged.environment = config.environment;
    }
    if (config.dataSource) {
      merged.dataSource = config.dataSource;
    }
    if (config.enableFallback !== undefined) {
      merged.enableFallback = config.enableFallback;
    }
  }
  
  return merged;
};

/**
 * Load configuration with proper priority handling
 * Priority: Runtime config.json (production) > Environment variables > Defaults
 */
const loadConfig = async (): Promise<ConfigLoadResult> => {
  let source: ConfigSource = 'defaults';
  let finalConfig: AppConfig;

  // Runtime config.json (K3s/nginx) takes precedence — including localhost port-forwards.
  const jsonConfig = await fetchConfigJson();
  if (jsonConfig) {
    const validation = validateConfig(jsonConfig);
    if (validation.valid) {
      finalConfig = mergeConfigs(jsonConfig);
      source = 'config.json';
      logConfigSource(source, finalConfig);
      return { config: finalConfig, source };
    }
    console.warn('⚠️ config.json missing required fields:', validation.missingFields);
  }

  // In development, prioritize environment variables
  if (isLocalDevelopment()) {
    console.log('🔧 Local development detected, checking environment variables...');
    const envConfig = loadFromEnvironment();
    const validation = validateConfig(envConfig);
    
    if (validation.valid) {
      console.log('✅ Using environment variable configuration');
      finalConfig = mergeConfigs(envConfig);
      source = 'environment';
      logConfigSource(source, finalConfig);
      return { config: finalConfig, source };
    }
    
    console.log('⚠️ Environment variables incomplete, falling back to defaults...');
  }
  
  // Fallback to environment variables
  console.log('🔄 Falling back to environment variables...');
  const envConfig = loadFromEnvironment();
  const validation = validateConfig(envConfig);
  
  if (validation.valid) {
    finalConfig = mergeConfigs(envConfig);
    source = 'environment';
    logConfigSource(source, finalConfig);
    return { config: finalConfig, source };
  }
  
  // Use defaults with warning
  console.warn('⚠️ No valid configuration found. Using defaults.');
  console.warn('Missing fields:', validation.missingFields);
  finalConfig = mergeConfigs(envConfig);
  source = 'defaults';
  logConfigSource(source, finalConfig);
  
  return { config: finalConfig, source };
};

/**
 * Log configuration source (excluding sensitive data)
 */
const logConfigSource = (source: ConfigSource, config: AppConfig): void => {
  const sourceFileMap: Record<ConfigSource, string> = {
    'config.json': '/public/config.json (runtime config)',
    'environment': '.env.local (environment variables via VITE_* prefix)',
    'defaults': 'built-in defaults (no config file found)'
  };
  
  console.log('═══════════════════════════════════════════════════════════════');
  console.log(`🔧 CONFIGURATION SOURCE: ${source}`);
  console.log(`📁 Reading configs from: ${sourceFileMap[source]}`);
  console.log('═══════════════════════════════════════════════════════════════');
  console.log('📋 Config summary:', {
    environment: config.environment,
    bypassAuth: config.bypassAuth,
    hasApiBaseUrl: !!config.api.baseUrl,
    apiBaseUrl: config.api.baseUrl || '(nginx proxy)',
    dataSource: config.dataSource,
    enableFallback: config.enableFallback,
    authMode: 'backend'  // Authentication now handled by backend
  });
};

// ============================================================================
// Public API
// ============================================================================

/**
 * Get the application configuration
 * Uses caching to avoid repeated fetches
 */
export const getConfig = async (): Promise<AppConfig> => {
  if (cachedConfig) {
    return cachedConfig;
  }
  
  if (configLoadPromise) {
    const result = await configLoadPromise;
    return result.config;
  }
  
  configLoadPromise = loadConfig();
  const result = await configLoadPromise;
  
  cachedConfig = result.config;
  cachedSource = result.source;
  
  return result.config;
};

/**
 * Check if the application is properly configured
 */
export const isConfigured = async (): Promise<boolean> => {
  const config = await getConfig();
  const validation = validateConfig(config);
  return validation.valid;
};

/**
 * Clear the configuration cache
 */
export const clearConfigCache = (): void => {
  cachedConfig = null;
  cachedSource = null;
  configLoadPromise = null;
  console.log('🗑️ Configuration cache cleared');
};

/**
 * Get the source of the current configuration
 */
export const getConfigSource = (): ConfigSource | null => {
  return cachedSource;
};

/**
 * Check if auth bypass is enabled
 */
export const isAuthBypassEnabled = async (): Promise<boolean> => {
  if (import.meta.env.VITE_BYPASS_AUTH === 'true') {
    return true;
  }
  const config = await getConfig();
  return config.bypassAuth;
};

/**
 * Get the configured data source
 */
export const getDataSource = async (): Promise<DataSource> => {
  const config = await getConfig();
  return config.dataSource;
};

/**
 * Get the deployment mode
 */
export const getDeploymentMode = async (): Promise<DeploymentMode> => {
  const config = await getConfig();
  return config.deploymentMode;
};

/**
 * Check if running in EKS deployment mode (nginx proxy)
 */
export const isEksMode = async (): Promise<boolean> => {
  return (await getDeploymentMode()) === 'eks';
};

/**
 * Check if fallback is enabled
 */
export const isFallbackEnabled = async (): Promise<boolean> => {
  const config = await getConfig();
  return config.enableFallback;
};

// Export the config service interface implementation
export const configService: ConfigService = {
  getConfig,
  isConfigured,
  clearCache: clearConfigCache
};

export default configService;
