# LocalStack Scripts

This folder contains all scripts for managing LocalStack development environment for nexus-backend.

## Quick Start

### Windows (PowerShell)
```powershell
# Start LocalStack + Gateway
.\localstack\start-gateway-localstack.ps1

# Stop all services
.\localstack\stop-gateway-localstack.ps1
```

### Linux/macOS
```bash
# Start LocalStack + Gateway
./localstack/start-gateway-localstack.sh

# Stop all services
./localstack/stop-gateway-localstack.sh
```

## Available Scripts

| Script | Description |
|--------|-------------|
| `start-localstack.{ps1,sh,bat}` | Start LocalStack container only |
| `stop-localstack.{ps1,sh}` | Stop LocalStack container |
| `reset-localstack.{ps1,sh}` | Clean and reset LocalStack data |
| `start-gateway-localstack.{ps1,sh}` | Start LocalStack + Gateway together |
| `stop-gateway-localstack.{ps1,sh}` | Stop Gateway + LocalStack |
| `localstack-init.{ps1,sh}` | Initialize LocalStack resources (DynamoDB, S3, CloudWatch) |
| `test-localstack.{ps1,sh}` | Verify LocalStack setup |
| `seed-localstack-data.py` | Seed sample test data |
| `run-localstack-tests.{ps1,sh}` | Run test automation suite |

## Service URLs

| Service | URL |
|---------|-----|
| Gateway API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| LocalStack | http://localhost:4566 |
| DynamoDB Admin | http://localhost:8001 |

## Environment Setup

Copy the example environment file:
```bash
cp .env.localstack.example .env.local
```

## Resources Created

The initialization scripts create:

### DynamoDB Tables
- `TransformationSystem` (with GSI1 index)
- `nexus-dev-wxcc-task-tracking`

### S3 Buckets
- `transformation-journey-logs`
- `transformation-journey-reports`
- `nexus-dev-wxcc-recordings`
- `nexus-dev-wxcc-transcripts`
- `nexus-dev-wxcc-simulator`

### CloudWatch Log Groups
- `/aws/nexus-backend/api`
- `/aws/nexus-backend/jobs`
