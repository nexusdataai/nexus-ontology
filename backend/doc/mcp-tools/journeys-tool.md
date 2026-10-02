# `journeys_tool`

**Purpose:** Core journey, stage, and rule management (CRUD operations). Supports comprehensive journey lifecycle management, stage orchestration, Second Brain AI rules, and job monitoring.

## Parameters

### Common Parameters
- `action` (required) - Action to perform (see Actions section)
- `journey_id` - Journey ID (required for most operations)
- `stage_id` - Stage ID (for stage operations)
- `rule_id` - Rule ID (for rule operations)
- `job_id` - Job ID (for job operations)

### Journey Creation/Update Parameters
- `name` - Journey name (for create)
- `description` - Journey description
- `odaComponentType` - ODA component type (PRODUCTCATALOG, CUSTOMER, ORDER, etc.)
- `journey_data` - Complete journey data dict with:
  - `name` - Journey name
  - `description` - Journey description
  - `odaComponentType` - Component type
  - `priority` - Priority level (low, medium, high, critical)
  - `status` - Status (pending, running, completed, failed, paused, cancelled)
  - `createdBy` - Creator identifier
  - `tags` - List of tags
  - `metadata` - Additional metadata

### Stage Management Parameters
- `stage_data` - Stage definition dict with:
  - `stageId` - Stage identifier
  - `name` - Stage name
  - `description` - Stage description
  - `order` - Stage order in sequence (integer)
  - `secondBrainEnabled` - Enable AI assistance (boolean)
  - `estimatedDuration` - Estimated duration (e.g., "30m", "2h")
  - `status` - Stage status
  - `steps` - List of step definitions
  - `dependencies` - List of dependent stage IDs
  - `metadata` - Additional metadata

### Rule Management Parameters
- `rule_data` - Second Brain rule dict with:
  - `title` - Rule title (required)
  - `description` - Rule description (required)
  - `type` - Rule type: field_mapping, contextual_recommendations, data_interpretation, validation_rules, business_logic, compliance_check (required)
  - `priority` - Priority level (low, medium, high, critical) (required)
  - `scope` - Rule scope: global, project, stage (required)
  - `status` - Rule status: active, inactive, deprecated (required)
  - `context` - Rule context description (required)
  - `content` - Rule content/prompt (required)
  - `conditions` - Rule conditions dict
  - `actions` - Rule actions dict
  - `examples` - List of example dicts
  - `metadata` - Additional metadata
- `rule_type` - Filter rules by type (for list_rules)

### Filter Parameters
- `status_filter` - Filter journeys by status (pending, running, completed, failed, paused, cancelled)
- `component_type_filter` - Filter journeys by ODA component type

### Job Management Parameters
- `job_status` - Job status for updates (pending, running, completed, failed, cancelled)
- `progress` - Job progress percentage (0-100)
- `current_step` - Current execution step name
- `error_message` - Error message for failed jobs
- `job_ids` - List of job IDs (for batch operations)
- `reason` - Reason for operation (for cancellations, job execution)
- `triggered_by` - Who triggered the job execution (for run_job action)

### Import/Export Parameters
- `output_file` - Output file path for export operations
- `input_file` - Input file path for import operations
- `new_journey_id` - New journey ID for import (optional)

### Options
- `include_all` - Include all details (boolean, default: false)
- `confirm` - Skip confirmation prompts (boolean, default: false)

---

## Actions (24 Total)

### Journey CRUD Operations (5 actions)

#### `create`
Create a new journey with metadata.

**Required Parameters:**
- Either `journey_data` OR (`name` + `odaComponentType`)

**Example Request:**
```json
{
  "action": "create",
  "name": "Product Catalog Migration",
  "odaComponentType": "PRODUCTCATALOG",
  "description": "Migrate legacy product catalog to TMF620"
}
```

**Example Response:**
```json
{
  "status": "success",
  "message": "Journey created successfully",
  "operation": "create_journey",
  "journey_id": "JRN-ABC123",
  "data": {
    "journeyId": "JRN-ABC123",
    "name": "Product Catalog Migration",
    "status": "pending",
    "priority": "medium",
    "odaComponentType": "PRODUCTCATALOG",
    "createdAt": "2025-11-01T20:30:00.000000Z",
    "createdBy": "system"
  }
}
```

#### `read`
Get detailed information about a specific journey.

**Required Parameters:**
- `journey_id`

