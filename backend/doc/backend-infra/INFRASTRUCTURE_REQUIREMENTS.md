# Backend Infrastructure Requirements

Infrastructure and configuration reference for the **call-processing** capability (nexus-backend).

## Table of Contents

- [Deployment Modes](#deployment-modes)
- [Credential Handling](#credential-handling)
- [AWS Resources](#aws-resources)
- [Environment Variables](#environment-variables)
- [SSM Parameters](#ssm-parameters)
- [Secrets Manager](#secrets-manager)
- [IAM Permissions](#iam-permissions)
- [Production Quick Reference](#production-quick-reference)

---

## Deployment Modes

The backend supports four deployment modes, auto-detected at startup:

| Mode | Detection | Config Source | Credentials |
|------|-----------|---------------|-------------|
| **EKS (IRSA)** | `AWS_WEB_IDENTITY_TOKEN_FILE` present | SSM + Secrets Manager | Web identity token (auto-refresh) |
| **ECS Fargate** | `ECS_CONTAINER_METADATA_URI` present | SSM + Secrets Manager | Task role (auto-refresh) |
| **Local + AWS** | No ECS/IRSA, `USE_LOCALSTACK=false` | `.env.local` + env vars | `~/.aws/credentials` or profile |
| **Local + LocalStack** | `USE_LOCALSTACK=true` | `.env.local` + env vars | Dummy (`test`/`test`) |

### EKS with IRSA

The recommended production mode. The Totogi Operator handles all setup automatically.

**How it works:**
- Pod has a ServiceAccount annotated with `eks.amazonaws.com/role-arn`
- AWS SDK detects the web identity token file and assumes the role automatically
- No manual credential management needed
- The `_is_running_under_irsa()` method in `aws_client_utils.py` detects this mode and skips manual role assumption

**Environment variables set by the operator:**
```
ENVIRONMENT=prod
AWS_REGION=ap-southeast-1
CAPABILITY_NAME=call-processing
SSM_PARAMETER_PREFIX=/call-processing/prod/
SECRETS_PREFIX=call-processing/prod/
```

**Automatically injected by EKS:**
```
AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
AWS_ROLE_ARN=arn:aws:iam::ACCOUNT:role/call-processing-prod-app-role
```

### ECS Fargate

**How it works:**
- ECS task definition has an IAM task role
- AWS SDK detects ECS metadata endpoint and uses task role credentials
- Configuration loaded from SSM Parameter Store and Secrets Manager

**Minimum task definition env vars:**
```
ENVIRONMENT=prod
AWS_REGION=ap-southeast-1
```

### Local Development with Real AWS

**How it works:**
- Load `.env.local` from project root
- Credentials from `~/.aws/credentials` (set via `aws-login.sh` or `aws configure`)
- All resource names configured in `.env.local`

**Start the gateway:**
```bash
./start_gateway.sh
```

**Or manually:**
```bash
source .env.local
python mcp_http_gateway.py --host 0.0.0.0 --port 8000
```

### Local Development with LocalStack

**How it works:**
- Set `USE_LOCALSTACK=true` in `.env.local`
- LocalStack emulates DynamoDB, S3, SSM, Secrets Manager, Glue, CloudWatch
- Dummy credentials used (`test`/`test`)
- All AWS clients configured with `http://localhost:4566` endpoint

**Start LocalStack + gateway:**
```bash
# Start LocalStack container
docker compose -f docker-compose-localstack.yml up -d

# Initialize resources (tables, buckets)
./localstack/localstack-init.sh

# Start gateway
./start_gateway.sh
```

**Or all-in-one:**
```bash
./localstack/start-gateway-localstack.sh
```

---

## Credential Handling

The `aws_client_utils.py` `_create_session()` method follows this priority:

```
1. LocalStack mode  (USE_LOCALSTACK=true)
   -> Dummy credentials, LocalStack endpoints

2. IRSA mode  (AWS_WEB_IDENTITY_TOKEN_FILE exists)
   -> Default boto3 session (SDK handles web identity)

3. Role assumption  (AWS_ROLE_ARN set, not IRSA)
   -> RefreshableCredentials, auto-refresh 5 min before expiry

4. Instance role  (ECS task role)
   -> Default boto3 session (SDK handles instance metadata)

5. Default chain
   -> AWS_PROFILE or ~/.aws/credentials
```

---

## AWS Resources

### Naming Convention

All resources use `call-processing-{env}-{name}`:

### DynamoDB Tables

| Table | Key Schema | Purpose |
|-------|-----------|---------|
| `call-processing-{env}-transformation-system` | PK (HASH) + SK (RANGE), GSI1 | Journey/Stage/Job state management |
| `call-processing-{env}-license` | PK (HASH) + SK (RANGE), 3 GSIs | License records and audit logs |
| `call-processing-{env}-wxcc-task-tracking` | task_id (HASH) | WXCC task tracking |

### S3 Buckets

| Bucket | Purpose | Structure |
|--------|---------|-----------|
| `call-processing-{env}-call-data` | Call data, Glue tables, recordings, transcripts | `call-data/year=YYYY/...`, `recordings/`, `transcripts/`, `athena-results/` |
| `call-processing-{env}-wxcc-simulator` | WXCC simulator data | `wxcc-simulator/tasks/`, `recordings/` |
| `call-processing-{env}-journey-logs` | Journey execution logs | Per-journey directories |
| `call-processing-{env}-journey-reports` | Journey reports and artifacts | Per-journey directories |

### Glue / Athena

| Resource | Name Pattern |
|----------|-------------|
| Database | `call-processing-{env}-analytics` |
| Table | `wxcc_calls` (partitioned by year/month/day/hour) |
| Athena results | Stored in `call-data` bucket under `athena-results/` |

### CloudWatch

| Resource | Pattern |
|----------|---------|
| Log group | `/aws/call-processing/{env}` |
| Log stream prefix | `script` |

---

## Environment Variables

### Core Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Deployment environment | `development` | Yes |
| `AWS_REGION` | AWS region | `ap-southeast-1` | Yes |
| `CAPABILITY_NAME` | Capability name | `call-processing` | Yes |
| `LOG_LEVEL` | Logging verbosity | `INFO` | No |
| `API_KEY` | Gateway API key | `super-secret` | Yes |
| `GATEWAY_PORT` | HTTP port | `8000` | No |
| `MIN_WORKERS` | Min worker pool size | `2` | No |
| `MAX_WORKERS` | Max worker pool size | `8` | No |
| `MCP_REQUEST_TIMEOUT` | Request timeout (seconds) | `300.0` | No |

### DynamoDB

| Variable | Default Pattern |
|----------|----------------|
| `DYNAMODB_TABLE` | `call-processing-{env}-transformation-system` |
| `LICENSE_TABLE` | `call-processing-{env}-license` |
| `DYNAMODB_TRACKING_TABLE` | `call-processing-{env}-wxcc-task-tracking` |

### S3

| Variable | Default Pattern |
|----------|----------------|
| `S3_RECORDINGS_BUCKET` | `call-processing-{env}-call-data` |
| `WXCC_SIMULATOR_BUCKET` | `call-processing-{env}-wxcc-simulator` |
| `S3_JOURNEY_LOGS_BUCKET` | `call-processing-{env}-journey-logs` |
| `S3_JOURNEY_REPORTS_BUCKET` | `call-processing-{env}-journey-reports` |

### Glue

| Variable | Default Pattern |
|----------|----------------|
| `GLUE_DATABASE_NAME` | `call-processing-{env}-analytics` |
| `GLUE_TABLE_NAME` | `wxcc_calls` |

### WXCC Simulator

| Variable | Default |
|----------|---------|
| `WXCC_SIMULATOR_ENABLED` | `true` |
| `WXCC_SIMULATOR_PREFIX` | `wxcc-simulator` |
| `WXCC_SIMULATOR_BASE_URL` | `http://localhost:8000/api/v1/simulator` |
| `WXCC_SIM_ORG_ID` | `sim-org-001` |
| `WXCC_SIM_TOKEN` | (in Secrets Manager) |

### Cognito (Optional)

| Variable | Description |
|----------|-------------|
| `COGNITO_REGION` | Cognito region |
| `COGNITO_USER_POOL_ID` | User Pool ID |
| `COGNITO_APP_CLIENT_ID` | App Client ID |

### LocalStack (Local Only)

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_LOCALSTACK` | `false` | Enable LocalStack mode |
| `LOCALSTACK_HOST` | `localhost` | LocalStack hostname |
| `LOCALSTACK_PORT` | `4566` | LocalStack port |

### AWS Credential Variables (Rarely Needed)

| Variable | When Needed |
|----------|-------------|
| `AWS_PROFILE` | Local dev with named profile |
| `AWS_ROLE_ARN` | Cross-account role assumption |
| `AWS_ACCESS_KEY_ID` | CI/CD pipelines only (never in ECS/EKS) |

---

## SSM Parameters

Parameter path: `/{capability}/{env}/{category}/{key}`

### Created by the Totogi Operator

| Path | Env Variable |
|------|-------------|
| `/{cap}/{env}/aws/region` | `AWS_REGION` |
| `/{cap}/{env}/server/environment` | `ENVIRONMENT` |
| `/{cap}/{env}/server/log-level` | `LOG_LEVEL` |
| `/{cap}/{env}/dynamodb/transformation-table` | `DYNAMODB_TABLE` |
| `/{cap}/{env}/dynamodb/license-table` | `LICENSE_TABLE` |
| `/{cap}/{env}/dynamodb/wxcc-task-table` | `DYNAMODB_TRACKING_TABLE` |
| `/{cap}/{env}/s3/recordings-bucket` | `S3_RECORDINGS_BUCKET` |
| `/{cap}/{env}/s3/journey-logs-bucket` | `S3_JOURNEY_LOGS_BUCKET` |
| `/{cap}/{env}/s3/journey-reports-bucket` | `S3_JOURNEY_REPORTS_BUCKET` |
| `/{cap}/{env}/glue/database` | `GLUE_DATABASE_NAME` |
| `/{cap}/{env}/glue/table` | `GLUE_TABLE_NAME` |
| `/{cap}/{env}/cloudwatch/log-group` | `CLOUDWATCH_LOG_GROUP` |

### Cognito Parameters (when `enableCognito: true`)

| Path | Env Variable |
|------|-------------|
| `/{cap}/{env}/cognito/region` | `COGNITO_REGION` |
| `/{cap}/{env}/cognito/user-pool-id` | `COGNITO_USER_POOL_ID` |
| `/{cap}/{env}/cognito/client-id` | `COGNITO_APP_CLIENT_ID` |
| `/{cap}/{env}/cognito/domain` | `COGNITO_DOMAIN` |
| `/{cap}/{env}/cognito/redirect-uri` | `COGNITO_REDIRECT_URI` |

**Config loading priority:** SSM Parameter Store > Environment variables > Defaults

---

## Secrets Manager

Secret path: `{capability}/{env}/{type}`

| Secret | Contents |
|--------|----------|
| `call-processing/{env}/api-keys` | `API_KEY` |
| `call-processing/{env}/wxcc` | `WXCC_SIM_TOKEN` |
| `call-processing/{env}/openai` | `OPENAI_API_KEY` |
| `call-processing/{env}/license` | `LICENSE_PUBLIC_KEY`, `LICENSE_PRIVATE_KEY` |
| `call-processing/{env}/anthropic` | `CLAUDE_API_KEY`, `ANTHROPIC_API_KEY` |
| `call-processing/{env}/github` | `GITHUB_TOKEN` |

---

## IAM Permissions

### Application Role (EKS/ECS)

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan",
                 "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:BatchGetItem",
                 "dynamodb:BatchWriteItem", "dynamodb:DescribeTable"],
      "Resource": ["arn:aws:dynamodb:REGION:ACCOUNT:table/call-processing-*",
                    "arn:aws:dynamodb:REGION:ACCOUNT:table/call-processing-*/index/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject",
                 "s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::call-processing-*", "arn:aws:s3:::call-processing-*/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
      "Resource": "arn:aws:ssm:REGION:ACCOUNT:parameter/call-processing/*"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
      "Resource": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:call-processing/*"
    },
    {
      "Effect": "Allow",
      "Action": ["glue:GetDatabase", "glue:GetTable", "glue:GetPartitions",
                 "athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream",
                 "logs:PutLogEvents", "logs:DescribeLogStreams"],
      "Resource": "arn:aws:logs:REGION:ACCOUNT:log-group:/aws/call-processing/*"
    }
  ]
}
```

---

## Production Quick Reference

### Minimum Required for EKS Deployment

The Totogi Operator provisions all of these automatically. For manual setup:

**DynamoDB tables:**
- `call-processing-prod-transformation-system`
- `call-processing-prod-license`
- `call-processing-prod-wxcc-task-tracking`

**S3 buckets:**
- `call-processing-prod-call-data`
- `call-processing-prod-wxcc-simulator`
- `call-processing-prod-journey-logs`
- `call-processing-prod-journey-reports`

**Secrets Manager:**
- `call-processing/prod/api-keys`
- `call-processing/prod/openai`
- `call-processing/prod/license`

**SSM parameters:** 12+ parameters under `/call-processing/prod/`

**IAM role:** `call-processing-prod-app-role` with IRSA trust policy

### Build and Deploy

```bash
# Build and push to ECR
cd /opt/mycode/trilogy/nexus-backend
SKIP_TESTS=true SKIP_SCAN=true ./build.sh

# Deploy via operator (EKS)
cd /opt/mycode/trilogy/nexus-deployer/kube-operator
kubectl apply -f examples/call-processing-complete.yaml

# Verify
./operator-nexus-test.sh verify-capability
```
