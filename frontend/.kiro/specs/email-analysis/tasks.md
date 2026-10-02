# Implementation Plan: Email Analysis for Deal Potential and Revenue Impact

## Overview

This implementation plan breaks down the email analysis feature into discrete coding tasks. The approach follows the existing codebase patterns, building incrementally from data models through services to UI components. Each task builds on previous work to ensure no orphaned code.

## Tasks

- [x] 1. Create email analysis type definitions
  - [x] 1.1 Create `src/types/email-analysis.ts` with all TypeScript interfaces
    - Define EmailMessage, EmailThread, EmailEngagementMetrics interfaces
    - Define EmailSentimentAnalysis, EmailDealPotential interfaces
    - Define EmailAnalysis, EmailAnalysisSummary, EmailRevenueImpact interfaces
    - Define EmailAnalysisData as the root data structure
    - Reuse existing types (SentimentMoment, TopPerformer, etc.) from qa-analysis.ts
    - _Requirements: 1.1, 1.2_
  
  - [x] 1.2 Write property test for email-specific fields presence
    - **Property 1: Email-Specific Fields Presence**
    - **Validates: Requirements 1.2**

- [x] 2. Create mock email data files
  - [x] 2.1 Create `/public/emails/` directory with mock email thread JSON files
    - Create 5-7 mock email thread files with realistic business scenarios
    - Include varying deal potential (high, medium, low probability)
    - Include varying sentiment (positive, neutral, negative)
    - _Requirements: 1.3, 1.5_
  
  - [x] 2.2 Create `/public/results/email-analysis.json` mock analysis file
    - Follow structure of existing analysis.json
    - Include analysis_summary, individual_email_analysis array
    - Include team_performance_summary, revenue_impact, alerts_and_flags
    - Populate with 10-15 email analysis records
    - _Requirements: 1.4_

- [x] 3. Checkpoint - Verify data models and mock data
  - Run property tests to ensure type definitions are correct
  - Verify mock data files load correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement EmailAnalyticsService
  - [x] 4.1 Create `src/services/emailAnalyticsService.ts` with singleton pattern
    - Implement getInstance() method following QAAnalyticsService pattern
    - Implement fetchAnalysisData() method with filter support
    - Implement getSummaryStats() method for KPI calculations
    - Implement getTopPerformers() method for agent rankings
    - Implement getRecentAlerts() method for alert filtering
    - Implement clearCache() method
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [x] 4.2 Write property test for singleton pattern
    - **Property 2: Singleton Pattern Consistency**
    - **Validates: Requirements 2.1**
  
  - [x] 4.3 Write property test for filtering correctness
    - **Property 3: Filtering Correctness**
    - **Validates: Requirements 2.3, 6.4, 9.5**
  
  - [x] 4.4 Write property test for summary statistics calculation
    - **Property 4: Summary Statistics Calculation**
    - **Validates: Requirements 2.4**
  
  - [x] 4.5 Write property test for engagement metrics calculation
    - **Property 5: Engagement Metrics Calculation**
    - **Validates: Requirements 2.5, 5.4**

- [x] 5. Extend Dashboard Data Provider for email data
  - [x] 5.1 Update `src/services/dashboardDataProvider.ts`
    - Add fetchEmailAnalysisData() method
    - Implement API-first with JSON fallback strategy
    - _Requirements: 2.2_
  
  - [x] 5.2 Update `src/services/providers/jsonDataProvider.ts`
    - Add fetchEmailAnalysisData() method to load from email-analysis.json
    - _Requirements: 2.2_
  
  - [x] 5.3 Update `src/services/providers/apiDataProvider.ts`
    - Add fetchEmailAnalysisData() stub method for future API integration
    - _Requirements: 2.2_

- [x] 6. Checkpoint - Verify service layer
  - Run all service tests
  - Verify data fetching works with mock data
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement deal potential and revenue calculation utilities
  - [x] 7.1 Add utility functions to emailAnalyticsService.ts
    - Implement calculateDealStatus() function matching call analysis logic
    - Implement calculatePipelineValue() for aggregation
    - Implement calculateRevenueProjection() for monthly projections
    - Implement calculateRiskScore() for risk assessment
    - _Requirements: 3.2, 3.5, 4.2_
  
  - [x] 7.2 Write property test for deal status classification
    - **Property 6: Deal Status Classification**
    - **Validates: Requirements 3.2**
  
  - [x] 7.3 Write property test for pipeline value aggregation
    - **Property 7: Pipeline Value Aggregation**
    - **Validates: Requirements 3.5**
  
  - [x] 7.4 Write property test for revenue projection calculation
    - **Property 8: Revenue Projection Calculation**
    - **Validates: Requirements 4.2**

- [x] 8. Implement sentiment and engagement utilities
  - [x] 8.1 Add sentiment and engagement calculation methods to emailAnalyticsService.ts
    - Implement sentiment progression tracking
    - Implement engagement score calculation
    - Implement low engagement flagging logic
    - _Requirements: 5.2, 5.4, 5.5_
  
  - [x] 8.2 Write property test for sentiment progression consistency
    - **Property 9: Sentiment Progression Consistency**
    - **Validates: Requirements 5.2**
  
  - [x] 8.3 Write property test for low engagement flagging
    - **Property 10: Low Engagement Flagging**
    - **Validates: Requirements 5.5**

- [ ] 9. Implement sorting and aggregation utilities
  - [x] 9.1 Add sorting and aggregation methods to emailAnalyticsService.ts
    - Implement sortEmailAnalyses() with multiple sort fields
    - Implement aggregateRiskFactors() for team-level view
    - Implement calculateAgentPerformance() for rankings
    - _Requirements: 6.5, 8.4, 9.1_
  
  - [x] 9.2 Write property test for sorting correctness
    - **Property 11: Sorting Correctness**
    - **Validates: Requirements 6.5**
  
  - [x] 9.3 Write property test for risk factor aggregation
    - **Property 12: Risk Factor Aggregation**
    - **Validates: Requirements 8.4**
  
  - [x] 9.4 Write property test for agent performance calculation
    - **Property 13: Agent Performance Calculation**
    - **Validates: Requirements 9.1**

