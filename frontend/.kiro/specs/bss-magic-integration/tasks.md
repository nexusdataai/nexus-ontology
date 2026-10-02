# Implementation Plan: Ontos FDW/TMF UI Integration

## Overview

Implement the Ontos workspace as a new top-level sidebar section in the nexus-ui application. The implementation proceeds bottom-up: types → services → components → integration, with property tests validating core logic at each layer.

## Tasks

- [x] 1. Create TypeScript types and service layer
  - [x] 1.1 Create `src/types/fdwTypes.ts` with all FDW and TMF TypeScript interfaces
    - Define ForeignServerInfo, ForeignTableInfo, ColumnInfo, FilterOperator, QueryFilter, OrderByItem, QueryRequest, QueryMetadata, QueryResponse, FdwHealthResponse, TmfStandardsResponse, TmfFieldDefinition, TmfTypeDefinition, TmfTypeMap
    - _Requirements: 9.1, 9.2_

  - [x] 1.2 Create `src/services/fdwService.ts` with FDW API client functions
    - Implement getHealth, listServers, listTables, getColumns, executeQuery, listTmfStandards
    - Use existing apiClient for all HTTP requests
    - _Requirements: 9.1, 9.3_

  - [x] 1.3 Create `src/services/tmfService.ts` with TMF API client functions
    - Implement execute (GET/POST/PATCH/DELETE), getTypeDefinitions
    - Construct URLs following `/tmf-api/{standard}/{resource}` pattern
    - Track request duration via performance.now()
    - Use existing apiClient for all HTTP requests
    - _Requirements: 9.2, 9.3_

  - [x] 1.4 Write property test for TMF URL construction
    - **Property 8: TMF API request URL is correctly constructed**
    - **Validates: Requirements 8.8**

  - [x] 1.5 Write property test for service error propagation
    - **Property 10: Service errors propagate with status and message**
    - **Validates: Requirements 9.4**

  - [x] 1.6 Write unit tests for fdwService and tmfService
    - Test each service function calls apiClient with correct endpoint
    - Test error handling for failed API calls
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 2. Create React Query keys and Ontos workspace shell
  - [x] 2.1 Create `src/components/ontos/queryKeys.ts` with cache key constants
    - Define ontosKeys object with health, servers, tables, columns, tmfStandards, tmfTypes keys
    - _Requirements: 10.2, 10.3, 10.4, 10.5, 10.6_

  - [x] 2.2 Create `src/components/ontos/OntosWorkspace.tsx` tabbed container
    - Use shadcn Tabs with 5 tabs: Dashboard, FDW Explorer, TMF Registry, TMF Objects, Query Builder
    - Default to Dashboard tab
    - Preserve selected tab in component state
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.3 Integrate Ontos into Sidebar and Index page
    - Add `onOntosSelect` prop and "Ontos" button (Database icon) to Sidebar.tsx between AI Workspace and Operations
    - Extend currentView type to include 'ontos' in Index.tsx
    - Add handleOntosSelect handler and OntosWorkspace rendering branch
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 3. Checkpoint - Verify shell integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement OntosDashboard
  - [x] 4.1 Create `src/components/ontos/OntosDashboard.tsx`
    - Use useQuery with key ontosKeys.health, refetchInterval: 30000
    - Use useQuery with key ontosKeys.tmfStandards, staleTime: 600000
    - Render 4 status cards: Connection Status (color-coded), Foreign Servers count, Foreign Tables count, TMF Standards count
    - Display latency value
    - Skeleton loaders while loading, error card with retry on failure
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 4.2 Write property test for dashboard health rendering
    - **Property 1: Dashboard renders all health fields**
    - **Validates: Requirements 3.2, 3.3**

- [x] 5. Implement FDW Explorer
  - [x] 5.1 Create `src/components/ontos/FdwExplorer.tsx`
    - Left panel: server list with useQuery key ontosKeys.servers (staleTime: 300000)
    - On server select: table list with useQuery key ontosKeys.tables(server) (staleTime: 300000)
    - Right panel: column table with useQuery key ontosKeys.columns(schema, table) (staleTime: 300000)
    - Search input filtering servers and tables by name (case-insensitive)
    - Refresh button invalidates server/table queries
    - Skeleton loaders, error cards with retry, empty state message
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 5.2 Write property test for FDW discovery rendering
    - **Property 2: FDW discovery items are fully rendered**
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [x] 5.3 Write property test for search filtering
    - **Property 3: Search filtering returns only matching items**
    - **Validates: Requirements 4.4**

