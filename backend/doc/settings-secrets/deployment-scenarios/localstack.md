# Local Development with LocalStack

LocalStack provides a local AWS emulation for development without AWS costs or credentials.

---

## Configuration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     LOCAL + LOCALSTACK CONFIGURATION                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Configuration Flow:                                                        │
│  ┌─────────────────┐                                                        │
│  │   .env.local    │ ──► Environment Variables ──► ConfigProvider           │
│  └─────────────────┘                                                        │
│                                                                             │
│  AWS Services:                                                              │
│  ┌─────────────────┐     ┌─────────────────────────────────────┐           │
│  │    LocalStack   │     │  Endpoint: http://localhost:4566    │           │
│  │    Container    │ ◄── │  Credentials: test/test (auto)      │           │
│  │    (Docker)     │     │  Region: ap-southeast-1             │           │
│  └─────────────────┘     └─────────────────────────────────────┘           │
│                                                                             │
│  Environment Detection Result:                                              │
│  • environment = 'local'                                                    │
│  • is_aws_environment() = False                                             │
│  • Config loaded from: .env.local only                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Required `.env.local` Settings

```bash
# Enable LocalStack mode
USE_LOCALSTACK=true
LOCALSTACK_HOST=localhost
LOCALSTACK_PORT=4566
ENVIRONMENT=local

# AWS Region (for LocalStack)
AWS_REGION=ap-southeast-1

# Resource names (LocalStack creates these)
DYNAMODB_TABLE=call-processing-local-transformation-system
S3_RECORDINGS_BUCKET=call-processing-local-call-data
WXCC_SIMULATOR_BUCKET=call-processing-local-wxcc-simulator
```

---

## Starting LocalStack

```bash
# Start LocalStack container
docker-compose -f docker-compose-localstack.yml up -d

# Initialize resources (DynamoDB tables, S3 buckets)
python -m tests.localstack_automation.run_automation --setup

# Verify LocalStack is running
curl http://localhost:4566/_localstack/health
```

---

## How AWS Clients Connect to LocalStack

```python
# src/config/ssm_loader.py
def _create_client(self):
    if os.getenv('USE_LOCALSTACK', '').lower() == 'true':
        endpoint_url = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
        return boto3.client(
            'ssm',
            region_name=self.region,
            endpoint_url=endpoint_url,
            aws_access_key_id='test',      # LocalStack accepts any credentials
            aws_secret_access_key='test'
        )
    return boto3.client('ssm', region_name=self.region)
```

---

## LocalStack Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_LOCALSTACK` | Enable LocalStack mode | `false` |
| `LOCALSTACK_HOST` | LocalStack hostname | `localhost` |
| `LOCALSTACK_PORT` | LocalStack port | `4566` |
| `AWS_ENDPOINT_URL` | Override endpoint for all services | `http://localhost:4566` |

---

## Verifying LocalStack Resources

```bash
# List DynamoDB tables
aws --endpoint-url=http://localhost:4566 dynamodb list-tables

# List S3 buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# Check SSM parameters
aws --endpoint-url=http://localhost:4566 ssm get-parameters-by-path \
  --path "/call-processing/local/" --recursive
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | LocalStack not running | `docker-compose -f docker-compose-localstack.yml up -d` |
| Tables not found | Resources not initialized | Run `python -m tests.localstack_automation.run_automation --setup` |
| Wrong endpoint | AWS_ENDPOINT_URL not set | Ensure `USE_LOCALSTACK=true` in `.env.local` |

---

*Related: [Local with Real AWS](local-aws.md) | [Configuration Sources](../configuration-sources.md)*
