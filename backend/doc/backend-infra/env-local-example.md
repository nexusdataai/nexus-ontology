# Local Development Configuration

Copy the configuration below to `.env.local` in the project root.

## For Real AWS

```bash
# =============================================================================
# Nexus Backend - Local Development with Real AWS
# =============================================================================
# On ECS/EKS, configuration is loaded from SSM Parameter Store and Secrets Manager.
# Locally, all config comes from this file.
#
# Naming Convention: call-processing-{env}-{resource-name}

# --- Mode ---
USE_LOCALSTACK=false

# --- AWS Credentials ---
AWS_PROFILE=external-access
AWS_REGION=ap-southeast-1
AWS_DEFAULT_REGION=ap-southeast-1
# AWS_ROLE_ARN=arn:aws:iam::764119721991:role/RAM-AWS-Prod-TelcoDR-TotogiPS-Admin

# --- Environment ---
ENVIRONMENT=dev
CAPABILITY_NAME=call-processing

# --- DynamoDB Tables ---
DYNAMODB_TABLE=call-processing-dev-transformation-system
LICENSE_TABLE=call-processing-dev-license
DYNAMODB_TRACKING_TABLE=call-processing-dev-wxcc-task-tracking

# --- S3 Buckets ---
S3_RECORDINGS_BUCKET=call-processing-dev-call-data
S3_JOURNEY_LOGS_BUCKET=call-processing-dev-journey-logs
S3_JOURNEY_REPORTS_BUCKET=call-processing-dev-journey-reports
WXCC_SIMULATOR_BUCKET=call-processing-dev-wxcc-simulator

# --- Glue ---
GLUE_DATABASE_NAME=call-processing-dev-wxcc-analytics
GLUE_TABLE_NAME=calls

# --- WXCC Simulator ---
WXCC_SIMULATOR_ENABLED=true
WXCC_SIMULATOR_PREFIX=wxcc-simulator
WXCC_SIMULATOR_BASE_URL=http://localhost:8000/api/v1/simulator
WXCC_SIM_TOKEN=test-token-12345
WXCC_SIM_ORG_ID=sim-org-001

# --- Gateway ---
LOG_LEVEL=INFO
API_KEY=super-secret
GATEWAY_PORT=8000
MIN_WORKERS=2
MAX_WORKERS=8
MCP_REQUEST_TIMEOUT=300.0

# --- OpenAI ---
OPENAI_API_KEY=sk-proj-your-openai-api-key

# --- Cognito (optional) ---
# COGNITO_REGION=ap-southeast-1
# COGNITO_USER_POOL_ID=
# COGNITO_APP_CLIENT_ID=

# --- ADFS Login (for aws-login.sh) ---
ADFS_HOST=adfs.devfactory.com/adfs/ls/idpinitiatedsignon
ADFS_PROVIDER_ID=urn:amazon:webservices
AD_USERNAME=devfactory\\your-username
AD_PASSWORD=your-password
```

## For LocalStack

```bash
# =============================================================================
# Nexus Backend - Local Development with LocalStack
# =============================================================================

# --- Mode ---
USE_LOCALSTACK=true
LOCALSTACK_HOST=localhost
LOCALSTACK_PORT=4566

# --- Environment ---
ENVIRONMENT=local
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test

# --- DynamoDB Tables (LocalStack uses simple names) ---
DYNAMODB_TABLE=TransformationSystem
LICENSE_TABLE=License
DYNAMODB_TRACKING_TABLE=WxccTaskTracking

# --- S3 Buckets ---
S3_RECORDINGS_BUCKET=nexus-dev-wxcc-recordings
WXCC_SIMULATOR_BUCKET=nexus-dev-wxcc-simulator
S3_JOURNEY_LOGS_BUCKET=nexus-dev-journey-logs
S3_JOURNEY_REPORTS_BUCKET=nexus-dev-journey-reports

# --- WXCC Simulator ---
WXCC_SIMULATOR_ENABLED=true
WXCC_SIMULATOR_PREFIX=wxcc-simulator
WXCC_SIMULATOR_BASE_URL=http://localhost:8000/api/v1/simulator

# --- Gateway ---
LOG_LEVEL=DEBUG
API_KEY=test-api-key
MIN_WORKERS=1
MAX_WORKERS=2
```

## Quick Start

### Real AWS
```bash
cp doc/backend-infra/env-local-example.md .env.local  # Then edit values
./start_gateway.sh
```

### LocalStack
```bash
# Copy LocalStack section to .env.local, then:
docker compose -f docker-compose-localstack.yml up -d
./localstack/localstack-init.sh
./start_gateway.sh
```

## Values to Update

After copying to `.env.local`, replace these placeholders:

| Variable | What to Set |
|----------|-------------|
| `AD_USERNAME` | Your DevFactory AD username |
| `AD_PASSWORD` | Your DevFactory AD password |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `AWS_ROLE_ARN` | Your IAM role ARN (if needed) |
