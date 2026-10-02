# Job Execution Flow - AI Job Engine

## Overview

The AI Job Engine executes transformation jobs using a **stage-based pipeline architecture** where each job runs through multiple steps, with comprehensive logging, progress tracking, and error handling.

---

## High-Level Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     Job Execution Lifecycle                       │
└──────────────────────────────────────────────────────────────────┘

1. Job Initialization
   ├─> User/System triggers job
   ├─> TransformationJobExecutor.start_job_execution()
   ├─> Generate unique Job ID
   ├─> Create job record in DynamoDB
   └─> Update journey's current job

2. Job Execution
   ├─> TransformationJobExecutor.execute_job()
   ├─> Load stage class (e.g., RawAnalysisStage)
   ├─> Create stage instance
   └─> Execute each step sequentially

3. Step Execution (repeated for each step)
   ├─> Update step status to "in_progress"
   ├─> Stage.execute_step()
   │   ├─> Collect logs in memory
   │   ├─> Generate metrics
   │   ├─> Process data
   │   └─> Create artifacts
   ├─> Upload logs to S3
   ├─> Upload report to S3
   ├─> Update step results in DynamoDB
   └─> Update job progress

4. Job Completion
   ├─> Mark job as "completed" (or "failed")
   ├─> Update journey statistics
   ├─> Save final metrics
   └─> Return results

```

---

## Detailed Step-by-Step Flow

### Phase 1: Job Initialization

**Entry Point:** `TransformationJobExecutor.start_job_execution()`

```python
# Called via:
python scripts/journey-scripts/run_transformation_job.py \
    --journey-id JRN-ABC123 \
    --stage-id raw_analysis \
    --triggered-by user
```

**What Happens:**

1. **Load Journey**
   ```python
   journey = get_journey(journey_id)
   # → DynamoDB: PK=JOURNEY#JRN-ABC123, SK=METADATA
   ```

2. **Get Stage Definition**
   ```python
   stage_class = get_stage_class(stage_id)
   # → Python: src/stages/raw-analysis/raw_analysis.py → RawAnalysisStage
   ```

3. **Generate Job ID**
   ```python
   timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
   execution_number = get_next_execution_number(journey_id, stage_id)
   job_id = f'JOB-{execution_number:03d}-{timestamp}'
   # → Result: "JOB-001-20251101203000"
   ```

4. **Create Job Record in DynamoDB**
   ```python
   job_data = {
       'PK': 'JOURNEY#JRN-ABC123',
       'SK': 'JOB#01#raw_analysis#001#20251101203000',
       'EntityType': 'JobExecution',
       'Data': {
           'jobId': 'JOB-001-20251101203000',
           'journeyId': 'JRN-ABC123',
           'stageId': 'raw_analysis',
           'status': 'in_progress',
           'startTime': '2025-11-01T20:30:00Z',
           'progress': 0,
           's3Config': {
               'logsBucket': 'transformation-journey-logs',
               'logsPrefix': 'journeys/JRN-ABC123/stages/raw_analysis/executions/JOB-001-20251101203000/',
               'reportsBucket': 'transformation-journey-reports',
               'reportsPrefix': 'journeys/JRN-ABC123/stages/raw_analysis/executions/JOB-001-20251101203000/'
           },
           'stepResults': {
               'schema_parsing': {'status': 'pending', 'progress': 0},
               'relationship_discovery': {'status': 'pending', 'progress': 0},
               'data_type_analysis': {'status': 'pending', 'progress': 0},
               'business_rules_extraction': {'status': 'pending', 'progress': 0},
               'complexity_assessment': {'status': 'pending', 'progress': 0}
           }
       }
   }
   ```

5. **Update Journey Current Job**
   ```python
   # Update journey metadata to track active job
   update_journey_current_job(journey_id, stage_id, job_id, execution_number)
   ```

---

### Phase 2: Job Execution

**Entry Point:** `TransformationJobExecutor.execute_job()`

```python
def execute_job(self, journey_id, job_id):
    # 1. Get job data from DynamoDB
    job_data = get_job_execution(journey_id, job_id)
    
    # 2. Get stage class
    stage_class = get_stage_class(stage_id)
    
    # 3. Create stage instance
    stage = stage_class(journey_id, stage_id, job_id, region_name, role_arn)
    
    # 4. Get steps from stage
    steps = stage.steps  # List of 5 steps for raw_analysis
    
    # 5. Execute each step
    for step_index, step in enumerate(steps):
        execute_single_step(step)
    
    # 6. Complete the job
    complete_job(journey_id, job_id)
