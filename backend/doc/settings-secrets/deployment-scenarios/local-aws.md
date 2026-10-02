# Local Development with Real AWS

For development against real AWS resources (not LocalStack).

---

## Configuration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     LOCAL + REAL AWS CONFIGURATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Configuration Flow:                                                        │
│  ┌─────────────────┐                                                        │
│  │   .env.local    │ ──► Environment Variables ──► ConfigProvider           │
│  └─────────────────┘                                                        │
│            │                                                                │
│            │  (Config values like bucket names, table names)                │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AWS Services (Real)                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │   DynamoDB   │  │      S3      │  │    Glue      │               │   │
│  │  │  (dev env)   │  │  (dev env)   │  │  (dev env)   │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AWS Credentials:                                                           │
│  • Loaded from ~/.aws/credentials (via aws-login.sh)                        │
│  • Profile: external-access (or configured profile)                         │
│  • No AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY in env                        │
│                                                                             │
│  Environment Detection Result:                                              │
│  • environment = 'dev' (from .env.local)                                    │
│  • is_aws_environment() = False (not ECS)                                   │
│  • Config loaded from: .env.local only                                      │
│  • SSM/Secrets NOT used (even though connecting to real AWS)                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Required `.env.local` Settings

```bash
# Disable LocalStack (use real AWS)
USE_LOCALSTACK=false
ENVIRONMENT=dev

# AWS credentials from CLI (not env vars)
AWS_PROFILE=external-access
AWS_REGION=ap-southeast-1

# Resource names (must match real AWS resources)
DYNAMODB_TABLE=call-processing-dev-transformation-system
LICENSE_TABLE=call-processing-dev-license
S3_RECORDINGS_BUCKET=call-processing-dev-call-data
WXCC_SIMULATOR_BUCKET=call-processing-dev-wxcc-simulator
S3_JOURNEY_LOGS_BUCKET=call-processing-dev-journey-logs
S3_JOURNEY_REPORTS_BUCKET=call-processing-dev-journey-reports

# API keys (from .env.local, not Secrets Manager for local dev)
OPENAI_API_KEY=sk-proj-xxx
API_KEY=super-secret
```

---

## Getting AWS Credentials

### Option 1: ADFS Login Script

```bash
# Use the ADFS login script
./aws-login.sh

# This will:
# 1. Authenticate via ADFS
# 2. Store credentials in ~/.aws/credentials
# 3. Set up the profile for use
```

### Option 2: AWS CLI Configure

```bash
# Manually configure AWS CLI
aws configure --profile external-access

# Enter when prompted:
# AWS Access Key ID: <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region name: ap-southeast-1
# Default output format: json
```

---

## Key Differences from LocalStack

| Aspect | LocalStack | Real AWS |
|--------|------------|----------|
| `USE_LOCALSTACK` | `true` | `false` |
| Credentials | `test/test` (auto) | `~/.aws/credentials` |
| Endpoint | `localhost:4566` | AWS regional endpoints |
| Cost | Free | AWS pricing |
| Data | Ephemeral | Persistent |
| Config Source | `.env.local` | `.env.local` |

---

## Important Notes

1. **Configuration still from `.env.local`**: Even when connecting to real AWS, configuration values (bucket names, table names) come from `.env.local`, NOT from SSM Parameter Store.

2. **SSM/Secrets Manager not used**: The `is_aws_environment()` function returns `False` for local development, so SSM and Secrets Manager are not queried.

3. **AWS credentials for data access only**: The AWS credentials are used to access S3, DynamoDB, and other data services, but NOT for configuration loading.

---

## Verifying AWS Connection

```bash
# Check AWS identity
aws sts get-caller-identity --profile external-access

# List DynamoDB tables
aws dynamodb list-tables --region ap-southeast-1

# List S3 buckets
aws s3 ls
```

---

*Related: [LocalStack](localstack.md) | [ECS Fargate](ecs-fargate.md)*
