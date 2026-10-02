# ECS Fargate Deployment

Production deployment on AWS ECS Fargate with configuration from SSM Parameter Store and Secrets Manager.

---

## Configuration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ECS FARGATE CONFIGURATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Configuration Flow:                                                        │
│  ┌─────────────────┐     ┌─────────────────┐                                │
│  │ SSM Parameter   │ ──► │                 │                                │
│  │ Store           │     │  ConfigProvider │ ──► Application                │
│  ├─────────────────┤ ──► │                 │                                │
│  │ Secrets Manager │     │                 │                                │
│  └─────────────────┘     └─────────────────┘                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      ECS Task Definition                             │   │
│  │                                                                     │   │
│  │  Environment Variables (injected by ECS):                           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ ENVIRONMENT=prod                                            │   │   │
│  │  │ AWS_REGION=ap-southeast-1                                   │   │   │
│  │  │ ECS_CONTAINER_METADATA_URI=http://169.254.170.2/v3/xxx     │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  Credentials: IAM Task Role (no keys needed)                        │   │
│  │  • Role: call-processing-prod-task-role                             │   │
│  │  • Permissions: SSM, Secrets Manager, DynamoDB, S3, etc.            │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Environment Detection Result:                                              │
│  • environment = 'prod' (from ECS task definition)                          │
│  • is_aws_environment() = True (ECS metadata present)                       │
│  • Config loaded from: SSM + Secrets Manager                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ECS Task Definition (Key Settings)

```json
{
  "containerDefinitions": [
    {
      "name": "call-processing-backend",
      "image": "xxx.dkr.ecr.ap-southeast-1.amazonaws.com/call-processing:latest",
      "environment": [
        { "name": "ENVIRONMENT", "value": "prod" },
        { "name": "AWS_REGION", "value": "ap-southeast-1" }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:ap-southeast-1:xxx:secret:call-processing/prod/openai"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/aws/call-processing/prod",
          "awslogs-region": "ap-southeast-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "taskRoleArn": "arn:aws:iam::xxx:role/call-processing-prod-task-role",
  "executionRoleArn": "arn:aws:iam::xxx:role/call-processing-prod-execution-role"
}
```

---

## Configuration Loading on ECS

```python
# When application starts on ECS:
def _load_from_aws(self):
    """Load configuration from SSM Parameter Store and Secrets Manager."""
    
    # Load all SSM parameters under /call-processing/prod/
    ssm_loader = SSMParameterLoader(region=self.aws_region)
    ssm_path = f"/{CAPABILITY_NAME}/{self.environment}/"
    self._ssm_params = ssm_loader.load_parameters_by_path(ssm_path)
    # Result: {'aws/region': 'ap-southeast-1', 'server/log-level': 'INFO', ...}
    
    # Load secrets
    secrets_loader = SecretsLoader(region=self.aws_region)
    for secret_name in ['api-keys', 'openai', 'license', 'wxcc']:
        secret = secrets_loader.get_secret(f"call-processing/prod/{secret_name}")
        self._secrets[secret_name] = secret
```

---

## Required IAM Roles

### Task Role (`call-processing-prod-task-role`)

Used by the application at runtime to access AWS services:

- SSM Parameter Store (read/write)
- Secrets Manager (read)
- DynamoDB (CRUD)
- S3 (CRUD)
- CloudWatch Logs (write)
- Glue/Athena (query)

### Execution Role (`call-processing-prod-execution-role`)

Used by ECS to start the task:

- ECR (pull images)
- CloudWatch Logs (create log streams)
- Secrets Manager (inject secrets into container)

---

## Environment Detection

On ECS, the `ECS_CONTAINER_METADATA_URI` environment variable is automatically set by AWS. This triggers:

1. `is_aws_environment()` returns `True`
2. Configuration loads from SSM Parameter Store
3. Secrets load from Secrets Manager

```python
def is_aws_environment() -> bool:
    """Check if running in AWS environment that should use SSM/Secrets."""
    if os.getenv('ECS_CONTAINER_METADATA_URI') or \
       os.getenv('ECS_CONTAINER_METADATA_URI_V4'):
        return True
    return False
```

---

## Minimum Required SSM Parameters (Production)

```bash
ENV=prod

# Server
/call-processing/${ENV}/server/environment=production
/call-processing/${ENV}/server/log-level=INFO

# S3 Buckets
/call-processing/${ENV}/s3/recordings-bucket=call-processing-${ENV}-call-data
/call-processing/${ENV}/s3/journey-logs-bucket=call-processing-${ENV}-journey-logs

# DynamoDB Tables
/call-processing/${ENV}/dynamodb/transformation-table=call-processing-${ENV}-transformation-system
/call-processing/${ENV}/dynamodb/license-table=call-processing-${ENV}-license

# Cognito
/call-processing/${ENV}/cognito/user-pool-id=<user-pool-id>
/call-processing/${ENV}/cognito/app-client-id=<app-client-id>
```

---

## Minimum Required Secrets (Production)

```bash
# API authentication key
call-processing/prod/api-keys     → {"API_KEY": "your-secure-key"}

# OpenAI API key
call-processing/prod/openai       → {"OPENAI_API_KEY": "sk-proj-xxx"}

# License verification keys
call-processing/prod/license      → {"LICENSE_PUBLIC_KEY": "...", "LICENSE_PRIVATE_KEY": "..."}
```

---

*Related: [EKS Kubernetes](eks-kubernetes.md) | [SSM Parameters Reference](../ssm-parameters.md) | [IAM Permissions](../iam-permissions.md)*