- [ ] 10. Implement serialization utilities
  - [x] 10.1 Add serialization/deserialization helpers to emailAnalyticsService.ts
    - Implement serializeEmailAnalysisData() function
    - Implement deserializeEmailAnalysisData() with validation
    - Handle missing/malformed data with defaults
    - _Requirements: 10.1, 10.2, 10.4_
  
  - [x] 10.2 Write property test for serialization round-trip
    - **Property 14: Serialization Round-Trip**
    - **Validates: Requirements 10.1, 10.2, 10.3**
  
  - [x] 10.3 Write unit tests for malformed data handling
    - Test missing required fields
    - Test invalid date formats
    - Test negative numeric values
    - _Requirements: 10.4_

- [x] 11. Checkpoint - Verify all service utilities
  - Run all property tests (Properties 2-14)
  - Verify all utility functions work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Create EmailsTable component
  - [x] 12.1 Create `src/components/processed-emails/EmailsTable.tsx`
    - Follow CallsTable component pattern
    - Display columns: Subject, Company, Agent, Date, Deal Value, Probability, Status
    - Implement row selection with onClick handler
    - Support sorting by clicking column headers
    - _Requirements: 6.1, 6.5_
  
  - [x] 12.2 Create `src/components/processed-emails/FilterBar.tsx`
    - Implement agent filter dropdown
    - Implement date range filter
    - Implement deal status filter
    - Implement sentiment filter
    - _Requirements: 6.4_

- [ ] 13. Create EmailDetailModal component
  - [x] 13.1 Create `src/components/processed-emails/EmailDetailModal.tsx`
    - Follow CallDetailModal pattern
    - Implement modal dialog with tabs
    - _Requirements: 6.2, 6.3_
  
  - [x] 13.2 Create `src/components/processed-emails/EmailOverviewTab.tsx`
    - Display thread summary, participants, duration
    - Display deal potential card with value, probability, status
    - Display engagement metrics
    - _Requirements: 3.1, 3.3, 5.1_
  
  - [x] 13.3 Create `src/components/processed-emails/EmailContentTab.tsx`
    - Display email thread messages in chronological order
    - Show sender, timestamp, subject, body for each message
    - _Requirements: 6.3_
  
  - [x] 13.4 Create `src/components/processed-emails/EmailAnalysisTab.tsx`
    - Display sentiment analysis with progression chart
    - Display risk factors with Badge severity indicators
    - Display next steps recommendations
    - _Requirements: 5.1, 5.3, 8.1, 8.2, 8.3_
  
  - [x] 13.5 Create `src/components/processed-emails/index.ts`
    - Export all processed-emails components
    - _Requirements: 6.3_

- [ ] 14. Create EmailAnalysisDashboard component
  - [x] 14.1 Create `src/components/dashboards/EmailAnalysisDashboard.tsx`
    - Follow DealAnalysisDashboard pattern
    - Implement KPI cards: Total Emails, Pipeline Value, High Probability Deals, At Risk Deals
    - Implement deal distribution bar chart using Recharts
    - Implement sentiment trends line chart
    - Implement engagement patterns visualization
    - Integrate with RefreshContext for data refresh
    - Implement agent and date range filters
    - _Requirements: 7.1, 7.3, 7.4, 7.5_
  
  - [x] 14.2 Add top performers section
    - Display agent rankings based on email performance
    - Show email-specific strengths
    - _Requirements: 9.2, 9.4_
  
  - [x] 14.3 Add alerts and recommendations section
    - Display recent alerts from email analysis
    - Show prioritized recommendations
    - _Requirements: 4.5, 8.5_

- [ ] 15. Integrate with navigation
  - [x] 15.1 Update `src/components/Sidebar.tsx` to include Email Analysis
    - Add menu item for Email Analysis dashboard
    - Add Mail icon from lucide-react
    - _Requirements: 7.2_
  
  - [x] 15.2 Add route for Email Analysis dashboard
    - Update App.tsx or router configuration
    - Add '/email-analysis' route
    - _Requirements: 7.2_

- [x] 16. Checkpoint - Verify UI components
  - Test all components render correctly
  - Verify navigation works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 17. Add comparison view between email and call metrics
  - [x] 17.1 Create combined revenue metrics view
    - Display side-by-side comparison of email vs call pipeline values
    - Show combined total pipeline
    - _Requirements: 4.4_

- [ ] 18. Final integration and cleanup
  - [x] 18.1 Verify all components integrate correctly
    - Test navigation flow
    - Test data loading and display
    - Test filtering and sorting
    - Test modal interactions
    - _Requirements: 7.2, 10.5_
  
  - [x] 18.2 Write integration tests
    - Test EmailAnalysisDashboard renders with mock data
    - Test EmailsTable filtering and sorting
    - Test EmailDetailModal tab navigation
    - _Requirements: 7.5_

- [x] 19. Final checkpoint - Complete feature verification
  - Run full test suite
  - Verify all 14 correctness properties pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (14 total)
- Unit tests validate specific examples and edge cases
- The implementation uses TypeScript throughout, matching the existing codebase


## Notes

- Tasks 1-2 are complete: Type definitions and mock data are implemented
- Task 3 onwards: Service layer, UI components, and integration remain to be implemented
- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (14 total)
- Unit tests validate specific examples and edge cases
- The implementation uses TypeScript throughout, matching the existing codebase
