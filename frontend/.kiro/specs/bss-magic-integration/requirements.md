# Requirements Document

## Introduction

This specification defines the "Ontos" FDW/TMF UI integration for the nexus-ui application. Ontos is a new top-level sidebar section that provides a unified interface for browsing Foreign Data Wrapper (FDW) metadata, exploring TMF (TeleManagement Forum) API standards and object types, and executing queries against both FDW foreign tables and TMF API endpoints. The feature consumes the existing nexus-backend FDW and TMF API endpoints (`/api/fdw/*`, `/tmf-api/*`, `/health/fdw`).

## Glossary

- **Ontos_Workspace**: The top-level container component rendered when the user selects the "Ontos" sidebar menu item, containing a tabbed sub-navigation for Dashboard, FDW Explorer, TMF Registry, TMF Objects, and Query Builder views
- **Ontos_Dashboard**: A summary view displaying FDW health status, foreign server count, foreign table count, TMF standards count, and connection latency
- **FDW_Explorer**: A view for browsing foreign servers, their associated foreign tables, and column schemas
- **TMF_Registry**: A view for browsing loaded TMF standards, their resources, and available HTTP operations
- **TMF_Object_Browser**: A view for inspecting TMF type definitions from types.json, including field names, types, and nested references
- **Query_Builder**: A dual-mode view for constructing and executing FDW raw queries and TMF API requests
- **FDW_Service**: A frontend service module (`fdwService.ts`) that wraps FDW backend API calls using the existing apiClient
- **TMF_Service**: A frontend service module (`tmfService.ts`) that wraps TMF backend API calls using the existing apiClient
- **Sidebar**: The existing collapsible left navigation panel in the nexus-ui application
- **apiClient**: The existing authenticated fetch wrapper that reads configuration from `/config.json`

## Requirements

### Requirement 1: Ontos Sidebar Navigation

**User Story:** As a user, I want an "Ontos" menu item in the sidebar, so that I can access FDW and TMF capabilities from the main navigation.

#### Acceptance Criteria

1. THE Sidebar SHALL display an "Ontos" button with a Database icon (from Lucide React) between the "AI Workspace" button and the "Operations" button
2. WHEN the user clicks the "Ontos" button, THE Sidebar SHALL set the current view to the Ontos_Workspace
3. WHILE the Ontos_Workspace is the active view, THE Sidebar SHALL highlight the "Ontos" button with the active style (`bg-[#003366] text-white`)
4. WHEN the sidebar is collapsed, THE Sidebar SHALL display only the Database icon for the Ontos menu item
5. WHEN the sidebar is expanded, THE Sidebar SHALL display the Database icon and the label "Ontos" for the menu item

### Requirement 2: Ontos Workspace Container

**User Story:** As a user, I want a tabbed workspace for Ontos features, so that I can navigate between FDW exploration, TMF browsing, and query execution.

#### Acceptance Criteria

1. THE Ontos_Workspace SHALL provide a horizontal tab bar with five tabs: "Dashboard", "FDW Explorer", "TMF Registry", "TMF Objects", and "Query Builder"
2. WHEN the user clicks a tab, THE Ontos_Workspace SHALL display the corresponding content panel
3. THE Ontos_Workspace SHALL default to the "Dashboard" tab on initial load
4. THE Ontos_Workspace SHALL preserve the selected tab when switching away from and back to the Ontos view within the same session

### Requirement 3: Ontos Dashboard

**User Story:** As a user, I want an overview dashboard for FDW/TMF status, so that I can quickly assess the health and scope of connected data sources.

#### Acceptance Criteria

1. WHEN the Dashboard tab is active, THE Ontos_Dashboard SHALL call the `GET /health/fdw` endpoint and display the connection status as a color-coded indicator (green for healthy, red for error)
2. THE Ontos_Dashboard SHALL display the foreign servers count, foreign tables count, and connection latency from the health endpoint response
3. THE Ontos_Dashboard SHALL display the number of loaded TMF standards by calling `GET /api/fdw/tmf/standards` and counting the returned standard keys
4. THE Ontos_Dashboard SHALL auto-refresh health data every 30 seconds
5. IF the health endpoint returns an error, THEN THE Ontos_Dashboard SHALL display an error card with the error message and a retry button
6. WHILE health data is loading, THE Ontos_Dashboard SHALL display skeleton loaders in place of the status cards

### Requirement 4: FDW Explorer

**User Story:** As a user, I want to browse foreign servers, tables, and column schemas, so that I can understand the available FDW data sources.

