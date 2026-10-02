# DynamoDB Database Structure for AI Job Engine

## Overview

The AI Job Engine uses **AWS DynamoDB** with a **Single Table Design** pattern to store all journey-related data in one table called `TransformationSystem`. This design provides exceptional performance, scalability, and cost-effectiveness by grouping related data together and using composite keys for efficient queries.

---

## Why Single Table Design?

**Business Benefits:**
- ✅ **Faster Queries** - All related data retrieved in one query (journey + stages + rules + jobs)
- ✅ **Lower Costs** - Fewer queries = lower AWS costs
- ✅ **Better Performance** - Related data stored together on same partition
- ✅ **Scalability** - Unlimited scale with predictable performance
- ✅ **Flexibility** - Easy to add new entity types without schema changes

**Traditional vs Single Table:**
```
Traditional (Multiple Tables):
- Journeys Table
- Stages Table  
- Rules Table
- Jobs Table
- Logs Table
→ 5 queries to get complete journey data ❌

Single Table Design:
- TransformationSystem Table
→ 1-2 queries to get complete journey data ✅
```

---

## Table Structure

### Primary Keys

#### Partition Key (PK)
Groups all data for a specific journey together.

**Pattern:** `JOURNEY#{journeyId}`

**Example:** `JOURNEY#JRN-ABC123456789`

**Why:** All data for journey JRN-ABC123456789 is stored on the same partition, enabling fast retrieval of complete journey information in a single query.

#### Sort Key (SK)
Uniquely identifies the type and instance of data within a journey.

**Patterns:**
- `METADATA` - Journey metadata (one per journey)
- `STAGE#{order:02d}#{stageId}` - Stage definitions (ordered)
- `RULE#{stageId}#{index:03d}#{ruleId}` - Second Brain AI rules
- `JOB#{order:02d}#{stageId}#{execution:03d}#{timestamp}` - Job executions
- `LOG#{jobId}#{stepName}#{timestamp}#{logId}` - Log entries
- `REPORT#{jobId}#{reportType}#{timestamp}#{reportId}` - Reports

**Examples:**
```
METADATA
STAGE#01#raw_analysis
STAGE#02#stripped_schema
RULE#raw_analysis#001#rule-raw_analysis-field_mapping-a1b2c3d4
JOB#01#raw_analysis#001#2025-11-01T20:30:00Z
LOG#JOB-456#schema_extraction#2025-11-01T20:31:15.234Z#LOG-789
REPORT#JOB-456#performance#2025-11-01T20:35:00Z#RPT-ABC
```

### Global Secondary Index (GSI1)

Enables queries across multiple journeys or specific subsets of data.

#### GSI1 Partition Key (GSI1PK)
Groups related entities for cross-journey queries.

**Patterns:**
- `JOURNEYS` - All journey metadata (for listing all journeys)
- `JOURNEY#{journeyId}#STAGES` - All stages for a journey
- `JOURNEY#{journeyId}#RULES` - All rules for a journey
- `JOB#{jobId}` - All logs for a specific job
- `REPORTS#{jobId}` - All reports for a specific job

#### GSI1 Sort Key (GSI1SK)
Orders the data within the GSI1PK group.

**Patterns:**
- ISO 8601 timestamps for time-based ordering
- `{order:02d}` for sequential ordering
- `{stageId}#{priority}#{index}` for complex sorting

---

## Entity Types

### 1. Journey Metadata

**Purpose:** Core information about a transformation journey

**Access Pattern:** Get specific journey by ID

**Keys:**
- **PK:** `JOURNEY#{journeyId}`
- **SK:** `METADATA`
- **GSI1PK:** `JOURNEYS`
- **GSI1SK:** `{creationTimestamp}`

**Data Structure:**
```json
{
  "PK": "JOURNEY#JRN-ABC123456789",
  "SK": "METADATA",
  "EntityType": "Journey",
  "GSI1PK": "JOURNEYS",
  "GSI1SK": "2025-11-01T20:00:00.000000Z",
  "CreatedAt": "2025-11-01T20:00:00.000000Z",
  "UpdatedAt": "2025-11-01T20:30:00.000000Z",
  "Data": {
    "journeyId": "JRN-ABC123456789",
    "name": "Product Catalog Migration to TMF620",
    "description": "Transform legacy product catalog to TMF620 API standard",
    "status": "running",
    "priority": "high",
    "createdBy": "data_team",
    "odaComponentType": "PRODUCTCATALOG",
    "source": {
      "type": "schema-based",
      "schemaId": "schema-PRODUCTCATALOG-001",
      "schemaName": "Legacy Product Database",
      "schemaVersion": "1.0.0"
    },
    "configuration": {
      "timeout": 1800,
      "maxDepth": 5,
      "tmfSpecVersion": "4.0.0",
      "outputFormat": "json",
      "retryAttempts": 3,
      "enableDetailedLogging": true,
      "validateAtEachStage": true,
      "secondBrainEnabled": true,
      "ruleEngineVersion": "v1.0"
    },
    "currentStageIndex": 2,
    "currentStageId": "tmf_mapping",
    "overallProgress": 45,
    "currentJobs": {
      "raw_analysis": "JOB-456",
      "stripped_schema": "JOB-457"
    },
    "aggregates": {
      "totalJobs": 12,
      "completedJobs": 8,
      "failedJobs": 1,
      "totalExecutionTime": "125m",
      "totalLogs": 1450,
      "totalErrors": 5,
      "totalWarnings": 28,
      "totalRules": 15,
      "activeRules": 12
    }
  }
}
```

