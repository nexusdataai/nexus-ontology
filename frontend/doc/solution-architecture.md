# Totogi Enterprise Solutions - Solution Architecture

## Table of Contents

- [Executive Summary](#executive-summary)
- [Overview](#overview)
- [Return on Investment (ROI)](#return-on-investment-roi)
- [System Architecture](#system-architecture)
- [Repository Structure](#repository-structure)
- [Core Applications](#core-applications)
  - [Application 1: Totogi CallSense](#application-1-totogi-callops)
  - [Application 2: Totogi Toolkit](#application-2-totogi-toolkit)
- [Integration Architecture](#integration-architecture)
- [Data Flow](#data-flow)
- [Deployment Architecture](#deployment-architecture)
- [Security Architecture](#security-architecture)
- [Commercial Model](#commercial-model)

---

## Executive Summary

Totogi provides **two primary enterprise applications** designed to transform telecommunications operations:

### 1. **Totogi CallSense Platform** - AI-Powered Call Analytics

An enterprise-grade AI-powered call processing and analytics platform that delivers:

- **100% automated QA coverage** of all calls (vs. 30% manual coverage)
- **Real-time AI insights** on sentiment, compliance, and performance
- **12.5-15% conversion rate improvement** from current 8-10% baseline
- **50% reduction** in manager time spent on manual QA
- **Multi-million dollar revenue impact** with measurable ROI of 25-55x

**Key Capabilities:**
- AI transcription and diarization
- Automated quality assurance and compliance monitoring
- Real-time sentiment analysis and coaching recommendations
- Product recommendation engine
- Automatic quote generation
- Salesforce and Office 365 integration

### 2. **Totogi Toolkit** - Self-Service Deployment Platform

An enterprise-grade self-service deployment toolkit that enables:

- **One-click AWS infrastructure deployment** via guided wizard
- **CloudFormation-based** infrastructure as code
- **License-controlled capability deployment**
- **Desktop (Electron), PWA, and web** deployment options
- **Complete infrastructure provisioning** (VPC, ECS, S3, DynamoDB, CloudFront, Cognito)

**Key Features:**
- Wizard-driven deployment flow
- AWS credential and permission validation
- Multi-capability architecture selection
- Post-deployment health verification
- Installation history and management

Together, these applications enable enterprises to rapidly deploy and operate AI-powered call analytics at scale.

---

## Overview

Totogi's enterprise solution consists of **two distinct but complementary applications**:

### Primary Applications

| Application | Purpose | Users | Technology |
|-------------|---------|-------|------------|
| **Totogi CallSense** | AI-powered call processing and analytics | Sales teams, QA managers, Coaches | React UI + Python Backend + AWS |
| **Totogi Toolkit** | Deploy Totogi capabilities to customer AWS | IT/DevOps teams, System administrators | Electron Desktop + React + Python + CloudFormation |

### Application Relationship

```
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT FLOW                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. IT Admin uses TOTOGI TOOLKIT to deploy                  │
│     ├─> Select Totogi CallSense capability                    │
│     ├─> Configure AWS credentials                           │
│     ├─> Deploy CloudFormation stacks                        │
│     └─> Provision complete infrastructure                   │
│                                                              │
│  2. TOTOGI CALLOPS deployed to customer AWS account         │
│     ├─> Frontend hosted on CloudFront + S3                  │
│     ├─> Backend running on ECS Fargate                      │
│     ├─> Data stored in S3 + DynamoDB                        │
│     └─> Integration with Webex CC + Salesforce              │
│                                                              │
│  3. End users access TOTOGI CALLOPS                         │
│     ├─> Sales teams use analytics dashboard                 │
│     ├─> Managers access QA and coaching tools               │
│     └─> Admins configure integrations and settings          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Return on Investment (ROI)

### Financial ROI – Revenue Impact

**Current State:**
- Enterprise Inside Sales conversion rates: **8-10%**
- Manual QA coverage: **~30%** of 600+ calls
- Manager time on manual QA: **50%** of their time

**With Totogi CallSense:**
- Conversion rates improved to: **12.5-15%**
- Automated QA coverage: **100%** of all calls
- Manager efficiency gain: **50%** time savings

#### Scenario 1: Conservative Case (10% → 12.5%)
- **Incremental bookings**: SGD $200,000/month
- **Annual uplift**: SGD $2.4M
- **ROI**: **25x** (compared to platform cost)

#### Scenario 2: Growth Case (10% → 15%)
- **Incremental bookings**: SGD $400,000/month
- **Annual uplift**: SGD $4.8M
- **ROI**: **55x** (compared to platform cost)

### Operational ROI – Efficiency Gains

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **QA Coverage** | 30% of calls | 100% of calls | +233% |
| **Manager QA Time** | 50% of time | 25% of time | -50% |
| **QA Speed** | Days to review | Real-time | Instant |
| **Insights** | Manual sampling | 100% automated | Complete |
| **Coaching Prep** | Hours per session | Minutes per session | 10x faster |

**Benefits:**
- ✅ Faster ramp times for new sales representatives
- ✅ Sustained productivity improvements across team
- ✅ Real-time coaching interventions
- ✅ Data-driven training need identification

### Strategic ROI – Insights Retained

Enterprises retain valuable assets even beyond platform usage:

1. **Comprehensive QA Dataset**
   - 100% call coverage vs. limited manual samples
   - Baseline benchmarks for conversion rates, adherence, and performance
   
2. **Performance Analytics**
   - Individual rep performance trends
   - Team-wide compliance and quality metrics
   - Product-specific conversion insights

3. **Process Improvements**
   - Identification of training gaps
   - Compliance gap analysis
   - Systemic process optimization opportunities

4. **Competitive Intelligence**
   - Comparative evaluation between AI-enabled vs. manual processes
   - Best practice documentation
   - Proven business case for digital transformation

### ROI Summary

| ROI Type | Impact | Value |
|----------|--------|-------|
| **Financial** | Revenue uplift | SGD $2.4M - $4.8M annually |
| **Operational** | Time savings | 50% manager efficiency gain |
| **Strategic** | Data assets | Permanent insights and benchmarks |
| **Commercial** | Platform cost | $42K annually ($350/user/month × 10 users) |
| **Net ROI** | Return multiple | **25x - 55x** investment |

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     TOTOGI ENTERPRISE SOLUTIONS                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │                    APPLICATION 1: TOTOGI CALLOPS                        │    │
│  │                   (AI-Powered Call Analytics)                           │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │                   APPLICATION 2: TOTOGI TOOLKIT                         │    │
│  │                   (Deployment & Installation)                           │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Application 1: Totogi CallSense Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         TOTOGI CALLOPS PLATFORM                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        USER INTERFACES                                    │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │   │
│  │  │   Nexus Telco UI        │  │  Nexus Telco Deployer   │  │   Electron App   │  │   │
│  │  │   (Analytics)       │  │  (Wizard Frontend)  │  │   (Desktop)      │  │   │
│  │  │   React + Vite      │  │  React + Vite       │  │   Cross-platform │  │   │
│  │  │   Port: 5173        │  │  Port: 5173         │  │                  │  │   │
│  │  └─────────┬───────────┘  └─────────┬───────────┘  └────────┬─────────┘  │   │
│  └────────────┼────────────────────────┼───────────────────────┼────────────┘   │
│               │                        │                       │                 │
│  ┌────────────▼────────────────────────▼───────────────────────▼────────────┐   │
│  │                        BACKEND SERVICES                                   │   │
│  │  ┌─────────────────────────────────┐  ┌────────────────────────────────┐ │   │
│  │  │   Nexus Telco Backend               │  │   Deployer Backend             │ │   │
│  │  │   (Call Processing)             │  │   (AWS Orchestration)          │ │   │
│  │  │   Python + FastAPI              │  │   Python + FastAPI             │ │   │
│  │  │   MCP HTTP Gateway              │  │   CloudFormation               │ │   │
│  │  │   Port: 8000                    │  │   Port: 8001                   │ │   │
│  │  └─────────────────────────────────┘  └────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        AWS INFRASTRUCTURE                                 │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │
│  │  │ DynamoDB │ │    S3    │ │  Athena  │ │  Glue    │ │ CloudWatch   │   │   │
│  │  │ Tables   │ │ Buckets  │ │ Queries  │ │ Catalog  │ │ Logs/Metrics │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │
│  │  │ Cognito  │ │   ECS    │ │CloudFront│ │ Secrets  │ │     SSM      │   │   │
│  │  │ Auth     │ │ Fargate  │ │   CDN    │ │ Manager  │ │ Parameters   │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     EXTERNAL INTEGRATIONS                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │ Webex CC     │  │ Salesforce   │  │ Office 365   │  │ OpenAI       │  │   │
│  │  │ Contact Ctr  │  │ CRM          │  │ Integration  │  │ GPT Analysis │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

### Three-Repository Architecture

| Repository | Application | Purpose | Technology Stack |
|------------|-------------|---------|------------------|
| **nexus-ui** | Totogi CallSense | Analytics Dashboard & Visualization | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| **nexus-backend** | Totogi CallSense | Call Processing & MCP Server | Python 3.11+, FastAPI, boto3, MCP Protocol |
| **nexus-deployer** | Totogi Toolkit | Deployment Wizard & AWS Orchestration | React + Python FastAPI + Electron |

### Repository Mapping to Applications

```
Application 1: Totogi CallSense
├── nexus-ui (Frontend)
│   └── React-based analytics dashboard
└── nexus-backend (Backend)
    └── Python-based call processing engine

Application 2: Totogi Toolkit
└── nexus-deployer (Complete Application)
    ├── Frontend (React wizard)
    ├── Backend (Python orchestrator)
    └── Desktop (Electron wrapper)
```

---

## Core Applications

### Application 1: Totogi CallSense

**Purpose**: AI-Powered Call Processing and Analytics Platform  
**Components**: Nexus Telco UI (Frontend) + Nexus Telco Backend (Processing Engine)  
**Users**: Sales Teams, QA Managers, Coaches, Administrators  

Totogi CallSense is the core call analytics capability that processes, transcribes, and analyzes calls with AI-powered insights.

---

#### Component 1.1: Nexus Telco UI (Analytics Dashboard)

The Nexus Telco UI is the frontend of Totogi CallSense, providing real-time insights and visualization for call analytics.

#### Technology Stack
- **Frontend**: React 18, TypeScript, Vite
- **UI Components**: Radix UI, shadcn/ui, Tailwind CSS
- **Charts**: Recharts, Mapbox GL
- **State Management**: React Query, Context API
- **Authentication**: AWS Amplify, Cognito

#### Key Features
- **Call Analytics Dashboard**: Real-time call metrics, sentiment analysis, performance tracking
- **Journey Management**: Transformation journey visualization and monitoring
- **WXCC Simulator**: Testing interface for Webex Contact Center simulation
- **AI Workspace**: AI-powered insights and recommendations
- **Tools Catalogue**: Connector management (Webex, Salesforce, Office 365)
- **Processed Calls View**: Call transcripts, diarization, and analysis results

#### Component Structure
```
nexus-ui/src/
├── components/
│   ├── dashboards/          # Analytics dashboards
│   ├── journeys/            # Journey management UI
│   ├── processed-calls/     # Call analysis views
│   ├── wxcc-simulator/      # Simulator interface
│   ├── settings/            # Configuration panels
│   └── ui/                  # Reusable UI components
├── services/
│   ├── callProcessingJourneyService.ts
│   ├── transformationJourneyService.ts
│   ├── wxccSimulatorService.ts
│   ├── licenseService.ts
│   └── webexConnectorService.ts
├── context/
│   ├── AuthContext.tsx
│   ├── DashboardContext.tsx
│   └── EnterpriseAuthContext.tsx
└── types/
    ├── transformationJourney.ts
    ├── processedCalls.ts
    └── license.ts
```

---

#### Component 1.2: Nexus Telco Backend (Call Processing Engine)

The Nexus Telco Backend is the processing engine of Totogi CallSense, handling all call processing, AI analysis, and data management.

#### Technology Stack
- **Framework**: Python 3.11+, FastAPI
- **Protocol**: Model Context Protocol (MCP) with HTTP Gateway
- **AWS SDK**: boto3 for AWS service integration
- **AI**: OpenAI GPT for transcription and analysis

#### Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                   Call Processing Capability                     │
├─────────────────────────────────────────────────────────────────┤
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
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  DynamoDB        │  │   S3 Buckets     │  │   AWS Glue     │ │
│  │  - transformation│  │  - call-data     │  │  - Analytics   │ │
│  │  - license       │  │  - journey-logs  │  │    Database    │ │
│  │  - wxcc-tracking │  │  - wxcc-simulator│  │  - Call Tables │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### MCP Tools
| Tool | Description |
|------|-------------|
| `journeys_tool` | Journey, stage, and job management |
| `logs_and_reports_tool` | Logs and report generation |
| `wxcc_simulator_tool` | WXCC simulator operations |
| `license_tool` | License activation and validation |

#### REST APIs
| Endpoint | Description |
|----------|-------------|
| `/api/v1/journeys/*` | Journey management |
| `/api/v1/license/*` | License management |
| `/api/v1/simulator/*` | WXCC Simulator APIs |
| `/api/v1/analytics/*` | Analytics and metrics |
| `/api/v1/calls/*` | Processed calls data |
| `/health` | Health check |

#### Call Processing Stages
1. **Fetch Tasks** - Retrieve tasks from Webex CC
2. **Deduplication** - Check for already-processed tasks
3. **Process Recordings** - Download, transcribe, upload
4. **Register Metadata** - Create metadata and Glue partitions
5. **AI Analysis** - GPT-powered call analysis

---

### Application 2: Totogi Toolkit

**Purpose**: Self-Service Deployment Platform for Totogi Capabilities  
**Components**: Nexus Telco Deployer (Wizard + Backend + Desktop App)  
**Users**: IT Administrators, DevOps Teams, System Administrators  

Totogi Toolkit is a separate application that enables IT teams to deploy Totogi capabilities (like CallSense) into customer AWS accounts through a guided wizard interface.

---

#### Component 2.1: Nexus Telco Deployer (Deployment Toolkit)

The Nexus Telco Deployer is Totogi Toolkit's core component - an enterprise-grade self-service deployment platform for AWS infrastructure.

#### Technology Stack
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: Python + FastAPI + boto3
- **Desktop**: Electron (cross-platform)
- **Infrastructure**: AWS CloudFormation
- **Database**: TinyDB (local state management)

#### Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    End Users                                     │
│          (Desktop App / PWA / Browser)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │   Electron Desktop App          │
        │   - Windows, macOS, Linux       │
        │   - Offline capability          │
        └────────────────┬────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │   React Frontend (PWA)          │
        │   - Deployment Wizard           │
        │   - AWS Configuration           │
        │   - Installation History        │
        └────────────────┬────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │   FastAPI Backend               │
        │   - Deployment Orchestrator     │
        │   - CloudFormation Service      │
        │   - Authentication Service      │
        └────────────────┬────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │   AWS CloudFormation            │
        │   - Template Generation         │
        │   - Stack Orchestration         │
        │   - Resource Provisioning       │
        └────────────────┬────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │   Customer AWS Account          │
        │   - VPC, ECS, RDS, S3, etc.     │
        │   - Complete infrastructure     │
        └─────────────────────────────────┘
```

#### Wizard Flow
1. **Welcome Screen** - License validation
2. **Capability Selection** - Choose capabilities to deploy
3. **Architecture Selection** - Frontend/Backend options
4. **AWS Configuration** - Credentials and region setup
5. **Permission Verification** - IAM permission checks
6. **Deployment Execution** - CloudFormation stack creation
7. **Post Verification** - Health checks and validation
8. **Results** - Deployment summary and endpoints

#### Backend Services
```
nexus-deployer/backend/app/
├── routers/
│   ├── auth.py              # Authentication endpoints
│   ├── aws.py               # AWS credential management
│   ├── capabilities.py      # Capability catalog
│   ├── deployment.py        # Deployment orchestration
│   ├── installations.py     # Installation history
│   └── health.py            # Health checks
├── services/
│   ├── deployment_orchestrator.py
│   ├── cloudformation_service.py
│   ├── aws_session_manager.py
│   ├── template_validator.py
│   ├── authentication_service.py
│   └── mfa_service.py
└── models/
    ├── deployment.py
    ├── capability.py
    └── aws_config.py
```

---

## Integration Architecture

### Component Interactions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INTEGRATION FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐          │
│   │  Nexus Telco    │  HTTP   │  Nexus Telco    │  AWS    │  Customer   │          │
│   │  UI         │◄───────►│  Backend    │◄───────►│  AWS Acct   │          │
│   │  :5173      │  REST   │  :8000      │  SDK    │             │          │
│   └─────────────┘         └─────────────┘         └─────────────┘          │
│         │                       │                       ▲                   │
│         │                       │                       │                   │
│         │                       ▼                       │                   │
│         │               ┌─────────────┐                 │                   │
│         │               │  External   │                 │                   │
│         │               │  Services   │                 │                   │
│         │               │  - Webex CC │                 │                   │
│         │               │  - SFDC     │                 │                   │
│         │               │  - O365     │                 │                   │
│         │               │  - OpenAI   │                 │                   │
│         │               └─────────────┘                 │                   │
│         │                                               │                   │
│         │         ┌─────────────┐                       │                   │
│         │  HTTP   │  Nexus Telco    │  CloudFormation       │                   │
│         └────────►│  Deployer   │───────────────────────┘                   │
│                   │  :8001      │                                           │
│                   └─────────────┘                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### API Integration Points

| Source | Target | Protocol | Purpose |
|--------|--------|----------|---------|
| Nexus Telco UI | Nexus Telco Backend | HTTP/REST | Call analytics, journey management |
| Nexus Telco UI | Nexus Telco Deployer | HTTP/REST | Deployment status, capability info |
| Nexus Telco Backend | AWS Services | boto3 SDK | DynamoDB, S3, Glue, CloudWatch |
| Nexus Telco Backend | Webex CC | REST API | Call recordings, task data |
| Nexus Telco Backend | OpenAI | REST API | Transcription, AI analysis |
| Nexus Telco Deployer | AWS CloudFormation | boto3 SDK | Stack provisioning |

---

## Data Flow

### Call Processing Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         CALL PROCESSING DATA FLOW                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  1. CALL INGESTION                                                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                       │
│  │  Webex CC   │───►│  Backend    │───►│  S3 Bucket  │                       │
│  │  API        │    │  Fetch      │    │  /audio     │                       │
│  └─────────────┘    └─────────────┘    └─────────────┘                       │
│                                                                               │
│  2. TRANSCRIPTION                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                       │
│  │  S3 Audio   │───►│  OpenAI     │───►│  S3 Bucket  │                       │
│  │  Files      │    │  Whisper    │    │  /transcripts│                      │
│  └─────────────┘    └─────────────┘    └─────────────┘                       │
│                                                                               │
│  3. AI ANALYSIS                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                       │
│  │  Transcripts│───►│  GPT-4      │───►│  S3 Bucket  │                       │
│  │             │    │  Analysis   │    │  /analysis  │                       │
│  └─────────────┘    └─────────────┘    └─────────────┘                       │
│                                                                               │
│  4. REPORTING                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                       │
│  │  S3 Data    │───►│  Athena     │───►│  Dashboard  │                       │
│  │  Partitions │    │  Queries    │    │  UI         │                       │
│  └─────────────┘    └─────────────┘    └─────────────┘                       │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### S3 Data Organization

```
s3://call-processing-{env}-call-data/
├── audio/
│   └── year=YYYY/month=MM/day=DD/
│       └── {call-id}-audio.wav
├── transcripts/
│   └── year=YYYY/month=MM/day=DD/
│       └── {call-id}-transcript.json
├── analysis/
│   └── year=YYYY/month=MM/day=DD/
│       └── {call-id}-analysis.json
├── diarized/
│   └── year=YYYY/month=MM/day=DD/
│       └── {call-id}-diarized.json
└── sfdcaction/
    └── year=YYYY/month=MM/day=DD/
        └── {call-id}-sfdcaction.json
```

### DynamoDB Tables

| Table | Purpose | Key Schema |
|-------|---------|------------|
| `call-processing-{env}-transformation-system` | Journey/Stage/Job tracking | PK: journey_id, SK: entity_type |
| `call-processing-{env}-license` | License management | PK: license_key |
| `call-processing-{env}-wxcc-tracking` | WXCC task tracking | PK: task_id |

---

## Deployment Architecture

### AWS Infrastructure (Deployed by Nexus Telco Deployer)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AWS DEPLOYMENT ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         VPC (10.0.0.0/16)                            │    │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐           │    │
│  │  │   Public Subnet         │  │   Private Subnet        │           │    │
│  │  │   ┌─────────────────┐   │  │   ┌─────────────────┐   │           │    │
│  │  │   │  ALB            │   │  │   │  ECS Fargate    │   │           │    │
│  │  │   │  (Load Balancer)│   │  │   │  (Backend)      │   │           │    │
│  │  │   └─────────────────┘   │  │   └─────────────────┘   │           │    │
│  │  │   ┌─────────────────┐   │  │   ┌─────────────────┐   │           │    │
│  │  │   │  NAT Gateway    │   │  │   │  RDS (optional) │   │           │    │
│  │  │   └─────────────────┘   │  │   └─────────────────┘   │           │    │
│  │  └─────────────────────────┘  └─────────────────────────┘           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐    │
│  │  CloudFront         │  │  S3 Buckets         │  │  Cognito         │    │
│  │  (CDN + Frontend)   │  │  - call-data        │  │  (User Pool)     │    │
│  │                     │  │  - wxcc-simulator   │  │                  │    │
│  └─────────────────────┘  └─────────────────────┘  └──────────────────┘    │
│                                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐    │
│  │  DynamoDB           │  │  Secrets Manager    │  │  SSM Parameter   │    │
│  │  (Tables)           │  │  (API Keys)         │  │  Store           │    │
│  └─────────────────────┘  └─────────────────────┘  └──────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Deployment Options

| Component | Option 1 | Option 2 |
|-----------|----------|----------|
| **Frontend** | CloudFront + S3 | AWS Amplify |
| **Backend** | ECS Fargate | EKS (Kubernetes) |
| **Database** | DynamoDB | RDS PostgreSQL |

---

## Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SECURITY ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    AUTHENTICATION LAYER                              │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │  Cognito    │  │  MFA        │  │  SSO        │  │  License   │  │    │
│  │  │  User Pool  │  │  TOTP/SMS   │  │  SAML/OIDC  │  │  Validation│  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    AUTHORIZATION LAYER                               │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │  Role-Based Access Control (RBAC)                           │    │    │
│  │  │  - Administrator: Full access                               │    │    │
│  │  │  - Operator: Deploy and manage                              │    │    │
│  │  │  - Viewer: Read-only access                                 │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    DATA PROTECTION                                   │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │  Encryption │  │  Secrets    │  │  IAM Roles  │  │  Audit     │  │    │
│  │  │  AES-256    │  │  Manager    │  │  Least Priv │  │  Logging   │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Security Features

| Feature | Implementation |
|---------|----------------|
| **Authentication** | AWS Cognito with MFA support |
| **API Security** | API Key + JWT tokens |
| **Encryption at Rest** | AES-256 (S3, DynamoDB) |
| **Encryption in Transit** | TLS 1.2+ |
| **Secrets Management** | AWS Secrets Manager |
| **Audit Logging** | CloudWatch Logs + CloudTrail |
| **License Enforcement** | Cryptographic validation |

---

## Commercial Model

### Totogi CallSense Pricing

**Subscription Model:**
- **Price**: USD $350 per user/month
- **Minimum**: 10 users
- **Commitment**: 2-year agreement
- **Total Investment**: USD $84,000 (over 2 years)

**Included Services:**
- Setup fee waived (normally $15,000) for 2-year commitment
- Fair use policy: Up to 2,000 sales calls per month
- Complete platform access and updates
- Technical support and maintenance
- Restricted to enterprise sales use cases

**Commercial Structure:**

| Item | Standard | With 2-Year Commitment |
|------|----------|------------------------|
| **Monthly per user** | $350 | $350 |
| **Minimum users** | 10 | 10 |
| **Monthly cost** | $3,500 | $3,500 |
| **Annual cost** | $42,000 | $42,000 |
| **Setup fee** | $15,000 | **Waived** |
| **2-Year total** | $99,000 | **$84,000** |
| **Savings** | - | **$15,000** |

**Fair Use Policy:**
- Maximum 2,000 sales calls per month included
- Additional calls available upon request
- Enterprise sales use case focus
- Volume discounts available for larger deployments

### Value Proposition

**Investment vs. Return:**
- **Annual Platform Cost**: $42,000 (10 users)
- **Conservative Revenue Uplift**: $2.4M annually
- **Growth Case Uplift**: $4.8M annually
- **ROI Multiple**: 25x - 55x

**Total Cost of Ownership (TCO):**
```
Year 1: $42,000 (no setup fee with commitment)
Year 2: $42,000
Total 2-Year Cost: $84,000

Expected 2-Year Revenue Impact: $4.8M - $9.6M
Net Return: $4.7M - $9.5M
```

---

## Environment Configuration

### Configuration Sources

| Environment | Config Source | Resource Pattern |
|-------------|---------------|------------------|
| **ECS/AWS** | SSM Parameter Store + Secrets Manager | `call-processing-prod-*` |
| **Local AWS** | Environment variables | `call-processing-dev-*` |
| **LocalStack** | `.env.local` file | `call-processing-local-*` |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name | `dev` |
| `AWS_REGION` | AWS region | `ap-southeast-1` |
| `USE_LOCALSTACK` | Enable LocalStack mode | `false` |
| `GATEWAY_PORT` | HTTP gateway port | `8000` |
| `API_KEY` | Gateway API key | `super-secret` |

---

## Development Setup

### Quick Start

**Nexus Telco UI:**
```bash
cd nexus-ui
npm install
npm run dev  # http://localhost:5173
```

**Nexus Telco Backend:**
```bash
cd nexus-backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
./gateway.sh start  # http://localhost:8000
```

**Nexus Telco Deployer:**
```bash
cd nexus-deployer
# Backend
cd backend && pip install -r requirements.txt && python app/main.py
# Frontend
cd frontend && npm install && npm run dev
# Electron
cd electron && npm install && npm run dev
```

### LocalStack Development

```bash
# Start LocalStack
docker-compose -f docker-compose-localstack.yml up -d

# Configure environment
export USE_LOCALSTACK=true
export LOCALSTACK_HOST=localhost
export LOCALSTACK_PORT=4566

# Initialize resources
python -m tests.localstack_automation.run_automation --setup
```

---

## Monitoring & Operations

### Health Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Nexus Telco Backend | `/health` | Service health |
| Nexus Telco Backend | `/ready` | Readiness probe |
| Nexus Telco Backend | `/live` | Liveness probe |
| Nexus Telco Deployer | `/` | Root health check |
| Nexus Telco Deployer | `/api/health` | Detailed health |

### CloudWatch Integration

- **Logs**: Application logs streamed to CloudWatch Logs
- **Metrics**: Custom metrics for call processing
- **Alarms**: Automated alerts for failures
- **Dashboards**: Real-time monitoring dashboards

---

## Additional Capabilities (Future Enhancements)

<<<<<<< HEAD
| Component | Version | Status |
|-----------|---------|--------|
| Nexus Telco UI | 1.0.0 | Production Ready |
| Nexus Telco Backend | 0.0.1 | Development |
| Nexus Telco Deployer | 0.0.1 | Development |
=======
The following advanced features are available for future activation beyond the core subscription:

### 1. Product Recommendations Engine
Automatically analyzes customer interactions and generates intelligent product suggestions to maximize sales opportunities.

**Features:**
- Recommendation categorization (upsells, cross-sells, bundles)
- Existing product analysis for upgrade opportunities
- Personalized offers based on customer needs
- Business rationale generation for each recommendation

### 2. Automatic Quote Generation
Transforms customer conversations into accurate, ready-to-send quotes through CloudSense integration.

**Capabilities:**
- Automatic product identification from conversations
- Real-time pricing rules application
- Complete quote generation
- Seamless delivery via Salesforce contact information

### 3. Office 365 Integration & Email Analysis
Extends analytics to written communications for complete customer interaction coverage.

**Features:**
- Automatic email capture and processing
- Intent and sentiment analysis of emails
- Compliance monitoring for written communications
- Attachment and conversation history linking
- Integration with Salesforce opportunities
>>>>>>> 526963d5b9e92b55e70d7b20e70edaa490767538

---

## Version Information

| Application | Component | Version | Status |
|-------------|-----------|---------|--------|
| **Totogi CallSense** | Nexus Telco UI | 1.0.0 | Production Ready |
| **Totogi CallSense** | Nexus Telco Backend | 2.0.0 | Production Ready |
| **Totogi Toolkit** | Nexus Telco Deployer | 1.0.0 | Production Ready |

---

## Conclusion

Totogi's enterprise solution delivers:

1. **Totogi CallSense** - A production-ready AI-powered call analytics platform that delivers 25-55x ROI through improved conversion rates, operational efficiency, and strategic insights.

2. **Totogi Toolkit** - A self-service deployment platform that enables rapid, secure deployment of Totogi capabilities to customer AWS infrastructure.

Together, these applications provide:
- ✅ **Proven ROI**: Multi-million dollar revenue impact
- ✅ **Operational Excellence**: 100% QA coverage, 50% time savings
- ✅ **Strategic Value**: Permanent data assets and insights
- ✅ **Simple Deployment**: One-click AWS infrastructure provisioning
- ✅ **Enterprise Security**: AWS-native security and compliance
- ✅ **Scalable Architecture**: Cloud-native design for growth

**Investment**: $84,000 (2-year commitment)  
**Expected Return**: $4.8M - $9.6M (2-year impact)  
**Net Value**: $4.7M - $9.5M  

---

*Last Updated: January 2026*  
*Document Version: 2.0*  
*Maintained by: Totogi Engineering Team*
