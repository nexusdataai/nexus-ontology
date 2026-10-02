# TMF ODA Transformation System Scripts

This directory contains management scripts for the TMF ODA Transformation System. These scripts provide comprehensive functionality for managing transformation journeys, stages, Second Brain rules, jobs, and DynamoDB infrastructure.

## Table of Contents

- [Setup & Infrastructure](#setup--infrastructure)
- [Journey Management](#journey-management)
- [Stage Management](#stage-management)
- [Second Brain Rules Management](#second-brain-rules-management)
- [Job Execution](#job-execution)
- [Table Inspection & Maintenance](#table-inspection--maintenance)
- [Testing & Development](#testing--development)
- [Utilities](#utilities)
- [AWS Authentication](#aws-authentication)
- [Common Usage Patterns](#common-usage-patterns)

---

## Setup & Infrastructure

### `setup_dynamodb.py`

**Purpose:** Initialize the TransformationSystem DynamoDB infrastructure with Second Brain support.

**Features:**
- Creates the TransformationSystem DynamoDB table with GSI1 index
- Sets up S3 buckets for logs and reports
- Creates sample journey with stages and Second Brain rules
- Configures table with streaming enabled
- Tests AWS credentials before setup

**Usage:**
```bash
python3 setup_dynamodb.py
```

**What it creates:**
- DynamoDB table: `TransformationSystem`
- S3 buckets: `transformation-journey-logs`, `transformation-journey-reports`
- Sample journey: `JRN-SAMPLE-001` with 2 stages and 3 rules

---

## Journey Management

### `create_complete_journey.py`

**Purpose:** Create a complete transformation journey with all 6 stages and comprehensive Second Brain rules.

**Features:**
- Creates journey with full stage definitions
- Generates 10 Second Brain rules across all stages
- Supports multiple ODA component types
- Configures AI-assisted steps
- Validates AWS credentials before creation

**Usage:**
```bash
# Create with default settings
python3 create_complete_journey.py

# Create with custom name and component type
python3 create_complete_journey.py \
  --name "Customer Management Migration" \
  --component-type customer-management
```

**Component Types:**
- `customer-management`
- `product-catalog`
- `order-management`
- `billing`
- `resource-inventory`
- `service-catalog`

**Stages Created:**
1. Raw Input Analysis
2. Create Stripped Document
3. TMF Schema Mapping
4. Data Migration Planning
5. Data Migration
6. Verification & Validation

---

### `manage_journey.py`

**Purpose:** Comprehensive journey, stage, rule, job, log, and report management tool.

**Features:**
- Complete CRUD operations for journeys, stages, rules, jobs
- Log and report management
- Import/export functionality
- Interactive mode and wizard
- Dashboard view
- Batch operations

**Usage:**

#### Journey Operations
```bash
# List all journeys
python3 manage_journey.py --action list-journeys

# Get specific journey
python3 manage_journey.py --action get-journey --journey-id JRN-123

# Create journey from JSON
python3 manage_journey.py --action create-journey --data-file journey.json

# Update journey
python3 manage_journey.py --action update-journey --journey-id JRN-123 --data-file updates.json

# Delete journey
python3 manage_journey.py --action delete-journey --journey-id JRN-123 --confirm
```

#### Stage Operations
```bash
# List stages for a journey
python3 manage_journey.py --action list-stages --journey-id JRN-123

# Add stage
python3 manage_journey.py --action add-stage --journey-id JRN-123 --data-file stage.json

# Add default stages (all 6)
python3 manage_journey.py --action add-default-stages --journey-id JRN-123

# Update stage
python3 manage_journey.py --action update-stage \
  --journey-id JRN-123 --stage-id raw_analysis --data-file updates.json

# Delete stage
python3 manage_journey.py --action delete-stage \
  --journey-id JRN-123 --stage-id raw_analysis --confirm
```

#### Rule Operations
```bash
# List rules for a journey
python3 manage_journey.py --action list-rules --journey-id JRN-123

# Filter rules by type
python3 manage_journey.py --action list-rules \
  --journey-id JRN-123 --rule-type field_mapping

# Add rule
python3 manage_journey.py --action add-rule --journey-id JRN-123 --data-file rule.json

# Update rule
python3 manage_journey.py --action update-rule \
  --journey-id JRN-123 --rule-id rule-123 --data-file updates.json

# Delete rule
python3 manage_journey.py --action delete-rule \
  --journey-id JRN-123 --rule-id rule-123 --confirm
```

#### Job Operations
```bash
# List jobs
python3 manage_journey.py --action list-jobs --journey-id JRN-123

# Get job details
python3 manage_journey.py --action get-job --journey-id JRN-123 --job-id JOB-456

# Run job
python3 manage_journey.py --action run-job \
  --journey-id JRN-123 --stage-id raw_analysis \
  --triggered-by user --reason "Manual execution"

# Update job status
python3 manage_journey.py --action update-job-status \
  --journey-id JRN-123 --job-id JOB-456 \
  --job-status running --progress 50

# Cancel job
python3 manage_journey.py --action cancel-job \
  --journey-id JRN-123 --job-id JOB-456 --reason "User requested"

# Batch cancel jobs
python3 manage_journey.py --action batch-cancel-jobs \
  --journey-id JRN-123 --job-ids "JOB-1,JOB-2,JOB-3"

# Get job metrics
python3 manage_journey.py --action get-job-metrics --journey-id JRN-123 --job-id JOB-456

# Get job timeline
python3 manage_journey.py --action get-job-timeline --journey-id JRN-123 --job-id JOB-456
```

#### Log Operations
```bash
# Get logs for a job
python3 manage_journey.py --action get-job-logs --journey-id JRN-123 --job-id JOB-456

# Add log entry
python3 manage_journey.py --action add-log-entry \
  --journey-id JRN-123 --job-id JOB-456 \
  --log-level info --log-message "Processing started"

# Search logs
python3 manage_journey.py --action search-logs \
  --journey-id JRN-123 --search-query "error"

# Get logs by level
python3 manage_journey.py --action get-logs-by-level \
  --journey-id JRN-123 --level-filter error

# Export job logs
python3 manage_journey.py --action export-job-logs \
  --journey-id JRN-123 --job-id JOB-456 --format json

# Get error summary
python3 manage_journey.py --action get-error-summary --journey-id JRN-123
```

#### Report Operations
```bash
# Get reports for a job
python3 manage_journey.py --action get-job-reports --journey-id JRN-123 --job-id JOB-456

# Create job report
python3 manage_journey.py --action create-job-report \
  --journey-id JRN-123 --job-id JOB-456 \
  --report-type summary --report-title "Job Summary"

# Generate summary report
python3 manage_journey.py --action generate-summary-report --journey-id JRN-123

# Generate performance report
python3 manage_journey.py --action generate-performance-report --journey-id JRN-123
```

#### Import/Export
```bash
# Export complete journey
python3 manage_journey.py --action export-complete \
  --journey-id JRN-123 --output-file journey_backup.json

# Export with all details
python3 manage_journey.py --action export-complete \
  --journey-id JRN-123 --output-file journey_full.json --include-all

# Import journey
python3 manage_journey.py --action import-complete --input-file journey_backup.json
```

#### Interactive Modes
```bash
# Interactive mode (menu-driven)
python3 manage_journey.py --action interactive

# Dashboard view
python3 manage_journey.py --action dashboard --journey-id JRN-123

# Setup wizard
python3 manage_journey.py --action wizard
```

---

### `delete_journey.py`

**Purpose:** Safely delete transformation journeys with all associated data.

**Features:**
- Deletes journey metadata, stages, rules, jobs, logs, and reports
- Shows preview of data to be deleted
- S3 object cleanup for logs and reports
- Requires confirmation (type "DELETE")
- Batch deletion support
- List available journeys before deletion

**Usage:**
```bash
# List available journeys first
python3 delete_journey.py --list-first

# Delete specific journey
python3 delete_journey.py --journey-id JRN-123

# Delete multiple journeys
python3 delete_journey.py --journey-ids JRN-123,JRN-456,JRN-789

# Skip confirmation (use with caution!)
python3 delete_journey.py --journey-id JRN-123 --yes
```

**Safety Features:**
- Shows detailed breakdown of what will be deleted
- Requires typing "DELETE" to confirm
- `--yes` flag for automated scripts
- Lists S3 objects that will be removed

---

### `cleanup_incomplete_journeys.py`

**Purpose:** Clean up test data by deleting journeys with incorrect stage counts.

**Features:**
- Identifies journeys with non-standard stage configurations
- Dry-run mode to preview deletions
- Configurable stage count filter
- Detailed reporting of deletions

**Usage:**
```bash
# Preview what would be deleted (dry run)
python3 cleanup_incomplete_journeys.py --dry-run

# Actually delete incomplete journeys
python3 cleanup_incomplete_journeys.py --confirm

# Delete journeys with specific stage count
python3 cleanup_incomplete_journeys.py --stages-count 4 --confirm
```

**Default Behavior:**
- Keeps journeys with exactly 6 stages
- Deletes journeys with any other stage count
- Always shows preview before deletion

---

## Stage Management

### `manage_journey_stages.py`

**Purpose:** Dedicated stage management tool with focus on stage operations.

**Features:**
- List, add, update, delete stages
- View stage details and steps
- Interactive stage builder
- Stage validation
- Step management

**Usage:**
```bash
# List stages
python3 manage_journey_stages.py --action list --journey-id JRN-123

# Get stage details
python3 manage_journey_stages.py --action get \
  --journey-id JRN-123 --stage-id raw_analysis

# Add stage from JSON
python3 manage_journey_stages.py --action add \
  --journey-id JRN-123 --data-file stage.json

# Update stage
python3 manage_journey_stages.py --action update \
  --journey-id JRN-123 --stage-id raw_analysis --data-file updates.json

# Delete stage
python3 manage_journey_stages.py --action delete \
  --journey-id JRN-123 --stage-id raw_analysis --confirm

# Interactive mode
python3 manage_journey_stages.py --action interactive --journey-id JRN-123
```

---

## Second Brain Rules Management

### `manage_second_brain_rules.py`

**Purpose:** Comprehensive Second Brain rules management.

**Features:**
- CRUD operations for rules
- Filter by type, priority, stage, status
- Batch operations
- Rule validation
- Import/export rules
- Interactive rule builder

**Usage:**
```bash
# List all rules
python3 manage_second_brain_rules.py --action list --journey-id JRN-123

# Filter by type
python3 manage_second_brain_rules.py --action list \
  --journey-id JRN-123 --rule-type field_mapping

# Filter by priority
python3 manage_second_brain_rules.py --action list \
  --journey-id JRN-123 --priority high

# Filter by stage
python3 manage_second_brain_rules.py --action list \
  --journey-id JRN-123 --stage-id raw_analysis

# Get specific rule
python3 manage_second_brain_rules.py --action get \
  --journey-id JRN-123 --rule-id rule-123

# Add rule
python3 manage_second_brain_rules.py --action add \
  --journey-id JRN-123 --data-file rule.json

# Update rule
python3 manage_second_brain_rules.py --action update \
  --journey-id JRN-123 --rule-id rule-123 --data-file updates.json

# Delete rule
python3 manage_second_brain_rules.py --action delete \
  --journey-id JRN-123 --rule-id rule-123 --confirm

# Delete multiple rules
python3 manage_second_brain_rules.py --action batch-delete \
  --journey-id JRN-123 --rule-ids "rule-1,rule-2,rule-3" --confirm

# Export rules
python3 manage_second_brain_rules.py --action export \
  --journey-id JRN-123 --output-file rules.json

# Import rules
python3 manage_second_brain_rules.py --action import \
  --journey-id JRN-123 --input-file rules.json

# Interactive mode
python3 manage_second_brain_rules.py --action interactive --journey-id JRN-123
```

**Rule Types:**
- `field_mapping` - Field-to-TMF mappings
- `contextual_recommendations` - AI guidance and best practices
- `data_interpretation` - Data understanding rules
- `validation_rules` - Validation and compliance checks

**Priority Levels:**
- `critical` - Must be applied
- `high` - Important
- `medium` - Recommended
- `low` - Optional

---

## Job Execution

### `run_transformation_job.py`

**Purpose:** Execute transformation jobs for specific stages.

**Features:**
- Starts job execution for a stage
- Configurable triggering user and reason
- Job status tracking
- Error handling and logging

**Usage:**
```bash
python3 run_transformation_job.py \
  --journey-id JRN-123 \
  --stage-id raw_analysis \
  --triggered-by admin \
  --reason "Manual execution for testing"
```

---

## Table Inspection & Maintenance

### `inspect_dynamodb_table.py`

**Purpose:** Comprehensive inspection and reporting of TransformationSystem table data.

**Features:**
- Complete table statistics
- Detailed journey information
- Stage, rule, job, log, and report analysis
- JSON export capability
- Journey-specific inspection
- Stats-only mode for quick overview

**Usage:**
```bash
# Full inspection
python3 inspect_dynamodb_table.py

# View specific journey
python3 inspect_dynamodb_table.py --journey-id JRN-123

# Statistics only
python3 inspect_dynamodb_table.py --stats-only

# Export as JSON
python3 inspect_dynamodb_table.py --format json > table_data.json
```

**Output Includes:**
- Total items by entity type
- Journey status breakdown
- Stage status distribution
- Rule categorization (by type and priority)
- Job status summary
- Log and report counts
- Detailed per-journey information

---

### `cleanup_dynamodb_table.py`

**Purpose:** Complete cleanup of TransformationSystem table (deletes ALL data).

**Features:**
- Scans and deletes all table items
- Shows detailed preview before deletion
- Entity type breakdown
- Journey listing
- Batch deletion for efficiency
- Progress tracking with deletion rate

**Usage:**
```bash
# Interactive mode (requires confirmation)
python3 cleanup_dynamodb_table.py

# Non-interactive mode (auto-confirm)
python3 cleanup_dynamodb_table.py --yes
```

**Safety:**
- Requires typing "DELETE ALL" to confirm
- Shows complete data breakdown before deletion
- `--yes` flag bypasses confirmation (use with caution!)
- Reports deletion rate and timing

---

## Testing & Development

### `manage_journey_test.py`

**Purpose:** Comprehensive test suite for journey management functionality.

**Features:**
- Tests all CRUD operations
- Journey, stage, rule, job testing
- Log and report testing
- Import/export validation
- Error handling tests
- Edge case testing
- Performance testing
- Concurrency testing
- Data integrity verification

**Test Categories:**
- Journey operations
- Stage management
- Rule management
- Job operations
- Log operations
- Report operations
- Import/export
- Error handling
- Data validation
- Interactive mode
- Performance
- Concurrency

**Usage:**
```bash
# Run all tests
python3 manage_journey_test.py

# Run specific test category
python3 manage_journey_test.py --category journey

# Run with verbose output
python3 manage_journey_test.py --verbose

# Run performance tests
python3 manage_journey_test.py --category performance
```

---

### `test_stage_creation.py`

**Purpose:** Test stage creation functionality through the API.

**Features:**
- Tests journey creation
- Validates stage addition
- Verifies stage retrieval
- Tests error handling

**Usage:**
```bash
# Requires server to be running on localhost:8000
python3 test_stage_creation.py
```

---

### `test_stage_creation_fix.py`

**Purpose:** Verify stage creation fixes are working correctly.

**Features:**
- Tests fixed stage creation logic
- Validates bug fixes
- Regression testing

**Usage:**
```bash
# Requires server to be running on localhost:8000
python3 test_stage_creation_fix.py
```

---

## Utilities

### `update_raw_analysis_steps.py`

**Purpose:** Update raw_analysis stage definition to include all required steps.

**Features:**
- Updates existing stages with new step definitions
- Adds missing steps
- Preserves existing configuration
- Updates all journeys

**Usage:**
```bash
python3 update_raw_analysis_steps.py
```

**What it Updates:**
- Adds all 5 required steps to raw_analysis stage
- Sets AI-assisted flags
- Updates step order and duration
- Maintains backward compatibility

---

## AWS Authentication

All scripts support multiple authentication methods:

### Environment Setup

**Virtual Environment (Recommended):**
```bash
# Activate virtual environment
source .venv/bin/activate
```

### Authentication Methods

### 1. Assume Role with Script (Recommended)
```bash
# Assume the external access role
./deploy/assume-role-to-profile.sh arn:aws:iam::764119721991:role/AssumableExternalAccessRole external-access

# Export the profile
export AWS_PROFILE=external-access

# Run scripts
python scripts/journey-scripts/script_name.py
```

### 2. AWS Profile (Direct)
```bash
export AWS_PROFILE=external-access
python scripts/journey-scripts/script_name.py
```

### 3. Role ARN (Environment Variable)
```bash
export AWS_ROLE_ARN=arn:aws:iam::123456789012:role/RoleName
python scripts/journey-scripts/script_name.py
```

### 4. Default Credential Chain
```bash
# Uses default AWS credentials from ~/.aws/credentials
python scripts/journey-scripts/script_name.py
```

### Complete Setup Example
```bash
# 1. Navigate to project
cd /opt/mycode/ptr/ai-job-engine

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Setup AWS credentials
./deploy/assume-role-to-profile.sh arn:aws:iam::764119721991:role/AssumableExternalAccessRole external-access
export AWS_PROFILE=external-access

# 4. Run any script
python scripts/journey-scripts/manage_journey.py --action list-journeys
```

---

## Common Usage Patterns

### Complete Setup Flow
```bash
# 0. Setup environment
cd /opt/mycode/ptr/ai-job-engine
source .venv/bin/activate
export AWS_PROFILE=external-access

# 1. Setup infrastructure
python scripts/journey-scripts/setup_dynamodb.py

# 2. Create a complete journey
python scripts/journey-scripts/create_complete_journey.py --name "My Journey" --component-type customer-management

# 3. Inspect the table
python scripts/journey-scripts/inspect_dynamodb_table.py

# 4. List journeys
python scripts/journey-scripts/manage_journey.py --action list-journeys
```

### Journey Development Flow
```bash
# Setup
source .venv/bin/activate
export AWS_PROFILE=external-access

# 1. Create journey
python scripts/journey-scripts/manage_journey.py --action create-journey --data-file journey.json

# 2. Add stages
python scripts/journey-scripts/manage_journey.py --action add-default-stages --journey-id JRN-123

# 3. Add rules
python scripts/journey-scripts/manage_second_brain_rules.py --action add --journey-id JRN-123 --data-file rule.json

# 4. Run job
python scripts/journey-scripts/run_transformation_job.py --journey-id JRN-123 --stage-id raw_analysis

# 5. Monitor progress
python scripts/journey-scripts/manage_journey.py --action dashboard --journey-id JRN-123
```

### Maintenance Flow
```bash
# Setup
source .venv/bin/activate
export AWS_PROFILE=external-access

# 1. Inspect current state
python scripts/journey-scripts/inspect_dynamodb_table.py --stats-only

# 2. Clean up incomplete journeys
python scripts/journey-scripts/cleanup_incomplete_journeys.py --dry-run
python scripts/journey-scripts/cleanup_incomplete_journeys.py --confirm

# 3. Delete specific journey
python scripts/journey-scripts/delete_journey.py --journey-id JRN-123

# 4. Complete table cleanup (if needed)
python scripts/journey-scripts/cleanup_dynamodb_table.py
```

### Backup and Restore Flow
```bash
# Setup
source .venv/bin/activate
export AWS_PROFILE=external-access

# Backup
python scripts/journey-scripts/manage_journey.py --action export-complete \
  --journey-id JRN-123 --output-file backup.json --include-all

# Restore
python scripts/journey-scripts/manage_journey.py --action import-complete --input-file backup.json
```

### Testing Flow
```bash
# Setup
source .venv/bin/activate
export AWS_PROFILE=external-access

# 1. Run comprehensive tests
python scripts/journey-scripts/manage_journey_test.py

# 2. Test stage creation
python scripts/journey-scripts/test_stage_creation.py

# 3. Verify fixes
python scripts/journey-scripts/test_stage_creation_fix.py
```

---

## Environment Variables

Common environment variables used by scripts:

```bash
# AWS Authentication
export AWS_PROFILE=external-access
export AWS_ROLE_ARN=arn:aws:iam::123456789012:role/RoleName
export AWS_REGION=us-east-1

# DynamoDB Configuration
export DYNAMODB_TABLE=TransformationSystem

# S3 Configuration
export S3_LOGS_BUCKET=transformation-journey-logs
export S3_REPORTS_BUCKET=transformation-journey-reports
```

---

## Script Dependencies

All scripts use:
- `boto3` - AWS SDK
- `src.utils.aws_client_utils` - Centralized AWS client management

Some scripts additionally require:
- `requests` - For API testing scripts
- Standard library: `json`, `argparse`, `sys`, `os`, `datetime`, `traceback`

---

## Error Handling

All scripts include:
- ✅ Comprehensive error messages
- ✅ Traceback output for debugging
- ✅ AWS credential validation
- ✅ DynamoDB connection testing
- ✅ Graceful failure handling
- ✅ User-friendly error reporting

---

## Tips and Best Practices

1. **Always test with `--dry-run` or `--stats-only` first** when using destructive operations
2. **Use `--list-first` flags** to see what will be affected
3. **Export journeys before deletion** for backup purposes
4. **Use interactive modes** for learning and exploration
5. **Set AWS_PROFILE** for consistent authentication
6. **Check `--help`** on any script for detailed usage
7. **Use JSON export** for data analysis and reporting
8. **Run tests regularly** to ensure system integrity

---

## Getting Help

For any script, use the `--help` flag:
```bash
python3 script_name.py --help
```

For issues or questions:
1. Check the script's help text
2. Review the error messages and tracebacks
3. Verify AWS credentials are configured
4. Ensure DynamoDB table exists
5. Check the script's source code comments

---

## Version History

- **v1.0** - Initial script collection
- **v1.1** - Added Second Brain rules support
- **v1.2** - Enhanced job and log management
- **v1.3** - Added inspection and cleanup tools
- **v1.4** - Centralized AWS authentication
- **v1.5** - Added comprehensive testing suite

---

## Contributing

When adding new scripts:
1. Follow the existing naming conventions
2. Include comprehensive `--help` text
3. Add error handling and validation
4. Use `print_with_flush()` for output
5. Support AWS authentication patterns
6. Update this README

---

## License

Part of the TMF ODA Transformation System project.

