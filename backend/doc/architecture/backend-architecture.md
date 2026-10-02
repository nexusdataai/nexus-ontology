# Nexus Telco Backend - System Architecture

This document describes the architecture of the Nexus Telco Backend, the processing engine for Totogi CallSense platform.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Technology Stack](#2-technology-stack)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Directory Structure](#4-directory-structure)
5. [API Layer](#5-api-layer)
6. [Services Layer](#6-services-layer)
7. [Stage Pipeline Architecture](#7-stage-pipeline-architecture)
8. [Configuration Management](#8-configuration-management)
9. [Data Layer](#9-data-layer)
10. [External Integrations](#10-external-integrations)
11. [Security Architecture](#11-security-architecture)
12. [Deployment Architecture](#12-deployment-architecture)
13. [Monitoring & Logging](#13-monitoring--logging)

---

## 1. Overview

### Purpose

The Nexus Telco Backend is the core processing engine of the Totogi CallSense platform. It provides:

- **AI-Powered Call Processing** - Fetch, transcribe, and analyze call recordings
- **Journey Orchestration** - Multi-stage transformation pipelines
- **External Integrations** - Webex CC, Salesforce, OpenAI connectivity
- **REST API** - Backend services for the frontend application
- **MCP Server** - Model Context Protocol for AI agent integration

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **Call Processing** | Fetch tasks from Webex CC, transcribe recordings, run AI analysis |
| **CRM Integration** | Create leads/opportunities in Salesforce based on call analysis |
| **WXCC Simulator** | Mock Webex CC API for development and testing |
| **License Management** | License activation, validation, and enforcement |
| **Analytics** | Call metrics, QA analytics, performance dashboards |

---

## 2. Technology Stack

### Core Technologies

| Component | Technology | Version |
|-----------|------------|---------|
| **Language** | Python | 3.11+ |
| **Web Framework** | FastAPI | Latest |
| **Protocol** | Model Context Protocol (MCP) | via FastMCP |
| **AWS SDK** | boto3 | Latest |
| **AI/ML** | OpenAI GPT | GPT-4 |
| **Database** | AWS DynamoDB | Serverless |
| **Storage** | AWS S3 | Standard |
| **Analytics** | AWS Glue + Athena | Serverless |

### Python Dependencies

```
fastapi>=0.100.0          # Web framework
uvicorn>=0.23.0           # ASGI server
boto3>=1.28.0             # AWS SDK
pydantic>=2.0.0           # Data validation
httpx>=0.24.0             # Async HTTP client
loguru>=0.7.0             # Logging
python-dotenv>=1.0.0      # Environment configuration
mcp>=0.1.0                # Model Context Protocol
```

---

## 3. High-Level Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NEXUS BACKEND ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         ENTRY POINTS                                 │   │
│  │  ┌─────────────────────┐     ┌─────────────────────────────────┐    │   │
│  │  │   MCP HTTP Gateway  │     │   MCP Server (stdio)            │    │   │
│  │  │   mcp_http_gateway  │     │   src/server.py                 │    │   │
│  │  │   Port: 8000        │     │   For AI Agents                 │    │   │
│  │  └──────────┬──────────┘     └──────────────────────────────────┘    │   │
│  └─────────────┼────────────────────────────────────────────────────────┘   │
│                │                                                            │
│  ┌─────────────▼────────────────────────────────────────────────────────┐   │
│  │                           API LAYER                                   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │ Journey  │ │  Calls   │ │  Auth    │ │  Webex   │ │ Simulator│   │   │
│  │  │   API    │ │   API    │ │   API    │ │   API    │ │   API    │   │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │   │
│  └───────┼────────────┼────────────┼────────────┼────────────┼──────────┘   │
│          │            │            │            │            │               │
│  ┌───────▼────────────▼────────────▼────────────▼────────────▼──────────┐   │
│  │                        SERVICES LAYER                                 │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │   │
│  │  │  JourneyService  │  │ProcessedCalls    │  │  WebexConnector    │  │   │
│  │  │                  │  │    Service       │  │     Service        │  │   │
│  │  └────────┬─────────┘  └────────┬─────────┘  └──────────┬─────────┘  │   │
│  └───────────┼─────────────────────┼───────────────────────┼────────────┘   │
│              │                     │                       │                │
│  ┌───────────▼─────────────────────▼───────────────────────▼────────────┐   │
│  │                         STAGE LAYER                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │   │
│  │  │ CallProcessStage│  │ RawAnalysisStage│  │WXCCSimulatorStage│      │   │
│  │  │ 6 steps pipeline│  │ Schema analysis │  │ Mock data gen   │       │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘       │   │
│  └───────────┼─────────────────────────────────────────┼────────────────┘   │
│              │                                         │                    │
│  ┌───────────▼─────────────────────────────────────────▼────────────────┐   │
│  │                          DATA LAYER                                   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │   │
│  │  │   DynamoDB   │  │      S3      │  │  AWS Glue    │  │  Athena  │  │   │
│  │  │   Tables     │  │   Buckets    │  │   Catalog    │  │  Queries │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     EXTERNAL INTEGRATIONS                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │   │
│  │  │  Webex CC    │  │  Salesforce  │  │   OpenAI     │  │  Cognito │  │   │
│  │  │  (or Sim)    │  │     CRM      │  │    GPT-4     │  │   Auth   │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Request Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REQUEST FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Frontend                                                                  │
│   (React)                                                                   │
│      │                                                                      │
│      │ HTTP/REST                                                            │
│      ▼                                                                      │
│   ┌─────────────────────┐                                                   │
│   │  MCP HTTP Gateway   │                                                   │
│   │  (FastAPI)          │                                                   │
│   │  - CORS handling    │                                                   │
│   │  - Auth middleware  │                                                   │
│   │  - Request routing  │                                                   │
│   └──────────┬──────────┘                                                   │
│              │                                                              │
│              ├──────────────────────────────────────────┐                   │
│              │                                          │                   │
│              ▼                                          ▼                   │
│   ┌─────────────────────┐                  ┌─────────────────────┐          │
│   │   REST API Route    │                  │   MCP Tool Route    │          │
│   │   /api/v1/...       │                  │   /mcp/tools/...    │          │
│   └──────────┬──────────┘                  └──────────┬──────────┘          │
│              │                                        │                     │
│              ▼                                        ▼                     │
│   ┌─────────────────────┐                  ┌─────────────────────┐          │
│   │   Service Layer     │                  │   MCP Server        │          │
│   │   - Business logic  │                  │   - Tool execution  │          │
│   │   - Data validation │                  │   - AI agent comms  │          │
│   └──────────┬──────────┘                  └──────────┬──────────┘          │
│              │                                        │                     │
│              └───────────────────┬────────────────────┘                     │
│                                  │                                          │
│                                  ▼                                          │
│              ┌───────────────────────────────────────┐                      │
│              │            Data Layer                 │                      │
│              │   DynamoDB │ S3 │ External APIs       │                      │
│              └───────────────────────────────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Directory Structure

```
nexus-backend/
├── mcp_http_gateway.py          # FastAPI HTTP gateway entry point
├── gateway.sh                   # Gateway startup script
├── pyproject.toml               # Python project configuration
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
│
├── src/                         # Main source code
│   ├── server.py               # MCP server entry point
│   ├── consts.py               # Application constants
│   │
│   ├── apis/                   # REST API endpoints
│   │   ├── __init__.py
│   │   ├── journey_api.py      # Journey management
│   │   ├── calls_api.py        # Processed calls
│   │   ├── auth_api.py         # Authentication
│   │   ├── cognito_auth_api.py # Cognito OAuth
│   │   ├── webex_connector_api.py  # Webex integration
│   │   ├── wxcc_simulator_api.py   # Simulator
│   │   ├── analytics_api.py    # Analytics
│   │   ├── health_api.py       # Health checks
│   │   └── config_api.py       # Configuration
│   │
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── journey_service.py  # Journey orchestration
│   │   ├── calls_service.py    # Call data management
│   │   ├── webex_connector_service.py  # Webex OAuth
│   │   ├── cognito_oauth_service.py    # Cognito auth
│   │   └── diagnostics_service.py      # System diagnostics
│   │
│   ├── stages/                 # Processing stages
│   │   ├── __init__.py         # Stage registry
│   │   ├── base_stage.py       # Abstract base class
│   │   │
│   │   ├── call-process/       # Call processing stage
│   │   │   ├── call_process_stage.py
│   │   │   └── call_processor.py
│   │   │
│   │   ├── raw-analysis/       # Raw data analysis
│   │   │   └── raw_analysis.py
│   │   │
│   │   └── wxcc-simulator/     # WXCC simulator
│   │       ├── wxcc_simulator_stage.py
│   │       └── simulator_processor.py
│   │
│   ├── models/                 # Data models
│   │   ├── journey_model.py    # Journey/Stage/Job models
│   │   ├── api_models.py       # API request/response
│   │   └── wxcc_simulator_models.py
│   │
│   ├── config/                 # Configuration
│   │   ├── config_provider.py  # Central config
│   │   ├── ssm_loader.py       # AWS SSM loader
│   │   └── secrets_loader.py   # Secrets Manager
│   │
│   ├── utils/                  # Utilities
│   │   ├── aws_client_utils.py # AWS client management
│   │   ├── s3_helper.py        # S3 operations
│   │   ├── job_executor.py     # Job execution
│   │   ├── sse_manager.py      # Server-Sent Events
│   │   └── logger.py           # Logging
│   │
│   ├── tools/                  # MCP tool wrappers
│   │   ├── journey_tool.py
│   │   └── logs_and_reports_tool.py
│   │
│   └── license/                # License management
│       ├── services/
│       ├── models/
│       └── tools/
│
├── scripts/                    # Supporting scripts
│   └── call-scripts/           # Call processing utilities
│       ├── wxcc_api.py         # Webex CC API client
│       ├── secrets_provider.py # Credential management
│       ├── sfdc_client.py      # Salesforce client
│       ├── ai_analyzer.py      # OpenAI analyzer
│       └── config.py           # Script configuration
│
├── tests/                      # Test suite
│   ├── unit/
│   ├── integration/
│   └── localstack_automation/
│
└── doc/                        # Documentation
    ├── architecture/
    └── call-processing/
```

---

## 5. API Layer

### API Module Structure

The API layer follows FastAPI patterns with modular routers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   mcp_http_gateway.py                                                       │
│   └── FastAPI Application                                                   │
│       ├── Include Router: /api/v1/journeys  → journey_api.router            │
│       ├── Include Router: /api/v1/calls     → calls_api.router              │
│       ├── Include Router: /api/v1/auth      → auth_api.router               │
│       ├── Include Router: /api/v1/cognito   → cognito_auth_api.router       │
│       ├── Include Router: /api/v1/webex     → webex_connector_api.router    │
│       ├── Include Router: /api/v1/simulator → wxcc_simulator_api.router     │
│       ├── Include Router: /api/v1/analytics → analytics_api.router          │
│       ├── Include Router: /api/v1/config    → config_api.router             │
│       └── Include Router: /health           → health_api.router             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core API Endpoints

#### Journey API (`/api/v1/journeys`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all journeys |
| POST | `/` | Create new journey |
| GET | `/{journey_id}` | Get journey details |
| PUT | `/{journey_id}` | Update journey |
| DELETE | `/{journey_id}` | Delete journey |
| GET | `/{journey_id}/stages` | List journey stages |
| POST | `/{journey_id}/jobs` | Run job on stage |
| GET | `/{journey_id}/jobs` | List job history |
| GET | `/{journey_id}/jobs/{job_id}` | Get job status |
| GET | `/{journey_id}/jobs/{job_id}/stream` | SSE job updates |
| GET | `/{journey_id}/jobs/{job_id}/logs/{step_id}` | Get step logs |

#### Calls API (`/api/v1/calls`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/processed-calls` | List processed calls |
| GET | `/processed-calls/{task_id}` | Get call details |
| GET | `/processed-calls/{task_id}/recording` | Get recording URL |
| GET | `/processed-calls/{task_id}/transcript` | Get transcript |
| GET | `/processed-calls/{task_id}/analysis` | Get AI analysis |
| GET | `/processed-calls/{task_id}/sfdc-action` | Get CRM action |

#### Authentication APIs

| Endpoint | Description |
|----------|-------------|
| `/api/v1/auth/login` | Session-based login |
| `/api/v1/auth/logout` | Session logout |
| `/api/v1/cognito/authorize` | Cognito OAuth initiate |
| `/api/v1/cognito/callback` | Cognito OAuth callback |
| `/api/v1/cognito/userinfo` | Get user info |

### Authentication Middleware

```python
# Session-based authentication
@router.get("/protected")
async def protected_endpoint(user: dict = Depends(require_authentication)):
    return {"user": user}

# Role-based access control
@router.post("/admin-only")
async def admin_endpoint(user: dict = Depends(require_role("admin"))):
    return {"admin": True}

# Permission-based access
@router.delete("/delete")
async def delete_endpoint(user: dict = Depends(require_permission("delete:calls"))):
    return {"deleted": True}
```

---

## 6. Services Layer

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICES LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        JourneyService                                │   │
│  │  - Journey CRUD operations                                          │   │
│  │  - Stage management                                                 │   │
│  │  - Job execution orchestration                                      │   │
│  │  - Rule management                                                  │   │
│  │                                                                     │   │
│  │  Methods:                                                           │   │
│  │  - create_journey() / get_journey() / list_journeys()              │   │
│  │  - run_job() / get_job_status() / list_jobs()                      │   │
│  │  - create_stage() / update_stage() / delete_stage()                │   │
│  │  - execute_action() ← Main entry point for all actions              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   ProcessedCallsService                              │   │
│  │  - List processed calls from Glue/Athena                            │   │
│  │  - Get call recordings from S3                                      │   │
│  │  - Retrieve transcripts and analysis                                │   │
│  │                                                                     │   │
│  │  Methods:                                                           │   │
│  │  - list_processed_calls() → Query Athena                            │   │
│  │  - get_call_details() → S3 + DynamoDB lookup                        │   │
│  │  - get_recording_url() → Generate presigned URL                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   WebexConnectorService                              │   │
│  │  - OAuth PKCE flow for Webex CC                                     │   │
│  │  - Token management                                                 │   │
│  │  - Configuration storage                                            │   │
│  │                                                                     │   │
│  │  Methods:                                                           │   │
│  │  - initiate_oauth() → Generate PKCE challenge                       │   │
│  │  - complete_oauth() → Exchange code for tokens                      │   │
│  │  - refresh_token() → Refresh expired tokens                         │   │
│  │  - get_connection_status() → Check connection health                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   WXCCSimulatorService                               │   │
│  │  - Manage simulator data in DynamoDB                                │   │
│  │  - Seed test data                                                   │   │
│  │  - Create/update/delete mock tasks                                  │   │
│  │                                                                     │   │
│  │  Methods:                                                           │   │
│  │  - seed_data() → Generate mock call data                            │   │
│  │  - create_task() → Create mock task                                 │   │
│  │  - list_tasks() → Query simulator tasks                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Service Pattern

```python
class JourneyService:
    """Example service pattern"""
    
    def __init__(self):
        self.config = get_config()
        self.manager = TransformationDataManager(
            table_name=self.config.transformation_table,
            region_name=self.config.aws_region
        )
    
    async def execute_action(self, request: JourneyActionRequest) -> JourneyResponse:
        """Main entry point for journey actions"""
        action = request.action
        
        if action == "create_journey":
            return await self.create_journey(request)
        elif action == "run_job":
            return await self.run_job(request)
        # ... other actions
    
    async def run_job(self, request: JourneyActionRequest) -> JourneyResponse:
        """Execute a transformation job"""
        # 1. Validate journey and stage
        # 2. Create job record
        # 3. Schedule background execution
        # 4. Return job_id immediately
        pass
```

---

## 7. Stage Pipeline Architecture

### Stage Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STAGE PIPELINE ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         BaseStage (Abstract)                         │   │
│  │  src/stages/base_stage.py                                           │   │
│  │                                                                     │   │
│  │  Abstract Methods:                                                  │   │
│  │  - execute_step(step_id, step_data) → Dict                          │   │
│  │                                                                     │   │
│  │  Provided Methods:                                                  │   │
│  │  - _log_local() → Local logging                                     │   │
│  │  - upload_logs_to_s3() → S3 log upload                              │   │
│  │  - upload_report_to_s3() → S3 report upload                         │   │
│  │  - set_metric() / get_metric() → Metrics management                 │   │
│  │  - add_artifact() → Step artifacts                                  │   │
│  │  - emit_sse_event() → Real-time updates                             │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                          │
│         ┌───────────────────────┼───────────────────────┐                  │
│         │                       │                       │                  │
│         ▼                       ▼                       ▼                  │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐           │
│  │CallProcess   │       │RawAnalysis   │       │WXCCSimulator │           │
│  │   Stage      │       │   Stage      │       │    Stage     │           │
│  │              │       │              │       │              │           │
│  │ 6 Steps:     │       │ 3 Steps:     │       │ 2 Steps:     │           │
│  │ - fetch_tasks│       │ - schema_scan│       │ - seed_data  │           │
│  │ - dedup      │       │ - complexity │       │ - validate   │           │
│  │ - process    │       │ - report     │       │              │           │
│  │ - metadata   │       │              │       │              │           │
│  │ - ai_analysis│       │              │       │              │           │
│  │ - crm_actions│       │              │       │              │           │
│  └──────────────┘       └──────────────┘       └──────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Call Processing Stage Steps

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CALL PROCESSING STAGE PIPELINE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Step 1: fetch_tasks                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Query Webex CC API (or simulator) for telephony tasks             │   │
│  │ • Time range: configured minutes_back (default 7 days)              │   │
│  │ • Output: List of task IDs with metadata                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  Step 2: deduplication                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Check DynamoDB for already-processed task IDs                     │   │
│  │ • Separate new tasks from already-processed                         │   │
│  │ • Output: new_task_ids[], skipped_task_ids[]                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  Step 3: process_recordings                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • For each new task:                                                │   │
│  │   - Download recording from Webex (or simulator)                    │   │
│  │   - Transcribe audio (OpenAI Whisper or AWS Transcribe)             │   │
│  │   - Upload to S3: recording.wav, transcript.json                    │   │
│  │   - Mark task as processed in DynamoDB                              │   │
│  │ • Emit SSE events for real-time progress                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  Step 4: register_metadata                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Create metadata JSON for each processed call                      │   │
│  │ • Register partitions in AWS Glue catalog                           │   │
│  │ • Query Athena to verify registration                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  Step 5: ai_analysis                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • For each transcript:                                              │   │
│  │   - Send to OpenAI GPT-4 for comprehensive analysis                 │   │
│  │   - Generate: summary, sentiment, grading, issues, recommendations  │   │
│  │   - Upload analysis.json to S3                                      │   │
│  │   - Update metadata with analysis reference                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  Step 6: crm_actions                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • For each analyzed call:                                           │   │
│  │   - Determine CRM action (create lead, convert, skip)               │   │
│  │   - Execute Salesforce API call                                     │   │
│  │   - Create deduplication marker in S3                               │   │
│  │   - Upload sfdc_action.json                                         │   │
│  │ • Generate execution report                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Stage Registry

```python
# src/stages/__init__.py

AVAILABLE_STAGES = {
    'call_process': 'stages.call-process.call_process_stage.CallProcessStage',
    'raw_analysis': 'stages.raw-analysis.raw_analysis.RawAnalysisStage',
    'wxcc_simulator': 'stages.wxcc-simulator.wxcc_simulator_stage.WXCCSimulatorStage',
}

def get_stage_class(stage_id: str):
    """Get stage class by ID"""
    if stage_id in AVAILABLE_STAGES:
        module_path = AVAILABLE_STAGES[stage_id]
        # Dynamic import and return class
        return import_class(module_path)
    return None

def list_available_stages() -> List[str]:
    """List all registered stage IDs"""
    return list(AVAILABLE_STAGES.keys())
```

---

## 8. Configuration Management

### Configuration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONFIGURATION MANAGEMENT                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       ConfigProvider                                 │   │
│  │  src/config/config_provider.py                                      │   │
│  │                                                                     │   │
│  │  Singleton access: get_config() → ConfigProvider                    │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                          │
│                    ┌────────────┴────────────┐                             │
│                    │   Environment Detection │                             │
│                    └────────────┬────────────┘                             │
│                                 │                                          │
│         ┌───────────────────────┼───────────────────────┐                  │
│         │                       │                       │                  │
│         ▼                       ▼                       ▼                  │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐           │
│  │   ECS/AWS    │       │  LocalStack  │       │    Local     │           │
│  │              │       │              │       │              │           │
│  │ SSM Params + │       │ .env.local + │       │ .env.local + │           │
│  │ Secrets Mgr  │       │ LocalStack   │       │ Env vars     │           │
│  │              │       │ endpoints    │       │              │           │
│  └──────────────┘       └──────────────┘       └──────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Configuration Properties

| Property | Source (ECS) | Source (Local) | Description |
|----------|--------------|----------------|-------------|
| `environment` | `ENVIRONMENT` env | `ENVIRONMENT` env | dev/stage/prod |
| `aws_region` | `AWS_REGION` | `AWS_REGION` | AWS region |
| `transformation_table` | SSM | env | DynamoDB table name |
| `s3_bucket` | SSM | env | S3 bucket name |
| `glue_database_name` | SSM | env | Glue database |
| `openai_api_key` | Secrets Manager | env | OpenAI API key |
| `webex_client_id` | Secrets Manager | env | Webex OAuth client ID |
| `cognito_user_pool_id` | SSM | env | Cognito user pool |

### Environment Detection

```python
class ConfigProvider:
    def _detect_environment(self) -> str:
        """Detect running environment"""
        # Check for ECS container metadata
        if os.environ.get('ECS_CONTAINER_METADATA_URI'):
            return 'ecs'
        
        # Check for LocalStack
        if os.environ.get('USE_LOCALSTACK', '').lower() == 'true':
            return 'localstack'
        
        # Default to local development
        return 'local'
    
    def _load_config(self):
        """Load configuration based on environment"""
        env = self._detect_environment()
        
        if env == 'ecs':
            self._load_from_ssm()
            self._load_from_secrets_manager()
        elif env == 'localstack':
            self._load_from_env()
            self._configure_localstack_endpoints()
        else:
            self._load_from_env()
```

### Resource Naming Convention

```
Pattern: call-processing-{environment}-{resource-type}

Examples:
- call-processing-prod-transformation-system  (DynamoDB)
- call-processing-prod-call-data              (S3 bucket)
- call-processing-prod-analytics              (Glue database)
- call-processing-prod-license                (DynamoDB)
```

---

## 9. Data Layer

### DynamoDB Tables

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DYNAMODB TABLES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Table: call-processing-{env}-transformation-system                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Purpose: Journey, Stage, Job, Rule tracking                         │   │
│  │                                                                     │   │
│  │ Key Schema:                                                         │   │
│  │   PK: JOURNEY#{journey_id}                                          │   │
│  │   SK: METADATA | STAGE#{stage_id} | JOB#{job_id} | RULE#{rule_id}   │   │
│  │                                                                     │   │
│  │ GSI: EntityType-CreatedAt-index                                     │   │
│  │   PK: EntityType (Journey | Stage | Job | Rule)                     │   │
│  │   SK: CreatedAt                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Table: call-processing-{env}-wxcc-tracking                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Purpose: Track processed Webex CC tasks for deduplication           │   │
│  │                                                                     │   │
│  │ Key Schema:                                                         │   │
│  │   PK: task_id                                                       │   │
│  │   Attributes: status, processed_at, error_message                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Table: call-processing-{env}-license                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Purpose: License activation and validation                          │   │
│  │                                                                     │   │
│  │ Key Schema:                                                         │   │
│  │   PK: license_key                                                   │   │
│  │   Attributes: activated_at, expires_at, features, status            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Table: call-processing-{env}-wxcc-simulator                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Purpose: WXCC simulator mock data storage                           │   │
│  │                                                                     │   │
│  │ Key Schema:                                                         │   │
│  │   PK: org_id                                                        │   │
│  │   SK: TASK#{task_id}                                                │   │
│  │   Attributes: status, direction, origin, destination, recording_url │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### S3 Bucket Structure

```
s3://call-processing-{env}-call-data/
│
├── call-detail/                    # Per-call artifacts
│   └── {task_id}/
│       ├── recording.wav           # Audio recording
│       ├── transcript.json         # Transcription with diarization
│       ├── analysis.json           # AI analysis results
│       └── sfdc_action.json        # CRM action results
│
├── call-data/                      # Partitioned metadata (Glue)
│   └── year=YYYY/month=MM/day=DD/hour=HH/
│       └── {task_id}.json          # Call metadata for Athena
│
├── journey-logs/                   # Job execution logs
│   └── {journey_id}/{job_id}/{step_id}/
│       ├── logs.txt                # Step logs
│       └── report.json             # Step report
│
└── SFDC/                           # CRM deduplication markers
    └── {task_id}.txt               # Marker file
```

### AWS Glue Catalog

```
Database: call-processing-{env}-analytics

Table: wxcc_calls
├── Columns:
│   ├── task_id (string)
│   ├── status (string)
│   ├── direction (string)
│   ├── origin_phone (string)
│   ├── destination_phone (string)
│   ├── queue_name (string)
│   ├── agent_name (string)
│   ├── duration_seconds (int)
│   ├── recording_file (string)
│   ├── transcript_file (string)
│   └── analysis_file (string)
│
├── Partitions:
│   ├── year (string)
│   ├── month (string)
│   ├── day (string)
│   └── hour (string)
│
└── Location: s3://call-processing-{env}-call-data/call-data/
```

---

## 10. External Integrations

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL INTEGRATIONS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Webex Contact Center                              │   │
│  │                                                                     │   │
│  │  Mode Selection: WXCC_SIMULATOR_ENABLED env var                     │   │
│  │                                                                     │   │
│  │  ┌───────────────────────┐    ┌───────────────────────┐             │   │
│  │  │   Real Mode           │    │   Simulator Mode      │             │   │
│  │  │   (Production)        │    │   (Development)       │             │   │
│  │  │                       │    │                       │             │   │
│  │  │ URL: api.wxcc-us1.    │    │ URL: localhost:8000/  │             │   │
│  │  │      cisco.com/v1     │    │      api/v1/simulator │             │   │
│  │  │                       │    │                       │             │   │
│  │  │ Auth: OAuth tokens    │    │ Auth: Static token    │             │   │
│  │  │       from Secrets    │    │       (WXCC_SIM_TOKEN)│             │   │
│  │  │       Manager         │    │                       │             │   │
│  │  └───────────────────────┘    └───────────────────────┘             │   │
│  │                                                                     │   │
│  │  Key Files:                                                         │   │
│  │  - scripts/call-scripts/wxcc_api.py       (API client)              │   │
│  │  - scripts/call-scripts/secrets_provider.py (Credential mgmt)       │   │
│  │  - src/services/webex_connector_service.py (OAuth service)          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Salesforce CRM                                 │   │
│  │                                                                     │   │
│  │  Integration: REST API via sfdc_client.py                           │   │
│  │                                                                     │   │
│  │  Operations:                                                        │   │
│  │  - create_lead() → Create new lead                                  │   │
│  │  - convert_lead() → Convert lead to opportunity                     │   │
│  │  - create_opportunity() → Create opportunity directly               │   │
│  │  - update_account() → Update existing account                       │   │
│  │                                                                     │   │
│  │  Authentication: OAuth 2.0 (client credentials)                     │   │
│  │  Credentials: AWS Secrets Manager                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         OpenAI GPT                                   │   │
│  │                                                                     │   │
│  │  Integration: OpenAI Python SDK via ai_analyzer.py                  │   │
│  │                                                                     │   │
│  │  Operations:                                                        │   │
│  │  - analyze_call_comprehensive() → Full call analysis                │   │
│  │    - Summary generation                                             │   │
│  │    - Sentiment analysis                                             │   │
│  │    - Agent performance grading                                      │   │
│  │    - Issue detection                                                │   │
│  │    - Recommendation generation                                      │   │
│  │                                                                     │   │
│  │  Model: GPT-4 (configurable)                                        │   │
│  │  API Key: AWS Secrets Manager or environment variable               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       AWS Cognito                                    │   │
│  │                                                                     │   │
│  │  Integration: boto3 + cognito-idp / cognito-identity                │   │
│  │                                                                     │   │
│  │  Features:                                                          │   │
│  │  - User authentication (OAuth 2.0 / OIDC)                           │   │
│  │  - JWT token validation                                             │   │
│  │  - User pool management                                             │   │
│  │  - SSO integration (SAML)                                           │   │
│  │                                                                     │   │
│  │  Key Files:                                                         │   │
│  │  - src/apis/cognito_auth_api.py (OAuth endpoints)                   │   │
│  │  - src/apis/cognito_auth_middleware.py (Token validation)           │   │
│  │  - src/services/cognito_oauth_service.py (OAuth service)            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Integration Configuration

| Integration | Config Source | Required Parameters |
|-------------|---------------|---------------------|
| **Webex CC** | SSM + Secrets Manager | client_id, client_secret, org_id, base_url |
| **Salesforce** | Secrets Manager | client_id, client_secret, instance_url |
| **OpenAI** | Secrets Manager | api_key |
| **Cognito** | SSM | user_pool_id, client_id, domain |

---

## 11. Security Architecture

### Authentication Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SECURITY ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AUTHENTICATION LAYER                              │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │  Cognito    │  │   API Key   │  │   Session   │  │  MFA       │ │   │
│  │  │  OAuth/OIDC │  │  Header     │  │  Cookie     │  │  Support   │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AUTHORIZATION LAYER                               │   │
│  │                                                                     │   │
│  │  Role-Based Access Control (RBAC):                                  │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ Admin      → Full access to all operations                   │   │   │
│  │  │ Operator   → Execute jobs, view data, manage integrations    │   │   │
│  │  │ Analyst    → View dashboards, access analytics               │   │   │
│  │  │ Viewer     → Read-only access                                │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  Permission-Based Access:                                           │   │
│  │  - journeys:read, journeys:write, journeys:delete                  │   │
│  │  - calls:read, calls:export                                        │   │
│  │  - settings:read, settings:write                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    DATA PROTECTION                                   │   │
│  │                                                                     │   │
│  │  Encryption at Rest:                                                │   │
│  │  - S3: AES-256 (SSE-S3 or SSE-KMS)                                 │   │
│  │  - DynamoDB: AES-256 (AWS managed)                                 │   │
│  │                                                                     │   │
│  │  Encryption in Transit:                                             │   │
│  │  - TLS 1.2+ for all API communications                             │   │
│  │  - HTTPS enforced                                                  │   │
│  │                                                                     │   │
│  │  Secrets Management:                                                │   │
│  │  - AWS Secrets Manager for API keys and credentials                │   │
│  │  - Dynamic secret loading at runtime                               │   │
│  │  - Support for secret rotation                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### API Security

```python
# Authentication middleware
async def require_authentication(request: Request) -> dict:
    """Verify user is authenticated"""
    # Check session cookie
    session_id = request.cookies.get("session_id")
    if session_id:
        return validate_session(session_id)
    
    # Check API key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return validate_api_key(api_key)
    
    # Check Cognito JWT token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return validate_cognito_token(auth_header[7:])
    
    raise HTTPException(status_code=401, detail="Authentication required")

# Role-based access
async def require_role(role: str):
    async def dependency(user: dict = Depends(require_authentication)):
        if user.get("role") != role and user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency
```

---

## 12. Deployment Architecture

### AWS Infrastructure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DEPLOYMENT ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         VPC (10.0.0.0/16)                            │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐          │   │
│  │  │   Public Subnet         │  │   Private Subnet        │          │   │
│  │  │   10.0.1.0/24           │  │   10.0.2.0/24           │          │   │
│  │  │                         │  │                         │          │   │
│  │  │  ┌─────────────────┐    │  │  ┌─────────────────┐    │          │   │
│  │  │  │      ALB        │    │  │  │   ECS Fargate   │    │          │   │
│  │  │  │ (Port 443/80)   │────┼──┼─►│   Container     │    │          │   │
│  │  │  └─────────────────┘    │  │  │   Port: 8000    │    │          │   │
│  │  │                         │  │  └─────────────────┘    │          │   │
│  │  │  ┌─────────────────┐    │  │                         │          │   │
│  │  │  │   NAT Gateway   │    │  │  ┌─────────────────┐    │          │   │
│  │  │  │                 │◄───┼──┼──│  Outbound       │    │          │   │
│  │  │  └─────────────────┘    │  │  │  Traffic        │    │          │   │
│  │  │                         │  │  └─────────────────┘    │          │   │
│  │  └─────────────────────────┘  └─────────────────────────┘          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      AWS Managed Services                            │   │
│  │                                                                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │ DynamoDB │ │    S3    │ │   Glue   │ │  Athena  │ │CloudWatch│  │   │
│  │  │          │ │          │ │          │ │          │ │          │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  │                                                                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │   │
│  │  │ Secrets  │ │   SSM    │ │  Cognito │ │   ECR    │               │   │
│  │  │ Manager  │ │ Params   │ │          │ │          │               │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Container Configuration

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY mcp_http_gateway.py .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
  CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["python", "mcp_http_gateway.py"]
```

### ECS Task Definition (Key Settings)

| Setting | Value |
|---------|-------|
| CPU | 512 - 2048 |
| Memory | 1024 - 4096 MB |
| Port Mapping | 8000 |
| Log Driver | awslogs |
| Environment | SSM parameters |
| Secrets | Secrets Manager references |

---

## 13. Monitoring & Logging

### Logging Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MONITORING & LOGGING                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        APPLICATION LOGS                              │   │
│  │                                                                     │   │
│  │  Source: loguru logger                                              │   │
│  │  Destination: CloudWatch Logs                                       │   │
│  │  Log Group: /ecs/call-processing-{env}-backend                      │   │
│  │                                                                     │   │
│  │  Log Levels:                                                        │   │
│  │  - DEBUG: Detailed debugging information                            │   │
│  │  - INFO: General operational events                                 │   │
│  │  - WARNING: Warning conditions                                      │   │
│  │  - ERROR: Error conditions                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         JOB LOGS                                     │   │
│  │                                                                     │   │
│  │  Storage: S3 (per-job, per-step)                                    │   │
│  │  Path: s3://{bucket}/journey-logs/{journey_id}/{job_id}/{step_id}/  │   │
│  │                                                                     │   │
│  │  Files:                                                             │   │
│  │  - logs.txt: Step execution logs                                    │   │
│  │  - report.json: Step execution report with metrics                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        HEALTH ENDPOINTS                              │   │
│  │                                                                     │   │
│  │  /health      → Basic health check (200 OK)                         │   │
│  │  /ready       → Readiness probe (checks DynamoDB connection)        │   │
│  │  /live        → Liveness probe (always 200 if running)              │   │
│  │  /api/health  → Detailed health with component status               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     REAL-TIME UPDATES (SSE)                          │   │
│  │                                                                     │   │
│  │  Endpoint: GET /api/v1/journeys/{id}/jobs/{job_id}/stream           │   │
│  │                                                                     │   │
│  │  Event Types:                                                       │   │
│  │  - step_status: Step status changes                                 │   │
│  │  - log: Real-time log messages                                      │   │
│  │  - task_progress: Task-level progress during processing             │   │
│  │  - job_complete: Job completion notification                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### CloudWatch Metrics

| Metric | Description |
|--------|-------------|
| `jobs_started` | Number of jobs started |
| `jobs_completed` | Number of jobs completed successfully |
| `jobs_failed` | Number of jobs failed |
| `step_duration` | Duration of each step execution |
| `calls_processed` | Number of calls processed |
| `api_latency` | API response latency |

### Alarms

| Alarm | Condition | Action |
|-------|-----------|--------|
| High Error Rate | `jobs_failed / jobs_started > 0.1` | SNS notification |
| High Latency | `api_latency > 5000ms` | SNS notification |
| Container Health | `UnhealthyHostCount > 0` | SNS notification |
| DynamoDB Throttling | `ThrottledRequests > 0` | SNS notification |

---

## Version Information

| Component | Version |
|-----------|---------|
| Nexus Telco Backend | 2.0.0 |
| Python | 3.11+ |
| FastAPI | Latest |
| boto3 | Latest |

---

*Last Updated: January 2026*  
*Document Version: 2.0*  
*Maintained by: Totogi Engineering Team*