**Business Logic:**
- `status` tracks overall journey state (pending, running, completed, failed, paused, cancelled)
- `priority` determines processing order (low, medium, high, critical)
- `currentStageId` shows which transformation stage is currently active
- `overallProgress` percentage (0-100) calculated from completed stages
- `aggregates` provides summary statistics for monitoring and reporting

---

### 2. Stage Definitions

**Purpose:** Define transformation stages in the journey workflow

**Access Pattern:** List all stages for a journey in order

**Keys:**
- **PK:** `JOURNEY#{journeyId}`
- **SK:** `STAGE#{order:02d}#{stageId}`
- **GSI1PK:** `JOURNEY#{journeyId}#STAGES`
- **GSI1SK:** `{order:02d}`

**Data Structure:**
```json
{
  "PK": "JOURNEY#JRN-ABC123456789",
  "SK": "STAGE#01#raw_analysis",
  "EntityType": "StageDefinition",
  "GSI1PK": "JOURNEY#JRN-ABC123456789#STAGES",
  "GSI1SK": "01",
  "CreatedAt": "2025-11-01T20:00:00.000000Z",
  "UpdatedAt": "2025-11-01T20:00:00.000000Z",
  "Data": {
    "stageId": "raw_analysis",
    "name": "Raw Analysis",
    "description": "Analyze source schema and extract metadata",
    "order": 1,
    "canSkip": false,
    "estimatedDuration": "30m",
    "status": "completed",
    "secondBrainEnabled": true,
    "ruleTypes": ["field_mapping", "data_interpretation"],
    "steps": [
      {
        "stepId": "schema_extraction",
        "name": "Schema Extraction",
        "description": "Extract schema from source database",
        "aiAssisted": true,
        "estimatedDuration": "10m"
      },
      {
        "stepId": "metadata_analysis",
        "name": "Metadata Analysis",
        "description": "Analyze table relationships and constraints",
        "aiAssisted": true,
        "estimatedDuration": "15m"
      },
      {
        "stepId": "data_profiling",
        "name": "Data Profiling",
        "description": "Profile data patterns and quality",
        "aiAssisted": false,
        "estimatedDuration": "5m"
      }
    ]
  }
}
```

**Default Stages (in order):**
1. **raw_analysis** - Analyze source schema and data patterns
2. **stripped_schema** - Extract and clean schema structure
3. **tmf_mapping** - Map to TMF API specifications
4. **migration_planning** - Plan data migration strategy
5. **data_migration** - Execute data transformation
6. **verification_validation** - Validate transformed data

**Business Logic:**
- `order` determines execution sequence (stages run in order 1, 2, 3, etc.)
- `canSkip` allows optional stages to be bypassed
- `secondBrainEnabled` activates AI-powered assistance for this stage
- `steps` define individual tasks within each stage
- `aiAssisted` flags indicate which steps use AI recommendations

---

### 3. Second Brain Rules

**Purpose:** AI-powered transformation rules that guide data mapping and validation

**Access Pattern:** Get all rules for a journey or specific stage

**Keys:**
- **PK:** `JOURNEY#{journeyId}`
- **SK:** `RULE#{stageId}#{index:03d}#{ruleId}`
- **GSI1PK:** `JOURNEY#{journeyId}#RULES`
- **GSI1SK:** `{stageId}#{priority}#{index:03d}`

**Data Structure:**
```json
{
  "PK": "JOURNEY#JRN-ABC123456789",
  "SK": "RULE#raw_analysis#001#rule-raw_analysis-field_mapping-a1b2c3d4",
  "EntityType": "SecondBrainRule",
  "GSI1PK": "JOURNEY#JRN-ABC123456789#RULES",
  "GSI1SK": "raw_analysis#high#001",
  "CreatedAt": "2025-11-01T20:00:00.000000Z",
  "UpdatedAt": "2025-11-01T20:00:00.000000Z",
  "Data": {
    "ruleId": "rule-raw_analysis-field_mapping-a1b2c3d4",
    "journeyId": "JRN-ABC123456789",
    "stageId": "raw_analysis",
    "title": "Map Product SKU to TMF Product Code",
    "description": "Transform legacy SKU format to TMF620 product code",
    "type": "field_mapping",
    "priority": "high",
    "scope": "stage",
    "status": "active",
    "context": "Product catalog field mapping during raw analysis",
    "content": "Map 'sku' field to TMF 'productCode' with format validation",
    "metadata": {
      "createdBy": "data_team",
      "version": "1.0",
      "tags": ["raw_analysis", "field_mapping", "high"],
      "applicableStages": ["raw_analysis", "tmf_mapping"],
      "ruleEngine": "second_brain_v1"
    }
  }
}
```

**Rule Types:**
- `field_mapping` - Map source fields to TMF API fields
- `contextual_recommendations` - Suggest transformation strategies
- `data_interpretation` - Guide data type and format transformations
- `validation_rules` - Define validation criteria
- `business_logic` - Business rules for transformation
- `compliance_check` - Regulatory compliance validations

**Business Logic:**
- Rules are organized by stage and priority
- `status` allows enabling/disabling rules (active, inactive, deprecated)
- `scope` determines where rule applies (global, project, stage)
- Multiple rules can apply to same stage, executed by priority order
- AI engine uses rules to make intelligent transformation decisions

---

### 4. Job Executions

**Purpose:** Track execution of transformation jobs for each stage

**Access Pattern:** List jobs for journey, filter by stage

**Keys:**
- **PK:** `JOURNEY#{journeyId}`
- **SK:** `JOB#{order:02d}#{stageId}#{execution:03d}#{timestamp}`
- **GSI1PK:** `JOB#{jobId}` (for log/report queries)
- **GSI1SK:** `{timestamp}`

