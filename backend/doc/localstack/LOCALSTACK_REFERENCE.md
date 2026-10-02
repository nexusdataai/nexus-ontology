# LocalStack Reference Guide

Quick reference for LocalStack commands, endpoints, and configurations.

## Service URLs

| Service | URL | Port |
|---------|-----|------|
| LocalStack Gateway | http://localhost:4566 | 4566 |
| DynamoDB Admin UI | http://localhost:8001 | 8001 |
| API Server | http://localhost:8000 | 8000 |

## Script Reference

### Start Scripts

| Script | Platform | Description |
|--------|----------|-------------|
| `localstack/start-localstack.ps1` | Windows PowerShell | Start LocalStack with initialization |
| `localstack/start-localstack.bat` | Windows CMD | Wrapper for PowerShell script |
| `localstack/start-localstack.sh` | Linux/macOS | Start LocalStack with initialization |

### Stop Scripts

| Script | Platform | Options |
|--------|----------|---------|
| `localstack/stop-localstack.ps1` | Windows | `-Volumes` to remove data |
| `localstack/stop-localstack.sh` | Linux/macOS | `--volumes` to remove data |

### Test Scripts

| Script | Platform | Description |
|--------|----------|-------------|
| `localstack/test-localstack.ps1` | Windows | Verify LocalStack setup |
| `localstack/test-localstack.sh` | Linux/macOS | Verify LocalStack setup |

### Initialization Scripts

| Script | Platform | Description |
|--------|----------|-------------|
| `localstack/localstack-init.ps1` | Windows | Create tables, buckets, log groups |
| `localstack/localstack-init.sh` | Linux/macOS | Create tables, buckets, log groups |

### Data Scripts

| Script | Description |
|--------|-------------|
| `localstack/seed-localstack-data.py` | Seed sample test data |

## AWS CLI Commands

### DynamoDB

```bash
# Set endpoint for all commands
export ENDPOINT="--endpoint-url http://localhost:4566"

# List tables
aws dynamodb list-tables $ENDPOINT

# Describe table
aws dynamodb describe-table --table-name TransformationSystem $ENDPOINT

# Scan table (get all items)
aws dynamodb scan --table-name TransformationSystem $ENDPOINT

# Query by partition key
aws dynamodb query \
    --table-name TransformationSystem \
    --key-condition-expression "PK = :pk" \
    --expression-attribute-values '{":pk":{"S":"JOURNEY#journey-001"}}' \
    $ENDPOINT

# Put item
aws dynamodb put-item \
    --table-name TransformationSystem \
    --item '{"PK":{"S":"TEST#1"},"SK":{"S":"DATA"}}' \
    $ENDPOINT

# Delete item
aws dynamodb delete-item \
    --table-name TransformationSystem \
    --key '{"PK":{"S":"TEST#1"},"SK":{"S":"DATA"}}' \
    $ENDPOINT
```

### S3

```bash
# List buckets
aws s3 ls $ENDPOINT

# List bucket contents
aws s3 ls s3://transformation-journey-logs $ENDPOINT

# Upload file
aws s3 cp myfile.txt s3://transformation-journey-logs/ $ENDPOINT

# Download file
aws s3 cp s3://transformation-journey-logs/myfile.txt ./downloaded.txt $ENDPOINT

# Delete file
aws s3 rm s3://transformation-journey-logs/myfile.txt $ENDPOINT

# Sync directory
aws s3 sync ./local-dir s3://transformation-journey-logs/remote-dir $ENDPOINT
```

### CloudWatch Logs

```bash
# List log groups
aws logs describe-log-groups $ENDPOINT

# List log streams
aws logs describe-log-streams \
    --log-group-name /aws/nexus-backend/api \
    $ENDPOINT

# Get log events
aws logs get-log-events \
    --log-group-name /aws/nexus-backend/api \
    --log-stream-name your-stream-name \
    $ENDPOINT

# Put log events
aws logs put-log-events \
    --log-group-name /aws/nexus-backend/api \
    --log-stream-name test-stream \
    --log-events timestamp=$(date +%s000),message="Test log" \
    $ENDPOINT
```

## API Endpoints

### Health Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/health/live` | GET | Liveness probe |
| `/health/ready` | GET | Readiness probe |
| `/health/localstack` | GET | LocalStack connectivity |
| `/health/metrics` | GET | System metrics |

### LocalStack Health Response

```json
{
  "status": "healthy",
  "endpoint": "http://localhost:4566",
  "region": "us-east-1",
  "services": {
    "dynamodb": "running",
    "s3": "running",
    "cloudwatch": "running",
    "sts": "running"
  },
  "timestamp": "2025-01-01T00:00:00.000Z"
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_LOCALSTACK` | `false` | Enable LocalStack mode |
| `LOCALSTACK_HOST` | `localhost` | LocalStack hostname |
| `LOCALSTACK_PORT` | `4566` | LocalStack port |
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | `test` | Access key (any value works) |
| `AWS_SECRET_ACCESS_KEY` | `test` | Secret key (any value works) |
| `DYNAMODB_TABLE_NAME` | `TransformationSystem` | DynamoDB table name |
| `LOG_LEVEL` | `INFO` | Logging level |

## Docker Commands

```bash
# View running containers
docker ps

# View LocalStack logs
docker logs nexus-localstack
docker logs -f nexus-localstack  # Follow logs

# Restart LocalStack
docker restart nexus-localstack

# Stop all LocalStack services
docker-compose -f docker-compose-localstack.yml down

# Stop and remove volumes
docker-compose -f docker-compose-localstack.yml down -v

# Rebuild and start
docker-compose -f docker-compose-localstack.yml up -d --build
```

## Verification Checklist

After starting LocalStack, verify:

- [ ] `docker ps` shows `nexus-localstack` running
- [ ] `curl http://localhost:4566/_localstack/health` returns services
- [ ] DynamoDB Admin accessible at http://localhost:8001
- [ ] `./localstack/test-localstack.sh` passes all checks
- [ ] API health endpoint returns healthy: `curl http://localhost:8000/health/localstack`

## Resources Created

### DynamoDB Tables

| Table | Partition Key | Sort Key | GSI |
|-------|--------------|----------|-----|
| TransformationSystem | PK (String) | SK (String) | GSI1 (GSI1PK, GSI1SK) |

### S3 Buckets

| Bucket | Purpose |
|--------|---------|
| transformation-journey-logs | Journey execution logs |
| transformation-journey-reports | Generated reports |
| nexus-dev-wxcc-recordings | WXCC call recordings |
| nexus-dev-wxcc-transcripts | WXCC call transcripts |
| nexus-dev-wxcc-simulator | WXCC simulator data |

### CloudWatch Log Groups

| Log Group | Purpose |
|-----------|---------|
| /aws/nexus-backend/api | API server logs |
| /aws/nexus-backend/jobs | Background job logs |

## Troubleshooting Quick Reference

| Issue | Command |
|-------|---------|
| Check if LocalStack running | `docker ps \| grep localstack` |
| View LocalStack logs | `docker logs nexus-localstack` |
| Check health | `curl http://localhost:4566/_localstack/health` |
| Restart LocalStack | `docker restart nexus-localstack` |
| Full reset | `docker-compose -f docker-compose-localstack.yml down -v` |
| Re-initialize | `./localstack/localstack-init.sh` |
