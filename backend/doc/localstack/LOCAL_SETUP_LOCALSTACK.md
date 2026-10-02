# LocalStack Complete Setup Guide

Comprehensive guide for setting up LocalStack development environment for nexus-backend.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Development Workflow](#development-workflow)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Topics](#advanced-topics)

## Overview

LocalStack provides a fully functional local AWS cloud stack for development and testing. This setup emulates:

- **DynamoDB** - NoSQL database for transformation data
- **S3** - Object storage for logs and reports
- **CloudWatch** - Logging and monitoring
- **STS** - Security token service
- **Athena** - Query service for analytics

### Benefits

- No AWS account required for development
- Fast iteration without cloud latency
- Isolated environment per developer
- Consistent test data
- Cost-free development

## Prerequisites

### Required Software

1. **Docker Desktop**
   - Windows: [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
   - macOS: `brew install --cask docker`
   - Linux: Follow [Docker installation guide](https://docs.docker.com/engine/install/)

2. **AWS CLI v2**
   - Windows: `winget install Amazon.AWSCLI`
   - macOS: `brew install awscli`
   - Linux: See [AWS CLI installation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

3. **Python 3.9+**
   - Verify: `python --version`

### Verify Prerequisites

```bash
# Check Docker
docker --version
docker info

# Check AWS CLI
aws --version

# Check Python
python --version
```

## Installation

### 1. Clone Repository (if not done)

```bash
git clone <repository-url>
cd nexus-backend
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start LocalStack

**Windows (PowerShell):**
```powershell
.\localstack\start-localstack.ps1
```

**Windows (Command Prompt):**
```cmd
localstack\start-localstack.bat
```

**Linux/macOS:**
```bash
chmod +x localstack/*.sh
./localstack/start-localstack.sh
```

The script will:
1. Start LocalStack Docker container
2. Wait for health check
3. Create DynamoDB tables
4. Create S3 buckets
5. Create CloudWatch log groups

### 4. Verify Installation

```bash
# Windows
.\localstack\test-localstack.ps1

# Linux/macOS
./localstack/test-localstack.sh
```

Expected output:
```
✓ LocalStack health endpoint
✓ TransformationSystem table exists
✓ GSI1 index exists
✓ S3 bucket: transformation-journey-logs
✓ S3 bucket: transformation-journey-reports
...
✅ All tests passed!
```

## Configuration

### Environment Variables

Create `.env.local` from the example:

```bash
cp .env.localstack.example .env.local
```

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_LOCALSTACK` | `true` | Enable LocalStack mode |
| `LOCALSTACK_HOST` | `localhost` | LocalStack hostname |
| `LOCALSTACK_PORT` | `4566` | LocalStack port |
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | `test` | Dummy access key |
| `AWS_SECRET_ACCESS_KEY` | `test` | Dummy secret key |

### Docker Compose Configuration

The `docker-compose-localstack.yml` defines:

- **localstack**: Main LocalStack container
  - Port 4566: Gateway for all AWS services
  - Health check enabled
  - Persistence enabled

- **dynamodb-admin**: Web UI for DynamoDB
  - Port 8001: Web interface
  - Connects to LocalStack DynamoDB

## Usage

### Option 1: Gateway-Based Workflow (Recommended)

The simplest way to run the full stack locally is using the unified gateway server with LocalStack. This starts both LocalStack and the gateway with a single command.

**Windows (PowerShell):**
```powershell
.\localstack\start-gateway-localstack.ps1
```

**Linux/macOS:**
```bash
chmod +x localstack/*.sh
./localstack/start-gateway-localstack.sh
```

This script will:
1. Start LocalStack Docker container
2. Wait for LocalStack health check
3. Create `.env.local` from template if missing
4. Start the gateway server (`mcp_http_gateway.py`)
5. Verify LocalStack connectivity through the gateway

**Stopping:**
```powershell
# Windows
.\localstack\stop-gateway-localstack.ps1

# Linux/macOS
./localstack/stop-gateway-localstack.sh

# To also remove LocalStack data:
.\localstack\stop-gateway-localstack.ps1 -Volumes    # Windows
./localstack/stop-gateway-localstack.sh --volumes    # Linux
```

**Service URLs (Gateway Mode):**

| Service | URL | Description |
|---------|-----|-------------|
| Gateway | http://localhost:8000 | Unified API gateway |
| API Docs | http://localhost:8000/docs | Swagger documentation |
| LocalStack Health | http://localhost:8000/health/localstack | LocalStack status |
| LocalStack Gateway | http://localhost:4566 | Direct LocalStack access |
| DynamoDB Admin | http://localhost:8001 | DynamoDB web UI |

**Verify Gateway + LocalStack:**
```bash
# Check gateway health
curl http://localhost:8000/health

# Check LocalStack connectivity through gateway
curl http://localhost:8000/health/localstack

# Expected response when healthy:
# {"status":"healthy","endpoint":"http://localhost:4566","services":{"dynamodb":"running",...}}
```

### Option 2: Separate Services Workflow

If you prefer to start LocalStack and the API server separately:

#### Starting Services

```bash
# Start LocalStack (includes initialization)
.\localstack\start-localstack.ps1    # Windows
./localstack/start-localstack.sh     # Linux

# Start API server
python -m uvicorn src.main:app --reload --port 8000
```

### Stopping Services

```bash
# Stop LocalStack (keep data)
.\localstack\stop-localstack.ps1    # Windows
./localstack/stop-localstack.sh     # Linux

# Stop and remove all data
.\localstack\stop-localstack.ps1 -Volumes    # Windows
./localstack/stop-localstack.sh --volumes    # Linux
```

### Seeding Test Data

```bash
python localstack/seed-localstack-data.py
```

Options:
- `--skip-seed`: Skip seeding (for clean tests)
- `--endpoint URL`: Custom LocalStack endpoint
- `--table NAME`: Custom table name

### Accessing Services

| Service | URL | Credentials |
|---------|-----|-------------|
| API Server | http://localhost:8000 | N/A |
| LocalStack Gateway | http://localhost:4566 | test/test |
| DynamoDB Admin | http://localhost:8001 | N/A |
| API Docs | http://localhost:8000/docs | N/A |

### Using AWS CLI with LocalStack

```bash
# List DynamoDB tables
aws dynamodb list-tables --endpoint-url http://localhost:4566

# Scan table
aws dynamodb scan --table-name TransformationSystem --endpoint-url http://localhost:4566

# List S3 buckets
aws s3 ls --endpoint-url http://localhost:4566

# Upload file to S3
aws s3 cp myfile.txt s3://transformation-journey-logs/ --endpoint-url http://localhost:4566
```

## Development Workflow

### Gateway-Based Development (Recommended)

The gateway-based workflow provides the simplest development experience with a single command startup.

1. **Start Everything** (once per session)
   ```bash
   # Windows
   .\localstack\start-gateway-localstack.ps1
   
   # Linux/macOS
   ./localstack/start-gateway-localstack.sh
   ```

2. **Develop and Test**
   - Make code changes
   - Test API endpoints at http://localhost:8000
   - View API docs at http://localhost:8000/docs
   - Check LocalStack status at http://localhost:8000/health/localstack

3. **Stop when done**
   ```bash
   # Windows
   .\localstack\stop-gateway-localstack.ps1
   
   # Linux/macOS
   ./localstack/stop-gateway-localstack.sh
   ```

### Traditional Development (Separate Services)

If you need more control or are debugging specific components:

1. **Start LocalStack** (once per session)
   ```bash
   ./localstack/start-localstack.sh
   ```

2. **Start API Server**
   ```bash
   python -m uvicorn src.main:app --reload --port 8000
   ```

3. **Develop and Test**
   - Make code changes
   - API auto-reloads
   - Test with curl or Postman

4. **Stop when done**
   ```bash
   ./localstack/stop-localstack.sh
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run LocalStack-specific tests
pytest tests/property/ -v

# Run with LocalStack integration
USE_LOCALSTACK=true pytest tests/integration/
```

### Checking Health

```bash
# LocalStack health
curl http://localhost:4566/_localstack/health

# API LocalStack health endpoint
curl http://localhost:8000/health/localstack
```

## Troubleshooting

### Gateway-Specific Issues

#### Gateway Not Starting

**Symptom:** Gateway fails to start or health check fails

**Solution:**
```bash
# Check gateway logs
cat gateway.log    # Linux
Get-Content gateway.log    # Windows

# Verify .env.local exists and has USE_LOCALSTACK=true
cat .env.local | grep USE_LOCALSTACK

# Restart everything
./localstack/stop-gateway-localstack.sh
./localstack/start-gateway-localstack.sh
```

#### LocalStack Health Shows "unreachable"

**Symptom:** `/health/localstack` returns status "unreachable"

**Solution:**
```bash
# Check if LocalStack container is running
docker ps | grep localstack

# Check LocalStack logs
docker logs nexus-localstack

# Verify LocalStack is healthy directly
curl http://localhost:4566/_localstack/health

# Restart LocalStack
docker-compose -f docker-compose-localstack.yml restart
```

#### Gateway Port Already in Use

**Symptom:** "Port 8000 is already in use"

**Solution:**
```bash
# Find process using port 8000
netstat -ano | findstr :8000    # Windows
lsof -i :8000                   # Linux

# Kill the process or use a different port
python mcp_http_gateway.py --port 8001
```

### Common Issues

#### Docker Not Running

**Symptom:** "Cannot connect to Docker daemon"

**Solution:**
```bash
# Windows: Start Docker Desktop from Start Menu
# Linux:
sudo systemctl start docker
```

#### Port Already in Use

**Symptom:** "Port 4566 is already in use"

**Solution:**
```bash
# Find process using port
netstat -ano | findstr :4566    # Windows
lsof -i :4566                   # Linux

# Kill process or use different port
docker-compose -f docker-compose-localstack.yml down
```

#### LocalStack Not Starting

**Symptom:** Health check fails

**Solution:**
```bash
# Check logs
docker logs nexus-localstack

# Restart with clean state
docker-compose -f docker-compose-localstack.yml down -v
./localstack/start-localstack.sh
```

#### Tables Not Created

**Symptom:** "Table not found" errors

**Solution:**
```bash
# Re-run initialization
./localstack/localstack-init.sh    # Linux
.\localstack\localstack-init.ps1   # Windows
```

#### Connection Refused

**Symptom:** "Connection refused" when accessing LocalStack

**Solution:**
1. Verify LocalStack is running: `docker ps`
2. Check endpoint URL matches configuration
3. Ensure firewall allows localhost connections

### Debug Commands

```bash
# View LocalStack logs
docker logs -f nexus-localstack

# Check container status
docker ps -a | grep localstack

# Inspect container
docker inspect nexus-localstack

# Check network
docker network ls
docker network inspect nexus-local
```

## Advanced Topics

### Custom Table Schema

To modify the DynamoDB table schema, edit `localstack/localstack-init.sh`:

```bash
aws dynamodb create-table \
    --endpoint-url "$ENDPOINT" \
    --table-name YourTable \
    --attribute-definitions \
        AttributeName=PK,AttributeType=S \
        AttributeName=SK,AttributeType=S \
    --key-schema \
        AttributeName=PK,KeyType=HASH \
        AttributeName=SK,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST
```

### Persistent Data

Data persists in `./localstack-data/` directory. To reset:

```bash
./localstack/stop-localstack.sh --volumes
rm -rf localstack-data/
./localstack/start-localstack.sh
```

### Multiple Environments

Create separate compose files for different environments:

```bash
# Development
docker-compose -f docker-compose-localstack.yml up -d

# Testing (isolated)
docker-compose -f docker-compose-localstack-test.yml up -d
```

### CI/CD Integration

See `.github/workflows/test-localstack.yml` for GitHub Actions integration.

```yaml
services:
  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"
    env:
      SERVICES: dynamodb,s3,cloudwatch
```

## Resources

- [LocalStack Documentation](https://docs.localstack.cloud/)
- [AWS CLI Reference](https://docs.aws.amazon.com/cli/latest/reference/)
- [DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/)
- [nexus-backend API Documentation](../api/README.md)