**Data Structure:**
```json
{
  "PK": "JOURNEY#JRN-ABC123456789",
  "SK": "JOB#01#raw_analysis#001#2025-11-01T20:30:00.000000Z",
  "EntityType": "JobExecution",
  "GSI1PK": "JOB#JOB-456",
  "GSI1SK": "2025-11-01T20:30:00.000000Z",
  "CreatedAt": "2025-11-01T20:30:00.000000Z",
  "UpdatedAt": "2025-11-01T20:32:05.500000Z",
  "Data": {
    "jobId": "JOB-456",
    "journeyId": "JRN-ABC123456789",
    "stageId": "raw_analysis",
    "status": "completed",
    "progress": 100,
    "currentStep": "data_profiling",
    "startTime": "2025-11-01T20:30:00.000000Z",
    "endTime": "2025-11-01T20:32:05.500000Z",
    "duration": 125.5,
    "triggeredBy": "user",
    "executionNumber": 1,
    "configuration": {
      "timeout": 1800,
      "retryAttempts": 3,
      "enableDetailedLogging": true
    },
    "results": {
      "recordsProcessed": 10000,
      "recordsSucceeded": 9998,
      "recordsFailed": 2,
      "tablesAnalyzed": 45,
      "fieldsExtracted": 450
    },
    "metrics": {
      "totalLogs": 145,
      "errorCount": 2,
      "warningCount": 8,
      "infoCount": 120,
      "debugCount": 15
    },
    "errorMessage": null,
    "steps": [
      {
        "stepId": "schema_extraction",
        "status": "completed",
        "startTime": "2025-11-01T20:30:00.000000Z",
        "endTime": "2025-11-01T20:30:45.000000Z",
        "duration": 45.0
      },
      {
        "stepId": "metadata_analysis",
        "status": "completed",
        "startTime": "2025-11-01T20:30:45.000000Z",
        "endTime": "2025-11-01T20:31:50.500000Z",
        "duration": 65.5
      },
      {
        "stepId": "data_profiling",
        "status": "completed",
        "startTime": "2025-11-01T20:31:50.500000Z",
        "endTime": "2025-11-01T20:32:05.500000Z",
        "duration": 15.0
      }
    ]
  }
}
```

**Job Status Values:**
- `pending` - Job queued for execution
- `running` - Job currently executing
- `completed` - Job finished successfully
- `failed` - Job encountered errors
- `cancelled` - Job cancelled by user or system

**Business Logic:**
- Each job execution gets unique `jobId` (e.g., JOB-456)
- `executionNumber` tracks retry attempts (1st attempt, 2nd attempt, etc.)
- `progress` percentage (0-100) updated during execution
- `results` contain outcome statistics
- `metrics` aggregate log counts for monitoring
- Failed jobs can be retried, creating new execution with higher number

---

### 5. Log Entries (Hybrid S3 + DynamoDB Storage)

**Purpose:** Detailed execution logs for troubleshooting and monitoring

**Storage Strategy: HYBRID PATTERN**

The system uses a **dual storage approach** for optimal performance and cost:

1. **Primary Storage (S3)** - Actual log files
   - **Location:** `s3://transformation-journey-logs/journeys/{journey_id}/stages/{stage_id}/executions/{job_id}/logs/{step_id}.json`
   - **Purpose:** Store complete, detailed logs for each step
   - **Benefits:** Unlimited storage, cost-effective ($0.023/GB), never deleted
   - **Access:** Retrieved via `get_job_logs()` function

2. **Metadata Storage (DynamoDB)** - Optional lightweight entries
   - **Purpose:** Quick queries, log summaries, recent activity
   - **Benefits:** Fast indexed queries, real-time monitoring
   - **Access:** Queried via GSI1 for job-level log aggregation

**S3 Log File Structure:**
```json
[
  {
    "jobId": "JOB-456",
    "step_id": "schema_extraction",
    "level": "INFO",
    "message": "Successfully extracted 45 tables from source database",
    "timestamp": "2025-11-01T20:30:15.234567Z",
    "details": {
      "database": "legacy_catalog",
      "tables_extracted": 45,
      "total_fields": 450,
      "duration_seconds": 12.5
    }
  },
  {
    "jobId": "JOB-456",
    "step_id": "schema_extraction",
    "level": "INFO",
    "message": "Analyzing table relationships",
    "timestamp": "2025-11-01T20:30:20.567890Z",
    "details": {
      "foreign_keys_found": 23,
      "indexes_found": 67
    }
  }
]
```

**DynamoDB Metadata (Optional):**

**Access Pattern:** Quick queries for recent logs or log summaries

**Keys:**
- **PK:** `JOURNEY#{journeyId}`
- **SK:** `LOG#{jobId}#{stepName}#{timestamp}#{logId}`
- **GSI1PK:** `JOB#{jobId}`
- **GSI1SK:** `{timestamp}`

**Data Structure:**
```json
{
  "PK": "JOURNEY#JRN-ABC123456789",
  "SK": "LOG#JOB-456#schema_extraction#2025-11-01T20:30:15.234567Z#LOG-789",
  "EntityType": "LogEntry",
  "GSI1PK": "JOB#JOB-456",
  "GSI1SK": "2025-11-01T20:30:15.234567Z",
  "CreatedAt": "2025-11-01T20:30:15.234567Z",
  "Data": {
    "jobId": "JOB-456",
    "step": "schema_extraction",
    "level": "info",
    "message": "Successfully extracted 45 tables from source database",
    "timestamp": "2025-11-01T20:30:15.234567Z",
    "source": "schema_analyzer",
    "s3Location": "s3://transformation-journey-logs/journeys/JRN-ABC123456789/stages/raw_analysis/executions/JOB-456/logs/schema_extraction.json",
    "details": {
      "tables_extracted": 45,
      "total_fields": 450
    }
  }
}
```