**Example Request:**
```json
{
  "action": "read",
  "journey_id": "JRN-ABC123"
}
```

#### `update`
Update journey metadata.

**Required Parameters:**
- `journey_id`
- `journey_data` (fields to update)

**Example Request:**
```json
{
  "action": "update",
  "journey_id": "JRN-ABC123",
  "journey_data": {
    "status": "running",
    "priority": "high"
  }
}
```

#### `delete`
Delete a journey and all related data (stages, rules, jobs, logs).

**Required Parameters:**
- `journey_id`

**Optional Parameters:**
- `confirm` (set to true to skip confirmation)

#### `list`
List all journeys with optional filtering.

**Optional Parameters:**
- `status_filter` - Filter by status
- `component_type_filter` - Filter by ODA component type

**Example Request:**
```json
{
  "action": "list",
  "status_filter": "running"
}
```

**Example Response:**
```json
{
  "status": "success",
  "message": "Found 3 journeys",
  "operation": "list_journeys",
  "data": [
    {
      "journeyId": "JRN-ABC123",
      "name": "Product Catalog Migration",
      "status": "running",
      "priority": "high",
      "odaComponentType": "PRODUCTCATALOG",
      "overallProgress": 45,
      "currentStageId": "tmf_mapping"
    }
  ],
  "metadata": {
    "total_count": 3,
    "filters": {
      "status": "running",
      "component_type": null
    }
  }
}
```

---

### Stage Management (5 actions)

#### `list_stages`
List all stages for a journey with their status, steps, rules, and jobs.

**Required Parameters:**
- `journey_id`

#### `add_stage`
Add a custom stage to a journey.

**Required Parameters:**
- `journey_id`
- `stage_data` (complete stage definition)

**Example Request:**
```json
{
  "action": "add_stage",
  "journey_id": "JRN-ABC123",
  "stage_data": {
    "stageId": "custom_validation",
    "name": "Custom Business Validation",
    "description": "Apply custom business rules",
    "order": 7,
    "secondBrainEnabled": true,
    "estimatedDuration": "45m",
    "steps": [
      {
        "stepId": "business_rules_check",
        "name": "Business Rules Validation",
        "aiAssisted": true
      }
    ]
  }
}
```

#### `update_stage`
Update an existing stage definition.

**Required Parameters:**
- `journey_id`
- `stage_id`
- `stage_data` (fields to update)

#### `delete_stage`
Delete a stage from a journey.

**Required Parameters:**
- `journey_id`
- `stage_id`

**Optional Parameters:**
- `confirm` (set to true to skip confirmation)

#### `add_default_stages`
Add all 6 default TMF ODA transformation stages to a journey:
1. **raw_analysis** - Analyze source schema and data
2. **stripped_schema** - Extract and clean schema
3. **tmf_mapping** - Map to TMF API specifications
4. **migration_planning** - Plan data migration strategy
5. **data_migration** - Execute data transformation
6. **verification_validation** - Validate transformed data

**Required Parameters:**
- `journey_id`

**Example Request:**
```json
{
  "action": "add_default_stages",
  "journey_id": "JRN-ABC123"
}
```

---

### Rule Management (4 actions)

Second Brain AI rules provide intelligent assistance during transformation stages.

#### `list_rules`
List Second Brain rules for a journey or stage.

**Required Parameters:**
- `journey_id`

**Optional Parameters:**
- `stage_id` - Filter by specific stage
- `rule_type` - Filter by rule type

**Example Request:**
```json
{
  "action": "list_rules",
  "journey_id": "JRN-ABC123",
  "stage_id": "tmf_mapping",
  "rule_type": "field_mapping"
}
```

#### `add_rule`
Add a new Second Brain AI rule to a journey/stage.

**Required Parameters:**
- `journey_id`
- `stage_id`
- `rule_data` (complete rule definition with all required fields)

**Example Request:**
```json
{
  "action": "add_rule",
  "journey_id": "JRN-ABC123",
  "stage_id": "raw_analysis",
  "rule_data": {
    "title": "Validate Product SKU Format",
    "description": "Ensure product SKU follows company standard format",
    "type": "validation_rules",
    "priority": "high",
    "scope": "stage",
    "status": "active",
    "context": "Product catalog validation during raw analysis",
    "content": "Check that all product SKUs match pattern: [A-Z]{3}-[0-9]{6}",
    "conditions": {
      "applies_to": ["product_catalog", "inventory"]
    },
    "examples": [
      {
        "valid": "PRD-123456",
        "invalid": "P123456"
      }
    ]
  }
}
```