```

**Example: Raw Analysis Stage Has 5 Steps:**

```python
steps = [
    {'id': 'schema_parsing', 'name': 'Schema File Parsing'},
    {'id': 'relationship_discovery', 'name': 'Relationship Discovery'},
    {'id': 'data_type_analysis', 'name': 'Data Type Analysis'},
    {'id': 'business_rules_extraction', 'name': 'Business Rules Extraction'},
    {'id': 'complexity_assessment', 'name': 'Complexity Assessment'}
]
```

---

### Phase 3: Step Execution (Detailed)

**For Each Step in the Job:**

#### **Step 3.1: Update Step Status**

```python
update_step_status(journey_id, job_id, step_id, 'in_progress', step_index)
# → DynamoDB: Update stepResults.schema_parsing.status = 'in_progress'
```

#### **Step 3.2: Execute Step Logic**

```python
step_result = stage.execute_step(step_id, step_data)
# → Calls stage-specific implementation
```

**Inside `execute_step()` (in RawAnalysisStage):**

```python
def execute_step(self, step_id, step_data):
    if step_id == 'schema_parsing':
        return self._execute_schema_parsing(step_data)
    elif step_id == 'relationship_discovery':
        return self._execute_relationship_discovery(step_data)
    # ... etc
```

**Example: Schema Parsing Step Execution:**

```python
def _execute_schema_parsing(self, step_data):
    step_id = 'schema_parsing'
    
    # 1. Log start
    self.log_info("Starting schema parsing", step_id)
    
    # 2. Read schema file from S3
    schema_content = self.s3.get_object(
        Bucket='mtn-totolcore-ui-1751374633-4498-1fc9a47e',
        Key='customer-input/MTN-SA/Eppix_Schema_202050317.sql'
    )
    
    # 3. Parse SQL schema
    tables = self._parse_sql_schema(schema_content)
    
    # 4. Log progress
    self.log_info(f"Parsed {len(tables)} tables", step_id)
    
    # 5. Set metrics
    self.set_metric('tables_parsed', len(tables), step_id)
    self.set_metric('total_columns', sum(len(t['columns']) for t in tables), step_id)
    
    # 6. Store artifacts
    self.add_artifact('parsed_tables', tables, step_id)
    
    # 7. Upload logs to S3
    self.upload_logs_to_s3(step_id)
    # → s3://transformation-journey-logs/journeys/JRN-ABC123/
    #    stages/raw_analysis/executions/JOB-001-20251101203000/
    #    logs/schema_parsing.json
    
    # 8. Generate and upload report
    report_data = {
        'stepId': step_id,
        'tablesFound': len(tables),
        'totalColumns': sum(len(t['columns']) for t in tables),
        'complexity': 'medium',
        'recommendations': [...]
    }
    self.upload_report_to_s3(step_id, report_data)
    # → s3://transformation-journey-reports/journeys/JRN-ABC123/
    #    stages/raw_analysis/executions/JOB-001-20251101203000/
    #    reports/schema_parsing.json
    
    # 9. Return results
    return {
        'status': 'completed',
        'metrics': self.metrics.get(step_id, {}),
        'artifacts': self.artifacts.get(step_id, {})
    }
```

#### **Step 3.3: Update Step Results**

```python
update_step_results(journey_id, job_id, step_id, step_result)
# → DynamoDB: Update stepResults.schema_parsing = {
#     status: 'completed',
#     metrics: {...},
#     artifacts: {...}
# }
```

#### **Step 3.4: Update Job Progress**

```python
progress = ((step_index + 1) / len(steps)) * 100
update_job_progress(journey_id, job_id, progress, step_index + 1)
# → DynamoDB: Update progress = 20 (for step 1 of 5)
```

---

### Phase 4: Logging During Execution

**Logging Architecture:**

```
┌─────────────────────────────────────────┐
│   Step Execution (in memory)            │
│                                          │
│   stage.log_info("Processing...")       │
│   ├─> Appends to self.logs[] array     │
│   ├─> Prints to console with emoji     │
│   └─> Writes to local log file         │
└─────────────────────────────────────────┘
              │
              │ After step completes
              ▼
