# LocalStack Quick Start Guide

Get nexus-backend running with LocalStack in 3 steps.

## Prerequisites

- Docker Desktop installed and running
- AWS CLI installed (`aws --version`)
- Python 3.9+ with pip

## Quick Start

### Step 1: Start LocalStack

**Windows (PowerShell):**
```powershell
.\scripts\start-localstack.ps1
```

**Linux/macOS:**
```bash
./scripts/start-localstack.sh
```

Wait for "LocalStack is ready!" message.

### Step 2: Configure Environment

Copy the example environment file:

**Windows:**
```powershell
Copy-Item .env.localstack.example .env.local
```

**Linux/macOS:**
```bash
cp .env.localstack.example .env.local
```

Or set environment variables:
```bash
export USE_LOCALSTACK=true
export LOCALSTACK_HOST=localhost
```

### Step 3: Start the API Server

```bash
python -m uvicorn src.main:app --reload --port 8000
```

## Verify Setup

Test LocalStack health:
```bash
curl http://localhost:8000/health/localstack
```

Expected response:
```json
{
  "status": "healthy",
  "endpoint": "http://localhost:4566",
  "services": {"dynamodb": "running", "s3": "running"}
}
```

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| API Server | http://localhost:8000 | nexus-backend API |
| LocalStack | http://localhost:4566 | AWS services |
| DynamoDB Admin | http://localhost:8001 | Database browser |

## Essential Commands

```bash
# Test LocalStack
.\scripts\test-localstack.ps1    # Windows
./scripts/test-localstack.sh     # Linux

# Seed test data
python scripts/seed-localstack-data.py

# Stop LocalStack
.\scripts\stop-localstack.ps1    # Windows
./scripts/stop-localstack.sh     # Linux

# Stop and remove data
.\scripts\stop-localstack.ps1 -Volumes    # Windows
./scripts/stop-localstack.sh --volumes    # Linux
```

## Troubleshooting

**LocalStack won't start:**
```bash
docker ps                              # Check Docker is running
docker logs nexus-localstack         # View LocalStack logs
```

**Connection refused:**
```bash
curl http://localhost:4566/_localstack/health
```

**Tables not created:**
```bash
.\scripts\localstack-init.ps1    # Windows
./scripts/localstack-init.sh     # Linux
```

## Next Steps

- [Full Setup Guide](LOCAL_SETUP_LOCALSTACK.md) - Detailed instructions
- [Reference Guide](LOCALSTACK_REFERENCE.md) - Command reference
- [API Documentation](../api/README.md) - API endpoints
