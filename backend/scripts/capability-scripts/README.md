# Business Capability Management Scripts

## Overview
This folder contains scripts for managing the TMF ODA Business Capability System in DynamoDB. These scripts handle table setup, data management, and capability lifecycle operations.

**Important Update**: The system now uses a single consolidated table design pattern (similar to TransformationSystem) where all capability-related data (capabilities, components, jobs, metrics) is stored in a single `BusinessCapability` table instead of multiple separate tables.

## DynamoDB Table - Single Table Design

### BusinessCapability Table
A single consolidated table using single-table design pattern to store all capability-related data:

**Table Structure:**
- **Table Name**: BusinessCapability
- **Primary Key**: PK (CAPABILITY#capabilityId), SK (entity-specific)
- **GSI1**: For status and type queries
- **GSI2**: For owner and assignee queries
- **GSI3**: For domain and component type queries
- **GSI4**: For date-based queries (metrics, jobs)
- **TTL**: Enabled for automatic metrics cleanup

**Entity Types Stored:**

1. **Business Capabilities** 
   - PK: CAPABILITY#<capabilityId>
   - SK: METADATA
   - Stores: Core capability information (name, description, status, domain, etc.)

2. **Components**
   - PK: CAPABILITY#<capabilityId>
   - SK: COMPONENT#<componentId>
   - Stores: Software components associated with capabilities

3. **Implementation Jobs**
   - PK: CAPABILITY#<capabilityId>
   - SK: JOB#<jobId>
   - Stores: Implementation and deployment job tracking

4. **Performance Metrics**
   - PK: CAPABILITY#<capabilityId>
   - SK: METRIC#<timestamp>#<metricId>
   - Stores: Performance metrics with TTL for auto-cleanup

5. **Version History**
   - PK: CAPABILITY#<capabilityId>
   - SK: VERSION#<timestamp>
   - Stores: Historical snapshots of capability changes

6. **Dependencies**
   - PK: CAPABILITY#<capabilityId>
   - SK: DEPENDENCY#<targetCapabilityId>
   - Stores: Inter-capability dependency relationships

## Setup & Management Scripts

### 📋 setup_business_capability_table.py
Creates the consolidated BusinessCapability table using single-table design.

```bash
# Create the single consolidated table
python3 setup_business_capability_table.py

# With custom role
AWS_ROLE_ARN=arn:aws:iam::... python3 setup_business_capability_table.py
```

**Features:**
- Creates single consolidated table with 4 GSI indexes
- Implements single-table design pattern
- Configures TTL for metrics retention
- Supports all entity types in one table
- Follows TransformationSystem pattern

### 🧹 cleanup_business_capability_table.py
Removes all data from the BusinessCapability table (destructive operation).

```bash
# Clean the table (with confirmation)
python3 cleanup_business_capability_table.py

# Skip confirmation
python3 cleanup_business_capability_table.py --yes

### 🔄 migrate_to_single_table.py
Migrates data from old multi-table structure to new single table (if upgrading).

```bash
# Dry run to see what would be migrated
python3 migrate_to_single_table.py --dry-run

# Perform actual migration
python3 migrate_to_single_table.py

# Skip confirmation
python3 migrate_to_single_table.py --skip-confirmation

# Clean specific table only
python3 cleanup_capabilities_tables.py --table BusinessCapabilitySystem
```

**Features:**
- Batch deletion for efficiency
- Progress tracking
- Table statistics before deletion
- Selective table cleaning

### 🔍 inspect_capabilities_tables.py
Inspects and displays table contents for debugging and monitoring.

```bash
# Inspect all tables
python3 inspect_capabilities_tables.py

# Inspect specific table
python3 inspect_capabilities_tables.py --table BusinessCapabilitySystem

# Filter by capability ID
python3 inspect_capabilities_tables.py --capability CAP-001

# Limit results
python3 inspect_capabilities_tables.py --limit 10

# Export to JSON
python3 inspect_capabilities_tables.py --export output.json
```

**Features:**
- Table statistics (size, item count)
- Grouped display by item type
- Export functionality
- Filtering options

### 🎯 init_sample_capabilities.py
Creates sample data for testing and development.

```bash
# Create full sample dataset
python3 init_sample_capabilities.py

# Clean existing data first
python3 init_sample_capabilities.py --clean

# Create minimal test data
python3 init_sample_capabilities.py --minimal
```

**Sample Data Created:**
- 5 Business Capabilities (2 in minimal mode)
- 6-9 Components across capabilities
- 3-9 Implementation Jobs
- 7 days of Performance Metrics

## Business Logic Scripts

### 📦 manage_capability.py
Core capability management operations.

```bash
# Run directly for interactive mode
python3 manage_capability.py
```

**Features:**
- CRUD operations for capabilities
- Interactive wizard for creation
- Validation and business rules
- Health score calculation

### 🔧 manage_components.py
Component lifecycle management.

```bash
# Run directly for interactive mode
python3 manage_components.py
```

**Features:**
- Component CRUD operations
- Dependency management
- Version tracking
- Interactive component wizard

### 🚀 manage_implementation_jobs.py
Job tracking and execution management.

```bash
# Run directly for interactive mode
python3 manage_implementation_jobs.py
```

**Features:**
- Job creation and tracking
- Status transitions
- Rollback support
- Job timeline tracking

### 📊 manage_performance_metrics.py
Performance metrics collection and analysis.

```bash
# Run directly for interactive mode
python3 manage_performance_metrics.py
```

**Features:**
- Metric recording
- Aggregation functions
- Alert creation
- Health status monitoring

### 🔧 db_utils.py
Shared database utilities and helper functions.

**Features:**
- DynamoDB client initialization
- Decimal handling for metrics
- Batch write operations
- Mock authentication for testing

## Typical Workflow

### Initial Setup
```bash
# 1. Create tables
python3 setup_dynamodb_capabilities.py

# 2. Initialize sample data
python3 init_sample_capabilities.py

# 3. Verify setup
python3 inspect_capabilities_tables.py
```

### Development Testing
```bash
# 1. Clean existing data
python3 cleanup_capabilities_tables.py --yes

# 2. Create minimal test data
python3 init_sample_capabilities.py --minimal

# 3. Test your operations
python3 manage_capability.py
```

### Production Operations
```bash
# 1. Inspect current state
python3 inspect_capabilities_tables.py --export backup.json

# 2. Run capability manager CLI
../actors/capability/capability-manager.py

# 3. Monitor metrics
python3 inspect_capabilities_tables.py --table PerformanceMetrics
```

## Environment Variables

- `AWS_ROLE_ARN`: Optional role ARN for cross-account access
- `ENVIRONMENT`: Environment tag (development/staging/production)
- `AWS_REGION`: AWS region (defaults to configured region)

## Data Model

### Capability Item Structure
```json
{
  "PK": "CAPABILITY#CAP-ABC123",
  "SK": "METADATA",
  "capabilityId": "CAP-ABC123",
  "name": "Customer Management",
  "businessDomain": "customer",
  "status": "active",
  "priority": "high",
  "owner": "John Doe",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:00:00Z"
}
```

### Component Item Structure
```json
{
  "PK": "CAPABILITY#CAP-ABC123",
  "SK": "COMPONENT#COMP-XYZ789",
  "capabilityId": "CAP-ABC123",
  "componentId": "COMP-XYZ789",
  "name": "API Gateway",
  "type": "api-server",
  "version": "2.1.0",
  "status": "active"
}
```

## Error Handling

All scripts include comprehensive error handling:
- AWS authentication errors
- Table not found errors
- Data validation errors
- Network/timeout issues

## Security Notes

1. **Destructive Operations**: The cleanup script permanently deletes data
2. **IAM Permissions**: Requires DynamoDB read/write permissions
3. **Data Sensitivity**: Be cautious with export operations
4. **TTL Configuration**: Metrics auto-expire after 90 days

## Integration with Capability Manager CLI

These scripts are designed to work with the comprehensive Capability Manager CLI located at:
```
../actors/capability/capability-manager.py
```

The CLI provides a user-friendly interface for all operations defined in these scripts.

## Troubleshooting

### Tables Not Found
```bash
# Verify tables exist
aws dynamodb list-tables | grep -E "(BusinessCapability|Component|Job|Metric)"

# Create missing tables
python3 setup_dynamodb_capabilities.py
```

### Permission Errors
```bash
# Check IAM permissions
aws dynamodb describe-table --table-name BusinessCapabilitySystem

# Use role assumption if needed
export AWS_ROLE_ARN=arn:aws:iam::...
```

### Data Inconsistency
```bash
# Export current state
python3 inspect_capabilities_tables.py --export current_state.json

# Clean and reinitialize
python3 cleanup_capabilities_tables.py --yes
python3 init_sample_capabilities.py
```

## Support
For issues or questions, contact the TMF ODA team.
