# Requirements Document

## Introduction

This document specifies the requirements for implementing a dual-mode data fetching strategy in the Nexus Telco QA Dashboard application. The system will support two data sources: **API mode** (fetching from backend API) and **JSON mode** (loading from static JSON files in the public folder). This pattern mirrors the successful implementation in the alert-engine-ui project, providing graceful degradation and development flexibility.

## Glossary

- **Data_Provider**: A service that abstracts data fetching logic and routes requests to the appropriate data source
- **Data_Source**: The origin of data, either 'api' (backend API) or 'json' (static JSON files)
- **API_Provider**: A service that fetches data from the backend API endpoints
- **JSON_Provider**: A service that loads data from static JSON files in the /public folder
- **Dashboard_Data_Provider**: The main router service that switches between API_Provider and JSON_Provider
- **Config_Service**: The existing configuration service that manages application settings
- **Cache_TTL**: Time-to-live duration for cached data before it expires
- **Fallback**: The automatic switch to JSON_Provider when API_Provider fails

## Requirements

### Requirement 1: Data Source Configuration

**User Story:** As a developer, I want to configure the data source mode via environment variables and runtime config, so that I can easily switch between API and JSON modes without code changes.

#### Acceptance Criteria

1. THE Config_Service SHALL support a new `dataSource` configuration field with values 'api' or 'json'
2. WHEN the `VITE_DATA_SOURCE` environment variable is set, THE Config_Service SHALL use its value as the default data source
3. WHEN the `/config.json` file contains a `dataSource` field, THE Config_Service SHALL use it to override the environment variable
4. WHERE no data source is configured, THE Config_Service SHALL default to 'api' mode
5. THE Config_Service SHALL expose a `getDataSource()` method that returns the current data source setting

### Requirement 2: Dashboard Data Provider Router

**User Story:** As a developer, I want a unified data provider that routes requests to the appropriate source, so that components don't need to know which data source is being used.

#### Acceptance Criteria

1. THE Dashboard_Data_Provider SHALL accept a `dataSource` parameter on each method call to override the default source
2. WHEN `dataSource` is 'api', THE Dashboard_Data_Provider SHALL route requests to the API_Provider
3. WHEN `dataSource` is 'json', THE Dashboard_Data_Provider SHALL route requests to the JSON_Provider
4. THE Dashboard_Data_Provider SHALL provide methods matching the existing service interfaces (QA analytics, call analytics, etc.)
5. THE Dashboard_Data_Provider SHALL return data in identical format regardless of the data source used

### Requirement 3: API Data Provider

**User Story:** As a developer, I want an API provider that fetches data from the backend with caching and retry logic, so that API calls are efficient and resilient.

#### Acceptance Criteria

1. THE API_Provider SHALL fetch data from the backend API using the existing apiClient
2. THE API_Provider SHALL implement caching with configurable TTL (default 5 minutes)
3. WHEN a cached response exists and is not expired, THE API_Provider SHALL return the cached data
4. THE API_Provider SHALL implement retry logic with exponential backoff (3 attempts, starting at 1 second)
5. WHEN an API call fails after all retries, THE API_Provider SHALL throw an error with descriptive message
6. THE API_Provider SHALL log API call status using console with emoji prefixes (🔄 loading, ✅ success, ❌ error)

### Requirement 4: JSON Data Provider

**User Story:** As a developer, I want a JSON provider that loads data from static files, so that the dashboard works without a backend API.

#### Acceptance Criteria

1. THE JSON_Provider SHALL load data from JSON files in the `/public/results/` directory
2. THE JSON_Provider SHALL add cache-busting query parameters to prevent browser caching
3. THE JSON_Provider SHALL transform JSON data to match the expected UI data format
4. WHEN a JSON file fails to load, THE JSON_Provider SHALL throw an error with the file path and status code
5. THE JSON_Provider SHALL support loading from the following files:
   - `/results/analysis.json` for QA analysis data
   - `/transcripts/ai_enhanced_analysis_all_scripts_report.json` for call analytics data