#### `update_rule`
Update an existing Second Brain rule.

**Required Parameters:**
- `journey_id`
- `stage_id`
- `rule_id`
- `rule_data` (fields to update)

#### `delete_rule`
Delete a Second Brain rule from a journey.

**Required Parameters:**
- `journey_id`
- `stage_id`
- `rule_id`

**Optional Parameters:**
- `confirm` (set to true to skip confirmation)

---

### Journey Utilities (5 actions)

#### `export_complete`
Export complete journey data including all stages, rules, jobs, and metadata to a JSON file.

**Required Parameters:**
- `journey_id`
- `output_file` - Path to output JSON file

**Example Request:**
```json
{
  "action": "export_complete",
  "journey_id": "JRN-ABC123",
  "output_file": "/tmp/journey_backup.json"
}
```

#### `import_complete`
Import a journey from a previously exported JSON file.

**Required Parameters:**
- `input_file` - Path to input JSON file

**Optional Parameters:**
- `new_journey_id` - Assign new journey ID (otherwise generates new one)

#### `dashboard`
Get comprehensive dashboard view of journey including summary, stages, rules, and recent jobs.

**Required Parameters:**
- `journey_id`

#### `get_journey_summary`
Get high-level summary statistics for a journey.

**Required Parameters:**
- `journey_id`

**Example Response:**
```json
{
  "status": "success",
  "message": "Journey summary retrieved",
  "operation": "get_journey_summary",
  "journey_id": "JRN-ABC123",
  "data": {
    "journeyId": "JRN-ABC123",
    "name": "Product Catalog Migration",
    "status": "running",
    "priority": "high",
    "overallProgress": 45,
    "currentStageId": "tmf_mapping",
    "totalStages": 6,
    "totalRules": 12,
    "activeRules": 10
  }
}
```

#### `get_comprehensive`
Get complete comprehensive data for a journey including all nested structures.

**Required Parameters:**
- `journey_id`

---

### Job Operations (5 actions)

#### `run_job`
Execute a transformation job for a specific stage of a journey.

**Required Parameters:**
- `journey_id` - The ID of the journey
- `stage_id` - The stage to execute (e.g., raw_analysis, stripped_schema)

**Optional Parameters:**
- `triggered_by` - Who triggered the job execution (default: "system")
- `reason` - Reason for running the job (default: "Automated execution via MCP")

**Example Request:**
```json
{
  "action": "run_job",
  "journey_id": "JRN-ABC123",
  "stage_id": "raw_analysis",
  "triggered_by": "user",
  "reason": "Manual execution for testing"
}
```

**Example Response:**
```json
{
  "status": "success",
  "message": "Job JOB-789 completed successfully for stage raw_analysis",
  "operation": "run_job",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-789",
  "data": {
    "job_id": "JOB-789",
    "stage_id": "raw_analysis",
    "status": "completed",
    "triggered_by": "user",
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:32:30Z"
  }
}
```

#### `update_job_status`
Update the status and progress of a running job.

**Required Parameters:**
- `journey_id`
- `job_id`
- `job_status` (pending, running, completed, failed, cancelled)

**Optional Parameters:**
- `progress` - Progress percentage (0-100)
- `current_step` - Current step name
- `error_message` - Error message if failed

**Example Request:**
```json
{
  "action": "update_job_status",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "job_status": "running",
  "progress": 65,
  "current_step": "field_mapping_analysis"
}
```

#### `get_job_metrics`
Get detailed performance metrics for a job.

**Required Parameters:**
- `journey_id`
- `job_id`

**Example Response:**
```json
{
  "status": "success",
  "message": "Job metrics retrieved successfully",
  "operation": "get_job_metrics",
  "journey_id": "JRN-ABC123",
  "job_id": "JOB-456",
  "data": {
    "job_id": "JOB-456",
    "stage_id": "raw_analysis",
    "status": "completed",
    "progress": 100,
    "duration": 125.5,
    "totalLogs": 145,
    "errorCount": 2,
    "warningCount": 8,
    "startTime": "2025-11-01T20:00:00Z",
    "endTime": "2025-11-01T20:02:05Z"
  }
}
```

#### `get_job_timeline`
Get execution timeline for a job showing all steps and their duration.