┌─────────────────────────────────────────┐
│   Upload Logs to S3                      │
│                                          │
│   self.upload_logs_to_s3(step_id)       │
│   ├─> Filter logs for this step        │
│   ├─> Convert to JSON                   │
│   └─> PUT to S3 bucket                  │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│   S3: transformation-journey-logs        │
│                                          │
│   Key: journeys/{journey_id}/stages/    │
│        {stage_id}/executions/{job_id}/  │
│        logs/{step_id}.json               │
│                                          │
│   Content: [                             │
│     {                                    │
│       timestamp: "2025-11-01...",        │
│       level: "INFO",                     │
│       message: "Processing table...",    │
│       step_id: "schema_parsing",         │
│       details: {...}                     │
│     },                                   │
│     ...                                  │
│   ]                                      │
└─────────────────────────────────────────┘
```

**Log Levels:**

```python
self.log_info("Processing table: products")      # → Level: INFO
self.log_warning("Missing index on column")      # → Level: WARNING
self.log_error("Failed to parse column type")    # → Level: ERROR
```

**Each log entry structure:**

```json
{
  "timestamp": "2025-11-01T20:30:15.234567Z",
  "level": "INFO",
  "message": "Successfully parsed 45 tables",
  "step_id": "schema_parsing",
  "stage_id": "raw_analysis",
  "job_id": "JOB-001-20251101203000",
  "details": {
    "tables_parsed": 45,
    "total_columns": 450,
    "duration_seconds": 12.5
  }
}
```

---

### Phase 5: Report Generation

**After Each Step:**

```python
def _execute_schema_parsing(self, step_data):
    # ... processing logic ...
    
    # Generate report
    report_data = {
        'reportId': f'{job_id}_schema_parsing',
        'reportType': 'step_completion',
        'title': 'Schema Parsing Results',
        'stepId': 'schema_parsing',
        'executionSummary': {
            'status': 'completed',
            'startTime': '2025-11-01T20:30:00Z',
            'endTime': '2025-11-01T20:30:45Z',
            'duration': 45.2,
            'itemsProcessed': 45
        },
        'detailedResults': {
            'tablesExtracted': 45,
            'columnsExtracted': 450,
            'foreignKeysFound': 23,
            'indexesFound': 67,
            'complexityScore': 'medium'
        },
        'insights': [
            'Schema is well-structured with clear relationships',
            'Foreign keys properly defined for referential integrity',
            'Some tables have large number of columns (>50)'
        ],
        'recommendations': [
            'Review tables with >50 columns for normalization opportunities',
            'Add indexes on frequently queried columns',
            'Document business logic in stored procedures'
        ],
        'generatedAt': '2025-11-01T20:30:45.500000Z'
    }
    
    # Upload to S3
    self.upload_report_to_s3('schema_parsing', report_data)
```

**S3 Report Storage:**

```
s3://transformation-journey-reports/
└── journeys/JRN-ABC123/
    └── stages/raw_analysis/
        └── executions/JOB-001-20251101203000/
            └── reports/
                ├── schema_parsing.json (step 1 report)
                ├── relationship_discovery.json (step 2 report)
                ├── data_type_analysis.json (step 3 report)
                ├── business_rules_extraction.json (step 4 report)
                └── complexity_assessment.json (step 5 report)
```

---

### Phase 6: Job Completion

**After All Steps Complete:**

```python
def complete_job(self, journey_id, job_id):
    end_time = datetime.utcnow().isoformat() + 'Z'
    
    # Calculate duration
    job_data = get_job_execution(journey_id, job_id)
    start_time = job_data['startTime']
    duration = calculate_duration(start_time, end_time)
    
    # Aggregate metrics
    total_logs = sum(step['metrics'].get('log_count', 0) 
                    for step in job_data['stepResults'].values())
    total_errors = sum(step['metrics'].get('error_count', 0) 
                      for step in job_data['stepResults'].values())
    
    # Update job in DynamoDB
    update_job_completion(journey_id, job_id, {
        'status': 'completed',
        'endTime': end_time,
        'duration': duration,
        'progress': 100,
        'jobMetrics': {
            'totalLogs': total_logs,
            'totalErrors': total_errors,
            'totalWarnings': total_warnings,
            'itemsProcessed': items_processed
        }
    })
    
    # Update journey statistics
    update_journey_stats(journey_id, {
        'completedJobs': increment(1),
        'totalExecutionTime': increment(duration)
    })