- [x] 6. Implement TMF Registry
  - [x] 6.1 Create `src/components/ontos/TmfRegistry.tsx`
    - Use useQuery with key ontosKeys.tmfStandards (staleTime: 600000)
    - Render shadcn Accordion with one item per standard
    - Show resources with colored HTTP method badges (GET=green, POST=blue, PATCH=yellow, DELETE=red)
    - Display API path pattern on resource click
    - "Query" button navigates to Query Builder with pre-filled standard/resource
    - Skeleton loaders, error card with retry
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [x] 6.2 Write property test for TMF standards rendering
    - **Property 4: TMF standards and resources are fully rendered**
    - **Validates: Requirements 5.1, 5.2, 5.4, 8.2, 8.3**

- [x] 7. Checkpoint - Verify dashboard, explorer, and registry
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement TMF Object Browser
  - [x] 8.1 Create `src/components/ontos/TmfObjectBrowser.tsx`
    - Fetch type definitions from tmfService.getTypeDefinitions()
    - Left: searchable list of type names
    - Right: structured field view (field name, type, required/optional) with toggle to raw JSON
    - $ref fields rendered as clickable links that update selected type
    - Skeleton loaders, error card with retry
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 8.2 Write property test for TMF type definition rendering
    - **Property 5: TMF type definitions are fully rendered with navigable refs**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 9. Implement Query Builder
  - [x] 9.1 Create `src/components/ontos/QueryBuilder.tsx` with dual-mode tabs
    - Two tabs: "TMF API" and "FDW Raw Query"
    - Accept optional pre-fill props (standard, resource) from TMF Registry
    - _Requirements: 7.1, 8.1_

  - [x] 9.2 Create `src/components/ontos/FdwQueryMode.tsx`
    - Schema/table dropdowns from discovery endpoints
    - Column multi-select populated on table selection
    - Filter builder: add/remove rows with column, operator (eq/neq/gt/gte/lt/lte/like/in), value
    - Order-by controls with column + direction
    - Limit/offset numeric inputs
    - Execute button calls fdwService.executeQuery via useMutation
    - Results: data table + JSON view toggle
    - Metadata bar: durationMs, rowCount, tableQueried
    - Loading indicator, disabled Execute during execution, error card on failure
    - Success/error toast notifications
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11, 7.12, 11.4, 11.5_

  - [x] 9.3 Create `src/components/ontos/TmfQueryMode.tsx`
    - Standard/resource dropdowns from TMF standards endpoint
    - HTTP method selector (GET, POST, PATCH, DELETE)
    - Conditional form fields based on method (fields/sort/limit/offset for GET list; ID input for GET-by-ID/PATCH/DELETE; JSON body for POST/PATCH)
    - Execute button calls tmfService.execute via useMutation
    - Results: JSON view with raw toggle
    - Metadata bar: status code, duration, URL
    - Loading indicator, disabled Execute during execution, error card on failure
    - Success/error toast notifications
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10, 8.11, 8.12, 11.4, 11.5_

  - [x] 9.4 Write property test for FDW query request construction
    - **Property 6: FDW query form state maps correctly to QueryRequest**
    - **Validates: Requirements 7.7**

  - [x] 9.5 Write property test for FDW query results rendering
    - **Property 7: FDW query results and metadata are fully rendered**
    - **Validates: Requirements 7.8, 7.10**

  - [x] 9.6 Write property test for TMF response metadata rendering
    - **Property 9: TMF API response metadata is fully rendered**
    - **Validates: Requirements 8.10**

- [x] 10. Final checkpoint - Full integration verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using fast-check
- Unit tests validate specific examples and edge cases
- All components use existing shadcn/ui primitives and Tailwind CSS with dark mode support
- No new npm dependencies required (fast-check, React Query, shadcn/ui, Lucide already installed)
