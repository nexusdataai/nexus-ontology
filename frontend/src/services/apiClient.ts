/**
 * Authenticated API Client
 *
 * Fetch wrapper that (a) resolves the backend base URL from `/config.json`
 * (with a same-origin fallback for the nginx-proxied EKS deployment) and
 * (b) attaches the current backend-issued access token from
 * ``backendAuthService`` when ``requireAuth`` is set.
 *
 * In EKS mode we ALSO carry a session cookie via ``credentials: 'include'``
 * on every fetch, so header injection is a belt-and-braces fallback for
 * endpoints that read the ``Authorization`` header directly.
 */

import { getConfig } from './configService';
import { backendAuthService } from './backendAuthService';

// Cached API configuration (includes fallback — never re-fetch config.json per request)
let cachedApiConfig: { baseUrl: string; timeout: number } | null = null;
let configLoadPromise: Promise<{ baseUrl: string; timeout: number }> | null = null;

const devFallbackApiConfig = (): { baseUrl: string; timeout: number } => ({
  baseUrl: import.meta.env.VITE_API_BASE_URL || '',
  timeout: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000', 10),
});

/**
 * Resolve API base URL via configService (VITE_* in local dev, config.json in prod).
 */
async function getApiConfig(): Promise<{ baseUrl: string; timeout: number }> {
  if (cachedApiConfig) {
    return cachedApiConfig;
  }

  if (!configLoadPromise) {
    configLoadPromise = (async () => {
      try {
        const config = await getConfig();
        cachedApiConfig = {
          baseUrl: config.api?.baseUrl || '',
          timeout: config.api?.timeout || 30000,
        };
        if (!cachedApiConfig.baseUrl && import.meta.env.VITE_API_BASE_URL) {
          cachedApiConfig.baseUrl = import.meta.env.VITE_API_BASE_URL;
        }
        console.log('✅ API config loaded:', { baseUrl: cachedApiConfig.baseUrl || '(same origin)' });
        return cachedApiConfig;
      } catch (error) {
        console.warn('⚠️ API config load failed, using env fallback:', error);
        cachedApiConfig = devFallbackApiConfig();
        return cachedApiConfig;
      }
    })();
  }

  return configLoadPromise;
}

function getAccessToken(): string | null {
  return backendAuthService.getAccessToken();
}

/**
 * API Error class for handling API-specific errors
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Options for API requests
 */
export interface ApiRequestOptions extends Omit<RequestInit, 'headers'> {
  headers?: Record<string, string>;
  requireAuth?: boolean;
  timeout?: number;
}

/**
 * Make an authenticated API request
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const { requireAuth = true, timeout, ...fetchOptions } = options;
  
  const apiConfig = await getApiConfig();
  const url = `${apiConfig.baseUrl}${endpoint}`;
  
  // Build headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    ...options.headers
  };

  // Attach Authorization header when required. In EKS mode the session
  // cookie carried via ``credentials: 'include'`` is the primary auth
  // channel; the header is redundant for cookie-reading endpoints but
  // required for endpoints that check the Bearer token directly.
  if (requireAuth) {
    const accessToken = getAccessToken();
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
  }

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutMs = timeout || apiConfig.timeout;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers,
      credentials: 'include',  // Send cookies for session-based auth (EKS mode)
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = null;
      }
      throw new ApiError(
        errorData?.message || `API request failed: ${response.status} ${response.statusText}`,
        response.status,
        response.statusText,
        errorData
      );
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      return await response.json();
    }
    
    return await response.text() as unknown as T;
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error instanceof ApiError) {
      throw error;
    }
    
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new ApiError('Request timeout', 408, 'Request Timeout');
      }
      throw new ApiError(error.message, 0, 'Network Error');
    }
    
    throw new ApiError('Unknown error occurred', 0, 'Unknown Error');
  }
}

/**
 * Convenience methods for common HTTP methods
 */
export const apiClient = {
  get: <T = any>(endpoint: string, options?: ApiRequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T = any>(endpoint: string, data?: any, options?: ApiRequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined
    }),

  put: <T = any>(endpoint: string, data?: any, options?: ApiRequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined
    }),

  patch: <T = any>(endpoint: string, data?: any, options?: ApiRequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined
    }),

  delete: <T = any>(endpoint: string, options?: ApiRequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'DELETE' })
};

/**
 * Get the API base URL (useful for constructing URLs manually)
 */
export async function getApiBaseUrl(): Promise<string> {
  const config = await getApiConfig();
  return config.baseUrl;
}

/**
 * Clear cached configuration (useful for testing or config reload)
 */
export function clearApiConfigCache(): void {
  cachedApiConfig = null;
  configLoadPromise = null;
}

export default apiClient;