#### Acceptance Criteria

1. WHEN the FDW Explorer tab is active, THE FDW_Explorer SHALL call `GET /api/fdw/servers` and display a list of foreign servers showing server name and wrapper type
2. WHEN the user selects a server, THE FDW_Explorer SHALL call `GET /api/fdw/tables?server={serverName}` and display the associated foreign tables showing table name, schema, and column count
3. WHEN the user selects a table, THE FDW_Explorer SHALL call `GET /api/fdw/tables/{schema}/{table}/columns` and display the column details in a table showing column name, data type, nullable status, and ordinal position
4. THE FDW_Explorer SHALL provide a search input that filters the displayed servers and tables by name
5. WHEN the user clicks a refresh button, THE FDW_Explorer SHALL re-fetch server and table data from the backend
6. WHILE server or table data is loading, THE FDW_Explorer SHALL display skeleton loaders
7. IF the server or table fetch fails, THEN THE FDW_Explorer SHALL display an error message with a retry button
8. WHEN no foreign servers are configured, THE FDW_Explorer SHALL display an empty state message: "No foreign servers configured"

### Requirement 5: TMF Registry

**User Story:** As a user, I want to view loaded TMF standards and their resources, so that I can understand which TMF APIs are available.

#### Acceptance Criteria

1. WHEN the TMF Registry tab is active, THE TMF_Registry SHALL call `GET /api/fdw/tmf/standards` and display each TMF standard (TMF620, TMF629, etc.) as an expandable section
2. WHEN the user expands a standard, THE TMF_Registry SHALL display the list of resources under that standard (productOffering, customer, etc.)
3. THE TMF_Registry SHALL display colored badges for each available HTTP method (GET, POST, PATCH, DELETE) next to each resource
4. WHEN the user clicks a resource, THE TMF_Registry SHALL display the API path pattern for that resource
5. THE TMF_Registry SHALL provide a button on each resource to navigate to the Query Builder pre-filled with that standard and resource
6. WHILE TMF standards data is loading, THE TMF_Registry SHALL display skeleton loaders
7. IF the TMF standards fetch fails, THEN THE TMF_Registry SHALL display an error message with a retry button

### Requirement 6: TMF Object Browser

**User Story:** As a user, I want to inspect TMF type definitions, so that I can understand the structure of TMF objects returned by the API.

#### Acceptance Criteria

1. THE TMF_Object_Browser SHALL display a searchable list of TMF type names loaded from the backend
2. WHEN the user selects a type, THE TMF_Object_Browser SHALL display the field definitions in a structured view showing field name, type (string, object, array), and required/optional status
3. WHEN a field has a `$ref` reference to another type, THE TMF_Object_Browser SHALL render the reference as a clickable link that navigates to that referenced type
4. THE TMF_Object_Browser SHALL provide a toggle to switch between a structured field view and a raw JSON view of the type definition
5. WHILE type data is loading, THE TMF_Object_Browser SHALL display skeleton loaders
6. IF the type data fetch fails, THEN THE TMF_Object_Browser SHALL display an error message with a retry button

### Requirement 7: Query Builder - FDW Raw Query Mode

**User Story:** As a user, I want to build and execute raw FDW queries against foreign tables, so that I can retrieve and inspect data from connected sources.

#### Acceptance Criteria

1. THE Query_Builder SHALL provide a "FDW Raw Query" mode accessible via a tab or toggle
2. WHEN in FDW Raw Query mode, THE Query_Builder SHALL display dropdown selectors for schema and table, populated from the FDW discovery endpoints
3. WHEN the user selects a table, THE Query_Builder SHALL populate a multi-select column picker with the discovered columns for that table
4. THE Query_Builder SHALL provide a filter builder where the user can add filter rows with a column dropdown, an operator dropdown (eq, neq, gt, gte, lt, lte, like, in), and a value input
5. THE Query_Builder SHALL provide order-by controls with column selection and direction toggle (ASC/DESC)
6. THE Query_Builder SHALL provide limit and offset numeric inputs
7. WHEN the user clicks "Execute", THE Query_Builder SHALL call `POST /api/fdw/query` with the constructed request body and display the results
8. THE Query_Builder SHALL display query results in a data table with sortable column headers
9. THE Query_Builder SHALL provide a toggle to switch between table view and raw JSON view of the results
10. THE Query_Builder SHALL display query metadata: duration (ms), row count, and table queried
11. IF the query execution fails, THEN THE Query_Builder SHALL display the error message in an error card
12. WHILE a query is executing, THE Query_Builder SHALL display a loading indicator and disable the Execute button