**How It Works:**

1. **During Job Execution:**
   ```python
   # base_stage.py logs messages to memory
   self.log_info("Processing table: products")
   self.log_warning("Missing index on product_id")
   ```

2. **After Step Completion:**
   ```python
   # Logs uploaded to S3
   self.upload_logs_to_s3(step_id)
   # → s3://transformation-journey-logs/.../schema_extraction.json
   ```

3. **When Retrieving Logs:**
   ```python
   # Read from S3 (primary source)
   logs = get_job_logs(journey_id, stage_name, job_id, step_name)
   # → Returns all logs from S3 file
   ```

**Log Levels:**
- `DEBUG` - Detailed diagnostic information
- `INFO` - General informational messages
- `WARNING` - Potential issues that don't stop execution
- `ERROR` - Errors that need attention

**Business Logic:**
- **Full logs stored in S3** - Complete execution history, never lost
- **DynamoDB stores summaries** - For quick dashboard queries
- **Logs organized by step** - One file per step per job
- **Logs include structured details** - Searchable metadata
- **S3 lifecycle policies** - Optional archival to Glacier after 90 days
- **Cost optimization** - S3 cheaper than DynamoDB for large log volumes

**Cost Comparison:**

**Storing 1GB of logs:**
- **S3 Standard:** $0.023/month ✅
- **DynamoDB:** $25/month (400KB limit per item) ❌

**Why Hybrid Approach:**
- S3 handles unlimited log volumes cost-effectively
- DynamoDB provides fast indexed queries for recent activity
- Best of both worlds: cost + performance

---

### 6. Reports (Hybrid S3 + DynamoDB Storage)

**Purpose:** Generated analysis reports for jobs (performance, errors, summary)

**Storage Strategy: HYBRID PATTERN**

Similar to logs, reports use a **dual storage approach**:

1. **Primary Storage (S3)** - Full report files
   - **Location:** `s3://transformation-journey-reports/journeys/{journey_id}/stages/{stage_id}/executions/{job_id}/reports/{step_id}.json`
   - **Purpose:** Store complete detailed reports for each step
   - **Benefits:** Unlimited storage, supports large reports, cost-effective
   - **Access:** Retrieved via `get_job_reports()` function

2. **Metadata Storage (DynamoDB)** - Report catalog and summaries
   - **Purpose:** List available reports, quick access to summaries
   - **Benefits:** Fast indexed queries, report discovery
   - **Access:** Queried via GSI1 for job-level report listing

**S3 Report File Structure:**
```json
{
  "reportId": "JOB-456_schema_extraction",
  "reportType": "performance",
  "title": "Schema Extraction Performance Report",
  "summary": "Extracted 45 tables in 45.2 seconds",
  "executionSummary": {
    "stepId": "schema_extraction",
    "jobId": "JOB-456",
    "status": "completed",
    "startTime": "2025-11-01T20:30:00.000000Z",
    "endTime": "2025-11-01T20:30:45.200000Z",
    "duration": 45.2,
    "itemsProcessed": 45
  },
  "performanceMetrics": {
    "throughput": 0.99,
    "tablesPerSecond": 0.99,
    "averageTableProcessingTime": 1.0,
    "errorRate": 0.0,
    "memoryUsage": "256MB",
    "cpuUtilization": "35%"
  },
  "detailedResults": {
    "tablesExtracted": 45,
    "fieldsExtracted": 450,
    "relationshipsIdentified": 23,
    "indexesFound": 67
  },
  "recommendations": [
    "Schema extraction performed well",
    "Consider parallel processing for larger databases",
    "Memory usage is optimal"
  ],
  "generatedAt": "2025-11-01T20:30:45.500000Z"
}
```

**DynamoDB Metadata:**

**Access Pattern:** List all reports for a job, get report summaries

**Keys:**
- **PK:** `JOURNEY#{journeyId}`
- **SK:** `REPORT#{jobId}#{reportType}#{timestamp}#{reportId}`
- **GSI1PK:** `REPORTS#{jobId}`
- **GSI1SK:** `{timestamp}`

**Data Structure:**
```json
{
  "PK": "JOURNEY#JRN-ABC123456789",
  "SK": "REPORT#JOB-456#performance#2025-11-01T20:35:00.000000Z#RPT-ABC",
  "EntityType": "JobReport",
  "GSI1PK": "REPORTS#JOB-456",
  "GSI1SK": "2025-11-01T20:35:00.000000Z",
  "CreatedAt": "2025-11-01T20:35:00.000000Z",
  "Data": {
    "reportId": "RPT-ABC",
    "jobId": "JOB-456",
    "reportType": "performance",
    "title": "Performance Analysis Report - Raw Analysis Job",
    "summary": "Job completed in 125.5 seconds with 2 errors",
    "s3Location": "s3://transformation-journey-reports/journeys/JRN-ABC123456789/stages/raw_analysis/executions/JOB-456/reports/schema_extraction.json",
    "generatedAt": "2025-11-01T20:35:00.000000Z",
    "status": "generated",
    "metrics": {
      "contentSize": 2048,
      "generationTime": 0.5,
      "reportSections": 5
    }
  }
}
```

**How It Works:**

1. **After Step Completion:**
   ```python
   # base_stage.py generates report data
   report_data = {
     "executionSummary": {...},
     "performanceMetrics": {...},
     "recommendations": [...]
   }
   ```

2. **Upload to S3:**
   ```python
   # Report uploaded to S3
   self.upload_report_to_s3(step_id, report_data)
   # → s3://transformation-journey-reports/.../schema_extraction.json
   ```