### Requirement 5: Automatic Fallback Mechanism

**User Story:** As a user, I want the dashboard to automatically fall back to JSON data when the API is unavailable, so that I always see data.

#### Acceptance Criteria

1. WHEN the API_Provider fails to fetch data, THE Dashboard_Data_Provider SHALL automatically attempt to load from JSON_Provider
2. THE Dashboard_Data_Provider SHALL return a `source` field indicating which provider returned the data ('api' or 'json')
3. WHEN fallback occurs, THE Dashboard_Data_Provider SHALL log a warning message indicating the fallback
4. IF both API_Provider and JSON_Provider fail, THEN THE Dashboard_Data_Provider SHALL throw an error with details from both failures

### Requirement 6: Service Integration

**User Story:** As a developer, I want the existing services (QAAnalyticsService, CallAnalyticsService) to use the new data provider, so that all data fetching goes through the unified system.

#### Acceptance Criteria

1. THE QAAnalyticsService SHALL use Dashboard_Data_Provider for fetching analysis data
2. THE CallAnalyticsService SHALL use Dashboard_Data_Provider for fetching call analytics data
3. WHEN services use Dashboard_Data_Provider, THE services SHALL preserve their existing public API methods
4. THE services SHALL accept an optional `dataSource` parameter to override the default source
5. THE services SHALL maintain backward compatibility with existing component usage

### Requirement 7: Data Source Indicator

**User Story:** As a user, I want to see which data source is currently active, so that I know if I'm viewing live or cached data.

#### Acceptance Criteria

1. THE Dashboard_Data_Provider SHALL track and expose the current data source being used
2. WHEN data is fetched, THE Dashboard_Data_Provider SHALL include a `source` property in the response
3. THE source property SHALL have value 'api' when data comes from the API_Provider
4. THE source property SHALL have value 'json' when data comes from the JSON_Provider
5. THE source property SHALL have value 'fallback' when data comes from JSON_Provider after API failure

### Requirement 8: Cache Management

**User Story:** As a developer, I want to manage the data cache, so that I can force refresh data when needed.

#### Acceptance Criteria

1. THE Dashboard_Data_Provider SHALL expose a `clearCache()` method that clears all cached data
2. THE API_Provider SHALL expose a `clearCache()` method that clears its internal cache
3. WHEN `clearCache()` is called, THE next data request SHALL fetch fresh data from the source
4. THE Dashboard_Data_Provider SHALL support per-endpoint cache TTL configuration
5. THE default cache TTL SHALL be 5 minutes for most endpoints and 2 minutes for frequently changing data

### Requirement 9: Type Safety

**User Story:** As a developer, I want type-safe data provider interfaces, so that I get compile-time errors for incorrect usage.

#### Acceptance Criteria

1. THE Dashboard_Data_Provider SHALL define TypeScript interfaces for all data types
2. THE API_Provider and JSON_Provider SHALL implement the same interface
3. THE DataSource type SHALL be defined as `'api' | 'json'`
4. THE response types SHALL include the `source` field in their type definitions
5. THE Dashboard_Data_Provider methods SHALL have proper return type annotations

### Requirement 10: Error Handling

**User Story:** As a developer, I want consistent error handling across data providers, so that I can handle failures gracefully.

#### Acceptance Criteria

1. WHEN an API request fails, THE API_Provider SHALL throw an ApiError with status code and message
2. WHEN a JSON file fails to load, THE JSON_Provider SHALL throw an Error with file path and HTTP status
3. THE Dashboard_Data_Provider SHALL catch provider errors and attempt fallback before re-throwing
4. IF fallback is disabled and API fails, THEN THE Dashboard_Data_Provider SHALL throw the original API error
5. THE error messages SHALL include enough context to debug the issue (endpoint, status, source)