```

**Final Job Record in DynamoDB:**

```json
{
  "PK": "JOURNEY#JRN-ABC123",
  "SK": "JOB#01#raw_analysis#001#20251101203000",
  "EntityType": "JobExecution",
  "UpdatedAt": "2025-11-01T20:45:00.000000Z",
  "Data": {
    "jobId": "JOB-001-20251101203000",
    "journeyId": "JRN-ABC123",
    "stageId": "raw_analysis",
    "status": "completed",
    "startTime": "2025-11-01T20:30:00.000000Z",
    "endTime": "2025-11-01T20:45:00.000000Z",
    "duration": 900.5,
    "progress": 100,
    "stepResults": {
      "schema_parsing": {
        "status": "completed",
        "progress": 100,
        "metrics": {
          "tables_parsed": 45,
          "total_columns": 450
        }
      },
      "relationship_discovery": {
        "status": "completed",
        "progress": 100,
        "metrics": {
          "foreign_keys_found": 23,
          "relationships_mapped": 67
        }
      },
      "data_type_analysis": {
        "status": "completed",
        "progress": 100,
        "metrics": {
          "data_types_analyzed": 450,
          "type_mappings_created": 450
        }
      },
      "business_rules_extraction": {
        "status": "completed",
        "progress": 100,
        "metrics": {
          "rules_extracted": 12,
          "constraints_found": 34
        }
      },
      "complexity_assessment": {
        "status": "completed",
        "progress": 100,
        "metrics": {
          "complexity_score": 65,
          "risk_areas": 3
        }
      }
    },
    "jobMetrics": {
      "totalLogs": 1450,
      "totalErrors": 2,
      "totalWarnings": 8,
      "itemsProcessed": 45,
      "overallProgress": 100
    }
  }
}
```

---

## Error Handling

### When a Step Fails

```python
try:
    step_result = stage.execute_step(step_id, step_data)
    update_step_results(journey_id, job_id, step_id, step_result)
except Exception as step_error:
    logger.error(f'Error in step {step_id}: {str(step_error)}')
    
    # Mark step as failed
    update_step_status(journey_id, job_id, step_id, 'failed')
    
    # Fail the entire job
    fail_job(journey_id, job_id, str(step_error))
    
    # Re-raise to stop execution
    raise
```

### Job Failure Handling

```python
def fail_job(self, journey_id, job_id, error_message):
    end_time = datetime.utcnow().isoformat() + 'Z'
    
    update_job_completion(journey_id, job_id, {
        'status': 'failed',
        'endTime': end_time,
        'errorMessage': error_message
    })
    
    # Update journey statistics
    update_journey_stats(journey_id, {
        'failedJobs': increment(1)
    })
    
    # Log error
    logger.error(f'Job {job_id} failed: {error_message}')
