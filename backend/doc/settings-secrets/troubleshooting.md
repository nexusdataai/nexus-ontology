# Troubleshooting

Common issues and solutions for configuration and secrets management.

---

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Config not loading from SSM | Not running on ECS | SSM loading only on ECS (detected via metadata URI) |
| Secrets not found | Wrong secret name | Check naming: `call-processing/{env}/secret-name` |
| LocalStack connection failed | Docker not running | Start: `docker-compose -f docker-compose-localstack.yml up -d` |
| AWS credentials error | Missing credentials | Run `aws-login.sh` or configure AWS CLI |
| Wrong environment | ENVIRONMENT not set | Set in .env.local or ECS task definition |
| Stale configuration | Cache not expired | Wait 5 minutes or invalidate cache programmatically |

---

## Debug Configuration Loading

### Python Script

```python
from src.config.config_provider import get_config, is_aws_environment, detect_environment

# Check environment detection
print(f"Detected environment: {detect_environment()}")
print(f"Is AWS environment: {is_aws_environment()}")

# Get config and inspect
config = get_config()
print(f"Environment: {config.environment}")
print(f"Region: {config.aws_region}")
print(f"DynamoDB Table: {config.dynamodb_transformation_table}")
print(f"S3 Bucket: {config.s3_recordings_bucket}")
print(f"Log Level: {config.log_level}")

# Check if specific config is from SSM or env
print(f"SSM params loaded: {len(config._ssm_params)}")
print(f"Secrets loaded: {len(config._secrets)}")
```

### Expected Output (Local Development)

```
Detected environment: dev
Is AWS environment: False
Environment: dev
Region: ap-southeast-1
DynamoDB Table: call-processing-dev-transformation-system
S3 Bucket: call-processing-dev-call-data
Log Level: INFO
SSM params loaded: 0
Secrets loaded: 0
```

### Expected Output (ECS)

```
Detected environment: prod
Is AWS environment: True
Environment: prod
Region: ap-southeast-1
DynamoDB Table: call-processing-prod-transformation-system
S3 Bucket: call-processing-prod-call-data
Log Level: INFO
SSM params loaded: 25
Secrets loaded: 4
```

---

## Verify SSM Parameters (AWS CLI)

### List All Parameters

```bash
# List all parameters for an environment
aws ssm get-parameters-by-path \
  --path "/call-processing/prod/" \
  --recursive \
  --query "Parameters[].{Name:Name,Value:Value}" \
  --output table
```

### Get Specific Parameter

```bash
# Get single parameter
aws ssm get-parameter \
  --name "/call-processing/prod/server/log-level" \
  --query "Parameter.Value" \
  --output text
```

### Check Parameter Exists

```bash
# Check if parameter exists (returns exit code 0 if exists)
aws ssm get-parameter --name "/call-processing/prod/server/log-level" > /dev/null 2>&1 && echo "EXISTS" || echo "NOT FOUND"
```

---

## Verify Secrets (AWS CLI)

### List Secrets

```bash
# List all secrets for an environment
aws secretsmanager list-secrets \
  --filter Key=name,Values=call-processing/prod \
  --query "SecretList[].Name"
```

### Get Secret Value

```bash
# Get secret (JSON output)
aws secretsmanager get-secret-value \
  --secret-id "call-processing/prod/openai" \
  --query "SecretString" \
  --output text

# Parse JSON and get specific key
aws secretsmanager get-secret-value \
  --secret-id "call-processing/prod/openai" \
  --query "SecretString" --output text | jq -r '.OPENAI_API_KEY'
```

---

## LocalStack Troubleshooting

### Check LocalStack Health

```bash
curl http://localhost:4566/_localstack/health
```

Expected output:
```json
{
  "services": {
    "dynamodb": "running",
    "s3": "running",
    "ssm": "running",
    "secretsmanager": "running"
  }
}
```

### List LocalStack Resources

