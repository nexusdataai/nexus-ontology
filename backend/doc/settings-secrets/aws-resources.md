# AWS Resources

Reference for DynamoDB tables and S3 buckets used by the Nexus Telco Backend.

---

## DynamoDB Tables

### Table Definitions

| Table Pattern | Purpose | Key Schema |
|---------------|---------|------------|
| `call-processing-{env}-transformation-system` | Journey/Stage/Job state | PK (HASH), SK (RANGE), GSI1 |
| `call-processing-{env}-license` | License records and audit | PK (HASH), SK (RANGE), GSIs |
| `call-processing-{env}-wxcc-task-tracking` | WXCC task deduplication | task_id (HASH) |
| `call-processing-{env}-wxcc-simulator` | Simulator mock data | org_id (HASH), SK (RANGE) |

### Schema Details

#### call-processing-{env}-transformation-system

```
Primary Key:
├── PK (HASH): "JOURNEY#<id>" | "JOB#<id>" | "STAGE#<id>"
├── SK (RANGE): "METADATA" | "STATUS" | "STAGE#<n>"
│
Global Secondary Index (GSI1):
├── GSI1PK: For alternate access patterns
└── GSI1SK: For sorting

Example Items:
┌─────────────────────────────────────────────────────────┐
│ Journey Metadata                                        │
│ PK: "JOURNEY#JRN-001"                                   │
│ SK: "METADATA"                                          │
│ name: "Call Processing Pipeline"                        │
│ status: "active"                                        │
├─────────────────────────────────────────────────────────┤
│ Job Status                                              │
│ PK: "JOB#JOB-001"                                       │
│ SK: "STATUS"                                            │
│ journey_id: "JRN-001"                                   │
│ status: "completed"                                     │
│ progress: 100                                           │
└─────────────────────────────────────────────────────────┘
```

#### call-processing-{env}-license

```
License Records:
├── PK (HASH): "INSTANCE#<instance_id>"
├── SK (RANGE): "LICENSE#<license_id>"
│
Audit Logs:
├── PK (HASH): "AUDIT#<YYYY-MM>"
├── SK (RANGE): "<timestamp>#<event_id>"
│
GSIs:
├── status-index: Query by license status
├── holder-index: Query by license holder
└── license-index: Query by license ID

Example Items:
┌─────────────────────────────────────────────────────────┐
│ License Record                                          │
│ PK: "INSTANCE#inst-001"                                 │
│ SK: "LICENSE#lic-001"                                   │
│ status: "active"                                        │
│ expires_at: "2026-12-31T23:59:59Z"                      │
├─────────────────────────────────────────────────────────┤
│ Audit Log                                               │
│ PK: "AUDIT#2026-01"                                     │
│ SK: "2026-01-27T10:30:00Z#evt-001"                      │
│ action: "license_validated"                             │
│ instance_id: "inst-001"                                 │
└─────────────────────────────────────────────────────────┘
```

#### call-processing-{env}-wxcc-task-tracking

```
Primary Key:
├── task_id (HASH): WXCC task identifier
│
Attributes:
├── processed_at: Timestamp when processed
├── status: Processing status
└── ttl: TTL for automatic cleanup

Used for:
• Task deduplication during call processing
• Tracking which tasks have been processed
• Preventing duplicate processing
```

---

## S3 Buckets

### Bucket Structure

| Bucket Pattern | Purpose | Structure |
|----------------|---------|-----------|
| `call-processing-{env}-call-data` | Call recordings, transcripts, Glue data | See below |
| `call-processing-{env}-wxcc-simulator` | WXCC simulator data | `wxcc-simulator/tasks/`, `recordings/` |
| `call-processing-{env}-journey-logs` | Job execution logs | `{journey_id}/{job_id}/{step_id}/` |
| `call-processing-{env}-journey-reports` | Job reports and artifacts | `{journey_id}/{job_id}/` |

### call-processing-{env}-call-data Structure

