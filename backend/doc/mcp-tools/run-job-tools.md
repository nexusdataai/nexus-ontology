#### `run_jobs_tool`
**Purpose:** Comprehensive job management - create, run, monitor, cancel, retry jobs

**Parameters:**
- `journey_id` (required) - Journey ID
- `stage_id` (required for run/create/list) - Stage to execute
- `action` (default: "run") - Action to perform
- `job_id` (required for status/cancel/retry/get) - Job ID
- `triggered_by` (default: "mcp-server")
- `reason` (default: "MCP Server execution")
- `job_config` (optional) - Job configuration parameters
- `wait_for_completion` (default: true) - Wait for job to finish
- `progress_callback` (default: false) - Include progress updates

**Actions:**
- `run` - Create and execute job (default)
- `create` - Create job without executing
- `status` - Get job status and progress
- `get` - Get comprehensive job information
- `cancel` - Cancel a running job
- `retry` - Retry a failed job
- `list` - List jobs for a stage

**What it does:**
1. Routes to appropriate action handler
2. Manages job lifecycle (create, execute, monitor, cancel)
3. Provides job status and progress information
4. Supports retry of failed jobs
5. Lists jobs for a specific stage
6. Returns detailed job information including timeline and step progress

**Returns (run action):**
```json
{
  "status": "success",
  "message": "Job JOB-XXX for stage raw_analysis completed successfully",
  "job_id": "JOB-XXX",
  "journey_id": "JRN-XXX",
  "stage_id": "raw_analysis",
  "execution_status": "completed",
  "job_details": {
    "status": "completed",
    "progress": 100,
    "current_step": "business_rules",
    "step_results": {...}
  }
}