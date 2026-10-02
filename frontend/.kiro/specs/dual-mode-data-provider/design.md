# Design Document: Dual-Mode Data Provider

## Overview

This design implements a dual-mode data fetching strategy for the Nexus Telco QA Dashboard, enabling seamless switching between API and JSON data sources. The architecture follows the proven pattern from alert-engine-ui, providing graceful degradation when the backend API is unavailable.

The system consists of three main layers:
1. **Configuration Layer** - Manages data source settings
2. **Provider Layer** - API and JSON providers with identical interfaces
3. **Router Layer** - Dashboard Data Provider that routes requests and handles fallback

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Components                                │
│  (QAAnalyticsDashboard, CallCenterDashboard, etc.)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Existing Services                              │
│  (QAAnalyticsService, CallAnalyticsService)                     │
│  - Accept optional dataSource parameter                          │
│  - Delegate to Dashboard Data Provider                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                Dashboard Data Provider (Router)                  │
│  - Routes requests based on dataSource config                    │
│  - Handles automatic fallback on API failure                     │
│  - Returns source indicator with response                        │
└─────────────────────────────────────────────────────────────────┘
                    │                       │
         ┌──────────┴──────────┐   ┌───────┴───────┐
         ▼                      ▼   ▼               ▼
┌─────────────────┐    ┌─────────────────┐
│   API Provider  │    │  JSON Provider  │
│  - apiClient    │    │  - fetch()      │
│  - Caching      │    │  - Cache-bust   │
│  - Retry logic  │    │  - Transform    │
└─────────────────┘    └─────────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│  Backend API    │    │  /public/*.json │
│  (call-api)     │    │  Static files   │
└─────────────────┘    └─────────────────┘
```

## Components and Interfaces

### 1. Data Source Type

```typescript
// src/types/dataProvider.types.ts

export type DataSource = 'api' | 'json';
export type ResponseSource = 'api' | 'json' | 'fallback';

export interface DataProviderConfig {
  defaultSource: DataSource;
  enableFallback: boolean;
  cacheTTL: Record<string, number>;
}

export interface DataResponse<T> {
  data: T;
  source: ResponseSource;
  timestamp: number;
}

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}
```

### 2. Provider Interface

```typescript
// src/services/providers/dataProvider.interface.ts

export interface IDataProvider {
  // QA Analytics methods
  fetchQAAnalysisData(agentFilter?: string, dateFrom?: string, dateTo?: string): Promise<QAAnalysisData>;
  fetchQAReport(): Promise<string>;
  
  // Call Analytics methods
  fetchCallAnalyticsData(): Promise<CallAnalyticsData>;
  
  // Cache management
  clearCache(): void;
}
```

### 3. API Data Provider

```typescript
// src/services/providers/apiDataProvider.ts

class ApiDataProvider implements IDataProvider {
  private cache: Map<string, CacheEntry<unknown>> = new Map();
  private defaultCacheTTL = 5 * 60 * 1000; // 5 minutes
  private retryAttempts = 3;
  private retryDelay = 1000; // 1 second base delay
  
  private cacheTTLConfig: Record<string, number> = {
    'qa-analysis': 5 * 60 * 1000,      // 5 minutes
    'qa-report': 10 * 60 * 1000,       // 10 minutes
    'call-analytics': 5 * 60 * 1000,   // 5 minutes
  };

  async fetchQAAnalysisData(agentFilter?: string, dateFrom?: string, dateTo?: string): Promise<QAAnalysisData> {
    const cacheKey = this.buildCacheKey('qa-analysis', { agentFilter, dateFrom, dateTo });
    
    // Check cache first (only for unfiltered requests)
    if (!agentFilter && !dateFrom && !dateTo) {
      const cached = this.getFromCache<QAAnalysisData>(cacheKey);
      if (cached) {
        console.log('✅ ApiDataProvider: Cache hit for QA analysis');
        return cached;
      }
    }
    
    // Build query params
    const params = new URLSearchParams();
    if (agentFilter) params.append('agent', agentFilter);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    
    const endpoint = `/api/v1/qa/analysis${params.toString() ? `?${params}` : ''}`;
    
    console.log('🔄 ApiDataProvider: Fetching QA analysis from API...');
    const data = await this.fetchWithRetry<QAAnalysisData>(endpoint);
    
    // Cache unfiltered results
    if (!agentFilter && !dateFrom && !dateTo) {
      this.setInCache(cacheKey, data, this.cacheTTLConfig['qa-analysis']);
    }
    
    console.log('✅ ApiDataProvider: QA analysis fetched successfully');
    return data;
  }

  async fetchQAReport(): Promise<string> {
    const cacheKey = 'qa-report';
    const cached = this.getFromCache<string>(cacheKey);
    if (cached) return cached;
    
    console.log('🔄 ApiDataProvider: Fetching QA report from API...');
    const response = await this.fetchWithRetry<{ report: string }>('/api/v1/qa/report');
    
    this.setInCache(cacheKey, response.report, this.cacheTTLConfig['qa-report']);
    console.log('✅ ApiDataProvider: QA report fetched successfully');
    return response.report;
  }

  async fetchCallAnalyticsData(): Promise<CallAnalyticsData> {
    const cacheKey = 'call-analytics';
    const cached = this.getFromCache<CallAnalyticsData>(cacheKey);
    if (cached) return cached;
    
    console.log('🔄 ApiDataProvider: Fetching call analytics from API...');
    const data = await this.fetchWithRetry<CallAnalyticsData>('/api/v1/qa/call-analytics');
    
    this.setInCache(cacheKey, data, this.cacheTTLConfig['call-analytics']);
    console.log('✅ ApiDataProvider: Call analytics fetched successfully');
    return data;
  }

  private async fetchWithRetry<T>(endpoint: string, attempt = 1): Promise<T> {
    try {
      return await apiClient.get<T>(endpoint);
    } catch (error) {
      if (attempt < this.retryAttempts) {
        const delay = this.retryDelay * Math.pow(2, attempt - 1);
        console.warn(`⚠️ ApiDataProvider: Retry ${attempt}/${this.retryAttempts} after ${delay}ms`);
        await new Promise(resolve => setTimeout(resolve, delay));
        return this.fetchWithRetry<T>(endpoint, attempt + 1);
      }
      console.error(`❌ ApiDataProvider: Failed after ${this.retryAttempts} attempts`);
      throw error;
    }
  }

  private buildCacheKey(base: string, params: Record<string, string | undefined>): string {
    const filtered = Object.entries(params)
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => `${k}=${v}`)
      .join('&');
    return filtered ? `${base}?${filtered}` : base;
  }

  private getFromCache<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;
    
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }
    
    return entry.data as T;
  }

  private setInCache(key: string, data: unknown, ttl: number): void {
    this.cache.set(key, { data, timestamp: Date.now(), ttl });
  }

  clearCache(): void {
    this.cache.clear();
    console.log('🗑️ ApiDataProvider: Cache cleared');
  }
}

export const apiDataProvider = new ApiDataProvider();
```

### 4. JSON Data Provider

```typescript
// src/services/providers/jsonDataProvider.ts

class JsonDataProvider implements IDataProvider {
  private readonly basePath = '/results';
  
  async fetchQAAnalysisData(): Promise<QAAnalysisData> {
    console.log('🔄 JsonDataProvider: Loading QA analysis from JSON...');
    const data = await this.loadJsonFile<QAAnalysisData>(`${this.basePath}/analysis.json`);
    console.log('✅ JsonDataProvider: QA analysis loaded from JSON');
    return data;
  }

  async fetchQAReport(): Promise<string> {
    console.log('🔄 JsonDataProvider: Loading QA report from file...');
    const timestamp = Date.now();
    const response = await fetch(`${this.basePath}/report.md?t=${timestamp}`);
    
    if (!response.ok) {
      throw new Error(`Failed to load report: ${response.status} ${response.statusText}`);
    }
    
    console.log('✅ JsonDataProvider: QA report loaded from file');
    return response.text();
  }

  async fetchCallAnalyticsData(): Promise<CallAnalyticsData> {
    console.log('🔄 JsonDataProvider: Loading call analytics from JSON...');
    const data = await this.loadJsonFile<CallAnalyticsData>(
      '/transcripts/ai_enhanced_analysis_all_scripts_report.json'
    );
    console.log('✅ JsonDataProvider: Call analytics loaded from JSON');
    return data;
  }

  private async loadJsonFile<T>(path: string): Promise<T> {
    // Add cache-busting timestamp
    const timestamp = Date.now();
    const url = `${path}?t=${timestamp}`;
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Failed to load ${path}: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
  }

  clearCache(): void {
    // JSON provider doesn't cache - browser handles it
    console.log('🗑️ JsonDataProvider: No cache to clear');
  }
}

export const jsonDataProvider = new JsonDataProvider();
```

### 5. Dashboard Data Provider (Router)

```typescript
// src/services/dashboardDataProvider.ts

import { apiDataProvider } from './providers/apiDataProvider';
import { jsonDataProvider } from './providers/jsonDataProvider';
import { getConfig } from './configService';
import type { DataSource, ResponseSource, DataResponse } from '@/types/dataProvider.types';

class DashboardDataProvider {
  private defaultSource: DataSource = 'api';
  private enableFallback: boolean = true;

  async initialize(): Promise<void> {
    const config = await getConfig();
    this.defaultSource = (config as any).dataSource || 'api';
    this.enableFallback = (config as any).enableFallback !== false;
    
    console.log(`📋 DashboardDataProvider initialized: source=${this.defaultSource}, fallback=${this.enableFallback}`);
  }

  private getProvider(source: DataSource) {
    return source === 'api' ? apiDataProvider : jsonDataProvider;
  }

  async fetchQAAnalysisData(
    agentFilter?: string,
    dateFrom?: string,
    dateTo?: string,
    dataSource?: DataSource
  ): Promise<DataResponse<QAAnalysisData>> {
    const source = dataSource || this.defaultSource;
    
    try {
      const data = await this.getProvider(source).fetchQAAnalysisData(agentFilter, dateFrom, dateTo);
      return { data, source, timestamp: Date.now() };
    } catch (apiError) {
      if (source === 'api' && this.enableFallback) {
        console.warn('⚠️ DashboardDataProvider: API failed, falling back to JSON');
        try {
          const data = await jsonDataProvider.fetchQAAnalysisData();
          return { data, source: 'fallback', timestamp: Date.now() };
        } catch (jsonError) {
          throw new Error(`Both API and JSON failed. API: ${apiError}. JSON: ${jsonError}`);
        }
      }
      throw apiError;
    }
  }

  async fetchQAReport(dataSource?: DataSource): Promise<DataResponse<string>> {
    const source = dataSource || this.defaultSource;
    
    try {
      const data = await this.getProvider(source).fetchQAReport();
      return { data, source, timestamp: Date.now() };
    } catch (apiError) {
      if (source === 'api' && this.enableFallback) {
        console.warn('⚠️ DashboardDataProvider: API failed, falling back to JSON');
        try {
          const data = await jsonDataProvider.fetchQAReport();
          return { data, source: 'fallback', timestamp: Date.now() };
        } catch (jsonError) {
          throw new Error(`Both API and JSON failed. API: ${apiError}. JSON: ${jsonError}`);
        }
      }
      throw apiError;
    }
  }

  async fetchCallAnalyticsData(dataSource?: DataSource): Promise<DataResponse<CallAnalyticsData>> {
    const source = dataSource || this.defaultSource;
    
    try {
      const data = await this.getProvider(source).fetchCallAnalyticsData();
      return { data, source, timestamp: Date.now() };
    } catch (apiError) {
      if (source === 'api' && this.enableFallback) {
        console.warn('⚠️ DashboardDataProvider: API failed, falling back to JSON');
        try {
          const data = await jsonDataProvider.fetchCallAnalyticsData();
          return { data, source: 'fallback', timestamp: Date.now() };
        } catch (jsonError) {
          throw new Error(`Both API and JSON failed. API: ${apiError}. JSON: ${jsonError}`);
        }
      }
      throw apiError;
    }
  }

  getDefaultSource(): DataSource {
    return this.defaultSource;
  }

  setDefaultSource(source: DataSource): void {
    this.defaultSource = source;
    console.log(`📋 DashboardDataProvider: Default source changed to ${source}`);
  }

  clearCache(): void {
    apiDataProvider.clearCache();
    jsonDataProvider.clearCache();
    console.log('🗑️ DashboardDataProvider: All caches cleared');
  }
}

export const dashboardDataProvider = new DashboardDataProvider();
```

## Data Models

### QA Analysis Data (existing type)

```typescript
// Already defined in src/types/qa-analysis.ts
export interface QAAnalysisData {
  analysis_summary: AnalysisSummary;
  team_performance_summary: TeamPerformanceSummary;
  revenue_impact: RevenueImpact;
  individual_call_analysis: IndividualCallAnalysis[];
  alerts_and_flags: AlertFlag[];
}
```

### Call Analytics Data (existing type)

```typescript
// Already defined in src/services/callAnalyticsService.ts
export interface CallAnalyticsData {
  analysis_period: string;
  total_calls_analyzed: number;
  analysis_timestamp: string;
  overall_quality_score: number;
  quality_trend: 'improving' | 'declining' | 'stable';
  deals_at_risk: DealAtRisk[];
  conversion_metrics: ConversionMetrics;
  // ... other fields
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Config service stores valid dataSource values

*For any* valid DataSource value ('api' or 'json') set in configuration, the Config_Service SHALL store and return that exact value when `getDataSource()` is called.

**Validates: Requirements 1.1, 1.5**

### Property 2: Data provider routes to correct provider based on dataSource

*For any* data request with a specified dataSource parameter, the Dashboard_Data_Provider SHALL route the request to the API_Provider when dataSource is 'api', and to the JSON_Provider when dataSource is 'json'.

**Validates: Requirements 2.1, 2.2, 2.3**

### Property 3: Data format consistency (round-trip property)

*For any* valid data that exists in both API and JSON sources, fetching via API_Provider and JSON_Provider SHALL return structurally equivalent data that can be used interchangeably by UI components.

**Validates: Requirements 2.5**

### Property 4: Cache returns cached data within TTL

*For any* successful API request, if the same request is made again within the cache TTL period, the API_Provider SHALL return the cached data without making a new API call.

**Validates: Requirements 3.2, 3.3**

### Property 5: Cache-busting parameters added to JSON fetches

*For any* JSON file fetch, the JSON_Provider SHALL append a unique timestamp query parameter to the URL to prevent browser caching.

**Validates: Requirements 4.2**

### Property 6: JSON data transformed to match expected schema

*For any* valid JSON file loaded by JSON_Provider, the returned data SHALL conform to the same TypeScript interface as data returned by API_Provider.

**Validates: Requirements 4.3**

### Property 7: Fallback to JSON when API fails

*For any* API request that fails (after retries), if fallback is enabled, the Dashboard_Data_Provider SHALL automatically attempt to load the equivalent data from JSON_Provider.

**Validates: Requirements 5.1, 10.3**

### Property 8: Response includes source field reflecting actual data origin

*For any* successful data response from Dashboard_Data_Provider, the response SHALL include a `source` field with value 'api' when data came from API_Provider, 'json' when explicitly requested from JSON_Provider, or 'fallback' when JSON was used after API failure.

**Validates: Requirements 5.2, 7.2, 7.3, 7.4, 7.5**

### Property 9: Cache clearing invalidates cached data

*For any* cached data in API_Provider, after calling `clearCache()`, the next request for that data SHALL fetch fresh data from the source rather than returning cached data.

**Validates: Requirements 8.1, 8.2, 8.3**

### Property 10: Provider errors include status and context

*For any* failed request, the thrown error SHALL include the HTTP status code (if applicable) and enough context (endpoint, source) to identify the failure point.

**Validates: Requirements 10.1, 10.2**

## Error Handling

### Error Types

```typescript
// src/types/dataProvider.types.ts

export class DataProviderError extends Error {
  constructor(
    message: string,
    public source: DataSource,
    public endpoint: string,
    public statusCode?: number,
    public originalError?: Error
  ) {
    super(message);
    this.name = 'DataProviderError';
  }
}

export class FallbackError extends Error {
  constructor(
    message: string,
    public apiError: Error,
    public jsonError: Error
  ) {
    super(message);
    this.name = 'FallbackError';
  }
}
```

### Error Handling Flow

```
API Request
    │
    ▼
┌─────────────────┐
│ Try API call    │
└─────────────────┘
    │
    ├── Success ──► Return { data, source: 'api' }
    │
    ▼ Failure
┌─────────────────┐
│ Retry (3x)      │
└─────────────────┘
    │
    ├── Success ──► Return { data, source: 'api' }
    │
    ▼ All retries failed
┌─────────────────┐
│ Fallback        │
│ enabled?        │
└─────────────────┘
    │
    ├── No ──► Throw DataProviderError
    │
    ▼ Yes
┌─────────────────┐
│ Try JSON        │
└─────────────────┘
    │
    ├── Success ──► Return { data, source: 'fallback' }
    │
    ▼ Failure
Throw FallbackError (contains both errors)
```

## Testing Strategy

### Unit Tests

Unit tests will verify specific examples and edge cases:

1. **Config Service Tests**
   - Test default dataSource value when not configured
   - Test environment variable override
   - Test config.json override priority

2. **API Provider Tests**
   - Test successful API fetch
   - Test cache hit within TTL
   - Test cache miss after TTL expiry
   - Test retry on failure
   - Test error after max retries

3. **JSON Provider Tests**
   - Test successful JSON file load
   - Test cache-busting parameter presence
   - Test error on missing file

4. **Dashboard Data Provider Tests**
   - Test routing to correct provider
   - Test fallback on API failure
   - Test error when both fail
   - Test source field in response

### Property-Based Tests

Property-based tests will use **fast-check** library to verify universal properties across many generated inputs.

Each property test must run minimum 100 iterations and be tagged with the design property it validates.

```typescript
// Example property test structure
import fc from 'fast-check';

describe('DashboardDataProvider Properties', () => {
  // Feature: dual-mode-data-provider, Property 2: Data provider routes to correct provider
  it('should route to correct provider based on dataSource', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('api', 'json'),
        async (dataSource) => {
          // Mock providers and verify correct one is called
          const result = await dashboardDataProvider.fetchQAAnalysisData(
            undefined, undefined, undefined, dataSource
          );
          expect(result.source).toBe(dataSource);
        }
      ),
      { numRuns: 100 }
    );
  });
});
```

### Test Configuration

```typescript
// vitest.config.ts additions
export default defineConfig({
  test: {
    // ... existing config
    testTimeout: 30000, // Allow time for property tests
  }
});
```

## Configuration Updates

### Environment Variables

Add to `.env.example`:

```bash
# Data Source Configuration
# Options: 'api' (default) or 'json'
VITE_DATA_SOURCE=api

# Enable automatic fallback to JSON when API fails
# Options: 'true' (default) or 'false'
VITE_ENABLE_FALLBACK=true
```

### Config.json Updates

Add to `public/config.json`:

```json
{
  "version": "1.0.0",
  "api": {
    "baseUrl": "https://call-api.totogicore.com",
    "timeout": 30000
  },
  "dataSource": "api",
  "enableFallback": true,
  "cognito": {
    // ... existing cognito config
  }
}
```

### ConfigService Updates

Update `src/services/configService.ts` to include dataSource:

```typescript
export interface AppConfig {
  api: ApiConfig;
  cognito: CognitoConfig;
  bypassAuth: boolean;
  environment: 'development' | 'staging' | 'production';
  dataSource: DataSource;      // NEW
  enableFallback: boolean;     // NEW
}
```

## Migration Path

### Phase 1: Add New Services (Non-Breaking)

1. Create `src/types/dataProvider.types.ts`
2. Create `src/services/providers/apiDataProvider.ts`
3. Create `src/services/providers/jsonDataProvider.ts`
4. Create `src/services/dashboardDataProvider.ts`
5. Update `configService.ts` with new fields

### Phase 2: Update Existing Services

1. Update `QAAnalyticsService` to use `dashboardDataProvider`
2. Update `CallAnalyticsService` to use `dashboardDataProvider`
3. Add optional `dataSource` parameter to service methods

### Phase 3: Component Updates (Optional)

1. Components can optionally display data source indicator
2. Add refresh button that clears cache and refetches

## File Structure

```
src/
├── services/
│   ├── providers/
│   │   ├── apiDataProvider.ts       # NEW
│   │   ├── jsonDataProvider.ts      # NEW
│   │   └── dataProvider.interface.ts # NEW
│   ├── dashboardDataProvider.ts     # NEW
│   ├── configService.ts             # UPDATED
│   ├── qaAnalyticsService.ts        # UPDATED
│   └── callAnalyticsService.ts      # UPDATED
├── types/
│   └── dataProvider.types.ts        # NEW
└── test/
    └── providers/
        ├── apiDataProvider.test.ts  # NEW
        ├── jsonDataProvider.test.ts # NEW
        └── dashboardDataProvider.test.ts # NEW
```