```
call-processing-{env}-call-data/
│
├── call-data/                        # Glue table data (partitioned Parquet/JSON)
│   └── year=YYYY/month=MM/day=DD/hour=HH/
│       └── {task_id}.json
│
├── call-detail/                      # Per-call artifacts
│   └── {task_id}/
│       ├── recording.wav             # Original audio recording
│       ├── transcript.json           # Transcription results
│       ├── analysis.json             # AI analysis results
│       └── sfdc_action.json          # Salesforce action results
│
├── recordings/                       # Raw recordings (legacy path)
│   └── {task_id}/
│       └── recording.wav
│
├── transcripts/                      # Transcription results (legacy path)
│   └── {task_id}/
│       └── transcript.json
│
├── SFDC/                             # CRM deduplication markers
│   └── {task_id}.txt                 # Marker file indicating SFDC processed
│
└── athena-results/                   # Athena query results
    └── *.csv
```

### call-processing-{env}-wxcc-simulator Structure

```
call-processing-{env}-wxcc-simulator/
│
└── wxcc-simulator/
    ├── tasks/                        # Simulated WXCC task metadata
    │   └── {org_id}/
    │       └── {task_id}.json
    │
    ├── recordings/                   # Task recordings
    │   └── {org_id}/
    │       └── {task_id}/
    │           └── recording.wav
    │
    └── sample-recordings/            # Sample recordings for seeding
        └── *.wav
```

### call-processing-{env}-journey-logs Structure

```
call-processing-{env}-journey-logs/
│
└── {journey_id}/
    └── {job_id}/
        ├── job_log.json              # Overall job log
        └── {step_id}/
            └── step_log.json         # Per-step detailed log
```

### call-processing-{env}-journey-reports Structure

```
call-processing-{env}-journey-reports/
│
└── {journey_id}/
    └── {job_id}/
        ├── report.json               # Job execution report
        ├── summary.json              # Job summary statistics
        └── artifacts/
            └── *.json                # Additional artifacts
```

---

## Create Resources (AWS CLI)

### DynamoDB Tables

```bash
ENV=prod

# Transformation System Table
aws dynamodb create-table \
  --table-name "call-processing-${ENV}-transformation-system" \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
    AttributeName=GSI1PK,AttributeType=S \
    AttributeName=GSI1SK,AttributeType=S \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --global-secondary-indexes \
    "IndexName=GSI1,KeySchema=[{AttributeName=GSI1PK,KeyType=HASH},{AttributeName=GSI1SK,KeyType=RANGE}],Projection={ProjectionType=ALL}" \
  --billing-mode PAY_PER_REQUEST

# License Table
aws dynamodb create-table \
  --table-name "call-processing-${ENV}-license" \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# WXCC Task Tracking Table
aws dynamodb create-table \
  --table-name "call-processing-${ENV}-wxcc-task-tracking" \
  --attribute-definitions \
    AttributeName=task_id,AttributeType=S \
  --key-schema \
    AttributeName=task_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### S3 Buckets

```bash
ENV=prod
REGION=ap-southeast-1

# Call Data Bucket
aws s3api create-bucket \
  --bucket "call-processing-${ENV}-call-data" \
  --region ${REGION} \
  --create-bucket-configuration LocationConstraint=${REGION}

# WXCC Simulator Bucket
aws s3api create-bucket \
  --bucket "call-processing-${ENV}-wxcc-simulator" \
  --region ${REGION} \
  --create-bucket-configuration LocationConstraint=${REGION}

# Journey Logs Bucket
aws s3api create-bucket \
  --bucket "call-processing-${ENV}-journey-logs" \
  --region ${REGION} \
  --create-bucket-configuration LocationConstraint=${REGION}

# Journey Reports Bucket
aws s3api create-bucket \
  --bucket "call-processing-${ENV}-journey-reports" \
  --region ${REGION} \
  --create-bucket-configuration LocationConstraint=${REGION}
```

---

*Related: [Naming Conventions](naming-conventions.md) | [IAM Permissions](iam-permissions.md)*
