# Implementation Plan: Dual-Mode Data Provider

## Overview

This implementation plan breaks down the dual-mode data provider feature into discrete coding tasks. Each task builds on previous tasks, ensuring incremental progress with no orphaned code. The implementation follows a bottom-up approach: types → providers → router → service integration.

## Tasks

- [x] 1. Create type definitions and interfaces
  - [x] 1.1 Create data provider types file
    - Create `src/types/dataProvider.types.ts`
    - Define `DataSource`, `ResponseSource`, `DataResponse<T>`, `CacheEntry<T>` types
    - Define `DataProviderConfig` interface
    - Define `DataProviderError` and `FallbackError` error classes
    - _Requirements: 9.1, 9.3, 9.4, 10.1, 10.2_

  - [x] 1.2 Create provider interface
    - Create `src/services/providers/dataProvider.interface.ts`
    - Define `IDataProvider` interface with all required methods
    - Import existing types from `qa-analysis.ts` and `callAnalyticsService.ts`
    - _Requirements: 9.2_

- [x] 2. Implement JSON Data Provider
  - [x] 2.1 Create JSON provider implementation
    - Create `src/services/providers/jsonDataProvider.ts`
    - Implement `IDataProvider` interface
    - Implement `fetchQAAnalysisData()` loading from `/results/analysis.json`
    - Implement `fetchQAReport()` loading from `/results/report.md`
    - Implement `fetchCallAnalyticsData()` loading from `/transcripts/ai_enhanced_analysis_all_scripts_report.json`
    - Add cache-busting timestamp query parameter to all fetch URLs
    - Add console logging with emoji prefixes
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 2.2 Write property test for cache-busting
    - **Property 5: Cache-busting parameters added to JSON fetches**
    - **Validates: Requirements 4.2**

- [x] 3. Implement API Data Provider
  - [x] 3.1 Create API provider implementation
    - Create `src/services/providers/apiDataProvider.ts`
    - Implement `IDataProvider` interface
    - Implement caching with configurable TTL (default 5 minutes)
    - Implement `fetchWithRetry()` with exponential backoff (3 attempts, 1s base delay)
    - Implement `fetchQAAnalysisData()` calling `/api/v1/qa/analysis`
    - Implement `fetchQAReport()` calling `/api/v1/qa/report`
    - Implement `fetchCallAnalyticsData()` calling `/api/v1/qa/call-analytics`
    - Implement `clearCache()` method
    - Add console logging with emoji prefixes
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 3.2 Write property test for caching behavior
    - **Property 4: Cache returns cached data within TTL**
    - **Validates: Requirements 3.2, 3.3**

  - [ ] 3.3 Write unit tests for retry logic
    - Test retry on transient failure
    - Test error after max retries exhausted
    - Test exponential backoff timing
    - _Requirements: 3.4, 3.5_

- [ ] 4. Checkpoint - Verify providers work independently
  - Ensure JSON provider loads files correctly
  - Ensure API provider calls endpoints correctly
  - Ensure all tests pass, ask the user if questions arise

- [x] 5. Implement Dashboard Data Provider (Router)
  - [x] 5.1 Create dashboard data provider
    - Create `src/services/dashboardDataProvider.ts`
    - Import both `apiDataProvider` and `jsonDataProvider`
    - Implement `getProvider(source)` method to select provider
    - Implement `fetchQAAnalysisData()` with dataSource parameter and fallback
    - Implement `fetchQAReport()` with dataSource parameter and fallback
    - Implement `fetchCallAnalyticsData()` with dataSource parameter and fallback
    - Implement `clearCache()` that clears both providers
    - Implement `getDefaultSource()` and `setDefaultSource()` methods
    - Return `DataResponse<T>` with source field from all methods
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.1, 5.2, 5.3, 5.4, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1_

  - [ ] 5.2 Write property test for routing
    - **Property 2: Data provider routes to correct provider based on dataSource**
    - **Validates: Requirements 2.1, 2.2, 2.3**

  - [ ] 5.3 Write property test for fallback behavior
    - **Property 7: Fallback to JSON when API fails**
    - **Validates: Requirements 5.1, 10.3**

  - [ ] 5.4 Write property test for source field
    - **Property 8: Response includes source field reflecting actual data origin**
    - **Validates: Requirements 5.2, 7.2, 7.3, 7.4, 7.5**