3. **Optionally Save Metadata to DynamoDB:**
   ```python
   # Create catalog entry in DynamoDB
   create_job_report(journey_id, job_id, report_type, title, content, summary)
   ```

4. **When Retrieving Reports:**
   ```python
   # Read from S3 (primary source)
   reports = get_job_reports(journey_id, job_id, stage_name)
   # → Returns all reports from S3 bucket
   ```

**Report Types:**
- `summary` - Overview of job execution
- `performance` - Performance analysis with recommendations
- `error_analysis` - Detailed error analysis
- `custom` - Custom reports
- `timeline` - Step-by-step execution timeline
- `metrics` - Detailed metrics dashboard

**Business Logic:**
- **Full reports stored in S3** - Complete analysis, charts, detailed data
- **DynamoDB stores catalog** - Quick listing of available reports
- **Reports generated per step** - One report file per step
- **Reports include recommendations** - AI-powered improvement suggestions
- **S3 enables large reports** - No size limitations (vs 400KB DynamoDB limit)
- **Cost optimization** - S3 storage 100x cheaper than DynamoDB

**S3 Bucket Organization:**
```
s3://transformation-journey-reports/
└── journeys/
    └── JRN-ABC123456789/
        └── stages/
            └── raw_analysis/
                └── executions/
                    └── JOB-456/
                        └── reports/
                            ├── schema_extraction.json
                            ├── metadata_analysis.json
                            └── data_profiling.json
```

**Why Hybrid Approach:**
- **S3:** Handles large reports (10MB+) cost-effectively
- **DynamoDB:** Fast report discovery and listing
- **Best practices:** Separate storage concerns from query concerns

---

## Hybrid Storage Architecture Summary

The AI Job Engine uses a **smart hybrid storage pattern** that combines the best of AWS S3 and DynamoDB:

### Storage Decision Matrix

| Data Type | Primary Storage | Secondary Storage | Reason |
|-----------|----------------|-------------------|---------|
| **Journey Metadata** | DynamoDB | - | Fast queries, frequent updates, small size |
| **Stage Definitions** | DynamoDB | - | Indexed access, relationship queries |
| **Second Brain Rules** | DynamoDB | - | Fast filtering, priority ordering |
| **Job Executions** | DynamoDB | - | Real-time status updates, progress tracking |
| **Log Files** | **S3** | DynamoDB (metadata) | Large volume, unlimited size, cost-effective |
| **Report Files** | **S3** | DynamoDB (catalog) | Large files, detailed analysis, archival |

### Why This Architecture?

**Problem:** A single transformation job can generate:
- 10,000+ log entries (50MB uncompressed)
- Multiple detailed reports (5-10MB each)
- Storing this in DynamoDB would be expensive and hit size limits

**Solution: Hybrid Pattern**

```
┌─────────────────────────────────────────────────────────────┐
│                    Job Execution Flow                        │
└─────────────────────────────────────────────────────────────┘

1. Job Starts
   ├─> DynamoDB: Create job record with status "in_progress"
   └─> S3 Config: Store logs/reports bucket paths

2. During Execution (Each Step)
   ├─> Memory: Collect logs in-memory
   ├─> Memory: Generate report data
   └─> DynamoDB: Update job progress (lightweight)

3. After Step Completion
   ├─> S3: Upload step logs (schema_extraction.json)
   ├─> S3: Upload step report (schema_extraction.json)
   └─> DynamoDB: Optional metadata entry (for quick queries)

4. Job Completion
   ├─> DynamoDB: Update job status to "completed"
   └─> DynamoDB: Store aggregated metrics (total logs, errors, etc.)

5. User Retrieves Logs/Reports
   ├─> Option A: get_job_logs() → Read from S3 (full details)
   ├─> Option B: Query DynamoDB GSI1 (quick summaries)
   └─> Best of both: Fast discovery + complete details
```

### Cost Analysis

**Example: 100 Jobs per Day**

Each job generates:
- 50MB of logs
- 10MB of reports
- Total: 60MB per job × 100 jobs = 6GB/day

**S3 Approach (Current):**
- Storage: 6GB × 30 days = 180GB/month
- Cost: 180GB × $0.023/GB = **$4.14/month** ✅
- Retrieval: $0.005/1000 requests = negligible

**DynamoDB Only (Alternative):**
- Can't store 60MB per job (400KB limit per item) ❌
- Would need 150 items per job × 100 jobs = 15,000 items
- Storage: 15,000 items × $0.25/GB = **$375/month** ❌
- Plus read/write costs

**Savings: 99% cost reduction with S3 hybrid approach!**

### Performance Comparison

| Operation | DynamoDB Only | S3 Only | Hybrid (Current) | Winner |
|-----------|--------------|---------|------------------|--------|
| **List all journeys** | 20ms | N/A | 20ms | Hybrid ✅ |
| **Get job status** | 5ms | N/A | 5ms | Hybrid ✅ |
| **Get full logs** | N/A | 50ms | 50ms | Hybrid ✅ |
| **Search recent logs** | 500ms (scan) | 200ms | 15ms (GSI) | Hybrid ✅ |
| **Large report (10MB)** | ❌ (size limit) | 100ms | 100ms | Hybrid ✅ |
| **Cost (monthly)** | $375 | $4.14 | $10 | Hybrid ✅ |

### S3 Bucket Structure