**Required Parameters:**
- `journey_id`
- `job_id`

#### `batch_cancel_jobs`
Cancel multiple jobs at once.

**Required Parameters:**
- `journey_id`
- `job_ids` - List of job IDs to cancel

**Optional Parameters:**
- `reason` - Reason for cancellation

**Example Request:**
```json
{
  "action": "batch_cancel_jobs",
  "journey_id": "JRN-ABC123",
  "job_ids": ["JOB-456", "JOB-457", "JOB-458"],
  "reason": "Switching to updated transformation rules"
}
```

---

## Data Models

### Journey Status
- `pending` - Journey created, not started
- `running` - Journey execution in progress
- `completed` - Journey successfully completed
- `failed` - Journey execution failed
- `paused` - Journey temporarily paused
- `cancelled` - Journey cancelled by user

### Priority Levels
- `low` - Low priority
- `medium` - Medium priority (default)
- `high` - High priority
- `critical` - Critical priority

### Stage IDs (Default Stages)
- `raw_analysis` - Analyze source schema and data
- `stripped_schema` - Extract and clean schema
- `tmf_mapping` - Map to TMF API specifications
- `migration_planning` - Plan data migration strategy
- `data_migration` - Execute data transformation
- `verification_validation` - Validate transformed data

### Rule Types (Second Brain)
- `field_mapping` - Field-level mapping rules
- `contextual_recommendations` - Context-aware suggestions
- `data_interpretation` - Data interpretation guidance
- `validation_rules` - Validation and compliance rules
- `business_logic` - Business logic rules
- `compliance_check` - Regulatory compliance checks

### Rule Scope
- `global` - Applies to all journeys
- `project` - Applies to specific project
- `stage` - Applies to specific stage

### Rule Status
- `active` - Rule is active and being used
- `inactive` - Rule is disabled
- `deprecated` - Rule is deprecated

### Job Status
- `pending` - Job queued for execution
- `running` - Job currently executing
- `completed` - Job completed successfully
- `failed` - Job execution failed
- `cancelled` - Job was cancelled

---

## Response Format

All operations return a standardized response:

```json
{
  "status": "success" | "error",
  "message": "Human-readable message",
  "operation": "operation_name",
  "journey_id": "JRN-XXX",
  "data": { /* operation-specific data */ },
  "metadata": { /* additional metadata */ },
  "error": "error details (only if status=error)"
}
```

---

## What It Does

1. **Routes Operations** - Dispatches to appropriate handler based on action
2. **Validates Parameters** - Uses Pydantic models to validate all parameters
3. **DynamoDB Operations** - Executes async operations via JourneyService
4. **Manages Journey Lifecycle** - Complete CRUD for journeys, stages, rules
5. **Job Monitoring** - Track and update job execution status
6. **Data Export/Import** - Backup and restore complete journey data
7. **Error Handling** - Comprehensive error handling with detailed messages
8. **Decimal Conversion** - Automatically converts DynamoDB Decimal types to float

---

## Error Handling

The tool provides detailed error messages for:
- **Validation Errors** - Missing or invalid required parameters
- **Not Found Errors** - Journey, stage, or rule not found
- **Operation Errors** - DynamoDB operation failures
- **Permission Errors** - AWS credential or permission issues

Example error response:
```json
{
  "status": "error",
  "message": "journey_id is required for action 'read'",
  "operation": "read",
  "error": "Validation error: journey_id is required for action 'read'"
}
```

---

## Implementation Details

- **Service Layer**: Uses `JourneyService` for all DynamoDB operations
- **Model Layer**: Uses Pydantic models for validation (`JourneyActionRequest`, `JourneyResponse`)
- **Async Execution**: All operations run asynchronously using `asyncio.run_in_executor`
- **DynamoDB Table**: Stores data in `TransformationSystem` table
- **Decimal Handling**: Automatically converts DynamoDB Decimal types for JSON serialization
- **MCP Protocol**: Fully compliant with MCP tool protocol for Cursor integration

---

## Best Practices

1. **Always provide required parameters** - Check action requirements before calling
2. **Use filters for list operations** - Filter by status or component type for better performance
3. **Export journeys before major changes** - Create backups before destructive operations
4. **Set confirm=true for automation** - Skip interactive confirmations in automated workflows
5. **Monitor job status** - Use job operations to track execution progress
6. **Leverage Second Brain rules** - Add AI rules for intelligent transformation assistance