- [x] 6. Update Configuration Service
  - [x] 6.1 Add dataSource configuration support
    - Update `src/services/configService.ts`
    - Add `dataSource: DataSource` to `AppConfig` interface
    - Add `enableFallback: boolean` to `AppConfig` interface
    - Update `loadFromEnvironment()` to read `VITE_DATA_SOURCE` and `VITE_ENABLE_FALLBACK`
    - Update `fetchConfigJson()` to read `dataSource` and `enableFallback` from config.json
    - Add `getDataSource()` method
    - Update default config to include `dataSource: 'api'` and `enableFallback: true`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ] 6.2 Write property test for config storage
    - **Property 1: Config service stores valid dataSource values**
    - **Validates: Requirements 1.1, 1.5**

- [ ] 7. Checkpoint - Verify router and config work together
  - Ensure dashboard data provider initializes with config
  - Ensure routing works based on config
  - Ensure fallback works when API fails
  - Ensure all tests pass, ask the user if questions arise

- [x] 8. Integrate with existing services
  - [x] 8.1 Update QAAnalyticsService
    - Update `src/services/qaAnalyticsService.ts`
    - Import `dashboardDataProvider`
    - Update `fetchAnalysisData()` to use `dashboardDataProvider.fetchQAAnalysisData()`
    - Add optional `dataSource` parameter to `fetchAnalysisData()`
    - Update `fetchReport()` to use `dashboardDataProvider.fetchQAReport()`
    - Preserve existing public API methods
    - Update cache clearing to use dashboard provider
    - _Requirements: 6.1, 6.3, 6.4, 6.5_

  - [x] 8.2 Update CallAnalyticsService
    - Update `src/services/callAnalyticsService.ts`
    - Import `dashboardDataProvider`
    - Update `loadAnalyticsData()` to use `dashboardDataProvider.fetchCallAnalyticsData()`
    - Add optional `dataSource` parameter to `loadAnalyticsData()`
    - Preserve existing public API methods
    - Update cache clearing to use dashboard provider
    - _Requirements: 6.2, 6.3, 6.4, 6.5_

  - [ ] 8.3 Write unit tests for service integration
    - Test QAAnalyticsService uses dashboard provider
    - Test CallAnalyticsService uses dashboard provider
    - Test backward compatibility with existing method signatures
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 9. Update configuration files
  - [x] 9.1 Update environment example file
    - Update `nexus-ui/.env.example`
    - Add `VITE_DATA_SOURCE=api` with documentation comment
    - Add `VITE_ENABLE_FALLBACK=true` with documentation comment
    - _Requirements: 1.2_

  - [x] 9.2 Update config.json
    - Update `nexus-ui/public/config.json`
    - Add `"dataSource": "api"` field
    - Add `"enableFallback": true` field
    - _Requirements: 1.3_

- [ ] 10. Final checkpoint - Full integration test
  - Test with `dataSource: 'api'` - verify API calls are made
  - Test with `dataSource: 'json'` - verify JSON files are loaded
  - Test fallback by simulating API failure
  - Verify source field is correct in all scenarios
  - Ensure all tests pass, ask the user if questions arise

- [ ] 11. Write property test for data format consistency
  - **Property 3: Data format consistency (round-trip property)**
  - Test that data from API and JSON providers can be used interchangeably
  - **Validates: Requirements 2.5**

- [ ] 12. Write property test for cache clearing
  - **Property 9: Cache clearing invalidates cached data**
  - **Validates: Requirements 8.1, 8.2, 8.3**

- [ ] 13. Write property test for error handling
  - **Property 10: Provider errors include status and context**
  - **Validates: Requirements 10.1, 10.2**

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation preserves backward compatibility with existing services
- Components don't need to change - they continue using existing service methods
