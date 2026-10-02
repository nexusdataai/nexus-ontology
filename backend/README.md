# Call Processing Capability - Nexus Backend

**Enterprise-grade AI-powered call processing and analytics platform for Webex Contact Center**

This repository contains the backend service for the **Call Processing Capability**, a comprehensive platform for processing Webex Contact Center calls with AI-powered transcription, analysis, and reporting.

## 🎯 Overview

### Core Purpose

The **Call Processing Capability** is an enterprise call analytics platform that:

1. **Processes Webex CC Calls** - Fetches, transcribes, and analyzes calls from Webex Contact Center
2. **Manages Transformation Journeys** - Orchestrates multi-stage processing workflows
3. **Provides AI Analytics** - Leverages OpenAI for intelligent call analysis and insights
4. **Enables Real-time Monitoring** - Comprehensive logging, reporting, and dashboards

### Key Features

- **📞 Call Processing**: Automated processing of Webex CC call recordings
- **🎙️ Transcription**: AI-powered speech-to-text transcription
- **🧠 AI Analysis**: GPT-powered call analysis and insights
- **🚀 Journey Management**: Create and manage multi-stage processing workflows
- **📊 Real-time Analytics**: Performance metrics and comprehensive reporting
- **🔄 WXCC Simulator**: Built-in simulator for testing without live Webex CC
- **🛠️ MCP Integration**: Model Context Protocol tools for AI agent integration
- **📋 License Management**: Enterprise licensing and feature gating

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                   Call Processing Capability                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │   MCP Tools      │  │  REST APIs       │  │  Config        │ │
│  │  - journeys      │  │  - /api/v1/...   │  │   Provider     │ │
│  │  - simulator     │  │  - journey API   │  │  - SSM Params  │ │
│  │  - license       │  │  - license API   │  │  - Secrets Mgr │ │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬────────┘ │
│           │                      │                    │          │
│  ┌────────▼──────────────────────▼────────────────────▼────────┐│
│  │              Transformation Stages                           ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐    ││
│  │  │call-process │ │raw-analysis │ │  ui-development     │    ││
│  │  │- Fetch Tasks│ │- Schema     │ │  - Claude AI        │    ││
│  │  │- Transcribe │ │  Analysis   │ │  - Code Generation  │    ││
│  │  │- AI Analyze │ │- Complexity │ │                     │    ││
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘    ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  DynamoDB        │  │   S3 Buckets     │  │   AWS Glue     │ │
│  │  - transformation│  │  - call-data     │  │  - Analytics   │ │
│  │  - license       │  │  - journey-logs  │  │    Database    │ │
│  │  - wxcc-tracking │  │  - wxcc-simulator│  │  - Call Tables │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Call Processing Stages

1. **Fetch Tasks** - Retrieve tasks from Webex CC for configured time period
2. **Deduplication** - Check for already-processed tasks
3. **Process Recordings** - Download, transcribe, and upload recordings
4. **Register Metadata** - Create metadata and register Glue partitions
5. **AI Analysis** - Run comprehensive GPT analysis on transcripts

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- AWS Account (or LocalStack for local development)
- Docker (for LocalStack)

### Configuration System

The service uses a centralized configuration provider that supports multiple environments:

| Environment | Config Source | Resource Pattern |
|-------------|---------------|------------------|
| **ECS/AWS** | SSM Parameter Store + Secrets Manager | `call-processing-prod-*` |
| **Local AWS** | Environment variables | `call-processing-dev-*` |
| **LocalStack** | `.env.local` file | `call-processing-local-*` |

### Running the Gateway

The gateway can be run in two modes: **LocalStack** (local development) or **Real AWS** (production/staging).

#### Using gateway.sh (Recommended)

The `gateway.sh` script provides a unified interface for managing the gateway:

```bash
# Available commands
./gateway.sh start    # Start the gateway
./gateway.sh stop     # Stop the gateway
./gateway.sh restart  # Restart the gateway
./gateway.sh status   # Check gateway status
./gateway.sh logs     # Tail gateway logs (Ctrl+C to exit)
./gateway.sh test     # Run comprehensive gateway tests
```