```
s3://transformation-journey-logs/
└── journeys/
    └── {journey_id}/
        └── stages/
            └── {stage_id}/
                └── executions/
                    └── {job_id}/
                        └── logs/
                            ├── schema_extraction.json
                            ├── metadata_analysis.json
                            ├── data_profiling.json
                            └── ...

s3://transformation-journey-reports/
└── journeys/
    └── {journey_id}/
        └── stages/
            └── {stage_id}/
                └── executions/
                    └── {job_id}/
                        └── reports/
                            ├── schema_extraction.json (5MB)
                            ├── metadata_analysis.json (8MB)
                            └── performance_summary.json (2MB)
```

### Data Flow Diagram

```
┌─────────────┐
│  Job Start  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  DynamoDB: TransformationSystem         │
│  ─────────────────────────────────────  │
│  PK: JOURNEY#JRN-ABC                    │
│  SK: JOB#01#raw_analysis#001#timestamp  │
│  Data: {                                │
│    jobId: "JOB-456",                    │
│    status: "in_progress",               │
│    s3Config: {                          │
│      logsBucket: "...-logs",            │
│      reportsBucket: "...-reports"       │
│    }                                    │
│  }                                      │
└─────────────────────────────────────────┘
       │
       ├── Step 1: schema_extraction
       │   ├─> Logs collected in memory
       │   ├─> Report generated in memory
       │   ▼
       │   ┌────────────────────────────┐
       │   │  S3: transformation-       │
       │   │      journey-logs          │
       │   │  ─────────────────────────│
       │   │  Key: .../logs/           │
       │   │       schema_extraction    │
       │   │       .json                │
       │   │  Content: [                │
       │   │    {log entry 1},          │
       │   │    {log entry 2},          │
       │   │    ... (10,000 entries)    │
       │   │  ]                         │
       │   └────────────────────────────┘
       │   ┌────────────────────────────┐
       │   │  S3: transformation-       │
       │   │      journey-reports       │
       │   │  ─────────────────────────│
       │   │  Key: .../reports/         │
       │   │       schema_extraction    │
       │   │       .json                │
       │   │  Content: {                │
       │   │    performanceMetrics,     │
       │   │    detailedResults,        │
       │   │    recommendations         │
       │   │  }                         │
       │   └────────────────────────────┘
       │
       ├── Step 2: metadata_analysis
       │   └─> Same pattern...
       │
       └── Step 3: data_profiling
           └─> Same pattern...
```

### Retrieval Workflow

**Scenario 1: Dashboard - Show All Jobs**
```python
# Fast! Uses DynamoDB GSI1
jobs = table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={':pk': f'STAGE#{journey_id}#{stage_id}'}
)
# Returns: List of jobs with status, progress, timestamps
# Response time: 15-20ms
```

**Scenario 2: Troubleshoot Failed Job - View Logs**
```python
# Read from S3 for complete details
logs = get_job_logs(journey_id, stage_name, job_id)
# → s3_client.get_object('transformation-journey-logs', key)
# Returns: Complete log history with all details
# Response time: 50-100ms
```

**Scenario 3: Generate Job Report**
```python
# Read from S3 for detailed analysis
reports = get_job_reports(journey_id, job_id, stage_name)
# → s3_client.list_objects_v2 + get_object for each report
# Returns: All step reports with performance data
# Response time: 100-200ms
```

### Key Benefits

1. **Cost Optimization (99% savings)**
   - S3 stores large files at $0.023/GB
   - DynamoDB only for fast-access metadata
   - No data size limitations

2. **Performance Optimization**
   - DynamoDB for real-time queries (journeys, jobs, status)
   - S3 for bulk data retrieval (logs, reports)
   - GSI for cross-journey analytics

3. **Scalability**
   - Unlimited log storage in S3
   - DynamoDB auto-scales for metadata queries
   - No architectural changes needed as data grows

4. **Operational Benefits**
   - Complete audit trail in S3 (never deleted)
   - Fast dashboards from DynamoDB
   - Separate concerns: storage vs query

5. **Developer Experience**
   - Simple APIs hide complexity
   - `get_job_logs()` abstracts S3 access
   - `list_jobs()` abstracts DynamoDB queries

### Best Practices

✅ **DO:**
- Store large, detailed data in S3 (logs, reports)
- Store metadata and indexes in DynamoDB (journey, job status)
- Use DynamoDB for real-time updates (job progress)
- Use S3 for historical analysis (log archives)

❌ **DON'T:**
- Store large logs in DynamoDB (hits size limits)
- Query S3 for real-time dashboards (too slow)
- Mix storage concerns (keep them separate)

---

## Data Retrieval Patterns

### Pattern 1: Get Complete Journey Information

**Business Need:** View all details about a journey including stages, rules, and jobs

**Query Strategy:**
1. Get journey metadata: Query `PK = JOURNEY#{id}` AND `SK = METADATA`
2. Get all stages: Query `PK = JOURNEY#{id}` AND `SK begins_with STAGE#`
3. Get all rules: Query `PK = JOURNEY#{id}` AND `SK begins_with RULE#`
4. Get recent jobs: Query `PK = JOURNEY#{id}` AND `SK begins_with JOB#`

**Why This Works:**
- All data for one journey is on same partition (fast!)
- Single partition query retrieves related data efficiently
- No cross-partition queries needed

**Code Example:**
```python
# Get journey metadata
journey = table.get_item(
    Key={
        'PK': 'JOURNEY#JRN-ABC123456789',
        'SK': 'METADATA'
    }
)

# Get all stages (sorted by order)
stages = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={
        ':pk': 'JOURNEY#JRN-ABC123456789',
        ':sk': 'STAGE#'
    }
)

# Get all rules
rules = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={
        ':pk': 'JOURNEY#JRN-ABC123456789',
        ':sk': 'RULE#'
    }
)
```

---

### Pattern 2: List All Journeys

**Business Need:** Show dashboard of all active journeys