```bash
# DynamoDB tables
aws --endpoint-url=http://localhost:4566 dynamodb list-tables

# S3 buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# SSM parameters
aws --endpoint-url=http://localhost:4566 ssm get-parameters-by-path \
  --path "/call-processing/local/" --recursive
```

### Reset LocalStack

```bash
# Stop and remove containers
docker-compose -f docker-compose-localstack.yml down

# Remove volumes
docker-compose -f docker-compose-localstack.yml down -v

# Restart
docker-compose -f docker-compose-localstack.yml up -d

# Re-initialize resources
python -m tests.localstack_automation.run_automation --setup
```

---

## AWS Credentials Issues

### Check Current Identity

```bash
aws sts get-caller-identity
```

### Refresh ADFS Credentials

```bash
# Run the login script
./aws-login.sh

# Or manually
python scripts/aws_adfs_login.py
```

### Check Credential File

```bash
cat ~/.aws/credentials
```

### Use Specific Profile

```bash
# Set in .env.local
AWS_PROFILE=external-access

# Or export
export AWS_PROFILE=external-access
```

---

## Cache Issues

### Force Cache Refresh

```python
from src.config.ssm_loader import SSMParameterLoader
from src.config.secrets_loader import SecretsLoader

# Clear SSM cache
ssm_loader = SSMParameterLoader(region='ap-southeast-1')
ssm_loader.clear_cache()

# Clear secrets cache
secrets_loader = SecretsLoader(region='ap-southeast-1')
secrets_loader.clear_cache()
```

### Invalidate Specific Path

```python
from src.config.ssm_loader import SSMParameterLoader

loader = SSMParameterLoader(region='ap-southeast-1')
loader.invalidate_path('/call-processing/prod/')
```

### Reset ConfigProvider

```python
from src.config.config_provider import reset_config, get_config

# Reset global config
reset_config()

# Re-initialize
config = get_config()
```

---

## Environment Variable Issues

### Check Environment Variables

```bash
# All relevant env vars
env | grep -E "(AWS_|ENVIRONMENT|USE_LOCALSTACK|DYNAMODB_|S3_)"
```

### Verify .env.local Loading

```python
import os

# Check if .env.local was loaded
print(f"USE_LOCALSTACK: {os.getenv('USE_LOCALSTACK')}")
print(f"ENVIRONMENT: {os.getenv('ENVIRONMENT')}")
print(f"AWS_REGION: {os.getenv('AWS_REGION')}")
```

### Manual .env.local Load

```python
from pathlib import Path

def load_env_file(path: str):
    env_file = Path(path)
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    print(f"{key.strip()} = {value.strip()}")

load_env_file('.env.local')
```

---

## Permission Issues

### Check IAM Permissions

```bash
# SSM
aws ssm get-parameter --name "/call-processing/prod/server/log-level"

# Secrets Manager
aws secretsmanager get-secret-value --secret-id "call-processing/prod/api-keys"

# DynamoDB
aws dynamodb describe-table --table-name "call-processing-prod-transformation-system"

# S3
aws s3 ls s3://call-processing-prod-call-data/
```

### Simulate IAM Policy

```bash
aws iam simulate-principal-policy \
  --policy-source-arn "arn:aws:iam::ACCOUNT:role/call-processing-prod-task-role" \
  --action-names "ssm:GetParameter" \
  --resource-arns "arn:aws:ssm:ap-southeast-1:ACCOUNT:parameter/call-processing/prod/server/log-level"
```

---

## Logging

### Enable Debug Logging

```python
import logging

# Enable debug for config modules
logging.getLogger('src.config').setLevel(logging.DEBUG)
logging.getLogger('src.config.config_provider').setLevel(logging.DEBUG)
logging.getLogger('src.config.ssm_loader').setLevel(logging.DEBUG)
logging.getLogger('src.config.secrets_loader').setLevel(logging.DEBUG)
```

### Check Config API Logs

```bash
# View CloudWatch logs
aws logs tail /aws/call-processing/prod --follow
```

---

*Related: [Configuration Sources](configuration-sources.md) | [Code Flow](code-flow.md)*