#### Mode 1: LocalStack (Local Development)

Use LocalStack for local development without AWS costs or credentials.

```bash
# 1. Start LocalStack
docker-compose -f docker-compose-localstack.yml up -d

# 2. Configure environment for LocalStack
cp .env.localstack.example .env.local

# 3. Set LocalStack environment variables
export USE_LOCALSTACK=true
export LOCALSTACK_HOST=localhost
export LOCALSTACK_PORT=4566
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# 4. Initialize LocalStack resources (creates tables and buckets)
python -m tests.localstack_automation.run_automation --setup

# 5. Start the gateway
./gateway.sh start

# 6. Verify
./gateway.sh test
# or
curl http://localhost:8000/health
```

**LocalStack Environment Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_LOCALSTACK` | Enable LocalStack mode | `false` |
| `LOCALSTACK_HOST` | LocalStack hostname | `localhost` |
| `LOCALSTACK_PORT` | LocalStack port | `4566` |
| `AWS_ACCESS_KEY_ID` | Dummy AWS key (any value) | `test` |
| `AWS_SECRET_ACCESS_KEY` | Dummy AWS secret (any value) | `test` |

#### Mode 2: Real AWS (Production/Staging)

Use real AWS services for production or staging environments.

```bash
# 1. Ensure AWS credentials are configured
# Option A: Use AWS CLI profile
export AWS_PROFILE=your-profile-name

# Option B: Use environment variables
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=ap-southeast-1

# Option C: Use IAM role (ECS/EC2)
# No credentials needed - uses instance role

# 2. Ensure LocalStack is DISABLED
export USE_LOCALSTACK=false
# or simply don't set USE_LOCALSTACK at all

# 3. Set environment name
export ENVIRONMENT=prod  # or dev, staging

# 4. Start the gateway
./gateway.sh start

# 5. Verify
./gateway.sh test
# or
curl http://localhost:8000/health
```

**Real AWS Environment Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_LOCALSTACK` | Must be `false` or unset | `false` |
| `ENVIRONMENT` | Environment name (dev/staging/prod) | `dev` |
| `AWS_REGION` | AWS region | `ap-southeast-1` |
| `AWS_PROFILE` | AWS CLI profile name | - |
| `AWS_ACCESS_KEY_ID` | AWS access key (if not using profile/role) | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (if not using profile/role) | - |

#### Gateway Configuration Options

Both modes support these common configuration options:

| Variable | Description | Default |
|----------|-------------|---------|
| `GATEWAY_PORT` | HTTP gateway port | `8000` |
| `MIN_WORKERS` | Minimum worker processes | `2` |
| `MAX_WORKERS` | Maximum worker processes | `8` |
| `API_KEY` | Gateway API authentication key | `super-secret` |
| `LOG_LEVEL` | Logging verbosity (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `MCP_REQUEST_TIMEOUT` | Request timeout in seconds | `60.0` |

#### Quick Reference

```bash
# LocalStack mode (one-liner)
USE_LOCALSTACK=true ./gateway.sh start

# Real AWS mode with profile (one-liner)
AWS_PROFILE=myprofile ENVIRONMENT=prod ./gateway.sh start

# Check which mode is active
./gateway.sh status
```

### Environment Variables

#### Core Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name | `dev` |
| `AWS_REGION` | AWS region | `ap-southeast-1` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `GATEWAY_PORT` | HTTP gateway port | `8000` |
| `API_KEY` | Gateway API key | `super-secret` |

#### Resource Names (Auto-generated from environment)

| Variable | Pattern | Example (prod) |
|----------|---------|----------------|
| `DYNAMODB_TABLE` | `call-processing-{env}-transformation-system` | `call-processing-prod-transformation-system` |
| `LICENSE_TABLE` | `call-processing-{env}-license` | `call-processing-prod-license` |
| `S3_RECORDINGS_BUCKET` | `call-processing-{env}-call-data` | `call-processing-prod-call-data` |
| `WXCC_SIMULATOR_BUCKET` | `call-processing-{env}-wxcc-simulator` | `call-processing-prod-wxcc-simulator` |

#### LocalStack Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_LOCALSTACK` | Enable LocalStack mode | `false` |
| `LOCALSTACK_HOST` | LocalStack hostname | `localhost` |
| `LOCALSTACK_PORT` | LocalStack port | `4566` |

#### AWS Access Mode (network profile)

These env vars are injected by the kube-operator based on
`NexusNetworkConfig.spec.awsAccessMode`. The cluster provisioning script at
[`nexus-deployer/deploy/eks/create-hardened-eks-cluster.sh`](../nexus-deployer/deploy/eks/create-hardened-eks-cluster.sh)
owns the matching VPC topology. See
[deploy/eks/README.md](../nexus-deployer/deploy/eks/README.md) for the cost table.

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_MODE` | `higher-cost`, `moderate`, `lowest-cost`, `public-nodes`, or `localstack` | `higher-cost` |
| `AWS_DISABLE_EXPLICIT_SERVICE_ENDPOINTS` | Force boto3 to default public hostnames (auto-set for non-`higher-cost` modes) | unset |
| `AWS_ENDPOINT_URL_<SERVICE>` | Per-service explicit endpoint override (escape hatch) | unset |

Verify the active mode at runtime:

```bash
curl https://<backend>/api/v1/health/aws
# {"aws_access_mode":"lowest-cost","explicit_endpoints_disabled":true,...,"sts_identity":{...}}
```

Switch modes on a running cluster:

```bash
# 1. Update the VPC topology (idempotent)
./nexus-deployer/deploy/eks/create-hardened-eks-cluster.sh \
    --name nexus-dev --network-profile lowest-cost --vpc-id <existing>

# 2. Update the CR -- operator validates + restarts backend pods with new env
kubectl patch nexusnetworkconfig vpc-endpoints --type=merge \
    -p '{"spec":{"awsAccessMode":"lowest-cost"}}'
kubectl annotate nexuscapability nexus-ai-dev reconcile=$(date +%s) --overwrite
```

NAT prerequisites (moderate / lowest-cost): the provisioning script launches
[fck-nat](https://fck-nat.dev/) `t4g.nano` instances via Auto Scaling Group.
The operator only validates that these exist and that private route tables
point to the NAT ENIs — it does not create or modify them.

For comprehensive configuration details, see [INFRASTRUCTURE_REQUIREMENTS.md](doc/INFRASTRUCTURE_REQUIREMENTS.md).

## 🐳 Docker Deployment

### Build and Run

```bash
# Build Docker image
docker build -t call-processing-backend:latest .

# Run with docker-compose
docker-compose up

# Run standalone (ECS-style)
docker run -p 8000:8000 \
  -e ENVIRONMENT=prod \
  -e AWS_REGION=ap-southeast-1 \
  call-processing-backend:latest
```

### ECS Deployment

The service is designed to run on AWS ECS with:
- IAM task role for AWS access (no credentials needed)
- SSM Parameter Store for configuration
- Secrets Manager for sensitive values

```bash
# ECS task definition sets ENVIRONMENT variable
ENVIRONMENT=prod

# Service automatically loads config from:
# - SSM: /call-processing/prod/...
# - Secrets: call-processing/prod/...
```

## 📚 API Reference

### REST APIs

| Endpoint | Description |
|----------|-------------|
| `/api/v1/journeys/*` | Journey management |
| `/api/v1/license/*` | License management |
| `/api/v1/simulator/*` | WXCC Simulator APIs |
| `/api/v1/analytics/*` | Analytics and metrics |
| `/health` | Health check |

### MCP Tools

| Tool | Description |
|------|-------------|
| `journeys_tool` | Journey, stage, and job management |
| `logs_and_reports_tool` | Logs and report generation |
| `wxcc_simulator_tool` | WXCC simulator operations |
| `license_tool` | License activation and validation |

### Example: Create a Journey

```bash
curl -X POST http://localhost:8000/api/v1/journeys \
  -H "X-API-Key: super-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Call Processing Journey",
    "description": "Process Webex CC calls",
    "stages": [
      {"id": "call_process", "name": "Call Processing", "order": 0}
    ]
  }'
```

### Example: Seed WXCC Simulator

```bash
curl -X POST http://localhost:8000/api/v1/simulator/admin/seed \
  -H "X-API-Key: super-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "numTasks": 5,
    "hoursBack": 24
  }'
```

## 🧪 Testing

### Unit Tests
```bash
pytest tests/unit/ -v
```

### Integration Tests
```bash
# With LocalStack
USE_LOCALSTACK=true pytest tests/integration/ -v
```

### BDD Tests
```bash
pytest tests/bdd/ -v --gherkin-terminal-reporter
```

### E2E Tests
```bash
pytest tests/e2e/ -v
```

## 🏗️ Project Structure

```
nexus-backend/
├── src/
│   ├── apis/                 # REST API endpoints
│   │   ├── journey_api.py
│   │   ├── license_api.py
│   │   └── wxcc_simulator_api.py
│   ├── config/               # Configuration management
│   │   ├── config_provider.py    # Central config provider
│   │   ├── ssm_loader.py         # SSM Parameter Store
│   │   ├── secrets_loader.py     # Secrets Manager
│   │   └── localstack_config.py  # LocalStack support
│   ├── license/              # License management
│   ├── models/               # Data models
│   ├── services/             # Business logic
│   ├── stages/               # Transformation stages
│   │   ├── base_stage.py
│   │   ├── call-process/     # Call processing stage
│   │   ├── raw-analysis/
│   │   └── ui-development/
│   ├── tools/                # MCP tools
│   └── utils/                # Utilities
├── scripts/
│   ├── call-scripts/         # Call processing scripts
│   └── wxcc-simulator/       # Simulator utilities
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── bdd/
│   └── e2e/
├── doc/
│   └── INFRASTRUCTURE_REQUIREMENTS.md
├── mcp_http_gateway.py       # Main gateway server
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## 🔒 Security

- **API Authentication**: X-API-Key header required
- **AWS IAM**: Role-based access via ECS task roles
- **Secrets Management**: AWS Secrets Manager for sensitive data
- **License Validation**: Enterprise license key verification
- **Cognito Integration**: Optional user authentication

## 📖 Documentation

- [Infrastructure Requirements](doc/INFRASTRUCTURE_REQUIREMENTS.md) - AWS resources and configuration
- [LocalStack Quick Start](doc/localstack/QUICKSTART_LOCALSTACK.md) - Local development setup

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary and confidential.

---

## 🗃️ Foundry Workspace Migration (Dashboards)

Dashboards are now persisted in DynamoDB via the `foundry-workspace` table
(item layout: `PK=DASHBOARD#{uid}`, `SK=META`, payload inline; large payloads
overflow to S3 when `DASHBOARD_S3_BUCKET` is configured). Solutions and Views
share the same single-table design.

To migrate existing dashboards from S3 into DynamoDB:

```bash
# Dry-run (lists what would be migrated, no writes)
python scripts/migrate_dashboards_s3_to_ddb.py --dry-run

# Real migration (idempotent: skips items already in DDB)
python scripts/migrate_dashboards_s3_to_ddb.py

# Force overwrite (re-migrates even if DDB item exists)
python scripts/migrate_dashboards_s3_to_ddb.py --force

# Override defaults
python scripts/migrate_dashboards_s3_to_ddb.py \
    --bucket my-dashboards-bucket \
    --prefix dashboards/ \
    --table call-processing-dev-foundry-workspace
```

The script uses the same config resolution as the runtime services
(`DASHBOARD_S3_BUCKET` / `s3_dashboards_bucket`, `FOUNDRY_WORKSPACE_TABLE` /
`dynamodb_foundry_workspace_table`).

---

**Version**: 0.0.1  
**Capability**: call-processing  
**Last Updated**: December 2024  
**Status**: Development