**Query Strategy:**
- Use GSI1: Query `GSI1PK = JOURNEYS`
- Returns all journey metadata sorted by creation time

**Why This Works:**
- GSI1 groups all journey metadata together
- No need to scan entire table
- Results naturally sorted by creation date

**Code Example:**
```python
journeys = table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={
        ':pk': 'JOURNEYS'
    }
)
```

---

### Pattern 3: Get All Logs for a Job

**Business Need:** Troubleshoot job by viewing all execution logs

**Query Strategy:**
- Use GSI1: Query `GSI1PK = JOB#{jobId}`
- Returns all logs sorted by timestamp

**Why This Works:**
- Logs indexed by jobId in GSI1
- Time-ordered for chronological viewing
- Fast retrieval regardless of journey size

**Code Example:**
```python
logs = table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={
        ':pk': 'JOB#JOB-456'
    }
)
```

---

### Pattern 4: Get Stage-Specific Rules

**Business Need:** Load AI rules for currently executing stage

**Query Strategy:**
- Query `PK = JOURNEY#{id}` AND `SK begins_with RULE#{stageId}#`
- Filter in application or use FilterExpression

**Why This Works:**
- Rules for specific stage are prefixed with stage ID
- Returns only relevant rules for current execution
- Rules naturally ordered by priority and index

**Code Example:**
```python
rules = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={
        ':pk': 'JOURNEY#JRN-ABC123456789',
        ':sk': 'RULE#raw_analysis#'
    }
)
```

---

### Pattern 5: Get Jobs for Specific Stage

**Business Need:** Monitor all executions of raw_analysis stage

**Query Strategy:**
- Query `PK = JOURNEY#{id}` AND `SK begins_with JOB#`
- Filter by stageId in application or using FilterExpression

**Code Example:**
```python
jobs = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    FilterExpression='#data.stageId = :stage_id',
    ExpressionAttributeNames={'#data': 'Data'},
    ExpressionAttributeValues={
        ':pk': 'JOURNEY#JRN-ABC123456789',
        ':sk': 'JOB#',
        ':stage_id': 'raw_analysis'
    }
)
```

---

### Pattern 6: Get Recent Job Logs

**Business Need:** View latest logs from currently running job

**Query Strategy:**
- Use GSI1: Query `GSI1PK = JOB#{jobId}`
- Set `ScanIndexForward = False` for newest first
- Set `Limit = 100` for most recent entries

**Code Example:**
```python
recent_logs = table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={
        ':pk': 'JOB#JOB-456'
    },
    ScanIndexForward=False,  # Newest first
    Limit=100
)
```

---

## Key Design Decisions

### 1. Why Use Sort Key Prefixes?

**Business Value:** Enables efficient querying of related entities

**Example:**
```
STAGE#01#raw_analysis
STAGE#02#stripped_schema
STAGE#03#tmf_mapping
```

**Benefits:**
- Query all stages with `begins_with(SK, 'STAGE#')`
- Natural ordering by `#01`, `#02`, `#03`
- Easy to add new stages without reorganizing data

---

### 2. Why Include Order in Sort Keys?

**Business Value:** Maintain execution sequence without additional queries

**Example:**
```
STAGE#01#raw_analysis     ← Executes first
STAGE#02#stripped_schema  ← Executes second
STAGE#03#tmf_mapping      ← Executes third
```

**Benefits:**
- Stages automatically returned in execution order
- No need for separate "order" field lookups
- DynamoDB sorts alphanumerically, so 01, 02, 03 works perfectly

---

### 3. Why Use Composite Job Keys?

**Business Value:** Track retries and execution history

**Example:**
```
JOB#01#raw_analysis#001#2025-11-01T20:30:00Z  ← First attempt
JOB#01#raw_analysis#002#2025-11-01T21:00:00Z  ← Retry (second attempt)
JOB#01#raw_analysis#003#2025-11-01T21:30:00Z  ← Retry (third attempt)
```

**Benefits:**
- Full execution history preserved
- Easy to find latest execution (highest number)
- Failed jobs don't overwrite previous attempts
- Audit trail for troubleshooting

---

### 4. Why Use GSI for Logs?

**Business Value:** Fast log retrieval across all steps of a job

**Without GSI:**
```
Query PK = JOURNEY#ABC, SK begins_with LOG#JOB-456
→ Returns logs mixed with stages, rules, etc.
→ Need to filter in application
```

**With GSI:**
```
Query GSI1PK = JOB#JOB-456
→ Returns ONLY logs for this job
→ Already sorted by timestamp
→ Fast and efficient
```

---

## Performance Considerations

### Partition Design