```

---

## Complete Data Flow Visualization

```
┌──────────────────────┐
│ User/System Trigger  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│ 1. Job Initialization                        │
│ ────────────────────────────────────────────│
│ • Generate Job ID: JOB-001-20251101203000   │
│ • Load journey from DynamoDB                 │
│ • Load stage class (RawAnalysisStage)       │
│ • Create job record in DynamoDB              │
│                                              │
│ DynamoDB Write:                              │
│   PK: JOURNEY#JRN-ABC123                    │
│   SK: JOB#01#raw_analysis#001#timestamp     │
│   Data: { status: "in_progress", ...}       │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│ 2. Step 1: schema_parsing                   │
│ ────────────────────────────────────────────│
│ • Update status: "in_progress"              │
│ • Execute step logic                         │
│   ├─> Read SQL schema from S3               │
│   ├─> Parse table definitions               │
│   ├─> Log to memory (self.logs[])          │
│   └─> Generate metrics                      │
│                                              │
│ S3 Read:                                     │
│   Bucket: mtn-totolcore-ui-...              │
│   Key: customer-input/.../schema.sql        │
│                                              │
│ • Upload logs to S3                          │
│   └─> logs/schema_parsing.json              │
│                                              │
│ • Upload report to S3                        │
│   └─> reports/schema_parsing.json           │
│                                              │
│ • Update step results in DynamoDB            │
│ • Update job progress: 20%                   │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│ 3. Step 2: relationship_discovery           │
│ ────────────────────────────────────────────│
│ • Same pattern as Step 1                     │
│ • Process: Find foreign keys                 │
│ • Upload logs & reports to S3                │
│ • Update progress: 40%                       │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│ 4. Step 3: data_type_analysis               │
│ ────────────────────────────────────────────│
│ • Same pattern                               │
│ • Process: Analyze data types                │
│ • Update progress: 60%                       │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│ 5. Step 4: business_rules_extraction        │
│ ────────────────────────────────────────────│
│ • Same pattern                               │
│ • Process: Extract business rules            │
│ • Update progress: 80%                       │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│ 6. Step 5: complexity_assessment             │
│ ────────────────────────────────────────────│
│ • Same pattern                               │
│ • Process: Assess complexity                 │
│ • Update progress: 100%                      │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│ 7. Job Completion                            │
│ ────────────────────────────────────────────│
│ • Calculate total duration                   │
│ • Aggregate all metrics                      │
│ • Update job status: "completed"             │
│ • Update journey statistics                  │
│                                              │
│ DynamoDB Write:                              │
│   Update: status="completed"                 │
│           endTime="..."                      │
│           jobMetrics={...}                   │
│                                              │
│ Final State:                                 │
│ ├─> 5 log files in S3 (one per step)       │
│ ├─> 5 report files in S3 (one per step)    │
│ └─> Job record in DynamoDB (completed)      │
└──────────────────────────────────────────────┘
```

---

## Key Components

### 1. TransformationJobExecutor

**Location:** `src/utils/job_executor.py`

**Responsibilities:**
- Initialize jobs
- Execute jobs
- Manage job lifecycle
- Update job progress
- Handle errors

**Key Methods:**
```python
start_job_execution()  # Create job record
execute_job()          # Run all steps
update_step_status()   # Update step progress
update_job_progress()  # Update overall progress
complete_job()         # Finalize job
fail_job()             # Handle failures
```

### 2. BaseStage

**Location:** `src/stages/base_stage.py`

**Responsibilities:**
- Define stage interface
- Provide logging utilities
- Handle S3 uploads
- Manage metrics and artifacts

**Key Methods:**
```python
execute_step()          # Execute specific step (abstract)
log_info()              # Log informational message
log_warning()           # Log warning
log_error()             # Log error
upload_logs_to_s3()     # Upload logs after step
upload_report_to_s3()   # Upload report after step
set_metric()            # Track metrics
add_artifact()          # Store results
```

### 3. Stage Implementations

**Location:** `src/stages/{stage-name}/{stage}.py`

**Examples:**
- `src/stages/raw-analysis/raw_analysis.py` → RawAnalysisStage
- `src/stages/stripped-schema/stripped_schema.py` → StrippedSchemaStage

**Responsibilities:**
- Define stage steps
- Implement step execution logic
- Generate stage-specific reports
- Handle stage-specific errors

**Key Methods:**
```python
@property
def steps():              # Define list of steps

execute_step():           # Route to specific step

_execute_step_name():     # Implement step logic
```

---

## Progress Tracking

### Job Progress Calculation

```python
progress = ((current_step_index + 1) / total_steps) * 100

# Example: 5 steps total
# Step 1 complete: (1/5) * 100 = 20%
# Step 2 complete: (2/5) * 100 = 40%
# Step 3 complete: (3/5) * 100 = 60%
# Step 4 complete: (4/5) * 100 = 80%
# Step 5 complete: (5/5) * 100 = 100%
```

### Real-Time Status Updates

Every step completion updates DynamoDB:

```python
{
  "progress": 40,  # Overall job progress
  "currentStepIndex": 2,
  "currentStepId": "relationship_discovery",
  "stepResults": {
    "schema_parsing": {
      "status": "completed",
      "progress": 100
    },
    "relationship_discovery": {
      "status": "completed",
      "progress": 100
    },
    "data_type_analysis": {
      "status": "in_progress",
      "progress": 0
    }
  }
}
```

---

## Summary

**The job execution flow follows a clear pattern:**

1. ✅ **Initialize** - Create job record, prepare environment
2. ✅ **Execute Steps** - Run each step sequentially with logging
3. ✅ **Track Progress** - Update DynamoDB after each step
4. ✅ **Store Results** - Upload logs and reports to S3
5. ✅ **Complete** - Mark job as done, update statistics

**Key Benefits:**

- **Modular:** Each stage is independent and reusable
- **Trackable:** Real-time progress updates in DynamoDB
- **Auditable:** Complete logs and reports in S3
- **Resilient:** Comprehensive error handling at every level
- **Scalable:** Stages can be added/removed without affecting others

This architecture enables the AI Job Engine to handle complex transformation workflows with full visibility, recoverability, and production-grade reliability! 🚀