### Requirement 8: Query Builder - TMF API Mode

**User Story:** As a user, I want to execute TMF API requests with filtering, sorting, and pagination, so that I can query TMF-compliant data through the standard API.

#### Acceptance Criteria

1. THE Query_Builder SHALL provide a "TMF API" mode accessible via a tab or toggle
2. WHEN in TMF API mode, THE Query_Builder SHALL display a standard selector dropdown populated from the TMF standards endpoint
3. WHEN the user selects a standard, THE Query_Builder SHALL display a resource selector dropdown populated with the resources for that standard
4. THE Query_Builder SHALL display an HTTP method selector (GET, POST, PATCH, DELETE)
5. WHEN the HTTP method is GET (list), THE Query_Builder SHALL display fields selector, sort builder, limit/offset inputs, and a filter builder for TMF query parameters
6. WHEN the HTTP method is GET by ID, PATCH, or DELETE, THE Query_Builder SHALL display a resource ID text input
7. WHEN the HTTP method is POST or PATCH, THE Query_Builder SHALL display a JSON body editor textarea
8. WHEN the user clicks "Execute", THE Query_Builder SHALL call the appropriate TMF API endpoint and display the response
9. THE Query_Builder SHALL display the response in a JSON tree view with a toggle to switch to a raw JSON view
10. THE Query_Builder SHALL display request metadata: HTTP status code, response duration, and the URL called
11. IF the TMF API request fails, THEN THE Query_Builder SHALL display the error details including HTTP status code and error body
12. WHILE a TMF API request is executing, THE Query_Builder SHALL display a loading indicator and disable the Execute button

### Requirement 9: Service Layer

**User Story:** As a developer, I want dedicated service modules for FDW and TMF API calls, so that API communication is encapsulated and reusable.

#### Acceptance Criteria

1. THE FDW_Service SHALL provide functions for: listing foreign servers, listing foreign tables (with optional server filter), getting table columns, executing FDW queries, fetching FDW health, and listing TMF standards
2. THE TMF_Service SHALL provide functions for: executing TMF GET (list), GET (by ID), POST, PATCH, and DELETE requests against the `/tmf-api/` endpoints
3. THE FDW_Service and TMF_Service SHALL use the existing apiClient for all HTTP requests
4. IF an API call fails, THEN THE FDW_Service and TMF_Service SHALL throw structured errors containing the HTTP status code and error message

### Requirement 10: State Management with React Query

**User Story:** As a developer, I want consistent cache management for all Ontos API calls, so that data is fresh and network requests are minimized.

#### Acceptance Criteria

1. THE Ontos_Workspace SHALL use React Query (TanStack Query) for all API data fetching
2. THE Ontos_Workspace SHALL use the cache key `['fdw', 'health']` for FDW health data with a refetch interval of 30 seconds
3. THE Ontos_Workspace SHALL use the cache key `['fdw', 'servers']` for foreign server data with a stale time of 5 minutes
4. THE Ontos_Workspace SHALL use the cache key `['fdw', 'tables', serverFilter]` for foreign table data with a stale time of 5 minutes
5. THE Ontos_Workspace SHALL use the cache key `['fdw', 'columns', schema, table]` for column data with a stale time of 5 minutes
6. THE Ontos_Workspace SHALL use the cache key `['fdw', 'tmf', 'standards']` for TMF standards data with a stale time of 10 minutes
7. THE Ontos_Workspace SHALL not cache query execution results (FDW queries and TMF API calls use fresh data on each execution)

### Requirement 11: Shared UI Patterns

**User Story:** As a user, I want consistent loading, error, and empty states across all Ontos views, so that the experience is predictable and informative.

#### Acceptance Criteria

1. WHILE data is loading in any Ontos view, THE Ontos_Workspace SHALL display skeleton loaders matching the layout of the expected content
2. IF an API call fails in any Ontos view, THEN THE Ontos_Workspace SHALL display an error card with the error message and a retry button
3. WHEN a view has no data to display, THE Ontos_Workspace SHALL display a contextual empty state message
4. WHEN a query executes successfully, THE Ontos_Workspace SHALL display a success toast notification
5. WHEN a query execution fails, THE Ontos_Workspace SHALL display an error toast notification with the error summary
6. THE Ontos_Workspace SHALL support the existing dark mode theme tokens and follow the application's current theme