**Hot Partitions:** 
- Each journey gets its own partition (PK = JOURNEY#{id})
- Large journeys (1000s of jobs) stay on single partition
- DynamoDB automatically handles partition scaling

**Cold Partitions:**
- Completed journeys accessed infrequently
- DynamoDB automatically moves to cheaper storage
- No performance impact on active journeys

### Query Efficiency

**Single Partition Queries (Fastest):**
```python
# Get journey metadata: ~5ms
table.get_item(Key={'PK': 'JOURNEY#ABC', 'SK': 'METADATA'})

# Get all stages for journey: ~10ms
table.query(KeyCondition='PK = :pk AND begins_with(SK, STAGE#)')
```

**GSI Queries (Fast):**
```python
# List all journeys: ~20ms
table.query(IndexName='GSI1', KeyCondition='GSI1PK = JOURNEYS')

# Get job logs: ~15ms
table.query(IndexName='GSI1', KeyCondition='GSI1PK = JOB#456')
```

**Scan Operations (Slow - Avoid):**
```python
# Never do this!
table.scan()  # Reads entire table ❌
```

### Data Size Limits

**Item Size Limit:** 400 KB per item
- Journey metadata: ~5-10 KB ✅
- Stage definition: ~2-5 KB ✅
- Rule: ~1-3 KB ✅
- Job execution: ~10-20 KB ✅
- Log entry: ~0.5-1 KB ✅

**Best Practices:**
- Store large files (schemas, reports) in S3
- Reference S3 URIs in DynamoDB items
- Keep log messages concise

---

## Scaling and Costs

### Horizontal Scaling

**Journey Growth:**
- 10 journeys: 1 partition each = 10 partitions
- 1,000 journeys: 1 partition each = 1,000 partitions
- 1,000,000 journeys: 1 partition each = 1,000,000 partitions

**DynamoDB automatically scales partitions!**

### Cost Optimization

**Read Costs:**
- Get journey metadata: 1 RCU (read capacity unit)
- Get all stages (6 stages): 1 RCU
- Get all rules (15 rules): 1 RCU
- **Total to load journey: ~3 RCUs**

**Traditional Design (Multiple Tables):**
- Get journey: 1 RCU
- Get 6 stages: 6 RCUs (6 separate queries)
- Get 15 rules: 15 RCUs (15 separate queries)
- **Total: 22 RCUs** ❌

**Savings: 86% fewer read costs with single table design!** ✅

---

## Backup and Recovery

### Point-in-Time Recovery (PITR)

**Enabled:** Yes
**Retention:** 35 days
**Granularity:** 1 second

**Business Value:**
- Recover from accidental deletes
- Restore to any point in last 35 days
- No impact on performance

### On-Demand Backups

**Journey Export:**
```python
# Export complete journey to S3
journey_data = get_journey_complete(journey_id)
s3.put_object(
    Bucket='transformation-backups',
    Key=f'journeys/{journey_id}/backup.json',
    Body=json.dumps(journey_data)
)
```

**Import Journey:**
```python
# Restore journey from S3
backup_data = s3.get_object(
    Bucket='transformation-backups',
    Key=f'journeys/{journey_id}/backup.json'
)
import_journey_complete(backup_data)
```

---

## Security and Access Control

### Encryption

**At Rest:** AES-256 encryption (AWS KMS)
**In Transit:** TLS 1.2+

### IAM Policies

**Read-Only Access:**
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:Query"
  ],
  "Resource": "arn:aws:dynamodb:*:*:table/TransformationSystem"
}
```

**Full Access:**
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem",
    "dynamodb:Query"
  ],
  "Resource": "arn:aws:dynamodb:*:*:table/TransformationSystem"
}
```

---

## Monitoring and Observability

### CloudWatch Metrics

**Key Metrics:**
- `ConsumedReadCapacityUnits` - Read throughput
- `ConsumedWriteCapacityUnits` - Write throughput
- `UserErrors` - Application errors
- `SystemErrors` - DynamoDB errors
- `ThrottledRequests` - Rate limit hits

### Application Metrics

**Tracked in Journey Aggregates:**
```json
{
  "totalJobs": 12,
  "completedJobs": 8,
  "failedJobs": 1,
  "totalExecutionTime": "125m",
  "totalLogs": 1450,
  "totalErrors": 5,
  "totalWarnings": 28
}
```

---

## Best Practices

### 1. Always Use Partition Key in Queries

❌ **Bad:**
```python
# Scans entire table!
table.scan(FilterExpression='journeyId = :id')
```

✅ **Good:**
```python
# Uses partition key
table.query(KeyConditionExpression='PK = :pk',
            ExpressionAttributeValues={':pk': 'JOURNEY#ABC'})
```

### 2. Use GSI for Cross-Journey Queries

❌ **Bad:**
```python
# Multiple queries, slow
for journey_id in all_journey_ids:
    table.get_item(Key={'PK': f'JOURNEY#{journey_id}', 'SK': 'METADATA'})
```

✅ **Good:**
```python
# Single GSI query, fast
table.query(IndexName='GSI1',
            KeyConditionExpression='GSI1PK = :pk',
            ExpressionAttributeValues={':pk': 'JOURNEYS'})
```

### 3. Batch Related Writes

❌ **Bad:**
```python
# Multiple separate writes
table.put_item(Item=journey)
table.put_item(Item=stage1)
table.put_item(Item=stage2)
```

✅ **Good:**
```python
# Batch write (transactional)
with table.batch_writer() as batch:
    batch.put_item(Item=journey)
    batch.put_item(Item=stage1)
    batch.put_item(Item=stage2)
```

### 4. Paginate Large Result Sets

✅ **Good:**
```python
# For jobs with 1000s of logs
paginator = table.meta.client.get_paginator('query')
for page in paginator.paginate(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={':pk': 'JOB#JOB-456'}
):
    process_logs(page['Items'])
```

---

## Summary

The AI Job Engine uses DynamoDB's **Single Table Design** to provide:

✅ **Performance** - All journey data in one partition
✅ **Scalability** - Unlimited journeys, automatic partitioning
✅ **Cost Efficiency** - 86% fewer read operations
✅ **Flexibility** - Easy to add new entity types
✅ **Reliability** - Built-in backup and recovery
✅ **Security** - Encryption at rest and in transit

**Key Takeaways:**
1. One table (`TransformationSystem`) stores all data
2. Partition key (`PK`) groups by journey
3. Sort key (`SK`) identifies entity type and order
4. GSI enables cross-journey queries
5. Composite keys provide rich querying capabilities
6. Design optimized for common access patterns

This design supports the complete journey lifecycle from creation through execution, monitoring, and analysis—all with exceptional performance and minimal cost.

